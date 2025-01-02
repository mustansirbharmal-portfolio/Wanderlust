from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
                
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wanderlust.db'
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    from .models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from .routes import main
    app.register_blueprint(main)
    
    return app
