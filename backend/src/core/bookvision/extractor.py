
# --- Standard Python imports ---
import ast
import base64
import logging
import json
import os
import re
import time
from typing import Optional
from urllib.parse import quote_plus

# --- Third-party imports ---
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from dotenv import load_dotenv
from google import genai
from groq import Groq
import numpy as np
import pandas as pd
from rapidfuzz import fuzz
import requests

# --- Local imports ---
from core.utils.file_manager import ReadManager, WriteManager
from core.bookvision.book_info import StoreData
from core.utils.logger import get_logger

# Initialization
load_dotenv()
log = get_logger(__name__)
read = ReadManager()
write = WriteManager()

# DB
NEON_API_URL = os.getenv("NEON_URI")
engine = create_engine(NEON_API_URL)

GOOGLE_API_KEY = os.getenv("GOOGLE_BOOK_API")
GEMINI_API_KEY = os.getenv("GEMINI_API")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_2")
GROQ_API_KEY = os.getenv("GROQ_API")

class Extractor:
    """
    A class to extract books metadata.

    Attributes:
        log (logging.Logger): Logger instance for logging events.
        db (pd.DataFrame): Load stored data from database.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes the GeneralAnalyzer object with an optional logger and dataframe.
        
        Args:
            logger (Optional[logging.Logger]): A logger to be used by the strategy (default None).
        """
        base = logger or log
        self.log =  base.getChild(self.__class__.__name__)
        self.db = pd.read_sql("SELECT * FROM books_metadata", engine)

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
    def text_read(input_path):
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read().replace("\n", " ")
        return text

    @staticmethod
    def fill_priority(row, cols):
        for i, col in enumerate(cols):
            val = row[col]
            if pd.notna(val):
                if i < 2:
                    return val
                else: 
                    return f"{col}: {val}"
        return np.nan

    @staticmethod
    def find_best_book(data, guide_authors, target_title):
        """
        data: JSON from Google Books API ("items")
        guide_authors: list of author hints or None
        target_title: the extracted title from image
        """
        # Filter by title similarity (>70%)
        title_matches = []
        for item in data.get("items", []):
            info = item.get("volumeInfo", {})
            google_title = info.get("title", "")
            title_score = fuzz.ratio(target_title.lower(), google_title.lower())
            if title_score >= 70:
                title_matches.append((title_score, info))

        if not title_matches:
            print("No good title match found.")
            return None

        # If only one title match, return it directly
        if len(title_matches) == 1:
            return Extractor.extract_book_info(title_matches[0][1])

        # If no guide authors provided, select the best title match
        if not guide_authors:
            best_match = max(title_matches, key=lambda x: x[0])[1]
            return Extractor.extract_book_info(best_match)

        # Use guide_author matching if provided
        best_matches = []
        best_author_score = 0

        for title_score, info in title_matches:
            google_authors = info.get("authors", [])
            for guide_author in guide_authors:
                for g_author in google_authors:
                    author_score = fuzz.ratio(guide_author.lower(), g_author.lower())
                    if author_score > best_author_score:
                        best_author_score = author_score
                        best_matches = [(title_score, info)]
                    elif author_score == best_author_score:
                        best_matches.append((title_score, info))

        if not best_matches or best_author_score < 50:
            print("No good author match found among title matches.")
            return None

        # Step 4: Break ties using max title similarity
        best_match = max(best_matches, key=lambda x: x[0])[1]
        return Extractor.extract_book_info(best_match)

    def find_best_book_frame(self, guide_authors, target_title):
        """
        df: Pandas DataFrame with book info (columns similar to extract_book_info structure)
        guide_authors: list of author hints or None
        target_title: the extracted title from image
        """
        # Filter by title similarity (>90%)
        title_matches = []
        for _, row in self.db.iterrows():
            google_title = str(row.get("title", ""))
            title_score = fuzz.ratio(target_title.lower(), google_title.lower())
            if title_score >= 90:
                title_matches.append((title_score, row.to_dict()))

        if not title_matches:
            print("No good title match found.")
            return None

        # If only one title match, return it directly
        if len(title_matches) == 1:
            return Extractor.extract_book_info_frame(title_matches[0][1])

        # If no guide authors provided, select the best title match
        if not guide_authors:
            best_match = max(title_matches, key=lambda x: x[0])[1]
            return Extractor.extract_book_info_frame(best_match)

        # Use guide_author matching if provided
        best_matches = []
        best_author_score = 0

        for title_score, info in title_matches:
            google_authors = [a.strip() for a in str(info.get("authors", "")).split(",") if a.strip()]
            for guide_author in guide_authors:
                for g_author in google_authors:
                    author_score = fuzz.ratio(guide_author.lower(), g_author.lower())
                    if author_score > best_author_score:
                        best_author_score = author_score
                        best_matches = [(title_score, info)]
                    elif author_score == best_author_score:
                        best_matches.append((title_score, info))

        if not best_matches or best_author_score < 50:
            print("No good author match found among title matches.")
            return None

        # Break ties using max title similarity
        best_match = max(best_matches, key=lambda x: x[0])[1]
        return Extractor.extract_book_info_frame(best_match)

    @staticmethod
    def extract_book_info(info):
        return {
            "title": info.get("title", ""),
            "authors": ", ".join(info.get("authors", [])),
            "isbn": ", ".join([id["identifier"] for id in info.get("industryIdentifiers", [])]) if info.get("industryIdentifiers") else "",
            "description": info.get("description", ""),
            "average_rating": info.get("averageRating", ""),
            "ratings_count": info.get("ratingsCount", ""),
            "language": info.get("language", ""),
            "page_count": info.get("pageCount", ""),
            "categories": ", ".join(info.get("categories", [])) if info.get("categories") else "",
            "publisher": info.get("publisher", ""),
            "published_date": info.get("publishedDate", ""),
            "image_link": info.get("imageLinks", {}).get("thumbnail", ""),
            "preview_link": info.get("previewLink", "")
        }

    @staticmethod
    def extract_book_info_frame(info):
        """
        Extract book info from a combined dictionary (Google + Amazon),
        keeping all key names exactly the same as extract_book_info().
        Uses fallback logic if some fields are missing or NaN.
        """
        def get_val(primary, fallback=np.nan):
            """Return primary if it exists and is not NaN, else fallback"""
            if primary is None:
                return fallback
            if isinstance(primary, float) and np.isnan(primary):
                return fallback
            return primary
        
        gle_info = {
            "title": get_val(info.get("title")),
            "authors": get_val(info.get("authors")),
            "isbn": get_val(info.get("isbn")),
            "description": get_val(info.get("description")),
            "average_rating": get_val(info.get("google_rating")),
            "ratings_count": get_val(info.get("google_counts")),
            "language": get_val(info.get("language")),
            "page_count": get_val(info.get("page_counts")),
            "categories": get_val(info.get("categories")),
            "publisher": get_val(info.get("publisher")),
            "published_date": get_val(info.get("published_date")),
            "image_link": get_val(info.get("image_link")),
            "preview_link": get_val(info.get("preview_link"))
        }

        amz_info = {
            "average_rating": get_val(info.get("amazon_rating")),
            "ratings_count": get_val(info.get("amazon_counts")),
            "publisher": get_val(info.get("publisher"))
        }
        open_info = {"subjects" : get_val(info.get("subjects"))}

        return gle_info, amz_info, open_info

    @staticmethod
    def get_google_books_details(title, authors=None, guide_authors=None):
        """Fetch metadata for a single book title from Google Books API."""
        base_url = "https://www.googleapis.com/books/v1/volumes"

        # Build query string
        query = f"intitle:{title}"
        if authors:
            author_query = "+".join([f"inauthor:{a}" for a in authors])
            query += "+" + author_query

        # URL encode the query
        encoded_query = quote_plus(query)

        url = f"{base_url}?q={encoded_query}&maxResults=40&key={GOOGLE_API_KEY}"
        r = requests.get(url)

        if r.status_code != 200:
            print(f"Error fetching '{title}' (status {r.status_code})")
            return None

        data = r.json()
        if "items" not in data:
            # Then again try to find book by `title` of the book 
            query = f"intitle:{title}"
            # URL encode the query
            encoded_query = quote_plus(query)
            url = f"{base_url}?q={encoded_query}&maxResults=40&key={GOOGLE_API_KEY}"
            r = requests.get(url)

            if r.status_code != 200:
                print(f"Error fetching '{title}' (status {r.status_code})")
                return None

            data = r.json()
            if "items" not in data:
                print(f"No results found for '{title}'")
                return None
            
            return Extractor.find_best_book(data, authors, title)

        if authors:
            info = data["items"][0]["volumeInfo"]
            return Extractor.extract_book_info(info)
        else:
            return Extractor.find_best_book(data, guide_authors, title)

    @staticmethod
    def find_dp(title, authors):

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        # Build query string
        query = f"{title} {authors}"
        url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}&i=stripbooks"
        r = requests.get(url, headers=headers)
        # Collect HTML
        soup = BeautifulSoup(r.text, "html.parser")

        first_book = soup.select_one("a.a-link-normal.s-line-clamp-2.s-link-style.a-text-normal")
        if first_book:
            book_url = "https://www.amazon.com" + first_book.get("href").split("?")[0]
            match = re.search(r'/dp/([A-Z0-9]+)', book_url)
            if match:
                asin = match.group(1)
            return asin

    # @staticmethod
    # def get_amazon_books_details(title, authors, delay):

    #     headers = {
    #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #                     "AppleWebKit/537.36 (KHTML, like Gecko) "
    #                     "Chrome/116.0.0.0 Safari/537.36",
    #         "Accept-Language": "en-US,en;q=0.9"
    #     }

    #     asin = Extractor.find_dp(title, authors, delay)
    #     book_url = f"https://www.amazon.com/dp/{asin}"
    #     response = requests.get(book_url, headers=headers)

    #     if response.status_code != 200:
    #         print(f"Failed to fetch page: {book_url}")
    #         return None
    #     soup = BeautifulSoup(response.text, "html.parser")
    #     # Average Rating
    #     try:
    #         avg_rating = soup.select_one("span[data-hook='rating-out-of-text']").text.split()[0]
    #     except:
    #         avg_rating = np.nan
    #     # Ratings Count
    #     try:
    #         ratings_count = soup.select_one("span[data-hook='total-review-count']").text.replace(",", "")
    #     except:
    #         ratings_count = np.nan
    #     # Publisher (from detailBulletsWrapper)
    #     try:
    #         bullets = soup.find(id="detailBulletsWrapper_feature_div")
    #         publisher = "Not available"
    #         for li in bullets.find_all("li"):
    #             text = li.get_text(strip=True)
    #             if "Publisher" in text:
    #                 publisher = text.split(":")[-1].strip()
    #                 break
    #     except:
    #         publisher = np.nan

    #     return {
    #         "average_rating": avg_rating,
    #         "ratings_count": ratings_count.replace('global ratings', ''),
    #         "publisher": publisher.replace('\u200e', '')
    #     }

    @staticmethod
    def get_open_library_metadata(title, authors):

        # Search for the book
        search_url = "https://openlibrary.org/search.json"
        params = {"title": title, "author": authors, "limit": 1}
        resp = requests.get(search_url, params=params)
        data = resp.json()
        
        if not data.get("docs"):
            return {
                "description": np.nan,
                "subjects": []
            }
        
        doc = data["docs"][0]
        
        # Fetch details from work
        description = np.nan
        subjects = []
        if doc.get("key"):
            work_url = f"https://openlibrary.org{doc['key']}.json"
            work_resp = requests.get(work_url).json()

            # Description
            desc = work_resp.get("description")
            if isinstance(desc, dict):
                description = desc.get("value", np.nan)
            elif isinstance(desc, str):
                description = desc

            # Subjects / categories
            subjects = work_resp.get("subjects", [])
        
        return {
            "description": description,
            "subjects": subjects
        }

     # MAin class
    def fetch_book_info(self, books_input, delay=0.5, is_input=False):
        """
        Fetch details for multiple book titles and return as a DataFrame.
        Collects all rows in memory and concatenates with existing data instead of writing CSV repeatedly.
        """
        # List to store all book info
        rows = []

        for i, book in enumerate(books_input):
            title = book['title'].title()
            authors = book['author'].title()
            serial_no = int(book['book_no'])
            auth_ensure = book['author_verified']
            guide_authors = None

            if not auth_ensure:
                guide_authors = [x for x in authors.split(',') if x.lower() != "not visible"]
                authors = None
            else:
                authors = authors.split(',')
            
            if title == 'Unreadable':
                rows.append({"serial_no": serial_no, "title": title, "positions": book['positions']})
                print(f"[Unreadable]: {serial_no}/{len(books_input)} — {title}")
                continue

            try:
                authors_info = guide_authors if guide_authors else authors
                info, amz_info, open_info = self.find_best_book_frame(authors_info, title)
                source = "STORED"
            except:
                info = Extractor.get_google_books_details(title, authors=authors, guide_authors=guide_authors)
                source = "FETCHED"

                amz_info = {
                    "average_rating": np.nan,
                    "ratings_count": np.nan,
                    "publisher": np.nan
                }

                try:
                    open_info = Extractor.get_open_library_metadata(title=info['title'], authors=info['authors'])
                except:
                    open_info = {
                        "description": np.nan,
                        "subjects": []
                    }

            if info:
                rows.append({
                    "serial_no": serial_no,
                    "title": info["title"],
                    "authors": info["authors"],
                    "isbn": info["isbn"],
                    "description": info.get("description") or open_info.get("description"),
                    "google_rating": info["average_rating"],
                    "google_counts": info["ratings_count"],
                    "amazon_rating": amz_info['average_rating'],
                    "amazon_counts": amz_info['ratings_count'],
                    "language": info["language"],
                    "page_counts": info["page_count"],
                    "categories": info["categories"],
                    "publisher": info["publisher"],
                    "published_date": info["published_date"],
                    "image_link": info["image_link"],
                    "preview_link": info["preview_link"],
                    "positions": book['positions'],
                    "subjects": open_info['subjects']
                })
            else:
                rows.append({"serial_no": serial_no, "title": title, "positions": book['positions']})

            print(f"[{source}]: {serial_no}/{len(books_input)} — {title}")
            time.sleep(delay)

        # Create a DataFrame from collected rows
        data = pd.DataFrame(rows)
        data['subjects'] = (
            data['subjects']
            .apply(self.normalize_subjects)
        )

        # Store in database
        StoreData().store(old_info= self.db, new_info= data.copy())

        if not is_input:
            data = data.dropna(subset=['positions']).reset_index(drop=True)
            data['positions'] = [
                ast.literal_eval(p) if isinstance(p, str) else p
                for p in data['positions']
            ]
        
        data = data[data.title != 'Unreadable'].reset_index(drop=True)
        return data
    
    def ocr_cover(self, IMG, Prompt_path="prompt.txt", coordinates=None, segment_path= None, counter = 0):
        # Set your API key in a variable
        PROMPT = self.text_read(Prompt_path)

        try:
            self.log.info("started.ocr [cover]")
            # Initialize the Client with the API key
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            response = client.models.generate_content(
                model= "gemini-2.5-flash",
                contents=[
                    IMG,
                    PROMPT
                ]
            )
            # Output
            self.log.info("success.ocr [cover]")
            clean_text = re.sub(r"```json|```", "", response.text).strip()
            books = json.loads(clean_text)

        except Exception as e:
            self.log.error(f"failed.ocr [cover]: {e}")
            if counter == 0:
                # Fallback to secondary key
                books = self.ocr_shelf(IMG, Prompt_path, coordinates, segment_path=segment_path, counter = 1)
                return books
            else:
                # Fallback to tertiarry key
                books = self.ocr_extra(Prompt_path, coordinates, segment_path=segment_path)
                return books
        
        # Adding coordinates
        for book in books:
            key = f"Book {book['book_no']}"  # match
            if key in coordinates:
                book['positions'] = coordinates[key]

        return books

    def ocr_shelf(self, IMG, Prompt_path="prompt.txt", coordinates=None, segment_path= None, counter = 0):
        # Set your API key in a variable
        PROMPT = self.text_read(Prompt_path)

        try:
            self.log.info("started.ocr [shelf]")
            # Initialize the Client with the API key
            client = genai.Client(api_key=GEMINI_API_KEY_2)
            
            response = client.models.generate_content(
                model= "gemini-2.5-flash", 
                contents=[
                    IMG,
                    PROMPT
                ]
            )
            # Output
            self.log.info("success.ocr [shelf]")
            clean_text = re.sub(r"```json|```", "", response.text).strip()
            books = json.loads(clean_text)

        except Exception as e:
            self.log.error(f"failed.ocr [shelf]: {e}")
            if counter == 0:
                # Fallback to secondary key
                books = self.ocr_cover(IMG, Prompt_path, coordinates, segment_path=segment_path, counter = 1)
                return books
            else:
                # Fallback to tertiarry key
                books = self.ocr_extra(Prompt_path, coordinates, segment_path=segment_path)
                return books
        
        # Adding coordinates
        for book in books:
            key = f"Book {book['book_no']}"  # match
            if key in coordinates:
                book['positions'] = coordinates[key]

        return books
    
    def ocr_extra(self, Prompt_path="prompt.txt", coordinates=None, segment_path= None):

        PROMPT = self.text_read(Prompt_path)

        # Helper
        def encode_image(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')

        # Replace with your image path
        image_path = segment_path
        base64_image = encode_image(image_path)

        try:
            self.log.info("started.ocr [groq]")
            # Initialize the Client with the API key
            client = Groq(api_key=GROQ_API_KEY)
            
            response = client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ],
                    }
                ],
            )
            # Output
            self.log.info("success.ocr [groq]")
            books = json.loads(response.choices[0].message.content)

        except Exception as e:
            self.log.error(f"failed.ocr [groq]: {e}")

        # Adding coordinates
        for book in books:
            key = f"Book {book['book_no']}"  # match
            if key in coordinates:
                book['positions'] = coordinates[key]

        return books

