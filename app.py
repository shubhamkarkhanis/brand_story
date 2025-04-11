# app.py
# Streamlit frontend for the Brand Story Generator
# *** V14 + Re-added Tone Selection ***

import streamlit as st
import time
import os
import sys
import base64 # For background and social icons
# import re # No longer needed for highlighting

# --- Attempt to import the pipeline function ---
try:
    # Assumes app.py is in root, modules/ is sibling
    # Assumes run_full_pipeline accepts 'desired_tone' argument
    from modules import run_full_pipeline
except ImportError as e:
    st.error(f"Fatal Error: Could not import pipeline function: {e}")
    st.error("Ensure 'app.py' is in the project root, the 'modules' directory with '__init__.py' exists, and 'run_full_pipeline' accepts 'desired_tone'.")
    st.stop() # Stop the streamlit app if import fails

# --- Optional Imports for Word Cloud ---
try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    WORDCLOUD_INSTALLED = True
except ImportError:
    WORDCLOUD_INSTALLED = False
    # Don't show warning at the top level, check later if needed
    # st.warning("Optional libraries 'wordcloud' and 'matplotlib' not found...", icon="⚠️")
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
}}

/* Style for social icons */
.social-icon {{
    width: 24px; height: 24px;
    vertical-align: middle;
    margin-right: 8px;
    transition: filter 0.2s ease-in-out;
}}
.social-icon:hover {{ filter: brightness(1.2); }}
.social-link-container {{
    margin-bottom: 8px; display: flex; align-items: center;
}}
.social-link-container a, .social-link-container a:visited {{
    color: inherit; text-decoration: none; display: inline-flex; align-items: center;
}}
.social-link-container span {{ margin-left: 5px; }}

/* Ensure matplotlib plots have a transparent background */
.stPlotlyChart, .stpyplot {{ background-color: transparent !important; }}

/* Center align elements within the main content column (kept for structure) */
.centered-content {{ display: flex; flex-direction: column; align-items: center; }}

