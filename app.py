import os
import logging
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_from_directory
from markupsafe import Markup
from flask_wtf.csrf import CSRFProtect
from extensions import db, login_manager, mail
from models import User, Notification, Contact
from flask_login import current_user

# Import blueprints
from routes.auth import bp as auth_bp
from routes.admin import bp as admin_bp
from routes.course import bp as course_bp
from routes.users import bp as users_bp
from routes.discussion import bp as discussion_bp
from routes.notification import bp as notification_bp
from routes.certificate import bp as certificate_bp
from routes.assignment import bp as assignment_bp
from routes.subscription import bp as subscription_bp
from routes.contact import bp as contact_bp
from routes.stripe_payment import bp as stripe_payment_bp
from routes.payment import bp as payment_bp
from routes.testimonial import bp as testimonial_bp
from routes.quiz import bp as quiz_bp
from routes.main import bp as main_bp

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app():
    # Create the Flask app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "development-secret-key")

    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///elearning.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configure file upload settings
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
    
    # Configure pagination settings
    app.config['COURSES_PER_PAGE'] = 12  # Number of courses to display per page

    # Set up CSRF protection
    csrf = CSRFProtect(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    app.register_blueprint(main_bp)  # Register main blueprint first
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(course_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(discussion_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(certificate_bp)
    app.register_blueprint(assignment_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(stripe_payment_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(testimonial_bp)
    app.register_blueprint(quiz_bp)

    # Custom Jinja filters
    def timeago(date):
        """Convert datetime to a 'time ago' string"""
        now = datetime.utcnow()
        diff = now - date
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{int(minutes)} {'minute' if minutes == 1 else 'minutes'} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{int(hours)} {'hour' if hours == 1 else 'hours'} ago"
        elif seconds < 604800:
            days = seconds // 86400
            return f"{int(days)} {'day' if days == 1 else 'days'} ago"
        else:
            return date.strftime('%Y-%m-%d')

    # nl2br filter for converting newlines to <br> tags
    def nl2br(value):
        """Convert newlines to <br> tags"""
        if not value:
            return ""
        return Markup(value.replace('\n', '<br>'))

    # Register the filters with Jinja
    app.jinja_env.filters['timeago'] = timeago
    app.jinja_env.filters['nl2br'] = nl2br

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logger.debug("Database tables created")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    # Setup Stripe
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe_key or stripe_key.startswith('sk_test_'):
        logger.warning("Using test Stripe API key. Set STRIPE_SECRET_KEY environment variable for production.")

    logger.debug("App initialized")

    # Context processors for template variables
    @app.context_processor
    def inject_template_vars():
        if current_user.is_authenticated:
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
            
            unread_messages = Contact.query.filter_by(
                recipient_id=current_user.id,
                is_read=False
            ).count()
            
            return {
                'unread_notifications': unread_notifications,
                'unread_messages': unread_messages
            }
        return {
            'unread_notifications': 0,
            'unread_messages': 0
        }

    return app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
