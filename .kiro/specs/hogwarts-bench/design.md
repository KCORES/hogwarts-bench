# Design Document

## Overview

Hogwarts-bench is a Python-based automated testing framework for evaluating LLM long-context capabilities. The system follows a pipeline architecture with three independent CLI tools that can be executed sequentially or separately. Each tool reads from and writes to standardized file formats (JSONL, JSON, HTML) to ensure modularity and extensibility.

The framework leverages the OpenAI Python SDK for LLM interactions, tiktoken for tokenization, and Plotly for interactive visualizations. All configuration is managed through environment variables and command-line arguments, with sensible defaults to minimize setup friction.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Hogwarts-Bench                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Question        │      │  Testing         │           │
│  │  Generator       │─────▶│  Tool            │           │
│  │  (generate.py)   │      │  (test.py)       │           │
│  └──────────────────┘      └──────────────────┘           │
│         │                           │                      │
│         │ questions.jsonl           │ results.jsonl        │
│         ▼                           ▼                      │
│  ┌──────────────────────────────────────────────┐         │
│  │         Report Generator                     │         │
│  │         (report.py)                          │         │
│  └──────────────────────────────────────────────┘         │
│                      │                                     │
│                      ▼                                     │
│              report.html                                   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                  Shared Components                          │
├─────────────────────────────────────────────────────────────┤
│  • Config Manager    • LLM Client    • Tokenizer           │
│  • Prompt Templates  • Validators    • File I/O Utils      │
└─────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

**Question Generator (`generate.py`)**
- Reads novel text and applies sampling strategies
- Generates questions via LLM with context windows
- Validates and saves structured question sets

**Testing Tool (`test.py`)**
- Loads questions and prepares test context
- Executes tests on target LLM with concurrent requests
- Parses responses and saves structured results

**Report Generator (`report.py`)**
- Analyzes test results and calculates metrics
- Generates interactive HTML reports with visualizations
- Provides error case analysis

## Components and Interfaces

### 1. Configuration Manager

**Purpose:** Centralized configuration loading and validation

**Interface:**
```python
class Config:
    @staticmethod
    def load_from_env() -> dict:
        """Load configuration from .env file"""
        
    @staticmethod
    def validate_config(config: dict) -> bool:
        """Validate required configuration parameters"""
        
    @staticmethod
    def get_llm_config() -> dict:
        """Return LLM-specific configuration"""
```

**Configuration Schema:**
```python
{
    "api_key": str,           # LLM API key
    "base_url": str,          # API endpoint (default: OpenRouter)
    "model_name": str,        # Model identifier
    "temperature": float,     # Generation temperature (default: 0.7)
    "max_tokens": int,        # Max response tokens (default: 2000)
    "timeout": int            # Request timeout in seconds (default: 60)
}
```

### 2. LLM Client

**Purpose:** Unified interface for LLM API calls with retry logic

**Interface:**
```python
class LLMClient:
    def __init__(self, config: dict):
        """Initialize OpenAI client with config"""
        
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate response from LLM"""
        
    async def generate_batch(self, prompts: list[str], 
                            concurrency: int = 5) -> list[str]:
        """Generate responses concurrently"""
        
    def _retry_with_backoff(self, func, max_retries: int = 3):
        """Retry failed requests with exponential backoff"""
```

**Error Handling:**
- Network errors: Retry with exponential backoff
- Rate limit errors: Wait and retry
- Timeout errors: Log and skip after max retries
- Invalid response: Return None and log

### 3. Tokenizer

**Purpose:** Consistent tokenization across all modules

**Interface:**
```python
class Tokenizer:
    def __init__(self, encoding_name: str = "cl100k_base"):
        """Initialize tiktoken encoder"""
        
    def encode(self, text: str) -> list[int]:
        """Convert text to token IDs"""
        
    def decode(self, tokens: list[int]) -> str:
        """Convert token IDs to text"""
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        
    def find_sentence_boundary(self, text: str, 
                              target_pos: int, 
                              direction: str = "forward") -> int:
        """Find nearest sentence boundary from target position"""
```

**Boundary Detection:**
- Use regex to identify sentence endings: `.!?` followed by whitespace or newline
- For paragraph boundaries: Look for double newlines `\n\n`
- If no boundary found within 100 tokens, use hard cutoff

### 4. Prompt Template Manager

**Purpose:** Load and manage customizable prompt templates

**Interface:**
```python
class PromptTemplateManager:
    def __init__(self, template_dir: str = "prompts/"):
        """Load templates from directory"""
        
    def get_question_generation_prompt(self, 
                                      context: str, 
                                      question_type: str) -> str:
        """Get prompt for question generation"""
        
    def get_testing_prompt(self, context: str, question: dict) -> str:
        """Get prompt for model testing"""
        
    def load_custom_template(self, template_path: str):
        """Load user-provided template"""
```

