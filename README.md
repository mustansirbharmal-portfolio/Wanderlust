# Wanderlust - AI-Powered Local Adventure Generator

Wanderlust is an innovative web application that helps users break out of their routine by generating spontaneous local adventures in Churchgate, Mumbai. Using AI-powered suggestions, the app creates unique experiences across food, culture, and adventure categories.

## Features

- AI-generated activity suggestions in 3 categories: Food, Culture, Adventure
- Difficulty levels (Easy/Medium/Hard) with time estimates
- Quest system with themed mini-adventures
- Points and achievements system
- User profiles and progress tracking
- Clean, modern UI with intuitive navigation

## Setup Instructions

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add your OpenRouter API key:
     ```
     OPENROUTER_API_KEY=your_api_key_here
     ```
4. Initialize the database:
   ```
   python init_db.py
   ```
5. Run the application:
   ```
   python app.py
   ```

## Project Structure

- `/static` - CSS, JavaScript, and image files
- `/templates` - HTML templates
- `/instance` - SQLite database
- `app.py` - Main Flask application
- `models.py` - Database models
- `routes.py` - Application routes
- `utils.py` - Utility functions
