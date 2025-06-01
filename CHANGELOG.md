# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Removed

### Fixed

## [0.3.0] - 2025-06-01
### Added
- **TYPING_SETUP.md**: Comprehensive guide for modern Python typing best practices and enforcement
- **Enhanced Code Quality**: Pre-commit hooks with modern Python typing enforcement (Python 3.9+)
- **Type Safety Improvements**: Fixed deprecated typing imports and enhanced type annotations throughout codebase

### Changed
- **Code Formatting**: Improved code formatting and consistency across all modules
- **Type System**: Updated to use modern Python typing features with proper import paths
- **Development Workflow**: Enhanced pre-commit configuration with comprehensive type checking

### Fixed
- **Typing Issues**: Resolved deprecated typing imports (`typing.List` → `list`, `typing.Dict` → `dict`, etc.)
- **Code Style**: Fixed trailing whitespace and formatting inconsistencies throughout the project
- **Import Organization**: Cleaned up import statements for better organization and compliance

## [0.2.0] - 2025-06-01
### Added
- **Job Metadata Extraction System**: Complete metadata extraction functionality for job-related content
- **Notion Integration**: Full Notion API service with database operations, page creation, and property management
- **LLM Clients**: OpenAI client implementation for AI-powered metadata extraction
- **SQLite-based Caching System**: Local file-based caching for crawled web content with PDF export capabilities
- **Comprehensive Configuration**: Environment-based config with validation and type safety
- **Modern Python Typing**: Setup guide and enforcement for Python 3.9+ typing features
- **Schema Conversion**: Notion-to-OpenAI schema conversion with special directives support
- **Extractor Service**: Complete metadata extraction pipeline with retry logic and error handling
- **Prompt Templates**: Specialized prompts for web crawling and metadata extraction
- **Test Suite**: Unit tests covering core modules with fixtures and mocks

### Changed
- **Enhanced Project Structure**: Reorganized codebase with proper module separation
- **Improved Configuration Management**: Enhanced config loading with environment validation
- **Better Error Handling**: Robust error handling and logging throughout the application
- **Updated Dependencies**: Added required packages for Notion, OpenAI, and testing (managed via pyproject.toml)
- **Pre-commit Hooks**: Enhanced pre-commit configuration with modern Python typing enforcement
- **Code Quality**: Improved code formatting and linting with ruff and mypy integration

### Removed
- **Deprecated Notion Client**: Removed old notion_client.py in favor of comprehensive notion_service.py
- **Example Test File**: Removed generic example_test.py in favor of specific test modules

### Fixed
- **Typing Issues**: Fixed deprecated typing imports throughout the codebase
- **Code Formatting**: Fixed trailing whitespace and formatting inconsistencies
- **Test Coverage**: Improved test reliability and coverage across all modules

## [0.1.0] - 2025-06-01
### Added
- Initial project setup with basic Python project template structure
