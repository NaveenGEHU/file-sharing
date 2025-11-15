import os
import random
import string
import time
import threading
from flask import Flask, request, send_file, render_template, jsonify
import openai
from PyPDF2 import PdfReader
import magic 

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024 
LINK_EXPIRY = 15 * 60 

openai.api_key = "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"

file_links = {}


def generate_random_string(length=8):
    """Generate random ID for each file link"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def extract_text_from_file(filepath):
    """Extract readable text from PDF or text file"""
    try:
        if filepath.lower().endswith(".pdf"):
            reader = PdfReader(filepath)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
        else:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        return text.strip()
    except Exception:
        return ""


def describe_file(filepath):
    """Generate an AI-based summary of the uploaded file"""
    try:
        text = extract_text_from_file(filepath)
        if not text:
            return "No readable text found in this file."

        text = text[:4000] 
        prompt = f"Summarize this document in 3-5 sentences:\n\n{text}"

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message['content'].strip()

    except Exception as e:
        return f"Could not generate description: {e}"


def suggest_filename(filepath):
    """Suggest a better filename based on the file's content"""
    try:
        text = extract_text_from_file(filepath)
        if not text:
            return None

        text = text[:1000]
        prompt = f"Based on the following content, suggest a short and descriptive filename:\n\n{text}"

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message['content'].strip()
    except Exception:
        return None


def detect_file_type(filepath):
    """Detect potentially unsafe file types (e.g., executables)"""
    try:
        mime = magic.Magic(mime=True)
        file_mime = mime.from_file(filepath)
        if 'exe' in file_mime or 'script' in file_mime:
            return True
        return False
    except Exception:
        return False

@app.errorhandler(413)
def file_too_large(e):
    return "File is too large. Max limit is 25 MB.", 413


@app.route("/", methods=["GET", "POST"])
def upload():
    """Main upload page"""
    if request.method == "POST":
        if 'file' not in request.files:
            return render_template("index.html", link=None, error="No file selected")

        file = request.files['file']
        if file.filename == "":
            return render_template("index.html", link=None, error="No file selected")

        filename = file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        if detect_file_type(filepath):
            os.remove(filepath)
            return render_template("index.html", link=None, error="Malicious or unsupported file detected.")

        # 🧠 AI Summaries & Suggestions
        ai_description = describe_file(filepath)
        suggested_filename = suggest_filename(filepath)

        random_id = generate_random_string()
        file_text = extract_text_from_file(filepath)
        file_links[random_id] = {
            "path": filepath,
            "time": time.time(),
            "text": file_text
        }

        share_link = request.host_url + random_id

        return render_template("index.html",
                               link=share_link,
                               error=None,
                               description=ai_description,
                               suggested_filename=suggested_filename)

    return render_template("index.html", link=None, error=None)


@app.route("/<random_id>")
def download(random_id):
    """Serve file if link is still valid"""
    file_info = file_links.get(random_id)
    if not file_info:
        return "Invalid or expired link", 404
    return send_file(file_info["path"], as_attachment=True)


@app.route("/ask_ai", methods=["POST"])
def ask_ai():
    """Handle user questions about uploaded file content"""
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Please ask a valid question."}), 400

    if not file_links:
        return jsonify({"answer": "No uploaded file found for context."})

    last_file = list(file_links.values())[-1]
    context_text = last_file.get("text", "")

    try:
        messages = [
            {"role": "system", "content": "You are an assistant helping users understand their uploaded document."},
            {"role": "user", "content": f"Here’s the file content:\n\n{context_text[:3000]}"},
            {"role": "user", "content": question}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        answer = response.choices[0].message['content'].strip()
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"Error: {e}"})

def cleanup_expired_files():
    """Periodically remove expired files"""
    while True:
        now = time.time()
        expired = []
        for key, info in list(file_links.items()):
            if now - info["time"] > LINK_EXPIRY:
                try:
                    os.remove(info["path"])
                except FileNotFoundError:
                    pass
                expired.append(key)

        for key in expired:
            del file_links[key]

        time.sleep(60)

threading.Thread(target=cleanup_expired_files, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)
