# app.py
# Streamlit frontend for the Brand Story Generator
# *** Includes styling enhancements - V2 Highlighting + Gradient Background + Resized Input + Swapped Columns (Story Left) ***

import streamlit as st
import time # Used for simulating work if needed, st.spinner handles waits
import os
import sys
import re # Needed for keyword highlighting

# --- Attempt to import the pipeline function ---
try:
    from modules import run_full_pipeline
except ImportError as e:
    st.error(f"Fatal Error: Could not import pipeline function: {e}")
    st.error("Ensure 'app.py' is in the project root and the 'modules' directory with '__init__.py' exists.")
    st.stop() # Stop the streamlit app if import fails

# --- Page Configuration ---
st.set_page_config(
    page_title="Brand Story Generator",
    page_icon="🚀",
    layout="wide" # Use wide layout for better column display
)

# --- Add Custom CSS for Background Gradient ---
st.markdown("""
<style>
/* Target the main block container */
div[data-testid="stAppViewContainer"] > .main .block-container {
    /* Subtle gradient from a slightly lighter dark blue/grey to the default dark background */
    /* Adjust colors #151F2B (top) and #0E1117 (bottom) if needed */
    background-image: linear-gradient(180deg, #151F2B , #0E1117);
    background-size: cover; /* Ensure gradient covers the background */
    background-attachment: fixed; /* Keep gradient fixed during scroll */
    /* Add some padding to push content away from edges if gradient makes them hard to see */
    padding-top: 5rem; /* Adjust as needed */
    padding-bottom: 5rem; /* Adjust as needed */
    padding-left: 2rem; /* Adjust as needed */
    padding-right: 2rem; /* Adjust as needed */
}

/* Optional: Style the main app view container itself if the above doesn't cover everything */
/*
div[data-testid="stAppViewContainer"] > .main {
    background-color: #0E1117; /* Fallback color */
}
*/

/* Style for keyword highlighting */
.highlight-keyword {
    background-color: #2E4053; /* Darker background for highlight */
    color: #EAECEE; /* Lighter text for highlight */
    padding: 0.15em 0.3em;
    margin: 0 0.1em;
    line-height: 1.75;
    border-radius: 5px;
    font-weight: 500;
    display: inline-block;
}

/* CSS rule for button alignment (commented out, adjust if needed) */
/*
div[data-testid="stButton"] > button {
    margin-top: 28px;
}
*/

</style>
""", unsafe_allow_html=True)
# --- End Custom CSS ---


# --- Helper function for highlighting (Unchanged) ---
def highlight_text(text, terms, class_name="highlight-keyword"):
    """Highlights terms in text by wrapping them in a span with a specific class."""
    if not text or not terms: return text
    sorted_terms = sorted(list(set(terms)), key=len, reverse=True)
    highlighted_text = text
    for term in sorted_terms:
        try:
            safe_term = re.escape(term)
            pattern = r"(\b" + safe_term + r"\b)"
            replacement = f"<span class='{class_name}'>\\1</span>"
            highlighted_text = re.sub(pattern, replacement, highlighted_text, flags=re.IGNORECASE)
        except re.error as e: print(f"Regex error highlighting term '{term}': {e}"); continue
    return highlighted_text

# --- Application Title ---
st.title("🚀 AI Brand Story Generator")
st.markdown("Enter a company's website URL to analyze its online presence and generate a brand story.")

# --- Input Section (Modified to use columns) ---
st.divider()
if 'url_input' not in st.session_state: st.session_state.url_input = ""

# Create columns for the input elements
input_col, button_col, _ = st.columns([2, 1, 1]) # Input takes half, button quarter, leave last quarter empty

with input_col:
    input_url = st.text_input(
        "Enter Company Website URL:", value=st.session_state.url_input,
        placeholder="e.g., https://www.example.com", key="company_url_input",
        label_visibility="collapsed" # Hide label if title is sufficient
    )
    st.session_state.url_input = input_url

