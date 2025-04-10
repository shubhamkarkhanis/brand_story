# run_analysis.py

import json
import os
import traceback

try:
    from modules.analyzer import analyze_content
except ImportError as e:
    print(f"❌ Error importing analyzer: {e}")
    print("Make sure 'run_analysis.py' is in the project root and 'analyzer.py' is in the 'modules' folder.")
    exit()

# --- Configuration ---
DEFAULT_JSON_INPUT_FILE = 'flipkart.com_scraped_data.json'
DEFAULT_JSON_OUTPUT_FILE = 'analysis_results1.json'
NUM_KEYWORDS_TO_EXTRACT = 100 # <--- Keep desired number of keywords
# Removed: NUM_SUMMARY_SENTENCES constant

# --- Function to Load and Process (Modified - Summary Removed) ---
def load_and_analyze_from_json(json_file_path: str, num_keywords: int): # Removed num_summary_sentences
    """
    Loads scraped data, runs analysis requesting specific numbers of keywords.
    Returns the FULL analysis dictionary or None on error.
    """
    print(f"Attempting to load data from: {json_file_path}")
    # ... (rest of loading logic remains the same) ...
    if not os.path.exists(json_file_path):
        print(f"❌ Error: JSON file not found at '{json_file_path}'")
        return None
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        print("✅ JSON file loaded successfully.")

        website_text = scraped_data.get('website_text')
        social_bios = scraped_data.get('social_bios')

        if not website_text: print("🟡 Info: No 'website_text' found or it's empty.")
        if not social_bios: print("🟡 Info: No 'social_bios' found or it's empty.")
        elif not isinstance(social_bios, dict):
             print(f"🟡 Warning: 'social_bios' in JSON is not a dictionary (type: {type(social_bios)}). Passing None.")
             social_bios = None

        print(f"\n🚀 Running content analysis (requesting {num_keywords} keywords)...") # Updated log message
        # *** Call analyze_content without summary param ***
        full_analysis_results = analyze_content(
            website_text,
            social_bios,
            num_keywords=num_keywords
            # Removed: num_summary_sentences argument
        )
        print("✅ Analysis complete.")
        return full_analysis_results

    except json.JSONDecodeError:
        print(f"❌ Error: Failed to decode JSON from '{json_file_path}'. Check format.")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during loading/analysis: {e}")
        traceback.print_exc()
        return None

# --- Function to Save Filtered Results (Keep as before) ---
def save_filtered_results_to_json(results_to_save: dict, output_file_path: str):
    """ Saves the provided (already filtered) dictionary to a JSON file. """
    print(f"\n💾 Attempting to save filtered results to: {output_file_path}")
    # ... (saving logic remains the same) ...
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(results_to_save, f, ensure_ascii=False, indent=4)
        print(f"✅ Filtered results successfully saved to '{output_file_path}'.")
        return True
    except Exception as e:
        print(f"❌ Error saving results to JSON: {e}")
        traceback.print_exc()
        return False


# --- Main Execution (Modified - Summary Removed) ---
if __name__ == "__main__":
    input_file = DEFAULT_JSON_INPUT_FILE
    output_file = DEFAULT_JSON_OUTPUT_FILE

    # 1. Load data and run analysis (passing only keyword count)
    full_analysis_results = load_and_analyze_from_json(
        input_file,
        num_keywords=NUM_KEYWORDS_TO_EXTRACT
        # Removed: num_summary_sentences argument
    )

    # 2. Proceed only if analysis was successful
    if full_analysis_results:
        print("\n--- 📊 Full Analysis Results (Console Preview) ---")
        # Print a summary of the full results to the console for review
        print(f"🔑 Keywords ({len(full_analysis_results.get('keywords', []))}/{NUM_KEYWORDS_TO_EXTRACT} requested): {full_analysis_results.get('keywords', 'N/A')[:15]}...") # Show first few
        sentiment_info = full_analysis_results.get('sentiment', {})
        print(f"😊 Sentiment: Label='{sentiment_info.get('label', 'N/A')}', Score={sentiment_info.get('score', 'N/A'):.4f}")
        # Removed: Summary printout
        source_keys = list(full_analysis_results.get('source_texts', {}).keys())
        print(f"📚 Sources Used (in analysis): {source_keys if source_keys else 'None'}")

        # 3. *** Create the filtered dictionary for saving (Keywords + Sentiment ONLY) ***
        results_for_llm = {
            'keywords': full_analysis_results.get('keywords', []),
            'sentiment': full_analysis_results.get('sentiment', {'label': 'Neutral', 'score': 0.0})
            # Removed: 'summary' key
        }
        print("\n--- Filtering results for LLM output file (keywords, sentiment only) ---")

        # 4. Save ONLY the filtered results to the output JSON file
        save_successful = save_filtered_results_to_json(results_for_llm, output_file)

        if not save_successful:
            print("\n⚠️ Failed to save filtered results to JSON file.")

    else:
        print("\n--- Analysis Failed ---")
        print("No output file generated. Please check errors above.")