# modules/generator.py
# Reads analyzed data, calls LLM, saves final story to export.md in project root.

import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import json
import argparse
import sys
import traceback # Import traceback for better error details

# --- Configuration ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
# Define the export filename for the STORY
STORY_EXPORT_FILENAME = "export.md"
# PROMPT_EXPORT_FILENAME = "export.md" # REMOVED - No longer exporting prompt

# --- Functions ---

def configure_gemini():
    """Configures the Google Generative AI SDK using the API key from environment variables."""
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
    """
    Generates a basic, template-based brand story as a fallback.
    """
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


def _generate_story_gemini(
    analysis_results: dict,
    desired_tone: str | None = None,
    model_name: str = "gemini-3-flash-preview"
) -> str | None:
    """
    Attempts to generate a structured brand story using the Google Gemini API,
    adjusting for a desired tone if specified.
    """
    if not configure_gemini():
        return None # Skip if Gemini isn't configured

    logging.info(f"Attempting to generate structured brand story using Gemini model ({model_name}).")
    if desired_tone: logging.info(f"Applying desired tone: {desired_tone}")

    try:
        model = genai.GenerativeModel(model_name)
        analysis_summary = json.dumps(analysis_results or {}, indent=2)

        # --- PROMPT Definition ---
        # (Using the prompt structure from your provided code - unchanged here)
        prompt = f"""
        Analysis Data:
        ```json
        {analysis_summary}
        ```

        **Input Data Context:**
        The JSON above contains analysis from scraping a company's website and potentially social media. It includes identified `keywords`, overall `sentiment` (label and score), and potentially the source `website_text` and `social_bios`.

        **Role:** You are an expert brand strategist and narrative copywriter.

        **Goal:** Generate a compelling and informative brand story based *only* on the provided Analysis Data. The story should be well-structured, using clear headings and paragraphs. Crucially, the story's language and style should match the specified `Desired Tone`.

        **Task:**
        1.  Analyze the provided `Analysis Data` (keywords, sentiment, text snippets).
        2.  Write a brand story using Markdown formatting.
        3.  Structure the story logically with appropriate Markdown headings (e.g., `## Brand Identity`, `## Core Themes`, `## Online Voice & Tone`, `## Overall Narrative`). Use at least 3-4 relevant headings.
        4.  Under each heading, write 1-3 detailed paragraphs synthesizing the relevant information from the Analysis Data. Weave in keywords naturally.
        5.  **Crucially:** Adjust the language, style, and word choices throughout the entire story to consistently match the `Desired Tone` specified below.

        **Requirements:**

        * **Structure:** Use Markdown headings (e.g., `## Heading Title`) and paragraphs.
        * **Content:** Synthesize information *only* from the provided `Analysis Data`.
        * **Formatting:** Standard Markdown for headings and paragraphs. Ensure proper paragraph breaks.
        * **Focus:** Base the story *exclusively* on the provided data. Do not add external information.
        * **Tone Consistency:** The language and style must uniformly reflect the `Desired Tone` throughout the narrative. If 'Default' is specified, use a professional and informative tone appropriate for a brand strategist, reflecting the detected sentiment in the data.
        * **Output Format:** Output **ONLY** the Markdown formatted brand story. **DO NOT** include the original JSON data, introductory phrases (like "Here is the story:"), concluding remarks, or any text other than the structured Markdown story itself.

        **Desired Tone:** [{desired_tone if desired_tone else 'Default Professional/Informative (based on sentiment)'}]

        **Structured Brand Story (Markdown):**
        """
        # --- END OF PROMPT Definition ---

        # --- Prompt Export REMOVED ---

        # --- Call LLM API ---
        logging.info(f"Calling Gemini model ({model_name})...")
        response = model.generate_content(prompt)

        # Safer access to response text
        try:
            if response.parts:
                if hasattr(response.parts[0], 'text'): story = response.parts[0].text
                else: story = response.text
            else: story = response.text

            logging.info("Gemini story generation successful.")
            story = story.strip().strip('`').strip()
            return story
        except (ValueError, AttributeError, IndexError) as ve:
            logging.warning(f"Could not access response text, likely blocked or unexpected format. Error: {ve}")
            try: # Log feedback
                if response.prompt_feedback:
                    block_reason = getattr(response.prompt_feedback, 'block_reason', 'N/A')
                    safety_ratings = getattr(response.prompt_feedback, 'safety_ratings', [])
                    logging.warning(f"Prompt Feedback Block Reason: {block_reason}")
                    logging.warning(f"Prompt Feedback Safety Ratings: {safety_ratings}")
                else: logging.warning("No prompt feedback available.")
            except Exception as feedback_e: logging.warning(f"Could not retrieve feedback details: {feedback_e}")
            return None
        except Exception as text_extract_e:
            logging.error(f"Unexpected error during text extraction: {text_extract_e}")
            try: # Log feedback
                 if response.prompt_feedback:
                     block_reason = getattr(response.prompt_feedback, 'block_reason', 'N/A')
                     safety_ratings = getattr(response.prompt_feedback, 'safety_ratings', [])
                     logging.warning(f"Prompt Feedback Block Reason (on text extraction error): {block_reason}")
                     logging.warning(f"Prompt Feedback Safety Ratings (on text extraction error): {safety_ratings}")
            except Exception as feedback_e: logging.warning(f"Could not retrieve feedback details: {feedback_e}")
            return None

    except Exception as e:
        logging.error(f"An error occurred during Gemini API call prep/execution: {e}")
        logging.debug(f"Gemini API call failed. Details:", exc_info=True)
        return None

