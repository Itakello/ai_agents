# MVP Task Plan

This document outlines the granular tasks required to build the Minimum Viable Product (MVP) for the Job Finder Assistant. Tasks are designed to be small, independently testable, and build upon each other.

## 0. Foundational Setup

- - [x] **Task 0.1: Initialize `src/config.py` for Settings Management**
    - Create `src/config.py` using `pydantic-settings`.
    - Define `Settings` model to load API keys (OpenAI, Notion) and other configurations (e.g., master resume path, Notion database ID) from a `.env` file.
    - Include fields for `OPENAI_API_KEY`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `MASTER_RESUME_PATH`.
    - *Test:* Create a sample `.env` file. Instantiate `Settings` and verify that values are loaded correctly. Verify error handling for missing required environment variables.

- - [x] **Task 0.2: Create `src/common/utils.py`**
    - Implement basic file reading utility (e.g., `read_file_content(file_path: Path) -> str`).
    - Implement basic file writing utility (e.g., `write_file_content(file_path: Path, content: str)`).
    - *Test:* Write unit tests for reading from and writing to temporary files.

- - [x] **Task 0.3: Setup `src/common/llm_clients.py` with a Basic OpenAI Client**
    - Create `src/common/llm_clients.py`.
    - Implement an `OpenAIClient` class.
    - Constructor should take `api_key` (from `config.Settings`).
    - Implement a basic method to interact with a chat model (e.g., `get_chat_completion(prompt: str, model_name: str = "gpt-3.5-turbo") -> str`). This is a placeholder for more structured interaction later.
    - *Test:* Unit test with mocked OpenAI API call, verifying correct API key usage and basic prompt/response handling. Requires `OPENAI_API_KEY` in test environment or proper mocking.

- - [x] **Task 0.4: Setup `src/metadata_extraction/notion_service.py` (Basic Notion Client)**
    - Create `src/metadata_extraction/notion_service.py`.
    - Implement a `NotionService` class.
    - Constructor should take `api_key` and `database_id` (from `config.Settings`).
    - Implement a method to fetch a Notion page by its ID (e.g., `get_page_content(page_id: str) -> dict`).
    - Implement a method to update a specific property on a Notion page (e.g., `update_page_property(page_id: str, property_name: str, property_value: Any)`).
    - *Test:* Unit test with mocked `notion-client` calls, verifying correct API key, database ID usage, and basic page retrieval/update logic. Requires `NOTION_API_KEY` and a test `NOTION_DATABASE_ID` / `PAGE_ID` in test environment or proper mocking.

## 1. Feature: Job Metadata Extraction

- - [x] **Task 1.1-1.2: Complete Schema and Data Conversion System in `src/metadata_extraction/models.py`**
    - Create `src/metadata_extraction/models.py`.
    - Implement `notion_property_to_openai_schema()` to convert Notion property definitions to OpenAI JSON Schema format.
    - Implement `openai_data_to_notion_property()` to convert OpenAI response data to Notion property value format.
    - Implement `create_openai_schema_from_notion_database()` to create complete OpenAI schemas from Notion database properties.
    - Implement `convert_openai_response_to_notion_update()` to convert OpenAI responses to Notion page update format.
    - Support all required Notion property types: **url**, **status**, **select**, **email**, **date**, **number**, **multi_select**, plus rich_text, title, checkbox, phone_number, people, files.
    - Automatically filter read-only properties (created_time, formula, rollup, etc.).
    - Handle edge cases like empty values, missing options, and unknown property types.
    - *Test:* Comprehensive test coverage with 48 test cases covering all conversion scenarios and property types.

- - [x] **Task 1.3: Enhance `NotionService` to Fetch Database Schema and Update Multiple Properties**
    - Add method `get_database_schema(self) -> dict` to `src/metadata_extraction/notion_service.py`.
        - This method retrieves the schema (properties) of the configured Notion database using `notion-client`.
        - Return the properties dictionary from the database object.
    - Add method `update_page_properties(self, page_id: str, properties_update: dict[str, Any]) -> dict` to support bulk property updates.
        - This method updates multiple properties on a Notion page in a single API call.
        - Takes the properties_update dict in Notion's expected format (as returned by `convert_openai_response_to_notion_update()`).
        - Returns the updated page object.
    - *Test:* Unit tests with mocked `notion-client` calls for both database schema retrieval and bulk property updates.

- - [x] **Task 1.4: Implement Core Logic in `src/metadata_extraction/extractor_service.py`**
    - Create `src/metadata_extraction/extractor_service.py`.
    - Implement `ExtractorService` class.
    - Constructor takes `OpenAIClient` and `NotionService` instances.
    - Implement `extract_metadata_from_job_description(self, job_description_text: str, notion_database_schema: dict) -> dict[str, Any]`:
        - Uses `create_openai_schema_from_notion_database()` to convert Notion schema to OpenAI JSON Schema.
        - Constructs a comprehensive prompt for OpenAI, including the job description and the desired JSON schema for structured output.
        - Uses OpenAI's structured output feature (if available in `llm_clients.py`) or JSON mode to ensure valid responses.
        - Returns the raw JSON response from OpenAI (ready for conversion to Notion format).
    - *Test:* Unit test with mocked `OpenAIClient`. Provide sample job description text and Notion schema, mock LLM JSON response, and verify the returned data structure.

