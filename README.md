# LiveCodeBench Pro - LLM Benchmarking Toolkit

<p align="center">
<img width="1415" height="420" alt="image" src="https://github.com/user-attachments/assets/2795fbe8-df64-4664-b834-33346157973e" />
</p>

This repository contains a benchmarking toolkit for evaluating Large Language Models (LLMs) on competitive programming tasks. The toolkit provides a standardized way to test your LLM's code generation capabilities across a diverse set of problems.

## Overview

LiveCodeBench Pro evaluates LLMs on their ability to generate solutions for programming problems. The benchmark includes problems of varying difficulty levels from different competitive programming platforms.

## Getting Started

### Prerequisites

- Ubuntu 20.04 or higher (or other distros with kernel version >= 3.10, and cgroup support. Refer to [go-judge](https://github.com/criyle/go-judge) for more details)
- Python 3.12 or higher
- pip package manager
- docker (for running the judge server), and ensure the user has permission to run docker commands

### Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install directly using `uv`:
   ```bash
   uv sync
   ```

2. Ensure Docker is installed and running:
   ```bash
   docker --version
   ```
   
   Make sure your user has permission to run Docker commands. On Linux, you may need to add your user to the docker group:
   ```bash
   sudo usermod -aG docker $USER
   ```
   Then log out and back in for the changes to take effect.

## How to Use

### Step 1: Implement Your LLM Interface

Create your own LLM class by extending the abstract `LLMInterface` class in `api_interface.py`. Your implementation needs to override the `call_llm` method.

Example:
```python
from api_interface import LLMInterface

class YourLLM(LLMInterface):
    def __init__(self):
        super().__init__()
        # Initialize your LLM client or resources here
        
    def call_llm(self, user_prompt: str):
        # Implement your logic to call your LLM with user_prompt
        # Return a tuple containing (response_text, metadata)
        
        # Example:
        response = your_llm_client.generate(user_prompt)
        return response.text, response.metadata
```

You can use the `ExampleLLM` class as a reference, which shows how to integrate with OpenAI's API.

### Step 2: Configure the Benchmark

Edit the `benchmark.py` file to use your LLM implementation:

```python
from your_module import YourLLM

# Replace this line:
llm_instance = YourLLM()  # Update with your LLM class
```

And change the number of judge workers (recommended to <= physical CPU cores).

### Step 3: Run the Benchmark

Execute the benchmark script:

```bash
python benchmark.py
```

The script will:
1. Load the LiveCodeBench-Pro dataset from Hugging Face
2. Process each problem with your LLM
3. Extract C++ code from LLM responses automatically
4. Submit solutions to the integrated judge system for evaluation
5. Collect judge results and generate comprehensive statistics
6. Save the results to `benchmark_result.json`

### (Optional) Step 4: Submit Your Results

Email your `benchmark_result.json` file to zz4242@nyu.edu to have it displayed on the leaderboard.

Please include the following information in your submission:
- LLM name and version
- Any specific details
- Contact information

## Understanding the Codebase

### api_interface.py

This file defines the abstract interface for LLM integration:
- `LLMInterface`: Abstract base class with methods for LLM interaction
- `ExampleLLM`: Example implementation with OpenAI's GPT-4o

### benchmark.py

The main benchmarking script that:
- Loads the dataset
- Processes each problem through your LLM
- Extracts C++ code from responses
- Submits solutions to the judge system
- Collects results and generates statistics
- Saves comprehensive results with judge verdicts

### judge.py

Contains the judge system integration:
- `Judge`: Abstract base class for judge implementations
- `LightCPVerifierJudge`: LightCPVerifier integration for local solution evaluation
- Automatic problem data downloading from Hugging Face

### util.py

Utility functions for code processing:
- `extract_longest_cpp_code()`: Intelligent C++ code extraction from LLM responses


### Dataset

The benchmark uses the [QAQAQAQAQ/LiveCodeBench-Pro](https://huggingface.co/datasets/QAQAQAQAQ/LiveCodeBench-Pro) and [QAQAQAQAQ/LiveCodeBench-Pro-Testcase](https://huggingface.co/datasets/QAQAQAQAQ/LiveCodeBench-Pro-Testcase) datasets from Hugging Face, which contains competitive programming problems with varying difficulty levels.




## Contact

For questions or support, please contact us at zz4242@nyu.edu.
