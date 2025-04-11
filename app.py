# app.py
# Streamlit frontend for the Brand Story Generator
# *** V14: Fixed f-string CSS syntax error ***

import streamlit as st
import time
import os
import sys
import base64 # For background and social icons
# import re # No longer needed for highlighting

# --- Attempt to import the pipeline function ---
try:
    # Assumes app.py is in root, modules/ is sibling
    from modules import run_full_pipeline
except ImportError as e:
    st.error(f"Fatal Error: Could not import pipeline function: {e}")
    st.error("Ensure 'app.py' is in the project root and the 'modules' directory with '__init__.py' exists.")
    st.stop() # Stop the streamlit app if import fails

# --- Optional Imports for Word Cloud ---
try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    WORDCLOUD_INSTALLED = True
except ImportError:
    WORDCLOUD_INSTALLED = False
    st.warning("Optional libraries 'wordcloud' and 'matplotlib' not found. Word cloud visualization will be disabled. Install them (`pip install wordcloud matplotlib`) to enable this feature.", icon="⚠️")
# --- End Optional Imports ---


# --- Page Configuration ---
st.set_page_config(
    page_title="Brand Story Generator",
    page_icon="🚀",
    layout="wide" # Use wide layout
)

# --- Function to generate Main Background CSS ---
def get_main_background_css(img_file):
    """ Generates CSS for the main background using a local file. """
    if not os.path.exists(img_file):
        print(f"Warning: Main background image file not found: {img_file}. Using fallback color.")
        return """
        div[data-testid="stAppViewContainer"] > .main {
            background-color: #0E1117; /* Fallback color */
        }
        """
    try:
        with open(img_file, "rb") as f: img_bytes = f.read()
        encoded_img = base64.b64encode(img_bytes).decode()
        img_ext = os.path.splitext(img_file)[1].lower().strip('.')
        # Corrected fallback extension check
        if img_ext not in ["png", "jpg", "jpeg", "gif", "webp", "svg"]:
             img_ext = "jpg" # Default to jpg if unknown common type
        main_bg_css = f"""
        div[data-testid="stAppViewContainer"] > .main {{
            background: url(data:image/{img_ext};base64,{encoded_img});
            background-size: cover; background-position: center center;
            background-repeat: no-repeat; background-attachment: fixed;
            background-color: #0E1117; /* Fallback color */
        }}"""
        print(f"Main background CSS generated using: {img_file}")
        return main_bg_css
    except Exception as e:
        print(f"Error generating main background CSS: {e}")
        # Fallback color on error
        return """
        div[data-testid="stAppViewContainer"] > .main {
            background-color: #0E1117; /* Fallback color */
        }"""

# --- Apply Backgrounds ---
main_image_path = 'assets/bg.jpg' # Ensure this path is correct
main_bg_css_rule = get_main_background_css(main_image_path)

# --- Inject All Custom CSS ---
# Use {{ and }} for literal braces in f-string CSS
st.markdown(f"""
<style>
/* --- Main Background CSS (dynamically generated) --- */
{main_bg_css_rule}

/* --- Other Styles --- */
/* Make block container transparent to show main background */
div[data-testid="stAppViewContainer"] > .main .block-container {{
    padding-top: 3rem; padding-bottom: 5rem;
    padding-left: 2rem; padding-right: 2rem;
    background: none; /* Make container transparent */
    /* background-color: rgba(14, 17, 23, 0.8); /* Optional: Slight dark overlay */
    /* border-radius: 10px; /* Optional: Rounded corners */
}}

/* Center align elements within the main content column (kept for structure) */
.centered-content {{
    display: flex;
    flex-direction: column;
    align-items: center; /* Center items horizontally */
}}

/* Style the form submit button container (handled by form layout) */
/* div[data-testid="stButton"] {{ display: flex; justify-content: center; }} /* Less needed with form */

/* Ensure matplotlib plots have a transparent background */
.stPlotlyChart, .stpyplot {{
    background-color: transparent !important;
}}

/* Style for social icons */
.social-icon {{
    width: 24px;      /* Adjust size as needed */
    height: 24px;     /* Adjust size as needed */
    vertical-align: middle;
    margin-right: 8px; /* Space between icon and text */
    /* Add slight brightness effect on hover */
    transition: filter 0.2s ease-in-out;
}}
.social-icon:hover {{
    filter: brightness(1.2);
}}
.social-link-container {{
    margin-bottom: 8px; /* Space between links */
    display: flex;       /* Use flexbox for alignment */
    align-items: center; /* Align icon and text vertically */
}}
/* Ensure links within the container are styled appropriately */
.social-link-container a, .social-link-container a:visited {{
    color: inherit; /* Inherit text color from parent */
    text-decoration: none; /* Remove underline */
    display: inline-flex; /* Align icon and text properly */
    align-items: center;
}}
.social-link-container span {{
     /* Style for the platform text next to the icon */
     margin-left: 5px; /* Keep the text slightly spaced from the icon if icon is linked */
}}

</style>
""", unsafe_allow_html=True)
# --- End Custom CSS ---

