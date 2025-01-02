from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from . import db
from .models import User, Activity, Quest, Achievement, Challenge
import os
import json
from datetime import datetime, timedelta
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import openai

main = Blueprint('main', __name__)

class ChallengeMode:
    def __init__(self, user_id):
        self.user_id = user_id
        self.activities = []
        self.current_activity_index = 0
        self.progress = 0

    def generate_activities(self):
        # Generate a list of related activities
        self.activities = [
            {'id': 1, 'name': 'Activity 1', 'duration': 30},
            {'id': 2, 'name': 'Activity 2', 'duration': 30},
            {'id': 3, 'name': 'Activity 3', 'duration': 30},
        ]

    def start_challenge(self):
        self.generate_activities()
        self.current_activity_index = 0
        self.progress = 0
        return self.activities

    def complete_activity(self):
        if self.current_activity_index < len(self.activities):
            self.progress += 1
            self.current_activity_index += 1
            return True
        return False

    def is_challenge_complete(self):
        return self.current_activity_index >= len(self.activities)

    def get_progress(self):
        return self.progress / len(self.activities) * 100

@main.route('/')
def index():
    if current_user.is_authenticated:
        completed_activities = Activity.query.filter_by(user_id=current_user.id, completed=True).count()
        active_quests = Quest.query.filter_by(user_id=current_user.id, completed_at=None).count()
        return render_template('home.html', completed_activities=completed_activities, active_quests=active_quests)
    return render_template('index.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user, remember=request.form.get('remember', False))
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.index'))
        flash('Invalid username or password')
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not request.form.get('terms'):
            flash('You must agree to the Terms of Service and Privacy Policy')
            return redirect(url_for('main.register'))
            
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('main.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('main.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('main.register'))
            
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('register.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/terms')
def terms():
    return render_template('terms.html')

@main.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@main.route('/profile')
@login_required
def profile():
    achievements = Achievement.query.filter_by(user_id=current_user.id).all()
    activities = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.created_at.desc()).all()
    return render_template('profile.html', 
                         achievements=achievements, 
                         activities=activities,
                         user_level=calculate_user_level(current_user.points))

@main.route('/settings', methods=['GET'])
@login_required
def settings():
    return render_template('settings.html')

@main.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    try:
        # Update user settings
        if 'email' in request.form:
            new_email = request.form['email']
            if new_email != current_user.email:
                if User.query.filter_by(email=new_email).first():
                    flash('Email already exists')
                    return redirect(url_for('main.settings'))
                current_user.email = new_email

        if 'username' in request.form:
            new_username = request.form['username']
            if new_username != current_user.username:
                if User.query.filter_by(username=new_username).first():
                    flash('Username already exists')
                    return redirect(url_for('main.settings'))
                current_user.username = new_username

        if 'current_password' in request.form and 'new_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect')
                return redirect(url_for('main.settings'))
                
            if new_password:
                current_user.password_hash = generate_password_hash(new_password)

        # Update notification preferences
        current_user.email_notifications = 'email_notifications' in request.form
        current_user.push_notifications = 'push_notifications' in request.form

        db.session.commit()
        flash('Settings updated successfully')
        return redirect(url_for('main.profile'))

    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating settings')
        return redirect(url_for('main.settings'))

@main.route('/quests')
@login_required
def quests():
    """Display user's quests."""
    # Get user's quests ordered by creation date
    user_quests = Quest.query.filter_by(user_id=current_user.id).order_by(Quest.created_at.desc()).all()
    return render_template('quests.html', quests=user_quests)

@main.route('/active_quests')
@login_required
def active_quests():
    """Get user's active quests."""
    active_quests = Quest.query.filter_by(
        user_id=current_user.id,
        completed_at=None
    ).order_by(Quest.created_at.desc()).all()
    return jsonify([quest.to_dict() for quest in active_quests])

@main.route('/completed_quests')
@login_required
def completed_quests():
    """Get user's completed quests."""
    completed_quests = Quest.query.filter_by(
        user_id=current_user.id
    ).filter(Quest.completed_at.isnot(None)
    ).order_by(Quest.completed_at.desc()).all()
    return jsonify([quest.to_dict() for quest in completed_quests])

