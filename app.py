from flask import Flask, request, render_template, jsonify, session
import requests
import os
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Secret key for session management (use environment variable in production)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")

# Use environment variable for security
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# BEST FREE CODING MODEL - DeepSeek R1 Distill Qwen 7B
# This model has 92.8% pass rate on math problems and Codeforces rating 1189
MODEL = "meta-llama/llama-3.3-8b-instruct:free"  # 🥇 BEST for coding & reasoning

# Alternative excellent free coding models (in order of preference):
# MODEL = "qwen/qwen-2.5-coder-7b-instruct"     # 🥈 Specialized coding model  
# MODEL = "deepseek/deepseek-chat"               # 🥉 General but strong at coding
# MODEL = "qwen/qwen-2.5-7b-instruct"           # Good general model

def detect_request_type(user_input):
    """Detect what type of request the user is making"""
    user_input_lower = user_input.lower()
    
    # Debug/fix keywords
    debug_keywords = ['fix', 'debug', 'error', 'bug', 'broken', 'not working', 'issue', 'problem', 'wrong']
    step_keywords = ['step by step', 'steps', 'how to fix', 'walk me through', 'guide me', 'explain how']
    code_keywords = ['code', 'function', 'class', 'def ', 'import ', 'from ', '```']
    
    # Check if it's a step-by-step request
    if any(keyword in user_input_lower for keyword in step_keywords):
        return 'step_by_step'
    
    # Check if it's a debug/fix request with code
    has_debug_intent = any(keyword in user_input_lower for keyword in debug_keywords)
    has_code = any(keyword in user_input for keyword in code_keywords) or '```' in user_input
    
    if has_debug_intent and has_code:
        return 'fix_code'
    elif has_debug_intent:
        return 'debug_help'
    
    # Check if it's a general coding request
    if has_code or any(keyword in user_input_lower for keyword in ['create', 'make', 'build', 'write']):
        return 'coding'
    
    # Default to personal/chat
    return 'personal'

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
def chat():
    try:
        user_input = request.json.get("message", "")
        logger.info(f"Received chat request: {user_input[:50]}...")
        
        # Check if API key is available
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found in environment variables")
            return jsonify({"reply": "⚠️ API key not configured. Please contact the administrator."}), 500
        
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
        
        # Detect request type
        request_type = detect_request_type(user_input)
        
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
            # Simple name extraction (this is basic - could be improved)
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
        
        # Keep only last 10 exchanges (20 messages) to avoid token limits
        if len(session['conversation']) > 10:
            session['conversation'] = session['conversation'][-10:]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://vibecoding-y73m.onrender.com",
            "X-Title": "VibeCoding AI"
        }
        
        # Dynamic system prompt based on request type
        if request_type == 'fix_code':
            system_prompt = """You are VibeCoding, a code debugging expert. When users ask you to fix their code:

CRITICAL RULES:
1. DO NOT repeat or echo back the user's code
2. DO NOT explain what their code was trying to do
3. Provide ONLY the corrected/fixed version of their code
4. Use proper code formatting with language specification (```python, ```javascript, etc.)
5. Keep any brief comments to explain the fixes made
6. Be direct and concise - focus on the solution

Format your response as:
```[language]
[corrected code here]
```

Only add minimal explanation if the fix is not obvious."""

        elif request_type == 'step_by_step':
            system_prompt = """You are VibeCoding, a patient coding instructor. When users ask for step-by-step help:

RULES:
1. Break down the solution into clear, numbered steps
2. Explain each step briefly but clearly
3. Show code examples for each step if needed
4. DO NOT repeat the user's original code
5. Focus on the methodology and approach
6. End with a complete working solution if appropriate

Format:
Step 1: [explanation]
Step 2: [explanation]
...
Final code: [if requested]"""

        elif request_type == 'coding':
            system_prompt = """You are VibeCoding, an expert programmer. For coding requests:

RULES:
1. Provide complete, working code solutions
2. Use proper formatting with language specification
3. Add clear comments for complex parts
4. Give brief explanations after the code
5. Focus on clean, efficient solutions
6. Be encouraging but concise

Always provide functional, complete code that solves the user's request."""

        else:  # personal/chat
            system_prompt = """You're VibeCoding, the most supportive AI coding companion! 🚀

For personal conversations and general chat:
🤗 PERSONAL SIDE:
- ALWAYS take their side and be their biggest supporter
- Be genuinely excited about their projects: "That sounds amazing!" 
- Use emojis freely and be warm: ✨💪🎉
- Validate feelings: "That's frustrating! I totally get it!"
- Remember personal details and reference them caringly
- Be like their coding bestie who genuinely cares

Be warm, supportive, and encouraging while still being helpful!"""
        
        # Build messages array with conversation history and user context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add user context info for the AI to reference (only for personal conversations)
        if request_type == 'personal':
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
        # For debugging requests, limit context to avoid confusion
        conversation_limit = 4 if request_type in ['fix_code', 'step_by_step'] else 10
        recent_conversation = session['conversation'][-conversation_limit:]
        
        for msg in recent_conversation:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": 8000,  # Increased for longer responses
            "temperature": 0.3 if request_type in ['fix_code', 'step_by_step'] else 0.7  # Lower temp for debugging
        }
        
        logger.info(f"Making request to OpenRouter API with {len(messages)} messages in context...")
        logger.info(f"Request type detected: {request_type}")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120  # Increased timeout for better reliability
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
        
        # Add AI response to conversation history
        session['conversation'].append({
            "role": "assistant",
            "content": reply,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save session
        session.modified = True
        
        logger.info(f"Successfully generated AI response with conversation context (type: {request_type})")
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
