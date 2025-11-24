# api.py
# uvicorn api:app --reload --host 127.0.0.1 --port 8000
# cloudflared tunnel --url http://127.0.0.1:8000

import asyncio
import os
import ast
from typing import Dict, Any
import numpy as np
import pandas as pd
import cv2
from sqlalchemy import create_engine
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import threading

from ultralytics import YOLO
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from core.utils.file_manager import ReadManager, WriteManager
from core.utils.io import ensure_directories, clean_old_dirs_async
from core.bookvision.vision import book_segments, book_recommendation
from core.bookvision.similarity import BookSimilarity
from core.process.helper import recommender_system
from core.utils.logger import setup_logging, get_logger

setup_logging(log_path="logs/api.log", console_level="INFO")
log = get_logger("bookvision-backend")
load_dotenv()
read = ReadManager()
write = WriteManager()

# FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB
NEON_API_URL = os.getenv("NEON_URI")
engine = create_engine(NEON_API_URL)

# ------------------ Paths ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "prompt.txt")
DATA_DIR = os.path.join(BASE_DIR, "data")
ensure_directories(DATA_DIR)

# ------ To clean temp directories ----------
# Lifespan handler (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):

    global yolo_cover, yolo_spine
    # Load model once
    yolo_cover = YOLO(r"models\BCIS_Y8n.pt")
    yolo_spine = YOLO(r"models\BSIS_Y8m.pt")
    log.info("load.success [YOLO MODELS]")

    # Start background cleanup thread
    monitor_thread = threading.Thread(
        target=lambda: asyncio.run(
            clean_old_dirs_async(DATA_DIR, max_age_minutes=15, interval_seconds=120)
        ),
        daemon=True
    )
    monitor_thread.start()
    log.info("[Startup] File cleanup thread started.")

    yield  # app runs normally

    log.info("[Shutdown] App shutting down.")

app.router.lifespan_context = lifespan

# ------------------ Extractor ------------------
try:
    from core.bookvision.extractor import Extractor
    HAS_EXTRACTOR = True
    log.info("Using real Extractor from src.core.bookvision.extractor")
except Exception:
    HAS_EXTRACTOR = False
    log.info("Extractor not available; using fallback stub implementations")

# ------------------ Helpers ------------------
def fetch_book_info_stub(books_input: Dict[str, Any], delay: float = 1.0) -> pd.DataFrame:
    title = books_input.get("title") or ""
    authors = books_input.get("authors") or ""
    row = {
        "serial_no": 1,
        "title": title,
        "authors": authors,
        "isbn": "",
        "description": "",
        "google_rating": "",
        "google_counts": "",
        "amazon_rating": "",
        "amazon_counts": "",
        "language": "",
        "page_counts": "",
        "categories": "",
        "publisher": "",
        "published_date": "",
        "image_link": "",
        "preview_link": "",
        "positions": "",
        "subjects": ""
    }
    return pd.DataFrame([row])

def _safe_uid(uid: str) -> str:
    # Allow only basic UUID characters to avoid path traversal
    if not isinstance(uid, str) or not uid:
        raise ValueError("invalid uid")
    # Only allow alphanumerics, dash and underscore
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]+", uid):
        raise ValueError("invalid uid characters")
    return uid


def user_store_paths(uid: str, type: str):
    uid = _safe_uid(uid)

    USER_DIR = os.path.join(DATA_DIR, uid)
    STORE_DIR = os.path.join(USER_DIR, "store")
    IMG_DIR = os.path.join(USER_DIR, "images")

    # Ensure exixtence of directory
    ensure_directories([USER_DIR, STORE_DIR, IMG_DIR])

    if type == 'store':
        user_store_csv = os.path.join(STORE_DIR, f"cover_data.csv")
        user_mod_store_csv = os.path.join(STORE_DIR, f"shelf_data.csv")
        return user_store_csv, user_mod_store_csv
    
    elif type == 'inputs':
        user_cover_csv = os.path.join(IMG_DIR, f"cover_image.png")
        user_final_image = os.path.join(IMG_DIR, f"final_image.png")
        return user_cover_csv, user_final_image
    
    elif type == 'debug':
        masks_img = os.path.join(IMG_DIR, f"masks_img.png")
        bbox_img = os.path.join(IMG_DIR, f"bbox_img.png")
        segments_img = os.path.join(IMG_DIR, f"segments_img.png")
        cover_segm_img = os.path.join(IMG_DIR, f"cover_segments_img.png")
        return masks_img, bbox_img, segments_img, cover_segm_img
    else:
        print("Provide type.")