@main.route('/challenges')
@login_required
def challenges():
    """Display the challenges page."""
    active = Challenge.query.filter_by(
        user_id=current_user.id,
        completed=False
    ).order_by(Challenge.created_at.desc()).all()
    
    completed = Challenge.query.filter_by(
        user_id=current_user.id,
        completed=True
    ).order_by(Challenge.completed_at.desc()).all()
    
    return render_template('challenges.html', 
                         active_challenges=active,
                         completed_challenges=completed,
                         timedelta=timedelta)

@main.route('/challenges/generate', methods=['POST'])
@login_required
def create_challenge():
    """Generate a new challenge for the user."""
    try:
        data = request.get_json()
        difficulty = request.form.get('difficulty', 'medium').lower()
        
        # Generate the appropriate prompt
        prompt = generate_challenge_prompt(difficulty)
        
        # Call OpenRouter API directly
        OPENROUTER_API_KEY = "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"
        
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'Wanderlust Challenge Generator'
        }
        
        request_data = {
            'model': 'mistralai/mistral-7b-instruct',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are an expert local guide creating exciting challenges.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 1000,
            'response_format': { 'type': 'json_object' }
        }
        
        response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=request_data,
                timeout=30
            )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status code: {response.status_code}\nResponse: {response.text}")
        
        # Parse the response
        api_response = response.json()
        if not api_response.get('choices') or not api_response['choices'][0].get('message'):
            raise Exception("Invalid API response format")
        
        # Extract and parse the challenge data
        challenge_text = api_response['choices'][0]['message']['content']
        
        try:
            challenge_data = json.loads(challenge_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', challenge_text, re.DOTALL)
            if json_match:
                challenge_data = json.loads(json_match.group(0))
            else:
                raise Exception("Could not parse challenge data as JSON")
        
        # Validate required fields
        required_fields = ['title', 'description', 'activities']
        missing_fields = [field for field in required_fields if field not in challenge_data]
        if missing_fields:
            raise Exception(f"Missing required fields in challenge data: {', '.join(missing_fields)}")
        
        # Create new challenge
        new_challenge = Challenge(
            title=challenge_data['title'],
            description=challenge_data['description'],
            activities=challenge_data['activities'],
            time_limit=int(challenge_data.get('time_limit', 120)),  # Default 2 hours in minutes
            points_reward=int(challenge_data.get('points_reward', 0)),
            user_id=current_user.id
        )
        
        db.session.add(new_challenge)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'challenge': {
                'id': new_challenge.id,
                'title': new_challenge.title,
                'description': new_challenge.description,
                'activities': new_challenge.activities,
                'time_limit': new_challenge.time_limit,
                'points_reward': new_challenge.points_reward
            }
        })
        
    except Exception as e:
        print(f"Error generating challenge: {str(e)}")  # For debugging
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@main.route('/challenges/complete/<int:challenge_id>', methods=['POST'])
@login_required
def complete_challenge(challenge_id):
    """Mark a challenge as completed and award points."""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if challenge.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    if challenge.completed:
        return jsonify({"status": "error", "message": "Challenge already completed"}), 400
        
    challenge.completed = True
    challenge.completed_at = datetime.utcnow()
    current_user.points += challenge.points_reward
    
    db.session.commit()
    
    # Check for achievements
    check_achievements()
    
    return jsonify({
        "status": "success",
        "message": "Challenge completed!",
        "points_earned": challenge.points_reward
    })

@main.route('/challenges/active')
@login_required
def get_active_challenges():
    """Get user's active challenges."""
    challenges = Challenge.query.filter_by(
        user_id=current_user.id,
        completed=False
    ).order_by(Challenge.created_at.desc()).all()
    
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'activities': c.activities,
        'time_limit': c.time_limit,
        'points_reward': c.points_reward,
        'created_at': c.created_at.isoformat()
    } for c in challenges])

@main.route('/challenges/completed')
@login_required
def get_completed_challenges():
    """Get user's completed challenges."""
    challenges = Challenge.query.filter_by(
        user_id=current_user.id,
        completed=True
    ).order_by(Challenge.completed_at.desc()).all()
    
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'activities': c.activities,
        'time_limit': c.time_limit,
        'points_reward': c.points_reward,
        'completed_at': c.completed_at.isoformat()
    } for c in challenges])

