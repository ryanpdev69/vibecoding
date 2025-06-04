from flask import Flask, request, render_template, jsonify
import requests
import os

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-3-haiku"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json["message"]
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vibecoding.onrender.com",  # Replace with your Render URL after deploy
        "X-Title": "VibeCoding AI"
    }
    
    system_prompt = """You're VibeCoding, a helpful AI coding assistant! 
    ... (same prompt here) ...
    """

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    reply = response.json()["choices"][0]["message"]["content"]
    
    return jsonify({"reply": reply})

# Remove this for production — Gunicorn handles it
# if __name__ == "__main__":
#     app.run(debug=True)