def save_books_metadata(df: pd.DataFrame, uid: str, is_input: bool = True) -> None:
    user_store_csv, user_mod_store_csv = user_store_paths(uid, type= "store")

    if is_input:
        write.files(file_content=df, output_path=user_store_csv)
    else:
        write.files(file_content=df, output_path=user_mod_store_csv)

def load_store_data() -> pd.DataFrame:

    try:
        db = pd.read_sql("SELECT * FROM books_metadata", engine)
        log.info("success.db")
        return db
    except:
        cols = [
            "serial_no", "title", "authors", "isbn", "description",
            "google_rating", "google_counts", "amazon_rating", "amazon_counts",
            "language", "page_counts", "categories", "publisher",
            "published_date", "image_link", "preview_link", "positions", "subjects"
        ]
        return pd.DataFrame(columns=cols)

# ------------------ API Endpoints ------------------
def _get_uid_from_request(request: Request) -> str:
    uid = request.headers.get("X-User-ID")
    if not uid:
        raise HTTPException(status_code=400, detail="Missing X-User-ID header")
    try:
        uid = _safe_uid(uid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid X-User-ID header")
    return uid


@app.post("/api/input/image")
async def input_image(request: Request, image: UploadFile = File(...)):
    uid = _get_uid_from_request(request)
    if not image.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
    
    # Save per-user input cover
    user_cover_csv, _ = user_store_paths(uid, type= "inputs")
    _, _, _, cover_segm_img = user_store_paths(uid, type= "debug")

    with open(user_cover_csv, "wb") as f:
        f.write(await image.read())

    # Prediction
    segments_image, _, _, crop_coordinates, _ = book_segments(user_cover_csv, yolo_cover, class_filter="book", threshold=0.2, need_visuals= True)

    # Save cover seg image
    segments_image.save(cover_segm_img)

    # OCR / Extractor
    cover_info = {"title": "", "authors": ""}
    try:
        extract = Extractor()
        if HAS_EXTRACTOR and hasattr(extract, "ocr_cover"):
            cover_info = extract.ocr_cover(IMG=segments_image, Prompt_path=PROMPT_PATH, coordinates=crop_coordinates, segment_path=cover_segm_img)
        else:
            cover_info = {"title": "Detected Book Title", "authors": "Detected Author"}
    except Exception as e:
        log.exception("Error running OCR/extractor: %s", e)

    # Fetch book info
    try:
        if HAS_EXTRACTOR and hasattr(extract, "fetch_book_info"):
            df = extract.fetch_book_info(books_input=cover_info, delay= 1.0)
            if isinstance(df, pd.DataFrame):
                save_books_metadata(df, uid=uid)
        else:
            df = fetch_book_info_stub(cover_info)
            save_books_metadata(df, uid=uid)
    except Exception as e:
        log.exception("Error fetching book info: %s", e)
        raise HTTPException(status_code=500, detail="failed to fetch book info")
    
    return JSONResponse(df.fillna("").to_dict(orient="records"))

@app.post("/api/input/self")
async def input_self(request: Request):
    uid = _get_uid_from_request(request)
    payload = await request.json()
    if not payload or ("title" not in payload and "authors" not in payload):
        raise HTTPException(status_code=400, detail="Payload must include 'title' or 'authors'")
    
    payload['book_no'] = 1
    payload['author_verified'] = True
    payload['positions'] = None
    try:
        extract = Extractor()
        if HAS_EXTRACTOR and hasattr(extract, "fetch_book_info"):
            df = extract.fetch_book_info(books_input=[payload], delay= 1.0, is_input=True)
            if isinstance(df, pd.DataFrame):
                save_books_metadata(df, uid=uid)
            else:
                df = load_store_data()
        else:
            df = fetch_book_info_stub(payload)
            save_books_metadata(df, uid=uid)
    except Exception as e:
        log.exception("Error fetching book info from self input: %s", e)
        raise HTTPException(status_code=500, detail="failed to fetch book info")

    return JSONResponse(df.fillna("").to_dict(orient="records"))

@app.post("/api/input/store")
async def input_store_db(request: Request):
    uid = _get_uid_from_request(request)
    payload = await request.json()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")
    isbn = payload.get("isbn") or payload.get("ISBN-10")
    if not isbn:
        raise HTTPException(status_code=400, detail="Payload must include 'isbn' or 'ISBN-10'")

    store_df = load_store_data()
    isbn_col = next((c for c in store_df.columns if "isbn" in c.lower()), None)
    if not isbn_col:
        raise HTTPException(status_code=500, detail="No ISBN column found in store data")

    matches = store_df[store_df[isbn_col].astype(str).str.strip() == str(isbn)]
    if matches.empty:
        raise HTTPException(status_code=404, detail="isbn not found")

    info_df = pd.DataFrame([{
        "serial_no": 1,
        "title": row.get("title"),
        "authors": row.get("authors"),
        "isbn": row.get("isbn"),
        "description": row.get("description"),
        "google_rating": row.get("google_rating"),
        "google_counts": row.get("google_counts"),
        "amazon_rating": row.get("amazon_rating"),
        "amazon_counts": row.get("amazon_counts"),
        "language": row.get("language"),
        "page_counts": row.get("page_counts"),
        "categories": row.get("categories"),
        "publisher": row.get("publisher"),
        "published_date": row.get("published_date"),
        "image_link": row.get("image_link"),
        "preview_link": row.get("preview_link"),
        "subjects": row.get("subjects"),
        "positions": None
    } for _, row in matches.iterrows()])
    # Overwrite per-user store csv with this selected item
    user_store_csv, _= user_store_paths(uid, type= "store")
    info_df.to_csv(user_store_csv, index=False)

    out = []
    for _, r in matches.fillna("").iterrows():
        out.append({
            "isbn": r.get(isbn_col, ""),
            "title": r.get("title", "") or r.get("Title", ""),
            "authors": r.get("authors", "") or r.get("author", ""),
            "image_link": r.get("image_link", "") or r.get("image", "")
        })
    return JSONResponse(out)

# --------------------------------------------------- 2nd Page --------------------------------------------------
def process_shelf_pipeline(image_path, uid):
    """
    ALL heavy work stays here.
    This function runs inside a thread pool.
    """

    # YOLO segmentation (CPU/GPU heavy)
    segments_image, bbox_img, mask_overlay, crop_coordinates, _ = book_segments(
        image_path, yolo_spine, class_filter="book", need_visuals=True
    )

    # Save segmentation debug images (OpenCV blocks)
    mask_dir, bbox_dir, segm_dir, _ = user_store_paths(uid=uid, type="debug")

    mask_overlay = cv2.cvtColor(mask_overlay, cv2.COLOR_RGB2BGR)
    cv2.imwrite(mask_dir, mask_overlay)

    bbox_img = cv2.cvtColor(bbox_img, cv2.COLOR_RGB2BGR)
    cv2.imwrite(bbox_dir, bbox_img)

    segments_image.save(segm_dir)

    # OCR
    try:
        extract = Extractor()
        if HAS_EXTRACTOR and hasattr(extract, "ocr_shelf"):
            cover_info = extract.ocr_shelf(
                IMG=segments_image, 
                Prompt_path=PROMPT_PATH, 
                coordinates=crop_coordinates,
                segment_path=segm_dir
            )
        else:
            cover_info = {"title": "Detected Book Title", "authors": "Detected Author"}
    except Exception:
        cover_info = {"title": "", "authors": ""}

    # Fetch book meta info (blocking HTTP/DB)
    if HAS_EXTRACTOR and hasattr(extract, "fetch_book_info"):
        df = extract.fetch_book_info(books_input=cover_info, delay=0.1)
        if isinstance(df, pd.DataFrame):
            save_books_metadata(df, uid=uid, is_input=False)
    else:
        df = fetch_book_info_stub(cover_info)
        save_books_metadata(df, uid=uid, is_input=False)

    return df


@app.post("/api/image_upload/image")
async def shelf_image(request: Request, image: UploadFile = File(...)):
    uid = _get_uid_from_request(request)

    if not image.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
    
    # SAVE IMAGE (this is async)
    _, user_final_image = user_store_paths(uid, type="inputs")

    with open(user_final_image, "wb") as f:
        f.write(await image.read())     # <-- non-blocking

    # RUN THE ENTIRE ML / OCR / YOLO PIPELINE IN THREAD
    try:
        df = await run_in_threadpool(process_shelf_pipeline, user_final_image, uid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"processing failed: {e}")

    return JSONResponse(df.fillna("").to_dict(orient="records"))

@app.post("/api/image_upload/recommender")
async def recommender(request: Request):
    uid = _get_uid_from_request(request)
    log.info("Recommender endpoint called for uid=%s client=%s", uid, request.client)

    payload = await request.json()
    if not payload or ("no_recoms" not in payload):
        raise HTTPException(status_code=400, detail="Payload must include 'no_recoms'")
    no_recom = int(payload['no_recoms'])
    try:
        log.info("Recommender request.base_url=%s host=%s", request.base_url, request.client.host)

        # Load per-user store files first (fall back to global DB)
        user_store_csv, user_mod_store_csv = user_store_paths(uid, type= "store")
        input_df = pd.read_csv(user_store_csv)
        shelf_df = pd.read_csv(user_mod_store_csv)
        if input_df.empty and shelf_df.empty:
            return JSONResponse([])

        data = pd.concat([input_df, shelf_df], ignore_index=True)
        similarity = BookSimilarity(data=data).score()
        movie_name = data.title.values[0] if len(data) > 0 else ""
        recom = recommender_system(data=data, matrix=similarity, movie_name=movie_name, recom_n=no_recom)
        recom['coord'] = recom['coord'].apply(ast.literal_eval)

        # Save final image per-user
        _, image_path = user_store_paths(uid, type= "inputs")
        final_img = book_recommendation(image_path=image_path, df=recom)
        final_img = cv2.cvtColor(final_img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(image_path, final_img)

        out = []
        for _, r in recom.iterrows():
            score = r.get("similarity_score", 0) 
            try:
                score = float(score)
                if np.isnan(score):
                    score = 0.0
            except Exception:
                score = 0.0

            coord = r.get("coord") or r.get("positions")
            if isinstance(coord, (np.ndarray, list, tuple)):
                coord = [int(x) if x is not None and not pd.isna(x) else 0 for x in coord]
            else:
                coord = None

            def safe_int(val):
                try:
                    return int(val) if val is not None and not pd.isna(val) else 0
                except Exception:
                    return 0

            def safe_str(val):
                return str(val) if val is not None and not pd.isna(val) else ""

            google_rating = safe_int(r.get("google_rating"))
            amazon_rating = safe_int(r.get("amazon_rating"))

            item = {
                "title": safe_str(r.get("title")),
                "similarity_score": score,
                "authors": safe_str(r.get("authors")),
                "isbn": safe_str(r.get("isbn")),
                "description": safe_str(r.get("description")),
                "language": safe_str(r.get("language")),
                "rating": max(google_rating, amazon_rating),
                "page_counts": safe_str(r.get("page_counts")),
                "categories": safe_str(r.get("categories")),
                "publisher": safe_str(r.get("publisher")),
                "published_date": safe_str(r.get("published_date")),
                "image_link": safe_str(r.get("image_link")),
                "preview_link": safe_str(r.get("preview_link")),
                "coord": coord,
            }
            out.append(item)

        # Build final image URL using request.base_url so the host and port are included
        # request.client.host alone does not include port; base_url includes host:port when present
        base = str(request.base_url).rstrip('/')
        final_image_url = f"{base}/api/image_upload/final_image?uid={uid}"
        return JSONResponse({"final_image_url": final_image_url, "recom": out})

    except Exception as e:
        log.exception("Recommender failed: %s", e)
        raise HTTPException(status_code=500, detail="Recommender failed")

@app.get("/api/store/books")
async def get_store_books(request: Request, limit: int = 50):
    log.info("--------------------------- Started Application ---------------------------")
    try:
        uid = _get_uid_from_request(request)
    except HTTPException:
        # If missing, fall back to global DB
        uid = None
    df = load_store_data()
    if df.empty:
        return JSONResponse([])

    isbn_col = "isbn" if "isbn" in df.columns else next((c for c in df.columns if "isbn" in c.lower()), None)
    title_col = "title" if "title" in df.columns else next((c for c in df.columns if "title" in c.lower()), None)
    authors_col = "authors" if "authors" in df.columns else next((c for c in df.columns if "author" in c.lower()), None)
    image_col = "image_link" if "image_link" in df.columns else next((c for c in df.columns if "image" in c.lower()), None)

    selected_cols = [c for c in [isbn_col, title_col, authors_col, image_col] if c]
    data = df.head(len(df))[selected_cols].fillna("")

    records = []
    for _, row in data.iterrows():
        records.append({
            "isbn": row.get(isbn_col, ""),
            "title": row.get(title_col, ""),
            "authors": row.get(authors_col, ""),
            "image_link": row.get(image_col, ""),
        })
    return JSONResponse(records) 

@app.get("/api/image_upload/final_image")
async def serve_final_image(request: Request, uid: str = None):
    # Prefer uid query param, then header
    if not uid:
        try:
            uid = _get_uid_from_request(request)
        except HTTPException:
            uid = None

    if not uid:
        raise HTTPException(status_code=400, detail="Missing uid for final image")

    try:
        _, path = user_store_paths(uid, type= "inputs")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid uid")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="final image not found")
    return FileResponse(path, media_type="image/png")


@app.api_route("/api/image_upload/{filename}", methods=["GET", "HEAD"])
async def serve_debug_image(request: Request, filename: str):
    """Serve debug images saved into IMG_DIR such as mask_overlay.png, bbox_img.png, segments_image.png.

    This endpoint is intentionally permissive for these specific filenames only to avoid exposing arbitrary files.
    """
    try:
        # Only allow known debug image filenames (per-user variants allowed)
        base_allowed = {f"masks_img.png", "bbox_img.png", "segments_img.png"}
        # Allow patterns like mask_overlay_<uid>.png
        import re
        if filename not in base_allowed:
            m = re.match(r"^(masks_img|bbox_img|segments_img)_([A-Za-z0-9_-]+)\.(png|jpg|jpeg)$", filename)
            if not m:
                log.info("Attempt to access disallowed debug file: %s", filename)
                raise HTTPException(status_code=404, detail="file not found")

        # Get UID
        filename, uid = (f"{m.group(1)}.{m.group(3)}", m.group(2)) if (m := re.match(r"^(masks_img|bbox_img|segments_img)_([A-Za-z0-9_-]+)\.(png|jpg|jpeg)$", filename)) else (None, None)
        IMG_DIR = os.path.join(DATA_DIR, uid, "images")
        
        path = os.path.join(IMG_DIR, filename)
        # Resolve and ensure the file is inside IMG_DIR
        path_abs = os.path.abspath(path)
        if not path_abs.startswith(os.path.abspath(IMG_DIR)):
            log.warning("Path traversal attempt blocked: %s", path)
            raise HTTPException(status_code=400, detail="invalid filename")

        if not os.path.exists(path_abs):
            log.info("Debug image not yet available: %s", path_abs)
            raise HTTPException(status_code=404, detail="file not found")

        # Best-effort media type detection for png/jpg
        media_type = "image/png"
        if filename.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"

        # If the client sent HEAD, return headers only (no body)
        if request.method == "HEAD":
            try:
                size = os.path.getsize(path_abs)
            except Exception:
                size = None
            headers = {"content-type": media_type}
            if size is not None:
                headers["content-length"] = str(size)
            log.info("Responding to HEAD for debug image: %s", filename)
            return Response(status_code=200, headers=headers)

        log.info("Serving debug image: %s", filename)
        return FileResponse(path_abs, media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Error serving debug image %s: %s", filename, e)
        raise HTTPException(status_code=500, detail="failed to serve debug image")