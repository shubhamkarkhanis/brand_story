# app.py
# Streamlit frontend for the Brand Story Generator
# *** V14 + Re-added Tone Selection ***
# *** V15: Added PDF Generation and Download Button ***
# *** V16: Combined PDF Gen/Download into single button flow ***

import streamlit as st
import time
import os
import sys
import base64 # For background and social icons
import subprocess # For PDF generation call

# --- Attempt to import the pipeline function ---
try:
    from modules import run_full_pipeline
except ImportError as e:
    st.error(f"Fatal Error: Could not import pipeline function: {e}")
    st.error("Ensure 'app.py' is in the project root, the 'modules' directory with '__init__.py' exists, and 'run_full_pipeline' accepts 'desired_tone'.")
    st.stop()

# --- Optional Imports for Word Cloud ---
try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    WORDCLOUD_INSTALLED = True
except ImportError:
    WORDCLOUD_INSTALLED = False
# --- End Optional Imports ---


# --- Page Configuration ---
st.set_page_config(
    page_title="Brand Story Generator",
    page_icon="🚀",
    layout="wide"
)

# --- Function to generate Main Background CSS ---
# (Assuming this function exists as provided before)
def get_main_background_css(img_file):
    """ Generates CSS for the main background using a local file. """
    if not os.path.exists(img_file):
        print(f"Warning: Main background image file not found: {img_file}. Using fallback color.")
        return """div[data-testid="stAppViewContainer"] > .main { background-color: #0E1117; }"""
    try:
        with open(img_file, "rb") as f: img_bytes = f.read()
        encoded_img = base64.b64encode(img_bytes).decode()
        img_ext = os.path.splitext(img_file)[1].lower().strip('.') or 'jpg'
        main_bg_css = f"""
        div[data-testid="stAppViewContainer"] > .main {{
            background: url(data:image/{img_ext};base64,{encoded_img});
            background-size: cover; background-position: center center;
            background-repeat: no-repeat; background-attachment: fixed;
            background-color: #0E1117; /* Fallback */
        }}"""
        # print(f"Main background CSS generated using: {img_file}") # Reduce console noise
        return main_bg_css
    except Exception as e:
        print(f"Error generating main background CSS: {e}")
        return """div[data-testid="stAppViewContainer"] > .main { background-color: #0E1117; }"""

# --- Apply Backgrounds ---
main_image_path = 'assets/bg.jpg' # Ensure this path is correct
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
.social-icon {{ width: 24px; height: 24px; vertical-align: middle; margin-right: 8px; transition: filter 0.2s ease-in-out; }}
.social-icon:hover {{ filter: brightness(1.2); }}
.social-link-container {{ margin-bottom: 8px; display: flex; align-items: center; }}
.social-link-container a, .social-link-container a:visited {{ color: inherit; text-decoration: none; display: inline-flex; align-items: center; }}
.social-link-container span {{ margin-left: 5px; }}
.stPlotlyChart, .stpyplot {{ background-color: transparent !important; }}
.centered-content {{ display: flex; flex-direction: column; align-items: center; }}

/* Center buttons within their containers */
div[data-testid="stButton"], div[data-testid="stDownloadButton"] {{
    display: flex;
    justify-content: center;
}}
/* Container for PDF button area */
.pdf-button-area {{
    margin-top: 20px;
    margin-bottom: 10px;
}}

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
}
# --- End Social Icon Paths ---


# --- Centered Input Section ---
_left_margin, main_content_col, _right_margin = st.columns([1, 2, 1])

# Initialize session state variables
if 'pipeline_results' not in st.session_state: st.session_state.pipeline_results = None
if 'last_run_url' not in st.session_state: st.session_state.last_run_url = ""
if 'url_input' not in st.session_state: st.session_state.url_input = ""
if 'selected_tone' not in st.session_state: st.session_state.selected_tone = "Default"
if 'last_run_tone' not in st.session_state: st.session_state.last_run_tone = "Default"
# PDF related state
if 'pdf_generation_triggered' not in st.session_state: st.session_state.pdf_generation_triggered = False
if 'pdf_path' not in st.session_state: st.session_state.pdf_path = None
if 'pdf_error' not in st.session_state: st.session_state.pdf_error = None

TONE_OPTIONS = ["Default", "Formal", "Casual", "Enthusiastic", "Witty", "Professional", "Concise", "Inspirational"]

with main_content_col:
    st.markdown("<h1 style='text-align: center; color: white;'>🚀 AI Brand Story Generator</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #e0e0e0;'>Enter a website URL, select a tone, and generate a brand story.</p>", unsafe_allow_html=True)
    st.write("")

    with st.form("input_form", clear_on_submit=False):
        input_url_from_form = st.text_input(
            "Company Website URL", value=st.session_state.url_input,
            placeholder="e.g., www.example.com", key="company_url_input_form",
            label_visibility="collapsed"
        )
        st.session_state.url_input = input_url_from_form

        selected_tone_option = st.selectbox(
            "Select Story Tone:", options=TONE_OPTIONS,
            key="tone_select_key",
            index=TONE_OPTIONS.index(st.session_state.selected_tone)
        )
        st.session_state.selected_tone = selected_tone_option

        st.write("")
        submit_button = st.form_submit_button(
            "✨ Analyze & Generate Story", type="primary", use_container_width=True
        )