</style>
""", unsafe_allow_html=True)
# --- End Custom CSS ---

# --- Social Icon Paths ---
SOCIAL_ICON_PATHS = {
    "linkedin": "assets/linkedin.png", "twitter": "assets/twitter.png",
    "x": "assets/twitter.png", "facebook": "assets/facebook.png",
    "youtube": "assets/youtube.png", "instagram": "assets/instagram.png",
    "pinterest": "assets/pinterest.png", "tiktok": "assets/tiktok.png",
    "github": "assets/github.png",
    # "default": "assets/default_link.png" # Optional default
}
# --- End Social Icon Paths ---


# --- Centered Input Section ---
_left_margin, main_content_col, _right_margin = st.columns([1, 2, 1]) # Adjust ratios if needed

# Initialize session state variables
if 'pipeline_results' not in st.session_state: st.session_state.pipeline_results = None
if 'last_run_url' not in st.session_state: st.session_state.last_run_url = ""
if 'url_input' not in st.session_state: st.session_state.url_input = ""
# --- Add Tone State ---
if 'selected_tone' not in st.session_state: st.session_state.selected_tone = "Default" # Default tone
if 'last_run_tone' not in st.session_state: st.session_state.last_run_tone = "Default"
# --- End Tone State ---

# Define tone options
TONE_OPTIONS = ["Default", "Formal", "Casual", "Enthusiastic", "Witty", "Professional", "Concise", "Inspirational"]


# Use a form for Enter key submission
with main_content_col:
    st.markdown("<h1 style='text-align: center; color: white;'>🚀 AI Brand Story Generator</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #e0e0e0;'>Enter a website URL, select a tone, and generate a brand story.</p>", unsafe_allow_html=True)
    st.write("") # Vertical space

    with st.form("input_form", clear_on_submit=False):
        # URL Input
        input_url_from_form = st.text_input(
            "Company Website URL",
            value=st.session_state.url_input,
            placeholder="e.g., www.example.com",
            key="company_url_input_form",
            label_visibility="collapsed"
        )
        # Update session state immediately for persistence
        st.session_state.url_input = input_url_from_form

        # --- Add Tone Selector ---
        selected_tone_option = st.selectbox(
            "Select Story Tone:",
            options=TONE_OPTIONS,
            key="tone_select_key", # Unique key for the selectbox widget
            index=TONE_OPTIONS.index(st.session_state.selected_tone), # Set default from session state
            # label_visibility="collapsed" # Optional: Hide label if context is clear
        )
        # Update session state when the selectbox value changes
        st.session_state.selected_tone = selected_tone_option
        # --- End Tone Selector ---

        st.write("") # Vertical space before button

        # Form Submit Button
        submit_button = st.form_submit_button(
            "✨ Analyze & Generate Story",
            type="primary",
            use_container_width=True
        )

st.divider()
# --- End Centered Input Section ---


# --- Output Section & Run Pipeline Logic ---

# Process the form submission *after* the form definition
if submit_button and st.session_state.url_input:
    raw_input_url = st.session_state.url_input.strip()
    current_selected_tone = st.session_state.selected_tone # Get current tone selection

    # --- URL Preprocessing ---
    processed_url = raw_input_url
    is_valid_input = True
    if not (processed_url.startswith("http://") or processed_url.startswith("https://")):
        if '.' not in processed_url or ' ' in processed_url or '<' in processed_url or '>' in processed_url:
            st.error(f"Invalid input: '{raw_input_url}'. Please enter a valid website address.")
            st.session_state.pipeline_results = None
            st.session_state.last_run_url = ""
            st.session_state.last_run_tone = "Default" # Reset last run tone on error too
            processed_url = None
            is_valid_input = False
        else:
            processed_url = f"https://{processed_url}"
            st.info(f"Assuming HTTPS. Analyzing: {processed_url}", icon="ℹ️")
    # --- End URL Preprocessing ---

    if is_valid_input and processed_url:
        # --- Check if URL or Tone has changed, requiring a re-run ---
        needs_rerun = (
            processed_url != st.session_state.last_run_url or
            current_selected_tone != st.session_state.last_run_tone or
            st.session_state.pipeline_results is None
        )

        if needs_rerun:
            st.session_state.pipeline_results = None # Clear previous results
            st.session_state.last_run_url = processed_url # Store URL for this run
            st.session_state.last_run_tone = current_selected_tone # Store Tone for this run

            # Map "Default" UI option to None for the backend function
            tone_to_pass = None if current_selected_tone == "Default" else current_selected_tone

            print(f"Streamlit App: Starting analysis for URL: {processed_url} with Tone: {current_selected_tone}")
            with st.spinner(f"Analyzing website with '{current_selected_tone}' tone... This might take a minute..."):
                try:
                    # *** Call the pipeline with the selected tone ***
                    results = run_full_pipeline(processed_url, desired_tone=tone_to_pass)
                    st.session_state.pipeline_results = results

                    if results and results.get("success"):
                        st.success("Analysis complete!")
                    else:
                        st.error(f"Pipeline failed: {results.get('message', 'Unknown error')}")

                except Exception as e:
                    st.error(f"An unexpected error occurred during the pipeline execution: {e}")
                    st.session_state.pipeline_results = {"success": False, "message": f"App error: {e}"}
                    print(f"Streamlit App: Error running pipeline for {processed_url}: {e}")
                    # st.exception(e) # Uncomment for detailed traceback

        elif processed_url == st.session_state.last_run_url and current_selected_tone == st.session_state.last_run_tone:
            st.info("Displaying previous results for this URL and Tone. Change URL or Tone and submit again to re-run.")

# --- Display Results ---
if st.session_state.pipeline_results:
    results = st.session_state.pipeline_results
    if results.get("success"):
        # Use the 'last_run_tone' from session state for consistency in display
        st.subheader(f"📊 Analysis & Story (Tone: {st.session_state.last_run_tone})")
        st.markdown("---")
        col_story, col_analysis = st.columns([2, 1])

        with col_story:
            st.markdown("#### Generated Brand Story")
            story = results.get("story")
            # Fallback read from file (optional, can be removed if pipeline always returns story)
            if not story:
                try:
                    output_story_path = os.path.abspath("output_story.txt")
                    if os.path.exists(output_story_path):
                        with open(output_story_path, "r", encoding="utf-8") as f: story = f.read()
                    else: story = None
                except Exception as e:
                    print(f"Warning: Could not read story file: {e}"); story = None

            if story:
                with st.container(): st.markdown(story)
            else: st.warning("Brand story could not be generated or found.")

        with col_analysis:
            st.markdown("#### Analysis Summary")
            analysis = results.get("analysis")
            if analysis and not analysis.get("error"):
                keywords = analysis.get("keywords", [])
                sentiment = analysis.get("sentiment", {})
                sentiment_label = sentiment.get('label', 'N/A'); sentiment_score = sentiment.get('score', 0.0)

                st.metric(label="Overall Sentiment", value=sentiment_label, delta=f"{sentiment_score:.2f} score", help="Sentiment analysis based on extracted text.")
                st.write("")

                if keywords:
                    st.markdown("**Keywords Found:**"); st.info(f"{', '.join(keywords)}")
                else: st.markdown("**Keywords Found:** N/A")
                st.write("")

                # --- Word Cloud ---
                if keywords and WORDCLOUD_INSTALLED:
                    st.markdown("#### Keyword Cloud")
                    try:
                        text = " ".join(keywords)
                        wordcloud = WordCloud(width=400, height=200, background_color=None, mode="RGBA", colormap='viridis', max_words=100, collocations=False).generate(text)
                        fig, ax = plt.subplots()
                        fig.patch.set_alpha(0.0); ax.patch.set_alpha(0.0) # Transparency
                        ax.imshow(wordcloud, interpolation='bilinear'); ax.axis("off")
                        st.pyplot(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error generating word cloud: {e}"); print(f"Word cloud error: {e}")
                elif keywords and not WORDCLOUD_INSTALLED:
                    st.markdown("#### Keyword Cloud"); st.info("Install 'wordcloud' and 'matplotlib' to view.")
                # --- End Word Cloud ---

            elif analysis and analysis.get("error"): st.warning(f"Analysis step had issues: {analysis.get('error')}")
            else: st.info("Analysis results not available.")

            # --- Social Links ---
            st.markdown("---"); st.markdown("#### Social Links Found")
            social_links = results.get("social_links", {})
            if social_links:
                for platform, link in social_links.items():
                    platform_key = platform.lower(); icon_path = SOCIAL_ICON_PATHS.get(platform_key)
                    html_content = ""
                    if icon_path and os.path.exists(icon_path):
                        try:
                            with open(icon_path, "rb") as img_f: img_bytes = img_f.read()
                            encoded_img = base64.b64encode(img_bytes).decode()
                            img_ext = os.path.splitext(icon_path)[1].lower().strip('.') or 'png'
                            html_content = f'<div class="social-link-container"><a href="{link}" target="_blank" title="{platform} Link"><img src="data:image/{img_ext};base64,{encoded_img}" class="social-icon" alt="{platform} Icon"><span>{platform}</span></a></div>'
                        except Exception as e:
                            print(f"Error encoding icon {icon_path}: {e}"); html_content = f'<div class="social-link-container"><a href="{link}" target="_blank"><span>🔗 {platform}</span></a></div>'
                    else:
                        print(f"Warning: Icon not found for {platform} at path: {icon_path}"); html_content = f'<div class="social-link-container"><a href="{link}" target="_blank"><span>🔗 {platform}</span></a></div>'
                    st.markdown(html_content, unsafe_allow_html=True)
            else: st.write("No social media links found.")
            # --- End Social Links ---

        # Raw Text Expander
        st.markdown("---")
        website_text = results.get("website_text", "")
        if website_text:
            with st.expander("📄 View Raw Fetched Website Text", expanded=False):
                st.text_area("Website Text", website_text, height=250, key="website_text_area", disabled=True) # Disable editing

    else:
        st.error(f"Analysis Failed: {results.get('message', 'An unknown error occurred in the backend pipeline.')}")

elif submit_button and not st.session_state.url_input:
    st.warning("Please enter a URL above.")
# --- End Output Section ---
