#!/usr/bin/env python3
"""
BFS DOM Traversal and Keyword Search

This script crawls a web page using Playwright, performs a breadth-first search
through the DOM, and identifies links containing a specific keyword.
"""

import os
import sys
import json
import re
import time
import asyncio
from urllib.parse import urlparse, urljoin
from collections import defaultdict, deque
from playwright.async_api import async_playwright

async def scrape_and_search(url, keyword, output_dir=None):
    """
    Scrape a web page, perform a BFS traversal of the DOM, and search for a keyword.
    
    Args:
        url (str): The URL to scrape
        keyword (str): The keyword to search for
        output_dir (str, optional): Directory to save results
    
    Returns:
        dict: Results of the search
    """
    # Create output directory
    if not output_dir:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = f"{domain}_{timestamp}"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save URL to a file
    url_path = os.path.join(output_dir, "url.txt")
    with open(url_path, 'w', encoding='utf-8') as f:
        f.write(url)
    
    # Launch Playwright and get DOM snapshot
    print(f"Launching browser and navigating to {url}")
    dom_snapshot = await get_dom_snapshot(url)
    
    # Save DOM snapshot to file
    snapshot_path = os.path.join(output_dir, "dom_snapshot.json")
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        json.dump(dom_snapshot, f, ensure_ascii=False, indent=2)
    print(f"DOM snapshot saved to {snapshot_path}")
    
    # Perform BFS traversal
    print("Performing BFS traversal to find hrefs by level")
    level_hrefs = bfs_traverse_dom(dom_snapshot, url)
    
    # Save BFS traversal results
    bfs_txt_path = os.path.join(output_dir, "bfs_hrefs_by_level.txt")
    bfs_html_path = os.path.join(output_dir, "bfs_hrefs_by_level.html")
    save_bfs_results(level_hrefs, url, bfs_txt_path, bfs_html_path)
    
    # Search for keyword
    print(f"Searching for keyword '{keyword}' in hrefs")
    keyword_results = search_keyword_in_hrefs(level_hrefs, keyword)
    
    # Save keyword search results
    keyword_txt_path = os.path.join(output_dir, f"keyword_search_{keyword}.txt")
    keyword_html_path = os.path.join(output_dir, f"keyword_search_{keyword}.html")
    save_keyword_results(keyword_results, keyword, url, keyword_txt_path, keyword_html_path)
    
    return {
        'output_dir': output_dir,
        'level_hrefs': level_hrefs,
        'keyword_results': keyword_results
    }

