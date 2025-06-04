from flask import Flask, request, render_template, jsonify
import requests
import os

app = Flask(__name__)

# Use environment variable for security
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-3-haiku"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vibecoding.onrender.com",  # Replace with your final deployed URL
        "X-Title": "VibeCoding AI"
    }

    system_prompt = """You're VibeCoding, a helpful AI coding assistant!

Your approach:
- Be friendly and encouraging, but focus on providing practical help
- When asked for code, provide complete, working examples
- Include brief explanations of what the code does
- Use emojis occasionally but don't overdo it
- Give constructive feedback and suggestions
- Always prioritize giving useful, actionable code solutions

For coding requests:
- Provide the actual code first
- Add brief explanations after the code
- Include comments in the code when helpful
- Suggest improvements or alternatives when relevant

Be supportive but prioritize being genuinely helpful with code and technical solutions."""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15  # optional timeout to avoid hanging
        )
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    
    except Exception as e:
        print("OpenRouter API Error:", e)
        print("Full response:", response.text if 'response' in locals() else "No response")
        return jsonify({"reply": "⚠️ Something went wrong with the AI response. Please try again later."}), 500
