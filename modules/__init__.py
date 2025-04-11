# modules/__init__.py
# Orchestrates the scraping, analysis, and generation pipeline via direct function calls.
# *** Updated to accept and pass 'desired_tone' ***

import json
import os
import traceback
from urllib.parse import urlparse
import re # Needed for filename sanitization
import logging # Use logging for better status messages

# --- Import functions from sibling modules ---
try:
    # Import necessary functions from scraper module
    from .scraper import find_social_links, get_website_text, get_social_bios
    logging.info("✅ Scraper functions imported successfully.")
except ImportError as e:
    logging.error(f"❌ Error importing from .scraper: {e}")
    raise # Re-raise error to stop Streamlit app if core components missing

try:
    # Import analysis function
    # ASSUMPTION: analyzer.py has: def analyze_content(website_text, social_bios_dict):
    from .analyzer import analyze_content
    logging.info("✅ Analyzer function imported successfully.")
except ImportError as e:
    logging.warning(f"⚠️ Warning: Could not import from .analyzer: {e}")
    logging.warning("Analysis step will be skipped.")
    # Define a dummy function if analyzer is missing to prevent crashes
    def analyze_content(website_text, social_bios_dict): # Match expected signature
        logging.warning("Using dummy analyze_content function.")
        return {"keywords": ["N/A"], "sentiment": {"label": "Unavailable", "score": 0.0}, "error": "Analyzer module not found"}

try:
    # Import the main story generation function
    # ASSUMPTION: generator.py has: def generate_brand_story(analysis_results: dict, desired_tone: str | None = None) -> str:
    from .generator import generate_brand_story
    logging.info("✅ Generator function imported successfully.")
except ImportError as e:
    logging.error(f"❌ Error importing from .generator: {e}")
    raise # Re-raise error

