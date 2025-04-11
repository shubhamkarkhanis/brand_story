# run_analysis.py
# Reads input JSON, runs analysis, OVERWRITES the input JSON
# with url, social_links, keywords, and sentiment.
# NOTE: Triggering generator.py is now handled by modules/__init__.py

import json
import os
import traceback
# Removed subprocess and sys imports as generator call is moved

try:
    # Ensure analyzer provides the analyze_content function
    # Use relative import since both scripts are in 'modules'
    from analyzer import analyze_content
except ImportError as e:
    print(f"❌ Error importing analyzer: {e}")
    print("Make sure 'run_analysis.py' and 'analyzer.py' are both inside the 'modules' directory.")
    print("This script ('run_analysis.py') is typically called from the project root directory.")
    exit()

# --- Configuration ---
# This is the file to READ from AND WRITE to
# Assumes input_file.json is in the directory where the calling script was run (project root)
TARGET_JSON_FILE = 'input_file.json'
NUM_KEYWORDS_TO_EXTRACT = 100 # Adjust as needed

# --- Main Processing Logic ---
def process_and_overwrite_json(json_file_path: str, num_keywords: int):
    """
    Loads data from json_file_path, analyzes it, and overwrites the same file
    with structured results (URL, links, keywords, sentiment).
    """
    print(f"🔄 Processing file: {json_file_path}")
    analysis_successful = False # Flag for successful analysis & overwrite

    # 1. Load the original data
    abs_json_file_path = os.path.abspath(json_file_path)
    if not os.path.exists(abs_json_file_path):
        print(f"❌ Error: Input JSON file not found at '{abs_json_file_path}'")
        return False
    try:
        with open(abs_json_file_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        print("✅ Original JSON data loaded successfully.")
    except json.JSONDecodeError:
        print(f"❌ Error: Failed to decode JSON from '{abs_json_file_path}'. Check format.")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred during loading: {e}")
        traceback.print_exc()
        return False

    # 2. Extract necessary fields for analysis
    website_text = original_data.get('website_text')
    social_bios = original_data.get('social_bios')
    source_url_to_keep = original_data.get('source_url', None)
    social_links_to_keep = original_data.get('social_links', {})

    # 3. Run the analysis
    print(f"\n🚀 Running content analysis (requesting {num_keywords} keywords)...")
    try:
        analysis_results = analyze_content(
            website_text,
            social_bios,
            num_keywords=num_keywords
        )
        print("✅ Analysis complete.")
    except Exception as e:
        print(f"❌ An unexpected error occurred during analysis: {e}")
        traceback.print_exc()
        return False # Stop processing if analysis fails

    # 4. Construct the final dictionary for output
    output_data = {
        'source_url': source_url_to_keep,
        'social_links': social_links_to_keep,
        'keywords': analysis_results.get('keywords', []),
        'sentiment': analysis_results.get('sentiment', {'label': 'Neutral', 'score': 0.0})
    }
    print("\n✨ Analysis data structure prepared:")
    for key, value in output_data.items():
         print(f"  - {key}: (Type: {type(value).__name__})")

    # 5. Overwrite the original file
    print(f"\n💾 Attempting to overwrite '{abs_json_file_path}' with processed data...")
    try:
        with open(abs_json_file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Successfully updated '{abs_json_file_path}'.")
        analysis_successful = True # Mark analysis and save as successful
    except IOError as e:
        print(f"❌ Error: Could not write to file '{abs_json_file_path}'. Check permissions.")
        print(f"   Error details: {e}")
        return False
    except TypeError as e:
        print(f"❌ Error: The final dictionary could not be serialized to JSON.")
        print(f"   Check data types. Error: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred during file writing: {e}")
        traceback.print_exc()
        return False

    # 6. ***** Trigger generator.py step REMOVED *****
    # This is now handled by modules/__init__.py

    return analysis_successful # Return True if analysis & overwrite succeeded


# --- Main Execution ---
if __name__ == "__main__":
    # This block allows testing run_analysis.py independently,
    # assuming input_file.json already exists in the current directory.
    print(f"--- Starting Standalone Analysis for {TARGET_JSON_FILE} ---")
    success = process_and_overwrite_json(
        TARGET_JSON_FILE,
        num_keywords=NUM_KEYWORDS_TO_EXTRACT
    )
    if success:
        print("\n--- Standalone Analysis Finished Successfully ---")
    else:
        print("\n--- Standalone Analysis Failed ---")

