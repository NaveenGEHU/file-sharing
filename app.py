import os
import random
import string
import time
import threading
from flask import Flask, request, send_file, render_template, jsonify, redirect, send_from_directory
import google.generativeai as genai
from PyPDF2 import PdfReader
import magic 
import qrcode 


app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
LINK_EXPIRY = 15 * 60

genai.configure(api_key="AIzaSyCKReLexlYplY90YkEhFM2sAg8eRP6A3SU")

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

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)

        return response.text.strip()

    except Exception as e:
        return f"Could not generate description: {e}"



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
        filepath = os.path.abspath(filepath)
        file.save(filepath)

        # File type check removed - allow any file type

        # 🧠 AI Summaries & Suggestions
        ai_description = describe_file(filepath)

        random_id = generate_random_string()
        file_text = extract_text_from_file(filepath)
        share_link = request.host_url + random_id

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(share_link)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        qr_path = os.path.join(UPLOAD_FOLDER, f"{random_id}.png")
        img.save(qr_path)

        file_links[random_id] = {
            "filepath": filepath,
            "qr_path": qr_path,
            "time": time.time(),
            "text": file_text
        }

        qr_code_url = f"/uploads/{random_id}.png"

        return render_template("index.html",
                               link=share_link,
                               qr_code_url=qr_code_url,
                               error=None,
                               description=ai_description)

    return render_template("index.html", link=None, error=None)


@app.route("/<random_id>")
def download(random_id):
    """Serve local file if still valid"""
    file_info = file_links.get(random_id)
    if not file_info:
        return "Invalid or expired link", 404
    filepath = file_info.get("filepath")
    if not filepath or not os.path.exists(filepath):
        return "File not found or expired", 404

    return send_file(filepath, as_attachment=True)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


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
        prompt = f"You are an assistant helping users understand their uploaded document. Here’s the file content:\n\n{context_text[:3000]}\n\nQuestion: {question}"

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        answer = response.text.strip()
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"Error: {e}"})

def cleanup_expired_links():
    """Periodically remove expired links and files"""
    while True:
        now = time.time()
        expired = []
        for key, info in list(file_links.items()):
            if now - info["time"] > LINK_EXPIRY:
                expired.append(key)
                filepath = info.get("filepath")
                if filepath and os.path.exists(filepath):
                    os.remove(filepath)
                qr_path = info.get("qr_path")
                if qr_path and os.path.exists(qr_path):
                    os.remove(qr_path)

        for key in expired:
            del file_links[key]

        time.sleep(60)

threading.Thread(target=cleanup_expired_links, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)
