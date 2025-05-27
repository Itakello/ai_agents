# Job Finder Assistant - Architecture

## 1. Project Vision & Goals

The Job Finder Assistant aims to streamline the initial phases of job application by automating two key processes:

1.  **Job Metadata Extraction:**
    *   Extract structured metadata (e.g., `is_remote`, `job_title`, `company_name`, `required_skills`, `salary_range`) from job descriptions obtained from various sources like LinkedIn and other job portals.
    *   Utilize OpenAI's `gpt-4.1` model (or a similar specified model identifier supporting the Responses API) for extraction. This model is expected to support structured outputs and an integrated web search tool via its Responses API, allowing for direct information retrieval from URLs and avoiding manual web scraping.
    *   Dynamically derive the extraction schema (field names, types, descriptions) from a user-configured Notion database, allowing for easy modifications and additions to the metadata fields.
    *   Future iteration: Integrate the user's master resume (PDF) as context to provide personalized insights related to the job (e.g., `strength_match`, `fit_score`, `recommend_apply`).
    *   Future iteration: Allow users to provide additional instructions/preferences for enhanced contextual understanding.

2.  **Resume Tailoring:**
    *   Adapt a user's master resume (provided in `.tex` format) to a specific job description.
    *   The goal is to produce a concise, targeted, 1-page resume by selectively removing less relevant content, rewriting or merging sentences for impact, and incorporating keywords from the job description.
    *   The tailored resume must maintain the structural integrity and coherence of the master resume, adhering to readability principles like the F-shape pattern (prioritizing key information top-left).
    *   Utilize the OpenAI `gpt-4.1` model for this task.
    *   The LLM output will include the tailored `.tex` file and a textual description of the changes made, along with their motivation.
    *   The user has an existing process to generate a `latexdiff` and PDF from the original and tailored `.tex` files. This process will be integrated into the application.
    *   The final tailored resume (as a PDF) will be uploaded to the corresponding job entry in Notion.
    *   Future iteration: Allow for iterative refinement of the tailored resume based on user feedback and additional instructions.

**Overall Goal:** To create an efficient, OpenAI LLM-powered assistant that helps users quickly assess job opportunities and prepare tailored application materials, starting with metadata extraction and resume customization.

## 2. Core Architectural Style

A **Modular Pipeline Architecture** will be adopted. This involves a series of distinct processing stages (modules) that can be invoked sequentially or independently. This style suits the project's nature, where job data flows through different transformation steps.

*   **Backend Focus:** The system will be primarily a Python-based backend application, initially operated via a Command Line Interface (CLI).
*   **Modularity:** Key functionalities (Notion integration, LLM interaction, metadata extraction, resume tailoring) will be encapsulated in separate modules to promote separation of concerns, testability, and maintainability.

## 3. Python-Specific Considerations

*   **Python Version:** Python 3.10+ (leveraging modern type hinting and features).
*   **Key Libraries & Frameworks:**
    *   **LLM SDKs:** `openai` for GPT models (specifically interacting with the Responses API for models like `gpt-4.1`).
    *   **Notion Integration:** `notion-client` for interacting with the Notion API.
    *   **Data Validation & Settings:** `pydantic` for defining data models (LLM inputs/outputs, configuration) and `pydantic-settings` for managing application configuration (API keys, etc.).
    *   **HTTP Requests:** `httpx` (async-capable) for any direct API calls if SDKs are insufficient or for web scraping (future).
    *   **File Handling:** `pathlib` for robust path manipulation.
    *   **CLI:** `argparse` for building the command-line interface.
    *   **LaTeX Processing:** Integrated into the application for generating PDFs from `.tex` files. This will rely on external command-line tools like `pdflatex` (and potentially `latexdiff` if diff generation is implemented) being available in the system's PATH.

## 4. Detailed `src/` Directory Structure