**Template Format:**
Templates are stored as JSON files with placeholders:
```json
{
    "system": "You are an expert at creating test questions...",
    "user": "Based on the following context:\n\n{context}\n\nGenerate a {question_type} question...",
    "constraints": [
        "Output must be valid JSON",
        "Include at least 2 distractor options for multiple choice"
    ]
}
```

### 5. Question Generator Core

**Purpose:** Main logic for question generation

**Interface:**
```python
class QuestionGenerator:
    def __init__(self, config: dict, llm_client: LLMClient):
        """Initialize with configuration and LLM client"""
        
    def generate_questions(self, 
                          novel_path: str,
                          num_questions: int,
                          sampling_strategy: str = "stratified",
                          context_window_size: int = 500,
                          concurrency: int = 5) -> list[dict]:
        """Main entry point for question generation"""
        
    def _sample_positions(self, 
                         total_tokens: int,
                         num_samples: int,
                         strategy: str) -> list[int]:
        """Sample positions based on strategy"""
        
    def _extract_context(self, 
                        tokens: list[int],
                        position: int,
                        window_size: int) -> tuple[list[int], int, int]:
        """Extract context window with boundary alignment"""
        
    async def _generate_single_question(self, 
                                       context: str,
                                       position: int) -> dict:
        """Generate one question from context"""
        
    def _validate_question(self, question: dict) -> bool:
        """Validate question structure and content"""
```

**Sampling Strategy Implementation:**

*Stratified Sampling:*
```python
def _stratified_sample(total_tokens: int, num_samples: int) -> list[int]:
    layer_size = 50000  # tokens per layer
    num_layers = ceil(total_tokens / layer_size)
    samples_per_layer = num_samples // num_layers
    
    positions = []
    for layer_idx in range(num_layers):
        layer_start = layer_idx * layer_size
        layer_end = min((layer_idx + 1) * layer_size, total_tokens)
        
        # Sample uniformly within layer
        for _ in range(samples_per_layer):
            pos = random.randint(layer_start, layer_end - 1)
            positions.append(pos)
    
    return sorted(positions)
```

*Random Sampling:*
```python
def _random_sample(total_tokens: int, num_samples: int) -> list[int]:
    return sorted(random.sample(range(total_tokens), num_samples))
```

### 6. Question Validator

**Purpose:** Validate generated questions meet quality standards

**Interface:**
```python
class QuestionValidator:
    @staticmethod
    def validate_structure(question: dict) -> tuple[bool, str]:
        """Validate JSON structure"""
        
    @staticmethod
    def validate_content(question: dict) -> tuple[bool, str]:
        """Validate content quality"""
        
    @staticmethod
    def validate_answer_choices(question: dict) -> tuple[bool, str]:
        """Validate answers are valid choices"""
```

**Validation Rules:**
1. Required fields: question, question_type, choice, answer, position
2. question_type must be in: single_choice, multiple_choice, negative_question
3. choice must be a dict with at least 2 options
4. answer must be a list of valid choice keys
5. position must have start_pos and end_pos integers
6. For multiple_choice: at least 2 distractor options (total - correct >= 2)

### 7. Testing Tool Core

**Purpose:** Execute tests on target LLM

**Interface:**
```python
class TestingTool:
    def __init__(self, config: dict, llm_client: LLMClient):
        """Initialize with configuration and LLM client"""
        
    def run_tests(self,
                 novel_path: str,
                 question_set_path: str,
                 context_length: int,
                 padding_size: int = 500,
                 concurrency: int = 5) -> list[dict]:
        """Main entry point for testing"""
        
    def _prepare_context(self, 
                        novel_tokens: list[int],
                        context_length: int) -> str:
        """Extract first N tokens as context"""
        
    def _filter_questions(self,
                         questions: list[dict],
                         context_length: int,
                         padding_size: int) -> list[dict]:
        """Filter questions that fit in context"""
        
    async def _test_single_question(self,
                                   context: str,
                                   question: dict) -> dict:
        """Test one question"""
        
    def _parse_answer(self, response: str) -> tuple[list[str], str]:
        """Parse LLM response with fallback strategies"""
```

**Answer Parsing Strategy:**
```python
def _parse_answer(response: str) -> tuple[list[str], str]:
    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(response)
        return data.get("answer", []), "success"
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Regex extraction
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return data.get("answer", []), "regex_extracted"
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Parsing failed
    return [], "parsing_error"
```

### 8. Report Generator Core

**Purpose:** Analyze results and generate HTML reports

