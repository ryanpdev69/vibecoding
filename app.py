from flask import Flask, request, render_template, jsonify
import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use environment variable for security
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-3-haiku"

# Health check endpoint for Render
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "message": "VibeCoding is running!"}), 200

@app.route("/")
def home():
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving home page: {e}")
        return jsonify({"error": "Template not found"}), 500

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message", "")
        logger.info(f"Received chat request: {user_input[:50]}...")
        
        # Check if API key is available
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found in environment variables")
            return jsonify({"reply": "⚠️ API key not configured. Please contact the administrator."}), 500
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://vibecoding-y73m.onrender.com",
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
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        logger.info("Making request to OpenRouter API...")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"OpenRouter API response status: {response.status_code}")
        
        # Check if request was successful
        if response.status_code != 200:
            logger.error(f"OpenRouter API Error - Status Code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return jsonify({"reply": f"⚠️ API Error (Status {response.status_code}). Please try again later."}), 500
        
        data = response.json()
        logger.info("Successfully parsed API response")
        
        # Check if the response has the expected structure
        if "choices" not in data:
            logger.error("'choices' key not found in response")
            logger.error(f"Available keys: {list(data.keys())}")
            
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown API error")
                logger.error(f"API Error: {error_msg}")
                return jsonify({"reply": f"⚠️ API Error: {error_msg}"}), 500
            
            return jsonify({"reply": "⚠️ Unexpected API response format. Please try again."}), 500
        
        if not data["choices"] or len(data["choices"]) == 0:
            logger.error("No choices in API response")
            return jsonify({"reply": "⚠️ No response generated. Please try again."}), 500
        
        reply = data["choices"][0]["message"]["content"]
        logger.info("Successfully generated AI response")
        return jsonify({"reply": reply})
    
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return jsonify({"reply": "⚠️ Request timed out. Please try again."}), 500
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return jsonify({"reply": "⚠️ Network error. Please check your connection and try again."}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        return jsonify({"reply": "⚠️ Something went wrong. Please try again later."}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
