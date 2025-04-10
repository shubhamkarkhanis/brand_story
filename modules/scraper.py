# modules/scraper.py
# Contains functions for scraping website content and social media links/bios.

import requests # For making HTTP requests
from bs4 import BeautifulSoup # For parsing HTML content
import re # For regular expressions (finding patterns in links and text)
from urllib.parse import urljoin, urlparse # For handling relative URLs
import json # ***** Added for JSON output *****
import os # ***** Added to help with filename generation *****

# --- Constants ---

# Define patterns for common social media links using regular expressions
# These help ensure we grab actual profile links, not just mentions.
SOCIAL_MEDIA_PATTERNS = {
    'LinkedIn': re.compile(r'https?://(www\.)?linkedin\.com/(company|in)/[\w-]+/?'),
    'Twitter': re.compile(r'https?://(www\.)?(twitter|x)\.com/\w+/?(?!\w)'), # Added 'x.com', avoid status links
    'Facebook': re.compile(r'https?://(www\.)?facebook\.com/[\w.-]+/?'),
    'Instagram': re.compile(r'https?://(www\.)?instagram\.com/[\w.]+/'),
    'YouTube': re.compile(r'https?://(www\.)?youtube\.com/(user|channel|c)/[\w-]+/?'),
    # Add more patterns here if needed (e.g., Pinterest, TikTok)
    # 'Pinterest': re.compile(r'https?://(www\.)?pinterest\.com/\w+/?'),
}

# Standard User-Agent to mimic a browser, reducing chances of being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Helper Function ---