async def get_dom_snapshot(url):
    """
    Get a DOM snapshot of a web page using Playwright.
    
    Args:
        url (str): The URL to navigate to
    
    Returns:
        dict: DOM snapshot as a dictionary
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Navigate to the URL
        await page.goto(url, wait_until="networkidle")
        
        # Take a screenshot
        await page.screenshot(path=os.path.join(os.path.dirname(url), "screenshot.png"), full_page=True)
        
        # Get DOM snapshot
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
        
        # Get the page HTML
        html_content = await page.content()
        
        # Get the page text
        page_text = await page.evaluate("() => document.body.innerText")
        
        # Save HTML and page text
        output_dir = os.path.dirname(url)
        with open(os.path.join(output_dir, "page_source.html"), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        with open(os.path.join(output_dir, "page_text.txt"), 'w', encoding='utf-8') as f:
            f.write(page_text)
        
        await browser.close()
        
        return dom_snapshot

def bfs_traverse_dom(dom_snapshot, base_url):
    """
    Traverse the DOM snapshot in breadth-first order and extract hrefs by level.
    
    Args:
        dom_snapshot (dict): DOM snapshot
        base_url (str): Base URL for resolving relative links
    
    Returns:
        dict: Dictionary mapping levels to lists of hrefs
    """
    # Image file extensions to exclude
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
    
    # BFS traversal
    queue = deque([(dom_snapshot, 0)])  # (node, level)
    level_hrefs = defaultdict(list)
    
    # Keep track of unique URLs to avoid duplicates
    seen_urls = set()
    
    while queue:
        node, level = queue.popleft()
        
        # Check if this node is an element
        if node.get('nodeType') == 1:  # Element node
            tag_name = node.get('tagName', '')
            
            # Check for href attribute
            if 'attributes' in node:
                href = node.get('attributes', {}).get('href', '')
                
                if href and not href.startswith('#') and not href.startswith('javascript:'):
                    # Skip image files
                    if not any(href.lower().endswith(ext) for ext in image_extensions):
                        # Get link text
                        link_text = node.get('linkText', '') or node.get('displayedText', '')
                        if not link_text:
                            link_text = node.get('attributes', {}).get('title', '') or "[No text]"
                        
                        # Create absolute URL
                        full_url = href
                        if href and not href.startswith(('http://', 'https://', '//')):
                            full_url = urljoin(base_url, href)
                        
                        # Clean text
                        if link_text:
                            link_text = ' '.join(link_text.split())
                        
                        # Add to the appropriate level list
                        level_hrefs[level].append({
                            'url': full_url,
                            'text': link_text,
                            'tag': tag_name,
                            'element_type': 'anchor' if tag_name.lower() == 'a' else 'element_with_href'
                        })
        
        # Add children to the queue for the next level
        if 'children' in node and node['children']:
            for child in node['children']:
                queue.append((child, level + 1))
    
    return level_hrefs

def search_keyword_in_hrefs(level_hrefs, keyword):
    """
    Search for a keyword in hrefs by level, applying the following rules:
    1. Make unique list of hrefs in each level.
    2. Remove links with similar path but having an anchor or query extensions
    3. Make sure the keyword is in the URL path for being counted
    4. The keyword in whole in the path may be ignored (eg. www.abc.com/fire/search where fire is the keyword)
    5. Each link may be counted only once
    6. Make a ratio of all links to the links with the keyword passing requirements
    
    Args:
        level_hrefs (dict): Dictionary mapping levels to lists of hrefs
        keyword (str): Keyword to search for
    
    Returns:
        dict: Dictionary of search results
    """
    keyword_regex = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
    level_stats = {}
    level_matches = {}
    level_debug = {}  # Store debugging info for each level
    
    # Process each level
    for level, hrefs in level_hrefs.items():
        # Track URLs for debugging
        debug_info = {
            'total_urls': len(hrefs),
            'skipped': {},
            'included': []
        }
        
        # 1. Create unique list of hrefs by normalizing URLs (removing anchors and query params)
        unique_urls = {}
        for href in hrefs:
            url = href['url']
            
            # Skip social media sharing links
            if any(share_domain in url.lower() for share_domain in [
                'facebook.com/sharer', 'twitter.com/intent/tweet', 
                'whatsapp.com/send', 'telegram.me/share'
            ]):
                debug_info['skipped'][url] = "Social media sharing link"
                continue
                
            # 2. Normalize URL by removing anchor and query parts
            parsed_url = urlparse(url)
            
            # Check if URL has anchor or query (these will be excluded from counting)
            has_anchor = bool(parsed_url.fragment)
            has_query = bool(parsed_url.query)
            
            # Get base URL without query and fragment
            normalized_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            
            # If this URL has an anchor or query, mark it as such for tracking
            if has_anchor or has_query:
                reason = []
                if has_anchor:
                    reason.append("Has anchor (#" + parsed_url.fragment + ")")
                if has_query:
                    reason.append("Has query parameters")
                
                debug_info['skipped'][url] = ", ".join(reason)
                continue  # Skip URLs with anchors or queries
            
            # Store in unique URLs dictionary if it hasn't been seen yet or has more text content
            if normalized_url not in unique_urls or len(href['text']) > len(unique_urls[normalized_url]['text']):
                unique_urls[normalized_url] = {
                    'text': href['text'],
                    'url': href['url'],  # Keep original URL for display
                    'tag': href['tag'],
                    'normalized_url': normalized_url
                }
        
        # Now we have unique URLs for this level (already excluded those with anchors/queries)
        matching_items = []
        total_valid_urls = len(unique_urls)
        
        # Analyze each unique URL 
        for norm_url, href_data in unique_urls.items():
            # Parse the URL to get the path
            parsed_url = urlparse(norm_url)
            path = parsed_url.path
            
            # 3. Check if keyword is in the URL path
            if not keyword_regex.search(path):
                debug_info['skipped'][norm_url] = f"Keyword '{keyword}' not in URL path"
                continue
                
            # 4. Check if the keyword is not the entire path
            path_segments = [segment for segment in path.split('/') if segment]
            
            # Skip if the path is just the keyword
            if len(path_segments) == 1 and keyword_regex.fullmatch(path_segments[0]):
                debug_info['skipped'][norm_url] = f"Keyword '{keyword}' is the entire path"
                continue
            
            # This URL matches all criteria
            href_data['path'] = path
            matching_items.append(href_data)
            debug_info['included'].append(norm_url)
        
        # Store stats for this level
        if total_valid_urls > 0:
            keyword_ratio = len(matching_items) / total_valid_urls
            
            level_stats[level] = {
                'total_unique_urls': total_valid_urls,
                'matching_urls': len(matching_items),
                'keyword_ratio': keyword_ratio
            }
            
            if matching_items:
                level_matches[level] = matching_items
            
        # Store debug info
        level_debug[level] = debug_info
    
    # Find the level with the highest keyword ratio
    if not level_stats:
        return None
    
    # Sort levels by keyword ratio (highest first)
    sorted_levels = sorted(level_stats.items(), key=lambda x: x[1]['keyword_ratio'], reverse=True)
    
    # Get the highest ratio
    highest_ratio = sorted_levels[0][1]['keyword_ratio']
    target_level = sorted_levels[0][0]
    
    # If multiple levels have the same highest ratio, choose the one closest to the root
    same_ratio_levels = [level for level, stats in level_stats.items() 
                         if stats['keyword_ratio'] == highest_ratio]
    if same_ratio_levels:
        target_level = min(same_ratio_levels)
    
    # Prepare the results
    best_matches = level_matches.get(target_level, [])
    
    return {
        'target_level': target_level,
        'all_matches': level_matches,
        'best_matches': best_matches,
        'level_stats': level_stats,
        'highest_ratio': highest_ratio,
        'debug_info': level_debug  # Include debug info
    }

def save_bfs_results(level_hrefs, base_url, txt_path, html_path):
    """
    Save BFS traversal results to text and HTML files.
    
    Args:
        level_hrefs (dict): Dictionary mapping levels to lists of hrefs
        base_url (str): Base URL of the page
        txt_path (str): Path to save text results
        html_path (str): Path to save HTML results
    """
    # Create text output
    output_lines = [f"BFS Traversal Results - hrefs by level for {base_url}", "=" * 60, ""]
    
    for level, hrefs in sorted(level_hrefs.items()):
        output_lines.append(f"Level {level} - {len(hrefs)} hrefs found")
        output_lines.append("-" * 40)
        
        for i, href in enumerate(hrefs, 1):
            text = href['text'].strip() if href['text'] else "[No text]"
            url = href['url']
            
            # Truncate very long strings
            if len(text) > 80:
                text = text[:77] + "..."
            if len(url) > 80:
                url = url[:77] + "..."
            
            output_lines.append(f"{i}. [{href['tag']}] {text}")
            output_lines.append(f"   URL: {url}")
            output_lines.append("")
        
        output_lines.append("")
    
    # Save to text file
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines))
    
    # Create HTML output
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>BFS Traversal - hrefs by Level for {base_url}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        h1, h2 {{ color: #333; }}
        .level-container {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .level-header {{ background-color: #f5f5f5; padding: 10px; margin-bottom: 15px; border-radius: 3px; }}
        .href-item {{ margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #eee; }}
        .href-text {{ font-weight: bold; margin-bottom: 5px; }}
        .href-url {{ color: blue; word-break: break-all; }}
        .href-tag {{ color: #666; font-style: italic; }}
        .toggle-btn {{ cursor: pointer; padding: 5px 10px; background: #e0e0e0; border: none; border-radius: 3px; margin-right: 10px; }}
        .href-list {{ max-height: 500px; overflow-y: auto; }}
        .filter-container {{ margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>BFS Traversal - hrefs by Level for {base_url}</h1>
    <p>This visualization shows href elements found at each DOM level during a breadth-first traversal.</p>
    
    <div class="filter-container">
        <button class="toggle-btn" onclick="toggleAllLevels()">Toggle All Levels</button>
        <input type="text" id="hrefFilter" placeholder="Filter by text..." 
               onkeyup="filterHrefs()" style="padding: 5px; width: 300px;">
    </div>
""")

        if not level_hrefs:
            f.write("<p>No href elements were identified.</p>")
        else:
            for level, hrefs in sorted(level_hrefs.items()):
                level_id = f"level{level}"
                
                f.write(f"""
    <div class="level-container" id="container-{level_id}">
        <div class="level-header">
            <button class="toggle-btn" onclick="toggleLevel('{level_id}')">Toggle</button>
            <h2>Level {level} - {len(hrefs)} hrefs found</h2>
        </div>
        
        <div id="{level_id}" class="href-list">
""")
                
                for i, href in enumerate(hrefs, 1):
                    text = href['text'].strip() if href['text'] else "[No text]"
                    url = href['url']
                    tag = href['tag']
                    
                    f.write(f"""
            <div class="href-item">
                <div class="href-text">{i}. {text}</div>
                <div class="href-tag">Element: &lt;{tag}&gt;</div>
                <div class="href-url"><a href="{url}" target="_blank">{url}</a></div>
            </div>
""")
                
                f.write("""
        </div>
    </div>
""")
        
        f.write("""
    <script>
        function toggleLevel(levelId) {
            const level = document.getElementById(levelId);
            if (level.style.display === 'none') {
                level.style.display = 'block';
            } else {
                level.style.display = 'none';
            }
        }
        
        function toggleAllLevels() {
            const levels = document.querySelectorAll('.href-list');
            const firstLevel = levels[0];
            const allHidden = firstLevel.style.display === 'none';
            
            levels.forEach(level => {
                level.style.display = allHidden ? 'block' : 'none';
            });
        }
        
        function filterHrefs() {
            const filterText = document.getElementById('hrefFilter').value.toLowerCase();
            const containers = document.querySelectorAll('.level-container');
            
            containers.forEach(container => {
                const hrefs = container.querySelectorAll('.href-item');
                let found = false;
                
                hrefs.forEach(href => {
                    const text = href.textContent.toLowerCase();
                    if (text.includes(filterText)) {
                        href.style.display = 'block';
                        found = true;
                    } else {
                        href.style.display = 'none';
                    }
                });
                
                container.style.display = found ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>
""")

