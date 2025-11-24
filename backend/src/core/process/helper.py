import pandas as pd
import numpy as np
import re
from typing import Literal, List

def recommender_system(data: pd.DataFrame, matrix: np.ndarray, movie_name: str, recom_n: int) -> pd.DataFrame:
    """
    Recommend movies similar to a given movie based on a similarity matrix.

    Args:
        data (pd.DataFrame): DataFrame containing movie information, must include a 'title' column.
        matrix (np.ndarray): Precomputed similarity matrix (e.g., cosine similarity) of shape [n_movies, n_movies].
        movie_name (str): The title of the movie for which recommendations are requested.
        recom_n (int): Number of similar movies to recommend (default is 5).

    Returns:
        pd.DataFrame: A DataFrame with recommended movies and their similarity scores, sorted by score descending.
    """
    # Reset index
    data = data.reset_index(drop=True)

    # Find the index of the movie
    try:
        idx = data[data['title'] == movie_name].index[0]
    except IndexError:
        raise ValueError(f"Movie '{movie_name}' not found in the dataset.")

    # Get similarity scores for this movie
    sim_scores = matrix[idx]

    # Get top N similar movies (excluding itself)
    top_indices = sorted(
        list(enumerate(sim_scores)),
        key=lambda x: x[1],
        reverse=True
    )[1:recom_n + 1]

    # Prepare the result as a DataFrame
    recommendations = pd.DataFrame({
        "title":          [data.iloc[i[0]]["title"] for i in top_indices],
        "similarity_score":[i[1]for i in top_indices],
        "authors":        [data.iloc[i[0]]["authors"] for i in top_indices],
        "isbn":           [data.iloc[i[0]]["isbn"] for i in top_indices],
        "description":    [data.iloc[i[0]]["description"] for i in top_indices],
        "google_rating": [data.iloc[i[0]]["google_rating"] for i in top_indices],
        "amazon_rating": [data.iloc[i[0]]["amazon_rating"] for i in top_indices],
        "language":       [data.iloc[i[0]]["language"] for i in top_indices],
        "page_counts":    [data.iloc[i[0]]["page_counts"] for i in top_indices],
        "categories":     [data.iloc[i[0]]["categories"] for i in top_indices],
        "publisher":      [data.iloc[i[0]]["publisher"] for i in top_indices],
        "published_date": [data.iloc[i[0]]["published_date"] for i in top_indices],
        "image_link":     [data.iloc[i[0]]["image_link"] for i in top_indices],
        "preview_link":   [data.iloc[i[0]]["preview_link"] for i in top_indices],
        "coord":          [data.iloc[i[0]]["positions"] for i in top_indices]
    })

    return recommendations

