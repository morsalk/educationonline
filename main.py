from flask import render_template
from flask_login import current_user

# Import route modules
from routes.auth import bp as auth_bp
from routes.course import bp as course_bp
from routes.discussion import bp as discussion_bp
from routes.payment import bp as payment_bp
from routes.admin import bp as admin_bp
from routes.notification import bp as notification_bp
from routes.contact import bp as contact_bp
from routes.users import bp as users_bp
from routes.subscription import bp as subscription_bp
from routes.testimonial import bp as testimonial_bp
from routes.certificate import bp as certificate_bp
from routes.assignment import bp as assignment_bp
from routes.stripe_payment import bp as stripe_payment_bp

from models import Course, Testimonial, Notification, Contact

def register_routes(app):
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(discussion_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(notification_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(testimonial_bp)
    app.register_blueprint(certificate_bp)
    app.register_blueprint(assignment_bp)
    app.register_blueprint(stripe_payment_bp)

    # Register home route
    @app.route('/')
    def home():
        courses = (
            Course.query
            .filter_by(is_published=True)
            .order_by(Course.rating.desc())
            .limit(6)
            .all()
        )
        testimonials = (
            Testimonial.query
            .filter_by(is_approved=True)
            .order_by(Testimonial.created_at.desc())
            .limit(6)
            .all()
        )
        return render_template(
            'home.html',
            courses=courses,
            testimonials=testimonials
        )

def notification_processor():
    if current_user.is_authenticated:
        unread_notifications = (
            Notification.query
            .filter_by(user_id=current_user.id, is_read=False)
            .count()
        )
        unread_messages = (
            Contact.query
            .filter_by(recipient_id=current_user.id, is_read=False)
            .count()
        )
        recent_notifications = (
            Notification.query
            .filter_by(user_id=current_user.id)
            .order_by(Notification.created_at.desc())
            .limit(5)
            .all()
        )
        return {
            'unread_notifications': unread_notifications,
            'unread_messages': unread_messages,
            'recent_notifications': recent_notifications
        }
    return {
        'unread_notifications': 0,
        'unread_messages': 0,
        'recent_notifications': []
    }

def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500
