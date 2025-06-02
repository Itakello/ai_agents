"""
URL content caching using SQLite for storing crawled markdown content.

This module provides functionality to cache crawled webpage content to avoid
re-fetching the same job_ids repeatedly.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pypandoc  # type: ignore

from ..core.config import get_settings


class JobCache:
    """SQLite-based cache for storing crawled job_id content."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the JobCache with a SQLite database.

        Args:
            cache_dir: Directory to store the cache database file. If None, uses configured cache directory.
        """
        if cache_dir is None:
            settings = get_settings()
            cache_dir = settings.CACHE_DIRECTORY

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "url_cache.db"
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database and create the cache table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS url_cache (
                    job_id TEXT PRIMARY KEY,
                    markdown_content TEXT NOT NULL,
                    crawled_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get_cached_content(self, job_id: str) -> str | None:
        """Retrieve cached markdown content for a job_id.

        Args:
            job_id: The job ID to look up in the cache.

        Returns:
            The cached markdown content if found, None otherwise.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT markdown_content FROM url_cache WHERE job_id = ?", (job_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def cache_content(self, job_id: str, markdown_content: str) -> None:
        """Store markdown content in the cache for a job_id.

        Args:
            job_id: The job ID that was crawled.
            markdown_content: The markdown content to cache.
        """
        crawled_at = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            # Use INSERT OR REPLACE to update existing entries
            conn.execute(
                """
                INSERT OR REPLACE INTO url_cache
                (job_id, markdown_content, crawled_at)
                VALUES (?, ?, ?)
            """,
                (job_id, markdown_content, crawled_at),
            )
            conn.commit()

    def export_to_pdf(self, job_id: str, output_dir: Path) -> Path:
        """Export cached markdown content for a job_id to PDF format using pandoc.

        Args:
            job_id: The job ID whose cached content to export.
            output_dir: Directory to save the PDF file.

        Returns:
            Path to the generated PDF file.

        Raises:
            ValueError: If the job_id is not found in cache.
            RuntimeError: If pandoc conversion fails.
        """
        markdown_content = self.get_cached_content(job_id)
        if not markdown_content:
            raise ValueError(f"job_id not found in cache: {job_id}")

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate a safe filename from the job_id
        safe_filename = f"job_{job_id[:8]}.pdf"
        output_path = output_dir / safe_filename

        # Add header with job_id and export timestamp
        enhanced_markdown = f"# Job Description\n\n**Job ID:** {job_id}\n**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n{markdown_content}\n\n---"

        settings = get_settings()

        font_args = [
            "--variable",
            f"mainfont={settings.PDF_MAIN_FONT}",
            "--variable",
            f"sansfont={settings.PDF_SANS_FONT}",
            "--variable",
            f"monofont={settings.PDF_MONO_FONT}",
        ]
        base_args = [
            "--variable",
            f"geometry:margin={settings.PDF_MARGIN}",
            "--variable",
            f"fontsize={settings.PDF_FONT_SIZE}",
            "--variable",
            f"linestretch={settings.PDF_LINE_STRETCH}",
        ]
        try:
            # Try primary PDF engine first
            pypandoc.convert_text(
                enhanced_markdown,
                "pdf",
                format="md",
                outputfile=str(output_path),
                extra_args=[f"--pdf-engine={settings.PDF_ENGINE_PRIMARY}"] + base_args + font_args,
            )
        except Exception as primary_err:
            try:
                # Fallback to secondary PDF engine if primary fails
                pypandoc.convert_text(
                    enhanced_markdown,
                    "pdf",
                    format="md",
                    outputfile=str(output_path),
                    extra_args=[f"--pdf-engine={settings.PDF_ENGINE_FALLBACK}"] + base_args + font_args,
                )
            except Exception as fallback_err:
                raise RuntimeError(
                    f"Failed to convert markdown to PDF. {settings.PDF_ENGINE_PRIMARY} error: {primary_err}\n"
                    f"{settings.PDF_ENGINE_FALLBACK} error: {fallback_err}\n"
                    f"Ensure {settings.PDF_MAIN_FONT} is installed and available to your TeX system."
                )

        return output_path

    def clear_cache(self) -> None:
        """Clear all cached content."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM url_cache")
            conn.commit()

    def get_cache_stats(self) -> dict[str, int]:
        """Get statistics about the cache.

        Returns:
            Dictionary with cache statistics.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM url_cache")
            total_entries = cursor.fetchone()[0]

            cursor = conn.execute("SELECT SUM(LENGTH(markdown_content)) FROM url_cache")
            total_size = cursor.fetchone()[0] or 0

        return {"total_entries": total_entries, "total_size_bytes": total_size}

    def list_cached_job_ids(self) -> list[dict[str, str]]:
        """List all cached job_ids with their metadata.

        Returns:
            List of dictionaries containing job_id information.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT job_id, crawled_at, LENGTH(markdown_content) as content_size
                FROM url_cache
                ORDER BY crawled_at DESC
            """)
            results = cursor.fetchall()

        return [{"job_id": row[0], "crawled_at": row[1], "content_size": row[2]} for row in results]

    def export_all_to_pdf(self, output_dir: Path) -> list[Path]:
        """Export all cached content to PDF files.

        Args:
            output_dir: Directory to save the PDF files.

        Returns:
            List of paths to generated PDF files.
        """
        cached_jobs = self.list_cached_job_ids()
        exported_files = []

        for job_info in cached_jobs:
            try:
                pdf_path = self.export_to_pdf(job_info["job_id"], output_dir)
                exported_files.append(pdf_path)
            except Exception as e:
                # Log error but continue with other job_ids
                print(f"Error exporting {job_info['job_id']}: {e}")

        return exported_files
