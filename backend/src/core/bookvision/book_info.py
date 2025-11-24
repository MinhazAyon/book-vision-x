
# --- Standard Python imports ---
import logging
import numpy as np
import os
import re
from typing import Optional

# --- Third-party imports ---
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# --- Local imports ---
from core.utils.file_manager import ReadManager, WriteManager
from core.utils.logger import get_logger

log = get_logger(__name__)
load_dotenv()
read = ReadManager()
write = WriteManager()

# DB
NEON_API_URL = os.getenv("NEON_URI")
engine = create_engine(NEON_API_URL)

class StoreData:
    """
    A class to handle and store unique data.

    Attributes:
        log (logging.Logger): Logger instance for logging events.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initializes the GeneralAnalyzer object with an optional logger and dataframe.
        
        Args:
            logger (Optional[logging.Logger]): A logger to be used by the strategy (default None).
        """
        base = logger or log
        self.log =  base.getChild(self.__class__.__name__)

    @staticmethod
    def extract_book_ids(row_value):
        """
        Parse a mixed string of book identifiers and separate them into columns:
        ISBN-10, ISBN-13, OCLC, LCCN, DOI, ISSN, ASIN.
        """
        result = {
            "ISBN-10": np.nan,
            "ISBN-13": np.nan,
            "OCLC": np.nan,
            "LCCN": np.nan,
            "DOI": np.nan,    
            "ISSN": np.nan,   
            "ASIN": np.nan    
        }
        
        if not row_value or pd.isna(row_value):
            return result
        
        # Split by comma or semicolon
        parts = [p.strip() for p in re.split(r"[,;]", str(row_value))]
        
        isbn_10_list, isbn_13_list, oclc_list, lccn_list = [], [], [], []
        doi_list, issn_list, asin_list = [], [], [] 
        
        for part in parts:
            if not part:
                continue
                
            part_upper = part.upper()
            
            # --- Prefixed Identifiers ---
            
            # OCLC
            if part_upper.startswith("OCLC:"):
                value = part.split(":", 1)[1].strip()
                oclc_list.append(re.sub(r"[^0-9]", "", value)) 
            # LCCN
            elif part_upper.startswith("LCCN:"):
                value = part.split(":", 1)[1].strip()
                lccn_list.append(value)
            # DOI (New)
            elif part_upper.startswith("DOI:"):
                value = part.split(":", 1)[1].strip()
                doi_list.append(value)
            # ISSN (New)
            elif part_upper.startswith("ISSN:"):
                value = part.split(":", 1)[1].strip()
                issn_list.append(re.sub(r"[^0-9Xx]", "", value)) 
            # ASIN (New)
            elif part_upper.startswith("ASIN:"):
                value = part.split(":", 1)[1].strip()
                asin_list.append(re.sub(r"[^A-Za-z0-9]", "", value)) 
            # ISBN
            elif part_upper.startswith("ISBN:"):
                value = part.split(":", 1)[1].strip()
                digits_only = re.sub(r"[^0-9]", "", value)
                digits_and_x = re.sub(r"[^0-9Xx]", "", value)
                
                if len(digits_only) == 13:
                    isbn_13_list.append(digits_only)
                elif len(digits_and_x) == 10:
                    isbn_10_list.append(digits_and_x)
            
            # --- No Prefix: Guess based on pattern ---
            else:
                digits_only = re.sub(r"[^0-9]", "", part)
                digits_and_x = re.sub(r"[^0-9Xx]", "", part.upper())
                
                # DOI (e.g., "10.1000/12345")
                if part.startswith("10."):
                    doi_list.append(part)
                    
                # ASIN (e.g., "B000FA5KKC")
                elif len(part) == 10 and part.upper().startswith("B0") and part.isalnum():
                    asin_list.append(part.upper())
                    
                # ISBN-13 (13 digits)
                elif len(digits_only) == 13 and (digits_only.startswith("978") or digits_only.startswith("979")):
                    isbn_13_list.append(digits_only)
                    
                # ISBN-10 (10 digits/X)
                elif len(digits_and_x) == 10:
                    isbn_10_list.append(digits_and_x)
                    
                # ISSN (8 digits/X)
                elif len(digits_and_x) == 8:
                    issn_list.append(digits_and_x)
                    
                # LCCN (User's original logic, slightly safer)
                elif part.isdigit() and 6 <= len(part) <= 12: # Common LCCN length
                    lccn_list.append(part)
                    
                # OCLC (User's original logic, as a fallback)
                elif part.isdigit() and len(part) > 5: # Avoid short random numbers
                    oclc_list.append(part)
        
        # --- Assign lists or NaN ---
        result["ISBN-10"] = ",".join(isbn_10_list) if isbn_10_list else np.nan
        result["ISBN-13"] = ",".join(isbn_13_list) if isbn_13_list else np.nan
        result["OCLC"] = ",".join(oclc_list) if oclc_list else np.nan
        result["LCCN"] = ",".join(lccn_list) if lccn_list else np.nan
        result["DOI"] = ",".join(doi_list) if doi_list else np.nan       
        result["ISSN"] = ",".join(issn_list) if issn_list else np.nan     
        result["ASIN"] = ",".join(asin_list) if asin_list else np.nan  
        
        return result

    def process_frame(self, data:pd.DataFrame):
        from core.bookvision.extractor import Extractor 
        
        if 'positions' in data.columns:
            data.drop(columns=['serial_no', 'positions'], inplace=True)
        else:
            data.drop(columns='serial_no', inplace=True)

        data = data[data.title != 'Unreadable'].reset_index(drop=True)
        data = data.replace(['None', None, 'Not available', 'nan', 'NaN', ''], np.nan)
        # Seperate IDs
        data = (
            pd.concat([data, data["isbn"]
            .apply(self.extract_book_ids)
            .apply(pd.Series)], axis=1)
            .drop(columns=['isbn'])
        )
        # Remove NAN
        data = data.dropna(subset=["ISBN-10", "ISBN-13", "OCLC", "LCCN", 'DOI', 'ISSN', 'ASIN', "authors"], how='all').reset_index(drop=True)

        # Consolidate all possible book identifiers into one "isbn" column
        data['isbn'] = data.apply(
            lambda r: Extractor.fill_priority(
                r, ["ISBN-10", "ISBN-13", "OCLC", "LCCN", "DOI", "ISSN", "ASIN"]
            ),
            axis=1
        )

        return data
    
    @staticmethod
    def store_data(existing_df, new_books_df):
        """
        Merge new books into existing_df, keeping the row with fewer NaNs if duplicates exist.
        Duplicate check is based on any of the IDs (ISBN-10, ISBN-13, OCLC, LCCN).
        Falls back to title+authors if all IDs are NaN.

        Args:
            existing_df (pd.DataFrame): Existing books
            new_books_df (pd.DataFrame): New books

        Returns:
            pd.DataFrame: Updated DataFrame with new books added or replacing less complete duplicates
        """

        id_cols = ["ISBN-10", "ISBN-13", "OCLC", "LCCN", "DOI", "ISSN", "ASIN"]
        all_cols = id_cols + ["title", "authors"]
        result_rows = []

        for _, new_row in new_books_df.iterrows():
            # Start with all False
            mask = pd.Series(False, index=existing_df.index)
            
            # Match by IDs
            for col in id_cols:
                val = new_row[col]
                if pd.notna(val):
                    mask |= existing_df[col] == val
            
            matched = existing_df[mask]

            # Fallback: title + authors
            if matched.empty:
                matched = existing_df[
                    (existing_df["title"] == new_row["title"]) &
                    (existing_df["authors"] == new_row["authors"])
                ]

            # Add or replace based on NaN count
            if matched.empty:
                result_rows.append(new_row)
            else:
                new_nan = new_row[all_cols].isna().sum()
                old_nan = matched[all_cols].isna().sum(axis=1).min()
                if new_nan < old_nan:
                    existing_df = existing_df.drop(matched.index)
                    result_rows.append(new_row)

        results = pd.DataFrame(result_rows)
        return existing_df, results
    
    @staticmethod
    def remove_duplicates(old, new):
        # Add a temporary identifier
        old_df = old.copy()
        new_df = new.copy()
        old_df['_source'] = 'old'
        new_df['_source'] = 'new'

        # Concatenate both DataFrames
        combined = pd.concat([old_df, new_df], ignore_index=True)

        # Process                             
        combined[['amazon_rating', 'amazon_counts']] = combined[['amazon_rating', 'amazon_counts']].astype('float64')
        combined['LCCN'] = combined['LCCN'].astype('object')

        # Redroping
        dupl = []
        for col in ['ISBN-10', 'ISBN-13', 'OCLC', 'LCCN', 'DOI', 'ISSN', 'ASIN', 'title']:
            dup_rows = combined[combined[col].notna() & combined[col].duplicated(keep='first')].index
            dupl.extend(dup_rows)
        # Drop    
        combined = combined.drop(index=dupl).reset_index(drop=True)

        # New Data
        clean_data = combined[combined['_source'] == 'new'].drop(columns=['_source']).reset_index(drop=True)

        return clean_data
    
    # Final function
    def store(self, old_info: pd.DataFrame, new_info:pd. DataFrame):

        # Process books
        new = self.process_frame(data=new_info)

        # Store Data
        old_data, final_data = self.store_data(old_info, new)

        if final_data.empty:
            self.log.info("No new contents added.")

        else:
            # Cleaned data
            data = self.remove_duplicates(old=old_data, new=final_data)

            # Save Data
            data.to_sql(
                "books_metadata",
                con=engine,
                if_exists="append", 
                index=False
            )

            self.log.info("store.success new added contents=%s", data.shape)