st.divider()
# --- End Centered Input Section ---


# --- Output Section & Run Pipeline Logic ---

# Process the form submission
if submit_button and st.session_state.url_input:
    raw_input_url = st.session_state.url_input.strip()
    current_selected_tone = st.session_state.selected_tone

    processed_url = raw_input_url
    is_valid_input = True
    if not (processed_url.startswith("http://") or processed_url.startswith("https://")):
        if '.' not in processed_url or ' ' in processed_url or '<' in processed_url or '>' in processed_url:
            st.error(f"Invalid input: '{raw_input_url}'. Please enter a valid website address.")
            st.session_state.pipeline_results = None; st.session_state.last_run_url = ""
            st.session_state.last_run_tone = "Default"; st.session_state.pdf_path = None # Reset PDF state
            st.session_state.pdf_error = None; st.session_state.pdf_generation_triggered = False
            processed_url = None; is_valid_input = False
        else:
            processed_url = f"https://{processed_url}"
            st.info(f"Assuming HTTPS. Analyzing: {processed_url}", icon="ℹ️")

    if is_valid_input and processed_url:
        needs_rerun = (
            processed_url != st.session_state.last_run_url or
            current_selected_tone != st.session_state.last_run_tone or
            st.session_state.pipeline_results is None
        )

        if needs_rerun:
            st.session_state.pipeline_results = None # Clear previous results
            st.session_state.pdf_path = None # Reset PDF state on new run
            st.session_state.pdf_error = None
            st.session_state.pdf_generation_triggered = False
            st.session_state.last_run_url = processed_url
            st.session_state.last_run_tone = current_selected_tone
            tone_to_pass = None if current_selected_tone == "Default" else current_selected_tone

            print(f"Streamlit App: Starting analysis for URL: {processed_url} with Tone: {current_selected_tone}")
            with st.spinner(f"Analyzing website with '{current_selected_tone}' tone... This might take a minute..."):
                try:
                    # IMPORTANT: Assumes run_full_pipeline returns a dict with results
                    results = run_full_pipeline(processed_url, desired_tone=tone_to_pass)
                    st.session_state.pipeline_results = results
                    if results and results.get("success"): st.success("Analysis complete!")
                    else: st.error(f"Pipeline failed: {results.get('message', 'Unknown error')}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during the pipeline execution: {e}")
                    st.session_state.pipeline_results = {"success": False, "message": f"App error: {e}"}
                    print(f"Streamlit App: Error running pipeline for {processed_url}: {e}")
                    # st.exception(e)

        elif processed_url == st.session_state.last_run_url and current_selected_tone == st.session_state.last_run_tone:
             st.info("Displaying previous results for this URL and Tone. Change URL or Tone and submit again to re-run.")

