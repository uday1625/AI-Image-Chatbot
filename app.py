import os
import re
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ==============================
# Load .env
# ==============================
load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    exit()

print(f"✅ API Loaded: {api_key[:10]}...")

# ==============================
# Gemini Configuration
# ==============================
genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

# ==============================
# Flask App Setup
# ==============================
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

chat_history = []

# ==============================
# Helper Functions
# ==============================
def preprocess_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s?.!,]", "", text)
    return text


def get_prompt(user_input):

    memory = "\n".join(
        [f"User: {u}\nEduBot: {b}" for u, b in chat_history[-5:]]
    )

    return f"""
You are EduBot, a concise educational tutor.

Rules:
- Give short answers
- Use bullet points
- Avoid long paragraphs
- Be clear and direct

{memory}

User: {user_input}

EduBot:
"""


# ==============================
# Routes
# ==============================
@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/get", methods=["POST"])
def chat():

    user_msg = request.form["msg"]

    cleaned_msg = preprocess_text(user_msg)

    prompt = get_prompt(cleaned_msg)

    try:

        response = model.generate_content(prompt)

        bot_reply = (
            response.text.strip()
            if response.text
            else "Please repeat your question."
        )

    except Exception as e:

        bot_reply = f"Error: {str(e)}"

    chat_history.append((user_msg, bot_reply))

    if len(chat_history) > 20:
        chat_history.pop(0)

    return jsonify({"response": bot_reply})


@app.route("/analyze", methods=["POST"])
def analyze_file():

    file = request.files.get("file")

    if not file:
        return jsonify({"response": "No file uploaded."})

    filename = secure_filename(file.filename)

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    try:

        # Image analysis
        if filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):

            uploaded = genai.upload_file(filepath)

            prompt = """
Analyze this image.

Explain:
- What is visible
- Important objects
- Educational interpretation

Use bullet points only.
"""

            response = model.generate_content(
                [prompt, uploaded]
            )

        else:

            response = model.generate_content(
                "Summarize this document in short educational points."
            )

        result = (
            response.text.strip()
            if response.text
            else "No response generated."
        )

        return jsonify({"response": result})

    except Exception as e:

        return jsonify({
            "response": f"Analysis Error: {str(e)}"
        })


# ==============================
# Run App
# ==============================
if __name__ == "__main__":
    app.run(debug=True)