# Python Project Template

This repository provides a robust starting point for various Python projects. It includes a common structure, development tools, and best practices to kickstart your development.

## Features

- Basic project structure.
- Configuration management using `.env` files.
- Logging setup.
- `Dockerfile` for easy containerization and deployment.
- Linting and formatting with Ruff.
- Testing with Pytest.
- **Metadata Extraction**: Advanced Notion-to-OpenAI schema conversion with special directives

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
python-project-template/
├── .git/                     # Git repository files
├── .github/                  # (Optional) GitHub actions for CI/CD
├── .vscode/                  # (Optional) VSCode settings
├── config/                   # (Optional) Static configuration files if not using .env solely
├── data/                     # (Optional) For local data storage, ensure it's in .gitignore if sensitive
├── docs/                     # (Optional) Project documentation
├── logs/                     # (Optional) For log files, ensure it's in .gitignore
├── scripts/                  # Utility scripts (e.g., deployment, data migration)
├── src/                      # Main source code
│   ├── core/                 # Core application logic, configuration loading
│   │   ├── __init__.py
│   │   └── config.py         # Loads environment variables
│   ├── metadata_extraction/  # Metadata extraction utilities
│   │   ├── __init__.py
│   │   └── models.py         # Schema conversion and extraction logic
│   ├── __init__.py
│   └── main.py               # Main application entry point
├── tests/                    # Unit and integration tests
│   ├── __init__.py
│   └── metadata_models_test.py # Tests for metadata extraction models
├── .env.example              # Example environment variables
├── .gitignore                # Specifies intentionally untracked files that Git should ignore
├── CHANGELOG.md              # Log of changes to the project
├── Dockerfile                # For building Docker container
├── LICENSE                   # Project license
├── README.md                 # This file
├── requirements-dev.txt      # Development dependencies (testing, linting)
├── requirements.txt          # Project dependencies
└── pyproject.toml            # Python project configuration (for Ruff, pytest, etc.)
```

## Setup and Installation

1.  **Clone the repository (or use it as a template on GitHub):**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt -r requirements-dev.txt
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

(Add more specific run instructions as the application develops, e.g., command-line arguments if any)

## Running Tests

```bash
pytest
```

## Linting and Formatting

This project uses `pre-commit` with `black` for code formatting and `ruff` for linting and additional formatting.

**Setup (First time for a new developer):**

1.  Ensure you have installed development dependencies:
    ```bash
    pip install -r requirements-dev.txt
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

## Building and Running with Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t your-project-name .
    ```

2.  **Run the Docker container:**
    Make sure to pass your `.env` file to the container if it contains necessary runtime configurations.
    ```bash
    docker run --env-file .env -p 8000:8000 your-project-name
    # Adjust port mapping as needed
    ```

## Contributing

(Add guidelines if you plan to collaborate or open-source the template/projects derived from it.)

## License

This project is licensed under the terms of the Apache Software License. See `LICENSE` file for details.
