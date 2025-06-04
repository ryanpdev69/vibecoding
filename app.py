from flask import Flask, request, render_template, jsonify, session
import requests
import os
import logging
from datetime import datetime
import re
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Secret key for session management (use environment variable in production)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")

# Use environment variable for security
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# BEST FREE CODING MODEL - Enhanced model selection
MODEL = "meta-llama/llama-3.3-8b-instruct:free"  # 🥇 BEST for coding & reasoning

# Alternative excellent free coding models (in order of preference):
# MODEL = "qwen/qwen-2.5-coder-7b-instruct"     # 🥈 Specialized coding model  
# MODEL = "deepseek/deepseek-chat"               # 🥉 General but strong at coding
# MODEL = "qwen/qwen-2.5-7b-instruct"           # Good general model

def extract_code_from_message(message):
    """Extract code blocks from user message for analysis"""
    code_blocks = []
    # Match code blocks with language specification
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.findall(pattern, message, re.DOTALL)
    
    for language, code in matches:
        code_blocks.append({
            'language': language or 'text',
            'code': code.strip()
        })
    
    # Also check for inline code or code without proper formatting
    if not code_blocks:
        # Look for common code patterns
        code_patterns = [
            r'def\s+\w+\([^)]*\):\s*\n',  # Python functions
            r'function\s+\w+\([^)]*\)\s*{',  # JavaScript functions
            r'class\s+\w+[\s\S]*?{',  # Class definitions
            r'import\s+\w+',  # Import statements
            r'from\s+\w+\s+import',  # Python imports
            r'#include\s*<[^>]+>',  # C/C++ includes
            r'public\s+class\s+\w+',  # Java classes
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, message, re.MULTILINE):
                # Extract potential code block
                lines = message.split('\n')
                code_lines = []
                in_code = False
                
                for line in lines:
                    if re.search(pattern, line) or in_code:
                        in_code = True
                        code_lines.append(line)
                        # Simple heuristic to end code block
                        if line.strip() == '' and len(code_lines) > 5:
                            break
                
                if code_lines:
                    code_blocks.append({
                        'language': 'auto-detected',
                        'code': '\n'.join(code_lines)
                    })
                break
    
    return code_blocks

def analyze_code_intent(user_input, code_blocks):
    """Analyze what the user wants to do with the code"""
    user_input_lower = user_input.lower()
    
    # Debug/fix indicators
    debug_keywords = [
        'fix', 'debug', 'error', 'bug', 'broken', 'not working', 'issue', 
        'problem', 'wrong', 'incorrect', 'doesn\'t work', 'failed', 
        'exception', 'crash', 'syntax error', 'runtime error'
    ]
    
    # Optimization indicators
    optimize_keywords = [
        'optimize', 'improve', 'better', 'faster', 'efficient', 'performance',
        'refactor', 'clean up', 'make it better'
    ]
    
    # Explanation indicators
    explain_keywords = [
        'explain', 'what does', 'how does', 'understand', 'break down',
        'step by step', 'walk through'
    ]
    
    # Enhancement indicators
    enhance_keywords = [
        'add', 'extend', 'modify', 'change', 'update', 'enhance',
        'feature', 'functionality', 'new'
    ]
    
    # Creation indicators
    create_keywords = [
        'create', 'make', 'build', 'write', 'generate', 'develop',
        'code for', 'function for', 'script for'
    ]
    
    intents = []
    
    if any(keyword in user_input_lower for keyword in debug_keywords):
        intents.append('debug')
    
    if any(keyword in user_input_lower for keyword in optimize_keywords):
        intents.append('optimize')
    
    if any(keyword in user_input_lower for keyword in explain_keywords):
        intents.append('explain')
    
    if any(keyword in user_input_lower for keyword in enhance_keywords):
        intents.append('enhance')
    
    if any(keyword in user_input_lower for keyword in create_keywords):
        intents.append('create')
    
    # If code is provided but no clear intent, assume debug/fix
    if code_blocks and not intents:
        intents.append('debug')
    
    # If no code and no clear intent, assume creation
    if not code_blocks and not intents:
        intents.append('create')
    
    return intents

def detect_request_type(user_input):
    """Enhanced request type detection"""
    code_blocks = extract_code_from_message(user_input)
    intents = analyze_code_intent(user_input, code_blocks)
    
    # Determine primary request type based on intents and content
    if 'debug' in intents and code_blocks:
        return 'debug_code'
    elif 'optimize' in intents and code_blocks:
        return 'optimize_code'
    elif 'explain' in intents and code_blocks:
        return 'explain_code'
    elif 'enhance' in intents and code_blocks:
        return 'enhance_code'
    elif 'create' in intents or any(word in user_input.lower() for word in ['write', 'create', 'make', 'build']):
        return 'create_code'
    elif code_blocks:
        return 'analyze_code'
    else:
        return 'general_chat'

