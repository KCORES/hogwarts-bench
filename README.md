# Hogwarts-bench

Automated testing framework for evaluating LLM long-context capabilities using the Harry Potter novel series.

## Overview

Hogwarts-bench is a "needle in a haystack" style benchmark that systematically evaluates large language models' ability to recall facts, remember details, and synthesize information across different context lengths and positions within long documents.

The framework uses the Harry Potter novel series as a standardized corpus to test:
- **Fact Retrieval**: Can the model find specific information at different positions?
- **Detail Recall**: Does the model remember fine-grained details from the text?
- **Information Synthesis**: Can the model combine information from multiple parts?
- **Position Bias**: Does performance degrade at certain context positions?

### Key Features

- **Automated Question Generation**: Generate diverse test questions from any novel text
- **Flexible Sampling Strategies**: Stratified or random sampling to cover different text regions
- **Concurrent Processing**: Parallel API calls for faster generation and testing
- **Robust Error Handling**: Retry logic and fallback strategies for API failures
- **Interactive Reports**: HTML reports with visualizations and error analysis
- **Customizable Prompts**: Easy-to-modify JSON templates for different use cases

### Architecture

The framework consists of three independent CLI tools that can be executed sequentially or separately:

1. **Question Generator** (`generate.py`): Automatically generates test questions from novel text
2. **Testing Tool** (`test.py`): Executes tests on target LLMs and collects results
3. **Report Generator** (`report.py`): Analyzes results and generates interactive HTML reports

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install the package in development mode:

```bash
pip install -e .
```

## Configuration

1. Copy the example configuration file:

```bash
cp .env.example .env
```

2. Edit `.env` and fill in your API credentials:

```bash
# Required
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=anthropic/claude-3-sonnet

# Optional (defaults provided)
OPENAI_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2000
DEFAULT_TIMEOUT=60
DEFAULT_CONCURRENCY=5
DEFAULT_RETRY_TIMES=3
```

## Usage

### Quick Start

Here's a complete workflow example:

```bash
# 1. Generate 200 questions from a novel
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --output data/questions.jsonl

# 2. Test an LLM with 50k token context
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --output data/results.jsonl

# 3. Generate an interactive HTML report
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html
```

### 1. Generate Questions

The question generator creates structured test questions from novel text using an LLM.

#### Basic Usage

```bash
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --output data/questions.jsonl
```

#### Advanced Usage with All Options

```bash
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --sampling_strategy stratified \
    --context_window_size 500 \
    --concurrency 10 \
    --retry_times 3 \
    --output data/questions.jsonl
```

#### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--novel` | Yes | - | Path to novel text file (UTF-8 encoded) |
| `--question_nums` | Yes | - | Number of questions to generate |
| `--sampling_strategy` | No | `stratified` | Sampling method: `stratified` or `random` |
| `--context_window_size` | No | `500` | Token window size for context extraction |
| `--concurrency` | No | `5` | Number of concurrent API requests |
| `--retry_times` | No | `3` | Maximum retry attempts for failed requests |
| `--output` | Yes | - | Output JSONL file path |

#### Sampling Strategies

- **Stratified Sampling** (recommended): Divides the novel into 50k token layers and samples uniformly from each layer. This ensures coverage across the entire novel.
- **Random Sampling**: Randomly samples positions across the entire novel. Useful for unbiased testing but may miss certain regions.

#### Output Format

The output is a JSONL file where each line contains:

```json
{
  "question": "What spell did Harry use?",
  "question_type": "single_choice",
  "choice": {
    "a": "Expelliarmus",
    "b": "Stupefy",
    "c": "Protego",
    "d": "Expecto Patronum"
  },
  "answer": ["a"],
  "position": {
    "start_pos": 12500,
    "end_pos": 12650
  }
}
```

### 2. Run Tests

The testing tool executes tests on a target LLM using generated questions.

#### Basic Usage

```bash
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --output data/results.jsonl
```

#### Advanced Usage with All Options

```bash
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --padding_size 500 \
    --concurrency 5 \
    --output data/results.jsonl
```

#### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--novel` | Yes | - | Path to novel text file (same as used for generation) |
| `--data_set` | Yes | - | Path to question set JSONL file |
| `--context_length` | Yes | - | Total context length (in tokens) to provide to LLM |
| `--padding_size` | No | `500` | Buffer tokens to ensure answers aren't truncated |
| `--concurrency` | No | `5` | Number of concurrent test requests |
| `--output` | Yes | - | Output results JSONL file path |

#### Context Length Guidelines

- **8k tokens**: Tests short-context performance
- **32k tokens**: Tests medium-context performance
- **50k-100k tokens**: Tests long-context performance
- **128k+ tokens**: Tests extended-context performance

The tool automatically filters questions whose answers fall outside the context window (considering padding).

#### Output Format

The output is a JSONL file where each line contains:

```json
{
  "question": "What spell did Harry use?",
  "question_type": "single_choice",
  "choice": {"a": "Expelliarmus", "b": "Stupefy", "c": "Protego", "d": "Expecto Patronum"},
  "correct_answer": ["a"],
  "model_answer": ["a"],
  "parsing_status": "success",
  "position": {"start_pos": 12500, "end_pos": 12650},
  "score": 1.0
}
```

### 3. Generate Report

The report generator creates an interactive HTML report with visualizations and metrics.

#### Basic Usage

```bash
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html
```

#### Advanced Usage with All Options

```bash
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html \
    --error_examples 15
```

#### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--results` | Yes | - | Path to test results JSONL file |
| `--output` | Yes | - | Output HTML report file path |
| `--error_examples` | No | `10` | Number of error cases to display in report |

#### Report Contents

The generated HTML report includes:

1. **Summary Section**
   - Test configuration (model, context length, etc.)
   - Overall metrics (accuracy, precision, recall, F1-score)
   - Question type breakdown

2. **Interactive Scatter Plot**
   - X-axis: Token position in novel
   - Y-axis: Performance score (0.0 to 1.0)
   - Color coding: Green (correct), Yellow (partial), Red (incorrect), Gray (error)
   - Hover tooltips with question details
   - Trend line showing performance across positions

3. **Error Analysis**
   - Random sample of incorrect or partially correct answers
   - Shows question, correct answer, model answer, and score
   - Helps identify patterns in model failures

## Project Structure

```
hogwarts-bench/
├── src/
│   ├── core/                      # Core utilities
│   │   ├── config.py              # Configuration manager
│   │   ├── llm_client.py          # LLM API client with retry logic
│   │   ├── tokenizer.py           # Tokenization utilities (tiktoken)
│   │   ├── validator.py           # Question validation
│   │   ├── prompt_template.py     # Prompt template manager
│   │   └── file_io.py             # File I/O utilities
│   ├── generator/                 # Question generation module
│   │   ├── question_generator.py  # Main generation logic
│   │   └── sampling.py            # Sampling strategies
│   ├── tester/                    # Testing module
│   │   ├── testing_tool.py        # Main testing logic
│   │   └── parser.py              # Answer parsing with fallbacks
│   ├── reporter/                  # Report generation module
│   │   ├── report_generator.py    # Main report logic
│   │   ├── metrics.py             # Metrics calculation
│   │   └── visualization.py       # Plotly visualizations
│   ├── generate.py                # Question generator CLI
│   ├── test.py                    # Testing tool CLI
│   └── report.py                  # Report generator CLI
├── prompts/                       # Prompt templates
│   ├── question_generation.json   # Question generation template
│   ├── testing.json               # Testing template
│   └── README.md                  # Template documentation
├── tests/                         # Test suite
│   ├── test_*.py                  # Unit and integration tests
│   └── fixtures/                  # Test fixtures
├── data/                          # Data directory (create this)
│   ├── novels/                    # Place your novel files here
│   ├── questions/                 # Generated question sets
│   └── results/                   # Test results
├── reports/                       # Generated HTML reports (create this)
├── .env.example                   # Example configuration
├── .env                           # Your configuration (create this)
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
└── README.md                      # This file
```

