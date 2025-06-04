from flask import Flask, request, render_template, jsonify
import requests
import os

app = Flask(__name__)

OPENROUTER_API_KEY = "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"
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
        "HTTP-Referer": "http://localhost:5000",  # Or your deployed URL
        "X-Title": "VibeCoding AI"
    }
    
    # Balanced system prompt - friendly but code-focused
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
    
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    reply = response.json()["choices"][0]["message"]["content"]
    
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)