def generate_activity_prompt(category, difficulty):
    """Generate a dynamic prompt based on category and difficulty."""
    base_location = "Churchgate, Mumbai"
    current_time = "daytime"  # You can make this dynamic based on actual time
    
    prompts = {
        "food": {
            "easy": f"Generate a casual dining experience in {base_location}. Focus on popular, easily accessible restaurants or cafes with average pricing. Include:\n"
                   "1. Restaurant/cafe name\n"
                   "2. Type of cuisine\n"
                   "3. Must-try dishes (2-3 items)\n"
                   "4. Average cost for two\n"
                   "5. Exact location\n"
                   "6. Best time to visit\n"
                   "7. Duration: 30-60 minutes\n"
                   "Format the response as JSON with these exact keys: title, description, duration, location",
            
            "medium": f"Create a food exploration activity in {base_location} that includes multiple stops. Consider:\n"
                     "1. 2-3 different eateries\n"
                     "2. Mix of street food and restaurants\n"
                     "3. Specific food items to try at each stop\n"
                     "4. Total budget range\n"
                     "5. Suggested route\n"
                     "6. Duration: 1-2 hours\n"
                     "Format the response as JSON with these exact keys: title, description, duration, location",
            
            "hard": f"Design a comprehensive food tour in {base_location} that includes:\n"
                   "1. 4-5 diverse food establishments\n"
                   "2. Mix of historic and modern eateries\n"
                   "3. Special dishes and their history\n"
                   "4. Cultural significance of each stop\n"
                   "5. Detailed tasting notes\n"
                   "6. Duration: 2-3 hours\n"
                   "Format the response as JSON with these exact keys: title, description, duration, location"
        },
        "culture": {
            "easy": f"Create a simple cultural activity in {base_location} suitable for {current_time}. Include:\n"
                   "1. One main cultural site or institution\n"
                   "2. Its historical significance\n"
                   "3. Key things to observe\n"
                   "4. Best time to visit\n"
                   "5. Duration: 30-60 minutes\n"
                   "Format the response as JSON with these exact keys: title, description, duration, location",
            
            "medium": f"Design a cultural exploration in {base_location} that includes:\n"
                     "1. 2-3 cultural sites\n"
                     "2. Historical background\n"
                     "3. Cultural practices to observe\n"
                     "4. Photo opportunities\n"
                     "5. Local customs to be aware of\n"
                     "6. Duration: 1-2 hours\n"
                     "Format the response as JSON with these exact keys: title, description, duration, location",
            
            "hard": f"Create an immersive cultural experience in {base_location} covering:\n"
                   "1. Multiple historical sites\n"
                   "2. Local art and architecture\n"
                   "3. Cultural workshops or activities\n"
                   "4. Traditional performances if available\n"
                   "5. Cultural significance of each location\n"
                   "6. Duration: 2-3 hours\n"
                   "Format the response as JSON with these exact keys: title, description, duration, location"
        },
        "adventure": {
            "easy": f"Design a light adventure activity in {base_location} suitable for {current_time}. Include:\n"
                   "1. One main location or activity\n"
                   "2. Required preparation\n"
                   "3. Safety considerations\n"
                   "4. Best time to do it\n"
                   "5. Duration: 30-60 minutes\n"
                   "Format the response as JSON with these exact keys: title, description, duration, location",
            
            "medium": f"Create an engaging adventure in {base_location} that includes:\n"
                     "1. 2-3 different activities\n"
                     "2. Required equipment or preparation\n"
                     "3. Physical requirements\n"
                     "4. Safety guidelines\n"
                     "5. Alternative options\n"
                     "6. Duration: 1-2 hours\n"
                     "Format the response as JSON with these exact keys: title, description, duration, location",
            
            "hard": f"Design a challenging adventure experience in {base_location} that involves:\n"
                   "1. Multiple challenging activities\n"
                   "2. Detailed preparation requirements\n"
                   "3. Physical fitness needs\n"
                   "4. Safety protocols\n"
                   "5. Emergency contacts\n"
                   "6. Duration: 2-3 hours\n"
                   "Format the response as JSON with these exact keys: title, description, duration, location"
        }
    }
    
    # Get the prompt for the selected category and difficulty
    selected_category = prompts.get(category.lower())
    if not selected_category:
        raise Exception(f"Invalid category: {category}. Must be one of: {', '.join(prompts.keys())}")
        
    selected_prompt = selected_category.get(difficulty.lower())
    if not selected_prompt:
        raise Exception(f"Invalid difficulty: {difficulty}. Must be one of: {', '.join(selected_category.keys())}")
    
    return selected_prompt

