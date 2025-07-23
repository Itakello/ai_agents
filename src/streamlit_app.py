import asyncio
from collections.abc import Coroutine
from typing import Any, cast

import streamlit as st

from src.common.services.notion_sync_service import NotionSyncService
from src.common.services.openai_service import OpenAIService
from src.core.config import get_settings
from src.metadata_extraction.extractor_service import ExtractorService
from src.resume_tailoring.latex_service import LatexService
from src.resume_tailoring.pdf_compiler import PDFCompiler
from src.resume_tailoring.tailor_service import TailorService

# -----------------------------------------------------------------------------
# Helper utilities
# -----------------------------------------------------------------------------


def _run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Safely execute *coro* in whichever event-loop context we are in.

    • If no loop is running (typical for Streamlit) we simply ``asyncio.run``.
    • If a loop **is** running we spin up a *temporary* loop so we can block
      until the coroutine finishes without interfering with the existing one.
    """
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is None:
        return asyncio.run(coro)

    tmp_loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(tmp_loop)
        return tmp_loop.run_until_complete(coro)
    finally:
        tmp_loop.close()
        asyncio.set_event_loop(running_loop)


@st.cache_resource(show_spinner=False)
def _init_services() -> dict[str, Any]:
    """Initialise and cache long-lived service instances."""
    settings = get_settings()

    # Core clients/services
    openai_service = OpenAIService(api_key=settings.OPENAI_API_KEY)
    notion_service = NotionSyncService(database_id=settings.NOTION_DATABASE_ID)

    # Metadata extraction
    extractor_service = ExtractorService(openai_service=openai_service, notion_service=notion_service)

    # Resume tailoring helpers
    pdf_compiler = PDFCompiler()
    latex_service = LatexService(pdf_compiler=pdf_compiler, settings=settings)
    tailor_service = TailorService(
        openai_service=openai_service, latex_service=latex_service, notion_service=notion_service
    )

    return {
        "settings": settings,
        "openai": openai_service,
        "notion": notion_service,
        "extractor": extractor_service,
        "tailor": tailor_service,
    }


# -----------------------------------------------------------------------------
# Streamlit UI
# -----------------------------------------------------------------------------

st.set_page_config(page_title="Job Finder Assistant", layout="wide")

authenticated_services = _init_services()
settings = authenticated_services["settings"]
notion_service: NotionSyncService = authenticated_services["notion"]
extractor_service: ExtractorService = authenticated_services["extractor"]
tailor_service: TailorService = authenticated_services["tailor"]

st.title("🛠️ Job Finder Assistant – Quick Operations Console")

tab_extract, tab_tailor = st.tabs(["🔍 Extract Metadata", "🎯 Tailor Resume"])

# -----------------------------------------------------------------------------
# 1) Metadata extraction tab
# -----------------------------------------------------------------------------
with tab_extract:
    st.header("Extract job metadata and save to Notion")

    links_input = st.text_area("Job posting URLs (one per line)")
    add_options_checkbox = st.checkbox("Add options to select / multi-select properties when missing", value=True)
    model_name = st.text_input("OpenAI model", value=settings.DEFAULT_MODEL_NAME)

    if st.button("Extract & Save", type="primary"):
        links = [ln.strip() for ln in links_input.split("\n") if ln.strip()]
        if not links:
            st.warning("Please enter at least one URL.")
        else:
            # Fetch (cached) database schema once
            database_schema = _run_async(notion_service.get_database_schema())
            extractor_service.add_properties_options = add_options_checkbox

            progress_bar = st.progress(0, text="Starting extraction …")
            for idx, link in enumerate(links, start=1):
                try:
                    cast("Any", progress_bar.update)((idx - 1) / len(links), text=f"Processing {link} …")
                    metadata = extractor_service.extract_metadata_from_job_url(
                        link, database_schema, cast("str", model_name)
                    )
                    _run_async(
                        notion_service.save_or_update_extracted_data(settings.NOTION_DATABASE_ID, link, metadata)
                    )
                    st.success(f"✔️ Processed and saved: {link}")
                except Exception as e:  # noqa: BLE001 (broad but user-facing)
                    st.error(f"❌ Error processing {link}: {e}")
            cast("Any", progress_bar.update)(1.0, text="Done ✅")

# -----------------------------------------------------------------------------
# 2) Resume tailoring tab
# -----------------------------------------------------------------------------
with tab_tailor:
    st.header("Tailor resume for applied jobs")

    if "applied_pages" not in st.session_state and st.button("🔄 Load 'Applied' jobs"):
        try:
            # The 'Status' property in Notion is a dedicated *status* type, not a regular select.
            # Use the matching filter key accordingly.
            st.session_state.applied_pages = _run_async(
                notion_service.query_database(
                    settings.NOTION_DATABASE_ID,
                    filter={"property": "Status", "status": {"equals": "Applied"}},
                )
            )
        except Exception as e:  # noqa: BLE001 – surface to the user
            st.error(f"Failed to fetch pages: {e}")

    applied_pages = st.session_state.get("applied_pages", [])

    # Map for selectbox display ↔ page instance
    page_display_map = {}
    for page in applied_pages:
        try:
            # Prefer Job Title → Company Name for readability; fall back to page ID
            title_prop = page.properties.get("Job Title") or page.properties.get("Title")
            company_prop = page.properties.get("Company Name") or page.properties.get("Company")

            title_text = (
                "".join(rt.plain_text for rt in title_prop.title) if getattr(title_prop, "title", None) else "—"
            )
            company_text = (
                "".join(rt.plain_text for rt in company_prop.rich_text)
                if getattr(company_prop, "rich_text", None)
                else ""
            )
            display_str = f"{title_text} @ {company_text}".strip(" @") or page.id
        except Exception:  # Fallback if unexpected structure
            display_str = page.id
        page_display_map[display_str] = page

    selected_display = None
    if page_display_map:
        selected_display = st.selectbox(
            "Select a job page to tailor", options=list(page_display_map.keys()), key="selected_page"
        )
    else:
        st.info("No 'Applied' pages loaded. Click the refresh button above.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Tailor selected", disabled=selected_display is None):
            page = page_display_map[selected_display]
            try:
                st.write(f"Tailoring resume for page **{page.id}** …")

                master_resume_content = settings.MASTER_RESUME_PATH.read_text(encoding="utf-8")
                job_metadata = page.model_dump()

                result = tailor_service.tailor_resume(
                    job_metadata=job_metadata,
                    master_resume_tex_content=master_resume_content,
                    notion_page_id=page.id,
                )
                if asyncio.iscoroutine(result):
                    _run_async(result)
                st.success("Resume tailored and uploaded to Notion ✅")
            except Exception as e:  # noqa: BLE001
                st.error(f"Failed to tailor resume: {e}")

    with col2:
        if st.button("Tailor ALL", disabled=not page_display_map):
            for disp, page in page_display_map.items():
                try:
                    st.write(f"Tailoring for **{disp}** …")
                    master_resume_content = settings.MASTER_RESUME_PATH.read_text(encoding="utf-8")
                    job_metadata = page.model_dump()
                    res = tailor_service.tailor_resume(
                        job_metadata=job_metadata,
                        master_resume_tex_content=master_resume_content,
                        notion_page_id=page.id,
                    )
                    if asyncio.iscoroutine(res):
                        _run_async(res)
                    st.success(f"✔️ Done for {disp}")
                except Exception as e:  # noqa: BLE001
                    st.error(f"❌ Error tailoring {disp}: {e}")

    st.caption("PDFs and diffs are uploaded to the 'Resume' property of each page.")