# --- Main Orchestrator Function ---
# *** MODIFIED: Changed output filename ***
def generate_brand_story(analysis_results: dict, desired_tone: str | None = None) -> str:
    """
    Generates a brand story (LLM or template) and saves it to export.md.

    Args:
        analysis_results: Dictionary containing analysis data.
        desired_tone: Optional string specifying the desired tone.

    Returns:
        The generated story string.
    """
    print(f"\n--- Generating Brand Story (Attempting Gemini with Tone: {desired_tone or 'Default'}) ---")
    final_story = None
    gemini_story = _generate_story_gemini(analysis_results, desired_tone=desired_tone)

    if gemini_story:
        logging.info(f"Successfully generated story using Gemini with tone '{desired_tone or 'Default'}'.")
        final_story = gemini_story
    else:
        logging.warning("Gemini generation failed/skipped. Using template fallback.")
        if desired_tone: logging.warning(f"Desired tone '{desired_tone}' not applied.")
        final_story = _generate_story_template(analysis_results)

    # --- Save Final Story to export.md ---
    try:
        # Use the constant defined at the top
        output_story_filename = STORY_EXPORT_FILENAME
        # Save in project root (one level up from modules/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_story_path = os.path.join(project_root, output_story_filename)
        with open(output_story_path, 'w', encoding='utf-8') as f:
            f.write(final_story)
        logging.info(f"Final story saved to: {output_story_path}")
    except Exception as e:
        logging.error(f"Failed to save final story to {output_story_path}: {e}")
        # Still return the story even if saving fails
    return final_story


# --- Script Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate brand story from JSON analysis file."
    )
    parser.add_argument(
        "input_file", type=str, help="Path to input JSON file."
    )
    parser.add_argument(
        "--tone", type=str, default=None, help="Desired story tone."
    )
    args = parser.parse_args()

    analysis_data = None
    try:
        abs_input_file = os.path.abspath(args.input_file)
        with open(abs_input_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        logging.info(f"Successfully loaded analysis data from: {abs_input_file}")
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at '{abs_input_file}'")
        sys.exit(1)
    except json.JSONDecodeError as json_err:
        logging.error(f"Error decoding JSON from '{abs_input_file}': {json_err}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading '{abs_input_file}': {e}")
        sys.exit(1)

    if analysis_data is not None:
        final_story = generate_brand_story(analysis_data, desired_tone=args.tone)
        print("\n--- Final Brand Story (from direct script run) ---")
        print(final_story) # Print story to console when run directly
    else:
        logging.error("Analysis data could not be loaded. Exiting.")
        sys.exit(1)
