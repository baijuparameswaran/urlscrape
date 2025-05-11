#!/usr/bin/env python3
"""
Test script to demonstrate the URL scraper.
"""

import asyncio
from url_scraper import scrape_url

async def test_scraper():
    # Example URL to scrape
    test_url = "https://example.com"
    output_directory = "example_output"
    
    # Call the scraper function
    result_dir = await scrape_url(test_url, output_directory)
    print(f"Test completed. Results available in: {result_dir}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