def _fetch_page(url: str) -> BeautifulSoup | None:
    """
    Helper function to fetch content from a URL and parse it with BeautifulSoup.
    Includes basic error handling and content type check.

    Args:
        url: The URL to fetch.

    Returns:
        A BeautifulSoup object if successful and content is HTML, otherwise None.
    """
    # Add basic URL validation
    if not url.startswith(('http://', 'https://')):
        print(f"Error: Invalid URL format. Please include http:// or https://. URL: {url}")
        return None

    print(f"--> Fetching page: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15) # Timeout after 15 seconds
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Check if the content type is HTML before parsing
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            print(f"Warning: Content-Type is not HTML for {url} (was: {content_type})")
            return None

        # Use html.parser (built-in), consider 'lxml' if installed (often faster)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup

    except requests.exceptions.Timeout:
        print(f"Error: Request timed out for {url}")
        return None
    except requests.exceptions.MissingSchema:
         print(f"Error: Invalid URL format (perhaps missing http:// or https://). URL: {url}")
         return None
    except requests.exceptions.HTTPError as http_err:
        print(f"Error: HTTP error occurred for {url}: {http_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Error: Request exception occurred for {url}: {req_err}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during fetching/parsing
        print(f"An unexpected error occurred fetching/parsing {url}: {e}")
        return None

# --- Core Scraping Functions ---

def find_social_links(base_url: str) -> dict:
    """
    Crawls a base URL and common pages (/about, /contact) to find social media links.
    Handles relative URLs and checks against predefined patterns.

    Args:
        base_url: The base URL of the website (e.g., https://www.example.com).

    Returns:
        A dictionary where keys are social media platform names (e.g., 'LinkedIn')
        and values are the found URLs. Returns an empty dict if errors occur or no links found.
    """
    print(f"\nStarting social link search for: {base_url}")
    social_links_found = {}

    # Validate and normalize base URL
    try:
        parsed_base = urlparse(base_url)
        if not parsed_base.scheme or not parsed_base.netloc:
            print(f"Error: Invalid base URL format provided: {base_url}")
            return {}
        # Ensure base_url ends with '/' for urljoin to work correctly
        base_url_normalized = f"{parsed_base.scheme}://{parsed_base.netloc}/"
    except Exception as e:
        print(f"Error parsing base URL {base_url}: {e}")
        return {}


    # Define pages to check (homepage + common contact/about pages)
    pages_to_check = [base_url_normalized]
    common_paths = ['/about', '/contact', '/about-us', '/contact-us']
    for path in common_paths:
        # Construct full URLs carefully
        try:
            # Use urljoin to handle potential relative paths correctly
            full_path_url = urljoin(base_url_normalized, path)
            pages_to_check.append(full_path_url)
        except Exception as e:
            print(f"Warning: Could not construct URL for path '{path}' on base {base_url_normalized}: {e}")


    # Remove duplicates that might arise from base_url being one of the common paths
    pages_to_check = sorted(list(dict.fromkeys(pages_to_check)))

    processed_hrefs = set() # Keep track of unique absolute URLs checked to avoid redundant checks

    for page_url in pages_to_check:
        # Optimization: If we've found links for all platforms we target, stop early.
        if len(social_links_found) >= len(SOCIAL_MEDIA_PATTERNS):
            print("Found links for all targeted platforms, stopping search.")
            break

        soup = _fetch_page(page_url)
        if not soup:
            # Error fetching or non-HTML content, message printed in _fetch_page
            continue # Skip to the next page

        print(f"Searching for links on: {page_url}")
        # Find all anchor tags with an 'href' attribute
        all_links = soup.find_all('a', href=True)
        print(f"Found {len(all_links)} potential links on this page.")

        for link in all_links:
            href = link.get('href', '').strip()

            # Skip empty links, anchors, mailto, tel links etc.
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                continue

            # Resolve relative URLs to absolute URLs using the page's URL
            try:
                absolute_href = urljoin(page_url, href)
            except Exception as e:
                print(f"Warning: Could not resolve relative URL '{href}' on page {page_url}: {e}")
                continue # Skip this link if resolution fails

            # Clean up potential tracking parameters (basic example)
            try:
                parsed_href = urlparse(absolute_href)
                # Reconstruct without query params or fragment
                clean_href = f"{parsed_href.scheme}://{parsed_href.netloc}{parsed_href.path}"
                # Remove trailing slash if present for consistent matching
                if clean_href.endswith('/'):
                    clean_href = clean_href[:-1]
            except Exception as e:
                 print(f"Warning: Could not parse or clean URL '{absolute_href}': {e}")
                 clean_href = absolute_href # Use original absolute if parsing fails

            if clean_href in processed_hrefs:
                continue # Already processed this link
            processed_hrefs.add(clean_href)

            # Check the cleaned, absolute URL against social media patterns
            for platform, pattern in SOCIAL_MEDIA_PATTERNS.items():
                 # Important: Only add if we haven't found a link for this platform yet
                if platform not in social_links_found:
                    # Use re.match which checks from the beginning of the string
                    if pattern.match(clean_href): # Match against the cleaned href
                        print(f"  [✓] Found {platform}: {clean_href}")
                        social_links_found[platform] = clean_href
                        # Once matched, no need to check this link against other patterns
                        break

    # --- Reporting Results ---
    if not social_links_found:
        print(f"Finished searching. No social media links found matching patterns for {base_url}")
    else:
        print(f"\nFinished searching for {base_url}. Found links:")
        for platform, link in social_links_found.items():
            print(f"  - {platform}: {link}")

    return social_links_found


def get_website_text(url: str) -> str | None:
    """
    Fetches and extracts the main textual content from a given website URL.
    Prioritizes title, meta description, and common content tags (p, h1, h2, etc.).
    Includes basic cleaning and fallback to grabbing all text if specific tags fail.

    Args:
        url: The URL of the website page to extract text from.

    Returns:
        A single string containing the extracted and cleaned text, or None if an error occurs.
    """
    print(f"\nAttempting to fetch website text from: {url}")
    soup = _fetch_page(url)
    if not soup:
        return None # Error message handled in _fetch_page

    extracted_texts = []

    # 1. Extract Title tag
    title = soup.find('title')
    if title and title.string:
        title_text = title.string.strip()
        if title_text:
            print(f"  [i] Found Title: {title_text}")
            extracted_texts.append(title_text)

    # 2. Extract Meta Description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        desc_text = meta_desc['content'].strip()
        if desc_text:
            print(f"  [i] Found Meta Description: {desc_text[:150]}...") # Preview
            extracted_texts.append(desc_text)

    # 3. Extract from common content tags
    # More robust approach might involve libraries like 'trafilatura' or 'goose3'
    # but this uses only BeautifulSoup for simplicity.
    content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'article', 'main', 'section', 'div']) # Added div, might get more noise
    tags_to_ignore_parents = ['nav', 'footer', 'header', 'script', 'style', 'aside', 'form', 'button', 'figure', 'figcaption'] # Added figure/figcaption
    min_text_length = 25 # Increased slightly to filter more UI elements

    print(f"  [i] Found {len(content_tags)} potential content tags (p, h1-h4, article, main, section, div). Filtering...")
    texts_from_tags = set() # Use a set to avoid duplicate text blocks
    for tag in content_tags:
        # Basic check: ignore if tag is inside common non-content parent elements
        is_inside_ignored = False
        # Check direct parent first for speed
        if tag.parent and tag.parent.name in tags_to_ignore_parents:
             continue
        # Check further up if needed (can be slow)
        # for parent in tag.parents:
        #     if parent.name in tags_to_ignore_parents:
        #         is_inside_ignored = True
        #         break
        # if is_inside_ignored:
        #     continue

        # Get text, stripping extra whitespace and joining separated parts
        # Use .get_text() which is generally robust
        text = tag.get_text(separator=' ', strip=True)

        # Filter based on length and avoid script/style content if any slipped through
        if text and len(text) >= min_text_length and '<script' not in text and '<style' not in text:
            # Basic check for excessive non-alphanumeric characters (might indicate code/junk)
            alphanumeric_ratio = sum(c.isalnum() for c in text) / len(text) if len(text) > 0 else 0
            if alphanumeric_ratio > 0.6: # Require at least 60% alphanumeric chars
                 texts_from_tags.add(text)

    if texts_from_tags:
        extracted_texts.extend(list(texts_from_tags)) # Convert set back to list
        print(f"  [i] Extracted {len(texts_from_tags)} unique text blocks from content tags.")
    else:
        print("Warning: Could not extract significant text from common content tags.")

    # --- Fallback and Final Processing ---
    if not extracted_texts:
        print("Warning: No text extracted from title, description, or main tags. Falling back to all body text.")
        # Attempt to get all text from the body, excluding script/style
        body = soup.find('body')
        if body:
            # Remove script and style elements before extracting text
            for element in body(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'figure', 'noscript']): # Added noscript
                element.decompose() # Remove the tag and its content
            all_text = body.get_text(separator=' ', strip=True)
            if all_text:
                 # Basic cleaning on fallback text too
                 all_text = re.sub(r'[ \t]+', ' ', all_text)
                 all_text = re.sub(r'\n{3,}', '\n\n', all_text)
                 extracted_texts.append(all_text.strip())
            else:
                print("Error: Failed to extract any text even from body fallback.")
                return None
        else:
            print("Error: Could not find body tag.")
            return None

    # Join all collected text blocks
    full_text = "\n\n".join(extracted_texts) # Use double newline as separator

    # More aggressive cleaning: replace multiple spaces/tabs/newlines globally
    full_text = re.sub(r'\s+', ' ', full_text).strip()

    print(f"Successfully extracted and cleaned website text ({len(full_text)} chars).")
    return full_text


