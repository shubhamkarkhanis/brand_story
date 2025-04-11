# modules/scraper.py
# Contains functions for scraping website content and social media links/bios.
# NOTE: The main execution block has been removed; use modules/__init__.py to run the pipeline.

import requests # For making HTTP requests
from bs4 import BeautifulSoup # For parsing HTML content
import re # For regular expressions (finding patterns in links and text)
from urllib.parse import urljoin, urlparse # For handling relative URLs
import json # For JSON output (potentially useful if functions save intermediate steps)
import os # For path joining (potentially useful)
# Removed subprocess and sys as orchestration is handled elsewhere

# --- Constants ---

# Define patterns for common social media links using regular expressions
SOCIAL_MEDIA_PATTERNS = {
    'LinkedIn': re.compile(r'https?://(www\.)?linkedin\.com/(company|in)/[\w-]+/?'),
    'Twitter': re.compile(r'https?://(www\.)?(twitter|x)\.com/\w+/?(?!\w)'),
    'Facebook': re.compile(r'https?://(www\.)?facebook\.com/[\w.-]+/?'),
    'Instagram': re.compile(r'https?://(www\.)?instagram\.com/[\w.]+/'),
    'YouTube': re.compile(r'https?://(www\.)?youtube\.com/(user|channel|c)/[\w-]+/?'),
}

# Standard User-Agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Helper Function ---

def _fetch_page(url: str) -> BeautifulSoup | None:
    """Fetches and parses a single page."""
    if not url.startswith(('http://', 'https://')):
        print(f"Error: Invalid URL format: {url}")
        return None
    print(f"--> Fetching page: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            print(f"Warning: Content-Type is not HTML for {url} (was: {content_type})")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out for {url}")
        return None
    except requests.exceptions.MissingSchema:
         print(f"Error: Invalid URL format: {url}")
         return None
    except requests.exceptions.HTTPError as http_err:
        print(f"Error: HTTP error occurred for {url}: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Error: Request exception occurred for {url}: {req_err}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred fetching/parsing {url}: {e}")
        return None

# --- Core Scraping Functions ---

def find_social_links(base_url: str) -> dict:
    """Finds social media links on a website."""
    print(f"\nStarting social link search for: {base_url}")
    social_links_found = {}
    try:
        parsed_base = urlparse(base_url)
        if not parsed_base.scheme or not parsed_base.netloc:
            print(f"Error: Invalid base URL format: {base_url}")
            return {}
        base_url_normalized = f"{parsed_base.scheme}://{parsed_base.netloc}/"
    except Exception as e:
        print(f"Error parsing base URL {base_url}: {e}")
        return {}

    pages_to_check = [base_url_normalized]
    common_paths = ['/about', '/contact', '/about-us', '/contact-us']
    for path in common_paths:
        try:
            full_path_url = urljoin(base_url_normalized, path)
            pages_to_check.append(full_path_url)
        except Exception as e:
            print(f"Warning: Could not construct URL for path '{path}': {e}")

    pages_to_check = sorted(list(dict.fromkeys(pages_to_check)))
    processed_hrefs = set()

    for page_url in pages_to_check:
        if len(social_links_found) >= len(SOCIAL_MEDIA_PATTERNS): break
        soup = _fetch_page(page_url)
        if not soup: continue
        print(f"Searching for links on: {page_url}")
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href', '').strip()
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')): continue
            try:
                absolute_href = urljoin(page_url, href)
            except Exception as e:
                print(f"Warning: Could not resolve relative URL '{href}': {e}")
                continue
            try:
                parsed_href = urlparse(absolute_href)
                clean_href = f"{parsed_href.scheme}://{parsed_href.netloc}{parsed_href.path}"
                if clean_href.endswith('/'): clean_href = clean_href[:-1]
            except Exception as e:
                 print(f"Warning: Could not parse/clean URL '{absolute_href}': {e}")
                 clean_href = absolute_href

            if clean_href in processed_hrefs: continue
            processed_hrefs.add(clean_href)

            for platform, pattern in SOCIAL_MEDIA_PATTERNS.items():
                if platform not in social_links_found and pattern.match(clean_href):
                    print(f"  [✓] Found {platform}: {clean_href}")
                    social_links_found[platform] = clean_href
                    break
    if not social_links_found: print(f"Finished searching. No social links found for {base_url}")
    else: print(f"\nFinished searching for {base_url}. Found links: {social_links_found}")
    return social_links_found


