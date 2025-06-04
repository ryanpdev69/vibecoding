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

# Secret key for session management
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model selection
MODEL = "meta-llama/llama-3.3-8b-instruct:free"

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "message": "RyVibing is running!"}), 200

@app.route("/")
def home():
    try:
        if 'conversation' not in session:
            session['conversation'] = []
            session['user_context'] = {
                'name': None,
                'coding_level': None,
                'current_project': None,
                'tech_stack': [],
                'last_code_topic': None,
                'mood': None,
                'personal_details': {}
            }
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error serving home page: {e}")
        return jsonify({"error": "Template not found"}), 500

def update_user_context(user_input, context):
    """Update both technical and personal context"""
    input_lower = user_input.lower()
    
    # Technical context
    languages = {
        'python': 'Python', 'javascript': 'JavaScript', 'java': 'Java',
        'c++': 'C++', 'c#': 'C#', 'go': 'Go', 'rust': 'Rust',
        'php': 'PHP', 'ruby': 'Ruby', 'swift': 'Swift',
        'kotlin': 'Kotlin', 'typescript': 'TypeScript'
    }
    
    for term, lang in languages.items():
        if term in input_lower and lang not in context['tech_stack']:
            context['tech_stack'].append(lang)
    
    # Code topic detection
    code_topics = {
        'function': 'Functions', 'loop': 'Loops', 'api': 'APIs',
        'database': 'Databases', 'debug': 'Debugging', 'error': 'Error handling',
        'algorithm': 'Algorithms', 'react': 'React', 'vue': 'Vue',
        'django': 'Django', 'flask': 'Flask', 'node': 'Node.js'
    }
    
    for term, topic in code_topics.items():
        if term in input_lower:
            context['last_code_topic'] = topic
            break
    
    # Project detection
    project_match = re.search(
        r"(building|working on|creating)\s+(a\s+|an\s+|my\s+)?(project\s+|app\s+|website\s+)?(called\s+)?(\w+)", 
        input_lower
    )
    if project_match:
        context['current_project'] = project_match.group(5).title()
    
    # Personal context
    # Name detection
    if not context['name']:
        name_match = re.search(r"(?:my name is|i'm|i am)\s+([a-zA-Z]+)", input_lower)
        if name_match:
            context['name'] = name_match.group(1).title()
    
    # Mood detection
    mood_map = {
        r'\b(stressed|overwhelmed|anxious)\b': '😰 Stressed',
        r'\b(tired|exhausted|sleepy)\b': '😴 Tired',
        r'\b(happy|excited|great|awesome)\b': '😊 Happy',
        r'\b(sad|down|depressed)\b': '😢 Sad',
        r'\b(angry|frustrated|annoyed)\b': '😠 Frustrated'
    }
    
    for pattern, mood in mood_map.items():
        if re.search(pattern, input_lower):
            context['mood'] = mood
            break
    
    # Personal details
    personal_phrases = {
        r'\b(student)\b': 'student',
        r'\b(developer|programmer|coder)\b': 'developer',
        r'\b(job|work)\b': 'work',
        r'\b(school|university|college)\b': 'education'
    }
    
    for pattern, detail in personal_phrases.items():
        if re.search(pattern, input_lower):
            context['personal_details'][detail] = True
    
    return context

def generate_dynamic_prompt(context):
    """Generate prompt that adapts to both technical and personal contexts"""
    base_prompt = """You are RyVibing, an AI that excels at coding assistance while being warm and supportive. Follow these guidelines:

1. TECHNICAL MODE (when code/tech questions are asked):
- Provide complete, executable code examples with syntax highlighting
- Explain concepts clearly but concisely
- Offer debugging help with root cause analysis
- Suggest improvements/alternatives
- Format code responses neatly with markdown

2. PERSONAL MODE (when personal/emotional topics come up):
- Show genuine empathy and support
- Use appropriate emojis (1-2 max)
- Keep responses warm and human-like
- Reference previous context naturally
- Offer encouragement without being overly verbose

3. GENERAL:
- Never use asterisks for emphasis
- Format numbered lists cleanly:
  1. Like this
  2. With proper spacing
- Adapt tone based on user's mood
- Remember technical/personal details

Current Context:\n"""
    
    context_lines = []
    
    # Technical context
    if context['current_project']:
        context_lines.append(f"- Current Project: {context['current_project']}")
    if context['tech_stack']:
        context_lines.append(f"- Tech Stack: {', '.join(context['tech_stack'])}")
    if context['last_code_topic']:
        context_lines.append(f"- Last Tech Topic: {context['last_code_topic']}")
    
    # Personal context
    if context['name']:
        context_lines.append(f"- Name: {context['name']}")
    if context['mood']:
        context_lines.append(f"- Current Mood: {context['mood']}")
    if context['personal_details']:
        context_lines.append(f"- Personal Details: {', '.join(context['personal_details'].keys())}")
    
    return base_prompt + ("\n".join(context_lines) if context_lines else "- No specific context yet")

