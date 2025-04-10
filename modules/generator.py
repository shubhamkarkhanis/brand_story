import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import json # Using json.dumps for potentially complex data in prompt

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

        # --- UNCOMMENTED: List available models ---
        print("-" * 20)
        print("Checking available models supporting 'generateContent'...")
        try:
            models_found = False
            for m in genai.list_models():
                # Check if 'generateContent' is a supported method for the model
                if 'generateContent' in m.supported_generation_methods:
                    # Print the full name of the model (e.g., 'models/gemini-1.0-pro')
                    print(f"  - {m.name}")
                    models_found = True
            if not models_found:
                 print("  No models found supporting 'generateContent'. Check API key permissions and enabled APIs in Google Cloud.")
        except Exception as list_e:
            print(f"  Error listing models: {list_e}")
            print("  This could indicate an issue with the API key, permissions, or network.")
        print("-" * 20)
        # --- End of Model Listing Block ---

    except Exception as e:
        logging.error(f"Failed to configure Google Generative AI SDK: {e}")
        GOOGLE_API_KEY = None # Prevent further API calls if config fails
else:
    logging.warning("GOOGLE_API_KEY not found in environment variables. LLM generation will be skipped.")

# --- Fallback Generator (Similar to before, kept for robustness) ---
def _generate_report_template(analysis_results: dict) -> str:
    """
    Generates a simple brand report using an f-string template. Fallback option.
    """
    logging.info("Using template-based report generator (fallback).")
    try:
        keywords = analysis_results.get('keywords', [])
        sentiment = analysis_results.get('sentiment', {})
        sentiment_label = sentiment.get('label', 'Neutral').capitalize()
        sentiment_score = sentiment.get('score', 0.0)
        website_text_exists = bool(analysis_results.get('source_texts', {}).get('website'))
        social_texts = {k: v for k, v in analysis_results.get('source_texts', {}).items() if k != 'website' and v}
        social_platforms_found = list(social_texts.keys())

        # --- Build the template report ---
        report = f"## Brand Analysis Report (Template)\n\n"
        report += f"**Overall Sentiment:** {sentiment_label} (Score: {sentiment_score:.2f})\n\n" # Made score more visible

        if keywords:
            top_keywords = ", ".join([f"`{k}`" for k in keywords[:7]]) # Use markdown for keywords
            report += f"**Key Themes & Keywords:** The analysis identified several key themes, including: {top_keywords}.\n\n"
        else:
            report += "**Key Themes & Keywords:** Specific prominent keywords were not readily extracted from the provided text.\n\n"

        report += "**Content Sources Analyzed:**\n"
        if website_text_exists:
            report += "- Primary Website Content\n"
        if social_platforms_found:
            # Ensure platform names are capitalized correctly if needed
            platform_names = [p.capitalize() for p in social_platforms_found]
            report += f"- Social Media Profiles: {', '.join(platform_names)}\n"
        if not website_text_exists and not social_platforms_found:
            report += "- No specific content sources could be confirmed.\n"

        report += f"\n**Summary:** This brand's online presence appears to convey a generally **{sentiment_label.lower()}** message. "
        if keywords:
             report += f"The focus seems to be around '{keywords[0]}'."
        report += "\n\n*[Note: This report was generated using a basic template due to limitations in accessing the advanced AI model.]*"
        return report

    except Exception as e:
        logging.error(f"Error generating template report: {e}")
        return "## Analysis Report\n\nAn error occurred during the automated report generation. Please review the raw analysis data."

