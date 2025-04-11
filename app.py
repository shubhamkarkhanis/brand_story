# app.py
# Streamlit frontend for the Brand Story Generator
# *** V3: Centered Input Section + Button Below Input + Constrained Width ***
# *** V4: Removed Keyword Highlighting ***

import streamlit as st
import time # Used for simulating work if needed, st.spinner handles waits
import os
import sys
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

# --- Add Custom CSS for Background Gradient ---
# Removed .highlight-keyword style
st.markdown("""
<style>
/* Target the main block container */
div[data-testid="stAppViewContainer"] > .main .block-container {
    /* Subtle gradient */
    background-image: linear-gradient(180deg, #151F2B , #0E1117);
    background-size: cover;
    background-attachment: fixed;
    /* Adjust padding */
    padding-top: 3rem; /* Reduced top padding slightly */
    padding-bottom: 5rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* Center align elements within the main content column */
.centered-content {
    display: flex;
    flex-direction: column;
    align-items: center; /* Center items horizontally */
}

/* Style the button container for centering */
div[data-testid="stButton"] {
    display: flex;
    justify-content: center;
}

</style>
""", unsafe_allow_html=True)
# --- End Custom CSS ---

# --- Helper function for highlighting REMOVED ---
# def highlight_text(...): ...
# --- End Helper Function ---


# --- Centered Input Section ---
# Use columns to create margins and constrain the central content width
_left_margin, main_content_col, _right_margin = st.columns([1, 2, 1])

with main_content_col:
    # Use markdown for centered title and subtitle
    st.markdown("<h1 style='text-align: center;'>🚀 AI Brand Story Generator</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Enter a company's website URL to analyze its online presence and generate a brand story.</p>", unsafe_allow_html=True)
    st.write("") # Add some vertical space

    # Initialize session state for input persistence
    if 'url_input' not in st.session_state: st.session_state.url_input = ""

    # Text Input (will take width of main_content_col)
    input_url = st.text_input(
        "Company Website URL", # Label is useful here for context
        value=st.session_state.url_input,
        placeholder="e.g., https://www.example.com",
        key="company_url_input",
        label_visibility="collapsed" # Hide label visually, but keep for accessibility
    )
    st.session_state.url_input = input_url

    st.write("") # Add vertical space before button

    # Button - placed directly below input, centering handled by column/CSS
    analyze_button = st.button("✨ Analyze & Generate Story", key="analyze_button", type="primary", use_container_width=True) # use_container_width helps alignment

# Add a divider below the input section
st.divider()
# --- End Centered Input Section ---


# --- Output Section ---
# Initialize session state for results
if 'pipeline_results' not in st.session_state: st.session_state.pipeline_results = None
if 'last_run_url' not in st.session_state: st.session_state.last_run_url = ""

# --- Run Pipeline Logic ---
if analyze_button and input_url:
    if input_url != st.session_state.last_run_url or st.session_state.pipeline_results is None:
        if not (input_url.startswith("http://") or input_url.startswith("https://")):
            st.error("Invalid URL. Please enter a full URL starting with http:// or https://")
            st.session_state.pipeline_results = None
            st.session_state.last_run_url = ""
        else:
            st.session_state.pipeline_results = None
            st.session_state.last_run_url = input_url
            print(f"Streamlit App: Starting analysis for URL: {input_url}")
            with st.spinner("Analyzing website... This might take a minute or two..."):
                try:
                    # Call the pipeline function from modules/__init__.py
                    # Assumes run_full_pipeline returns a dictionary like:
                    # {'success': True/False, 'message': '...', 'story': '...', 'analysis': {...}, ...}
                    results = run_full_pipeline(input_url)
                    st.session_state.pipeline_results = results

                    if results and results.get("success"):
                        st.success("Analysis complete!")
                    else:
                        st.error(f"Pipeline failed: {results.get('message', 'Unknown error')}")

                except Exception as e:
                    st.error(f"An unexpected error occurred during the pipeline execution: {e}")
                    st.session_state.pipeline_results = {"success": False, "message": f"App error: {e}"}
                    print(f"Streamlit App: Error running pipeline for {input_url}: {e}")
                    # st.exception(e) # Uncomment for detailed traceback in app

    elif input_url == st.session_state.last_run_url:
         st.info("Displaying previous results for this URL. Enter a new URL or click button again to re-run.")

# --- Display Results (Story Left, Analysis Right) ---
if st.session_state.pipeline_results:
    results = st.session_state.pipeline_results

    if results.get("success"):
        st.subheader("📊 Analysis & Story")
        st.markdown("---")

        col_story, col_analysis = st.columns([2, 1])

        with col_story:
            st.markdown("#### Generated Brand Story")
            # --- Reading Story Output ---
            story = results.get("story")
            if not story:
                 try:
                      output_story_path = os.path.abspath("output_story.txt")
                      if os.path.exists(output_story_path):
                           with open(output_story_path, "r", encoding="utf-8") as f:
                                story = f.read()
                      else: story = None
                 except Exception as e:
                      st.warning(f"Could not read story file: {e}")
                      story = None
            # --- End Reading Story Output ---

            # --- Display Story (No Highlighting) ---
            if story:
                with st.container():
                    # Display the story directly using markdown
                    st.markdown(story)
            else:
                st.warning("Brand story could not be generated or found.")
            # --- End Display Story ---

        with col_analysis:
            st.markdown("#### Analysis Summary")
            analysis = results.get("analysis")
            if analysis and not analysis.get("error"):
                keywords = analysis.get("keywords", [])
                sentiment = analysis.get("sentiment", {})
                sentiment_label = sentiment.get('label', 'N/A')
                sentiment_score = sentiment.get('score', 0.0)

                st.metric(label="Overall Sentiment", value=sentiment_label, delta=f"{sentiment_score:.2f} score", help="Sentiment analysis based on extracted text.")
                st.write("")

                if keywords:
                    st.markdown("**Keywords Found:**")
                    st.info(f"{', '.join(keywords)}")
                else:
                    st.markdown("**Keywords Found:** N/A")
                st.write("")

            elif analysis and analysis.get("error"):
                 st.warning(f"Analysis step had issues: {analysis.get('error')}")
            else:
                 st.info("Analysis results not available.")

            st.markdown("---")
            st.markdown("#### Social Links Found")
            social_links = results.get("social_links", {})
            if social_links:
                for platform, link in social_links.items():
                    st.markdown(f"**{platform}:** [{link}]({link})")
            else:
                st.write("No social media links found.")

        # Raw Text Expander
        st.markdown("---")
        website_text = results.get("website_text", "")
        if website_text:
             with st.expander("📄 View Raw Fetched Website Text", expanded=False):
                  st.text_area("Website Text", website_text, height=250, key="website_text_area")

    else:
        st.error(f"Analysis Failed: {results.get('message', 'An unknown error occurred in the backend pipeline.')}")

elif analyze_button and not input_url:
    st.warning("Please enter a URL above.")