```plaintext
job_finder_assistant/
├── .env                  # Local environment variables (API keys, Notion IDs) - Gitignored
├── .env.example          # Example environment file
├── design_docs/
│   ├── architecture.md     # This file
│   └── tasks.md            # Detailed MVP tasks (to be created)
├── src/
│   ├── __init__.py
│   ├── config.py           # Application configuration (Pydantic Settings)
│   ├── common/
│   │   ├── __init__.py
│   │   ├── llm_clients.py  # Wrapper client for OpenAI LLM (Responses API)
│   │   ├── models.py       # Common Pydantic models (e.g., LLM responses)
│   │   └── utils.py        # General utility functions
│   ├── metadata_extraction/
│   │   ├── __init__.py
│   │   ├── notion_service.py # Handles Notion DB reads (schema, job data) & writes
│   │   ├── schema_converter.py # Converts Notion schema to JSON Schema for LLMs
│   │   ├── extractor_service.py # Orchestrates metadata extraction using LLMs
│   │   └── models.py         # Pydantic models for job metadata & personalized insights
│   ├── resume_tailoring/
│   │   ├── __init__.py
│   │   ├── latex_service.py  # Handles .tex file I/O and PDF compilation/upload
│   │   ├── pdf_compiler.py   # Compiles .tex files into PDF documents
│   │   ├── tailor_service.py # Orchestrates resume tailoring using LLMs
│   │   └── models.py         # Pydantic models for tailored resume output (tex, changes)
│   └── main_cli.py           # Main CLI entry point (using Argparse)
├── tests/
│   ├── __init__.py
│   ├── fixtures/             # Sample data for tests (job descriptions, tex files)
│   ├── common/
│   ├── metadata_extraction/
│   └── resume_tailoring/
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```

## 5. Component Breakdown & Responsibilities (within `src/`)

*   **`src/config.py`:**
    *   Manages all application settings, including API keys (OpenAI, Notion), Notion database/page IDs, LLM model names.
    *   Uses `pydantic-settings` to load configuration from environment variables and/or `.env` files.

*   **`src/common/llm_clients.py`:**
    *   Provides an abstracted client class/function for interacting with the OpenAI LLM (e.g., `gpt-4.1` via the Responses API).
    *   Handles API request construction (including enabling web search tools and requesting structured JSON output), authentication, response parsing, and error handling for the OpenAI API.
    *   Supports structured output requests based on JSON schemas.

*   **`src/common/models.py`:**
    *   Contains shared Pydantic models, e.g., a generic structure for LLM responses if applicable across modules.

*   **`src/common/utils.py`:**
    *   Houses general utility functions used across different modules (e.g., file reading/writing helpers, text cleaning).

*   **`src/metadata_extraction/notion_service.py`:**
    *   Interacts with the Notion API via `notion-client`.
    *   Responsibilities: fetching job description data from a Notion page, retrieving the metadata schema definition from the Notion database properties, and writing extracted metadata back to the relevant Notion page fields.

*   **`src/metadata_extraction/schema_converter.py`:**
    *   Takes the schema definition (field names, types, descriptions) retrieved from Notion by `notion_service.py`.
    *   Converts this into a JSON Schema object that can be passed to LLMs to guide structured output generation.

*   **`src/metadata_extraction/extractor_service.py`:**
    *   Orchestrates the metadata extraction process.
    *   Takes a job description (and later, resume context/user instructions).
    *   Uses `schema_converter.py` to get the JSON schema.
    *   Calls `llm_clients.py` to send requests to the OpenAI model with the job description, schema, and instructions to use web search if needed.
    *   Processes LLM responses and prepares data for `notion_service.py` to write back.

*   **`src/metadata_extraction/models.py`:**
    *   Defines Pydantic models for representing the structured job metadata (e.g., `JobMetadataOpenAI`) and any personalized insights.

*   **`src/resume_tailoring/pdf_compiler.py`:**
    *   Responsible for compiling `.tex` files (both tailored resumes and potentially diff files) into PDF documents. This will be achieved by invoking a LaTeX distribution's command-line tool (e.g., `pdflatex`) as a subprocess.
    *   Handles any necessary error checking, management of auxiliary files related to LaTeX compilation, and ensures the output PDF is placed in an expected location for further processing or upload.

*   **`src/resume_tailoring/latex_service.py`:**
    *   Handles reading the master `.tex` resume file.
    *   Saves the tailored `.tex` content received from `tailor_service.py` to a new file (e.g., `master_tailored.tex`).
    *   **Optional `latexdiff` Generation:** Based on analysis of the user's `Itakello/resume` repository (which uses a `create-diff.sh` script), this service can optionally generate a `diff.tex` file by invoking the `latexdiff` command-line tool. This would compare the original master resume with the LLM-tailored `.tex` file.
    *   Orchestrates the compilation of the tailored `.tex` file (and the `diff.tex` file, if generated) into PDF documents via `pdf_compiler.py`.
    *   Coordinates with `notion_service.py` to upload the generated PDF(s) (tailored resume PDF, and optionally the diff PDF) to the corresponding job entry in Notion and store their URL(s).