- - [x] **Task 1.5: Integrate Complete Metadata Extraction Pipeline**
    - Create `src/main_cli.py` if it doesn't exist.
    - Use `argparse` to create a command, e.g., `extract-metadata`.
    - Command takes a Notion Page ID (`--page-id`) and optional job description property name (`--job-desc-property`, defaults to "Job Description").
    - Logic:
        1. Initialize `Settings`, `OpenAIClient`, `NotionService`, `ExtractorService`.
        2. `NotionService`: Fetch database schema using `get_database_schema()`.
        3. `NotionService`: Fetch job description text from the specified property of the Notion page.
        4. `ExtractorService`: Extract metadata using `extract_metadata_from_job_description()`.
        5. Use `convert_openai_response_to_notion_update()` from models.py to convert the extracted data to Notion format.
        6. `NotionService`: Update the Notion page properties using `update_page_properties()`.
        7. Print confirmation with summary of extracted fields to console.
    - Include proper error handling for missing pages, empty job descriptions, API failures, etc.
    - *Test:* Manual end-to-end test with a real Notion page. Mock external calls for automated testing.

## 2. Feature: Resume Tailoring

- - [x] **Task 2.1: Define Pydantic Models for Tailored Resume in `src/resume_tailoring/models.py`**
    - Create `src/resume_tailoring/models.py`.
    - Define `TailoredResumeOutput` model: `tailored_tex_content: str`, `changes_summary: str`.
    - *Test:* Basic Pydantic model instantiation and validation tests.

- - [x] **Task 2.2: Implement `src/resume_tailoring/pdf_compiler.py`**
    - Create `src/resume_tailoring/pdf_compiler.py`.
    - Implement `PDFCompiler` class.
    - Implement `compile_tex_to_pdf(self, tex_file_path: Path, output_directory: Path) -> Path | None`:
        - Uses `subprocess.run` to execute `pdflatex`.
        - Command and arguments should be configurable, defaulting to sensible values (see memory for `pdflatex` config).
        - Handles placeholders like `%OUTDIR%` and `%DOC%`.
        - Checks for successful compilation (e.g., return code, existence of PDF file).
        - Returns path to the generated PDF or `None` on failure.
        - Ensure it handles multiple runs of `pdflatex` if necessary for references/citations (though likely not needed for typical resumes).
    - *Test:* Unit test: Create a minimal valid `.tex` file. Mock `subprocess.run`. Verify `pdflatex` is called with correct arguments and output path. Test with a `.tex` file that successfully compiles (requires `pdflatex` installed in test environment or more complex mocking of file system operations).

- - [x] **Task 2.3: Implement `src/resume_tailoring/latex_service.py`**
    - Create `src/resume_tailoring/latex_service.py`.
    - Implement `LatexService` class.
    - Constructor takes `PDFCompiler` instance and `Settings` (for output paths).
    - Method `save_tex_file(self, content: str, filename_stem: str, output_subdir: str = "tailored_resumes") -> Path`:
        - Saves `.tex` content to a file in a structured output directory (e.g., `output/tailored_resumes/<filename_stem>.tex`).
        - Uses `common.utils.write_file_content`.
    - Method `compile_resume(self, tex_file_path: Path) -> Path | None`:
        - Calls `PDFCompiler.compile_tex_to_pdf`.
    - Method `run_latexdiff(self, original_tex_path: Path, tailored_tex_path: Path, diff_output_stem: str, output_subdir: str = "resume_diffs") -> Path | None`:
        - Uses `subprocess.run` to execute `latexdiff`.
        - Saves the output `_diff.tex` file (e.g., `output/resume_diffs/<diff_output_stem>_diff.tex`).
        - Returns path to the `_diff.tex` file or `None` on failure.
    - *Test:* Unit tests: Mock `PDFCompiler` and `subprocess.run` for `latexdiff`. Test file saving logic. Test compilation calls. Test `latexdiff` command formation.

- - [ ] **Task 2.4: Enhance `NotionService` to Upload Files and Update Page with URL**
    - Add method `upload_file_to_page_property(self, page_id: str, property_name: str, file_path: Path) -> str | None` to `src/common/notion_service.py`.
        - This is tricky as Notion API doesn't directly support file uploads to page properties in the way one might expect for general files. It usually involves hosting the file elsewhere and linking the URL.
        - For MVP, this might mean: The method uploads the file to a pre-configured cloud storage (e.g., S3, not implemented in MVP) OR simply stores the *local file path* in the Notion property if direct upload is too complex for MVP.
        - **Decision for MVP:** Store the local file path in a Text or URL property in Notion. The user will be responsible for accessing it locally. A more robust solution is post-MVP.
        - So, this method will effectively be similar to `update_page_property` but specialized for file paths.
    - *Test:* Unit test with mocked `notion-client` call to update a page property with a file path string.

