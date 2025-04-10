# modules/analyzer.py

import re
import string
import collections
from nltk.corpus import stopwords
# No longer need: from nltk.tokenize import sent_tokenize
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk

# --- One-time Setup ---
# Only need stopwords now
try:
    stopwords.words('english')
except LookupError:
    print("NLTK stopwords not found. Downloading...")
    nltk.download('stopwords', quiet=True)
# No longer need: punkt download check

# --- Constants ---
DEFAULT_NUM_KEYWORDS = 10 # Default if not specified
ENGLISH_STOPWORDS = set(stopwords.words('english'))
CUSTOM_STOPWORDS = {'ai', 'business', 'company', 'service', 'product', 'solution', 'contact', 'about', 'home', 'learn', 'more'}
ALL_STOPWORDS = ENGLISH_STOPWORDS.union(CUSTOM_STOPWORDS)
sentiment_analyzer = SentimentIntensityAnalyzer()

# --- Helper Functions (Keep _clean_text, _get_sentiment_vader as before or revert _clean_text if preferred) ---
def _clean_text(text: str) -> str:
    """ Basic text cleaning: lowercase, remove punctuation, extra whitespace. """
    if not text or not isinstance(text, str): return ""
    text = text.lower()
    # Revert to simpler punctuation removal if sentence structure isn't critical
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _extract_keywords_counter(cleaned_text: str, num_keywords: int) -> list[str]:
    """ Extracts keywords using word frequency. Takes cleaned text. """
    if not cleaned_text: return []
    words = cleaned_text.split()
    filtered_words = [word for word in words if word not in ALL_STOPWORDS and len(word) > 2 and not word.isdigit()]
    if not filtered_words: return []
    word_counts = collections.Counter(filtered_words)
    actual_num_keywords = min(num_keywords, len(word_counts))
    keywords = [word for word, count in word_counts.most_common(actual_num_keywords)]
    return keywords

def _get_sentiment_vader(text: str) -> dict:
    """ Analyze sentiment using VADER. """
    # (Keep this function exactly as before)
    if not text: return {'label': 'Neutral', 'score': 0.0}
    # Use original text for VADER usually works well
    scores = sentiment_analyzer.polarity_scores(text)
    compound_score = scores['compound']
    if compound_score >= 0.05: label = 'Positive'
    elif compound_score <= -0.05: label = 'Negative'
    else: label = 'Neutral'
    return {'label': label, 'score': compound_score}

# Removed: _generate_extractive_summary function

# --- Main Function (Modified - Summary Removed) ---
def analyze_content(
    website_text: str | None,
    social_bios_dict: dict | None,
    num_keywords: int = DEFAULT_NUM_KEYWORDS # Keep keyword count parameter
    # Removed: num_summary_sentences parameter
) -> dict:
    """
    Analyzes aggregated text content from website and social media bios.
    Extracts specified number of keywords and determines sentiment.

    Args:
        website_text (str | None): Text from website.
        social_bios_dict (dict | None): Dictionary of social bios {platform: text}.
        num_keywords (int): The target number of keywords to extract.

    Returns:
        dict: A dictionary containing keywords, sentiment analysis, and source texts.
    """
    source_texts = {}
    aggregated_text_parts = []
    original_aggregated_text = "" # Keep original for sentiment analysis

    # Process website text
    if website_text and isinstance(website_text, str) and website_text.strip():
        clean_web_text = website_text.strip()
        source_texts['website'] = clean_web_text
        aggregated_text_parts.append(_clean_text(clean_web_text)) # Cleaned for keywords
        original_aggregated_text += clean_web_text + " " # Original for sentiment

    # Process social bios
    if social_bios_dict and isinstance(social_bios_dict, dict):
        for platform, bio in social_bios_dict.items():
            if bio and isinstance(bio, str) and bio.strip():
                clean_bio_text = bio.strip()
                source_texts[platform.lower()] = clean_bio_text
                aggregated_text_parts.append(_clean_text(clean_bio_text)) # Cleaned for keywords
                original_aggregated_text += clean_bio_text + " " # Original for sentiment

    cleaned_aggregated_text = " ".join(aggregated_text_parts)
    original_aggregated_text = original_aggregated_text.strip()

    # --- Perform Analysis ---
    if not cleaned_aggregated_text:
        return {
            'keywords': [],
            'sentiment': {'label': 'Neutral', 'score': 0.0},
            # Removed: 'summary' key
            'source_texts': source_texts
        }

    # 1. Extract Keywords (using cleaned text)
    keywords = _extract_keywords_counter(cleaned_aggregated_text, num_keywords)

    # 2. Analyze Sentiment/Tone (using original text)
    sentiment_result = _get_sentiment_vader(original_aggregated_text)

    # 3. Removed: Summary generation step

    # 4. Assemble final output
    analysis_results = {
        'keywords': keywords,
        'sentiment': sentiment_result,
        # Removed: 'summary' key
        'source_texts': source_texts # Still include sources in this function's return
    }

    return analysis_results