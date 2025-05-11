#!/usr/bin/env python3
"""
URL Scraper using Playwright.
This script takes a URL as input and generates a folder with:
- Screenshot of the page
- DOM snapshot in JSON format
- Text file with the original URL
"""

import os
import sys
import json
import time
from pathlib import Path
from urllib.parse import urlparse
import asyncio
from playwright.async_api import async_playwright


async def scrape_url(url, output_dir=None):
    """
    Scrape a URL using Playwright and save the results.
    
    Args:
        url (str): The URL to scrape
        output_dir (str, optional): Directory to save results. If None, a directory will be created
                                    based on the domain name and timestamp.
    
    Returns:
        str: Path to the output directory
    """
    # Parse the URL to extract domain for folder naming
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Create an output directory if not specified
    if output_dir is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = f"{domain}_{timestamp}"
    
    # Create the directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Navigate to the URL
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        
        # Save screenshot
        screenshot_path = os.path.join(output_dir, "screenshot.png")
        print(f"Taking screenshot and saving to {screenshot_path}")
        await page.screenshot(path=screenshot_path, full_page=True)
        
        # Get DOM snapshot as JSON with improved text capture
        dom_snapshot = await page.evaluate("""() => {
            function serializeNode(node) {
                if (!node) return null;
                
                const serialized = {
                    nodeType: node.nodeType,
                };
                
                if (node.nodeType === Node.ELEMENT_NODE) {
                    serialized.tagName = node.tagName;
                    serialized.attributes = {};
                    for (const attr of node.attributes) {
                        serialized.attributes[attr.name] = attr.value;
                    }
                    
                    // Capture the rendered text content for all elements
                    // This gets text as displayed on the page
                    const computedStyle = window.getComputedStyle(node);
                    if (computedStyle.display !== 'none' && computedStyle.visibility !== 'hidden') {
                        serialized.displayedText = node.innerText || '';
                    }
                    
                    // For special cases like links, capture the href and text specially
                    if (node.tagName === 'A') {
                        serialized.linkText = node.textContent || '';
                        serialized.linkHref = node.href || '';
                    }
                } else if (node.nodeType === Node.TEXT_NODE) {
                    serialized.textContent = node.textContent || '';
                } else if (node.nodeType === Node.COMMENT_NODE) {
                    serialized.comment = node.textContent || '';
                }
                
                // Check for CSS-generated content
                if (node.nodeType === Node.ELEMENT_NODE) {
                    try {
                        const before = window.getComputedStyle(node, '::before').content;
                        const after = window.getComputedStyle(node, '::after').content;
                        if (before && before !== 'none') serialized.beforeContent = before;
                        if (after && after !== 'none') serialized.afterContent = after;
                    } catch (e) {
                        // Ignore errors from getComputedStyle
                    }
                }
                
                if (node.childNodes.length > 0) {
                    serialized.children = [];
                    for (const child of node.childNodes) {
                        const serializedChild = serializeNode(child);
                        if (serializedChild) {
                            serialized.children.push(serializedChild);
                        }
                    }
                }
                
                return serialized;
            }
            
            return serializeNode(document.documentElement);
        }""")
        
        # Save DOM snapshot to file
        dom_path = os.path.join(output_dir, "dom_snapshot.json")
        print(f"Saving DOM snapshot to {dom_path}")
        with open(dom_path, 'w', encoding='utf-8') as f:
            json.dump(dom_snapshot, f, ensure_ascii=False, indent=2)
        
        # Save URL to text file
        url_path = os.path.join(output_dir, "url.txt")
        print(f"Saving URL to {url_path}")
        with open(url_path, 'w', encoding='utf-8') as f:
            f.write(url)
        
        # Extract and save full page text
        page_text = await page.evaluate("() => document.body.innerText")
        text_path = os.path.join(output_dir, "page_text.txt")
        print(f"Saving full page text to {text_path}")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(page_text)
            
        # Also save HTML content for reference
        html_content = await page.content()
        html_path = os.path.join(output_dir, "page_source.html")
        print(f"Saving HTML source to {html_path}")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        await browser.close()
    
    print(f"Scraping completed! Results saved in {output_dir}")
    return output_dir


def main():
    # Check if a URL was provided
    if len(sys.argv) < 2:
        print("Usage: python url_scraper.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(scrape_url(url, output_dir))


if __name__ == "__main__":
    main()