@main.route('/generate_activity', methods=['POST'])
@login_required
def generate_activity():
    try:
        category = request.form.get('category', 'food').lower()
        difficulty = request.form.get('difficulty', 'easy').lower()
        
        # Generate the appropriate prompt
        prompt = generate_activity_prompt(category, difficulty)
        
        # Call OpenRouter API directly (no OpenAI client needed)
        OPENROUTER_API_KEY = "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"  # Replace with your actual OpenRouter API key
        
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'Wanderlust Adventure Generator'
        }
        
        request_data = {
            'model': 'mistralai/mistral-7b-instruct',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are an expert local guide in Mumbai, specializing in creating personalized adventures. Always respond in the exact JSON format requested with these keys: title, description, duration, location'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 1000,
            'response_format': { 'type': 'json_object' }
        }
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status code: {response.status_code}\nResponse: {response.text}")
            
        # Parse the response
        api_response = response.json()
        if not api_response.get('choices') or not api_response['choices'][0].get('message'):
            raise Exception("Invalid API response format")
            
        # Extract and parse the activity data
        activity_text = api_response['choices'][0]['message']['content']
        
        # Try to parse the JSON response
        try:
            activity_data = json.loads(activity_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the text
            import re
            json_match = re.search(r'\{.*\}', activity_text, re.DOTALL)
            if json_match:
                activity_data = json.loads(json_match.group(0))
            else:
                raise Exception("Could not parse activity data as JSON")
        
        # Create new activity
        new_activity = Activity(
            title=activity_data['title'],
            description=activity_data['description'],
            category=category,
            difficulty=difficulty,
            duration=activity_data.get('duration', '60 minutes'),
            location=activity_data.get('location', 'Churchgate, Mumbai'),
            user_id=current_user.id
        )
        
        db.session.add(new_activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'activity': {
                'id': new_activity.id,
                'title': new_activity.title,
                'description': new_activity.description,
                'category': new_activity.category,
                'difficulty': new_activity.difficulty,
                'duration': new_activity.duration,
                'location': new_activity.location
            }
        })
        
    except Exception as e:
        print(f"Error generating activity: {str(e)}")  # For debugging
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main.route('/complete_activity/<int:activity_id>', methods=['POST'])
@login_required
def complete_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    activity.completed = True
    current_user.points += calculate_points(activity)
    db.session.commit()
    
    check_achievements()
    return jsonify({'success': True, 'points': current_user.points})

def calculate_points(activity):
    points = {
        'easy': 10,
        'medium': 25,
        'hard': 50
    }
    return points.get(activity.difficulty.lower(), 10)

def calculate_user_level(points):
    levels = [
        (0, "Novice Explorer"),
        (100, "Adventure Seeker"),
        (250, "Urban Wanderer"),
        (500, "City Navigator"),
        (1000, "Local Legend")
    ]
    
    for threshold, level in reversed(levels):
        if points >= threshold:
            return level
    return levels[0][1]

def check_achievements():
    # Check for new achievements based on user's activities and points
    completed_activities = Activity.query.filter_by(
        user_id=current_user.id, completed=True).count()
    
    achievements_data = [
        {
            'title': 'Adventure Beginner',
            'description': 'Complete 5 activities',
            'requirement': lambda: completed_activities >= 5,
            'points': 50
        },
        {
            'title': 'Explorer',
            'description': 'Complete 10 activities',
            'requirement': lambda: completed_activities >= 10,
            'points': 100
        },
        {
            'title': 'Wanderlust Master',
            'description': 'Complete 25 activities',
            'requirement': lambda: completed_activities >= 25,
            'points': 250
        }
    ]
    
    for achievement_data in achievements_data:
        if achievement_data['requirement']() and not Achievement.query.filter_by(
            user_id=current_user.id, title=achievement_data['title']).first():
            new_achievement = Achievement(
                title=achievement_data['title'],
                description=achievement_data['description'],
                points_value=achievement_data['points'],
                user_id=current_user.id
            )
            db.session.add(new_achievement)
            current_user.points += achievement_data['points']
            
    db.session.commit()