def render_excluded_urls_table(f, search_results, target_level):
    """
    Render the HTML table showing excluded URLs
    
    Args:
        f: File handle to write to
        search_results: Search results dictionary
        target_level: The target level to show skipped URLs for
    """
    f.write("""
    <!-- Show skipped URLs -->
    <div class="skipped-container" style="margin-bottom: 20px;">
        <h3>URLs Excluded from Analysis:</h3>
        <div class="collapsible-content" style="max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background-color: #f5f5f5;">
                    <th style="text-align: left; padding: 8px; border: 1px solid #ddd;">URL</th>
                    <th style="text-align: left; padding: 8px; border: 1px solid #ddd;">Reason for Exclusion</th>
                </tr>
    """)

    # Add up to 20 skipped URLs
    skipped_urls = search_results.get('skipped_urls', {}).get(target_level, [])
    for i, item in enumerate(skipped_urls[:20]):
        bg_color = '#f9f9f9' if i % 2 == 0 else 'white'
        anchor_highlight = 'background-color: #ffe6e6;' if "anchor" in item['reason'].lower() else ''
        
        f.write(f"""
                <tr style="background-color: {bg_color};">
                    <td style="padding: 8px; border: 1px solid #ddd; {anchor_highlight}">{item['url']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{item['reason']}</td>
                </tr>""")
    
    if skipped_urls:
        if len(skipped_urls) > 20:
            f.write(f"""
                <tr>
                    <td colspan="2" style="padding: 8px; text-align: center; font-style: italic;">
                        And {len(skipped_urls) - 20} more URLs were excluded...
                    </td>
                </tr>""")
    else:
        f.write("""
                <tr>
                    <td colspan="2" style="padding: 8px; text-align: center;">
                        No URLs were excluded at this level.
                    </td>
                </tr>""")
    
    f.write("""
            </table>
        </div>
    </div>
    """)