# --- Configuration ---
# Logging setup (optional, can be configured in app.py as well)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Pipeline Function (MODIFIED) ---
# Added 'desired_tone' parameter with a default value of None
def run_full_pipeline(target_url: str, desired_tone: str | None = None) -> dict:
    """
    Runs the full scrape -> analyze -> generate pipeline for a given URL
    using direct function calls and returns results in a dictionary.

    Args:
        target_url: The company website URL to process.
        desired_tone: Optional desired tone for the story generation (e.g., "Formal", "Casual").

    Returns:
        A dictionary containing results including success status, messages,
        scraped data, analysis, and the generated story.
    """
    print("="*50)
    print(f"🚀 Starting Full Pipeline for: {target_url}")
    if desired_tone:
        print(f"🎨 Requested Tone: {desired_tone}")
    print("="*50)

    # Initialize the results dictionary
    pipeline_results = {
        "success": False, # Overall success flag for the entire pipeline run
        "message": "Pipeline started.",
        "source_url": target_url,
        "social_links": {},
        "website_text": None,
        "analysis": None, # To store results from the analysis step
        "story": None,    # To store the final generated story
        "social_bios": {} # Initialize social_bios in results as well
    }
    # Local variable for bios, easier to pass around if needed
    social_bios_data = {}

    # --- Step 1: Scraping ---
    print("\n--- Phase 1: Scraping ---")
    try:
        print("  Running find_social_links...")
        pipeline_results["social_links"] = find_social_links(target_url) or {} # Ensure it's a dict even if None is returned
        print(f"  Found social links: {list(pipeline_results['social_links'].keys())}")

        print("  Running get_website_text...")
        pipeline_results["website_text"] = get_website_text(target_url) # Returns text content or None
        if pipeline_results["website_text"]:
             print(f"  Retrieved website text (Length: {len(pipeline_results['website_text'])} chars).")
        else:
             print("  Could not retrieve website text.")


        # Scrape social bios if links were found
        if pipeline_results["social_links"]:
            print("  Running get_social_bios...")
            social_bios_data = get_social_bios(pipeline_results["social_links"])
            pipeline_results["social_bios"] = social_bios_data # Store bios in results
            print(f"  Retrieved social bios for: {list(social_bios_data.keys())}")
        else:
            print("  Skipping get_social_bios (no links found).")

        # Check if any content was retrieved at all
        if pipeline_results["website_text"] is None and not social_bios_data:
            raise ValueError("Failed to retrieve any content (neither website text nor social bios).")

        print("✅ Scraping phase complete.")
        pipeline_results["message"] = "Scraping complete."

    except Exception as e:
        print(f"❌ Error during scraping phase: {e}")
        traceback.print_exc() # Print detailed traceback for debugging
        pipeline_results["message"] = f"Scraping failed: {e}"
        # Return early as subsequent steps depend on scraped data
        return pipeline_results

    # --- Step 2: Analysis ---
    # Only proceed if we have website text or social bios to analyze
    if pipeline_results["website_text"] or social_bios_data:
        print("\n--- Phase 2: Analyzing Content ---")
        try:
            # Call analyze_content, passing both website text and the retrieved social bios
            print("  Running analyze_content...")
            pipeline_results["analysis"] = analyze_content(
                pipeline_results["website_text"], # Pass website text (can be None)
                social_bios_data                  # Pass social bios dict (can be empty)
            )
            print("✅ Analysis phase complete.")
            pipeline_results["message"] = "Analysis complete."
        except Exception as e:
            print(f"❌ Error during analysis phase: {e}")
            traceback.print_exc()
            pipeline_results["message"] = f"Analysis failed: {e}"
            # Store error information in the analysis field
            pipeline_results["analysis"] = {"error": f"Analysis failed: {e}"}
    else:
        # This case should be caught by the check in scraping, but added for safety
        print("🟡 Skipping analysis phase (no website text or social bios found).")
        pipeline_results["message"] = "Scraping yielded no content for analysis."


    # --- Step 3: Generation ---
    print("\n--- Phase 3: Generating Story ---")
    # Check if analysis results exist AND don't contain an error key we might have added
    if pipeline_results["analysis"] is not None and not pipeline_results["analysis"].get("error"):
        try:
            print(f"  Running generate_brand_story (Tone: {desired_tone or 'Default'})...")
            # *** Pass the desired_tone to generate_brand_story ***
            pipeline_results["story"] = generate_brand_story(
                pipeline_results["analysis"],
                desired_tone=desired_tone # Pass the tone received by the pipeline
            )

            if pipeline_results["story"]:
                print("✅ Generation phase complete.")
                pipeline_results["message"] = "Story generated successfully."
                pipeline_results["success"] = True # Mark overall pipeline success
            else:
                 # Handle case where generator returns None or empty string
                 print("⚠️ Generation phase completed, but no story was returned (check generator logs/API keys).")
                 pipeline_results["message"] = "Generation failed to produce a story (LLM issue?)."
                 # Keep success as False if story generation is critical

        except Exception as e:
            print(f"❌ Error during generation phase: {e}")
            traceback.print_exc()
            pipeline_results["message"] = f"Story generation failed: {e}"
            # Ensure overall success remains False
            pipeline_results["success"] = False
    else:
        # Handle cases where analysis was skipped or failed
        if pipeline_results["analysis"] and pipeline_results["analysis"].get("error"):
            print("🟡 Skipping generation phase (Analysis step failed).")
            # Keep the analysis error message if more specific
            pipeline_results["message"] = pipeline_results["analysis"].get("error", "Analysis failed, cannot generate story.")
        else: # Analysis was skipped due to no content
            print("🟡 Skipping generation phase (no analysis results available).")
            pipeline_results["message"] = "Analysis results missing, cannot generate story."


    # --- Pipeline End ---
    print("\n" + "="*50)
    print(f"🏁 Pipeline Finished: Success={pipeline_results['success']}, Message='{pipeline_results['message']}'")
    print("="*50)

    return pipeline_results