### Directory Setup

Create the necessary directories for data and reports:

```bash
mkdir -p data/novels data/questions data/results reports
```

## Customization

### Prompt Templates

Hogwarts-bench uses customizable JSON prompt templates for question generation and testing. You can modify these templates to adapt the framework for different languages, domains, or question styles.

#### Template Location

Prompt templates are stored in the `prompts/` directory:
- `prompts/question_generation.json`: Template for generating questions
- `prompts/testing.json`: Template for testing LLMs

#### Template Structure

Each template file must be valid JSON with the following structure:

```json
{
  "system": "System prompt that sets the context and role",
  "user": "User prompt with {placeholders} for dynamic content",
  "constraints": [
    "Optional constraint 1",
    "Optional constraint 2"
  ]
}
```

#### Available Placeholders

**Question Generation Template:**
- `{context}`: The text context extracted from the novel
- `{question_type}`: The type of question to generate (e.g., "single_choice", "multiple_choice")

**Testing Template:**
- `{context}`: The novel text context for answering the question
- `{question}`: The question text
- `{choices}`: Formatted string of answer choices

#### Customization Example

To create questions in English instead of Chinese, modify `prompts/question_generation.json`:

```json
{
  "system": "You are an expert at creating test questions. Generate structured test questions based on the provided context.",
  "user": "Based on the following text:\n\n{context}\n\nGenerate a {question_type} question.\n\nRequirements:\n1. The question should test detailed understanding and recall\n2. For single_choice: provide 4 options with 1 correct answer and 3 distractors\n3. For multiple_choice: provide 4 options with at least 2 correct answers and at least 2 distractors\n4. Output must be valid JSON in this format:\n{\n  \"question\": \"Question text\",\n  \"question_type\": \"single_choice or multiple_choice\",\n  \"choice\": {\n    \"a\": \"Option A\",\n    \"b\": \"Option B\",\n    \"c\": \"Option C\",\n    \"d\": \"Option D\"\n  },\n  \"answer\": [\"a\"]\n}\n\nOutput only the JSON, no additional text.",
  "constraints": [
    "Output must be valid JSON",
    "Multiple choice must have at least 2 distractors",
    "Answers must be valid choices"
  ]
}
```

#### Loading Custom Templates Programmatically

```python
from src.core.prompt_template import PromptTemplateManager

# Load templates from custom directory
manager = PromptTemplateManager(template_dir="my_prompts/")

# Or load a specific custom template
manager.load_custom_template(
    "path/to/custom_template.json",
    template_type="question_generation"
)
```

For more details, see `prompts/README.md`.

### Sampling Strategies

Two sampling strategies are available:

- **Stratified** (default): Divides the novel into 50k token layers and samples uniformly from each layer. This ensures comprehensive coverage across the entire novel and is recommended for most use cases.

- **Random**: Randomly samples positions across the entire novel. Useful for unbiased testing but may result in uneven coverage of different text regions.

You can specify the strategy using the `--sampling_strategy` parameter when generating questions.

## Troubleshooting

### Common Issues and Solutions

#### API Rate Limits

**Problem:** Getting rate limit errors from the API provider.

**Solutions:**
1. Reduce the `--concurrency` parameter (try `--concurrency 3` or `--concurrency 1`)
2. Increase `DEFAULT_RETRY_TIMES` in your `.env` file to allow more retries
3. Add delays between requests by reducing concurrency
4. Check your API provider's rate limits and adjust accordingly

```bash
# Example: Lower concurrency for rate-limited APIs
python -m src.generate \
    --novel data/novel.txt \
    --question_nums 100 \
    --concurrency 2 \
    --retry_times 5 \
    --output data/questions.jsonl
```

#### Timeout Errors

**Problem:** Requests timing out before completion.

**Solutions:**
1. Increase `DEFAULT_TIMEOUT` in your `.env` file (e.g., `DEFAULT_TIMEOUT=120`)
2. Reduce `DEFAULT_MAX_TOKENS` if responses are too long
3. Check your network connection and API endpoint status
4. For very slow endpoints, consider using a different model or provider