def generate_quest_prompt(difficulty):
    """Generate a dynamic prompt for quest generation."""
    base_location = "Churchgate, Mumbai"
    current_time = "evening"  # You can make this dynamic based on actual time
    
    prompts = {
        "easy": f"""Create a beginner-friendly quest in {base_location} with 3 connected steps. 
Return ONLY a JSON object with this exact format:
{{
    "title": "Quest title here",
    "description": "Overall quest description here",
    "duration": 90,
    "steps": [
        {{
            "title": "Step 1 title",
            "description": "Step 1 description"
        }},
        {{
            "title": "Step 2 title",
            "description": "Step 2 description"
        }},
        {{
            "title": "Step 3 title",
            "description": "Step 3 description"
        }}
    ]
}}

The quest should:
1. Take 1-2 hours total
2. Include easy-to-find locations
3. Mix of activities (e.g., food, sightseeing)
4. Be suitable for any time of day""",
        
        "medium": f"""Design a moderate quest in {base_location} with 4 connected steps. 
Return ONLY a JSON object with this exact format:
{{
    "title": "Quest title here",
    "description": "Overall quest description here",
    "duration": 150,
    "steps": [
        {{
            "title": "Step 1 title",
            "description": "Step 1 description"
        }},
        {{
            "title": "Step 2 title",
            "description": "Step 2 description"
        }},
        {{
            "title": "Step 3 title",
            "description": "Step 3 description"
        }},
        {{
            "title": "Step 4 title",
            "description": "Step 4 description"
        }}
    ]
}}

The quest should:
1. Take 2-3 hours total
2. Include some lesser-known spots
3. Mix of activities and challenges
4. Consider time of day for activities""",
        
        "hard": f"""Create a challenging quest in {base_location} with 5 connected steps. 
Return ONLY a JSON object with this exact format:
{{
    "title": "Quest title here",
    "description": "Overall quest description here",
    "duration": 210,
    "steps": [
        {{
            "title": "Step 1 title",
            "description": "Step 1 description"
        }},
        {{
            "title": "Step 2 title",
            "description": "Step 2 description"
        }},
        {{
            "title": "Step 3 title",
            "description": "Step 3 description"
        }},
        {{
            "title": "Step 4 title",
            "description": "Step 4 description"
        }},
        {{
            "title": "Step 5 title",
            "description": "Step 5 description"
        }}
    ]
}}

The quest should:
1. Take 3-4 hours total
2. Include hidden gems and local secrets
3. Complex mix of activities and challenges
4. Strategic planning of timing and routes"""
    }
    
    selected_prompt = prompts.get(difficulty.lower())
    if not selected_prompt:
        raise Exception(f"Invalid difficulty: {difficulty}. Must be one of: {', '.join(prompts.keys())}")
    
    return selected_prompt