# --- Social Icon Paths ---
# Maps lowercase platform names to their image file paths
# *** IMPORTANT: Ensure these files exist in the 'assets' folder ***
SOCIAL_ICON_PATHS = {
    "linkedin": "assets/linkedin.png",
    "twitter": "assets/twitter.png",
    "x": "assets/twitter.png", # Map 'x' to twitter icon if needed
    "facebook": "assets/facebook.png",
    "youtube": "assets/youtube.png",
    "instagram": "assets/instagram.png",
    "pinterest": "assets/pinterest.png",
    "tiktok": "assets/tiktok.png",
    "github": "assets/github.png", # Example: Add github if relevant
    # Add other platforms and their corresponding image paths here
    # "default": "assets/default_link.png" # Optional default icon
}
# --- End Social Icon Paths ---


# --- Centered Input Section ---
# Use columns to create margins and constrain the central content width
_left_margin, main_content_col, _right_margin = st.columns([1, 2, 1])

# Initialize session state for results and inputs
if 'pipeline_results' not in st.session_state: st.session_state.pipeline_results = None
if 'last_run_url' not in st.session_state: st.session_state.last_run_url = ""
if 'url_input' not in st.session_state: st.session_state.url_input = "" # Persist user's raw input

# Use a form for Enter key submission
with main_content_col:
    # Use markdown for centered title and subtitle (apply styles if needed)
    st.markdown("<h1 style='text-align: center; color: white;'>🚀 AI Brand Story Generator</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #e0e0e0;'>Enter a company's website URL (e.g., www.example.com or https://www.example.com) to analyze its online presence and generate a brand story.</p>", unsafe_allow_html=True)
    st.write("") # Add some vertical space

    with st.form("input_form", clear_on_submit=False):
        # Text Input (will take width of main_content_col)
        input_url_from_form = st.text_input( # Renamed variable inside form scope slightly for clarity
            "Company Website URL", # Label is useful here for context
            value=st.session_state.url_input, # Display the session state value
            placeholder="e.g., www.example.com",
            key="company_url_input_form", # Use a key specific to the form input
            label_visibility="collapsed" # Hide label visually, but keep for accessibility
        )
        # Update session state immediately on input change *within* the form context
        # This ensures the value persists if the form isn't submitted but other interactions happen
        st.session_state.url_input = input_url_from_form

        st.write("") # Add vertical space before button

        # Form Submit Button - Pressing Enter in text_input triggers this
        submit_button = st.form_submit_button(
            "✨ Analyze & Generate Story",
            type="primary",
            use_container_width=True
        )

# Add a divider below the input section
st.divider()
# --- End Centered Input Section ---


# --- Output Section & Run Pipeline Logic ---