*   **`src/resume_tailoring/tailor_service.py`:**
    *   Orchestrates the resume tailoring process.
    *   Inputs: job description text, master resume (`.tex` content from `latex_service.py`), and optionally, extracted metadata.
    *   Constructs appropriate prompts for the OpenAI LLM.
    *   Uses `llm_clients.py` to send requests to the OpenAI model.
    *   Receives tailored `.tex` content and a description of changes/motivations from the LLM.
    *   Passes the tailored `.tex` to `latex_service.py` for saving and PDF compilation/upload.

*   **`src/resume_tailoring/models.py`:**
    *   Defines Pydantic models for the output from the resume tailoring LLMs (e.g., `TailoredResumeOutput` containing `tex_content: str`, `changes_summary: str`).

*   **`src/main_cli.py`:**
    *   Provides the command-line interface for the application using `argparse`.
    *   Allows users to trigger:
        *   Metadata extraction for a given Notion job entry/URL.
        *   Resume tailoring for a given job description and master resume.
    *   Orchestrates the calls to the respective services (`extractor_service.py`, `tailor_service.py`).

## 6. Data Model (Conceptual)

*   **Notion Database (Job Tracking):** Each row represents a job application.
    *   Properties (Columns):
        *   `JobID` (Unique ID, e.g., Notion Page ID)
        *   `Job Title` (Text, manual or from extraction)
        *   `Company` (Text, manual or from extraction)
        *   `Job Posting URL` (URL)
        *   `Job Description` (Text, pasted or scraped)
        *   `Status` (Select: e.g., "To Process", "Metadata Extracted", "Resume Tailored", "Applied")
        *   `Master Resume Used` (Text/Relation, path or ID of the master resume version)
        *   `Additional Instructions` (Text, for tailoring or metadata stage)
        *   **(Dynamic Metadata Fields):** These are defined by the user directly as properties in the Notion database. `notion_service.py` reads these property names, types, and descriptions to build the schema. Examples:
            *   `Is Remote` (Checkbox/Boolean)
            *   `Location` (Text)
            *   `Key Skills Required` (Multi-select/Text)
            *   `Salary Estimate` (Text)
        *   `Extracted Metadata (OpenAI)` (Text/JSON - stores the structured output)
        *   `Tailored Resume PDF URL` (URL - Link to the PDF file uploaded to the Notion page/block associated with the job entry)
        *   `Resume Raw Changes (OpenAI)` (Text - LLM-generated summary of changes to the resume)
        *   `Resume Tailored .tex (Local Path)` (Text - Path to the locally saved tailored .tex file, for reference or debugging)
        *   *(Future Personalized Insights Fields)*
            *   `Strength Match (OpenAI)` (Text)
            *   `Fit Score (OpenAI)` (Number)

*   **File System Data:**
    *   Master Resume: User-provided `.tex` file (e.g., `master_resume.tex`), path provided to the application.
    *   Tailored Resumes (.tex): Generated `.tex` files, named systematically (e.g., `jobID_company_openai_tailored.tex`), stored locally, at least temporarily.
    *   Tailored Resumes (.pdf): Generated PDF files from the tailored `.tex` files. These are uploaded to Notion. Local copies might be kept temporarily or for archival/debugging purposes.

## 7. Authentication and Authorization Strategy

*   **External APIs:** API keys for OpenAI and Notion will be managed via environment variables.
    *   The `config.py` module (using `pydantic-settings`) will load these keys from a `.env` file (which is gitignored) or directly from the environment.
*   **User Access:** As a local CLI tool, no user authentication/authorization within the application itself is required for the MVP.

## 8. State Management & Service Interaction

