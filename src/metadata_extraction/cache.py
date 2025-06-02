"""
URL content caching using SQLite for storing crawled markdown content.

This module provides functionality to cache crawled webpage content to avoid
re-fetching the same URLs repeatedly.
"""

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pypandoc  # type: ignore

from ..core.config import get_settings


class URLCache:
    """SQLite-based cache for storing crawled URL content."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the URLCache with a SQLite database.

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
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    job_id TEXT,
                    markdown_content TEXT NOT NULL,
                    crawled_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create index on url for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON url_cache(url)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_id ON url_cache(job_id)")
            conn.commit()

    def _get_url_hash(self, url: str) -> str:
        """Generate a hash for the URL to use as a unique identifier.

        Args:
            url: The URL to hash.

        Returns:
            SHA256 hash of the URL.
        """
        return hashlib.sha256(url.encode()).hexdigest()

    def get_cached_content(self, url: str) -> str | None:
        """Retrieve cached markdown content for a URL.

        Args:
            url: The URL to look up in the cache.

        Returns:
            The cached markdown content if found, None otherwise.
        """
        url_hash = self._get_url_hash(url)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT markdown_content FROM url_cache WHERE url_hash = ?", (url_hash,))
            result = cursor.fetchone()
            return result[0] if result else None

    def cache_content(self, url: str, markdown_content: str, job_id: str | None = None) -> None:
        """Store markdown content in the cache for a URL, with optional job_id.

        Args:
            url: The URL that was crawled.
            markdown_content: The markdown content to cache.
            job_id: Optional job ID to associate with the cached content.
        """
        url_hash = self._get_url_hash(url)
        crawled_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Use INSERT OR REPLACE to update existing entries
            conn.execute(
                """
                INSERT OR REPLACE INTO url_cache
                (url_hash, url, job_id, markdown_content, crawled_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (url_hash, url, job_id, markdown_content, crawled_at),
            )
            conn.commit()

    def get_url_by_job_id(self, job_id: str) -> str | None:
        """Retrieve the URL for a given job_id.

        Args:
            job_id: The job ID to look up.

        Returns:
            The URL associated with the job ID if found, None otherwise.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT url FROM url_cache WHERE job_id = ?", (job_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_cached_content_by_job_id(self, job_id: str) -> str | None:
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

    def export_to_pdf(self, url: str, output_dir: Path) -> Path:
        """Export cached markdown content for a URL to PDF format using pandoc.

        Args:
            url: The URL whose cached content to export.
            output_dir: Directory to save the PDF file.

        Returns:
            Path to the generated PDF file.

        Raises:
            ValueError: If the URL is not found in cache.
            RuntimeError: If pandoc conversion fails.
        """
        markdown_content = self.get_cached_content(url)
        if not markdown_content:
            raise ValueError(f"URL not found in cache: {url}")

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate a safe filename from the URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "")
        safe_filename = f"{domain}_{self._get_url_hash(url)[:8]}.pdf"
        output_path = output_dir / safe_filename

        # Add header with URL and export timestamp
        enhanced_markdown = f"# Job Description\n\n**Source:** {url}\n**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n{markdown_content}\n\n---"

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

    def export_to_pdf_by_job_id(self, job_id: str, output_dir: Path) -> Path:
        """Export cached markdown content for a job_id to PDF format using pandoc.

        Args:
            job_id: The job ID whose cached content to export.
            output_dir: Directory to save the PDF file.

        Returns:
            Path to the generated PDF file.

        Raises:
            ValueError: If no URL is found for the job ID.
            RuntimeError: If pandoc conversion fails.
        """
        url = self.get_url_by_job_id(job_id)
        if not url:
            raise ValueError(f"No URL found for job_id: {job_id}")
        return self.export_to_pdf(url, output_dir)

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

    def list_cached_urls(self) -> list[dict[str, str]]:
        """List all cached URLs with their metadata.

        Returns:
            List of dictionaries containing URL information.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT url, crawled_at, LENGTH(markdown_content) as content_size
                FROM url_cache
                ORDER BY crawled_at DESC
            """)
            results = cursor.fetchall()

        return [{"url": row[0], "crawled_at": row[1], "content_size": row[2]} for row in results]

    def export_all_to_pdf(self, output_dir: Path) -> list[Path]:
        """Export all cached content to PDF files.

        Args:
            output_dir: Directory to save the PDF files.

        Returns:
            List of paths to generated PDF files.
        """
        cached_urls = self.list_cached_urls()
        exported_files = []

        for url_info in cached_urls:
            try:
                pdf_path = self.export_to_pdf(url_info["url"], output_dir)
                exported_files.append(pdf_path)
            except Exception as e:
                # Log error but continue with other URLs
                print(f"Error exporting {url_info['url']}: {e}")

        return exported_files
