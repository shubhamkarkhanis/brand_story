# modules/analyzer.py

import re
import string
import collections
from nltk.corpus import stopwords
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk

# --- One-time Setup ---
try:
    stopwords.words('english')
except LookupError:
    print("NLTK stopwords not found. Downloading...")
    nltk.download('stopwords', quiet=True)

# --- Constants ---
DEFAULT_NUM_KEYWORDS = 10 # Default if not specified
ENGLISH_STOPWORDS = set(stopwords.words('english'))
# *** Enhance CUSTOM_STOPWORDS for more meaningful keywords ***
CUSTOM_STOPWORDS = {
    'ai', 'business', 'company', 'service', 'product', 'solution', 'contact', 'about', 'home',
    'learn', 'more', 'get', 'us', 'use', 'help', 'work', 'team', 'like', 'need', 'new', 'also',
    'well', 'based', 'provide', 'offer', 'inc', 'llc', 'corp', 'group', 'limited', 'org',
    'http', 'https', 'www', 'com', 'net', 'io', 'ly', 'co', # Common URL parts/TLDs
    'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december', # Months
    'privacy', 'policy', 'terms', 'conditions', 'support', 'faq', # Common website sections
    'data', 'technology', 'platform', 'innovation', 'global', 'world', # Often too generic depending on context
    'login', 'signup', 'join', 'follow', 'share', # Action words
    # Add more based on observing common non-informative words in your test cases
}
ALL_STOPWORDS = ENGLISH_STOPWORDS.union(CUSTOM_STOPWORDS)
sentiment_analyzer = SentimentIntensityAnalyzer()

# --- Helper Functions (Keep as before) ---
def _clean_text(text: str) -> str:
    """ Basic text cleaning: lowercase, remove punctuation, extra whitespace. """
    if not text or not isinstance(text, str): return ""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _extract_keywords_counter(cleaned_text: str, num_keywords: int) -> list[str]:
    """ Extracts unique, non-stopword keywords using word frequency. """
    if not cleaned_text: return []
    words = cleaned_text.split()
    # Filter words: not in stopwords, longer than 2 chars, not purely numeric
    filtered_words = [
        word for word in words
        if word not in ALL_STOPWORDS and len(word) > 2 and not word.isdigit()
    ]
    if not filtered_words: return []
    word_counts = collections.Counter(filtered_words)
    # Get the most common keywords, up to the requested number
    actual_num_keywords = min(num_keywords, len(word_counts))
    # Counter keys are unique words, most_common gives sorted list
    keywords = [word for word, count in word_counts.most_common(actual_num_keywords)]
    return keywords

def _get_sentiment_vader(text: str) -> dict:
    """ Analyze sentiment using VADER. """
    if not text: return {'label': 'Neutral', 'score': 0.0}
    scores = sentiment_analyzer.polarity_scores(text)
    compound_score = scores['compound']
    if compound_score >= 0.05: label = 'Positive'
    elif compound_score <= -0.05: label = 'Negative'
    else: label = 'Neutral'
    return {'label': label, 'score': compound_score}

# --- Main Function (Keep as before, returning full analysis dict) ---
def analyze_content(
    website_text: str | None,
    social_bios_dict: dict | None,
    num_keywords: int = DEFAULT_NUM_KEYWORDS
) -> dict:
    """
    Analyzes aggregated text content.
    Returns dict with keywords, sentiment, and original source_texts.
    """
    source_texts = {}
    aggregated_text_parts = []
    original_aggregated_text = ""

    # (Logic for processing website_text and social_bios_dict remains the same)
    if website_text and isinstance(website_text, str) and website_text.strip():
        clean_web_text = website_text.strip()
        source_texts['website'] = clean_web_text
        aggregated_text_parts.append(_clean_text(clean_web_text))
        original_aggregated_text += clean_web_text + " "
    if social_bios_dict and isinstance(social_bios_dict, dict):
        for platform, bio in social_bios_dict.items():
            if bio and isinstance(bio, str) and bio.strip():
                clean_bio_text = bio.strip()
                source_texts[platform.lower()] = clean_bio_text
                aggregated_text_parts.append(_clean_text(clean_bio_text))
                original_aggregated_text += clean_bio_text + " "

    cleaned_aggregated_text = " ".join(aggregated_text_parts)
    original_aggregated_text = original_aggregated_text.strip()

    if not cleaned_aggregated_text:
        return {
            'keywords': [],
            'sentiment': {'label': 'Neutral', 'score': 0.0},
            'source_texts': source_texts
        }

    keywords = _extract_keywords_counter(cleaned_aggregated_text, num_keywords)
    sentiment_result = _get_sentiment_vader(original_aggregated_text)

    analysis_results = {
        'keywords': keywords,
        'sentiment': sentiment_result,
        'source_texts': source_texts # Still return sources from this function
    }
    return analysis_results