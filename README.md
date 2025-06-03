# AI Agents - Job Metadata Extraction System

This repository provides a comprehensive AI-powered system for extracting, processing, and managing job-related metadata using advanced language models and Notion integration. Built with modern Python practices, it offers robust tools for automated content analysis and structured data extraction.

## Features

- **AI-Powered Metadata Extraction**: Advanced job content analysis using OpenAI models
- **Notion Integration**: Complete Notion API service with database operations and property management
- **SQLite-based Caching System**: Local file-based caching for crawled web content with PDF export capabilities
- **Schema Conversion**: Sophisticated Notion-to-OpenAI schema conversion with special directives
- **Configuration Management**: Environment-based configuration with validation and type safety
- **Modern Python Typing**: Comprehensive typing setup with pre-commit hooks for code quality
- **Unit Testing**: Test coverage for core modules with fixtures and mocks
- **Logging and Monitoring**: Structured logging with configurable levels and output formats
- **Code Quality**: Pre-commit hooks with Ruff, Black, and MyPy integration

## Metadata Extraction Module

The `src/metadata_extraction/models.py` module provides sophisticated utilities for converting between Notion database properties and OpenAI JSON schemas. This enables seamless integration between Notion databases and AI-powered structured data extraction.

### Key Features

- **Automatic Schema Conversion**: Convert Notion property definitions to OpenAI-compatible JSON schemas
- **Special Description Directives**: Control schema generation behavior using special commands in property descriptions
- **Bi-directional Data Conversion**: Convert data from OpenAI responses back to Notion property format
- **Smart Option Handling**: Intelligent handling of select/multi-select/status properties with example generation

### Property Description Rules

When configuring Notion database properties, you can use special directives in the property descriptions to control how they are handled during schema generation:

#### Available Directives

1. **`#exclude`** - Skip this property entirely in schema generation
   ```
   Description: "Internal tracking field #exclude"
   Result: Property will not appear in the generated OpenAI schema
   ```

2. **`#keep-options`** - Always include enum options for select/multi-select/status properties
   ```
   Description: "Project status #keep-options"
   Result: Will include enum values even if add_options=False
   ```

#### Property Type Handling

The module automatically handles various Notion property types:

- **Text Properties**: `rich_text`, `title` → `string`
- **Numeric Properties**: `number` → `number`
- **Boolean Properties**: `checkbox` → `boolean`
- **Selection Properties**: `select`, `multi_select`, `status` → `string` or `array` with optional enum constraints
- **Date Properties**: `date` → `string` with date format
- **Contact Properties**: `email`, `phone_number`, `url` → `string` with appropriate formats/patterns
- **Relation Properties**: `people`, `files` → `array` of strings

#### Read-Only Properties

The following Notion property types are automatically excluded as they are read-only:
- `created_time`, `created_by`, `last_edited_time`, `last_edited_by`
- `formula`, `rollup`

#### Example Generation

For select-type properties without enum options, the system automatically generates example descriptions:

```python
# Property with options but add_options=False
{
    "type": "select",
    "description": "Priority level",
    "select": {"options": [{"name": "High"}, {"name": "Medium"}, {"name": "Low"}]}
}

# Generated description: "Priority level | e.g. High, Medium, Low, ..."
```

### Usage Examples

#### Basic Schema Generation

```python
from src.metadata_extraction.models import create_openai_schema_from_notion_database

# Notion properties from database
notion_properties = {
    "title": {
        "type": "title",
        "description": "Task title"
    },
    "status": {
        "type": "select",
        "description": "Current status #keep-options",
        "select": {"options": [{"name": "Todo"}, {"name": "In Progress"}, {"name": "Done"}]}
    },
    "internal_id": {
        "type": "rich_text",
        "description": "Internal tracking #exclude"
    }
}

# Generate OpenAI schema
schema = create_openai_schema_from_notion_database(notion_properties, add_options=False)

# Result:
{
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Task title"},
        "status": {
            "type": "string",
            "description": "Current status #keep-options",
            "enum": ["Todo", "In Progress", "Done"]
        }
        # internal_id is excluded due to #exclude directive
    },
    "required": ["title", "status"],
    "additionalProperties": false
}
```

#### Data Conversion

