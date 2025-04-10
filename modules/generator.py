import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import json # Used for loading input file AND formatting prompt data
import argparse # For command-line arguments
import sys # For exiting script on error

# --- Configuration ---
load_dotenv() # Load environment variables from .env file
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure the Gemini client library
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        logging.info("Google Generative AI SDK configured successfully.")
        # Optional: Uncomment the model listing block if needed for debugging
        # print("-" * 20); print("Checking available models..."); # etc.
    except Exception as e:
        logging.error(f"Failed to configure Google Generative AI SDK: {e}")
        GOOGLE_API_KEY = None
else:
    logging.warning("GOOGLE_API_KEY not found in environment variables. LLM generation will be skipped.")

# --- MODIFIED: Fallback Story Generator ---
def _generate_story_template(analysis_results: dict) -> str:
    """
    Generates a very simple brand story using an f-string template. Fallback option.
    """
    logging.info("Using template-based story generator (fallback).")
    try:
        keywords = analysis_results.get('keywords', [])
        sentiment = analysis_results.get('sentiment', {})
        sentiment_label = sentiment.get('label', 'Neutral').lower()

        # --- Build the simple template story ---
        story = f"This brand communicates with a generally {sentiment_label} tone. "
        if keywords:
            story += f"Key themes like '{keywords[0]}' and '{keywords[1] if len(keywords) > 1 else 'its core offerings'}' appear central to its online presence. "
        else:
            story += "Its online presence focuses on its core offerings. "
        story += "The overall impression is a brand focused on its primary area of expertise."
        story += "\n\n*[Note: This brief story was generated using a basic template.]*"
        return story

    except Exception as e:
        logging.error(f"Error generating template story: {e}")
        return "[Template generation error: Could not create basic story.]"

# --- MODIFIED: Gemini Story Generator ---
# Renamed function, updated docstring, replaced prompt
def _generate_story_gemini(analysis_results: dict, model_name: str = "models/gemini-1.5-pro-latest") -> str | None:
    """
    Attempts to generate a concise brand story using the Google Gemini API based on the provided analysis.
    Returns the story string on success, None on failure.
    """
    if not GOOGLE_API_KEY:
        logging.warning("Google API key not available. Skipping Gemini story generation.")
        return None

    logging.info(f"Attempting to generate brand story using Gemini model ({model_name}).")

    try:
        model = genai.GenerativeModel(model_name)

        # Convert analysis results to JSON string for the prompt
        analysis_summary = json.dumps(analysis_results, indent=2)

        # --- NEW PROMPT ---
        prompt = f"""
        Analysis Data:
        ```json
        {analysis_summary}
        ```

       **Input Data Context:**

        **Input Data Context:**

            Immediately preceding these instructions, you will find analysis data formatted as a JSON object. This JSON represents the findings from scraping and analyzing a company's online presence.

            The core analysis results (from the NLP module) typically include:

            * `keywords`: A list of important keywords or themes identified in the text (e.g., `["notion", "docs", "projects", ...]`).
            * `sentiment`: An object containing the sentiment analysis:
                * `label`: The overall sentiment label (e.g., `"Positive"`, `"Neutral"`).
                * `score`: A numerical score associated with the sentiment (e.g., `0.9998`).

            **Role:** You are an expert brand strategist and narrative copywriter specializing in distilling a company's essence into a compelling, flowing, and descriptive story.

            **Goal:** Generate an **expansive and detailed** brand story, presented as a single block of narrative text. Use the analysis data (provided just before these instructions) to inform the story. The goal is to weave the analyzed data into a fluid, **verbose**, and evocative narrative, **not** to create a summary, report, or analysis of the data itself. Explore the nuances suggested by the data.

            **Task:**

            Based **only** on the analysis data provided immediately preceding this instruction set, write a compelling, **verbose**, and descriptive brand story for the company identified in that data. Focus on creating a rich narrative flow that captures the brand's identity, painting a vivid picture by synthesizing the `keywords`, `sentiment`, `website_text`, and any available `social_bios`. Develop the narrative arc suggested by the data.

            **Requirements:**

            1.  **Length:** Approximately **400-500 words**, ensuring an expansive, detailed, and verbose narrative within this length.
            2.  **Tone:** The story's tone should reflect the `sentiment` found in the preceding analysis data.
            3.  **Content:** Synthesize the key `keywords`/themes and reflect the core message found in the preceding analysis data (`website_text`, `social_bios` if available) into a cohesive, detailed, and evocative story.
            4.  **Focus:** Capture the perceived essence and identity of the brand as presented online in the preceding data, telling its story vividly and in detail.
            5.  **(Optional)** If inferred audience or brand archetype data is present in the preceding analysis, subtly weave it into the extended narrative.
            6.  **Output Format:** Output **ONLY** the brand story itself as a single block of narrative text. **DO NOT** include any analysis, summaries, bullet points, keywords, introductory phrases (like "Here is the brand story:"), concluding remarks, or any text other than the story narrative itself. Ensure the output is pure, verbose narrative prose.

            **Brand Story:**

        """
        # --- END OF NEW PROMPT ---

        response = model.generate_content(prompt)

        try:
            story = response.text
            logging.info("Gemini story generation successful.")
            # Simple check to remove potential unwanted preamble, although the prompt asks not to add it
            lines = story.strip().split('\n')
            if lines and lines[0].lower().startswith("here is the brand story"):
                story = "\n".join(lines[1:]).strip()
            return story
        except ValueError as ve:
            logging.warning(f"Could not access response text, likely blocked. Error: {ve}")
            if response.prompt_feedback:
                 logging.warning(f"Prompt Feedback Block Reason: {response.prompt_feedback.block_reason}")
                 logging.warning(f"Prompt Feedback Safety Ratings: {response.prompt_feedback.safety_ratings}")
            return None
        except Exception as text_e:
            logging.error(f"Error accessing response text: {text_e}")
            return None

    except Exception as e:
        logging.error(f"An error occurred during Gemini story generation: {e}")
        return None

