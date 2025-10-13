import requests
import jwt
import logging
import pydantic
import typing
import json
import tqdm
import time
from tempfile import TemporaryFile
from judge import LightCPVerifierJudge, SupportedLanguage, ProblemNotFoundError
import traceback
from util import extract_longest_cpp_code, extract_python_code

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("standard_judge")

API_BASE = "https://webhook.cp-bench.orzzh.com"

token = None

def get_oidc_token():
    global token
    if token and jwt.decode(token, options={"verify_signature": False})["exp"] > time.time() + 60:
        return token
    logger.info("Fetching new OIDC token from GCP metadata server")
    response = requests.get(f"http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?audience={API_BASE}&format=full", headers={
        "Metadata-Flavor": "Google",
    })
    response.raise_for_status()
    token = response.text
    return token

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

def prepare_inputs() -> list[ProblemTestState]:
    logger.info("Fetching input file")
    response = requests.get(
        f"{API_BASE}/standard_judge/callback/input_file",
        headers={"Authorization": f"Bearer {get_oidc_token()}"},
        allow_redirects=True
    )
    raw_data = response.json()
    data = []
    for item in raw_data:
        item = BenchmarkResult(**item)
        if not item.code:
            item.code = extract_longest_cpp_code(item.text_response) or extract_python_code(item.text_response)
        data.append(ProblemTestState(**item.model_dump()))
    logger.info(f"Fetched {len(data)} problems to judge")
    return data

def upload_output(results: list[dict]):
    logger.info("Fetching output file upload URL")
    resp = requests.get(
        f"{API_BASE}/standard_judge/callback/output_file",
        headers={"Authorization": f"Bearer {get_oidc_token()}"}
    )
    resp.raise_for_status()
    with TemporaryFile("w+") as f:
        json.dump(results, f, indent=4)
        f.flush()
        f.seek(0)
        logger.info("Uploading output file")
        upload_resp = requests.put(
            resp.text,
            data=f,
            headers={"Content-Type": "application/json"}
        )
        upload_resp.raise_for_status()
    logger.info("Output file uploaded successfully")

def update_status(status: str):
    logger.info(f"Updating status to '{status}'")
    resp = requests.put(
        f"{API_BASE}/standard_judge/callback/status",
        headers={"Authorization": f"Bearer {get_oidc_token()}"},
        json={"status": status}
    )
    resp.raise_for_status()
    logger.info("Status updated successfully")

def append_log(log: str):
    logger.info(f"Appending log: {log}")
    resp = requests.post(
        f"{API_BASE}/standard_judge/callback/append_log",
        headers={"Authorization": f"Bearer {get_oidc_token()}"},
        json={"log": log}
    )
    resp.raise_for_status()
    logger.info("Log appended successfully")

def detect_language(code: str) -> SupportedLanguage:
    if code.strip().startswith("#include"):
        return SupportedLanguage.CPP
    return SupportedLanguage.PYPY

def main():
    inputs = prepare_inputs()
    update_status("running")
    with LightCPVerifierJudge(worker=1) as judge:
        for index, item in enumerate(inputs):
            logger.info("Submitting problem %d/%d: %s", index + 1, len(inputs), item.problem_id)
            if not item.code:
                item.judge_result = "Judge Failed"
                continue
            try:
                item.submission_id = judge.submit(item.problem_id, detect_language(item.code), item.code)
            except ProblemNotFoundError:
                logger.warning(f"Problem {item.problem_id} not found in judge dataset.")
                item.judge_result = "Judge Failed"
                continue
            except Exception as e:
                logger.error(f"Error submitting problem {item.problem_id}: {e}")
                item.judge_result = "Judge Failed"
                continue
        for index, item in enumerate(inputs):
            logger.info("Fetching result for problem %d/%d: %s", index + 1, len(inputs), item.problem_id)
            if not item.submission_id:
                continue
            while True:
                item.judge_result = judge.get_result(item.submission_id)
                if item.judge_result != "Judging":
                    break
                time.sleep(1)
    results = [BenchmarkResult(**item.model_dump()).model_dump() for item in inputs]
    upload_output(results)

if __name__ == "__main__":
    try:
        main()
        update_status("finished")
    except Exception as e:
        logger.error(f"Error during judging process: {e}")
        traceback_str = traceback.format_exc()
        logger.error(traceback_str)
        append_log(f"Python error: {e}, Traceback: {traceback_str}")
        update_status("failed")
