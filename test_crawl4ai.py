#!/usr/bin/env python3
"""
Test script for crawl4ai functionality.

Usage:
    python test_crawl4ai.py <URL>

Example:
    python test_crawl4ai.py https://example.com
"""

import argparse
import asyncio
import sys

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig


async def crawl_url(url: str) -> None:
    """Crawl a URL and print its markdown content.

    Args:
        url: The URL to crawl
    """
    browser_config = BrowserConfig()  # Default browser configuration
    run_config = CrawlerRunConfig()  # Default crawl run configuration

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Crawling URL: {url}")
        print("=" * 80)

        result = await crawler.arun(url=url, config=run_config)

        if result.success:
            print("SUCCESS: Crawling completed")
            print("=" * 80)
            print("MARKDOWN CONTENT:")
            print("-" * 40)
            print(result.markdown)
        else:
            print(f"ERROR: Failed to crawl URL")
            print(f"Error message: {result.error_message}")
            sys.exit(1)


def main() -> None:
    """Main function to parse arguments and run the crawler."""
    parser = argparse.ArgumentParser(
        description="Test crawl4ai by extracting markdown from a URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_crawl4ai.py https://example.com
  python test_crawl4ai.py https://linkedin.com/jobs/view/123456
        """,
    )

    parser.add_argument("url", help="URL to crawl and extract markdown from")

    args = parser.parse_args()

    try:
        asyncio.run(crawl_url(args.url))
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