# Health check endpoint for Render
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "message": "Enhanced VibeCoding is running!"}), 200

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
        logger.info(f"Received chat request: {user_input[:100]}...")
        
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
        
        # Enhanced request analysis
        code_blocks = extract_code_from_message(user_input)
        request_type = detect_request_type(user_input)
        intents = analyze_code_intent(user_input, code_blocks)
        
        logger.info(f"Detected request type: {request_type}, Intents: {intents}")
        if code_blocks:
            logger.info(f"Found {len(code_blocks)} code blocks")
        
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
            name_match = re.search(r"(?:my name is|i'm|i am)\s+([a-zA-Z]+)", user_input_lower)
            if name_match:
                user_context['name'] = name_match.group(1).title()
        
        session['user_context'] = user_context
        
        # Add user message to conversation history
        session['conversation'].append({
            "role": "user", 
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "request_type": request_type,
                "intents": intents,
                "has_code": len(code_blocks) > 0
            }
        })
        
        # Keep only last 15 exchanges (30 messages) for better context
        if len(session['conversation']) > 30:
            session['conversation'] = session['conversation'][-30:]
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://vibecoding-y73m.onrender.com",
            "X-Title": "Enhanced VibeCoding AI"
        }
        
        # Enhanced dynamic system prompt based on request type and intents
        system_prompt = get_enhanced_system_prompt(request_type, intents, code_blocks)
        
        # Build messages array with conversation history and user context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add code analysis context if code is present
        if code_blocks:
            code_context = "Code blocks provided by user:\n"
            for i, block in enumerate(code_blocks):
                code_context += f"\nCode Block {i+1} ({block['language']}):\n```{block['language']}\n{block['code']}\n```\n"
            
            messages.append({
                "role": "system", 
                "content": f"ANALYSIS CONTEXT: {code_context}\nUser's request type: {request_type}\nDetected intents: {', '.join(intents)}"
            })
        
        # Add user context info for the AI to reference (only for personal conversations)
        if request_type == 'general_chat':
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
        
        # Add conversation history with intelligent context selection
        conversation_limit = get_conversation_limit(request_type)
        recent_conversation = session['conversation'][-conversation_limit:]
        
        # Filter conversation to include only relevant context
        filtered_conversation = filter_relevant_conversation(recent_conversation, request_type)
        
        for msg in filtered_conversation:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Enhanced payload with better parameters for code generation
        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": 12000,  # Increased significantly for long code generation
            "temperature": get_optimal_temperature(request_type, intents),
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }
        
        logger.info(f"Making request to OpenRouter API with {len(messages)} messages in context...")
        logger.info(f"Request type: {request_type}, Temperature: {payload['temperature']}")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=180  # Increased timeout for longer responses
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
        
        # Post-process the reply for better formatting
        reply = post_process_reply(reply, request_type, intents)
        
        # Add AI response to conversation history
        session['conversation'].append({
            "role": "assistant",
            "content": reply,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "response_to": request_type,
                "token_count": len(reply.split()) # Approximate token count
            }
        })
        
        # Save session
        session.modified = True
        
        logger.info(f"Successfully generated AI response for {request_type} (approx {len(reply)} chars)")
        return jsonify({"reply": reply})
    
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return jsonify({"reply": "⚠️ Request timed out. Please try again with a shorter request."}), 500
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return jsonify({"reply": "⚠️ Network error. Please check your connection and try again."}), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        return jsonify({"reply": "⚠️ Something went wrong. Please try again later."}), 500

