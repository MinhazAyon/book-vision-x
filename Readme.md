# BookVisionX – AI Book Recommender

[![License](https://img.shields.io/badge/license-MIT-green)](#license)

## Project Overview

BookVisionX – AI Book Recommender System makes finding books easier by combining computer vision with intelligent recommendation systems. In traditional libraries or bookstores, it can be hectic to locate books related to your favorite content, especially when series or similar books are scattered across shelves. BookVisionX simplifies this process: first, users take a picture of their favorite book’s cover, and the system uses YOLO (You Only Look Once) and OCR (Optical Character Recognition) to extract text information such as the title and author. Next, users can take a picture of the bookshelf, where YOLO segments books (spines) and localizes each book with bounding boxes, cropping each region for further analysis. Each cropped book cover is passed through OCR to fetch metadata from sources such as the Google Books API, Open Library by extracted title and authors. The system then compares the extracted favorite book information with the detected bookshelf books, ranking recommendations based on content similarity—considering text features like titles, authors, categories, and descriptions. Finally, users receive a user-friendly output: an annotated bookshelf image with recommended books highlighted via bounding boxes and similarity percentages, their details, and making it effortless to discover the next book to read.

Furthermore, a React + Next.js web application (deployed on Vercel) serves as the frontend. It communicates with a standalone FastAPI backend—responsible for hosting datasets and ML models—by sending user inputs and rendering the returned recommendations.

Explore and test the website here: [MN-Predict Unknown and Unseen](https://mn-frontend-pages.onrender.com)

--- 

## Table of Contents

- [Project Overview](#project-overview)
- [Project Highlights](#project-highlights)
- [Dataset](#dataset)
- [Installation](#installation)
- [License](#license)
- [Contact](#contact)

---
## Project Highlights

- **Book Detection:** 

	- Implemented YOLOV8-seg for detecting book covers and spines (nano version for cover, medium for spine).

- **OCR:** 

	- Utilizes Gemini 2.5 Flash (primary) and Groq (meta-llama/llama-4-maverick-17b-128e-instruct) (alternative) APIs for accurate text extraction from book covers and spines.

- **Book Metadata Fetching:**

	- Retrieves metadata via Google Books API, with Open Library as an optional source.

	- If OCR extraction reliably captures title and author, the system directly fetches book information via exact matching.

	- If exact match fails, it searches by title, retrieves the top 40 results, and applies similarity thresholds (≥70% for title, ≥50% for author) to select the most relevant book.

	- Handles books with unclear authors similarly. Unreadable books are discarded.

- **Content Similarity:**

	- For recommendations from bookshelf books, the system calculates cosine similarity using TF-IDF embeddings of titles, authors, and other book content to find the most relevant matches.

- **Frontend & Backend:**

	- Frontend deployed on Vercel, providing an interactive interface.

	- Backend powered by FastAPI, managing OCR, detection, and recommendation logic.

---
## Datasets

### Book Cover
- **Dataset**: Kitaptanıma (Roboflow Universe)
- **URL**: [https://universe.roboflow.com/minhaz/kitaptanima-2lfio](https://universe.roboflow.com/computervision-jynhl/kitaptanima)
- **Usage**: Used for training and validating book cover detection. Polygon segments were created manually for this project.
- **License**: CC BY 4.0
- **Project Link**: [Book Cover Segmentation](https://universe.roboflow.com/minhaz/book_cover_segmentation-vjwhu)

### Book Spine
- **Dataset**: Book Spine Detection (Roboflow Universe)
- **URL**: [https://universe.roboflow.com/books-26cz6/book-spline-detection](https://universe.roboflow.com/books-26cz6/book-spline-detection)
- **Usage**: Labeled book spine instances for spine detection and segmentation.
- **License**: CC BY 4.0

---

## Installation

1. Clone the repository:
```bash
git clone https://github.com/MinhazAyon/book-vision-x.git
cd book-vision-x
```

2. Create a virtual environment and activate it:
```bash
python -m venv expenv
source venv/bin/activate     # Linux/macOS
venv\Scripts\activate        # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the FastAPI backend:

```bash
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

5. Configure environment variable for the frontend (.env):

```bash
NEXT_PUBLIC_FASTAPI_URL="http://127.0.0.1:8000"
```

5. Run the React/Next.js frontend:

```bash
npm run dev
```

The frontend will run locally at:

[Click Here](http://127.0.0.1:3000)

---

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/MinhazAyon/book-vision-x/blob/main/LICENSE) file for details. 

---

## Contact

- **Author:** Minhaz Uddin  
- **Email:** minhaz182219@gmail.com  
- **GitHub:** [github.com/MinhazAyon](https://github.com/MinhazAyon)
- **Whatsapp:** 01628182219