*   **State:** The primary state of job applications and their processed data will reside in the Notion database. Temporary state during processing (e.g., job description text, resume content) will be passed as data objects (Pydantic models) between services/functions.
*   **Interaction Flow (Metadata Extraction Example):**
    1.  `main_cli.py` receives command to process a job (e.g., by Notion Page URL).
    2.  Calls `notion_service.py` to fetch job description and metadata schema.
    3.  Calls `schema_converter.py` to transform Notion schema to JSON Schema.
    4.  Calls `extractor_service.py` with text and JSON Schema.
    5.  `extractor_service.py` calls `llm_clients.py` (OpenAI).
    6.  LLM responses are processed by `extractor_service.py`.
    7.  `extractor_service.py` calls `notion_service.py` to write results back to Notion.

*   **Interaction Flow (Resume Tailoring Example):**
    1.  `main_cli.py` receives command to tailor a resume for a specific job (e.g., by Notion Page URL and path to master resume). It may also take a flag to indicate if a diff PDF should be generated.
    2.  `main_cli.py` (or a coordinating service) fetches job description details using `notion_service.py`.
    3.  `latex_service.py` reads the master `.tex` resume file.
    4.  `tailor_service.py` (invoking `llm_clients.py`) uses the job description and master resume content to generate tailored `.tex` content and a summary of changes. This tailored content is saved by `latex_service.py` (e.g., as `master_tailored.tex`).
    5.  **Optional `latexdiff` Step:** If requested, `latex_service.py` invokes the `latexdiff` tool, comparing the original `master.tex` with `master_tailored.tex` to produce `master_diff.tex`.
    6.  `latex_service.py` invokes `pdf_compiler.py` to compile `master_tailored.tex` into `master_tailored.pdf`.
    7.  **Optional `diff.pdf` Compilation:** If `master_diff.tex` was generated, `latex_service.py` invokes `pdf_compiler.py` again to compile it into `master_diff.pdf`.
    8.  `latex_service.py` coordinates with `notion_service.py` to:
        a.  Upload the generated `master_tailored.pdf` (and `master_diff.pdf` if created) to the Notion page associated with the job entry.
        b.  Update the Notion job entry with the URL(s) of the uploaded PDF(s) and the summary of changes.

## 9. Testing Strategy

*   **Framework:** `pytest` will be used for writing and running tests.
*   **Unit Tests:** Each module and critical function will have unit tests.
    *   Mocking external services (Notion API, LLM APIs) using `unittest.mock` or `pytest-mock`.
    *   Testing `schema_converter.py` with various Notion schema examples.
    *   Testing Pydantic model validation.
    *   Testing helper functions in `utils.py`.
*   **Integration Tests:** Test the end-to-end flows for:
    *   Metadata extraction pipeline (from fetching Notion data to writing back results, with mocked external calls).
    *   Resume tailoring pipeline (from reading master resume to saving tailored resume, with mocked LLM calls).
*   **Fixtures:** `tests/fixtures/` will store sample job descriptions (text files), example Notion API responses (JSON files), and sample master `.tex` files.
*   **Coverage:** Aim for high test coverage, tracked using tools like `coverage.py`.

## 10. Deployment Considerations (High-Level)

*   **MVP:** The application will be run as a local CLI tool directly from the source code.
*   **Dependencies:** Managed via `pyproject.toml` and `requirements.txt`. Users will need to set up a Python environment and install dependencies.
*   **Configuration:** Users will need to provide their API keys in a `.env` file.
*   **Future:** If a UI or web service is developed:
    *   **Containerization:** Docker could be used to package the application and its dependencies for easier deployment.
    *   **API Exposure:** FastAPI could be used to expose endpoints if it evolves into a web service.

## 11. Future Considerations

*   **Web Scraping:** Robustly extracting job description text directly from URLs if not manually provided.
*   **Advanced Resume Diff/Merge:** Interactive UI for reviewing and accepting/rejecting specific changes in the tailored resume, potentially beyond simple `latexdiff`.
*   **Iterative Feedback Loop:** Allowing users to provide feedback on a tailored resume and have the LLM refine it further.
*   **Expanded Features:** Job search aggregation, cover letter generation, interview preparation assistance.
*   **User Interface:** A simple UI (e.g., Streamlit, Gradio) for easier interaction than CLI.
*   **Error Handling & Resilience:** More sophisticated error handling, retries for API calls, rate limit management.
*   **Caching:** Caching LLM responses for identical inputs to reduce costs and improve speed.
*   **Performance:** Optimizing long-running processes, especially LLM interactions.
*   **Security:** Securely managing API keys and user data, especially if deployed as a web service.
