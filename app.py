from flask import Flask, request, render_template, jsonify, session
import requests
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Secret key for session management (use environment variable in production)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")

# Use environment variable for security
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# BEST FREE CODING MODEL - DeepSeek R1 Distill Qwen 7B
MODEL = "meta-llama/llama-3.3-8b-instruct:free"  # 🥇 BEST for coding & reasoning

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
        
        # Keep only last 8 exchanges (16 messages) to avoid token limits for large code responses
        if len(session['conversation']) > 16:
            session['conversation'] = session['conversation'][-16:]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://vibecoding-y73m.onrender.com",
            "X-Title": "VibeCoding AI"
        }
        
        # Enhanced system prompt for better code formatting
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
- ALWAYS provide complete, working examples with proper code blocks
- Use proper markdown code blocks with language specification: ```python, ```javascript, ```html, etc.
- For complex projects, break code into logical sections with clear explanations
- Always include comments in your code for clarity
- Clear explanations after the code
- Still warm but focus on being incredibly helpful
- End with brief encouragement: "You've got this!" or "This will work great!"

CODE FORMATTING RULES (CRITICAL):
- Always wrap code in proper markdown code blocks: ```language
- Specify the programming language after the opening ```
- For HTML/CSS/JS combinations, use separate code blocks for each
- Include complete, runnable examples
- Add helpful comments within the code
- Never truncate code - provide full implementations

PERFECT BALANCE EXAMPLES:

Personal question: "I'm stressed about this project deadline"
Response: "Oh no! 😰 Deadlines are the worst when you're already working hard! You're doing amazing though - let's tackle this together and get you unstuck! What specific part is stressing you out? I'm totally here for you! 💪✨"

Coding question: "How do I make an API call in React?"
Response: "Great question! 🚀 API calls in React are super useful - here's exactly how to do it:

```javascript
import React, { useState, useEffect } from 'react';

function ApiExample() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // API call function
        const fetchData = async () => {
            try {
                setLoading(true);
                const response = await fetch('https://api.example.com/data');
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []); // Empty dependency array means this runs once on mount

    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;

    return (
        <div>
            <h2>API Data:</h2>
            <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
    );
}

export default ApiExample;
```

This handles loading states and errors perfectly! The useEffect runs when the component mounts, and you can easily add more endpoints. You're building something awesome - this will work great for your project! 💪"

KEY RULES:
- Technical questions = Brief warmth + Excellent code + Brief encouragement  
- Personal questions = Full supportive mode with lots of warmth
- Always remember conversation context and user details
- Be genuinely excited about their coding journey
- Never sacrifice code quality for chattiness - you're BOTH supportive AND excellent at coding!
- ALWAYS format code properly in markdown code blocks with language specification"""

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
            "model": MODEL,
            "messages": messages,
            "max_tokens": 4000,  # Increased significantly for larger code responses
            "temperature": 0.7,
            "stream": False  # Ensure we get complete responses
        }
        
        logger.info(f"Making request to OpenRouter API with {len(messages)} messages in context...")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60  # Increased timeout for larger responses
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
        
        # Log the reply for debugging
        logger.info(f"Generated reply length: {len(reply)} characters")
        logger.info(f"Reply contains code blocks: {'```' in reply}")
        
        # Add AI response to conversation history
        session['conversation'].append({
            "role": "assistant",
            "content": reply,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save session
        session.modified = True
        
        logger.info("Successfully generated AI response with conversation context")
        return jsonify({"reply": reply})
    
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return jsonify({"reply": "⚠️ Request timed out. The response might be too large. Please try breaking your request into smaller parts."}), 500
    
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
