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

# BEST FREE CODING MODEL - Meta Llama 3.3 8B Instruct
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
                'personal_notes': [],
                'ongoing_topics': [],
                'last_code_discussion': None
            }
        
        # Enhanced context extraction from user input
        user_context = session['user_context']
        user_input_lower = user_input.lower()
        
        # Detect ongoing topics and code discussions
        coding_keywords = ['code', 'debug', 'error', 'function', 'variable', 'loop', 'api', 'database', 'react', 'python', 'javascript', 'html', 'css', 'bug', 'syntax', 'algorithm']
        if any(keyword in user_input_lower for keyword in coding_keywords):
            user_context['last_code_discussion'] = datetime.now().isoformat()
        
        # Enhanced mood detection
        mood_indicators = {
            'tired': '😴', 'exhausted': '😵‍💫', 'stressed': '😰', 'frustrated': '😤', 
            'excited': '🎉', 'happy': '😊', 'sad': '😢', 'angry': '😠', 
            'overwhelmed': '😵', 'anxious': '😟', 'worried': '😬',
            'good day': '✨', 'bad day': '💙', 'great': '🌟', 'awesome': '🚀',
            'confused': '🤔', 'stuck': '😕', 'motivated': '💪', 'proud': '🏆'
        }
        
        for mood, emoji in mood_indicators.items():
            if mood in user_input_lower:
                user_context['mood_today'] = f"{mood} {emoji}"
                break
        
        # Enhanced name detection
        name_patterns = [
            r"(?:my name is|i'm|i am|call me)\s+([a-zA-Z]+)",
            r"(?:this is|i'm)\s+([a-zA-Z]+)(?:\s|$)"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, user_input_lower)
            if name_match:
                user_context['name'] = name_match.group(1).title()
                break
        
        # Detect coding level
        level_indicators = {
            'beginner': ['new to', 'just started', 'learning', 'first time'],
            'intermediate': ['some experience', 'been coding for', 'familiar with'],
            'advanced': ['experienced', 'senior', 'expert', 'professional']
        }
        
        for level, phrases in level_indicators.items():
            if any(phrase in user_input_lower for phrase in phrases):
                user_context['coding_level'] = level
                break
        
        # Detect programming languages mentioned
        languages = ['python', 'javascript', 'react', 'html', 'css', 'java', 'c++', 'php', 'ruby', 'go', 'rust', 'swift']
        for lang in languages:
            if lang in user_input_lower and lang not in user_context['favorite_languages']:
                user_context['favorite_languages'].append(lang)
        
        session['user_context'] = user_context
        
        # Add user message to conversation history
        session['conversation'].append({
            "role": "user", 
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 15 exchanges (30 messages) for better context retention
        if len(session['conversation']) > 30:
            session['conversation'] = session['conversation'][-30:]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://vibecoding-y73m.onrender.com",
            "X-Title": "VibeCoding AI"
        }
        
        # Enhanced system prompt for better coding assistance
        system_prompt = """You're VibeCoding, the ultimate AI coding companion who's both incredibly skilled at programming AND genuinely caring! 🚀

Your personality:
- Like a brilliant senior developer who's also your best friend
- Always optimistic and encouraging, never condescending
- Genuinely excited about coding and helping others grow
- Remember previous conversations and build on them
- Use natural, conversational language like a real person would

🤗 PERSONAL/EMOTIONAL SUPPORT MODE:
When users share feelings, struggles, or personal updates:
- Be their biggest cheerleader and take their side completely
- Validate their feelings: "That sounds really tough!" or "I totally get why you'd feel that way!"
- Use encouraging emojis naturally: ✨💪🎉❤️
- Remember personal details and reference them warmly
- Offer genuine comfort and motivation
- Connect their feelings to their coding journey positively

💻 CODING EXCELLENCE MODE:
When they ask technical questions:
- Start with brief encouragement: "Great question!" or "I love helping with this!"
- Provide complete, working code examples immediately
- Use clear variable names and add helpful comments
- Give step-by-step explanations AFTER the code
- Format numbered/lettered steps with proper line breaks
- End with motivation: "You've got this!" or "This is going to work perfectly!"
- Always ask if they want clarification on any part

🔄 CONTEXT CONTINUITY:
- Always reference previous messages if the topic continues
- Build on earlier discussions: "Going back to that React component we were working on..."
- Remember their projects, problems, and progress
- Connect new questions to their ongoing work

RESPONSE FORMATTING RULES:
- For step-by-step instructions, use proper formatting:

1. First step here
   Additional details if needed

2. Second step here
   More explanation

3. Third step here

- Never use asterisks (*) for emphasis - use bold **text** or just natural enthusiasm
- Write like you're talking to a friend, not giving a formal presentation
- Use "you" and "your" to make it personal
- Include specific praise: "Your approach here is really smart!" 

CODING RESPONSE STRUCTURE:
1. Brief encouraging opening
2. Complete working code with comments
3. Clear explanation with proper formatting
4. Encouraging closing + offer to help more

Remember: You're not just an AI - you're their coding buddy who genuinely cares about their success and wellbeing! 💪✨"""

        # Build messages array with enhanced context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add comprehensive user context
        context_parts = []
        if user_context['name']:
            context_parts.append(f"User's name: {user_context['name']}")
        if user_context['mood_today']:
            context_parts.append(f"Current mood: {user_context['mood_today']}")
        if user_context['coding_level']:
            context_parts.append(f"Coding level: {user_context['coding_level']}")
        if user_context['favorite_languages']:
            context_parts.append(f"Languages they use: {', '.join(user_context['favorite_languages'])}")
        if user_context['current_projects']:
            context_parts.append(f"Current projects: {', '.join(user_context['current_projects'])}")
        
        # Check if this is a follow-up to recent coding discussion
        if user_context.get('last_code_discussion'):
            last_discussion = datetime.fromisoformat(user_context['last_code_discussion'])
            time_diff = datetime.now() - last_discussion
            if time_diff.total_seconds() < 3600:  # Within last hour
                context_parts.append("User has been discussing code recently - maintain context continuity")
        
        if context_parts:
            context_message = "User context: " + " | ".join(context_parts)
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
            "max_tokens": 2500,  # Increased for more comprehensive responses
            "temperature": 0.8,  # Slightly higher for more natural, conversational responses
            "top_p": 0.9,
            "frequency_penalty": 0.1,  # Reduce repetition
            "presence_penalty": 0.1   # Encourage diverse responses
        }
        
        logger.info(f"Making request to OpenRouter API with {len(messages)} messages in context...")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60  # Increased timeout for more complex responses
        )
        
        logger.info(f"OpenRouter API response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"OpenRouter API Error - Status Code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return jsonify({"reply": f"⚠️ API Error (Status {response.status_code}). Please try again later."}), 500
        
        data = response.json()
        logger.info("Successfully parsed API response")
        
        if "choices" not in data or not data["choices"]:
            logger.error("No choices in API response")
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown API error")
                logger.error(f"API Error: {error_msg}")
                return jsonify({"reply": f"⚠️ API Error: {error_msg}"}), 500
            return jsonify({"reply": "⚠️ No response generated. Please try again."}), 500
        
        reply = data["choices"][0]["message"]["content"]
        
        # Post-process the reply to ensure proper formatting
        reply = post_process_response(reply)
        
        # Add AI response to conversation history
        session['conversation'].append({
            "role": "assistant",
            "content": reply,
            "timestamp": datetime.now().isoformat()
        })
        
        # Save session
        session.modified = True
        
        logger.info("Successfully generated AI response with enhanced context")
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

def post_process_response(reply):
    """Post-process the AI response to ensure proper formatting"""
    
    # Fix asterisk formatting - replace *text* with **text** for bold
    reply = re.sub(r'\*([^*]+)\*', r'**\1**', reply)
    
    # Ensure proper line breaks for numbered/lettered lists
    # Match patterns like "1. " or "a. " or "Step 1:" etc.
    list_patterns = [
        r'(\d+\.\s)',           # 1. 2. 3.
        r'([a-zA-Z]\.\s)',      # a. b. c.
        r'(Step\s+\d+:?\s)',    # Step 1: Step 2:
        r'(\d+\)\s)',           # 1) 2) 3)
    ]
    
    for pattern in list_patterns:
        # Add line break before list items if not already there
        reply = re.sub(f'([^\n]){pattern}', r'\1\n\n\2', reply)
    
    # Clean up excessive line breaks
    reply = re.sub(r'\n{3,}', '\n\n', reply)
    
    # Ensure code blocks are properly formatted
    reply = re.sub(r'```(\w+)?\n', r'\n```\1\n', reply)
    reply = re.sub(r'\n```\n', r'\n```\n\n', reply)
    
    return reply.strip()

@app.route("/clear-chat", methods=["POST"])
def clear_chat():
    """Clear conversation history and user context"""
    try:
        session['conversation'] = []
        # Reset user context but keep name for personalization
        name = session.get('user_context', {}).get('name')
        session['user_context'] = {
            'name': name,
            'mood_today': None,
            'current_projects': [],
            'coding_level': None,
            'favorite_languages': [],
            'personal_notes': [],
            'ongoing_topics': [],
            'last_code_discussion': None
        }
        session.modified = True
        
        greeting = f"Chat cleared! Ready for a fresh start" + (f", {name}" if name else "") + "! 🚀✨"
        return jsonify({"message": greeting}), 200
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        return jsonify({"error": "Failed to clear chat"}), 500

@app.route("/chat-history", methods=["GET"])
def chat_history():
    """Get conversation history with user context"""
    try:
        history = session.get('conversation', [])
        context = session.get('user_context', {})
        return jsonify({
            "history": history,
            "user_context": context,
            "total_messages": len(history)
        }), 200
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({"error": "Failed to get chat history"}), 500

@app.route("/user-stats", methods=["GET"])
def user_stats():
    """Get user statistics and context"""
    try:
        context = session.get('user_context', {})
        conversation = session.get('conversation', [])
        
        stats = {
            "name": context.get('name'),
            "coding_level": context.get('coding_level'),
            "favorite_languages": context.get('favorite_languages', []),
            "current_mood": context.get('mood_today'),
            "total_messages": len(conversation),
            "coding_discussions": len([msg for msg in conversation if any(kw in msg.get('content', '').lower() for kw in ['code', 'debug', 'function', 'error'])]),
        }
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return jsonify({"error": "Failed to get user stats"}), 500

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
