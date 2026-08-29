# CLAUDE.md

## Development Commands

```bash
pytest                        # Run all tests with coverage and mypy
pytest tests/test_file.py     # Run specific test file
pytest -k "test_name"         # Run specific test by name
ruff check .                  # Lint
ruff format .                 # Format
pre-commit run --all-files    # Run all pre-commit hooks
python src/main.py            # CLI entry point (argparse-based, supports agent selection)
streamlit run src/streamlit_app.py  # Streamlit UI
```

## Architecture

AI Agents for Notion — a multi-agent toolkit for job application workflows. Two pipelines:

1. **Metadata Extraction**: Extracts structured metadata from job descriptions via OpenAI, syncs to Notion
2. **Resume Tailoring**: Adapts master resume (.tex) per job description, compiles PDF, uploads to Notion

### Project Structure
```
src/
├── core/                    # Config (pydantic-settings) and logging (loguru)
├── common/
│   ├── models/              # Notion data models (NotionDatabase, NotionPage)
│   ├── schemas/             # OpenAI structured output schemas
│   ├── services/            # Shared services:
│   │   ├── notion_api_service.py    # Notion API CRUD
│   │   ├── notion_file_service.py   # File upload/download to Notion
│   │   ├── notion_sync_service.py   # Bidirectional Notion sync
│   │   └── openai_service.py        # OpenAI client with structured output
│   ├── exceptions/          # Custom exception types
│   └── utils.py             # File utilities
├── metadata_extraction/
│   ├── extractor_service.py # Orchestrates extraction pipeline
│   ├── models.py            # Extraction-specific models
│   └── schema_utils.py      # Notion DB schema -> OpenAI schema conversion
├── resume_tailoring/
│   ├── tailor_service.py    # Orchestrates tailoring pipeline
│   ├── latex_service.py     # LaTeX manipulation
│   ├── pdf_compiler.py      # pdflatex compilation
│   └── models.py            # Tailoring-specific models
├── main.py                  # CLI entry point (argparse)
└── streamlit_app.py         # Streamlit web UI
prompts/                     # LLM prompt templates
docs/                        # Project documentation
data/                        # Input data
out/                         # Generated output (PDFs, diffs)
```

### Data Flow
- Job data: Notion -> OpenAI extraction -> back to Notion
- Resume: Master .tex -> OpenAI tailoring -> pdflatex -> PDF -> Notion upload

## Environment Variables (see `.env.example`)
- `OPENAI_API_KEY`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `MASTER_RESUME_PATH`

## System Requirements
- pdflatex and latexdiff must be in PATH for resume tailoring pipeline
