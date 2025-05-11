# URL Scraper

A Python utility that scrapes web pages using Playwright and generates a folder with:
- A screenshot of the page
- A DOM snapshot in JSON format
- A text file containing the URL

## Requirements

- Python 3.7+
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

## Usage

```bash
pipenv run python url_scraper.py <URL> [output_directory]
```

### Arguments:
- `URL`: The web page URL to scrape
- `output_directory`: (Optional) Directory to save results. If not specified, a directory will be created based on the domain name and timestamp.

### Example:
```bash
pipenv run python url_scraper.py https://example.com my_output_dir
```

## Output

The script will create a directory containing:
- `screenshot.png`: Full-page screenshot
- `dom_snapshot.json`: Enhanced DOM structure in JSON format with better text content handling
- `url.txt`: Text file with the original URL
- `page_text.txt`: Full page text content as rendered in the browser
- `page_source.html`: Complete HTML source of the page
