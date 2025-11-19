# File Sharing (Flask)

Simple Flask-based file-sharing web application that creates short-lived shareable links and QR codes for uploaded files. It also uses Google Generative AI to generate brief summaries of text/PDF uploads and provides a question-answer endpoint against the most recently uploaded file.

---

## Features

- Upload files (max 25 MB)
- Generate short random shareable links (default expiry: 15 minutes)
- Generate a QR code for each share link
- AI-generated summaries for text and PDF files (requires Google Generative AI API key)
- `/ask_ai` endpoint for Q&A on the most-recent upload
- Automatic cleanup of expired files and links (background thread)

## Repository structure

- `app.py` - main Flask application
- `templates/` - HTML templates (app expects `index.html`)
- `uploads/` - (created at runtime) stores uploaded files and generated QR codes
- `TODO.md`, `test.txt` - extras

## Requirements

The app uses the following Python libraries (inferred from `app.py`):

- Flask
- google-generative-ai (or the Google GenAI client library you use)
- PyPDF2
- python-magic (or python-magic-bin on Windows)
- qrcode
- pillow

Create a `requirements.txt` with these packages or install them directly:

pip install Flask google-generative-ai PyPDF2 python-magic qrcode pillow

Note: The exact package name for the Google Generative AI client can vary; install the package that matches the SDK you plan to use.

## Configuration

Important: Remove any hard-coded API keys from source. `app.py` currently contains a hard-coded Google API key — replace it to use an environment variable.

Recommended change in `app.py`:

```python
import os
# ...
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
```

Set the environment variable before running (Unix/macOS):

export GOOGLE_API_KEY="your_key_here"

Windows PowerShell:

$env:GOOGLE_API_KEY = "your_key_here"

If you do not want AI features, you can remove or comment out the `genai.configure(...)` line.

## Running locally

1. Clone the repository and create a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

2. Install dependencies:

pip install -r requirements.txt  # or pip install Flask PyPDF2 python-magic qrcode pillow google-generative-ai

3. Ensure `templates/index.html` exists (the app renders `index.html`).

4. Run the app:

python app.py

5. Open http://127.0.0.1:5000/ in your browser.

Notes:
- The app runs with `debug=True` when executed directly. For production, run behind a WSGI server (gunicorn/uWSGI) and disable debug.
- Uploaded files are stored in `uploads/` and removed after expiry by a background thread.

## Endpoints

- GET / - upload page (renders `index.html`)
- POST / - upload a file (form field name: `file`)
- GET /<random_id> - download the file if the link is still valid
- GET /uploads/<filename> - serves QR codes and other files in the uploads folder
- POST /ask_ai - JSON body: {"question":"..."} returns {"answer":"..."}

## Security & Production Considerations

- There is no authentication or authorization; do not expose this service publicly without adding access control.
- The code currently allows any file type. Reintroduce file-type checks and virus scanning for production.
- The app stores link state in memory; links will be lost on restart. Use a persistent store for production.
- Do not keep API keys in source. Use environment variables or a secrets manager.
- Consider using cloud storage (S3/GCS) for file storage if you expect large or many uploads.

## Suggested Improvements

- Add a `requirements.txt` and CI (lint/tests).
- Move AI processing to background tasks for responsiveness.
- Add authentication, access control, logging, and monitoring.
- Add a proper license file. Recommended default: MIT. If you'd like, I can add a LICENSE file — tell me which license you prefer.

## License

No license is included in the repository. If you want a license added, tell me which one (MIT, Apache-2.0, GPL-3.0, etc.) and I will add it.

---

If you want me to also add a `requirements.txt` and a LICENSE file (and push them to the repository), tell me which license to use and I will create and commit them.