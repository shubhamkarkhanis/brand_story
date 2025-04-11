# # In app.py
# from modules.analyzer import analyze_content

# # ... later in the Streamlit logic ...
# website_text = "..." # Text from Person 2's module
# social_bios = {...} # Dict from Person 2's module
# if website_text or social_bios: # Check if there's any text to analyze
#     analysis_data = analyze_content(website_text, social_bios)
#     # Now display analysis_data['keywords'], analysis_data['sentiment'], etc.
#     st.subheader("Analysis Summary")
#     st.write(f"**Tone:** {analysis_data['sentiment']['label']} (Score: {analysis_data['sentiment']['score']:.2f})")
#     st.write("**Keywords:**")
#     st.write(", ".join(analysis_data['keywords']))

#     # Optionally show source texts in an expander
#     with st.expander("See Source Texts Used"):
#         st.write(analysis_data['source_texts'])
# else:
#     st.warning("No text could be extracted from the website or social media links provided.")


# app.py
# Basic script to run the full analysis pipeline from the command line.
# Takes the target URL as a command-line argument.

import sys
import os

# Ensure the 'modules' directory is discoverable if running app.py from root
# (This might not be strictly necessary if Python path is set up correctly,
# but can help avoid import issues in some environments)
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Import the main pipeline function from the modules package
    from modules import run_full_pipeline
except ImportError as e:
    print(f"❌ Error importing pipeline function: {e}")
    print("Make sure 'app.py' is in the project root directory ('brand_story/')")
    print("and the 'modules' directory with '__init__.py' exists.")
    sys.exit(1) # Exit if import fails

# --- Main Execution ---
if __name__ == "__main__":
    # Check if a command-line argument (the URL) was provided
    if len(sys.argv) < 2:
        print("❌ Error: Missing argument.")
        print("Usage: python app.py <target_url>")
        print("Example: python app.py https://www.example.com")
        sys.exit(1) # Exit if no URL is given

    # Get the URL from the first command-line argument
    target_url = sys.argv[1]

    print(f"▶️ Received URL: {target_url}")
    print("--- Initializing Pipeline ---")

    try:
        # Call the main pipeline function
        run_full_pipeline(target_url)
        print("\n--- app.py: Pipeline execution finished ---")
        # Note: Detailed status/output is printed by the pipeline function itself.
        # The final story needs to be read from a file saved by generator.py
        # if you want to display it here. Example:
        # try:
        #     with open("output_story.txt", "r", encoding="utf-8") as f:
        #         print("\n--- Generated Story ---")
        #         print(f.read())
        # except FileNotFoundError:
        #     print("\nNote: Output story file not found.")

    except Exception as e:
        print(f"\n❌ An unexpected error occurred in app.py while running the pipeline: {e}")
        # Consider adding more detailed error logging if needed
        # import traceback
        # traceback.print_exc()
        sys.exit(1) # Exit with error status

    sys.exit(0) # Exit successfully

