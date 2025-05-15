from datasets import load_dataset
import pydantic
import typing
import api_interface
import json
import tqdm


class BenchmarkResult(pydantic.BaseModel):
    problem_id: str
    problem_title: str
    difficulty: str
    platform: str
    text_response: str
    response_meta: typing.Any


# *************************** Change this before use ****************************

llm_instance = (
    api_interface.ExampleLLM()
)  # change this to the LLM class you want to benchmark on

# *******************************************************************************

if __name__ == "__main__":
    dataset = load_dataset("anonymous1926/anonymous_dataset")
    result = []
    for split_name, split in dataset.items():
        for row in tqdm.tqdm(split, desc=f"Processing {split_name}"):
            response, meta = llm_instance.generate_solution(row["problem_statement"])
            benchmark_result = BenchmarkResult(
                problem_id=row["problem_id"],
                problem_title=row["problem_title"],
                difficulty=row["difficulty"],
                platform=row["platform"],
                text_response=response,
                response_meta=meta,
            ).model_dump()
            result.append(benchmark_result)
    with open("benchmark_result.json", "w") as f:
        json.dump(result, f, indent=4)
