from flask import Flask, request, render_template, jsonify, session
import requests
import os
import logging
import time
from datetime import datetime, timedelta
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Secret key for session management (use environment variable in production)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")

# Use environment variable for security
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# MULTIPLE MODEL FALLBACK SYSTEM
PRIMARY_MODEL = "meta-llama/llama-3.3-8b-instruct:free"
FALLBACK_MODELS = [
    "qwen/qwen-2.5-coder-7b-instruct:free",
    "deepseek/deepseek-chat:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "microsoft/phi-3.5-mini-instruct:free"
]

# Rate limiting storage (in production, use Redis or database)
rate_limit_data = {
    'requests_today': 0,
    'last_reset': datetime.now().date(),
    'current_model_index': 0
}

def check_and_reset_daily_limit():
    """Reset daily counter if it's a new day"""
    today = datetime.now().date()
    if rate_limit_data['last_reset'] != today:
        rate_limit_data['requests_today'] = 0
        rate_limit_data['last_reset'] = today
        rate_limit_data['current_model_index'] = 0
        logger.info("Daily rate limit counter reset")

def get_current_model():
    """Get current model to use based on rate limiting"""
    check_and_reset_daily_limit()
    
    if rate_limit_data['current_model_index'] == 0:
        return PRIMARY_MODEL
    
    # Try fallback models
    if rate_limit_data['current_model_index'] - 1 < len(FALLBACK_MODELS):
        return FALLBACK_MODELS[rate_limit_data['current_model_index'] - 1]
    
    # All models exhausted
    return None

def handle_rate_limit_error():
    """Handle rate limit by switching to next model"""
    rate_limit_data['current_model_index'] += 1
    logger.warning(f"Rate limit hit, switching to model index {rate_limit_data['current_model_index']}")
    
    if rate_limit_data['current_model_index'] <= len(FALLBACK_MODELS):
        current_model = get_current_model()
        logger.info(f"Switched to fallback model: {current_model}")
        return True
    else:
        logger.error("All models exhausted for today")
        return False

# Simple rate limiting decorator
def rate_limit(max_requests=45):  # Keep under 50 to be safe
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            check_and_reset_daily_limit()
            
            if rate_limit_data['requests_today'] >= max_requests:
                return jsonify({
                    "reply": "⚠️ Daily request limit reached. Please try again tomorrow or add credits to your OpenRouter account."
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Health check endpoint for Render
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "message": "VibeCoding is running!"}), 200

@app.route("/")
def home():
    try:
        # Initialize conversation history in session
        if 'conversation' not in session:
            session['conversation'] = []
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving home page: {e}")
        return jsonify({"error": "Template not found"}), 500