```bash
# In .env file
DEFAULT_TIMEOUT=120
DEFAULT_MAX_TOKENS=1500
```

#### Memory Issues

**Problem:** Running out of memory when processing large novels.

**Solutions:**
1. Reduce `--context_length` when testing (e.g., use 32000 instead of 128000)
2. Process questions in smaller batches
3. Reduce `--concurrency` to limit simultaneous operations
4. Close other memory-intensive applications

```bash
# Example: Test with smaller context length
python -m src.test \
    --novel data/large_novel.txt \
    --data_set data/questions.jsonl \
    --context_length 32000 \
    --concurrency 3 \
    --output data/results.jsonl
```

#### Invalid JSON Responses

**Problem:** LLM returns responses that can't be parsed as JSON.

**Solutions:**
1. The framework includes fallback parsing strategies (regex extraction)
2. Check your prompt templates to ensure they clearly request JSON output
3. Try a different model that better follows JSON formatting instructions
4. Review the `parsing_status` field in results to identify problematic responses
5. Increase `DEFAULT_TEMPERATURE` slightly if responses are too rigid, or decrease if too creative

#### Missing or Corrupted Files

**Problem:** Error loading novel, question set, or results files.

**Solutions:**
1. Verify file paths are correct and files exist
2. Ensure files are UTF-8 encoded (especially for non-English text)
3. Check that JSONL files have valid JSON on each line
4. Verify you have read/write permissions for the directories

```bash
# Check file encoding (Linux/Mac)
file -i data/novel.txt

# Convert to UTF-8 if needed (Linux/Mac)
iconv -f GBK -t UTF-8 data/novel.txt > data/novel_utf8.txt
```

#### API Authentication Errors

**Problem:** Getting 401 or 403 errors from the API.

**Solutions:**
1. Verify your `OPENAI_API_KEY` in the `.env` file is correct
2. Check that your API key has sufficient credits/quota
3. Ensure `OPENAI_BASE_URL` matches your API provider
4. For OpenRouter, verify your key is from https://openrouter.ai/keys
5. For OpenAI, use `OPENAI_BASE_URL=https://api.openai.com/v1`

```bash
# Example .env for OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4-turbo-preview

# Example .env for OpenRouter
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=anthropic/claude-3-sonnet
```

#### Questions Not Being Generated

**Problem:** Question generation completes but produces few or no questions.

**Solutions:**
1. Check the logs for validation errors
2. Verify your prompt template requests the correct JSON format
3. Try increasing `--retry_times` to allow more attempts
4. Test with a smaller `--question_nums` first to debug
5. Review the LLM's raw responses to see if they match expected format

#### Poor Test Performance

**Problem:** LLM performs poorly on tests.

**Solutions:**
1. Verify `--context_length` is sufficient to include answer positions
2. Check that `--padding_size` provides enough buffer (default 500 tokens)
3. Ensure the novel text is clean and properly formatted
4. Try a different model that may have better long-context capabilities
5. Review error cases in the HTML report to identify patterns

#### Report Generation Fails

**Problem:** Cannot generate HTML report from results.

**Solutions:**
1. Verify the results JSONL file is valid and not corrupted
2. Check that you have write permissions for the output directory
3. Ensure all required dependencies are installed (`pip install -r requirements.txt`)
4. Try reducing `--error_examples` if there are issues with error sampling
5. Check the console output for specific error messages

### Getting Help

If you encounter issues not covered here:

1. Check the console output for detailed error messages
2. Review the design document (`.kiro/specs/hogwarts-bench/design.md`) for technical details
3. Verify your environment meets the prerequisites (Python 3.8+)
4. Try running with a minimal example first to isolate the issue
5. Open an issue on the project repository with:
   - Error message and stack trace
   - Command you ran
   - Python version and OS
   - Relevant configuration (without API keys)

## Advanced Usage

### Testing Multiple Context Lengths

To evaluate how performance changes with context length, run tests with different `--context_length` values:

