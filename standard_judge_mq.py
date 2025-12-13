import requests
import logging
import pydantic
import typing
import json
import time
from judge import LightCPVerifierJudge, Judge, SupportedLanguage, ProblemNotFoundError
import traceback
from google.cloud.secretmanager_v1 import SecretManagerServiceClient
import os
import pika.exceptions
import pika.spec
import pika.channel
import functools

logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()

logger = logging.getLogger("standard_judge_mq")

JUDGE_MQ_URL_KEY = "judge-mq-url"
JUDGE_MQ_QUEUE = "local_codeforces"
project_id = os.getenv("GCP_PROJECT_ID")

def get_project_id():
    global project_id
    if project_id:
        return project_id
    logger.info("Fetching project ID from GCP metadata server")
    response = requests.get(f"http://metadata/computeMetadata/v1/project/project-id", headers={
        "Metadata-Flavor": "Google",
    })
    response.raise_for_status()
    project_id = response.text
    return project_id

def get_mq_url() -> str:
    client = SecretManagerServiceClient()
    secret = client.access_secret_version(name=f"projects/{get_project_id()}/secrets/{JUDGE_MQ_URL_KEY}/versions/latest")
    return secret.payload.data.decode("utf-8")

class BenchmarkResult(pydantic.BaseModel):
    problem_id: str
    problem_title: str
    difficulty: str
    platform: str
    text_response: str
    code: str | None = None
    judge_result: str = "Judging"
    response_meta: typing.Any = None

class ProblemTestState(pydantic.BaseModel):
    problem_id: str
    problem_title: str
    difficulty: str
    platform: str
    text_response: str | None = None
    code: str | None = None
    submission_id: int | None = None
    judge_result: str = "Judging"
    response_meta: typing.Any = None

def detect_language(code: str) -> SupportedLanguage:
    if code.strip().startswith("#include"):
        return SupportedLanguage.CPP
    return SupportedLanguage.PYPY

def call_judge(request: dict, judge: Judge) -> dict:
    session_id = request["session_id"]
    problem_id = request["problem_id"]
    req_language = request["language"]
    code = request["code"]
    
    if req_language == "C++":
        language = SupportedLanguage.CPP
    elif req_language == "Python":
        language = SupportedLanguage.PYPY
    else:
        raise ValueError("Invalid language: " + req_language)
    
    try:
        submission_id = judge.submit(problem_id, language, code)
    except ProblemNotFoundError:
        logger.warning(f"session_id={session_id} Problem {problem_id} not found in judge dataset.")
        raise ValueError("Problem not found")

    while True:
        judge_result = judge.get_result_dict(submission_id)
        if judge_result["verdict"] != "Judging":
            break
        time.sleep(1)
    
    if judge_result["verdict"] == "Accepted":
        judge_result["verdict"] = "ACCEPTED"
    elif judge_result["verdict"] == "Wrong Answer":
        judge_result["verdict"] = "WRONG_ANSWER"
    elif judge_result["verdict"] == "Time Limit Exceeded":
        judge_result["verdict"] = "TIME_LIMIT_EXCEEDED"
    elif judge_result["verdict"] == "Signalled":
        judge_result["verdict"] = "RUNTIME_ERROR"
    else:
        judge_result["verdict"] = "OTHER_ERROR"
    
    return judge_result

def consume(chan: pika.channel.Channel, method: pika.spec.Basic.Deliver, _header: pika.spec.BasicProperties, body: bytes, judge: Judge):
    request = json.loads(body)
    session_id = request["session_id"]
    report_url = request["report_url"]
    logger.info("session_id=%s Got request", session_id)
    try:
        result = call_judge(request, judge)
    except Exception as e:
        import traceback
        stacktrace = traceback.format_exc()
        logger.error("session_id=%s Judge failed", session_id, exc_info=True)
        result = {"verdict": "SYSTEM_ERROR", "error": str(e), "stacktrace": stacktrace}

    for _ in range(3):
        try:
            requests.post(f"{report_url}/{session_id}/final", json=result)
            chan.basic_ack(method.delivery_tag)
            logger.info("session_id=%s ACK", session_id)
            return
        except Exception as e:
            logger.error("session_id=%s Failed to report result", session_id, exc_info=True)
    
    chan.basic_nack(method.delivery_tag)
    logger.info("session_id=%s NACK", session_id)

def consumer_connection_loop(mq_url: str, judge: Judge):
    while True:
        conn = pika.BlockingConnection(pika.URLParameters(mq_url))
        chan = conn.channel()
        chan.queue_declare(JUDGE_MQ_QUEUE, durable=True)
        chan.basic_qos(prefetch_count=1)
        chan.basic_consume(JUDGE_MQ_QUEUE, on_message_callback=functools.partial(consume, judge=judge))
        try:
            chan.start_consuming()
        except KeyboardInterrupt:
            break
        except pika.exceptions.AMQPConnectionError:
            logger.warning("AMQP connection error, retrying after 10s", exc_info=True)
            time.sleep(10)
            continue
        finally:
            chan.stop_consuming()
            chan.close()
            conn.close()

def main():
    mq_url = get_mq_url()
    with LightCPVerifierJudge(worker=1) as judge:
        consumer_connection_loop(mq_url, judge)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error during judging process: {e}")
        traceback_str = traceback.format_exc()
        logger.error(traceback_str)