@main.route('/generate_quest', methods=['POST'])
@login_required
def generate_quest():
    try:
        difficulty = request.form.get('difficulty', 'medium').lower()
        
        # Generate the appropriate prompt
        prompt = generate_quest_prompt(difficulty)
        
        # Call OpenRouter API directly (no OpenAI client needed)
        OPENROUTER_API_KEY = "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"
        
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'Wanderlust Quest Generator'
        }
        
        request_data = {
            'model': 'mistralai/mistral-7b-instruct',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are an expert local guide in Mumbai. You must ONLY return a JSON object with the exact format specified in the prompt. Do not include any other text or explanations.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 1000,
            'response_format': { 'type': 'json_object' }
        }
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status code: {response.status_code}\nResponse: {response.text}")
        
        # Parse the response
        api_response = response.json()
        if not api_response.get('choices') or not api_response['choices'][0].get('message'):
            raise Exception("Invalid API response format")
        
        # Extract and parse the quest data
        quest_text = api_response['choices'][0]['message']['content']
        
        try:
            quest_data = json.loads(quest_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the text
            import re
            json_match = re.search(r'\{.*\}', quest_text, re.DOTALL)
            if json_match:
                quest_data = json.loads(json_match.group(0))
            else:
                raise Exception("Could not parse quest data as JSON")
        
        # Validate required fields
        required_fields = ['title', 'description', 'steps']
        missing_fields = [field for field in required_fields if field not in quest_data]
        if missing_fields:
            raise Exception(f"Missing required fields in quest data: {', '.join(missing_fields)}")
        
        # Create new quest
        new_quest = Quest(
            title=quest_data['title'],
            description=quest_data['description'],
            difficulty=difficulty,
            duration=int(quest_data.get('duration', 120)),  # Default 2 hours in minutes
            steps=quest_data['steps'],
            user_id=current_user.id
        )
        
        db.session.add(new_quest)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'quest': {
                'id': new_quest.id,
                'title': new_quest.title,
                'description': new_quest.description,
                'difficulty': new_quest.difficulty,
                'duration': new_quest.duration,
                'steps': new_quest.steps
            }
        })
        
    except Exception as e:
        print(f"Error generating quest: {str(e)}")  # For debugging
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main.route('/complete_quest/<int:quest_id>', methods=['POST'])
@login_required
def complete_quest(quest_id):
    try:
        quest = Quest.query.get_or_404(quest_id)
        
        # Verify quest belongs to current user
        if quest.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        
        # Check if quest is already completed
        if quest.completed_at:
            return jsonify({'success': False, 'error': 'Quest already completed'}), 400
        
        # Calculate points based on difficulty
        points_map = {
            'easy': 100,
            'medium': 200,
            'hard': 300
        }
        points_earned = points_map.get(quest.difficulty.lower(), 100)
        
        # Update quest
        quest.completed_at = datetime.utcnow()
        quest.points = points_earned
        
        # Add points to user
        current_user.points = (current_user.points or 0) + points_earned
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'points_earned': points_earned,
            'total_points': current_user.points
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_challenge_prompt(difficulty):
    base_prompt = """Create an exciting mini-adventure challenge with multiple related activities. 
    Format the response as a JSON object with the following structure:
    {
        "title": "Challenge title",
        "description": "Overall challenge description",
        "activities": [
            {
                "description": "Activity description",
                "time_limit": minutes_to_complete,
                "completed": false,
                "points": points_for_activity
            }
        ],
        "total_time_limit": total_minutes,
        "points_reward": total_points
    }"""
    
    difficulty_modifiers = {
        "easy": "3-4 simple activities, 15-30 minutes each, total time 2 hours",
        "medium": "4-5 moderate activities, 30-45 minutes each, total time 3 hours",
        "hard": "5-6 challenging activities, 45-60 minutes each, total time 4 hours"
    }
    
    return f"{base_prompt}\n\nDifficulty level: {difficulty_modifiers[difficulty]}"

