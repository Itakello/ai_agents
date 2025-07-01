# AI Agents – Notion-Integrated Automation Toolkit

A growing collection of command-line "agents" that plug directly into your Notion workspace.  Each agent automates a specific workflow – starting today with a **Resume Tailoring** agent and with many more to come.

---

## 🚀 Quick Start

```bash
# 1 Create env (Python 3.12) and activate
conda create -n ai-agents python=3.12 -y
conda activate ai-agents

# 2 Install project
pip install -e .

# 3 Configure secrets (OpenAI & Notion)
cp .env.example .env && $EDITOR .env

# 4 Initialise / repair the Notion DB
python src/main.py resume init

# 5 Extract metadata from a job ad
python src/main.py resume extract "https://careers.example.com/jobs/1234"

# 6 Generate a laser-focused PDF resume (uses the metadata now stored in Notion, *not* the raw job ad)
python src/main.py resume tailor "https://careers.example.com/jobs/1234"
```

> **Customize** – tweak `data/template.tex` and/or add new properties to the Notion DB. The agent will pick them up automatically.

---

## 🤖 Available Agents

<details open>
<summary><strong>Resume Tailoring Agent</strong> (currently the only agent)</summary>

| Command | Description |
|---------|-------------|
| `resume init` | Verifies **and fixes** the configured Notion database schema. Run this once or after you modify the DB. |
| `resume extract <job_url>` | Scrapes & analyses the job posting, producing structured metadata and saving it to Notion. |
| `resume tailor <job_url>` | Creates a PDF resume tailored to the job (based on `template.tex`) and uploads it to Notion. |

The Resume Tailoring agent exposes three sub-commands:

* **init** – verifies (and automatically repairs) your Notion database schema. Run this once (or any time you change the DB).
* **extract &lt;job_url&gt;** – scrapes & analyses a job posting, then saves rich, structured metadata back to Notion.
* **tailor &lt;job_url&gt;** – renders `data/template.tex` into a PDF resume **solely using the metadata stored in Notion**. (The richer the metadata – e.g. "Key Achievements", "Core Competencies", "Tech Stack" – the better the tailoring quality.)

Run any of the above with:

```bash
python src/main.py resume <command> [...]
```

</details>

Future agents (e.g. *Job-Application Tracker*, *Content Planner*, …) will be added under their own top-level command (`python src/main.py <agent> <command>`).

---

## 📝 Property Description Directives

When you create properties in your Notion database you can add special tags in the *description* field to control how they're treated by the agents:

* `#exclude` – exclude the property from the AI JSON schema (useful for internal fields like status flags, URLs, etc.).
* `#keep-options` – for `select` / `multi_select` / `status` types, always include the option list as an enum even when `--add-properties-options` is false.

> **Tip:** Add additional context-rich properties (e.g. *Key Achievements*, *Core Competencies*, *Mission Statement*) to your Notion page. The more context the LLM has, the better it can tailor your resume.

---

## ✨ Features

<details>
<summary>Click to view full list</summary>

* AI-powered metadata extraction (GPT-4o-mini by default)
* Seamless Notion API integration (schema validation, file uploads, property mapping)
* LaTeX ➜ PDF compilation pipeline with automatic Notion upload
* Rich-style logging & Pydantic configuration
* 100 % typed codebase with Ruff, Black and MyPy pre-commit hooks
* Extensive unit-test suite & fixtures

</details>

---

## 🗂️ Key Project Structure

```
ai_agents/
├─ data/                 # LaTeX template & prompt files
├─ src/
│  ├─ common/            # Shared services (Notion, OpenAI, …)
│  ├─ metadata_extraction/  # Job-posting analysis
│  ├─ resume_tailoring/     # LaTeX rendering & PDF compiler
│  └─ main.py            # CLI entry-point (python src/main.py ...)
└─ tests/                # Pytest suite
```

See `design_docs/` for deep-dive architecture notes.

---

## 🛠️ Development

```bash
# 0 (one-time) install *dev* extras and pre-commit hooks
pip install -e .[dev]
pre-commit install

# 1 Run the full test + lint stack
pytest -v
ruff format .    # auto-format all files
ruff check .     # lint
mypy src tests   # static type checks

# 2 Run pre-commit on all files (optional but handy)
pre-commit run --all-files
```

---

## 📄 License

Apache 2.0 – see `LICENSE` for details.