**Interface:**
```python
class ReportGenerator:
    def __init__(self, results_path: str):
        """Load test results"""
        
    def generate_report(self, output_path: str):
        """Generate complete HTML report"""
        
    def _calculate_metrics(self) -> dict:
        """Calculate all performance metrics"""
        
    def _generate_summary_section(self) -> str:
        """Generate HTML for summary section"""
        
    def _generate_scatter_plot(self) -> str:
        """Generate Plotly scatter plot HTML"""
        
    def _generate_error_analysis(self, num_examples: int = 10) -> str:
        """Generate error case analysis HTML"""
```

**Metrics Calculation:**

*Single-Choice Accuracy:*
```python
def calculate_accuracy(results: list[dict]) -> float:
    correct = sum(1 for r in results 
                  if r["question_type"] == "single_choice" 
                  and r["model_answer"] == r["correct_answer"])
    total = sum(1 for r in results 
                if r["question_type"] == "single_choice")
    return correct / total if total > 0 else 0.0
```

*Multiple-Choice Metrics:*
```python
def calculate_multi_choice_metrics(results: list[dict]) -> dict:
    precisions, recalls, f1_scores = [], [], []
    
    for result in results:
        if result["question_type"] != "multiple_choice":
            continue
            
        correct = set(result["correct_answer"])
        predicted = set(result["model_answer"])
        
        if len(predicted) == 0:
            precision = 0.0
        else:
            precision = len(correct & predicted) / len(predicted)
            
        if len(correct) == 0:
            recall = 0.0
        else:
            recall = len(correct & predicted) / len(correct)
            
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)
            
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
    
    return {
        "avg_precision": sum(precisions) / len(precisions) if precisions else 0.0,
        "avg_recall": sum(recalls) / len(recalls) if recalls else 0.0,
        "avg_f1": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    }
```

### 9. Visualization Generator

**Purpose:** Create interactive Plotly visualizations

**Interface:**
```python
class VisualizationGenerator:
    def create_scatter_plot(self, 
                           results: list[dict],
                           context_length: int) -> str:
        """Create scatter plot with trend line"""
        
    def _assign_colors(self, result: dict) -> str:
        """Assign color based on correctness"""
        
    def _calculate_trend_line(self, 
                             positions: list[int],
                             scores: list[float]) -> tuple[list[int], list[float]]:
        """Calculate smoothed trend line"""
```

