# LiveCodeBench Pro - LLM Benchmarking Toolkit

This repository contains a benchmarking toolkit for evaluating Large Language Models (LLMs) on competitive programming tasks. The toolkit provides a standardized way to test your LLM's code generation capabilities across a diverse set of problems.

## Overview

LiveCodeBench Pro evaluates LLMs on their ability to generate solutions for programming problems. The benchmark includes problems of varying difficulty levels from different competitive programming platforms.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- pip package manager

### Installation

Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

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

### Step 3: Run the Benchmark

Execute the benchmark script:

```bash
python benchmark.py
```

The script will:
1. Load the LiveCodeBench-Pro dataset from Hugging Face
2. Process each problem with your LLM
3. Save the results to `benchmark_result.json`

### Step 4: Submit Your Results

Send your `benchmark_result.json` file to zz4242@nyu.edu for evaluation.

Please include the following information in your submission:
- LLM name and version
- Any specific details
- Contact information for results

## Understanding the Codebase

### api_interface.py

This file defines the abstract interface for LLM integration:
- `LLMInterface`: Abstract base class with methods for LLM interaction
- `ExampleLLM`: Example implementation with OpenAI's GPT-4o

### benchmark.py

The main benchmarking script that:
- Loads the dataset
- Processes each problem through your LLM
- Collects and saves results

### Dataset

The benchmark uses the [QAQAQAQAQ/LiveCodeBench-Pro](https://huggingface.co/datasets/QAQAQAQAQ/LiveCodeBench-Pro) dataset from Hugging Face, which contains competitive programming problems with varying difficulty levels.



## Contact

For questions or support, please contact us at zz4242@nyu.edu.