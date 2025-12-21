# Prompt Templates

This directory contains prompt templates used by hogwarts-bench for question generation and testing.

## Template Files

- `question_generation.json`: Template for generating test questions from novel text
- `testing.json`: Template for testing LLMs with generated questions

## Template Structure

Each template file must be a valid JSON file with the following structure:

```json
{
  "system": "System prompt text",
  "user": "User prompt text with {placeholders}",
  "constraints": [
    "Optional constraint 1",
    "Optional constraint 2"
  ]
}
```

### Required Fields

- **system** (string): The system prompt that sets the context and role for the LLM
- **user** (string): The user prompt template with placeholders for dynamic content

### Optional Fields

- **constraints** (array of strings): List of constraints or requirements for the LLM output

## Placeholders

### Question Generation Template

The `question_generation.json` template supports the following placeholders:

- `{context}`: The text context extracted from the novel
- `{question_type}`: The type of question to generate (e.g., "single_choice", "multiple_choice")

### Testing Template

The `testing.json` template supports the following placeholders:

- `{context}`: The novel text context for answering the question
- `{question}`: The question text
- `{choices}`: Formatted string of answer choices

## Customization

To customize the prompts:

1. Edit the JSON files directly in this directory, or
2. Create new template files and load them programmatically using `PromptTemplateManager.load_custom_template()`

### Example: Custom Question Generation Template

```json
{
  "system": "You are an expert at creating challenging test questions.",
  "user": "Based on this text:\n\n{context}\n\nCreate a {question_type} question that tests deep understanding.",
  "constraints": [
    "Question must be answerable from the text",
    "Distractors should be plausible but incorrect"
  ]
}
```

## Validation

Templates are automatically validated when loaded. The validation checks:

- All required fields are present
- Field types are correct (strings for system/user, array for constraints)
- Template structure is valid JSON

If validation fails, the system will fall back to the default built-in templates.

## Default Templates

If template files are missing or invalid, hogwarts-bench will use built-in default templates. The defaults are optimized for Chinese language content and Harry Potter novels.

## Usage in Code

```python
from src.core.prompt_template import PromptTemplateManager

# Load templates from this directory
manager = PromptTemplateManager(template_dir="prompts/")

# Get formatted prompts for question generation
system, user = manager.get_question_generation_prompt(
    context="Your text here",
    question_type="single_choice"
)

# Get formatted prompts for testing
system, user = manager.get_testing_prompt(
    context="Novel text context",
    question="What spell did Harry use?",
    choices="a) Expelliarmus\nb) Stupefy\nc) Protego\nd) Expecto Patronum"
)

# Load a custom template
manager.load_custom_template(
    "path/to/custom_template.json",
    template_type="question_generation"
)
```

## Tips for Effective Prompts

### For Question Generation

1. **Be Specific**: Clearly specify the output format (JSON) and required fields
2. **Provide Examples**: Include example output in the prompt to guide the LLM
3. **Set Constraints**: Explicitly state requirements (e.g., "at least 2 distractors")
4. **Request Validation**: Ask the LLM to ensure answers are valid choices
5. **Language Consistency**: Use the same language throughout (system, user, constraints)

### For Testing

1. **Clear Instructions**: Tell the LLM to base answers only on the provided text
2. **Format Requirements**: Explicitly request JSON format with specific structure
3. **Avoid Hallucination**: Instruct the model not to make up information
4. **Handle Edge Cases**: Provide guidance for ambiguous or unanswerable questions

## Troubleshooting Templates

### LLM Not Following Format

If the LLM doesn't output valid JSON:

1. Make the format requirements more explicit in the prompt
2. Add more examples of correct output
3. Try a different model that better follows instructions
4. Reduce temperature for more deterministic output

### Poor Question Quality

If generated questions are too easy or too hard:

1. Adjust the context window size
2. Modify the prompt to request specific difficulty levels
3. Add constraints about question complexity
4. Review and filter questions manually

### Wrong Language Output

If the LLM outputs in the wrong language:

1. Ensure system and user prompts are in the target language
2. Add explicit language requirements in constraints
3. Include language-specific examples
4. Use a model trained on the target language