def get_social_bios(social_links_dict: dict) -> dict:
    """
    Attempts to scrape the bio/description text from social media profile URLs.
    ** This function is highly experimental and prone to breaking due to website changes. **
    It relies on finding specific HTML elements/attributes that might change frequently.

    Args:
        social_links_dict: A dictionary {Platform: URL} from find_social_links.

    Returns:
        A dictionary {Platform: bio_text} for any successfully scraped bios.
    """
    print("\nAttempting to fetch social media bios (experimental & fragile)...")
    bios_found = {}

    if not social_links_dict:
        print("No social media links provided to fetch bios from.")
        return {}

    for platform, url in social_links_dict.items():
        print(f"--> Attempting bio scrape for {platform}: {url}")
        # Add delay between requests to be slightly nicer to servers
        # import time
        # time.sleep(random.uniform(1, 3)) # Consider adding random delay

        soup = _fetch_page(url)
        if not soup:
            print(f"  [!] Failed to fetch page for {platform}, skipping bio.")
            continue # Skip to next platform if page fetch fails

        bio_text = None
        try:
            # --- Platform-Specific Selector Logic ---
            # IMPORTANT: These selectors are GUESSES and WILL LIKELY BREAK.
            # They need verification and updates by inspecting the live social media pages.

            if platform == 'LinkedIn':
                 # LinkedIn is notoriously difficult to scrape without API / JS rendering.
                 # These selectors are very likely to fail or return minimal info.
                 possible_selectors = [
                     'section.pv-about-section p', # Personal profile about text?
                     'p.org-top-card-summary__tagline', # Org tagline?
                     'div.org-top-card-summary-info-list__info-item', # Org info list item?
                     'section[class*="summary"] p', # Paragraph within a summary section?
                     'div[class*="description"] p', # Paragraph within a description div?
                     'h1[class*="top-card__title"]', # Company Name (as fallback?)
                     'h2[class*="top-card__headline"]' # Headline?
                 ]
                 found_text = []
                 for selector in possible_selectors:
                     elements = soup.select(selector) # Use select to get all matches
                     for element in elements:
                         text = element.get_text(separator=' ', strip=True)
                         if text and len(text) > 10: # Basic length check
                             found_text.append(text)
                 if found_text:
                     bio_text = " | ".join(list(dict.fromkeys(found_text))) # Join unique findings

            elif platform == 'Twitter': # Or X
                # Twitter/X heavily relies on JavaScript. Static scraping is very difficult.
                # data-testid might work sometimes but is unreliable.
                possible_selectors = [
                    'div[data-testid="UserDescription"]',
                    'div[data-testid="UserProfileHeader_bio"]' # Older?
                ]
                found_text = []
                for selector in possible_selectors:
                     element = soup.select_one(selector)
                     if element:
                         text = element.get_text(separator=' ', strip=True)
                         if text: found_text.append(text)
                if found_text:
                     bio_text = " | ".join(list(dict.fromkeys(found_text)))


            elif platform == 'Facebook':
                # Facebook is extremely difficult to scrape reliably without API.
                # Class names are often obfuscated and change frequently. JS is required.
                # This section is highly unlikely to work consistently.
                # Try finding meta tags sometimes used for SEO/previews
                meta_desc = soup.find('meta', property='og:description')
                if meta_desc and meta_desc.get('content'):
                    bio_text = meta_desc['content'].strip()
                else:
                    # Fallback to trying title if description fails
                    title = soup.find('title')
                    if title and title.string:
                        bio_text = title.string.strip()


            # Add elif blocks for Instagram, YouTube, etc.
            # Instagram: Almost impossible without JS rendering or private API. Look for meta description.
            # YouTube: Look for channel description in meta tags or specific elements like '#description', '#channel-description'.
            elif platform == 'YouTube':
                 possible_selectors = [
                    'meta[property="og:description"]', # OpenGraph description
                    'meta[name="description"]', # Standard meta description
                    '#description.ytd-channel-about-metadata-renderer', # Specific element ID/class (may change)
                    'yt-formatted-string#description'
                 ]
                 found_text = []
                 for selector in possible_selectors:
                     element = soup.select_one(selector)
                     if element:
                         text = ""
                         if element.name == 'meta':
                             text = element.get('content', '').strip()
                         else:
                             text = element.get_text(separator=' ', strip=True)
                         if text and len(text) > 10:
                             found_text.append(text)
                 if found_text:
                      bio_text = " | ".join(list(dict.fromkeys(found_text)))


            # --- End Platform-Specific Logic ---

            # Clean and validate extracted text
            if bio_text:
                # Remove common boilerplate/links often included in bios
                cleaned_bio = re.sub(r'http\S+', '', bio_text) # Remove URLs
                cleaned_bio = re.sub(r'\s+', ' ', cleaned_bio).strip() # Normalize whitespace

                if cleaned_bio and len(cleaned_bio) > 10: # Ensure it's not just whitespace or short fragments
                    print(f"  [✓] Successfully extracted potential bio for {platform}.")
                    bios_found[platform] = cleaned_bio
                elif bio_text: # Keep original if cleaning removed everything useful
                     print(f"  [✓] Extracted potential bio for {platform} (kept original due to cleaning result).")
                     bios_found[platform] = bio_text.strip() # Keep original but strip ends
                else:
                    print(f"  [!] Found potential bio element for {platform}, but text was empty/short after cleaning.")
            else:
                print(f"  [!] Could not find a matching bio element for {platform} using current selectors/methods.")

        except Exception as e:
            # Catch errors during parsing for a specific platform
            print(f"  [!] An error occurred trying to parse bio for {platform}: {e}")
            # Continue to the next platform

    # --- Reporting Results ---
    if not bios_found:
        print("Finished social bio scraping attempt. No bios extracted (this is common).")
    else:
        print("\nFinished social bio scraping attempt. Successfully extracted potential bios:")
        for platform, bio in bios_found.items():
            print(f"  - {platform}: {bio[:150]}...") # Print longer preview

    return bios_found


