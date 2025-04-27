import os
import secrets
from PIL import Image
from flask import current_app
from werkzeug.utils import secure_filename

def save_picture(form_picture, folder_name):
    """
    Save picture with a random name to prevent collisions
    """
    # Generate a random hex to make filename unique
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    # Create upload folder if it doesn't exist
    picture_path = os.path.join(current_app.root_path, 'static/uploads', folder_name)
    if not os.path.exists(picture_path):
        os.makedirs(picture_path)
    
    picture_path = os.path.join(picture_path, picture_fn)
    
    # Resize image to save space
    output_size = (400, 400)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn

def allowed_file(filename, allowed_extensions):
    """
    Check if a file has an allowed extension
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def calculate_progress(enrollment):
    """
    Calculate and update student progress in a course
    """
    from models import Content
    # Get total course content
    course_contents = Content.query.filter_by(course_id=enrollment.course_id).count()
    
    # Calculate percentage completed
    if course_contents > 0:
        # This would be more complex in a real application
        # Here we would need to track which content items the student has viewed
        enrollment.progress = 0.0
        # In a real app, we'd set progress based on completed content
        
    enrollment.progress = max(0.0, min(100.0, enrollment.progress))
    return enrollment.progress

def generate_course_analytics(course_id):
    """
    Generate analytics data for a course
    """
    from models import Course, Enrollment, Payment
    from datetime import datetime, timedelta
    
    # Get the course
    course = Course.query.get(course_id)
    if not course:
        return None
    
    # Get enrollments by date (last 30 days)
    today = datetime.utcnow()
    thirty_days_ago = today - timedelta(days=30)
    
    enrollments = Enrollment.query.filter(
        Enrollment.course_id == course_id,
        Enrollment.enrolled_at >= thirty_days_ago
    ).all()
    
    # Get payments
    payments = Payment.query.filter(
        Payment.course_id == course_id,
        Payment.status == 'completed'
    ).all()
    
    # Calculate metrics
    total_enrollments = len(enrollments)
    total_revenue = sum(payment.amount for payment in payments)
    
    # Group enrollments by date
    enrollment_dates = {}
    for enrollment in enrollments:
        date_str = enrollment.enrolled_at.strftime('%Y-%m-%d')
        if date_str in enrollment_dates:
            enrollment_dates[date_str] += 1
        else:
            enrollment_dates[date_str] = 1
    
    # Structure data for charts
    dates = []
    counts = []
    for i in range(30):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        dates.insert(0, date)
        counts.insert(0, enrollment_dates.get(date, 0))
    
    return {
        'total_enrollments': total_enrollments,
        'total_revenue': total_revenue,
        'enrollment_dates': dates,
        'enrollment_counts': counts,
        'course': course
    }
    
def create_notification(user_id, title, message, notification_type, related_id=None):
    """
    Create a notification for a user
    
    Parameters:
    - user_id: ID of the user to receive the notification
    - title: Title of the notification
    - message: Detailed message for the notification
    - notification_type: Type of notification (enrollment, payment, content, etc)
    - related_id: ID of the related item (course_id, payment_id, etc)
    
    Returns:
    - Notification object or None if error
    """
    from models import Notification, User
    from app import db
    import logging
    
    try:
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            logging.error(f"Failed to create notification: User ID {user_id} not found")
            return None
        
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_id=related_id
        )
        db.session.add(notification)
        db.session.commit()
        
        logging.info(f"Notification created for user {user_id}: {title}")
        return notification
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating notification: {str(e)}")
        return None

def get_file_url(file_path):
    """
    Formats a file path for proper URL display
    Prevents issues with double paths like /static/uploads/content/static/uploads/content/file.mp4
    """
    if not file_path:
        return None
        
    # If the path already has /static/ at the beginning, return it as is
    if file_path.startswith('/static/'):
        return file_path
        
    # If the path starts with static/, add the leading slash
    if file_path.startswith('static/'):
        return f"/{file_path}"
        
    # If it's a relative path within uploads/
    if file_path.startswith('uploads/'):
        return f"/static/{file_path}"
        
    # For legacy paths that are just filenames
    return f"/static/uploads/content/{file_path}"

def save_file(form_file, folder_name, custom_filename=None):
    """
    Save any file type with a secure name to specified folder
    
    Parameters:
    - form_file: File object from form
    - folder_name: Target folder under static/uploads/
    - custom_filename: Optional custom filename to use
    
    Returns:
    - Filename of saved file
    """
    if not form_file:
        return None
    
    # Generate a random hex to make filename unique if no custom name provided
    if custom_filename:
        filename = secure_filename(custom_filename)
    else:
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_file.filename)
        filename = random_hex + f_ext
    
    # Create upload folder if it doesn't exist
    file_path = os.path.join(current_app.root_path, 'static/uploads', folder_name)
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    
    file_path = os.path.join(file_path, filename)
    
    # Save the file
    form_file.save(file_path)
    
    return filename