def save_keyword_results(search_results, keyword, base_url, txt_path, html_path):
    """
    Save keyword search results to text and HTML files.
    
    Args:
        search_results (dict): Dictionary of search results
        keyword (str): The search keyword
        base_url (str): Base URL of the page
        txt_path (str): Path to save text results
        html_path (str): Path to save HTML results
    """
    if not search_results:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"No matches found for keyword '{keyword}'")
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Keyword Search Results - '{keyword}'</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        h1, h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Keyword Search Results - '{keyword}'</h1>
    <p>No matches found for keyword '{keyword}'</p>
</body>
</html>
""")
        return
    
    target_level = search_results['target_level']
    best_matches = search_results['best_matches']
    level_stats = search_results.get('level_stats', {})
    highest_ratio = search_results.get('highest_ratio', 0)
    debug_info = search_results.get('debug_info', {}).get(target_level, {})
    
    # Get stats for the target level
    total_unique_urls = 0
    matching_urls = 0
    if target_level in level_stats:
        total_unique_urls = level_stats[target_level].get('total_unique_urls', 0)
        matching_urls = level_stats[target_level].get('matching_urls', 0)
    
    # Format ratio as percentage
    ratio_percentage = f"{highest_ratio * 100:.2f}%"
    
    # Create text output
    result_lines = [
        f"Keyword Search Results for '{keyword}'",
        "=" * 60,
        f"Level {target_level} - Level with highest keyword match ratio ({ratio_percentage})",
        f"Matches: {matching_urls} / Total unique URLs at this level: {total_unique_urls}",
        "",
        "Ranking applied with the following rules:",
        "1. Only unique URLs after removing query parameters and anchors",
        "2. Only counting URLs with keyword in their path",
        "3. Excluding URLs where the keyword is the entire path",
        "4. Each URL counted only once",
        ""
    ]
    
    # Add skipped URLs information
    skipped_urls = debug_info.get('skipped', {})
    if skipped_urls:
        # Focus on URLs with anchors
        anchor_urls = [(url, reason) for url, reason in skipped_urls.items() if "anchor" in reason.lower()]
        
        if anchor_urls:
            result_lines.append(f"URLs with anchors skipped at this level:")
            result_lines.append("-" * 40)
            
            for i, (url, reason) in enumerate(anchor_urls[:5], 1):
                result_lines.append(f"{i}. {url}")
                result_lines.append(f"   Reason: {reason}")
                result_lines.append("")
            
            if len(anchor_urls) > 5:
                result_lines.append(f"...and {len(anchor_urls) - 5} more URLs with anchors were skipped.")
            
            result_lines.append("")
    
    # Add all level statistics
    result_lines.append("Level Statistics:")
    result_lines.append("-" * 40)
    
    for level, stats in sorted(level_stats.items()):
        level_ratio = stats['keyword_ratio']
        level_ratio_pct = f"{level_ratio * 100:.2f}%"
        result_lines.append(f"Level {level}: {stats['matching_urls']}/{stats['total_unique_urls']} = {level_ratio_pct}")
    
    result_lines.append("")
    
    # Add the best matches
    result_lines.append("Best Matches:")
    result_lines.append("-" * 40)
    
    for i, item in enumerate(best_matches, 1):
        result_lines.append(f"{i}. {item['text']}")
        result_lines.append(f"   URL: {item['url']}")
        result_lines.append(f"   Normalized URL: {item['normalized_url']}")
        result_lines.append(f"   Path: {item.get('path', 'N/A')}")
        result_lines.append(f"   Tag: {item['tag']}")
        result_lines.append("")
    
    # Save to text file
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(result_lines))
    
    # Create HTML output
    with open(html_path, 'w', encoding='utf-8') as f:
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Keyword Search Results - '{keyword}'</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        h1, h2 {{ color: #333; }}
        .result-container {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .result-header {{ background-color: #f5f5f5; padding: 10px; margin-bottom: 15px; border-radius: 3px; }}
        .match-item {{ margin-bottom: 12px; padding: 10px; border-bottom: 1px solid #eee; }}
        .match-text {{ font-weight: bold; margin-bottom: 5px; }}
        .match-url {{ color: blue; word-break: break-all; margin-bottom: 3px; }}
        .match-norm-url {{ color: #555; word-break: break-all; font-style: italic; font-size: 0.9em; margin-bottom: 3px; }}
        .match-path {{ color: #777; font-family: monospace; margin-bottom: 3px; }}
        .match-tag {{ color: #666; font-style: italic; margin-top: 5px; }}
        .highlight {{ background-color: #ffff00; font-weight: bold; }}
        .stats {{ margin-top: 10px; font-size: 0.9em; color: #555; }}
        .ratio-bar {{ height: 20px; background-color: #ddd; margin-top: 5px; border-radius: 3px; position: relative; margin-bottom: 15px; }}
        .ratio-fill {{ height: 100%; background-color: #4CAF50; border-radius: 3px; }}
        .ratio-text {{ position: absolute; right: 5px; top: 0; font-size: 0.8em; color: #000; }}
        .rules {{ background-color: #f9f9f9; padding: 10px; border-left: 3px solid #4CAF50; margin: 15px 0; }}
        .level-stats {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        .level-stat-item {{ border: 1px solid #ddd; padding: 10px; border-radius: 5px; flex-grow: 1; min-width: 200px; }}
        .level-best {{ background-color: #e8f5e9; }}
        .skipped-container {{ margin: 20px 0; }}
        .skipped-table {{ width: 100%; border-collapse: collapse; }}
        .skipped-table th, .skipped-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .skipped-table th {{ background-color: #f5f5f5; }}
        .skipped-anchor {{ background-color: #ffe6e6; }}
    </style>
</head>
<body>
    <h1>Keyword Search Results - '{keyword}'</h1>
    <div class="result-header">
        <h2>Level {target_level} - {matching_urls} matches found</h2>
        <p>This level has the highest keyword match ratio ({ratio_percentage})</p>
        <div class="stats">
            <p>Matches: {matching_urls} / Total unique URLs at this level: {total_unique_urls}</p>
            <div class="ratio-bar">
                <div class="ratio-fill" style="width: {ratio_percentage};"></div>
                <div class="ratio-text">{ratio_percentage}</div>
            </div>
        </div>
    </div>
    
    <div class="rules">
        <h3>Ranking Rules Applied:</h3>
        <ol>
            <li>Only counting unique URLs after removing query parameters and anchors</li>
            <li>Only counting URLs with keyword in their path (not in query or fragment)</li>
            <li>Excluding URLs where the keyword is the entire path</li>
            <li>Each URL counted only once</li>
            <li>Level with the highest ratio of keyword URLs to total URLs is selected</li>
        </ol>
    </div>
    
    <!-- Show excluded URLs -->
    <div class="skipped-container">
        <h3>URLs Excluded from Analysis:</h3>
        <table class="skipped-table">
            <tr>
                <th>URL</th>
                <th>Reason for Exclusion</th>
            </tr>
"""
        
        # Add excluded URLs with anchors
        anchor_urls = [(url, reason) for url, reason in skipped_urls.items() if "anchor" in reason.lower()]
        
        if anchor_urls:
            for i, (url, reason) in enumerate(anchor_urls[:10]):
                bg_color = '#f9f9f9' if i % 2 == 0 else 'white'
                html_content += f"""
            <tr style="background-color: {bg_color};">
                <td class="skipped-anchor">{url}</td>
                <td>{reason}</td>
            </tr>"""
                
            if len(anchor_urls) > 10:
                html_content += f"""
            <tr>
                <td colspan="2" style="text-align: center; font-style: italic;">
                    And {len(anchor_urls) - 10} more URLs with anchors were excluded...
                </td>
            </tr>"""
        else:
            html_content += """
            <tr>
                <td colspan="2" style="text-align: center;">
                    No URLs with anchors were excluded at this level.
                </td>
            </tr>"""
        
        html_content += """
        </table>
    </div>
    
    <h3>Level Statistics:</h3>
    <div class="level-stats">
"""
        
        # Add level statistics
        for level, stats in sorted(level_stats.items()):
            level_ratio = stats['keyword_ratio']
            level_ratio_pct = f"{level_ratio * 100:.2f}%"
            is_best = level == target_level
            
            best_class = ' level-best' if is_best else ''
            
            html_content += f"""
        <div class="level-stat-item{best_class}">
            <h4>Level {level}{' (BEST)' if is_best else ''}</h4>
            <p>Matches: {stats['matching_urls']} / Total: {stats['total_unique_urls']}</p>
            <p>Ratio: {level_ratio_pct}</p>
            <div class="ratio-bar">
                <div class="ratio-fill" style="width: {level_ratio_pct};"></div>
                <div class="ratio-text">{level_ratio_pct}</div>
            </div>
        </div>"""
        
        html_content += """
    </div>
    
    <h3>Matching URLs:</h3>
    <div class="result-container">
"""
        
        if not best_matches:
            html_content += "<p>No matches found.</p>"
        else:
            for i, match in enumerate(best_matches, 1):
                import re
                # Highlight the keyword in text, URL, and path
                highlighted_text = re.sub(
                    f'(?i)\\b({re.escape(keyword)})\\b', 
                    r'<span class="highlight">\1</span>', 
                    match['text']
                )
                
                highlighted_url = re.sub(
                    f'(?i)\\b({re.escape(keyword)})\\b', 
                    r'<span class="highlight">\1</span>', 
                    match['url']
                )
                
                path = match.get('path', '')
                highlighted_path = re.sub(
                    f'(?i)\\b({re.escape(keyword)})\\b', 
                    r'<span class="highlight">\1</span>', 
                    path
                ) if path else ''
                
                html_content += f"""
        <div class="match-item">
            <div class="match-text">{i}. {highlighted_text}</div>
            <div class="match-url"><a href="{match['url']}" target="_blank">{highlighted_url}</a></div>
            <div class="match-norm-url">Normalized: {match['normalized_url']}</div>
            <div class="match-path">Path: {highlighted_path}</div>
            <div class="match-tag">Element: &lt;{match['tag']}&gt;</div>
        </div>"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        f.write(html_content)
    

async def main():
    if len(sys.argv) < 3:
        print("Usage: python bfs_keyword_search.py <URL> <keyword> [output_directory]")
        sys.exit(1)
    
    url = sys.argv[1]
    keyword = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    results = await scrape_and_search(url, keyword, output_dir)
    print(f"Process complete! Results saved to {results['output_dir']}")

if __name__ == "__main__":
    asyncio.run(main())