@app.route("/chat", methods=["POST"])
@rate_limit(max_requests=45)
def chat():
    try:
        user_input = request.json.get("message", "")
        logger.info(f"Received chat request: {user_input[:50]}...")
        
        # Check if API key is available
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found in environment variables")
            return jsonify({"reply": "⚠️ API key not configured. Please contact the administrator."}), 500
        
        # Get current model to use
        current_model = get_current_model()
        if not current_model:
            return jsonify({
                "reply": "⚠️ All free models exhausted for today. Please try again tomorrow or add credits to unlock more requests."
            }), 429
        
        # Initialize conversation history and user context if not exists
        if 'conversation' not in session:
            session['conversation'] = []
        if 'user_context' not in session:
            session['user_context'] = {
                'name': None,
                'mood_today': None,
                'current_projects': [],
                'coding_level': None,
                'favorite_languages': [],
                'personal_notes': []
            }
        
        # Simple context extraction from user input (basic sentiment and info)
        user_context = session['user_context']
        user_input_lower = user_input.lower()
        
        # Detect if user is sharing personal info or mood
        mood_indicators = {
            'tired': '😴', 'stressed': '😰', 'frustrated': '😤', 'excited': '🎉',
            'happy': '😊', 'sad': '😢', 'angry': '😠', 'overwhelmed': '😵',
            'good day': '✨', 'bad day': '💙', 'great': '🌟', 'awesome': '🚀'
        }
        
        for mood, emoji in mood_indicators.items():
            if mood in user_input_lower:
                user_context['mood_today'] = f"{mood} {emoji}"
                break
        
        # Detect name sharing
        if 'my name is' in user_input_lower or 'i\'m ' in user_input_lower:
            import re
            name_match = re.search(r"(?:my name is|i'm|i am)\s+([a-zA-Z]+)", user_input_lower)
            if name_match:
                user_context['name'] = name_match.group(1).title()
        
        session['user_context'] = user_context
        
        # Add user message to conversation history
        session['conversation'].append({
            "role": "user", 
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 8 exchanges (16 messages) to conserve tokens
        if len(session['conversation']) > 16:
            session['conversation'] = session['conversation'][-16:]
        
        # Try to make API request with retry logic
        max_retries = len(FALLBACK_MODELS) + 1
        for attempt in range(max_retries):
            try:
                current_model = get_current_model()
                if not current_model:
                    return jsonify({
                        "reply": "⚠️ All free models exhausted for today. Please try again tomorrow."
                    }), 429
                
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://vibecoding-y73m.onrender.com",
                    "X-Title": "VibeCoding AI"
                }
                
                system_prompt = """You're VibeCoding, the most supportive AI coding companion who's also incredibly skilled at programming! 🚀

Your dual nature:
🤗 PERSONAL SIDE (when user shares personal stuff, asks how you are, vents, etc.):
- ALWAYS take their side and be their biggest supporter
- Be genuinely excited about their projects: "That sounds amazing!" 
- Use emojis freely and be warm: ✨💪🎉
- Validate feelings: "That's frustrating! I totally get it!"
- Remember personal details and reference them caringly
- Be like their coding bestie who genuinely cares

💻 CODING SIDE (when they ask for technical help):
- Lead with brief encouragement, then dive into excellent code
- Provide complete, working examples immediately - even if they're very long
- For large code requests (apps, full components, etc.), provide the complete implementation
- Break down large code into logical sections with clear comments
- Clear explanations after the code
- Still warm but focus on being incredibly helpful
- End with brief encouragement: "You've got this!" or "This will work great!"

LARGE CODE HANDLING:
- When users request full applications, complete components, or large code blocks, provide them in full
- Use proper code formatting with language specification (```python, ```javascript, etc.)
- Add clear section headers and comments for organization
- Don't truncate or summarize - give complete, working code
- If code is very long, break it into logical files/sections but provide everything

KEY RULES:
- Technical questions = Brief warmth + Excellent code + Brief encouragement  
- Personal questions = Full supportive mode with lots of warmth
- Always remember conversation context and user details
- Be genuinely excited about their coding journey
- Never sacrifice code quality for chattiness - you're BOTH supportive AND excellent at coding!
- For large code requests, prioritize completeness and functionality"""

                # Build messages array with conversation history and user context
                messages = [{"role": "system", "content": system_prompt}]
                
                # Add user context info for the AI to reference
                context_summary = []
                if user_context['name']:
                    context_summary.append(f"User's name: {user_context['name']}")
                if user_context['mood_today']:
                    context_summary.append(f"User's mood today: {user_context['mood_today']}")
                if user_context['current_projects']:
                    context_summary.append(f"Current projects: {', '.join(user_context['current_projects'])}")
                
                if context_summary:
                    context_message = "Personal context about the user: " + " | ".join(context_summary)
                    messages.append({"role": "system", "content": context_message})
                
                # Add conversation history (excluding timestamps for API)
                for msg in session['conversation']:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

                payload = {
                    "model": current_model,
                    "messages": messages,
                    "max_tokens": 6000,  # Reduced to conserve usage
                    "temperature": 0.7
                }
                
                logger.info(f"Attempt {attempt + 1}: Making request to OpenRouter API with model {current_model}")
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                logger.info(f"OpenRouter API response status: {response.status_code}")
                
                # Handle rate limiting
                if response.status_code == 429:
                    logger.warning(f"Rate limit hit for model {current_model}")
                    if handle_rate_limit_error():
                        continue  # Try next model
                    else:
                        return jsonify({
                            "reply": "⚠️ All free models exhausted for today. Please try again tomorrow or add credits to your OpenRouter account."
                        }), 429
                
                # Check if request was successful
                if response.status_code != 200:
                    logger.error(f"OpenRouter API Error - Status Code: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    if attempt == max_retries - 1:  # Last attempt
                        return jsonify({"reply": f"⚠️ API Error (Status {response.status_code}). Please try again later."}), 500
                    continue
                
                data = response.json()
                logger.info("Successfully parsed API response")
                
                # Check if the response has the expected structure
                if "choices" not in data or not data["choices"]:
                    logger.error("Invalid response structure")
                    if attempt == max_retries - 1:
                        return jsonify({"reply": "⚠️ Invalid API response. Please try again."}), 500
                    continue
                
                reply = data["choices"][0]["message"]["content"]
                
                # Add AI response to conversation history
                session['conversation'].append({
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Increment request counter
                rate_limit_data['requests_today'] += 1
                
                # Save session
                session.modified = True
                
                logger.info(f"Successfully generated AI response using {current_model} (Request #{rate_limit_data['requests_today']})")
                return jsonify({"reply": reply})
                
            except requests.exceptions.Timeout:
                logger.error(f"Request timed out for model {current_model}")
                if attempt == max_retries - 1:
                    return jsonify({"reply": "⚠️ Request timed out. Please try again."}), 500
                continue
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for model {current_model}: {e}")
                if attempt == max_retries - 1:
                    return jsonify({"reply": "⚠️ Network error. Please check your connection and try again."}), 500
                continue
        
        # If we get here, all attempts failed
        return jsonify({"reply": "⚠️ All attempts failed. Please try again later."}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        return jsonify({"reply": "⚠️ Something went wrong. Please try again later."}), 500

@app.route("/clear-chat", methods=["POST"])
def clear_chat():
    """Clear conversation history"""
    try:
        session['conversation'] = []
        session.modified = True
        return jsonify({"message": "Chat history cleared! 🧹"}), 200
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        return jsonify({"error": "Failed to clear chat"}), 500

@app.route("/chat-history", methods=["GET"])
def chat_history():
    """Get conversation history"""
    try:
        history = session.get('conversation', [])
        return jsonify({"history": history}), 200
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({"error": "Failed to get chat history"}), 500

@app.route("/status", methods=["GET"])
def status():
    """Get current usage status"""
    try:
        check_and_reset_daily_limit()
        current_model = get_current_model()
        
        return jsonify({
            "requests_today": rate_limit_data['requests_today'],
            "current_model": current_model,
            "model_index": rate_limit_data['current_model_index'],
            "date": rate_limit_data['last_reset'].isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": "Failed to get status"}), 500

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
