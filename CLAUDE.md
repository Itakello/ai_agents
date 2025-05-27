# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
pytest                    # Run all tests with coverage and mypy
pytest tests/test_file.py # Run specific test file
pytest -k "test_name"     # Run specific test by name
```

### Code Quality
```bash
ruff check .              # Check for linting issues
ruff format .             # Format code
ruff check . --fix        # Auto-fix linting issues
pre-commit run --all-files # Run all pre-commit hooks
```

### Running the Application
```bash
python src/main.py        # Run the main application
```

### Dependencies
```bash
pip install -r requirements.txt -r requirements-dev.txt  # Install all dependencies
```

## Architecture Overview

This is a Python project template with a modular structure:

### Core Components
- **src/core/config.py**: Centralized configuration using Pydantic Settings with .env file support
- **src/core/logger.py**: Pre-configured Loguru logger with structured formatting
- **src/main.py**: Application entry point that demonstrates config and logging usage

### Configuration System
The project uses Pydantic Settings for configuration management:
- Environment variables loaded from `.env` file
- Settings defined with Field aliases for env var mapping
- Type validation and defaults handled by Pydantic
- Access via `from src.core.config import settings`

### Logging System
Loguru is configured with:
- Log level controlled by LOG_LEVEL environment variable
- Structured format with timestamps, levels, and source location
- Colorized output with backtrace and diagnostic info
- Import via `from src.core.logger import logger`

### Code Quality Setup
- Ruff for linting and formatting (line length: 120)
- pytest with coverage reporting and mypy integration
- pre-commit hooks for automated quality checks
- Target Python version: 3.13

## Project Structure
```
src/
├── core/           # Core utilities (config, logging)
├── main.py         # Application entry point
tests/              # Test files following pytest conventions
```

## Branching Strategy

This repository uses a protected branching model:

```
main (protected)
 ↑ (PR only from dev)
dev (protected)
 ↑ (PR only from feature branches)
feat/feature-name
docs/documentation-update
test/test-improvements
fix/bug-fix
```

### Workflow
1. **Start from dev**: `git checkout dev && git pull`
2. **Create feature branch**: `git checkout -b feat/my-feature` (or `docs/`, `test/`, `fix/`)
3. **Work and commit**: Make changes, commit frequently
4. **Push and PR to dev**: `git push -u origin feat/my-feature` → Create PR to `dev`
5. **After merge to dev**: Create PR from `dev` to `main`
6. **Deploy from main**: Production deployments only from `main` branch

### Branch Protection
- **main**: Requires PR approval, only accepts merges from `dev`
- **dev**: Requires PR approval, only accepts merges from feature branches
- Direct pushes to `main` and `dev` are blocked

## Environment Setup
Copy `.env.example` to `.env` and configure project-specific settings. The config system automatically loads these values with type validation.