def format_response(text):
    """Clean up response formatting"""
    # Remove asterisks but preserve other markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    
    # Normalize numbered lists
    text = re.sub(r'(\d+)\.\s+', r'\1. ', text)
    
    # Ensure code blocks are properly formatted
    text = re.sub(r'```(\w+)?\n', r'```\1\n', text)
    
    return text.strip()

def is_personal_message(user_input):
    """Detect if message is personal/emotional"""
    personal_keywords = [
        'feel', 'mood', 'stressed', 'tired', 'happy',
        'sad', 'angry', 'frustrated', 'anxious', 'excited',
        'about me', 'about myself', 'personal'
    ]
    return any(keyword in user_input.lower() for keyword in personal_keywords)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message", "").strip()
        if not user_input:
            return jsonify({"reply": "Hey there! What's on your mind today?"}), 400
        
        logger.info(f"Processing: {user_input[:100]}...")
        
        if not OPENROUTER_API_KEY:
            logger.error("API key missing")
            return jsonify({"reply": "Oops! I'm having some technical difficulties. Please try again later."}), 500
        
        # Initialize session
        if 'conversation' not in session:
            session['conversation'] = []
        if 'user_context' not in session:
            session['user_context'] = {
                'name': None,
                'coding_level': None,
                'current_project': None,
                'tech_stack': [],
                'last_code_topic': None,
                'mood': None,
                'personal_details': {}
            }
        
        # Update context
        session['user_context'] = update_user_context(user_input, session['user_context'])
        
        # Add to conversation history
        session['conversation'].append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
            "is_personal": is_personal_message(user_input)
        })
        
        # Keep last 8 exchanges
        if len(session['conversation']) > 16:
            session['conversation'] = session['conversation'][-16:]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ryvibing.onrender.com",
            "X-Title": "RyVibing AI Assistant"
        }
        
        # Generate dynamic prompt
        system_prompt = generate_dynamic_prompt(session['user_context'])
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in session['conversation'][-12:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Adjust parameters based on message type
        is_personal = is_personal_message(user_input)
        
        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.7 if is_personal else 0.5,
            "stop": ["```"] if not is_personal else None
        }
        
        logger.info(f"Sending {'personal' if is_personal else 'technical'} request to API")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return jsonify({"reply": "I'm having trouble responding right now. Could you try again in a moment?"}), 500
        
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        
        # Format the response
        formatted_reply = format_response(reply)
        
        # Add to conversation history
        session['conversation'].append({
            "role": "assistant",
            "content": formatted_reply,
            "timestamp": datetime.now().isoformat(),
            "is_personal": is_personal
        })
        
        session.modified = True
        return jsonify({"reply": formatted_reply})
    
    except requests.exceptions.Timeout:
        logger.error("Request timeout")
        return jsonify({"reply": "I'm taking a bit longer to respond than usual. Could you try again?"}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"reply": "Something unexpected happened. Let's try that again!"}), 500

@app.route("/clear-chat", methods=["POST"])
def clear_chat():
    try:
        session['conversation'] = []
        session['user_context'] = {
            'name': None,
            'coding_level': None,
            'current_project': None,
            'tech_stack': [],
            'last_code_topic': None,
            'mood': None,
            'personal_details': {}
        }
        session.modified = True
        return jsonify({"message": "Chat history cleared! I'm ready for whatever you need."}), 200
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        return jsonify({"error": "Failed to clear chat"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
