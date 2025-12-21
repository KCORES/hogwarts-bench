# Implementation Plan

- [ ] 1. Set up project structure and core utilities
  - Create directory structure following the design (src/, prompts/, tests/, data/)
  - Implement configuration manager to load and validate .env settings
  - Implement tokenizer wrapper with tiktoken for encoding, decoding, and boundary detection
  - Implement file I/O utilities for reading novels and writing JSONL files
  - Create .env.example with all required configuration parameters
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 2. Implement LLM client with retry logic
  - Create LLMClient class using OpenAI Python SDK
  - Implement single generation method with timeout handling
  - Implement batch generation method with configurable concurrency
  - Add retry logic with exponential backoff for network and rate limit errors
  - Add error logging for failed requests
  - _Requirements: 5.2, 5.3, 5.4, 5.5, 6.4, 6.5_

- [ ] 3. Implement prompt template management
  - Create PromptTemplateManager class to load templates from JSON files
  - Create default question generation prompt template with placeholders
  - Create default testing prompt template requiring JSON format output
  - Implement template loading from custom file paths
  - Add validation for template structure
  - _Requirements: 3.5, 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 4. Implement question validator
  - Create QuestionValidator class with structure validation
  - Implement JSON schema validation for required fields
  - Implement content validation for question_type values
  - Implement answer-choice validation to ensure answers are valid choices
  - Add validation for multiple-choice questions to ensure at least 2 distractors
  - _Requirements: 4.2, 4.3, 3.4_

- [ ] 5. Implement sampling strategies
  - Create sampling module with strategy interface
  - Implement stratified sampling by dividing novel into 50k token layers
  - Implement random sampling across entire novel
  - Add position sorting to ensure sequential processing
  - _Requirements: 1.2, 1.3, 1.4, 1.5_

- [ ] 6. Implement context extraction with boundary alignment
  - Create context extraction function in tokenizer module
  - Implement sentence boundary detection using regex for punctuation
  - Implement paragraph boundary detection using double newlines
  - Add fallback to hard cutoff if no boundary found within 100 tokens
  - Return aligned context with adjusted start and end positions
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 7. Implement question generation core logic
  - Create QuestionGenerator class with initialization
  - Implement main generate_questions method orchestrating the pipeline
  - Implement single question generation with LLM call and validation
  - Add concurrent question generation using asyncio
  - Implement retry logic for failed generations
  - Save generated questions to JSONL with metadata
  - _Requirements: 1.1, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.4, 4.5, 5.1_

- [ ] 8. Create question generator CLI
  - Create generate.py CLI script with argparse
  - Add command-line arguments: --novel, --question_nums, --sampling_strategy, --context_window_size, --concurrency, --retry_times, --output
  - Implement main function to load config, initialize components, and run generation
  - Add progress logging and error reporting
  - Add summary statistics at completion
  - _Requirements: 1.1, 1.2, 1.3, 5.1, 5.4_

- [ ] 9. Implement answer parser with fallback strategies
  - Create answer parser module in tester package
  - Implement direct JSON parsing as primary strategy
  - Implement regex extraction as fallback strategy
  - Return parsed answer and parsing status
  - Handle edge cases like empty responses or malformed JSON
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 10. Implement testing tool core logic
  - Create TestingTool class with initialization
  - Implement context preparation by extracting first N tokens
  - Implement question filtering based on position and padding size
  - Implement single question testing with LLM call and answer parsing
  - Add concurrent testing using asyncio
  - Save test results to JSONL with metadata
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.5_

- [ ] 11. Create testing tool CLI
  - Create test.py CLI script with argparse
  - Add command-line arguments: --novel, --data_set, --context_length, --padding_size, --concurrency, --output
  - Implement main function to load config, initialize components, and run tests
  - Add progress logging and error reporting
  - Add summary statistics at completion
  - _Requirements: 7.1, 7.2, 7.4_

- [ ] 12. Implement metrics calculation
  - Create metrics module in reporter package
  - Implement accuracy calculation for single-choice questions
  - Implement precision, recall, and F1-score calculation for multiple-choice questions
  - Implement macro-average calculation across all multiple-choice questions
  - Add result categorization (correct, partially correct, incorrect, parsing error)
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 13. Implement visualization generator
  - Create visualization module using Plotly
  - Implement scatter plot with token position on X-axis and score on Y-axis
  - Implement color coding: green for correct, yellow for partial, red for incorrect, gray for errors
  - Add hover tooltips with question details
  - Implement trend line calculation using moving average
  - Return Plotly HTML div for embedding
  - _Requirements: 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 14. Implement report generator core logic
  - Create ReportGenerator class to load and process results
  - Implement summary section generation with test configuration and metrics
  - Implement error analysis section with random error case sampling
  - Integrate scatter plot visualization
  - Generate complete standalone HTML file with embedded CSS and JavaScript
  - _Requirements: 10.1, 10.2, 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 15. Create report generator CLI
  - Create report.py CLI script with argparse
  - Add command-line arguments: --results, --output, --error_examples
  - Implement main function to load results and generate report
  - Add error handling for missing or corrupted files
  - Add success message with output file path
  - _Requirements: 10.1_

- [ ] 16. Create example configuration and documentation
  - Create .env.example with all configuration parameters and comments
  - Write README.md with project overview, installation, and usage instructions
  - Add CLI usage examples for all three tools
  - Document prompt template customization process
  - Add troubleshooting section for common issues
  - _Requirements: 6.1, 6.2, 13.1, 13.2_

- [ ] 17. Set up dependencies and package configuration
  - Create requirements.txt with all dependencies and version constraints
  - Create setup.py for package installation
  - Add __init__.py files to all packages
  - Configure package entry points for CLI scripts
  - _Requirements: 6.4_
