# modules/generator.py
# (Keep other imports and functions as they were)
import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import json
import argparse
import sys

# --- Configuration ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Functions (_generate_story_template, configure_gemini remain the same) ---
def configure_gemini():
    # ...(keep existing implementation)...
    if GOOGLE_API_KEY:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            logging.info("Google Generative AI SDK configured successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to configure Google Generative AI SDK: {e}")
            return False
    else:
        logging.warning("GOOGLE_API_KEY not found in environment variables. LLM generation will be skipped.")
        return False

def _generate_story_template(analysis_results: dict) -> str:
    # ...(keep existing implementation)...
    logging.info("Using template-based story generator (fallback).")
    try:
        analysis_results = analysis_results or {}
        keywords = analysis_results.get('keywords', [])
        sentiment = analysis_results.get('sentiment', {})
        sentiment_label = sentiment.get('label', 'Neutral').lower()
        story = f"This brand communicates with a generally {sentiment_label} tone. "
        if keywords and len(keywords) > 0:
            kw_snippet = f"'{keywords[0]}'"
            if len(keywords) > 1: kw_snippet += f" and '{keywords[1]}'"
            story += f"Key themes like {kw_snippet} appear central to its online presence. "
        else: story += "Its online presence focuses on its core offerings. "
        story += "The overall impression is a brand focused on its primary area of expertise."
        story += "\n\n*[Note: This brief story was generated using a basic template.]*"
        return story
    except Exception as e:
        logging.error(f"Error generating template story: {e}")
        return "[Template generation error: Could not create basic story.]"


# --- MODIFIED: Gemini Story Generator ---
def _generate_story_gemini(analysis_results: dict, model_name: str = "models/gemini-1.5-pro-latest") -> str | None:
    """
    Attempts to generate a structured brand story using the Google Gemini API.
    Returns the story string (Markdown formatted) on success, None on failure.
    """
    if not configure_gemini():
        return None

    logging.info(f"Attempting to generate structured brand story using Gemini model ({model_name}).")

    try:
        model = genai.GenerativeModel(model_name)
        # Ensure analysis_results is a dict before dumping
        analysis_summary = json.dumps(analysis_results or {}, indent=2)

        # --- *** MODIFIED PROMPT *** ---
        # Changed requirements to ask for Markdown headings and paragraphs
        prompt = f"""
        Analysis Data:
        ```json
        {analysis_summary}
        ```

        **Input Data Context:**
        The JSON above contains analysis from scraping a company's website and potentially social media. It includes identified `keywords`, overall `sentiment` (label and score), and potentially the source `website_text` and `social_bios`.

        **Role:** You are an expert brand strategist and narrative copywriter.

        **Goal:** Generate a compelling and informative brand story based *only* on the provided Analysis Data. The story should be well-structured, using clear headings and paragraphs to present different facets of the brand's identity as revealed by the data.

        **Task:**
        Write a brand story using Markdown formatting. Structure the story logically with appropriate headings and well-written paragraphs underneath each. Synthesize the `keywords`, `sentiment`, `website_text`, and any available `social_bios` from the Analysis Data.

        **Requirements:**

        1.  **Structure:** Organize the story using Markdown headings (e.g., `## Brand Identity`, `## Core Themes`, `## Online Voice & Tone`, `## Overall Narrative`). Use at least 3-4 relevant headings.
        2.  **Content:** Under each heading, write 1-3 detailed paragraphs synthesizing the relevant information from the Analysis Data. Weave in keywords naturally. Reflect the detected sentiment in the language used.
        3.  **Formatting:** Use standard Markdown for headings (`## Heading Title`) and paragraphs (standard text separated by blank lines). Ensure proper paragraph breaks.
        4.  **Focus:** Base the story *exclusively* on the provided Analysis Data. Do not add external information or make assumptions beyond the data.
        5.  **Output Format:** Output **ONLY** the Markdown formatted brand story. **DO NOT** include the original JSON data, introductory phrases (like "Here is the story:"), concluding remarks, or any text other than the structured Markdown story itself.

        **Structured Brand Story (Markdown):**
        """
        # --- *** END OF MODIFIED PROMPT *** ---

        response = model.generate_content(prompt)

        # Safer access to response text
        try:
            story = response.text
            logging.info("Gemini story generation successful.")
            # Basic cleaning (remove potential leading/trailing markdown indicators if any)
            story = story.strip().strip('`')
            return story
        except (ValueError, AttributeError, IndexError) as ve:
            logging.warning(f"Could not access response text, likely blocked or unexpected format. Error: {ve}")
            try: # Log feedback if available
                if response.prompt_feedback:
                    logging.warning(f"Prompt Feedback Block Reason: {response.prompt_feedback.block_reason}")
                    logging.warning(f"Prompt Feedback Safety Ratings: {response.prompt_feedback.safety_ratings}")
            except Exception as feedback_e:
                 logging.warning(f"Could not retrieve prompt feedback details: {feedback_e}")
            return None

    except Exception as e:
        logging.error(f"An error occurred during Gemini API call: {e}")
        return None

# --- Main Orchestrator Function (Unchanged from previous refactor) ---
def generate_brand_story(analysis_results: dict) -> str:
    """
    Generates a brand story, trying the Gemini LLM first and falling back to a template story.
    Returns the story string.
    """
    print("\n--- Generating Brand Story (Attempting Gemini) ---")
    gemini_story = _generate_story_gemini(analysis_results)
    if gemini_story:
        return gemini_story
    else:
        logging.warning("Gemini story generation failed or skipped, using template fallback.")
        return _generate_story_template(analysis_results)

# --- Script Execution Block (Unchanged - for testing generator.py directly) ---
if __name__ == "__main__":
    # ... (keep existing test block) ...
    parser = argparse.ArgumentParser(description="Generate a brand story from NLP analysis results stored in a JSON file.")
    parser.add_argument("input_file", type=str, help="Path to the JSON file containing the NLP analysis results.")
    args = parser.parse_args()
    analysis_data = None
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f: analysis_data = json.load(f)
        logging.info(f"Successfully loaded analysis data from: {args.input_file}")
    except FileNotFoundError: logging.error(f"Error: Input file not found at '{args.input_file}'"); sys.exit(1)
    except json.JSONDecodeError: logging.error(f"Error: Could not decode JSON from '{args.input_file}'."); sys.exit(1)
    except Exception as e: logging.error(f"An unexpected error occurred while reading '{args.input_file}': {e}"); sys.exit(1)

    if analysis_data:
        final_story = generate_brand_story(analysis_data)
        print("\n--- Final Brand Story (from direct script run) ---")
        print(final_story)
    else:
        logging.error("Analysis data could not be loaded. Exiting."); sys.exit(1)