**Scatter Plot Specification:**
- X-axis: Token position (0 to context_length)
- Y-axis: Performance score (0.0 to 1.0)
- Point colors:
  - Green (#28a745): score == 1.0
  - Yellow (#ffc107): 0.0 < score < 1.0
  - Red (#dc3545): score == 0.0
  - Gray (#6c757d): parsing_error or refused
- Hover info: Question text (truncated), correct answer, model answer, score
- Trend line: Moving average with window size = 20 points

## Data Models

### Question Schema

```python
{
    "question": str,              # Question text
    "question_type": str,         # "single_choice" | "multiple_choice" | "negative_question"
    "choice": {                   # Answer choices
        "a": str,
        "b": str,
        "c": str,
        "d": str
    },
    "answer": list[str],          # Correct answer(s), e.g., ["a"] or ["a", "c"]
    "position": {                 # Answer location in novel
        "start_pos": int,         # Start token position
        "end_pos": int            # End token position
    }
}
```

### Question Set Metadata Schema

```python
{
    "metadata": {
        "generated_at": str,      # ISO timestamp
        "model_name": str,        # Model used for generation
        "novel_path": str,        # Source novel file
        "total_questions": int,   # Number of questions
        "sampling_strategy": str, # Sampling method used
        "context_window_size": int,
        "config": dict            # Full generation config
    },
    "questions": list[Question]   # List of question objects
}
```

### Test Result Schema

```python
{
    "question": str,              # Original question
    "question_type": str,         # Question type
    "choice": dict,               # Answer choices
    "correct_answer": list[str],  # Correct answer(s)
    "model_answer": list[str],    # Model's answer(s)
    "parsing_status": str,        # "success" | "regex_extracted" | "parsing_error"
    "position": dict,             # Answer position
    "score": float,               # 0.0 to 1.0 (accuracy or F1)
    "metrics": {                  # For multiple choice only
        "precision": float,
        "recall": float,
        "f1_score": float
    }
}
```

### Test Results File Schema

```python
{
    "metadata": {
        "tested_at": str,         # ISO timestamp
        "model_name": str,        # Model tested
        "novel_path": str,        # Source novel
        "question_set_path": str, # Question set used
        "context_length": int,    # Context length used
        "padding_size": int,      # Padding size used
        "total_questions": int,   # Questions in set
        "tested_questions": int,  # Questions actually tested
        "config": dict            # Full test config
    },
    "results": list[TestResult]   # List of result objects
}
```

## Error Handling

### Question Generation Errors

| Error Type | Handling Strategy |
|------------|------------------|
| LLM API timeout | Retry up to retry_times, then skip question |
| Invalid JSON response | Log error, retry up to retry_times, then skip |
| Validation failure | Log validation error, retry with modified prompt |
| Rate limit exceeded | Wait with exponential backoff, then retry |
| Network error | Retry with exponential backoff up to retry_times |

### Testing Errors

| Error Type | Handling Strategy |
|------------|------------------|
| LLM API timeout | Retry up to retry_times, mark as "timeout" |
| Parsing failure | Apply fallback strategies, mark as "parsing_error" |
| Model refusal | Mark as "refused", include in report |
| Context too long | Skip question, log warning |
| Network error | Retry with exponential backoff |

### Report Generation Errors

| Error Type | Handling Strategy |
|------------|------------------|
| Missing results file | Exit with clear error message |
| Corrupted results data | Skip corrupted entries, log warnings |
| Visualization failure | Generate report without visualization, log error |
| File write error | Exit with error message and suggested fixes |

## Testing Strategy

### Unit Tests

**Core Components to Test:**
1. Tokenizer boundary detection
2. Question validator logic
3. Answer parser with various formats
4. Metrics calculation functions
5. Sampling strategy implementations

**Test Approach:**
- Use pytest framework
- Mock LLM API calls with predefined responses
- Test edge cases (empty input, malformed data, boundary conditions)
- Verify error handling paths

### Integration Tests

**Scenarios to Test:**
1. End-to-end question generation with mock LLM
2. End-to-end testing with mock LLM responses
3. Report generation from sample results
4. Configuration loading and validation
5. File I/O operations

**Test Data:**
- Small sample novel (1000 tokens)
- Pre-generated question sets
- Mock LLM responses (valid, invalid, edge cases)

### Manual Testing

**Validation Steps:**
1. Generate questions from Harry Potter sample chapter
2. Verify question quality and diversity
3. Run tests on a real LLM (e.g., GPT-3.5)
4. Review generated HTML report for correctness
5. Test interactive features in report (hover, zoom)

## Project Structure

```
hogwarts-bench/
├── src/
│   ├── __init__.py
│   ├── generate.py              # Question generator CLI
│   ├── test.py                  # Testing tool CLI
│   ├── report.py                # Report generator CLI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration manager
│   │   ├── llm_client.py        # LLM client wrapper
│   │   ├── tokenizer.py         # Tokenization utilities
│   │   ├── validator.py         # Question validator
│   │   └── file_io.py           # File I/O utilities
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── question_generator.py
│   │   └── sampling.py          # Sampling strategies
│   ├── tester/
│   │   ├── __init__.py
│   │   ├── testing_tool.py
│   │   └── parser.py            # Answer parser
│   └── reporter/
│       ├── __init__.py
│       ├── report_generator.py
│       ├── metrics.py           # Metrics calculation
│       └── visualization.py     # Plotly visualizations
├── prompts/
│   ├── question_generation.json # Default generation prompts
│   └── testing.json             # Default testing prompts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── data/                        # Sample data and outputs
├── .env.example                 # Example configuration
├── requirements.txt
├── README.md
└── setup.py
```

## Dependencies

```
openai>=1.0.0              # LLM API client
tiktoken>=0.5.0            # Tokenization
plotly>=5.0.0              # Interactive visualizations
python-dotenv>=1.0.0       # Environment configuration
aiohttp>=3.9.0             # Async HTTP requests
pytest>=7.0.0              # Testing framework
pytest-asyncio>=0.21.0     # Async test support
```

## Configuration Examples

### .env File

```bash
# LLM Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=anthropic/claude-3-sonnet

# Generation Settings
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2000
DEFAULT_TIMEOUT=60

# Concurrency Settings
DEFAULT_CONCURRENCY=5
DEFAULT_RETRY_TIMES=3
```

### Command-Line Usage

```bash
# Generate questions
python -m src.generate \
    --novel data/harry_potter_1.txt \
    --question_nums 200 \
    --sampling_strategy stratified \
    --context_window_size 500 \
    --concurrency 10 \
    --retry_times 3 \
    --output data/questions.jsonl

# Run tests
python -m src.test \
    --novel data/harry_potter_1.txt \
    --data_set data/questions.jsonl \
    --context_length 50000 \
    --padding_size 500 \
    --concurrency 5 \
    --output data/results.jsonl

# Generate report
python -m src.report \
    --results data/results.jsonl \
    --output reports/report.html \
    --error_examples 15
```