```python
from src.metadata_extraction.models import convert_openai_response_to_notion_update

# OpenAI response data
openai_response = {
    "title": "Complete project documentation",
    "status": "In Progress"
}

# Convert to Notion update format
notion_update = convert_openai_response_to_notion_update(openai_response, notion_properties)

# Result ready for Notion API:
{
    "properties": {
        "title": {"rich_text": [{"text": {"content": "Complete project documentation"}}]},
        "status": {"select": {"name": "In Progress"}}
    }
}
```

### Testing

The module includes comprehensive tests covering:
- Individual property type conversions
- Special directive handling
- Schema generation edge cases
- Data conversion accuracy
- Error handling scenarios

Run the tests with:
```bash
pytest tests/metadata_models_test.py -v
```

## Project Structure

```
ai_agents/
├── .git/                     # Git repository files
├── .github/                  # (Optional) GitHub actions for CI/CD
├── .vscode/                  # (Optional) VSCode settings
├── design_docs/              # Architecture documentation and task planning
├── exported_pdfs/            # Sample PDFs for metadata extraction testing
├── prompts/                  # AI prompt templates for extraction and crawling
├── src/                      # Main source code
│   ├── common/               # Shared utilities and services
│   │   ├── __init__.py
│   │   ├── llm_clients.py    # OpenAI client integration
│   │   ├── notion_service.py # Complete Notion API client
│   │   └── utils.py          # Common utility functions
│   ├── core/                 # Core application logic and configuration
│   │   ├── __init__.py
│   │   ├── config.py         # Environment-based configuration management
│   │   └── logger.py         # Structured logging setup
│   ├── metadata_extraction/  # Metadata extraction system
│   │   ├── __init__.py
│   │   ├── cache.py          # SQLite-based caching with PDF export
│   │   ├── extractor_service.py # Main extraction service with retry logic
│   │   └── models.py         # Schema conversion and data models
│   ├── __init__.py
│   └── main.py               # Main application entry point
├── tests/                    # Unit and integration tests
│   ├── __init__.py
│   ├── config_test.py        # Configuration tests
│   ├── extractor_service_test.py # Extractor service tests
│   ├── llm_clients_test.py   # LLM client tests
│   ├── main_test.py          # Main module tests
│   ├── metadata_models_test.py # Metadata models tests
│   ├── notion_service_test.py # Notion service tests
│   └── utils_test.py         # Utility function tests
├── .env.example              # Example environment variables
├── .gitignore                # Specifies intentionally untracked files that Git should ignore
├── CHANGELOG.md              # Log of changes to the project
├── Dockerfile                # For building Docker container (placeholder)
├── LICENSE                   # Project license
├── README.md                 # This file
├── pyproject.toml            # Python project configuration (dependencies, tools, etc.)
└── TYPING_SETUP.md           # Modern Python typing setup guide
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/ai-agents.git
    cd ai-agents
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -e .
    ```

4.  **Set up environment variables:**
    Copy the example environment file and fill in your actual values:
    ```bash
    cp .env.example .env
    ```
    Then, edit `.env` with your project-specific settings (e.g., API keys, database URLs).
    **IMPORTANT:** Ensure `.env` is listed in your `.gitignore` file to prevent committing secrets.

## Running the Application

```bash
python src/main.py
```

## Running Tests

```bash
pytest
```

## Linting and Formatting

This project uses `pre-commit` with `black` for code formatting and `ruff` for linting and additional formatting.

**Setup (First time for a new developer):**

1.  Ensure you have installed development dependencies:
    ```bash
    pip install -e .[dev]
    ```
2.  Install the pre-commit hooks:
    ```bash
    python -m pre_commit install
    ```
    This will ensure that `black` and `ruff` run on changed files before each commit.

**Running manually:**

*   The hooks will run automatically on commit for staged files.
*   To manually run the checks on all files (e.g., after initial setup or when troubleshooting):
    ```bash
    python -m pre_commit run --all-files
    ```
*   If you want to run `ruff` checks directly (though pre-commit is recommended for consistency):
    To check for linting issues:
    ```bash
    ruff check .
    ```
    To automatically fix linting and formatting issues with ruff:
    ```bash
    ruff format .
    ruff check . --fix
    ```

## Contributing

(Add guidelines if you plan to collaborate or open-source the template/projects derived from it.)

## License

This project is licensed under the terms of the Apache Software License. See `LICENSE` file for details.
