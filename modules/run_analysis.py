# run_analysis.py
# Reads input JSON, runs analysis, and OVERWRITES the input JSON
# with url, social_links, keywords, and sentiment.

import json
import os
import traceback

try:
    # Ensure analyzer provides the analyze_content function
    from analyzer import analyze_content
except ImportError as e:
    print(f"❌ Error importing analyzer: {e}")
    print("Make sure 'run_analysis.py' is in the project root and 'analyzer.py' is in the 'modules' folder.")
    exit()

# --- Configuration ---
# *** This is now the file to READ from AND WRITE to ***
TARGET_JSON_FILE = 'amazon.com_scraped_data.json'
NUM_KEYWORDS_TO_EXTRACT = 100 # Adjust as needed

# --- Main Processing Logic ---
def process_and_overwrite_json(json_file_path: str, num_keywords: int):
    """
    Loads data from json_file_path, analyzes it, and overwrites the same file
    with structured results (URL, links, keywords, sentiment).
    """
    print(f"🔄 Processing file: {json_file_path}")

    # 1. Load the original data
    if not os.path.exists(json_file_path):
        print(f"❌ Error: Input JSON file not found at '{json_file_path}'")
        return False
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        print("✅ Original JSON data loaded successfully.")
    except json.JSONDecodeError:
        print(f"❌ Error: Failed to decode JSON from '{json_file_path}'. Check format.")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred during loading: {e}")
        traceback.print_exc()
        return False

    # 2. Extract necessary fields for analysis (use .get for safety)
    website_text = original_data.get('website_text') # Assuming this key exists
    social_bios = original_data.get('social_bios')   # Assuming this key exists

    # Extract fields to keep in the final output (use .get with defaults)
    source_url_to_keep = original_data.get('source_url', None) # ** MUST EXIST IN INPUT **
    social_links_to_keep = original_data.get('social_links', []) # ** MUST EXIST IN INPUT **

    # Optional: Check if required fields are present
    if source_url_to_keep is None:
        print("🟡 Warning: 'source_url' key not found in input JSON. It will be missing from the output.")
    if not social_links_to_keep:
        print("🟡 Warning: 'social_links' key not found or empty in input JSON.")


    # 3. Run the analysis
    print(f"\n🚀 Running content analysis (requesting {num_keywords} keywords)...")
    try:
        # Call the analyzer function from modules/analyzer.py
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
    # Only include the specifically requested fields
    output_data = {
        'source_url': source_url_to_keep,
        'social_links': social_links_to_keep,
        'keywords': analysis_results.get('keywords', []), # Get keywords from analysis
        'sentiment': analysis_results.get('sentiment', {'label': 'Neutral', 'score': 0.0}) # Get sentiment
    }
    print("\n✨ Final data structure prepared:")
    # Preview keys and types for confirmation
    for key, value in output_data.items():
         print(f"  - {key}: (Type: {type(value).__name__})")


    # 5. Overwrite the original file
    print(f"\n💾 Attempting to overwrite '{json_file_path}' with processed data...")
    try:
        # Open the *same file path* in write mode ('w')
        with open(json_file_path, 'w', encoding='utf-8') as f:
            # Dump the new 'output_data' dictionary
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Successfully updated '{json_file_path}'.")
        return True # Indicate success
    except IOError as e:
        print(f"❌ Error: Could not write to file '{json_file_path}'. Check permissions.")
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


# --- Main Execution ---
if __name__ == "__main__":
    success = process_and_overwrite_json(
        TARGET_JSON_FILE,
        num_keywords=NUM_KEYWORDS_TO_EXTRACT
    )

    if success:
        print("\n--- Processing Finished Successfully ---")
    else:
        print("\n--- Processing Failed ---")
        print(f"Please check errors above. '{TARGET_JSON_FILE}' might be unchanged or corrupted.")