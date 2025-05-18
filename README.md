# URL Scraper

A Python utility that scrapes web pages using Playwright and generates a folder with:
- A screenshot of the page
- A DOM snapshot in JSON format
- A text file containing the URL

## Requirements

- Python 3.12
- Pipenv

## Installation

1. Clone this repository
2. Install dependencies using Pipenv:
   ```
   pipenv install
   ```
3. Install Playwright browsers:
   ```
   pipenv run python -m playwright install
   ```

### Updating to Python 3.12

If you need to update an existing installation to Python 3.12:

1. Make sure Python 3.12 is installed on your system
2. Run the update script:
   ```
   ./update_to_python312.sh
   ```
   
This script will:
- Remove the current virtual environment
- Create a new one with Python 3.12
- Install all dependencies
- Install Playwright browsers

## Usage

### URL Scraper

```bash
pipenv run python url_scraper.py <URL> [output_directory]
```

#### Arguments:
- `URL`: The web page URL to scrape
- `output_directory`: (Optional) Directory to save results. If not specified, a directory will be created based on the domain name and timestamp.

#### Example:
```bash
pipenv run python url_scraper.py https://example.com my_output_dir
```

### Link Extractor

To analyze an existing DOM snapshot for links without re-scraping:

```bash
pipenv run python extract_links.py <path_to_dom_snapshot.json> [--output output_directory]
```

#### Arguments:
- `path_to_dom_snapshot.json`: Path to a previously generated DOM snapshot file
- `--output`, `-o`: (Optional) Directory to save extraction results. If not specified, will use the directory of the snapshot file.

#### Example:
```bash
pipenv run python extract_links.py my_results/dom_snapshot.json
```

### BFS Traverse

To traverse a DOM snapshot in breadth-first order and find hrefs at each level:

```bash
pipenv run python bfs_traverse.py <path_to_dom_snapshot.json> [output_file]
```

#### Arguments:
- `path_to_dom_snapshot.json`: Path to a previously generated DOM snapshot file
- `output_file`: (Optional) Path to save the BFS traversal results

#### Example:
```bash
pipenv run python bfs_traverse.py my_results/dom_snapshot.json
```

### Keyword Search

To search for links containing a specific keyword in a BFS traversal result:

```bash
pipenv run python keyword_search.py <path_to_bfs_html_file> <keyword> [output_file]
```

#### Arguments:
- `path_to_bfs_html_file`: Path to the BFS traversal HTML results file
- `keyword`: The keyword to search for
- `output_file`: (Optional) Path to save keyword search results

#### How it works:
The keyword search algorithm:
1. Analyzes all href elements at each DOM level
2. Calculates the ratio of hrefs containing the keyword to total hrefs at each level
3. Selects the first level with the highest keyword match ratio
4. Returns all href elements from that level containing the keyword

This approach is particularly effective at identifying the most relevant DOM level that contains structured search results or link lists related to the keyword.

#### Example:
```bash
pipenv run python keyword_search.py my_results/bfs_hrefs_by_level.html fire
```

#### Testing the Keyword Ratio Search:
You can test the keyword ratio search algorithm with the included test script:

```bash
pipenv run python test_keyword_ratio.py
```

This will demonstrate how the algorithm selects the level with the highest concentration of keyword matches rather than simply the most matches.

### Search Extractor

To extract search result links from Level 16 of the DOM (which typically contains search results):

```bash
pipenv run python search_extractor.py <path_to_bfs_html_file> <keyword> [output_file]
```

#### Arguments:
- `path_to_bfs_html_file`: Path to the BFS traversal HTML results file
- `keyword`: The keyword to highlight in results
- `output_file`: (Optional) Path to save search results

#### Example:
```bash
pipenv run python search_extractor.py my_results/bfs_hrefs_by_level.html fire
```

### All-in-One BFS Keyword Search

To perform the entire process (scrape URL, BFS traversal, and keyword search) in one step:

```bash
pipenv run python bfs_keyword_search.py <URL> <keyword> [output_directory]
```

#### Arguments:
- `URL`: The web page URL to scrape
- `keyword`: The keyword to search for
- `output_directory`: (Optional) Directory to save results

#### Features:
- Creates a unique list of hrefs at each DOM level
- Normalizes URLs by removing anchors or query parameters for analysis
- Ensures the keyword appears in the URL path (not just query parameters)
- Excludes URLs where the entire path is just the keyword
- Counts each URL only once in the analysis
- Calculates the ratio of keyword-containing URLs to total URLs at each level
- Selects the level with the highest ratio of keyword matches

#### Example:
```bash
pipenv run python bfs_keyword_search.py https://example.com/search?q=fire fire
```

## Output Files

### URL Scraper Output

The script will create a directory containing:
- `screenshot.png`: Full-page screenshot
- `dom_snapshot.json`: Enhanced DOM structure in JSON format with better text content handling
- `url.txt`: Text file with the original URL
- `page_text.txt`: Full page text content as rendered in the browser
- `page_source.html`: Complete HTML source of the page
- `search_result_links.json`: Extracted groups of links that appear to be search results or navigation lists
- `search_results_summary.txt`: Human-readable summary of the extracted links

### Link Extractor Output

The extractor creates the following files:
- `extracted_links.json`: All link groups with URLs, texts, and metadata
- `extracted_links_summary.txt`: Human-readable summary of all link groups
- `extracted_links.html`: Interactive HTML report for easy viewing and exploration of links

### BFS Traverse Output

The BFS traversal creates the following files:
- `bfs_hrefs_by_level.txt`: Text file showing all hrefs organized by DOM level
- `bfs_hrefs_by_level.html`: Interactive HTML visualization of all hrefs by level

### Keyword Search Output

The keyword search creates the following files:
- `keyword_search_<keyword>.txt`: Text file with search results for the keyword, including keyword match ratio information, a list of excluded URLs with reasons, and comprehensive level statistics
- `keyword_search_<keyword>.html`: Interactive HTML visualization highlighting matches, with visual representation of the keyword match ratio, level statistics, and URLs that were excluded (such as those with anchors or query parameters)

### Search Extractor Output

The search extractor creates the following files:
- `search_results_<keyword>.html`: Interactive HTML visualization of search results

### All-in-One BFS Keyword Search Output

The all-in-one script creates all the above outputs in a single execution, plus:
- Detailed analysis of URL exclusions with reasons (e.g., links with anchors, query parameters)
- Comprehensive level-by-level statistics showing keyword match ratios
- Normalized URLs for better analysis (removing anchors and query parameters)
- Interactive HTML reports with color-coded highlighting of excluded URLs and keyword matches