- - [ ] **Task 2.5: Implement Core Logic in `src/resume_tailoring/tailor_service.py`**
    - Create `src/resume_tailoring/tailor_service.py`.
    - Implement `TailorService` class.
    - Constructor takes `OpenAIClient`, `LatexService`, `NotionService`.
    - Implement `tailor_resume(self, job_description_text: str, job_metadata: dict, master_resume_tex_content: str, notion_page_id: str, output_filename_stem: str, generate_diff: bool = False) -> None`:
        1. Construct LLM prompt:
            - Input: job description, extracted job metadata, master resume `.tex` content.
            - Requirements:
                * Add job position at the top.
                * Add a 3-sentence summary at the top (who I am, why I’m applying, concise).
                * Make the tailored resume comprehensive, cohesive, and highlight best/most relevant skills/experiences/projects.
                * Keep the PDF length to 1 page (retry if not).
                * Only explain (in a summary) why it kept/updated/added content (not why it removed).
        2. Call `OpenAIClient` to get `TailoredResumeOutput` (tailored `.tex` and summary of changes).
        3. `LatexService`: Save the `tailored_tex_content` (e.g., `output/tailored_resumes/<output_filename_stem>.tex`).
        4. `LatexService`: Compile `tailored_tex_path` to PDF. Let's call this `tailored_pdf_path`.
        5. `NotionService`: Update Notion page (`notion_page_id`) with:
            - The summary of why content was kept/updated/added (e.g., to property "Resume Tailoring Summary").
            - The local path to `tailored_pdf_path` (e.g., to property "Tailored Resume").
        6. If `generate_diff`:
            a. `LatexService`: Run `latexdiff` between master resume (`Settings.MASTER_RESUME_PATH`) and `tailored_tex_path`. Get `diff_tex_path`.
            b. `LatexService`: Compile `diff_tex_path` to PDF. Get `diff_pdf_path`.
            c. `NotionService`: Update Notion page with local path to `diff_pdf_path` (e.g., to property "Tailored Resume Diff").
    - *Test:* Unit test with mocked `OpenAIClient`, `LatexService`, `NotionService`. Provide sample inputs, mock LLM response, and verify correct service calls and data flow.

- - [ ] **Task 2.6: Integrate Resume Tailoring into `main.py`**
    - Add a new command to `src/main.py`, e.g., `tailor-resume`.
    - Command takes Notion Page ID (`--page-id`), master resume path (`--master-resume` - can default to `Settings.MASTER_RESUME_PATH`), output filename stem (`--output-stem`), and an optional flag for diff (`--diff`).
    - Logic:
        1. Initialize `Settings`, `OpenAIClient`, `PDFCompiler`, `LatexService`, `NotionService`, `TailorService`.
        2. `NotionService`: Fetch job description text and job metadata from the Notion page.
        3. `common.utils.read_file_content`: Read master resume `.tex` content.
        4. `TailorService`: Call `tailor_resume`.
        5. Print confirmation to console.
    - *Test:* Manual end-to-end test: Setup Notion page, master resume. Run CLI. Verify tailored PDF (and diff PDF if requested) are generated in the output directory, and Notion page is updated with summary and file paths. Mock external calls for automated testing if feasible.

## 3. Feature: Hosted Service & Webhook Integration

- - [ ] **Task 3.1: Set Up Hosted Web Service (FastAPI)**
    - Create `src/web_service.py` (or similar).
    - Set up FastAPI app with endpoints for:
        - `/extract-metadata` (POST): Accepts Notion page URL/ID, triggers metadata extraction pipeline.
        - `/tailor-resume` (POST): Accepts Notion page URL/ID, triggers resume tailoring pipeline.
    - *Test:* Start server locally, hit endpoints with sample payloads, verify correct pipeline execution (mock external calls).

- - [ ] **Task 3.2: Implement Notion Webhook Handler**
    - Add endpoint `/notion-webhook` (POST): Handles webhook requests from Notion DB button.
    - Parse payload, extract Notion page ID, trigger full pipeline (metadata extraction + resume tailoring).
    - *Test:* Simulate webhook POST from Notion, verify pipeline runs and Notion DB is updated.

- - [ ] **Task 3.3: Automate Full Pipeline on Webhook Trigger**
    - On webhook, orchestrate:
        1. Fetch job description and metadata from Notion.
        2. Run metadata extraction (if not already done).
        3. Run resume tailoring (as above).
        4. Generate PDFs and update Notion DB properties.
    - *Test:* End-to-end test with mocked Notion and LLM calls.

- - [ ] **Task 3.4: Security and Configuration**
    - Secure webhook endpoints (e.g., secret token, IP allowlist).
    - Ensure API keys and secrets are loaded from environment/config.
    - *Test:* Attempt unauthorized requests, verify they are rejected.

- - [ ] **Task 3.5: Scalability and Batch Processing**
    - Support batch processing of multiple jobs (e.g., queue or async tasks).
    - *Test:* Trigger multiple webhooks/jobs, verify all are processed and Notion DB is updated.