# --- MODIFIED: Main Orchestrator Function ---
# Renamed function
def generate_brand_story(analysis_results: dict) -> str:
    """
    Generates a brand story, trying the Gemini LLM first and falling back to a template story.
    """
    print("\n--- Generating Brand Story (Attempting Gemini) ---") # Updated print

    # Calls the Gemini *story* generator
    gemini_story = _generate_story_gemini(analysis_results)

    if gemini_story:
        return gemini_story
    else:
        # If Gemini fails, use the fallback *story* template
        logging.warning("Gemini story generation failed or skipped, using template fallback.")
        return _generate_story_template(analysis_results) # Calls the story template

# --- MODIFIED: Script Execution Block ---
if __name__ == "__main__":
    # --- Setup Argument Parser ---
    # Fixed the description string
    parser = argparse.ArgumentParser(description="Generate a brand story from NLP analysis results stored in a JSON file.")
    parser.add_argument(
        "input_file", # Name of the argument (positional)
        type=str,     # Expected type is string (file path)
        help="Path to the JSON file containing the NLP analysis results." # Help message
    )
    args = parser.parse_args() # Parse the command-line arguments

    # --- Load data from the specified JSON file ---
    analysis_data = None # Initialize variable
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        logging.info(f"Successfully loaded analysis data from: {args.input_file}")
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at '{args.input_file}'")
        print(f"Error: Input file not found at '{args.input_file}'", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from '{args.input_file}'.")
        print(f"Error: Could not decode JSON from '{args.input_file}'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while reading '{args.input_file}': {e}")
        print(f"An unexpected error occurred while reading '{args.input_file}': {e}", file=sys.stderr)
        sys.exit(1)

    # --- Proceed only if data was loaded successfully ---
    if analysis_data:
        # Pass the loaded data to the STORY generator
        final_story = generate_brand_story(analysis_data) # Renamed variable

        print("\n--- Final Brand Story ---") # Updated print
        print(final_story) # Renamed variable
    else:
        logging.error("Analysis data could not be loaded. Exiting.")
        print("Error: Analysis data could not be loaded.", file=sys.stderr)
        sys.exit(1)