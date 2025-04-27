from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, TextAreaField,
    SelectField, FloatField, IntegerField, DateField, RadioField
)
from wtforms.validators import (
    DataRequired, Length, Email, EqualTo, ValidationError,
    Optional, NumberRange
)
from flask_login import current_user
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=20)]
    )
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    role = SelectField(
        'Role',
        choices=[
            ('student', 'Student'),
            ('instructor', 'Instructor'),
            ('admin', 'Admin')
        ]
    )
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError(
                'Username is already taken. Please choose a different one.'
            )

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError(
                'Email is already registered. Please use a different one.'
            )

class ProfileUpdateForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=20)]
    )
    email = StringField('Email', validators=[DataRequired(), Email()])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    profile_pic = FileField(
        'Profile Picture',
        validators=[FileAllowed(['jpg', 'png', 'jpeg'])]
    )
    submit = SubmitField('Update')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError(
                    'Username is already taken. Please choose a different one.'
                )

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError(
                    'Email is already registered. Please use a different one.'
                )

class CourseForm(FlaskForm):
    title = StringField('Course Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('programming', 'Programming'),
        ('design', 'Design'),
        ('business', 'Business'),
        ('marketing', 'Marketing'),
        ('music', 'Music'),
        ('photography', 'Photography'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    level = SelectField('Level', choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ], validators=[DataRequired()])
    course_type = RadioField('Course Type', choices=[
        ('free', 'Free Course - Available to all students at no cost'),
        ('paid', 'Paid Course - Students must purchase to access')
    ], default='free')
    price = FloatField('Price (if paid course)', validators=[NumberRange(min=0)], default=0)
    thumbnail = FileField('Thumbnail', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    max_enrollments = IntegerField('Maximum Enrollments', default=100, validators=[NumberRange(min=1)])
    enrollment_deadline = DateField('Enrollment Deadline', format='%Y-%m-%d', validators=[Optional()])
    duration_days = IntegerField('Course Duration (days)', default=365, 
                             validators=[NumberRange(min=1, max=3650)],
                             description="Number of days students will have access to the course after enrollment")
    is_published = BooleanField('Publish Course')
    submit = SubmitField('Save Course')

    def validate_price(self, field):
        if self.course_type.data == 'free' and field.data > 0:
            raise ValidationError('Free courses cannot have a price.')
        elif self.course_type.data == 'paid' and field.data <= 0:
            raise ValidationError('Paid courses must have a price greater than 0.')

class ContentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content_type = SelectField('Content Type', choices=[
        ('video', 'Video'), 
        ('pdf', 'PDF Document'), 
        ('text', 'Text Content'),
        ('assignment', 'Assignment')
    ])
    file = FileField('File Upload')
    text_content = TextAreaField('Text Content')
    order = IntegerField('Display Order', default=0)
    submit = SubmitField('Save Content')

class QuizForm(FlaskForm):
    title = StringField('Quiz Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    time_limit = IntegerField('Time Limit (minutes, 0 for no limit)', default=0, validators=[NumberRange(min=0)])
    passing_score = FloatField('Passing Score (%)', default=70, validators=[NumberRange(min=0, max=100)])
    submit = SubmitField('Save Quiz')

class QuestionForm(FlaskForm):
    text = TextAreaField('Question Text', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer')
    ])
    points = IntegerField('Points', default=1, validators=[NumberRange(min=1)])
    submit = SubmitField('Save Question')

class AnswerForm(FlaskForm):
    text = StringField('Answer Text', validators=[DataRequired()])
    is_correct = BooleanField('Correct Answer')
    submit = SubmitField('Add Answer')

class QuizAttemptForm(FlaskForm):
    submit = SubmitField('Submit Quiz')

class DiscussionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post Discussion')

class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post Comment')
    
class ContactForm(FlaskForm):
    """Form for sending contact messages to other users"""
    recipient = SelectField('Recipient', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=5, max=100)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=2000)])
    submit = SubmitField('Send Message')

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[
        ('student', 'Student'), 
        ('instructor', 'Instructor'), 
        ('admin', 'Admin')
    ])
    is_approved = BooleanField('Approve Account')
    submit = SubmitField('Save User')

class TestimonialForm(FlaskForm):
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    content = TextAreaField('Your Testimonial', validators=[DataRequired(), Length(min=20, max=500)])
    rating = RadioField('Rating', choices=[
        (1, '1 Star'), 
        (2, '2 Stars'), 
        (3, '3 Stars'), 
        (4, '4 Stars'), 
        (5, '5 Stars')
    ], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Submit Testimonial')

class CertificateForm(FlaskForm):
    """Form for issuing certificates to students"""
    instructor_notes = TextAreaField('Notes on Student Performance', 
                                  validators=[Optional(), Length(max=500)])
    submit = SubmitField('Issue Certificate')

class AssignmentSubmissionForm(FlaskForm):
    submission_file = FileField('Upload File', validators=[
        FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip'])
    ])
    submission_text = TextAreaField('Text Submission')
    submit = SubmitField('Submit Assignment')
    
    def validate(self, **kwargs):
        if not super(AssignmentSubmissionForm, self).validate(**kwargs):
            return False
        
        # At least one of file or text must be provided
        if not self.submission_file.data and not self.submission_text.data:
            self.submission_text.errors = ['Please either upload a file or provide a text submission.']
            return False
            
        return True

class AssignmentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    total_points = IntegerField('Total Points', default=100, validators=[DataRequired(), NumberRange(min=1, max=1000)])
    submit = SubmitField('Create Assignment')

class SubmissionForm(FlaskForm):
    submission_text = TextAreaField('Your Submission', validators=[DataRequired()])
    submit = SubmitField('Submit Assignment')

class GradeForm(FlaskForm):
    """Form for instructors to grade assignment submissions"""
    grade = IntegerField('Grade', validators=[
        DataRequired(), 
        NumberRange(min=0, max=100, message="Grade must be between 0 and 100")
    ])
    feedback = TextAreaField('Feedback', validators=[Optional()])
    submit = SubmitField('Save Grade')