def preprocess_text(series: pd.Series, remove: bool = False, patterns_to_remove: List[Literal['urls', 'hyperlinks', 'emails', 'currency_signs', 'html_tags', 'html_entities', 'special_chars','repeated_words', 'repeated_words_fixed_length', 'repeated_chars', 'html_tags',
                        'slang_abbreviations', 'code_snippets', 'suspicious_misc', 'numbers', 'written_numbers', 'dates']] = None):
    """
    If remove=True: clean text and replace words containing accented letters with TAG_<no-accent-word>.
    If remove=False: detect presence of patterns (HTML, emoji, etc.) in the series.
    """
    results = {k: False for k in [
        'html_tags', 'html_entities', 'html', 'invisible_whitespace',
        'breaklines', 'emojis_or_symbols', 'urls', 'emails', 'dates',
        'com_domains', 'currency_signs', 'numbers', 'suspicious_misc',
        'hyperlinks', 'special_chars', 'whitespace_only',
        'slang_abbreviations', 'repeated_words', 'code_snippets', 'repeated_chars', 'written_numbers'
    ]}

    emoji_category_map = {
        
        # Positive emotions
        '😀': 'worrrpos', '😁': 'worrrpos', '🍀': 'worrrpos',
        '😃': 'worrrpos', '😄': 'worrrpos', '🤙': 'worrrpos',
        '😉': 'worrrpos', '😊': 'worrrpos', '😍': 'worrrpos',
        '😘': 'worrrpos', '😚': 'worrrpos', '💖': 'worrrpos',
        '💕': 'worrrpos', '💞': 'worrrpos', '💯': 'worrrpos',
        '👍': 'worrrpos', '👏': 'worrrpos', '👌': 'worrrpos', 
        '👐': 'worrrpos', '🎁': 'worrrpos', '🌷': 'worrrpos', 
        '🌟': 'worrrpos', '🔝': 'worrrpos', '💋': 'worrrpos', 
        '💟': 'worrrpos', '💓': 'worrrpos', '💝': 'worrrpos', 
        '💚': 'worrrpos',
    
        # Negative emotions
        '😐': 'worrrneg', '😓': 'worrrneg', '😔': 'worrrneg',
        '😕': 'worrrneg', '😞': 'worrrneg', '😟': 'worrrneg',
        '😠': 'worrrneg', '😡': 'worrrneg', '😢': 'worrrneg',
        '😣': 'worrrneg', '😤': 'worrrneg', '😥': 'worrrneg',
        '😩': 'worrrneg', '😭': 'worrrneg', '😱': 'worrrneg',
        '👎': 'worrrneg', '👊': 'worrrneg',
    
        # noa
        '👆': 'no', '🙏': 'no', '🐕': 'no', '🐘': 'no',
        '👉': 'no', '😂': 'no', '😆': 'no', '💅': 'no',  
        '🚚': 'no', '📺': 'no', '🙌🏻': 'no', '👧': 'no',
    }

    def replace_emojis_with_categories(text, emoji_map, patterns):
        """
        Replace emojis in the text with nothing, and append their category label once.
        If any emoji not found in emoji_map, remove it using the given regex pattern.
        """
        found_categories = set()
        emojis_found = False
    
        for emj in emoji_map:
            if emj in text:
                text = text.replace(emj, "")
                found_categories.add(emoji_map[emj])
                emojis_found = True
    
        # Remove unknown emojis or symbols using regex once, if needed
        if not emojis_found:
            text = re.sub(patterns['emojis_or_symbols'], '', text)
        
        if found_categories:
            text += " " + " ".join(sorted(found_categories))  # Append category labels
    
        return text.strip()


    patterns = {
        'html_tags': r'<[^>]+>',
        'html_entities': r'&[a-zA-Z]+;|&#\d+;',
        'urls': r'https?://\S+',
        'emails': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        'numbers': r'\d+([,\.]\d+)?',
        'currency_signs': r'(r\$|\$|€|£|¥|₹|₩|₽|₦)',
        'special_chars': r'[\\/@#%&*^|]+',
        'suspicious_misc': r'[@]{2,}|[#]{2,}|//+|\*\*+|==+',
        'hyperlinks': r'<a\s+href=|https?://\S+|.∗?.*?http.∗?http.*?',
        'code_snippets': r'[{}`=()<>;]|==|!=|//|/\*|\*/',
        'emojis_or_symbols': r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+',
        'repeated_words': r'\b([A-Za-z]+)\s+\1\b',
        'repeated_chars': r'(.)\1{2,}',
        'dates': r'\b(?:\d{1,2}[/-]){2}\d{2,4}\b|\b\d{4}[-./]\d{2}[-./]\d{2}\b|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(, \d{4})?'
    }
    
    cleaned_series = []

    for raw_text in series.fillna('').astype(str):
        text = raw_text.strip()

        if not remove:
            for key, pattern in patterns.items():
                if not results[key] and re.search(pattern, text, flags=re.IGNORECASE if key in ['slang_abbreviations', 'dates', 'written_numbers'] else 0):
                    results[key] = True

            if not results['html'] and any(tag in text.lower() for tag in ['<html', '<head', '<body']):
                results['html'] = True

            if not results['invisible_whitespace'] and any(c in text for c in ['\n', '\r', '\t']):
                results['invisible_whitespace'] = True

            if not results['breaklines'] and any(c in text for c in ['\n', '\r']):
                results['breaklines'] = True

            if not results['com_domains'] and re.search(r'(https?://)?([\w-]+\.)+(com|net|org)\b|(?<=\s)\.(com|net|org)\b', text, flags=re.IGNORECASE):
                results['com_domains'] = True

            if not results['whitespace_only'] and text.strip() == ' ':
                results['whitespace_only'] = True
        else:

            text = replace_emojis_with_categories(text, emoji_category_map, patterns)

            for key in patterns_to_remove:

                if key in patterns.keys():
                
                    if key == 'repeated_chars':
                        text = re.sub(patterns[key], r'\1', text)

                    elif key == 'urls' or key == "hyperlinks":
                        text = re.sub(patterns[key], 'link', text)

                    elif key == 'emails':
                        text = re.sub(patterns['emails'], 'emails', text)

                    elif key in ['repeated_words', 'repeated_words_fixed_length']:
                        text = re.sub(patterns[key], r'\1', text, flags=re.IGNORECASE)

                    else:
                        # Remove other patterns completely
                        text = re.sub(patterns[key], '', text, flags=re.IGNORECASE)

            text = re.sub(r'\s([.,;!?])', r'\1', text).strip()  # Clean up punctuation spacing
            text = re.sub(r',\s*,', ',', text).strip()  # Clean up consecutive commas
            text = re.sub(r',\s*$', '', text).strip()  # Remove trailing commas
            text = re.sub(r'[^\w\s]', '', text).strip()  # Remove special characters

            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            # Remove words longer than 25 characters
            text = " ".join([w for w in text.split() if len(w) <= 25])

            text = re.sub(r'\s+', ' ', text).strip()
            text = text.lower()

            cleaned_series.append(text)

    return cleaned_series if remove else {k: 'Yes' if v else 'No' for k, v in results.items()}