# Process the form submission *after* the form definition
# Uses the session state value which was updated by the input inside the form
if submit_button and st.session_state.url_input:
    raw_input_url = st.session_state.url_input.strip() # Get the latest value and strip whitespace

    # --- URL Preprocessing: Add https:// if missing ---
    processed_url = raw_input_url
    is_valid_input = True # Flag for validity
    if not (processed_url.startswith("http://") or processed_url.startswith("https://")):
        # Basic check to avoid prefixing things like "hello" or invalid chars
        # Require a dot to be considered a potential domain
        if '.' not in processed_url or ' ' in processed_url or '<' in processed_url or '>' in processed_url:
             st.error(f"Invalid input: '{raw_input_url}'. Please enter a valid website address (e.g., www.example.com).")
             st.session_state.pipeline_results = None
             st.session_state.last_run_url = "" # Clear last run URL
             processed_url = None # Flag as invalid
             is_valid_input = False
        else:
            processed_url = f"https://{processed_url}"
            st.info(f"Assuming HTTPS. Analyzing: {processed_url}", icon="ℹ️") # Inform user
    # --- End URL Preprocessing ---

    # Proceed only if URL processing didn't invalidate it
    if is_valid_input and processed_url:
        # Check if we need to re-run the analysis
        if processed_url != st.session_state.last_run_url or st.session_state.pipeline_results is None:
            st.session_state.pipeline_results = None # Clear previous results before new run
            st.session_state.last_run_url = processed_url # Store the URL we are *processing*

            print(f"Streamlit App: Starting analysis for URL: {processed_url}")
            with st.spinner("Analyzing website... This might take a minute or two..."):
                try:
                    # Call the pipeline function from modules/__init__.py
                    results = run_full_pipeline(processed_url) # Use the processed URL
                    st.session_state.pipeline_results = results

                    if results and results.get("success"):
                        st.success("Analysis complete!")
                    else:
                        st.error(f"Pipeline failed: {results.get('message', 'Unknown error')}")

                except Exception as e:
                    st.error(f"An unexpected error occurred during the pipeline execution: {e}")
                    st.session_state.pipeline_results = {"success": False, "message": f"App error: {e}"}
                    print(f"Streamlit App: Error running pipeline for {processed_url}: {e}")
                    # st.exception(e) # Uncomment for detailed traceback in app

        elif processed_url == st.session_state.last_run_url:
             # URL hasn't changed since last successful/failed run, show existing results
             st.info("Displaying previous results for this URL. Modify the URL and submit again to re-run.")

