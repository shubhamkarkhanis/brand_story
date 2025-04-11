# app.py
# Streamlit frontend for the Brand Story Generator
# *** V3: Centered Input Section + Button Below Input + Constrained Width ***
# *** V4: Removed Keyword Highlighting ***
# *** V5: Added Image Background ***
# *** V6: Adjusted CSS target for background image ***
# *** V7: Added Sidebar Background Image Functionality ***
# *** V8: Use Local Image for Main Background via Base64 ***
# *** V9: Removed Sidebar Background Functionality ***
# *** V10: Removed Main Background Image Functionality ***
# *** V11: Added Social Media Icons ***
# *** V12: Use Local Image Files for Social Icons via Base64 ***

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
        if img_ext not in ["png", "jpg", "jpeg", "gif", "webp", "svg"]:
             if img_ext not in ["jpeg", "gif", "svg", "webp"]: img_ext = "jpg"
        main_bg_css = f"""
        div[data-testid="stAppViewContainer"] > .main {{
            background: url(data:image/{img_ext};base64,{encoded_img});
            background-size: cover; background-position: center center;
            background-repeat: no-repeat; background-attachment: fixed;
            background-color: #0E1117; /* Fallback */
        }}"""
        print(f"Main background CSS generated using: {img_file}")
        return main_bg_css
    except Exception as e:
        print(f"Error generating main background CSS: {e}")
        return """
        div[data-testid="stAppViewContainer"] > .main {
            background-color: #0E1117; /* Fallback color */
        }"""

# --- Apply Backgrounds ---
main_image_path = 'assets/bg.jpg'
main_bg_css_rule = get_main_background_css(main_image_path)

