from abc import ABC, abstractmethod
from typing import Self
import docker
import docker.errors
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
import logging
import requests
import time
import os
from enum import Enum
from zipfile import ZipFile

logger = logging.getLogger(__name__)

class SupportedLanguage(Enum):
    CPP = "cpp"
    PYTHON3 = "python3"
    PYPY3 = "pypy3"

class Judge(ABC):
    @abstractmethod
    def __enter__(self) -> Self:
        pass
    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        pass
    @abstractmethod
    def submit(self, problem_id: str, language: SupportedLanguage, code: str) -> int:
        pass
    @abstractmethod
    def get_result(self, submission_id: int) -> str:
        pass

class ProblemNotFoundError(Exception):
    pass

class LightCPVerifierJudge(Judge):
    IMAGE_NAME = "lightcpverifier"
    CONTAINER_NAME = "lightcpverifier"
    REPO_DIR = os.path.realpath("LightCPVerifier")
    PROBLEMS_DIR = os.path.join(REPO_DIR, "problems")
    DATASET_HF_REPO = "QAQAQAQAQ/LiveCodeBench-Pro-Testcase"

    def __init__(self, worker: int = 4):
        self.worker = worker

    def __enter__(self):
        self.docker_client = docker.from_env()
        self._build_image()
        self._start_container()
        self._ensure_connection()
        return self

    def _build_image(self):
        try:
            self.docker_client.images.get(self.IMAGE_NAME)
            logger.info(f"Image '{self.IMAGE_NAME}' found locally.")
        except docker.errors.ImageNotFound:
            logger.warning(f"Image '{self.IMAGE_NAME}' not found. Building it now...")
            self.docker_client.images.build(
                path=self.REPO_DIR,
                tag=self.IMAGE_NAME,
            )
            logger.info(f"Image '{self.IMAGE_NAME}' built successfully.")

    def _start_container(self):
        try:
            existing_container = self.docker_client.containers.get(self.CONTAINER_NAME)
            logger.info(f"Container '{self.CONTAINER_NAME}' already exists. Removing it...")
            existing_container.stop()
            existing_container.remove()
            logger.info(f"Container '{self.CONTAINER_NAME}' removed.")
        except docker.errors.NotFound:
            pass
        os.makedirs(self.PROBLEMS_DIR, exist_ok=True)
        self.container = self.docker_client.containers.run(
            image=self.IMAGE_NAME,
            name=self.CONTAINER_NAME,
            privileged=True,
            detach=True,
            shm_size="4g",
            environment={
                "JUDGE_WORKERS": str(self.worker),
                "GJ_PARALLELISM": str(self.worker),
            },
            volumes=[
                f"{self.PROBLEMS_DIR}:/app/problems",
                f"{os.path.join(self.REPO_DIR, "submissions")}:/app/submissions",
                f"{os.path.join(self.REPO_DIR, "data")}:/app/data",
            ],
            ports={"8081/tcp": None},
            restart_policy={"Name": "on-failure"},
        )
        while self.container.status != "running":
            time.sleep(1)
            self.container.reload()
        port = self.container.ports['8081/tcp'][0]['HostPort']
        self.base_url = f"http://localhost:{port}"
        logger.info(f"Container '{self.CONTAINER_NAME}' started, listening on port {port}.")

    def _check_connection(self):
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Connection to judge service failed: {e}")
            return False

    def _ensure_connection(self):
        logger.info("Checking connection to judge service...")
        for _ in range(30):
            if self._check_connection():
                logger.info("Connection to judge service established.")
                return
            time.sleep(2)
        raise RuntimeError("Failed to connect to judge service after multiple attempts.")

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            logger.info(f"Stopping and removing container '{self.CONTAINER_NAME}'...")
            self.container.stop()
            self.container.remove()
            logger.info(f"Container '{self.CONTAINER_NAME}' stopped and removed.")
        except Exception as e:
            logger.error(f"Error stopping/removing container '{self.CONTAINER_NAME}': {e}")

    def _ensure_data_downloaded(self, problem_id: str):
        problem_dir = os.path.join(self.PROBLEMS_DIR, problem_id)
        if os.path.exists(os.path.join(problem_dir, "config.yaml")):
            return
        logger.debug(f"Downloading data for problem '{problem_id}'...")
        try:
            zip_path = hf_hub_download(
                repo_id=self.DATASET_HF_REPO,
                filename=f"{problem_id}.zip",
                repo_type="dataset",
            )
        except EntryNotFoundError:
            raise ProblemNotFoundError(f"Problem '{problem_id}' not found in dataset repository.")
        os.makedirs(problem_dir, exist_ok=True)
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(problem_dir)
        logger.debug(f"Data for problem '{problem_id}' downloaded and extracted.")

    def submit(self, problem_id: str, language: SupportedLanguage, code: str) -> int:
        self._ensure_data_downloaded(problem_id)
        response = requests.post(
            f"{self.base_url}/submit",
            json={
                "pid": problem_id,
                "lang": language.value,
                "code": code
            }
        )
        if response.status_code != 200:
            print(response.text)
        response.raise_for_status()
        return response.json()["sid"]

    def get_result(self, submission_id: int) -> str:
        response = requests.get(f"{self.base_url}/result/{submission_id}")
        if response.status_code == 404:
            return "Judging"
        response.raise_for_status()
        result = response.json()
        if result["status"] == "queued":
            return "Judging"
        if result["status"] == "error":
            return "Judge Failed"
        return result["result"]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with LightCPVerifierJudge(worker=2) as judge:
        sid = judge.submit("2000A", SupportedLanguage.CPP, "#include <bits/stdc++.h>\nusing namespace std;\n\n\nint main()\n{   int t;\ncin>>t;\nwhile(t--){\n    string s;\n    cin>>s;\n    if(s[0]=='1'&&s[1]=='0'&&s[2]!='0'&&(!(s[2]=='1')||s.length()>3)&&s.length()>2){cout<<\"YES\"<<endl; }\n    else cout<<\"NO\"<<endl;\n\n}\n\n    return 0;\n}\n\n")
        print(f"Submitted with ID: {sid}")
        while True:
            result = judge.get_result(sid)
            print(f"Result: {result}")
            if result != "Judging":
                break
            time.sleep(2)