# --- Display Results (Story Left, Analysis Right) ---
if st.session_state.pipeline_results:
    results = st.session_state.pipeline_results
    if results.get("success"):
        st.subheader("📊 Analysis & Story"); st.markdown("---") # Divider
        col_story, col_analysis = st.columns([2, 1]) # Story gets more width

        with col_story:
            st.markdown("#### Generated Brand Story")
            # --- Reading Story Output ---
            story = results.get("story")
            if not story:
                 try:
                      # Attempt to read from file as a fallback (adjust path if needed)
                      output_story_path = os.path.abspath("output_story.txt")
                      if os.path.exists(output_story_path):
                           with open(output_story_path, "r", encoding="utf-8") as f: story = f.read()
                      else: story = None
                 except Exception as e:
                      st.warning(f"Could not read story file: {e}"); story = None
            # --- End Reading Story Output ---

            # --- Display Story ---
            if story:
                with st.container(): # Use container for better control if needed later
                    st.markdown(story)
            else: st.warning("Brand story could not be generated or found.")
            # --- End Display Story ---

        with col_analysis:
            st.markdown("#### Analysis Summary")
            analysis = results.get("analysis")
            if analysis and not analysis.get("error"):
                keywords = analysis.get("keywords", [])
                sentiment = analysis.get("sentiment", {})
                sentiment_label = sentiment.get('label', 'N/A'); sentiment_score = sentiment.get('score', 0.0)

                # Display Sentiment
                st.metric(label="Overall Sentiment", value=sentiment_label, delta=f"{sentiment_score:.2f} score", help="Sentiment analysis based on extracted text.")
                st.write("") # Spacer

                # Display Keywords List
                if keywords:
                    st.markdown("**Keywords Found:**")
                    st.info(f"{', '.join(keywords)}") # Display as comma-separated list in an info box
                else:
                    st.markdown("**Keywords Found:** N/A")
                st.write("") # Spacer

                # --- Generate and Display Word Cloud ---
                if keywords and WORDCLOUD_INSTALLED:
                    st.markdown("#### Keyword Cloud")
                    try:
                        # Combine keywords into a single string
                        text = " ".join(keywords)
                        # Generate word cloud object - adjust parameters as desired
                        # Using RGBA mode and None background for transparency attempt
                        # Using a colormap suitable for dark backgrounds
                        wordcloud = WordCloud(width=400, height=200,
                                              background_color=None, # Try transparency
                                              mode="RGBA", # Needed for transparency
                                              colormap='viridis', # Good contrast on dark
                                              max_words=100, # Limit number of words
                                              collocations=False # Avoid word pairs unless frequent
                                              ).generate(text)

                        # Display using matplotlib
                        fig, ax = plt.subplots()
                        # Set figure background to transparent
                        fig.patch.set_alpha(0.0)
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis("off")
                        # Set axes background to transparent
                        ax.patch.set_alpha(0.0)
                        # Display in Streamlit, making it fit the column width
                        st.pyplot(fig, use_container_width=True)

                    except Exception as e:
                        st.error(f"Error generating word cloud: {e}")
                        print(f"Word cloud generation error: {e}")

                elif keywords and not WORDCLOUD_INSTALLED:
                    # Message if libraries are not installed (already shown at top, but good fallback here)
                    st.markdown("#### Keyword Cloud")
                    st.info("Install 'wordcloud' and 'matplotlib' to view the keyword cloud visualization.")
                # --- End Word Cloud ---

            elif analysis and analysis.get("error"):
                 st.warning(f"Analysis step had issues: {analysis.get('error')}")
            else:
                 st.info("Analysis results not available.") # If analysis dict is missing entirely

            # --- Display Social Links with Icons ---
            st.markdown("---") # Divider before social links
            st.markdown("#### Social Links Found")
            social_links = results.get("social_links", {})
            if social_links:
                # Loop to display icons using local images
                for platform, link in social_links.items():
                    platform_key = platform.lower()
                    # Handle common variations if needed (e.g., 'x' vs 'twitter')
                    if platform_key == 'x': platform_key = 'twitter'

                    icon_path = SOCIAL_ICON_PATHS.get(platform_key)
                    html_content = ""

                    if icon_path and os.path.exists(icon_path):
                        try:
                            # Read image and encode to base64
                            with open(icon_path, "rb") as img_f:
                                img_bytes = img_f.read()
                            encoded_img = base64.b64encode(img_bytes).decode()
                            img_ext = os.path.splitext(icon_path)[1].lower().strip('.')
                            if not img_ext: img_ext = 'png' # Default if no extension

                            # Create HTML for the linked image icon + text
                            # Link the whole container div content (icon + text)
                            html_content = f"""
                            <div class="social-link-container">
                                <a href="{link}" target="_blank" title="{platform} Link">
                                    <img src="data:image/{img_ext};base64,{encoded_img}" class="social-icon" alt="{platform} Icon">
                                    <span>{platform}</span>
                                </a>
                            </div>
                            """
                        except Exception as e:
                            print(f"Error encoding/processing icon {icon_path}: {e}")
                            # Fallback to text link with generic icon if encoding fails
                            html_content = f'<div class="social-link-container"><a href="{link}" target="_blank"><span>🔗 {platform}</span></a></div>'
                    else:
                        # Fallback to text link with generic icon if icon path not found or file doesn't exist
                        print(f"Warning: Icon not found for {platform} at path: {icon_path}")
                        html_content = f'<div class="social-link-container"><a href="{link}" target="_blank"><span>🔗 {platform}</span></a></div>'

                    st.markdown(html_content, unsafe_allow_html=True)
                # --- End loop ---
            else:
                st.write("No social media links found.")
            # --- End Social Links ---

        # Raw Text Expander (below both columns)
        st.markdown("---") # Divider before raw text
        website_text = results.get("website_text", "")
        if website_text:
             with st.expander("📄 View Raw Fetched Website Text", expanded=False):
                  st.text_area("Website Text", website_text, height=250, key="website_text_area")

    else:
        # Display failure message if pipeline_results exists but success is False
        st.error(f"Analysis Failed: {results.get('message', 'An unknown error occurred in the backend pipeline.')}")

elif submit_button and not st.session_state.url_input:
    # This case handles clicking the button/pressing Enter with an empty input field
    st.warning("Please enter a URL above.")

# --- End Output Section ---