def get_website_text(url: str) -> str | None:
    """Fetches and extracts website text."""
    print(f"\nAttempting to fetch website text from: {url}")
    soup = _fetch_page(url)
    if not soup: return None
    extracted_texts = []
    title = soup.find('title')
    if title and title.string: extracted_texts.append(title.string.strip())
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'): extracted_texts.append(meta_desc['content'].strip())

    content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'article', 'main', 'section', 'div'])
    tags_to_ignore_parents = ['nav', 'footer', 'header', 'script', 'style', 'aside', 'form', 'button', 'figure', 'figcaption']
    min_text_length = 25
    texts_from_tags = set()
    for tag in content_tags:
        if tag.parent and tag.parent.name in tags_to_ignore_parents: continue
        text = tag.get_text(separator=' ', strip=True)
        if text and len(text) >= min_text_length and '<script' not in text and '<style' not in text:
            alphanumeric_ratio = sum(c.isalnum() for c in text) / len(text) if len(text) > 0 else 0
            if alphanumeric_ratio > 0.6: texts_from_tags.add(text)

    if texts_from_tags: extracted_texts.extend(list(texts_from_tags))
    else: print("Warning: Could not extract significant text from common tags.")

    if not extracted_texts:
        print("Warning: Falling back to all body text.")
        body = soup.find('body')
        if body:
            for element in body(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'figure', 'noscript']):
                element.decompose()
            all_text = body.get_text(separator=' ', strip=True)
            if all_text: extracted_texts.append(re.sub(r'\s+', ' ', all_text).strip())
            else: return None
        else: return None

    full_text = "\n\n".join(extracted_texts)
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    print(f"Successfully extracted website text ({len(full_text)} chars).")
    return full_text


def get_social_bios(social_links_dict: dict) -> dict:
    """Attempts to scrape social media bios (experimental)."""
    print("\nAttempting to fetch social media bios (experimental)...")
    bios_found = {}
    if not social_links_dict: return {}

    for platform, url in social_links_dict.items():
        print(f"--> Attempting bio scrape for {platform}: {url}")
        soup = _fetch_page(url)
        if not soup: continue
        bio_text = None
        try:
            # Platform-Specific Selector Logic (Highly Likely to Need Updates)
            if platform == 'LinkedIn':
                 possible_selectors = ['section.pv-about-section p','p.org-top-card-summary__tagline','div.org-top-card-summary-info-list__info-item','section[class*="summary"] p','div[class*="description"] p','h1[class*="top-card__title"]','h2[class*="top-card__headline"]']
                 found_text = [el.get_text(separator=' ', strip=True) for sel in possible_selectors for el in soup.select(sel) if el.get_text(strip=True) and len(el.get_text(strip=True)) > 10]
                 if found_text: bio_text = " | ".join(list(dict.fromkeys(found_text)))
            elif platform == 'Twitter':
                possible_selectors = ['div[data-testid="UserDescription"]','div[data-testid="UserProfileHeader_bio"]']
                found_text = [el.get_text(separator=' ', strip=True) for sel in possible_selectors if (el := soup.select_one(sel)) and el.get_text(strip=True)]
                if found_text: bio_text = " | ".join(list(dict.fromkeys(found_text)))
            elif platform == 'Facebook':
                meta_desc = soup.find('meta', property='og:description')
                if meta_desc and meta_desc.get('content'): bio_text = meta_desc['content'].strip()
                else:
                    title = soup.find('title')
                    if title and title.string: bio_text = title.string.strip()
            elif platform == 'YouTube':
                 possible_selectors = ['meta[property="og:description"]','meta[name="description"]','#description.ytd-channel-about-metadata-renderer','yt-formatted-string#description']
                 found_text = []
                 for selector in possible_selectors:
                     element = soup.select_one(selector)
                     if element:
                         text = element.get('content', '').strip() if element.name == 'meta' else element.get_text(separator=' ', strip=True)
                         if text and len(text) > 10: found_text.append(text)
                 if found_text: bio_text = " | ".join(list(dict.fromkeys(found_text)))

            if bio_text:
                cleaned_bio = re.sub(r'http\S+', '', bio_text)
                cleaned_bio = re.sub(r'\s+', ' ', cleaned_bio).strip()
                if cleaned_bio and len(cleaned_bio) > 10:
                    print(f"  [✓] Extracted potential bio for {platform}.")
                    bios_found[platform] = cleaned_bio
                elif bio_text:
                     print(f"  [✓] Extracted potential bio for {platform} (original).")
                     bios_found[platform] = bio_text.strip()
                else: print(f"  [!] Found element for {platform}, but text empty/short.")
            else: print(f"  [!] Could not find bio element for {platform}.")
        except Exception as e:
            print(f"  [!] Error parsing bio for {platform}: {e}")

    if bios_found: print(f"\nFinished social bio scraping. Found: {list(bios_found.keys())}")
    else: print("Finished social bio scraping. No bios extracted.")
    return bios_found


# --- Main Execution Block Removed ---
# The workflow is now orchestrated by modules/__init__.py
# You can test individual functions by importing them in a separate test script or Python console.

