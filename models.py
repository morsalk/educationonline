from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='student')  # student, instructor, admin
    is_approved = db.Column(db.Boolean, default=False)  # Account approval status
    approval_date = db.Column(db.DateTime, nullable=True)  # When the account was approved
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin who approved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_pic = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)  # Optional phone number
    
    # Relationships
    courses_created = db.relationship('Course', backref='instructor', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    discussions_created = db.relationship('Discussion', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_instructor(self):
        return self.role == 'instructor' or self.role == 'admin'
    
    def is_student(self):
        return self.role == 'student'
    
    def is_active(self):
        # Admin accounts are always active
        if self.role == 'admin':
            return True
        # Other accounts need approval
        return self.is_approved
    
    def approve_account(self, admin_id):
        """Approve a user account"""
        self.is_approved = True
        self.approval_date = datetime.utcnow()
        self.approved_by = admin_id
    
    def __repr__(self):
        return f'<User {self.username}>'


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    thumbnail = db.Column(db.String(200), default='default_course.jpg')
    price = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)  # Average rating (0-5)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)
    max_enrollments = db.Column(db.Integer, default=100)  # Maximum allowed enrollments
    enrollment_deadline = db.Column(db.DateTime, nullable=True)  # Optional deadline for enrollment
    duration_days = db.Column(db.Integer, default=365)  # Course access duration in days
    category = db.Column(db.String(50), nullable=True)  # Course category
    level = db.Column(db.String(20), nullable=True)  # Course difficulty level
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='course', lazy=True, cascade="all, delete-orphan")
    contents = db.relationship('Content', backref='course', lazy=True, cascade="all, delete-orphan")
    quizzes = db.relationship('Quiz', backref='course', lazy=True, cascade="all, delete-orphan")
    discussions = db.relationship('Discussion', backref='course', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Course {self.title}>'
        
    def has_enrollment_capacity(self):
        """Check if course has capacity for more enrollments"""
        return len(self.enrollments) < self.max_enrollments
        
    def is_enrollment_open(self):
        """Check if enrollment deadline has passed"""
        if not self.enrollment_deadline:
            return True  # No deadline set means always open
        return datetime.utcnow() < self.enrollment_deadline

    def calculate_expiry_date(self, enrollment_date):
        """Calculate the expiry date for a new enrollment"""
        return enrollment_date + timedelta(days=self.duration_days)
        
    def calculate_progress(self, student_id):
        """Calculate the progress of a student in this course"""
        # Get the student's enrollment
        enrollment = Enrollment.query.filter_by(
            student_id=student_id,
            course_id=self.id
        ).first()
        
        if not enrollment:
            return 0
            
        # Get all content items for this course
        total_content = Content.query.filter_by(
            course_id=self.id
        ).count()
        if total_content == 0:
            return 0
            
        # Since there's no direct relationship between enrollments and completed content,
        # we'll use the progress field from the enrollment itself
        return enrollment.progress


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    progress = db.Column(db.Float, default=0.0)  # percentage completed
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    subscription_type = db.Column(db.String(20), default='unlimited')  # unlimited, monthly, yearly
    is_active = db.Column(db.Boolean, default=True)
    subscription_renewed = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Enrollment {self.student_id} - {self.course_id}>'
    
    def is_expired(self):
        """Check if the enrollment has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def days_until_expiry(self):
        """Calculate days remaining until expiration"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def renew_subscription(self, duration_days=30):
        """Renew the subscription for a specified number of days"""
        if self.expires_at and datetime.utcnow() < self.expires_at:
            # If not expired, add to existing expiry date
            self.expires_at = self.expires_at + timedelta(days=duration_days)
        else:
            # If expired, set from current date
            self.expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        self.subscription_renewed = datetime.utcnow()
        self.is_active = True
        db.session.commit()

    def set_expiry_date(self):
        """Set the expiry date based on course duration"""
        self.expires_at = self.course.calculate_expiry_date(self.enrolled_at)
        db.session.commit()

    def has_access(self):
        """Check if the student has access to the course"""
        return self.is_active and not self.is_expired()


class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # video, pdf, text, assignment
    file_path = db.Column(db.String(255), nullable=True)
    text_content = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Content {self.title}>'


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='lessons')
    completed_by = db.relationship('CompletedLesson', backref='lesson', lazy=True)
    
    def __repr__(self):
        return f'<Lesson {self.title}>'


class CompletedLesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', backref='completed_lessons')
    
    def __repr__(self):
        return f'<CompletedLesson {self.student_id} - {self.lesson_id}>'


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    course = db.relationship('Course', backref=db.backref('assignments', lazy=True))
    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy=True)

    def __repr__(self):
        return f'<Assignment {self.title}>'


class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submission_file = db.Column(db.String(255), nullable=True)
    submission_text = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    graded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='assignment_submissions', lazy=True)
    grader = db.relationship('User', foreign_keys=[graded_by], backref='graded_assignments', lazy=True)
    
    def __repr__(self):
        return f'<AssignmentSubmission {self.id}>'


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    time_limit = db.Column(db.Integer, default=0)  # time in minutes, 0 means no limit
    passing_score = db.Column(db.Float, default=70.0)  # percentage needed to pass
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade="all, delete-orphan")
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Quiz {self.title}>'


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='multiple_choice')  # multiple_choice, true_false, short_answer
    points = db.Column(db.Integer, default=1)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Question {self.id}>'


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Answer {self.id}>'


class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, default=0.0)
    completed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<QuizAttempt {self.id}>'


class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='discussion', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Discussion {self.title}>'


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_solution = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Recursive relationship for replies
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]),
                             lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Comment {self.id}>'


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_id = db.Column(db.String(100), nullable=True)  # external payment id (stripe, etc)
    payment_method = db.Column(db.String(20), default='easyload')  # easyload, hesabpay, paypal, stripe
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=True)  # JSON-encoded payment details
    
    # Reference to course
    course = db.relationship('Course', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.id}>'
        

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(20), nullable=False)  # enrollment, payment, content, etc
    related_id = db.Column(db.Integer, nullable=True)  # ID of related item (course_id, payment_id, etc)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Reference to user
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'
        
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='messages_sent')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='messages_received')
    
    def __repr__(self):
        return f'<Contact {self.id}: {self.subject}>'


class Testimonial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)  # Rating from 1-5
    is_approved = db.Column(db.Boolean, default=False)  # Admin must approve testimonials
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='testimonials')
    
    def __repr__(self):
        return f'<Testimonial {self.id} by {self.user.username}>'


class CourseRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating from 1-5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', backref='course_ratings')
    course = db.relationship('Course', backref='ratings')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', name='unique_student_course_rating'),
    )
    
    def __repr__(self):
        return f'<CourseRating {self.id}: {self.rating} stars by student {self.student_id} for course {self.course_id}>'


class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    certificate_id = db.Column(db.String(50), unique=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=True)
    instructor_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='certificates')
    course = db.relationship('Course', backref='certificates')
    
    def __repr__(self):
        return f'<Certificate {self.certificate_id} for {self.student.username} in {self.course.title}>'
        
    def generate_certificate_id(self):
        """Generate a unique certificate ID"""
        import uuid
        import time
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4().hex)[:8]
        return f"CERT-{self.course_id}-{self.student_id}-{timestamp}-{unique_id}"