# --- Inject All Custom CSS ---
st.markdown(f"""
<style>
/* --- Main Background CSS (dynamically generated) --- */
{main_bg_css_rule}

/* --- Other Styles --- */
div[data-testid="stAppViewContainer"] > .main .block-container {{
    padding-top: 3rem; padding-bottom: 5rem;
    padding-left: 2rem; padding-right: 2rem;
    background: none;
}}
.centered-content {{ display: flex; flex-direction: column; align-items: center; }}
div[data-testid="stButton"] {{ display: flex; justify-content: center; }}

/* Style for social icons */
.social-icon {{
    width: 24px;      /* Adjust size as needed */
    height: 24px;     /* Adjust size as needed */
    vertical-align: middle;
    margin-right: 8px; /* Space between icon and text (optional) */
}}
.social-link-container {{
    margin-bottom: 8px; /* Space between links */
    display: flex;       /* Use flexbox for alignment */
    align-items: center; /* Align icon and text vertically */
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
    "facebook": "assets/facebook.png", # Assuming you have facebook.png
    "youtube": "assets/youtube.png",
    "instagram": "assets/instagram.png", # Assuming you have instagram.png
    "pinterest": "assets/pinterest.png", # Assuming you have pinterest.png
    "tiktok": "assets/tiktok.png",
    # Add other platforms and their corresponding image paths here
    # "default": "assets/default_link.png" # Optional default icon
}
# --- End Social Icon Paths ---


# --- Centered Input Section ---
_left_margin, main_content_col, _right_margin = st.columns([1, 2, 1])
with main_content_col:
    st.markdown("<h1 style='text-align: center;'>🚀 AI Brand Story Generator</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Enter a company's website URL to analyze its online presence and generate a brand story.</p>", unsafe_allow_html=True)
    st.write("")
    if 'url_input' not in st.session_state: st.session_state.url_input = ""
    input_url = st.text_input(
        "Company Website URL", value=st.session_state.url_input,
        placeholder="e.g., https://www.example.com", key="company_url_input",
        label_visibility="collapsed"
    )
    st.session_state.url_input = input_url
    st.write("")
    analyze_button = st.button("✨ Analyze & Generate Story", key="analyze_button", type="primary", use_container_width=True)
st.divider()
# --- End Centered Input Section ---


# --- Output Section ---
if 'pipeline_results' not in st.session_state: st.session_state.pipeline_results = None
if 'last_run_url' not in st.session_state: st.session_state.last_run_url = ""

# --- Run Pipeline Logic ---
if analyze_button and input_url:
    if input_url != st.session_state.last_run_url or st.session_state.pipeline_results is None:
        if not (input_url.startswith("http://") or input_url.startswith("https://")):
            st.error("Invalid URL. Please enter a full URL starting with http:// or https://")
            st.session_state.pipeline_results = None; st.session_state.last_run_url = ""
        else:
            st.session_state.pipeline_results = None; st.session_state.last_run_url = input_url
            print(f"Streamlit App: Starting analysis for URL: {input_url}")
            with st.spinner("Analyzing website... This might take a minute or two..."):
                try:
                    results = run_full_pipeline(input_url)
                    st.session_state.pipeline_results = results
                    if results and results.get("success"): st.success("Analysis complete!")
                    else: st.error(f"Pipeline failed: {results.get('message', 'Unknown error')}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during the pipeline execution: {e}")
                    st.session_state.pipeline_results = {"success": False, "message": f"App error: {e}"}
                    print(f"Streamlit App: Error running pipeline for {input_url}: {e}")
                    # st.exception(e)

    elif input_url == st.session_state.last_run_url:
         st.info("Displaying previous results for this URL. Enter a new URL or click button again to re-run.")

# --- Display Results (Story Left, Analysis Right) ---
if st.session_state.pipeline_results:
    results = st.session_state.pipeline_results
    if results.get("success"):
        st.subheader("📊 Analysis & Story"); st.markdown("---")
        col_story, col_analysis = st.columns([2, 1])
        with col_story:
            st.markdown("#### Generated Brand Story")
            story = results.get("story")
            if not story:
                 try:
                      output_story_path = os.path.abspath("output_story.txt")
                      if os.path.exists(output_story_path):
                           with open(output_story_path, "r", encoding="utf-8") as f: story = f.read()
                      else: story = None
                 except Exception as e:
                      st.warning(f"Could not read story file: {e}"); story = None
            if story:
                with st.container(): st.markdown(story)
            else: st.warning("Brand story could not be generated or found.")
        with col_analysis:
            st.markdown("#### Analysis Summary")
            analysis = results.get("analysis")
            if analysis and not analysis.get("error"):
                keywords = analysis.get("keywords", []); sentiment = analysis.get("sentiment", {})
                sentiment_label = sentiment.get('label', 'N/A'); sentiment_score = sentiment.get('score', 0.0)
                st.metric(label="Overall Sentiment", value=sentiment_label, delta=f"{sentiment_score:.2f} score", help="Sentiment analysis based on extracted text.")
                st.write("")
                if keywords: st.markdown("**Keywords Found:**"); st.info(f"{', '.join(keywords)}")
                else: st.markdown("**Keywords Found:** N/A")
                st.write("")
            elif analysis and analysis.get("error"): st.warning(f"Analysis step had issues: {analysis.get('error')}")
            else: st.info("Analysis results not available.")

            st.markdown("---"); st.markdown("#### Social Links Found")
            social_links = results.get("social_links", {})
            if social_links:
                # --- Loop to display icons using local images ---
                for platform, link in social_links.items():
                    platform_key = platform.lower()
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

                            # Create HTML for the linked image icon
                            html_content = f"""
                            <div class="social-link-container">
                                <a href="{link}" target="_blank" title="{platform} Link">
                                    <img src="data:image/{img_ext};base64,{encoded_img}" class="social-icon" alt="{platform} Icon">
                                </a>
                                <span style="margin-left: 5px;">{platform}</span>
                            </div>
                            """
                        except Exception as e:
                            print(f"Error encoding/processing icon {icon_path}: {e}")
                            # Fallback to text link if encoding fails
                            html_content = f'<div class="social-link-container"><span>🔗</span> <a href="{link}" target="_blank">{platform}</a></div>'
                    else:
                        # Fallback to text link if icon path not found or file doesn't exist
                        print(f"Warning: Icon not found for {platform} at path: {icon_path}")
                        html_content = f'<div class="social-link-container"><span>🔗</span> <a href="{link}" target="_blank">{platform}</a></div>'

                    st.markdown(html_content, unsafe_allow_html=True)
                # --- End loop ---
            else:
                st.write("No social media links found.")

        st.markdown("---")
        website_text = results.get("website_text", "")
        if website_text:
             with st.expander("📄 View Raw Fetched Website Text", expanded=False):
                  st.text_area("Website Text", website_text, height=250, key="website_text_area")
    else: st.error(f"Analysis Failed: {results.get('message', 'An unknown error occurred in the backend pipeline.')}")
elif analyze_button and not input_url: st.warning("Please enter a URL above.")