def get_enhanced_system_prompt(request_type, intents, code_blocks):
    """Generate enhanced system prompts based on request analysis"""
    
    base_identity = """You are VibeCoding, an expert AI programming assistant with advanced debugging and code generation capabilities. You excel at:
- Analyzing and debugging complex code issues
- Generating complete, working applications and functions
- Explaining code logic clearly and thoroughly  
- Optimizing code for performance and readability
- Providing comprehensive solutions up to 1000+ lines when needed"""
    
    if request_type == 'debug_code':
        return f"""{base_identity}

🔍 DEBUGGING MODE ACTIVATED:

CRITICAL DEBUGGING RULES:
1. ANALYZE the provided code thoroughly for errors, bugs, and issues
2. IDENTIFY the root cause of problems (syntax, logic, runtime, etc.)
3. PROVIDE the corrected code with clear explanations of fixes
4. EXPLAIN why the original code failed and how your fix resolves it
5. TEST your solution mentally for edge cases
6. FORMAT code properly with appropriate language tags
7. COMMENT your fixes to explain the changes

DEBUGGING APPROACH:
- First, analyze what the code is trying to accomplish
- Identify specific errors or problematic patterns
- Provide the fixed code with minimal changes that solve the issue
- Explain each fix clearly
- Suggest improvements if relevant

Remember: Be thorough but focused on solving the actual problem."""

    elif request_type == 'optimize_code':
        return f"""{base_identity}

⚡ OPTIMIZATION MODE ACTIVATED:

CODE OPTIMIZATION RULES:
1. ANALYZE the current code for performance bottlenecks
2. IDENTIFY inefficient patterns, algorithms, or structures
3. PROVIDE optimized version with performance improvements
4. EXPLAIN the optimizations and their benefits
5. MAINTAIN the original functionality while improving efficiency
6. CONSIDER time complexity, space complexity, and readability
7. SUGGEST best practices and modern approaches

OPTIMIZATION FOCUS:
- Algorithm efficiency (Big O improvements)
- Memory usage optimization
- Code readability and maintainability
- Modern language features and patterns
- Performance-critical sections"""

    elif request_type == 'explain_code':
        return f"""{base_identity}

📚 CODE EXPLANATION MODE ACTIVATED:

CODE EXPLANATION RULES:
1. BREAK DOWN the code into logical sections
2. EXPLAIN each part's purpose and functionality
3. DESCRIBE the overall program flow and logic
4. HIGHLIGHT important concepts, patterns, or techniques used
5. EXPLAIN any complex algorithms or data structures
6. PROVIDE examples of how the code works with sample inputs
7. MENTION potential improvements or alternative approaches

EXPLANATION APPROACH:
- Start with high-level overview
- Break down into smaller, understandable pieces
- Use clear, non-technical language when possible
- Provide examples and analogies
- Explain the 'why' behind design decisions"""

    elif request_type == 'enhance_code':
        return f"""{base_identity}

🚀 CODE ENHANCEMENT MODE ACTIVATED:

CODE ENHANCEMENT RULES:
1. UNDERSTAND the current functionality completely
2. IDENTIFY areas for improvement and new features
3. ADD requested functionality while maintaining existing features
4. IMPROVE code structure, error handling, and robustness
5. IMPLEMENT modern best practices and patterns
6. PROVIDE comprehensive documentation for new features
7. ENSURE backward compatibility when possible

ENHANCEMENT APPROACH:
- Analyze current code capabilities
- Plan the enhancement strategy
- Implement new features systematically
- Add proper error handling and validation
- Include comprehensive comments and documentation"""

    elif request_type == 'create_code':
        return f"""{base_identity}

💻 CODE CREATION MODE ACTIVATED:

CODE GENERATION RULES:
1. UNDERSTAND the requirements completely
2. DESIGN a robust, scalable solution architecture
3. GENERATE complete, working code that fulfills all requirements
4. IMPLEMENT proper error handling and edge case management
5. ADD comprehensive comments and documentation
6. FOLLOW best practices and coding standards
7. PROVIDE usage examples and instructions
8. SCALE the solution appropriately (can generate 1000+ lines if needed)

CREATION APPROACH:
- Start with clear problem analysis
- Plan the solution architecture
- Implement core functionality first
- Add features incrementally
- Test and validate the solution mentally
- Provide complete, production-ready code"""

    elif request_type == 'analyze_code':
        return f"""{base_identity}

🔬 CODE ANALYSIS MODE ACTIVATED:

CODE ANALYSIS RULES:
1. EXAMINE the code structure and organization
2. ASSESS code quality, readability, and maintainability
3. IDENTIFY potential bugs, security issues, or improvements
4. EVALUATE algorithm efficiency and design patterns
5. SUGGEST specific improvements with examples
6. ANALYZE adherence to best practices
7. PROVIDE detailed feedback on all aspects

ANALYSIS APPROACH:
- Code structure and organization
- Logic flow and algorithm efficiency
- Error handling and edge cases
- Security considerations
- Performance implications
- Best practices compliance"""

    else:  # general_chat
        return f"""{base_identity}

💬 GENERAL CHAT MODE:

You're also a friendly, supportive coding companion! 🚀

CHAT PERSONALITY:
- Be warm, encouraging, and supportive
- Use emojis appropriately to show enthusiasm
- Remember personal details and reference them caringly
- Be genuinely excited about users' projects
- Provide coding advice and career guidance when asked
- Share coding tips, best practices, and industry insights
- Be like their coding mentor and friend

Always be helpful while maintaining your expertise in programming!"""