```bash
# Test at different context lengths
for length in 8000 16000 32000 64000 128000; do
    python -m src.test \
        --novel data/harry_potter_1.txt \
        --data_set data/questions.jsonl \
        --context_length $length \
        --output data/results_${length}.jsonl
    
    python -m src.report \
        --results data/results_${length}.jsonl \
        --output reports/report_${length}.html
done
```

### Batch Processing Multiple Novels

Process multiple novels in a batch:

```bash
# Generate questions for multiple novels
for novel in data/novels/*.txt; do
    basename=$(basename "$novel" .txt)
    python -m src.generate \
        --novel "$novel" \
        --question_nums 200 \
        --output "data/questions_${basename}.jsonl"
done
```

### Using Different Models

Test the same question set with different models by changing the `MODEL_NAME` in your `.env` file:

```bash
# Test with Claude
MODEL_NAME=anthropic/claude-3-sonnet python -m src.test \
    --novel data/novel.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --output data/results_claude.jsonl

# Test with GPT-4
MODEL_NAME=openai/gpt-4-turbo python -m src.test \
    --novel data/novel.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --output data/results_gpt4.jsonl
```

## Performance Tips

1. **Optimize Concurrency**: Start with low concurrency (2-3) and gradually increase based on your API rate limits
2. **Use Stratified Sampling**: For comprehensive evaluation, stratified sampling ensures coverage across the entire novel
3. **Appropriate Context Windows**: Use 500-1000 tokens for question generation to provide sufficient context
4. **Padding Size**: Keep padding at 500+ tokens to ensure answers aren't cut off at context boundaries
5. **Batch Size**: Generate 50-100 questions at a time for easier debugging and iteration

## Data Format Specifications

### Question Set Format (JSONL)

Each line in the question set file is a JSON object:

```json
{
  "question": "问题文本",
  "question_type": "single_choice",
  "choice": {
    "a": "选项A",
    "b": "选项B", 
    "c": "选项C",
    "d": "选项D"
  },
  "answer": ["a"],
  "position": {
    "start_pos": 12500,
    "end_pos": 12650
  }
}
```

### Test Results Format (JSONL)

Each line in the results file is a JSON object:

```json
{
  "question": "问题文本",
  "question_type": "single_choice",
  "choice": {"a": "选项A", "b": "选项B", "c": "选项C", "d": "选项D"},
  "correct_answer": ["a"],
  "model_answer": ["a"],
  "parsing_status": "success",
  "position": {"start_pos": 12500, "end_pos": 12650},
  "score": 1.0,
  "metrics": {
    "precision": 1.0,
    "recall": 1.0,
    "f1_score": 1.0
  }
}
```

## Metrics Explanation

### Single-Choice Questions

- **Accuracy**: Percentage of questions answered correctly (exact match)

### Multiple-Choice Questions

- **Precision**: Of the options the model selected, what percentage were correct?
- **Recall**: Of the correct options, what percentage did the model select?
- **F1-Score**: Harmonic mean of precision and recall (balanced metric)

### Overall Metrics

- **Macro-Average**: Average of metrics across all questions (treats each question equally)
- **Parsing Success Rate**: Percentage of responses successfully parsed as JSON
- **Refusal Rate**: Percentage of questions the model refused to answer

## Requirements

- Python 3.8 or higher
- pip package manager
- Internet connection for API calls
- API key from OpenAI, OpenRouter, or compatible provider

## Dependencies

Key dependencies (see `requirements.txt` for full list):

- `openai>=1.0.0` - LLM API client
- `tiktoken>=0.5.0` - Tokenization
- `plotly>=5.0.0` - Interactive visualizations
- `python-dotenv>=1.0.0` - Environment configuration
- `aiohttp>=3.9.0` - Async HTTP requests

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd hogwarts-bench

# Install in development mode
pip install -e .

# Run tests
pytest tests/
```

## Citation

If you use Hogwarts-bench in your research, please cite:

```bibtex
@software{hogwarts_bench,
  title={Hogwarts-bench: A Long-Context Evaluation Framework for LLMs},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/hogwarts-bench}
}
```