with button_col:
    # The button should align reasonably well by default in columns
    analyze_button = st.button("✨ Analyze & Generate Story", key="analyze_button", type="primary", use_container_width=True)

st.divider()
# --- End Input Section Modification ---


# --- Output Section ---
if 'pipeline_results' not in st.session_state: st.session_state.pipeline_results = None
if 'last_run_url' not in st.session_state: st.session_state.last_run_url = ""

# --- Run Pipeline Logic ---
# ...(logic remains the same)...
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
                    if results.get("success"): st.success("Analysis complete!")
                    else: st.error(f"Pipeline failed: {results.get('message', 'Unknown error')}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during the pipeline execution: {e}")
                    st.session_state.pipeline_results = {"success": False, "message": f"App error: {e}"}
                    print(f"Streamlit App: Error running pipeline for {input_url}: {e}")
    elif input_url == st.session_state.last_run_url:
         st.info("Displaying previous results for this URL. Click button again to re-run.")


# --- Display Results (Story Left, Analysis Right) ---
if st.session_state.pipeline_results:
    results = st.session_state.pipeline_results

    # CSS is injected near the top of the script

    if results.get("success"):
        st.subheader("📊 Analysis & Story")
        st.markdown("---") # Visual separator

        # *** Define columns with Story first (wider), Analysis second (narrower) ***
        col_story, col_analysis = st.columns([2, 1]) # Story:Analysis ratio 2:1

        # *** Put Story code in the first column ***
        with col_story:
            st.markdown("#### Generated Brand Story")
            story = results.get("story")
            keywords_for_highlight = results.get("analysis", {}).get("keywords", [])
            if story:
                highlighted_story = highlight_text(story, keywords_for_highlight, class_name="highlight-keyword")
                with st.container():
                     st.markdown(highlighted_story, unsafe_allow_html=True)
            else:
                st.warning("Brand story could not be generated.")

        # *** Put Analysis and Links code in the second column ***
        with col_analysis:
            st.markdown("#### Analysis Summary")
            analysis = results.get("analysis")
            if analysis and not analysis.get("error"):
                keywords = analysis.get("keywords", []); sentiment = analysis.get("sentiment", {})
                sentiment_label = sentiment.get('label', 'N/A'); sentiment_score = sentiment.get('score', 0.0)
                st.metric(label="Overall Sentiment", value=sentiment_label, delta=f"{sentiment_score:.2f} score", help="Sentiment analysis based on extracted text.")
                st.write("") # Add spacing
                if keywords: st.markdown("**Keywords Found:**"); st.info(f"{', '.join(keywords)}")
                else: st.markdown("**Keywords Found:** N/A")
                st.write("") # Add spacing
                confidence_note = "Analysis based on Website Text"
                if results.get("social_bios"): confidence_note += f" + {', '.join(results['social_bios'].keys())} Bio(s)"
                st.caption(confidence_note)
            elif analysis and analysis.get("error"): st.warning(f"Analysis step had issues: {analysis.get('error')}")
            else: st.info("Analysis step was skipped or did not produce results.")

            st.markdown("---"); st.markdown("#### Social Links")
            social_links = results.get("social_links", {})
            if social_links:
                for platform, link in social_links.items(): st.markdown(f"**{platform}:** [{link}]({link})")
            else: st.write("No social media links found.")

        # Raw Text Expander (Full Width Below Columns - unchanged)
        st.markdown("---")
        website_text = results.get("website_text", "")
        if website_text:
             with st.expander("📄 View Raw Fetched Website Text", expanded=False):
                  st.text_area("Website Text", website_text, height=250, key="website_text_area")

    else:
        # If pipeline ran but reported failure
        st.error(f"Analysis Failed: {results.get('message', 'An unknown error occurred in the backend pipeline.')}")

elif analyze_button and not input_url:
    st.warning("Please enter a URL above.")