@main.route('/challenges/accept/<int:challenge_id>', methods=['POST'])
@login_required
def accept_challenge(challenge_id):
    try:
        challenge = Challenge.query.get_or_404(challenge_id)
        
        if challenge.user_id != current_user.id:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
            
        if challenge.accepted:
            return jsonify({"status": "error", "message": "Challenge already accepted"}), 400
            
        challenge.accepted = True
        challenge.accepted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Challenge accepted! Complete the activities within the time limit."
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/challenges/complete-activity/<int:challenge_id>/<int:activity_index>', methods=['POST'])
@login_required
def complete_activity2(challenge_id, activity_index):
    try:
        challenge = Challenge.query.get_or_404(challenge_id)
        
        if challenge.user_id != current_user.id:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
            
        if not challenge.accepted:
            return jsonify({"status": "error", "message": "Challenge not accepted yet"}), 400
            
        if challenge.is_expired():
            return jsonify({"status": "error", "message": "Challenge has expired"}), 400
            
        if activity_index >= len(challenge.activities):
            return jsonify({"status": "error", "message": "Invalid activity index"}), 400
            
        # Update activity completion
        challenge.activities[activity_index]['completed'] = True
        challenge.activities[activity_index]['completed_at'] = datetime.utcnow().isoformat()
        
        # Check if all activities are completed
        if all(activity['completed'] for activity in challenge.activities):
            challenge.completed = True
            challenge.completed_at = datetime.utcnow()
            current_user.points += challenge.points_reward
            
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Activity completed!",
            "progress": challenge.get_progress(),
            "challenge_completed": challenge.completed,
            "points_earned": challenge.points_reward if challenge.completed else 0
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/generate_challenge', methods=['POST'])
@login_required
def generate_challenge():
    try:
        difficulty = request.form.get('difficulty', 'medium').lower()
        
        # Generate the appropriate prompt
        prompt = generate_challenge_prompt(difficulty)
        
        # Call OpenRouter API directly
        OPENROUTER_API_KEY = "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"
        
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'Wanderlust Challenge Generator'
        }
        
        request_data = {
            'model': 'mistralai/mistral-7b-instruct',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are an expert local guide creating exciting challenges.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 1000,
            'response_format': { 'type': 'json_object' }
        }
        
        response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=request_data,
                timeout=30
            )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status code: {response.status_code}\nResponse: {response.text}")
        
        # Parse the response
        api_response = response.json()
        if not api_response.get('choices') or not api_response['choices'][0].get('message'):
            raise Exception("Invalid API response format")
        
        # Extract and parse the challenge data
        challenge_text = api_response['choices'][0]['message']['content']
        
        try:
            challenge_data = json.loads(challenge_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', challenge_text, re.DOTALL)
            if json_match:
                challenge_data = json.loads(json_match.group(0))
            else:
                raise Exception("Could not parse challenge data as JSON")
        
        # Validate required fields
        required_fields = ['title', 'description', 'activities']
        missing_fields = [field for field in required_fields if field not in challenge_data]
        if missing_fields:
            raise Exception(f"Missing required fields in challenge data: {', '.join(missing_fields)}")
        
        # Create new challenge
        new_challenge = Challenge(
            title=challenge_data['title'],
            description=challenge_data['description'],
            activities=challenge_data['activities'],
            time_limit=int(challenge_data.get('time_limit', 120)),  # Default 2 hours in minutes
            points_reward=int(challenge_data.get('points_reward', 0)),
            user_id=current_user.id
        )
        
        db.session.add(new_challenge)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'challenge': {
                'id': new_challenge.id,
                'title': new_challenge.title,
                'description': new_challenge.description,
                'activities': new_challenge.activities,
                'time_limit': new_challenge.time_limit,
                'points_reward': new_challenge.points_reward
            }
        })
        
    except Exception as e:
        print(f"Error generating challenge: {str(e)}")  # For debugging
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main.route('/challenges/complete/<int:challenge_id>', methods=['POST'])
@login_required
def get_challenge(challenge_id):
    """Mark a challenge as completed and award points."""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if challenge.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    if challenge.completed:
        return jsonify({"status": "error", "message": "Challenge already completed"}), 400
        
    challenge.completed = True
    challenge.completed_at = datetime.utcnow()
    current_user.points += challenge.points_reward
    
    db.session.commit()
    
    # Check for achievements
    check_achievements()
    
    return jsonify({
        "status": "success",
        "message": "Challenge completed!",
        "points_earned": challenge.points_reward
    })

@main.route('/active_challenges')
@login_required
def active_challenges():
    """Get user's active challenges."""
    challenges = Challenge.query.filter_by(
        user_id=current_user.id,
        completed=False
    ).order_by(Challenge.created_at.desc()).all()
    
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'activities': c.activities,
        'time_limit': c.time_limit,
        'points_reward': c.points_reward,
        'created_at': c.created_at.isoformat()
    } for c in challenges])

@main.route('/completed_challenges')
@login_required
def completed_challenges():
    """Get user's completed challenges."""
    challenges = Challenge.query.filter_by(
        user_id=current_user.id,
        completed=True
    ).order_by(Challenge.completed_at.desc()).all()
    
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'activities': c.activities,
        'time_limit': c.time_limit,
        'points_reward': c.points_reward,
        'completed_at': c.completed_at.isoformat()
    } for c in challenges])