# --- Main Execution Block (for testing) ---

if __name__ == '__main__':
    # This block runs only when the script is executed directly (e.g., python modules/scraper.py)
    # It's used for testing the functions in this file.

    # Ensure libraries are installed: pip install requests beautifulsoup4
    # You might need: pip install lxml (optional, potentially faster parser)

    print("="*50)
    print(" SCRAPER MODULE TESTER")
    print("="*50)

    # --- Get URL from User Input ---
    test_company_url = input("Enter the company website URL to test (e.g., https://www.example.com): ").strip()

    if not test_company_url:
        print("No URL entered. Exiting test.")
    else:
        print(f"\nStarting tests for: {test_company_url}\n")
        # Initialize results dictionary
        scraped_data = {
            "source_url": test_company_url,
            "social_links": {},
            "website_text": None,
            "social_bios": {}
        }

        # 1. Test finding social links
        print("\n--- Testing find_social_links ---")
        found_socials = find_social_links(test_company_url)
        scraped_data["social_links"] = found_socials # Store results
        print("-" * 30)

        # 2. Test getting website text
        print("\n--- Testing get_website_text ---")
        # Use the URL provided by the user directly here as well
        website_text = get_website_text(test_company_url)
        scraped_data["website_text"] = website_text # Store results
        if website_text:
            print(f"\nExtracted Website Text Sample (first 500 chars):\n{website_text[:500]}...")
        else:
            print("\nFailed to extract website text.")
        print("-" * 30)

        # 3. Test getting social bios (only if links were found)
        print("\n--- Testing get_social_bios ---")
        if found_socials:
            extracted_bios = get_social_bios(found_socials)
            scraped_data["social_bios"] = extracted_bios # Store results
            if not extracted_bios:
                print("\nNo social bios were successfully extracted with current selectors (as expected for many sites).")
        else:
            print("\nSkipping social bio test as no social links were found initially.")
        print("-" * 30)

        # --- ***** SAVE RESULTS TO JSON FILE ***** ---
        print("\n--- Saving Scraped Data ---")
        # Create a filename based on the domain name
        try:
            domain_name = urlparse(test_company_url).netloc.replace('www.', '')
            # Sanitize domain name for filename (replace dots, etc.)
            safe_filename = "input_file.json"
            output_filepath = os.path.join(".", safe_filename) # Save in current directory

            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(scraped_data, f, ensure_ascii=False, indent=4) # Use indent for readability
            print(f"[✓] Scraped data successfully saved to: {output_filepath}")

        except Exception as e:
            print(f"[!] Error saving data to JSON file: {e}")
            # Optionally print the data to console as a fallback
            # print("\nScraped Data (JSON fallback):")
            # print(json.dumps(scraped_data, indent=4))

        print("-" * 30)

        print("\n" + "="*50)
        print(" SCRAPER MODULE TEST COMPLETE")
        print("="*50)