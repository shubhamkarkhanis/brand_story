# modules/__init__.py

import json
import os
import subprocess
import sys
import traceback
from urllib.parse import urlparse
import re # Needed for filename sanitization

# --- Import functions from sibling modules using relative imports ---
try:
    from .scraper import find_social_links, get_website_text, get_social_bios
    print("✅ Scraper functions imported successfully.")
except ImportError as e:
    print(f"❌ Error importing from .scraper: {e}")
    print("Ensure scraper.py is in the 'modules' directory.")
    # Decide if you want to exit or handle this differently
    # exit()

# --- Configuration ---
OUTPUT_FILENAME = "input_file.json" # Fixed intermediate filename

# --- Helper to create safe filename (if needed, though fixed name is used here) ---
def create_safe_filename_from_url(url: str) -> str:
    """Generates a safe filename from a URL, typically based on the domain."""
    try:
        domain_name = urlparse(url).netloc.replace('www.', '')
        safe_name = re.sub(r'[^\w\-]+', '_', domain_name)
        return f"{safe_name}.json" if safe_name else "unknown_domain.json"
    except Exception:
        return f"scraped_url_{hash(url)}.json"

# --- Main Pipeline Function ---
def run_full_pipeline(target_url: str):
    """
    Runs the full scrape -> analyze -> generate pipeline for a given URL.

    Args:
        target_url: The company website URL to process.
    """
    print("="*50)
    print(f"🚀 Starting Full Pipeline for: {target_url}")
    print("="*50)

    # --- Step 1: Scraping ---
    print("\n--- Phase 1: Scraping ---")
    scraped_data = {
        "source_url": target_url,
        "social_links": {},
        "website_text": None,
        "social_bios": {}
    }
    scrape_successful = True # Assume success initially

    try:
        print("  Running find_social_links...")
        scraped_data["social_links"] = find_social_links(target_url)
        print("  Running get_website_text...")
        scraped_data["website_text"] = get_website_text(target_url)
        if scraped_data["social_links"] and isinstance(scraped_data["social_links"], dict):
             print("  Running get_social_bios...")
             scraped_data["social_bios"] = get_social_bios(scraped_data["social_links"])
        else:
             print("  Skipping get_social_bios (no links found).")
        print("✅ Scraping phase complete.")
    except Exception as e:
        print(f"❌ Error during scraping phase: {e}")
        traceback.print_exc()
        scrape_successful = False

    # --- Step 2: Save Scraped Data ---
    print("\n--- Phase 2: Saving Scraped Data ---")
    output_filepath = os.path.abspath(OUTPUT_FILENAME) # Use absolute path from CWD
    saved_successfully = False
    if scrape_successful:
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(scraped_data, f, ensure_ascii=False, indent=4)
            print(f"✅ Scraped data successfully saved to: {output_filepath}")
            saved_successfully = True
        except Exception as e:
            print(f"❌ Error saving scraped data to '{output_filepath}': {e}")
            traceback.print_exc()
    else:
        print("🟡 Skipping save due to scraping errors.")

    # --- Step 3: Run Analysis Script ---
    analysis_ok = False
    if saved_successfully: # Only run analysis if scraping and saving worked
        print("\n--- Phase 3: Triggering Analysis Script ---")
        # Assuming run_analysis.py is in the 'modules' subdirectory
        analysis_script_path = os.path.join("modules", "run_analysis.py")
        analysis_command = [sys.executable, analysis_script_path]
        print(f"  Running command: {' '.join(analysis_command)}")
        try:
            # Run analysis, wait for completion, check for errors
            analysis_result = subprocess.run(analysis_command, check=True, capture_output=True, text=True, encoding='utf-8', cwd='.') # Run from project root
            print(f"✅ {analysis_script_path} executed successfully.")
            analysis_ok = True
            if analysis_result.stdout:
                print("  --- Analysis Script Output ---")
                print(analysis_result.stdout.strip())
                print("  ----------------------------")
        except FileNotFoundError:
            print(f"❌ Error: Analysis script not found at '{analysis_script_path}' (relative to project root).")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {analysis_script_path} failed with exit code {e.returncode}.")
            if e.stdout: print(f"     Output:\n{e.stdout.strip()}")
            if e.stderr: print(f"     Error Output:\n{e.stderr.strip()}")
        except Exception as e:
            print(f"❌ An unexpected error occurred while running {analysis_script_path}: {e}")
            traceback.print_exc()
    else:
        print("🟡 Skipping analysis due to previous errors.")

    # --- Step 4: Run Generator Script ---
    generator_ok = False
    if analysis_ok: # Only run generator if analysis was successful
        print("\n--- Phase 4: Triggering Generator Script ---")
        # Assuming generator.py is in the 'modules' subdirectory
        generator_script_path = os.path.join("modules", "generator.py")
        # Pass the fixed filename as a command-line argument
        generator_command = [sys.executable, generator_script_path, OUTPUT_FILENAME]
        print(f"  Running command: {' '.join(generator_command)}")
        try:
            # Run generator, wait for completion, check for errors
            generator_result = subprocess.run(generator_command, check=True, capture_output=True, text=True, encoding='utf-8', cwd='.') # Run from project root
            print(f"✅ {generator_script_path} executed successfully.")
            generator_ok = True
            if generator_result.stdout:
                print("  --- Generator Script Output ---")
                print(generator_result.stdout.strip())
                print("  -----------------------------")
        except FileNotFoundError:
            print(f"❌ Error: Generator script not found at '{generator_script_path}' (relative to project root).")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {generator_script_path} failed with exit code {e.returncode}.")
            if e.stdout: print(f"     Output:\n{e.stdout.strip()}")
            if e.stderr: print(f"     Error Output:\n{e.stderr.strip()}")
        except Exception as e:
            print(f"❌ An unexpected error occurred while running {generator_script_path}: {e}")
            traceback.print_exc()
    else:
         print("\n🟡 Skipping Generation: Analysis script did not complete successfully.")

    # --- Pipeline End ---
    print("\n" + "="*50)
    if generator_ok:
        print("✅ Full Pipeline Completed Successfully!")
    elif analysis_ok:
        print("⚠️ Pipeline Completed Analysis, but Generator Failed.")
    elif saved_successfully:
         print("❌ Pipeline Failed during Analysis.")
    else:
         print("❌ Pipeline Failed during Scraping or Saving.")
    print("="*50)

# Example of how to call this from another script (e.g., app.py or a main runner script)
# if __name__ == '__main__':
#     test_url = "https://streamlit.io/"
#     run_full_pipeline(test_url)

