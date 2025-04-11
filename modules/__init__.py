# modules/__init__.py
# Orchestrates the scraping, analysis, and generation pipeline via direct function calls.
# *** Includes fix for TypeError in analyze_content call ***

import json
import os
import traceback
from urllib.parse import urlparse
import re # Needed for filename sanitization
import logging # Use logging for better status messages

# --- Import functions from sibling modules ---
try:
    # *** Make sure get_social_bios is imported if you intend to use it ***
    from .scraper import find_social_links, get_website_text, get_social_bios
    logging.info("✅ Scraper functions imported successfully.")
except ImportError as e:
    logging.error(f"❌ Error importing from .scraper: {e}")
    raise # Re-raise error to stop Streamlit app if core components missing

try:
    # *** ASSUMPTION: You have an analyzer.py with analyze_content function ***
    # This function definition likely looks like: def analyze_content(website_text, social_bios_dict):
    from .analyzer import analyze_content
    logging.info("✅ Analyzer function imported successfully.")
except ImportError as e:
    logging.warning(f"⚠️ Warning: Could not import from .analyzer: {e}")
    logging.warning("Analysis step will be skipped.")
    # Define a dummy function if analyzer is missing, so pipeline doesn't crash
    def analyze_content(website_text, social_bios_dict): # Match expected signature
        logging.warning("Using dummy analyze_content function.")
        return {"keywords": ["N/A"], "sentiment": {"label": "Unavailable", "score": 0.0}, "error": "Analyzer module not found"}

try:
    from .generator import generate_brand_story # Imports the main function from generator.py
    logging.info("✅ Generator function imported successfully.")
except ImportError as e:
    logging.error(f"❌ Error importing from .generator: {e}")
    raise # Re-raise error

# --- Configuration ---
# No longer need fixed intermediate filename for this flow

# --- Main Pipeline Function (Refactored) ---
def run_full_pipeline(target_url: str) -> dict:
    """
    Runs the full scrape -> analyze -> generate pipeline for a given URL
    using direct function calls and returns results in a dictionary.

    Args:
        target_url: The company website URL to process.

    Returns:
        A dictionary containing results.
    """
    print("="*50)
    print(f"🚀 Starting Full Pipeline for: {target_url}")
    print("="*50)

    pipeline_results = {
        "success": False, # Overall success flag
        "message": "Pipeline started.",
        "source_url": target_url,
        "social_links": {},
        "website_text": None,
        "analysis": None,
        "story": None
        # You might want to add social_bios to the results dict too
        # "social_bios": {}
    }
    social_bios = {} # Initialize social_bios dict here

    # --- Step 1: Scraping ---
    print("\n--- Phase 1: Scraping ---")
    try:
        print("  Running find_social_links...")
        pipeline_results["social_links"] = find_social_links(target_url) or {} # Ensure dict
        print("  Running get_website_text...")
        pipeline_results["website_text"] = get_website_text(target_url) # Returns text or None

        # *** Ensure get_social_bios is called if links exist ***
        if pipeline_results["social_links"]:
             print("  Running get_social_bios...")
             social_bios = get_social_bios(pipeline_results["social_links"]) # Assign to local variable
             # pipeline_results["social_bios"] = social_bios # Optionally store in main results
        else:
             print("  Skipping get_social_bios (no links found).")
        # *** End change ***

        if pipeline_results["website_text"] is None and not pipeline_results["social_links"]:
             raise ValueError("Failed to retrieve website text and social links.")

        print("✅ Scraping phase complete.")
        pipeline_results["message"] = "Scraping complete."

    except Exception as e:
        print(f"❌ Error during scraping phase: {e}")
        traceback.print_exc()
        pipeline_results["message"] = f"Scraping failed: {e}"
        return pipeline_results # Exit early if scraping fails critically

    # --- Step 2: Analysis ---
    # Only proceed if we have some text to analyze
    if pipeline_results["website_text"]:
        print("\n--- Phase 2: Analyzing Content ---")
        try:
            # *** Modify the call to analyze_content ***
            # Pass website_text and social_bios as separate arguments
            pipeline_results["analysis"] = analyze_content(
                pipeline_results["website_text"], # First argument
                social_bios                     # Second argument (using the variable populated above)
            )
            # *** End modification ***

            print("✅ Analysis phase complete.")
            pipeline_results["message"] = "Analysis complete."
        except Exception as e:
            print(f"❌ Error during analysis phase: {e}")
            traceback.print_exc()
            pipeline_results["message"] = f"Analysis failed: {e}"
            # Set analysis to None or an error dict if needed downstream
            pipeline_results["analysis"] = {"error": f"Analysis failed: {e}"}
    else:
        print("🟡 Skipping analysis phase (no website text found).")
        pipeline_results["message"] = "Scraping yielded no text for analysis."


    # --- Step 3: Generation ---
    print("\n--- Phase 3: Generating Story ---")
    # Check if analysis results exist AND don't contain an error key we might have added
    if pipeline_results["analysis"] is not None and not pipeline_results["analysis"].get("error"):
         try:
             pipeline_results["story"] = generate_brand_story(pipeline_results["analysis"])
             if pipeline_results["story"]:
                 print("✅ Generation phase complete.")
                 pipeline_results["message"] = "Story generated successfully."
                 pipeline_results["success"] = True # Mark overall success
             else:
                  print("⚠️ Generation phase completed, but no story was returned (check logs/API keys).")
                  pipeline_results["message"] = "Generation failed to produce a story."

         except Exception as e:
             print(f"❌ Error during generation phase: {e}")
             traceback.print_exc()
             pipeline_results["message"] = f"Story generation failed: {e}"
    else:
        # Handle cases where analysis was skipped or failed
        if pipeline_results["analysis"] and pipeline_results["analysis"].get("error"):
             print("🟡 Skipping generation phase (Analysis step failed).")
             # Keep the analysis error message
             pipeline_results["message"] = pipeline_results["analysis"].get("error", "Analysis failed, cannot generate story.")
        else: # Analysis was skipped due to no text
             print("🟡 Skipping generation phase (no analysis results available).")
             pipeline_results["message"] = "Analysis results missing, cannot generate story."


    # --- Pipeline End ---
    print("\n" + "="*50)
    print(f"🏁 Pipeline Finished: Success={pipeline_results['success']}, Message='{pipeline_results['message']}'")
    print("="*50)

    return pipeline_results

