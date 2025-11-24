
# --- Standard Python imports ---
import logging, ast
import numpy as np
from typing import Optional

# --- Third-party imports ---
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

# --- Local imports ---
from core.utils.file_manager import ReadManager, WriteManager
from core.process.helper import preprocess_text
from core.utils.logger import get_logger

# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

log = get_logger(__name__)
read = ReadManager()
write = WriteManager()

class BookSimilarity:
    """
    A class to handle initial data processing like object to catgeory, find strings in numeric,
    numeric to categories etc.

    Attributes:
        log (logging.Logger): Logger instance for logging events.
    """

    def __init__(self, data:pd.DataFrame, *, logger: Optional[logging.Logger] = None):
        """
        Initializes the GeneralAnalyzer object with an optional logger and dataframe.
        
        Args:
            logger (Optional[logging.Logger]): A logger to be used by the strategy (default None).
        """
        base = logger or log
        self.log =  base.getChild(self.__class__.__name__)
        data = data[data.title != 'Unreadable'].reset_index(drop=True)
        self.df = data
        self.scaler = StandardScaler()


    @staticmethod
    def normalize_subjects(val):
        if isinstance(val, list):
            return ' '.join(val)

        if isinstance(val, str):
            try:
                parsed = ast.literal_eval(val)
                if isinstance(parsed, list):
                    return ' '.join(parsed)
            except:
                return val.strip()

        return 'Unknown'

    @staticmethod
    def combine_ratings(amazon_rating, amazon_count, google_rating, google_count):
        """
        Combine Amazon and Google ratings into a single weighted score.

        Args:
            amazon_rating (float): Amazon rating value.
            amazon_count (int): Number of Amazon ratings.
            google_rating (float): Google rating value.
            google_count (int): Number of Google ratings.

        Returns:
            float: Weighted combined rating.
        """
        total_count = amazon_count + google_count
        if total_count == 0:
            return 0  # fallback if no ratings

        combined = (amazon_rating * amazon_count + google_rating * google_count) / total_count
        return combined
    
    def similarity_matrix(self, data:pd.DataFrame):
        # Applying sclaing
        normalized = pd.DataFrame(
            self.scaler .fit_transform(data), 
            columns=data.columns, 
            index=data.index
        )
        # Compute the cosine similarity matrix
        similarity = cosine_similarity(normalized)
        similarity = similarity.astype('float32')

        return similarity

    def popularity(self):
        data = self.df[['title', 'google_rating', 'google_counts', 'amazon_rating', 'amazon_counts']]
        data = data.replace('Not available', np.nan)
        data = data.fillna(0)
        data[['google_rating', 'google_counts', 
              'amazon_rating', 'amazon_counts']] = data[['google_rating', 'google_counts', 
                                                         'amazon_rating', 'amazon_counts']].astype(float)

        data['combined_rating'] = data.apply(
            lambda row: self.combine_ratings(row['amazon_rating'], row['amazon_counts'],
                                        row['google_rating'], row['google_counts']),
            axis=1
        )

        data.drop(columns= ['google_rating', 'google_counts', 'amazon_rating', 'amazon_counts'], inplace=True)

        # Place `title` as index
        final_data=data.set_index('title')
        # Similarity matrix
        self.popularity_mat = self.similarity_matrix(data=final_data)

    def lang_pub(self):
        data = self.df[['title', 'language', 'publisher']]
        data = data.replace('Not available', np.nan)
        data = data.fillna('Unknown')


        # Place `title` as index
        final_data=data.set_index('title')
        # Apply one hot encoding
        ohe = (
            pd.get_dummies(
                final_data, columns= ['language', 'publisher'], 
                drop_first=True
                )
        ).astype('int')
        # Similarity matrix
        self.lang_pub_mat = self.similarity_matrix(data=ohe)

    def category(self):
        data = self.df[['title', 'categories', 'authors']]
        data = data.replace('Not available', np.nan)
        data = data.fillna('Unknown')

        data['tags'] = data[['categories', 'authors']].apply(
            lambda x: ' '.join(str(i) for i in x if pd.notna(i) and str(i).strip() != ''),
            axis=1
        )

        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform(data['tags'].tolist())
        # Similiarity
        cat_mat = cosine_similarity(vectors)
        self.cat_mat = cat_mat.astype('float32')
        
    def content(self):
        data = self.df[['title', 'description', 'subjects']]
        data = data.replace('Not available', np.nan)
        data['description'] = data['description'].fillna(data['title'])

        # data['subjects'] = data['subjects'].apply(self.normalize_subjects)
        data['tags'] = data[['description', 'subjects']].apply(
            lambda x: ' '.join(str(i) for i in x if pd.notna(i) and str(i).strip() != ''),
            axis=1
        )
        # Preprocess Texts
        pattern_dict = preprocess_text(data.tags)
        data['tags'] = preprocess_text(
            data.tags, 
            remove=True, 
            patterns_to_remove=[k for k, v in pattern_dict.items() if v == 'Yes']
        ) 

        # TF-IDF Vectorization
        nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])  # light pipeline

        def spacy_tokenizer(text):
            doc = nlp(text.lower())
            return [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]

        vectorizer = TfidfVectorizer(tokenizer=spacy_tokenizer, token_pattern=None)
        vectors = vectorizer.fit_transform(data['tags'].tolist())
        # Similiarity
        content_mat = cosine_similarity(vectors)
        self.content_mat = content_mat.astype('float32')

        # # Embeddings
        # embeddings = model.encode(data['tags'].tolist(), normalize_embeddings=True)
        # # Similiarity
        # content_mat = cosine_similarity(embeddings)
        # self.content_mat = content_mat.astype('float32')

    def score(self):
        # self.popularity()
        # self.lang_pub()
        self.category()
        self.content()
        
        matrix = (
            # 0.1 * self.popularity_mat +
            # 0.1 * self.lang_pub_mat +
            0.4 * self.cat_mat +
            0.6 * self.content_mat
        )

        return matrix

        