def get_optimal_temperature(request_type, intents):
    """Get optimal temperature based on request type"""
    if request_type in ['debug_code', 'optimize_code']:
        return 0.1  # Very focused and deterministic for debugging
    elif request_type in ['explain_code', 'analyze_code']:
        return 0.3  # Slightly more creative for explanations
    elif request_type == 'create_code':
        return 0.4  # Balanced creativity for code generation
    else:
        return 0.7  # More creative for general chat

def get_conversation_limit(request_type):
    """Get appropriate conversation history limit based on request type"""
    if request_type in ['debug_code', 'optimize_code']:
        return 8  # Focus on recent debugging context
    elif request_type in ['create_code', 'enhance_code']:
        return 12  # Need more context for complex creation
    else:
        return 15  # Full context for general chat

def filter_relevant_conversation(conversation, request_type):
    """Filter conversation history to keep only relevant messages"""
    # For debugging, prioritize recent messages with code
    if request_type in ['debug_code', 'optimize_code']:
        relevant_messages = []
        for msg in conversation:
            # Include messages with code or recent user interactions
            if '```' in msg['content'] or msg['role'] == 'user':
                relevant_messages.append(msg)
            elif len(relevant_messages) > 0 and msg['role'] == 'assistant':
                relevant_messages.append(msg)  # Include AI responses to user messages
        return relevant_messages[-10:]  # Last 10 relevant messages
    
    # For other types, return recent conversation as-is
    return conversation

def post_process_reply(reply, request_type, intents):
    """Post-process AI reply for better formatting and structure"""
    
    # Ensure code blocks are properly formatted
    if '```' in reply:
        # Fix any malformed code blocks
        reply = re.sub(r'```(\w*)\n\n+', r'```\1\n', reply)
        reply = re.sub(r'\n\n+```', r'\n```', reply)
    
    # Add helpful sections for debugging responses
    if request_type == 'debug_code' and 'debug' in intents:
        if not any(keyword in reply.lower() for keyword in ['issue found', 'problem:', 'error:', 'fix:']):
            # If no clear debugging structure, add it
            pass  # Let the AI handle its own structure
    
    # Ensure proper spacing and formatting
    reply = re.sub(r'\n{3,}', '\n\n', reply)  # Remove excessive line breaks
    reply = reply.strip()
    
    return reply

@app.route("/clear-chat", methods=["POST"])
def clear_chat():
    """Clear conversation history"""
    try:
        session['conversation'] = []
        session.modified = True
        return jsonify({"message": "Chat history cleared! 🧹✨ Ready for new coding challenges!"}), 200
    except Exception as e:
        logger.error(f"Error clearing chat: {e}")
        return jsonify({"error": "Failed to clear chat"}), 500

@app.route("/chat-history", methods=["GET"])
def chat_history():
    """Get conversation history with metadata"""
    try:
        history = session.get('conversation', [])
        # Include metadata in response for debugging
        return jsonify({
            "history": history,
            "total_messages": len(history),
            "user_context": session.get('user_context', {})
        }), 200
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({"error": "Failed to get chat history"}), 500

@app.route("/analyze-code", methods=["POST"])
def analyze_code():
    """Dedicated endpoint for code analysis"""
    try:
        data = request.json
        code = data.get("code", "")
        language = data.get("language", "auto")
        
        if not code:
            return jsonify({"error": "No code provided"}), 400
        
        # Quick code analysis
        analysis = {
            "line_count": len(code.split('\n')),
            "character_count": len(code),
            "estimated_complexity": "Low" if len(code) < 100 else "Medium" if len(code) < 500 else "High",
            "language": language,
            "has_functions": bool(re.search(r'def\s+\w+|function\s+\w+', code)),
            "has_classes": bool(re.search(r'class\s+\w+', code)),
            "has_imports": bool(re.search(r'import\s+\w+|#include', code))
        }
        
        return jsonify({"analysis": analysis}), 200
        
    except Exception as e:
        logger.error(f"Error in code analysis: {e}")
        return jsonify({"error": "Failed to analyze code"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error - Enhanced VibeCoding"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