# --- Gemini LLM Generator ---
# MODIFICATION: Changed the default model_name to a potentially more current one.
# *** IMPORTANT: Replace 'models/gemini-1.5-pro-latest' with the actual model name
# *** found from the listing above if this one doesn't work!
def _generate_report_gemini(analysis_results: dict, model_name: str = "models/gemini-1.5-pro-latest") -> str | None:
    """
    Attempts to generate a fancy, user-pleasing report using the Google Gemini API.
    Returns the report string on success, None on failure.
    """
    if not GOOGLE_API_KEY:
        logging.warning("Google API key not available. Skipping Gemini report generation.")
        return None

    # Using the model_name passed
    logging.info(f"Attempting to generate report using Gemini model ({model_name}).")

    try:
        # Initialize the Gemini model using the specified name
        # Ensure the model_name is one listed as available by genai.list_models()
        model = genai.GenerativeModel(model_name)

        # --- Craft the Prompt (This is key!) ---
        # Convert analysis results to a string format suitable for the prompt
        # Using json.dumps can handle complex structures safely
        analysis_summary = json.dumps(analysis_results, indent=2)

        # Make sure the prompt is well-formed and doesn't contain unexpected characters
        prompt = f"""
        **Objective:** Generate an engaging, insightful, and user-pleasing brand analysis report based on the provided data. The report should synthesize the findings into a coherent narrative, highlighting the brand's perceived online identity.

        **Role:** You are a skilled marketing analyst and storyteller. Your tone should be professional, positive (where appropriate based on sentiment), and insightful. Use clear headings and bullet points where helpful for readability. Avoid overly technical jargon.

        **Input Data (JSON format):**
        ```json
        {analysis_summary}
        ```

        **Instructions:**
        1.  **Introduction:** Start with a brief overview summarizing the analysis scope (e.g., website, social media).
        2.  **Sentiment Analysis:** Clearly state the overall sentiment (Positive/Negative/Neutral) and its strength (score). Elaborate slightly on what this sentiment suggests about the brand's online communication style.
        3.  **Key Themes & Keywords:** Discuss the prominent keywords. Don't just list them; explain what these themes suggest about the brand's focus, values, or industry positioning. Group related keywords if possible.
        4.  **Brand Voice & Story:** Synthesize the sentiment and keywords into a short narrative (1-2 paragraphs) describing the *perceived* brand story or voice based *only* on the analyzed text. What impression does the brand seem to be making online?
        5.  **Conclusion/Recommendations (Optional, keep brief):** Briefly conclude the report. You could add a sentence about potential strengths or areas for consistency based *only* on the analysis (e.g., "The consistent positive tone is a strength," or "Highlighting core themes more across platforms could be beneficial"). Do NOT invent recommendations outside the data.
        6.  **Formatting:** Use Markdown for formatting (headings `##`, bold `**`, italics `*`, bullet points `-`). Ensure the output is well-structured and easy to read.

        **Generate the Brand Analysis Report:**
        """

        # Generate the content
        # Consider adding safety_settings if needed, see Gemini docs
        # Example: safety_settings={'HARASSMENT': 'BLOCK_NONE'} # Use with caution
        response = model.generate_content(prompt) # Add safety_settings=safety_settings if needed

        # Enhanced response checking
        try:
            # Accessing response.text might raise an exception if blocked
            report = response.text
            logging.info("Gemini report generation successful.")
            return report
        except ValueError as ve:
            # This often happens if the response was blocked
            logging.warning(f"Could not access response text, likely blocked. Error: {ve}")
            if response.prompt_feedback:
                 logging.warning(f"Prompt Feedback Block Reason: {response.prompt_feedback.block_reason}")
                 logging.warning(f"Prompt Feedback Safety Ratings: {response.prompt_feedback.safety_ratings}")
            return None
        except Exception as text_e:
            logging.error(f"Error accessing response text: {text_e}")
            return None


    except Exception as e:
        # Catching specific API errors can be helpful
        # Example: from google.api_core import exceptions as api_exceptions
        # if isinstance(e, api_exceptions.NotFound): ...
        # if isinstance(e, api_exceptions.PermissionDenied): ...
        logging.error(f"An error occurred during Gemini report generation: {e}")
        # The error message `e` often contains the specific reason (like the 404)
        return None

# --- Main Orchestrator Function ---
def generate_brand_report(analysis_results: dict) -> str:
    """
    Generates a brand report, trying the Gemini LLM first and falling back to a template.

    Args:
        analysis_results: A dictionary containing keywords, sentiment, and source_texts
                          from Module 3. Example structure:
                          {
                              'keywords': ['innovation', 'data', 'cloud', ...],
                              'sentiment': {'label': 'Positive', 'score': 0.85},
                              'source_texts': {'website': '...', 'linkedin': '...'}
                          }

    Returns:
        A string containing the generated brand report (Markdown formatted).
    """
    print("\n--- Generating Brand Report (Attempting Gemini) ---") # Moved print statement here

    # Try Gemini first
    # It calls the modified _generate_report_gemini which now defaults to a newer model
    gemini_report = _generate_report_gemini(analysis_results)

    if gemini_report:
        return gemini_report
    else:
        # If Gemini fails (key missing, API error, content blocked, wrong model etc.), use the fallback
        logging.warning("Gemini generation failed or skipped, using template fallback.")
        return _generate_report_template(analysis_results)

# --- Example Usage ---
if __name__ == "__main__":
    # Dummy data simulating output from Module 3
    dummy_analysis = {
        'keywords': ['sustainable finance', 'impact investing', 'ESG', 'reporting', 'green bonds', 'climate action', 'transparency'],
        'sentiment': {'label': 'Positive', 'score': 0.88},
        'source_texts': {
            'website': 'Our firm leads in sustainable finance, offering bespoke ESG solutions and impact investing opportunities focused on measurable outcomes and client transparency...',
            'linkedin': 'Driving change through sustainable finance and ESG integration. Proud to support the transition to a greener economy. #impactinvesting #esg #sustainability',
            'twitter': None # Example where a social fetch failed
            }
    }

    # The call to generate_brand_report now handles the initial print message
    final_report = generate_brand_report(dummy_analysis)
    print("\n--- Final Brand Report ---")
    print(final_report)
