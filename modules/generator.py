# modules/generator.py
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
# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

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
    This function does *not* support tone adjustment.
    """
    logging.info("Using template-based story generator (fallback).")
    try:
        # Ensure analysis_results is a dictionary, default to empty if None or invalid
        analysis_results = analysis_results or {}
        keywords = analysis_results.get('keywords', [])
        sentiment = analysis_results.get('sentiment', {})
        # Default sentiment label to 'Neutral' if not found
        sentiment_label = sentiment.get('label', 'Neutral').lower()

        story = f"This brand communicates with a generally {sentiment_label} tone. "

        if keywords and len(keywords) > 0:
            # Create a snippet of the first one or two keywords
            kw_snippet = f"'{keywords[0]}'"
            if len(keywords) > 1:
                kw_snippet += f" and '{keywords[1]}'"
            story += f"Key themes like {kw_snippet} appear central to its online presence. "
        else:
            story += "Its online presence focuses on its core offerings. "

        story += "The overall impression is a brand focused on its primary area of expertise."
        story += "\n\n*[Note: This brief story was generated using a basic template. Advanced features like tone adjustment are not applied in this fallback mode.]*"
        return story
    except Exception as e:
        logging.error(f"Error generating template story: {e}")
        return "[Template generation error: Could not create basic story.]"


# --- MODIFIED: Gemini Story Generator with Tone Adjustment ---
def _generate_story_gemini(
    analysis_results: dict,
    desired_tone: str | None = None, # Added parameter for desired tone
    model_name: str = "models/gemini-1.5-pro-latest"
) -> str | None:
    """
    Attempts to generate a structured brand story using the Google Gemini API,
    adjusting for a desired tone if specified.

    Args:
        analysis_results: Dictionary containing website/social media analysis data.
        desired_tone: Optional string specifying the desired tone (e.g., "Formal", "Casual", "Enthusiastic").
        model_name: The specific Gemini model to use.

    Returns:
        The story string (Markdown formatted) on success, None on failure.
    """
    if not configure_gemini():
        return None # Skip if Gemini isn't configured

    logging.info(f"Attempting to generate structured brand story using Gemini model ({model_name}).")
    if desired_tone:
        logging.info(f"Applying desired tone: {desired_tone}")

    try:
        model = genai.GenerativeModel(model_name)
        # Ensure analysis_results is a dict before dumping, default to empty dict if None
        analysis_summary = json.dumps(analysis_results or {}, indent=2)

        # --- *** MODIFIED PROMPT with Tone Instruction *** ---
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
        # --- *** END OF MODIFIED PROMPT *** ---

        # Configure safety settings to be less restrictive if needed, but be cautious
        # safety_settings = [
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        # ]
        # response = model.generate_content(prompt, safety_settings=safety_settings)

        response = model.generate_content(prompt)

        # Safer access to response text and error handling for blocked content
        try:
            # Access parts if available, otherwise try text
            if response.parts:
                 # Check if the first part has text attribute
                if hasattr(response.parts[0], 'text'):
                    story = response.parts[0].text
                else: # Handle cases where parts might not contain text directly (rare)
                     logging.warning("Response part does not contain text attribute.")
                     # Attempt to get text attribute directly from response as fallback
                     story = response.text
            else:
                 # Fallback to response.text if parts is empty
                 story = response.text


            logging.info("Gemini story generation successful.")
            # Basic cleaning (remove potential leading/trailing markdown indicators/quotes)
            story = story.strip().strip('`').strip()
            return story
        except (ValueError, AttributeError, IndexError) as ve:
            logging.warning(f"Could not access response text, likely blocked or unexpected format. Error: {ve}")
            # Attempt to log blocking feedback if available
            try:
                if response.prompt_feedback:
                    # Log the block reason if available
                    block_reason = getattr(response.prompt_feedback, 'block_reason', 'N/A')
                    logging.warning(f"Prompt Feedback Block Reason: {block_reason}")
                     # Log safety ratings if available
                    safety_ratings = getattr(response.prompt_feedback, 'safety_ratings', [])
                    logging.warning(f"Prompt Feedback Safety Ratings: {safety_ratings}")
                else:
                    logging.warning("No prompt feedback available in the response.")
            except Exception as feedback_e:
                logging.warning(f"Could not retrieve prompt feedback details: {feedback_e}")
            return None
        except Exception as text_extract_e: # Catch other potential errors during text extraction
            logging.error(f"An unexpected error occurred during text extraction from Gemini response: {text_extract_e}")
            # Also log feedback here if possible
            try:
                if response.prompt_feedback:
                    block_reason = getattr(response.prompt_feedback, 'block_reason', 'N/A')
                    logging.warning(f"Prompt Feedback Block Reason (on text extraction error): {block_reason}")
                    safety_ratings = getattr(response.prompt_feedback, 'safety_ratings', [])
                    logging.warning(f"Prompt Feedback Safety Ratings (on text extraction error): {safety_ratings}")
            except Exception as feedback_e:
                 logging.warning(f"Could not retrieve prompt feedback details during text extraction error handling: {feedback_e}")
            return None


    except Exception as e:
        logging.error(f"An error occurred during Gemini API call: {e}")
        # Log detailed error, potentially including response object if available
        # Be careful about logging sensitive info from the response if applicable
        logging.debug(f"Gemini API call failed. Exception details: {e}", exc_info=True) # Include stack trace if debugging
        return None

# --- MODIFIED: Main Orchestrator Function with Tone ---
def generate_brand_story(analysis_results: dict, desired_tone: str | None = None) -> str:
    """
    Generates a brand story, trying the Gemini LLM first with tone adjustment,
    and falling back to a basic template story.

    Args:
        analysis_results: Dictionary containing website/social media analysis data.
        desired_tone: Optional string specifying the desired tone for the story.

    Returns:
        The generated story string (either from Gemini or the template).
    """
    print(f"\n--- Generating Brand Story (Attempting Gemini with Tone: {desired_tone or 'Default'}) ---")
    # Pass the desired_tone to the Gemini generator
    gemini_story = _generate_story_gemini(analysis_results, desired_tone=desired_tone)

    if gemini_story:
        logging.info(f"Successfully generated story using Gemini with tone '{desired_tone or 'Default'}'.")
        return gemini_story
    else:
        logging.warning("Gemini story generation failed or skipped.")
        if desired_tone:
            logging.warning(f"Desired tone '{desired_tone}' could not be applied. Using template fallback.")
        else:
            logging.warning("Using template fallback.")
        # Generate the fallback template story
        return _generate_story_template(analysis_results)

# --- MODIFIED: Script Execution Block with Tone Argument ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a brand story from NLP analysis results stored in a JSON file, with optional tone adjustment."
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the JSON file containing the NLP analysis results."
    )
    # Add the optional tone argument
    parser.add_argument(
        "--tone",
        type=str,
        default=None, # Default is None, meaning no specific tone is requested initially
        help="Specify the desired tone for the generated story (e.g., 'Formal', 'Casual', 'Enthusiastic', 'Witty'). If omitted, uses a default professional tone."
    )
    args = parser.parse_args()

    analysis_data = None
    # Robust file reading and JSON parsing
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        logging.info(f"Successfully loaded analysis data from: {args.input_file}")
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at '{args.input_file}'")
        sys.exit(1) # Exit with error code 1
    except json.JSONDecodeError as json_err:
        logging.error(f"Error: Could not decode JSON from '{args.input_file}'. Invalid JSON format. Details: {json_err}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while reading '{args.input_file}': {e}")
        sys.exit(1)

    # Proceed only if analysis_data was successfully loaded
    if analysis_data is not None: # Check explicitly for None, as empty dict {} is valid
        # Pass the parsed tone argument to the main generation function
        final_story = generate_brand_story(analysis_data, desired_tone=args.tone)

        print("\n--- Final Brand Story (from direct script run) ---")
        print(final_story)
    else:
        # This case should ideally be caught by the exceptions above, but added for safety
        logging.error("Analysis data could not be loaded or is empty. Exiting.")
        sys.exit(1)