# --- Display Results ---
if st.session_state.pipeline_results:
    results = st.session_state.pipeline_results
    if results.get("success"):
        st.subheader(f"📊 Analysis & Story (Tone: {st.session_state.last_run_tone})")
        st.markdown("---")
        col_story, col_analysis = st.columns([2, 1])

        with col_story:
            st.markdown("#### Generated Brand Story")
            story = results.get("story")
            # Fallback read from file (ensure generator saves to export.md now)
            if not story:
                 try:
                      output_story_path = os.path.abspath("export.md") # Read the MD file
                      if os.path.exists(output_story_path):
                           with open(output_story_path, "r", encoding="utf-8") as f: story = f.read()
                      else: story = None
                 except Exception as e:
                      print(f"Warning: Could not read story file 'export.md': {e}"); story = None

            if story:
                with st.container(): st.markdown(story)

                # --- PDF Download Area ---
                st.write("") # Add space
                pdf_button_area = st.empty() # Placeholder for button/download/error

                with pdf_button_area.container():
                    # Check if PDF is ready from a previous click in this session
                    if st.session_state.get('pdf_path') and os.path.exists(st.session_state.pdf_path):
                         try:
                             with open(st.session_state.pdf_path, "rb") as pdf_file:
                                 pdf_bytes = pdf_file.read()
                             # Use columns to center download button
                             _d1, d_col, _d2 = st.columns([1,2,1])
                             with d_col:
                                  st.download_button(
                                      label="⬇️ Download PDF Report",
                                      data=pdf_bytes,
                                      file_name="BrandStoryReport.pdf", # User-friendly name
                                      mime="application/pdf",
                                      key="download_pdf_btn",
                                      use_container_width=True
                                  )
                         except Exception as e:
                              st.error(f"Error reading PDF for download: {e}")
                              st.session_state.pdf_path = None # Reset state
                    # Display error if PDF generation failed on last attempt
                    elif st.session_state.pdf_error:
                         st.error(st.session_state.pdf_error)
                         # Optionally add a retry button here
                         _b1, b_col, _b2 = st.columns([1,2,1])
                         with b_col:
                              if st.button("Retry PDF Generation", key="retry_pdf_btn", use_container_width=True):
                                   st.session_state.pdf_generation_triggered = True
                                   st.session_state.pdf_error = None # Clear error for retry
                                   st.rerun() # Rerun to trigger generation logic below
                    # Otherwise, display the initial button to generate/download
                    else:
                         # Use columns to center the button
                         _b1, b_col, _b2 = st.columns([1,2,1])
                         with b_col:
                              if st.button("⬇️ Generate & Download PDF", key="gen_and_download_pdf_btn", use_container_width=True):
                                   st.session_state.pdf_generation_triggered = True
                                   st.rerun() # Rerun immediately to trigger PDF generation

                # --- PDF Generation Logic (runs if triggered) ---
                if st.session_state.get('pdf_generation_triggered', False):
                    # Reset trigger immediately to prevent re-running on next interaction
                    st.session_state.pdf_generation_triggered = False
                    st.session_state.pdf_path = None # Reset path
                    st.session_state.pdf_error = None # Clear previous error

                    with st.spinner("Generating PDF..."):
                        export_script_path = 'exportpdf.py' # Assuming it's in root
                        pdf_output_path = os.path.abspath("export.pdf")
                        command = [sys.executable, export_script_path]
                        print(f"Running command: {' '.join(command)}")
                        try:
                            # Run exportpdf.py script
                            pdf_process = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', timeout=30)
                            print(f"[✓] {export_script_path} executed successfully.")
                            if os.path.exists(pdf_output_path):
                                 st.session_state.pdf_path = pdf_output_path # Store path if successful
                                 st.session_state.pdf_error = None
                            else:
                                 st.session_state.pdf_error = "PDF generation script ran but output file was not found."
                                 st.session_state.pdf_path = None
                            st.rerun() # Rerun to display download button or error

                        except FileNotFoundError:
                            st.session_state.pdf_error = f"Error: PDF generation script not found at '{export_script_path}'"
                        except subprocess.TimeoutExpired:
                             st.session_state.pdf_error = "Error: PDF generation timed out."
                        except subprocess.CalledProcessError as e:
                            st.session_state.pdf_error = f"Error: PDF generation script failed (Code: {e.returncode}). See console logs."
                            print(f"PDF Generation Error Output:\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
                        except Exception as e:
                            st.session_state.pdf_error = f"An unexpected error occurred during PDF generation: {e}"
                            print(f"Unexpected PDF Generation Error: {e}")

                        # If we got here due to an error, rerun to display the error message
                        if st.session_state.pdf_error:
                             st.rerun()
                # --- End PDF Generation Logic ---
                # --- End PDF Download Area ---

            else: st.warning("Brand story could not be generated or found.")

        with col_analysis:
            # (Analysis display logic remains the same)
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
                # Word Cloud
                if keywords and WORDCLOUD_INSTALLED:
                    st.markdown("#### Keyword Cloud")
                    try:
                        text = " ".join(keywords)
                        wordcloud = WordCloud(width=400, height=200, background_color=None, mode="RGBA", colormap='viridis', max_words=100, collocations=False).generate(text)
                        fig, ax = plt.subplots(); fig.patch.set_alpha(0.0); ax.patch.set_alpha(0.0)
                        ax.imshow(wordcloud, interpolation='bilinear'); ax.axis("off")
                        st.pyplot(fig, use_container_width=True)
                    except Exception as e: st.error(f"Error generating word cloud: {e}"); print(f"Word cloud error: {e}")
                elif keywords and not WORDCLOUD_INSTALLED: st.markdown("#### Keyword Cloud"); st.info("Install 'wordcloud' and 'matplotlib' to view.")
            elif analysis and analysis.get("error"): st.warning(f"Analysis step had issues: {analysis.get('error')}")
            else: st.info("Analysis results not available.")
            # Social Links
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
                        except Exception as e: print(f"Error encoding icon {icon_path}: {e}"); html_content = f'<div class="social-link-container"><a href="{link}" target="_blank"><span>🔗 {platform}</span></a></div>'
                    else: print(f"Warning: Icon not found for {platform} at path: {icon_path}"); html_content = f'<div class="social-link-container"><a href="{link}" target="_blank"><span>🔗 {platform}</span></a></div>'
                    st.markdown(html_content, unsafe_allow_html=True)
            else: st.write("No social media links found.")

        # Raw Text Expander
        st.markdown("---")
        website_text = results.get("website_text", "")
        if website_text:
             with st.expander("📄 View Raw Fetched Website Text", expanded=False):
                  st.text_area("Website Text", website_text, height=250, key="website_text_area", disabled=True)

    else: st.error(f"Analysis Failed: {results.get('message', 'An unknown error occurred in the backend pipeline.')}")
elif submit_button and not st.session_state.url_input: st.warning("Please enter a URL above.")
# --- End Output Section ---

