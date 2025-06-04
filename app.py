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
    
    # Check if API key is available
    if not OPENROUTER_API_KEY:
        return jsonify({"reply": "⚠️ API key not configured. Please set OPENROUTER_API_KEY environment variable."}), 500
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vibecoding-y73m.onrender.com",  # Updated with your actual URL
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
        "max_tokens": 1000,  # Add token limit
        "temperature": 0.7   # Add temperature for consistency
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30  # Increased timeout for better reliability
        )
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"OpenRouter API Error - Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return jsonify({"reply": f"⚠️ API Error (Status {response.status_code}). Please try again later."}), 500
        
        data = response.json()
        
        # Debug: Print the full response to understand the structure
        print("Full API Response:", data)
        
        # Check if the response has the expected structure
        if "choices" not in data:
            print("Error: 'choices' key not found in response")
            print("Available keys:", list(data.keys()))
            
            # Check if there's an error message in the response
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown API error")
                return jsonify({"reply": f"⚠️ API Error: {error_msg}"}), 500
            
            return jsonify({"reply": "⚠️ Unexpected API response format. Please try again."}), 500
        
        if not data["choices"] or len(data["choices"]) == 0:
            return jsonify({"reply": "⚠️ No response generated. Please try again."}), 500
        
        reply = data["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    
    except requests.exceptions.Timeout:
        print("Request timed out")
        return jsonify({"reply": "⚠️ Request timed out. Please try again."}), 500
    
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return jsonify({"reply": "⚠️ Network error. Please check your connection and try again."}), 500
    
    except KeyError as e:
        print(f"KeyError: {e}")
        print("Response data:", data if 'data' in locals() else "No data")
        return jsonify({"reply": "⚠️ Unexpected response format from AI service."}), 500
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Full response:", response.text if 'response' in locals() else "No response")
        return jsonify({"reply": "⚠️ Something went wrong with the AI response. Please try again later."}), 500

if __name__ == "__main__":
    app.run(debug=True)
