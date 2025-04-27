import os
import logging
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

from flask import (
    render_template, flash, redirect, url_for, 
    request, abort, send_from_directory
)
from flask_login import login_user, logout_user, current_user, login_required

from app import app, db
from models import (
    User, Course, Enrollment, Content, Quiz, Question, Answer,
    QuizAttempt, Discussion, Comment, Payment, Testimonial,
    Notification
)
from forms import (
    LoginForm, RegistrationForm, CourseForm, ContentForm,
    QuizForm, QuestionForm, AnswerForm, QuizAttemptForm,
    DiscussionForm, CommentForm, AdminUserForm
)
from utils import save_picture, calculate_progress, allowed_file

logger = logging.getLogger(__name__)

def register_routes(app):
    
    # Decorator for checking if user is an instructor
    def instructor_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_instructor():
                flash('You need to be an instructor to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Decorator for checking if user is an admin
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin():
                flash('You need to be an admin to access this page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Home route
    @app.route('/')
    def home():
        # Get popular courses sorted by rating (highest first)
        popular_courses = Course.query.filter_by(is_published=True).order_by(Course.rating.desc(), Course.id.desc()).limit(6).all()
        # Get approved testimonials for the homepage
        testimonials = Testimonial.query.filter_by(is_approved=True).order_by(Testimonial.created_at.desc()).limit(3).all()
        return render_template('home.html', courses=popular_courses, testimonials=testimonials)
    
    # Auth routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('main.home'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                
                # Redirect to appropriate dashboard based on role
                if user.is_admin():
                    return redirect(url_for('admin_dashboard'))
                elif user.is_instructor():
                    return redirect(url_for('instructor_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            else:
                flash('Login failed. Please check your email and password.', 'danger')
        
        return render_template('auth/login.html', form=form)
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('main.home'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = generate_password_hash(form.password.data)
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=hashed_password,
                role=form.role.data
            )
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        
        return render_template('auth/register.html', form=form)
    
    @app.route('/logout')
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('main.home'))
    
    # Course discussion routes
    @app.route('/courses/<int:course_id>/discussions')
    def course_discussions(course_id):
        course = Course.query.get_or_404(course_id)
        discussions = Discussion.query.filter_by(course_id=course_id).order_by(Discussion.created_at.desc()).all()
        return render_template('courses/discussions.html', course=course, discussions=discussions)
    
    @app.route('/forum/thread/<int:thread_id>', methods=['GET'])
    def view_thread(thread_id):
        """View a specific forum thread"""
        thread = Discussion.query.get_or_404(thread_id)
        course = Course.query.get_or_404(thread.course_id)
        form = CommentForm()
        
        # Update view count
        thread.views += 1
        db.session.commit()
        
        # Get all comments for this thread
        comments = Comment.query.filter_by(discussion_id=thread.id).order_by(Comment.created_at.asc()).all()
        
        return render_template('forum/view.html', thread=thread, comments=comments, form=form, course=course)
    
    @app.route('/forum/new', methods=['GET', 'POST'])
    @login_required
    def new_thread():
        """Create a new forum thread"""
        course_id = request.args.get('course_id')
        course = Course.query.get_or_404(course_id)
        form = DiscussionForm()
        if form.validate_on_submit():
            discussion = Discussion(
                course_id=course.id,
                author_id=current_user.id,
                title=form.title.data,
                content=form.content.data
            )
            db.session.add(discussion)
            db.session.commit()
            flash('Your thread has been created!', 'success')
            return redirect(url_for('view_thread', thread_id=discussion.id))
        return render_template('forum/create.html', form=form, course=course)
    
    @app.route('/forum/thread/<int:thread_id>/comment', methods=['POST'])
    @login_required
    def add_comment(thread_id):
        """Add a comment to a thread"""
        thread = Discussion.query.get_or_404(thread_id)
        course = Course.query.get_or_404(thread.course_id)
        form = CommentForm()
        if form.validate_on_submit():
            comment = Comment(
                content=form.content.data,
                discussion_id=thread.id,
                author_id=current_user.id
            )
            db.session.add(comment)
            db.session.commit()
            
            # Create a notification for the thread creator if it's not the same user
            if thread.author_id != current_user.id:
                notification = Notification(
                    user_id=thread.author_id,
                    title="New Comment on Your Thread",
                    message=f"{current_user.username} commented on your thread '{thread.title}'",
                    notification_type='forum_comment',
                    related_id=thread.id
                )
                db.session.add(notification)
            
            flash('Your comment has been added!', 'success')
        return redirect(url_for('view_thread', thread_id=thread.id))
    
    @app.route('/forum/comment/<int:comment_id>/delete', methods=['GET', 'POST'])
    @login_required
    def delete_comment(comment_id):
        """Delete a comment from a thread"""
        comment = Comment.query.get_or_404(comment_id)
        thread_id = comment.discussion_id
        
        # Ensure only the comment author or admin can delete it
        if comment.author_id != current_user.id and not current_user.is_admin():
            abort(403)
        
        db.session.delete(comment)
        db.session.commit()
        
        flash('Comment deleted successfully!', 'success')
        return redirect(url_for('view_thread', thread_id=thread_id))
    
    @app.route('/forum/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_comment(comment_id):
        """Edit a comment on a thread"""
        comment = Comment.query.get_or_404(comment_id)
        thread = Discussion.query.get_or_404(comment.discussion_id)
        
        # Ensure only the comment author or admin can edit it
        if comment.author_id != current_user.id and not current_user.is_admin():
            abort(403)
        
        form = CommentForm()
        if form.validate_on_submit():
            comment.content = form.content.data
            comment.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Your comment has been updated!', 'success')
            return redirect(url_for('view_thread', thread_id=thread.id))
        elif request.method == 'GET':
            form.content.data = comment.content
        
        return render_template('forum/edit_comment.html', form=form, comment=comment, thread=thread)
    
    @app.route('/forum/thread/<int:thread_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_thread(thread_id):
        """Edit a forum thread"""
        thread = Discussion.query.get_or_404(thread_id)
        course = Course.query.get_or_404(thread.course_id)
        if thread.author_id != current_user.id and not current_user.is_admin():
            abort(403)
        
        form = DiscussionForm()
        if form.validate_on_submit():
            thread.title = form.title.data
            thread.content = form.content.data
            thread.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Your thread has been updated!', 'success')
            return redirect(url_for('view_thread', thread_id=thread.id))
        elif request.method == 'GET':
            form.title.data = thread.title
            form.content.data = thread.content
        
        return render_template('forum/edit.html', form=form, thread=thread, course=course)
    
    @app.route('/forum/thread/<int:thread_id>/delete', methods=['GET', 'POST'])
    @login_required
    def delete_thread(thread_id):
        """Delete a forum thread"""
        thread = Discussion.query.get_or_404(thread_id)
        course = Course.query.get_or_404(thread.course_id)
        
        # Ensure only the thread author or admin can delete it
        if thread.author_id != current_user.id and not current_user.is_admin():
            abort(403)
        
        # Delete all comments associated with this thread
        Comment.query.filter_by(discussion_id=thread.id).delete()
        
        # Delete the thread
        db.session.delete(thread)
        db.session.commit()
        
        flash('Your thread has been deleted!', 'success')
        return redirect(url_for('course_discussions', course_id=course.id))
    
    # Dashboard routes
    @app.route('/dashboard/student')
    @login_required
    def student_dashboard():
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        return render_template('dashboard/student.html', enrollments=enrollments)
    
    @app.route('/dashboard/instructor')
    @instructor_required
    def instructor_dashboard():
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
        return render_template('dashboard/instructor.html', courses=courses)
    
    @app.route('/dashboard/admin')
    @admin_required
    def admin_dashboard():
        users = User.query.all()
        courses = Course.query.all()
        payments = Payment.query.all()
        return render_template('dashboard/admin.html', users=users, courses=courses, payments=payments)
    
    # Course routes
    @app.route('/courses')
    def courses():
        return redirect(url_for('course.list_courses'))
    
    @app.route('/courses/create', methods=['GET', 'POST'])
    @instructor_required
    def create_course():
        # Ensure only instructors can create courses (admin cannot create courses)
        if not current_user.is_instructor():
            flash('Only instructors can create courses.', 'danger')
            return redirect(url_for('course.list_courses'))
            
        form = CourseForm()
        if form.validate_on_submit():
            thumbnail_file = form.thumbnail.data
            thumbnail_filename = None
            
            if thumbnail_file:
                thumbnail_filename = save_picture(thumbnail_file, 'course_thumbnails')
            
            # Ensure price is 0 or positive
            price = 0 if form.price.data is None else max(0, form.price.data)
            
            course = Course(
                title=form.title.data,
                description=form.description.data,
                price=price,  # Use the validated price
                thumbnail=thumbnail_filename if thumbnail_filename else 'default_course.jpg',
                instructor_id=current_user.id,
                is_published=form.is_published.data
            )
            db.session.add(course)
            db.session.commit()
            
            if price == 0:
                flash('Free course created successfully!', 'success')
            else:
                flash('Course created successfully!', 'success')
                
            return redirect(url_for('instructor_dashboard'))
        
        return render_template('courses/create.html', form=form)
    
    @app.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
    @instructor_required
    def edit_course(course_id):
        course = Course.query.get_or_404(course_id)
        # Only the instructor who created the course can edit it (admin cannot edit)
        if course.instructor_id != current_user.id:
            flash('You can only edit courses you have created.', 'danger')
            abort(403)
        
        form = CourseForm()
        if form.validate_on_submit():
            course.title = form.title.data
            course.description = form.description.data
            # Ensure price is 0 or positive
            course.price = 0 if form.price.data is None else max(0, form.price.data)
            course.is_published = form.is_published.data
            
            if form.thumbnail.data:
                thumbnail_filename = save_picture(form.thumbnail.data, 'course_thumbnails')
                course.thumbnail = thumbnail_filename
            
            db.session.commit()
            
            if course.price == 0:
                flash('Free course updated successfully!', 'success')
            else:
                flash('Course updated successfully!', 'success')
                
            return redirect(url_for('instructor_dashboard'))
        elif request.method == 'GET':
            form.title.data = course.title
            form.description.data = course.description
            form.price.data = course.price
            form.is_published.data = course.is_published
        
        return render_template('courses/edit.html', form=form, course=course)
    
    @app.route('/courses/<int:course_id>')
    def view_course(course_id):
        course = Course.query.get_or_404(course_id)
        is_enrolled = False
        if current_user.is_authenticated:
            enrollment = Enrollment.query.filter_by(
                student_id=current_user.id, 
                course_id=course.id
            ).first()
            is_enrolled = enrollment is not None
        
        return render_template('courses/view.html', course=course, is_enrolled=is_enrolled)
    
    @app.route('/courses/<int:course_id>/enroll')
    @login_required
    def enroll_course(course_id):
        course = Course.query.get_or_404(course_id)
        # Check if already enrolled
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id, 
            course_id=course.id
        ).first()
        
        # If enrollment exists but expired, redirect to renewal page
        if enrollment and enrollment.is_expired():
            flash('Your subscription for this course has expired. Please renew to continue learning.', 'warning')
            return redirect(url_for('renew_course', course_id=course.id))
        
        # If already enrolled and not expired
        if enrollment and not enrollment.is_expired():
            flash('You are already enrolled in this course.', 'info')
            return redirect(url_for('view_course', course_id=course.id))
        
        # If course is free, enroll directly with unlimited access
        if course.price == 0:
            enrollment = Enrollment(
                student_id=current_user.id,
                course_id=course.id,
                subscription_type='unlimited',
                expires_at=None,
                is_active=True
            )
            db.session.add(enrollment)
            
            # Notify student and instructor
            notification = Notification(
                user_id=current_user.id,
                title='Course Enrollment',
                message=f'You have successfully enrolled in {course.title}.',
                notification_type='enrollment',
                related_id=course.id
            )
            db.session.add(notification)
            
            instructor_notification = Notification(
                user_id=course.instructor_id,
                title='New Student Enrollment',
                message=f'{current_user.username} has enrolled in your course {course.title}.',
                notification_type='enrollment',
                related_id=course.id
            )
            db.session.add(instructor_notification)
            
            db.session.commit()
            flash('You have been enrolled in the course!', 'success')
            return redirect(url_for('view_course', course_id=course.id))
        else:
            # Redirect to payment page for paid courses
            return redirect(url_for('checkout', course_id=course.id))
    
    # Content management routes
    @app.route('/courses/<int:course_id>/content', methods=['GET', 'POST'])
    @app.route('/courses/<int:course_id>/manage-content', methods=['GET', 'POST'])
    @instructor_required
    def manage_content(course_id):
        course = Course.query.get_or_404(course_id)
        # Only the instructor who created the course can manage its content
        if course.instructor_id != current_user.id:
            flash('You can only manage content for courses you have created.', 'danger')
            abort(403)
        
        form = ContentForm()
        if form.validate_on_submit():
            file_path = None
            if form.content_type.data in ['video', 'pdf'] and form.file.data:
                file = form.file.data
                if allowed_file(file.filename, ['mp4', 'pdf']):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join('static/uploads/content', filename)
                    file.save(file_path)
            
            content = Content(
                course_id=course.id,
                title=form.title.data,
                content_type=form.content_type.data,
                file_path=file_path,
                text_content=form.text_content.data if form.content_type.data == 'text' else None,
                order=form.order.data
            )
            db.session.add(content)
            db.session.commit()
            flash('Content added successfully!', 'success')
            return redirect(url_for('manage_content', course_id=course.id))
        
        contents = Content.query.filter_by(course_id=course.id).order_by(Content.order).all()
        return render_template('courses/edit.html', form=form, course=course, contents=contents, active_tab='content')
    
    @app.route('/content/<int:content_id>/delete', methods=['POST'])
    @instructor_required
    def delete_content(content_id):
        content = Content.query.get_or_404(content_id)
        course = Course.query.get_or_404(content.course_id)
        
        # Only the instructor who created the course can delete its content
        if course.instructor_id != current_user.id:
            flash('You can only delete content for courses you have created.', 'danger')
            abort(403)
        
        # Delete file if exists
        if content.file_path and os.path.exists(content.file_path):
            os.remove(content.file_path)
        
        db.session.delete(content)
        db.session.commit()
        flash('Content deleted successfully!', 'success')
        return redirect(url_for('manage_content', course_id=course.id))
    
    # Quiz routes
    @app.route('/courses/<int:course_id>/quizzes', methods=['GET', 'POST'])
    @instructor_required
    def manage_quizzes(course_id):
        course = Course.query.get_or_404(course_id)
        # Only the instructor who created the course can manage its quizzes
        if course.instructor_id != current_user.id:
            flash('You can only manage quizzes for courses you have created.', 'danger')
            abort(403)
        
        form = QuizForm()
        if form.validate_on_submit():
            quiz = Quiz(
                course_id=course.id,
                title=form.title.data,
                description=form.description.data,
                time_limit=form.time_limit.data,
                passing_score=form.passing_score.data
            )
            db.session.add(quiz)
            db.session.commit()
            flash('Quiz created successfully!', 'success')
            return redirect(url_for('edit_quiz', quiz_id=quiz.id))
        
        quizzes = Quiz.query.filter_by(course_id=course.id).all()
        return render_template('courses/edit.html', form=form, course=course, quizzes=quizzes, active_tab='quizzes')
    
    @app.route('/quizzes/<int:quiz_id>/edit', methods=['GET', 'POST'])
    @instructor_required
    def edit_quiz(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)
        course = Course.query.get_or_404(quiz.course_id)
        
        # Only the instructor who created the course can edit quizzes
        if course.instructor_id != current_user.id:
            flash('You can only edit quizzes for courses you have created.', 'danger')
            abort(403)
        
        form = QuestionForm()
        if form.validate_on_submit():
            question = Question(
                quiz_id=quiz.id,
                text=form.text.data,
                question_type=form.question_type.data,
                points=form.points.data
            )
            db.session.add(question)
            db.session.commit()
            
            # For true/false questions, add answers automatically
            if form.question_type.data == 'true_false':
                true_answer = Answer(question_id=question.id, text='True', is_correct=False)
                false_answer = Answer(question_id=question.id, text='False', is_correct=False)
                db.session.add_all([true_answer, false_answer])
                db.session.commit()
            
            flash('Question added successfully!', 'success')
            return redirect(url_for('edit_question', question_id=question.id))
        
        questions = Question.query.filter_by(quiz_id=quiz.id).all()
        return render_template('courses/quiz.html', quiz=quiz, form=form, questions=questions, course=course)
    
    @app.route('/questions/<int:question_id>/edit', methods=['GET', 'POST'])
    @instructor_required
    def edit_question(question_id):
        question = Question.query.get_or_404(question_id)
        quiz = Quiz.query.get_or_404(question.quiz_id)
        course = Course.query.get_or_404(quiz.course_id)
        
        # Only the instructor who created the course can edit quiz questions
        if course.instructor_id != current_user.id:
            flash('You can only edit questions for courses you have created.', 'danger')
            abort(403)
        
        form = AnswerForm()
        if form.validate_on_submit() and question.question_type != 'short_answer':
            answer = Answer(
                question_id=question.id,
                text=form.text.data,
                is_correct=form.is_correct.data
            )
            db.session.add(answer)
            db.session.commit()
            flash('Answer added successfully!', 'success')
            return redirect(url_for('edit_question', question_id=question.id))
        
        answers = Answer.query.filter_by(question_id=question.id).all()
        return render_template('courses/quiz.html', question=question, form=form, 
                              answers=answers, quiz=quiz, course=course)
    
    @app.route('/questions/<int:question_id>/delete', methods=['POST'])
    @instructor_required
    def delete_question(question_id):
        question = Question.query.get_or_404(question_id)
        quiz_id = question.quiz_id
        quiz = Quiz.query.get_or_404(quiz_id)
        course = Course.query.get_or_404(quiz.course_id)
        
        # Only the instructor who created the course can delete quiz questions
        if course.instructor_id != current_user.id:
            flash('You can only delete questions for courses you have created.', 'danger')
            abort(403)
        
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully!', 'success')
        return redirect(url_for('edit_quiz', quiz_id=quiz_id))
    
    @app.route('/answers/<int:answer_id>/delete', methods=['POST'])
    @instructor_required
    def delete_answer(answer_id):
        answer = Answer.query.get_or_404(answer_id)
        question_id = answer.question_id
        question = Question.query.get_or_404(question_id)
        quiz = Quiz.query.get_or_404(question.quiz_id)
        course = Course.query.get_or_404(quiz.course_id)
        
        # Only the instructor who created the course can delete quiz answers
        if course.instructor_id != current_user.id:
            flash('You can only delete answers for courses you have created.', 'danger')
            abort(403)
        
        db.session.delete(answer)
        db.session.commit()
        flash('Answer deleted successfully!', 'success')
        return redirect(url_for('edit_question', question_id=question_id))
    
    @app.route('/quizzes/<int:quiz_id>/take', methods=['GET', 'POST'])
    @login_required
    def take_quiz(quiz_id):
        quiz = Quiz.query.get_or_404(quiz_id)
        course = Course.query.get_or_404(quiz.course_id)
        
        # Check if user is enrolled
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id, 
            course_id=course.id
        ).first()
        
        if not enrollment and not current_user.is_instructor():
            flash('You need to be enrolled in this course to take the quiz.', 'warning')
            return redirect(url_for('view_course', course_id=course.id))
        
        # Check for existing attempts
        existing_attempt = QuizAttempt.query.filter_by(
            quiz_id=quiz.id,
            student_id=current_user.id,
            completed=False
        ).first()
        
        if existing_attempt:
            # Continue with existing attempt
            attempt = existing_attempt
        else:
            # Create a new attempt
            attempt = QuizAttempt(
                quiz_id=quiz.id,
                student_id=current_user.id,
                started_at=datetime.utcnow()
            )
            db.session.add(attempt)
            db.session.commit()
        
        form = QuizAttemptForm()
        questions = Question.query.filter_by(quiz_id=quiz.id).all()
        
        if form.validate_on_submit():
            score = 0
            total_points = sum(q.points for q in questions)
            
            for question in questions:
                # Get submitted answer for the question
                if question.question_type == 'multiple_choice':
                    selected_answer_id = request.form.get(f'question_{question.id}')
                    if selected_answer_id:
                        selected_answer = Answer.query.get(selected_answer_id)
                        if selected_answer and selected_answer.is_correct:
                            score += question.points
                elif question.question_type == 'true_false':
                    selected_value = request.form.get(f'question_{question.id}')
                    correct_value = next((a.text for a in question.answers if a.is_correct), None)
                    if selected_value == correct_value:
                        score += question.points
                elif question.question_type == 'short_answer':
                    # For simplicity, we're assuming the instructor would manually grade these
                    pass
            
            # Calculate percentage score
            percentage_score = (score / total_points * 100) if total_points > 0 else 0
            
            # Update the attempt
            attempt.score = percentage_score
            attempt.completed = True
            attempt.completed_at = datetime.utcnow()
            db.session.commit()
            
            # Update course progress
            calculate_progress(enrollment)
            
            flash(f'Quiz submitted! Your score: {percentage_score:.2f}%', 'info')
            return redirect(url_for('view_course', course_id=course.id))
        
        return render_template('courses/quiz.html', quiz=quiz, questions=questions, 
                              form=form, attempt=attempt, course=course, taking=True)
    
    # Discussion forum routes
    @app.route('/courses/<int:course_id>/discussions')
    @login_required
    def course_discussions(course_id):
        course = Course.query.get_or_404(course_id)
        
        # Check if user is enrolled or is instructor/admin
        if not current_user.is_instructor():
            enrollment = Enrollment.query.filter_by(
                student_id=current_user.id, 
                course_id=course.id
            ).first()
            
            if not enrollment:
                flash('You need to be enrolled in this course to access discussions.', 'warning')
                return redirect(url_for('view_course', course_id=course.id))
        
        discussions = Discussion.query.filter_by(course_id=course.id).order_by(Discussion.created_at.desc()).all()
        form = DiscussionForm()
        
        return render_template('forum/index.html', course=course, discussions=discussions, form=form)
    
    @app.route('/courses/<int:course_id>/discussions/create', methods=['POST'])
    @login_required
    def new_thread(course_id):
        course = Course.query.get_or_404(course_id)
        
        # Check if user is enrolled or is instructor/admin
        if not current_user.is_instructor():
            enrollment = Enrollment.query.filter_by(
                student_id=current_user.id, 
                course_id=course.id
            ).first()
            
            if not enrollment:
                flash('You need to be enrolled in this course to create discussions.', 'warning')
                return redirect(url_for('view_course', course_id=course.id))
        
        form = DiscussionForm()
        if form.validate_on_submit():
            discussion = Discussion(
                course_id=course.id,
                author_id=current_user.id,
                title=form.title.data,
                content=form.content.data
            )
            db.session.add(discussion)
            db.session.commit()
            flash('Discussion created successfully!', 'success')
        
        return redirect(url_for('course_discussions', course_id=course.id))
    
    @app.route('/discussions/<int:thread_id>', methods=['GET', 'POST'])
    @login_required
    def view_thread(thread_id):
        discussion = Discussion.query.get_or_404(thread_id)
        course = Course.query.get_or_404(discussion.course_id)
        
        # Check if user is enrolled or is instructor/admin
        if not current_user.is_instructor():
            enrollment = Enrollment.query.filter_by(
                student_id=current_user.id, 
                course_id=course.id
            ).first()
            
            if not enrollment:
                flash('You need to be enrolled in this course to view discussions.', 'warning')
                return redirect(url_for('view_course', course_id=course.id))
        
        form = CommentForm()
        if form.validate_on_submit():
            comment = Comment(
                discussion_id=discussion.id,
                author_id=current_user.id,
                content=form.content.data
            )
            db.session.add(comment)
            db.session.commit()
            flash('Comment added successfully!', 'success')
            return redirect(url_for('view_thread', thread_id=discussion.id))
        
        comments = Comment.query.filter_by(discussion_id=discussion.id).order_by(Comment.created_at).all()
        
        return render_template('forum/topic.html', discussion=discussion, 
                              comments=comments, form=form, course=course)
    
    # Payment routes
    @app.route('/courses/<int:course_id>/checkout')
    @login_required
    def checkout(course_id):
        course = Course.query.get_or_404(course_id)
        
        # Check if already enrolled
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id, 
            course_id=course.id
        ).first()
        
        if enrollment:
            flash('You are already enrolled in this course.', 'info')
            return redirect(url_for('view_course', course_id=course.id))
        
        return render_template('payment/checkout.html', course=course)
    
    @app.route('/create-checkout-session/<int:course_id>', methods=['POST'])
    @login_required
    def create_checkout_session(course_id):
        course = Course.query.get_or_404(course_id)
        
        # Set the domain to use for redirection
        YOUR_DOMAIN = request.host_url.rstrip('/')
        
        try:
            # Create a Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': course.title,
                                'description': course.description[:100] + '...' if len(course.description) > 100 else course.description,
                            },
                            'unit_amount': int(course.price * 100),  # Stripe requires amount in cents
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=YOUR_DOMAIN + url_for('payment_success', course_id=course.id),
                cancel_url=YOUR_DOMAIN + url_for('payment_cancel', course_id=course.id),
                metadata={
                    'course_id': course.id,
                    'user_id': current_user.id
                }
            )
            
            # Create a pending payment record
            payment = Payment(
                user_id=current_user.id,
                course_id=course.id,
                amount=course.price,
                payment_id=checkout_session.id,
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            flash('An error occurred while processing your payment.', 'danger')
            return redirect(url_for('view_course', course_id=course.id))
    
    @app.route('/payment/success/<int:course_id>')
    @login_required
    def payment_success(course_id):
        course = Course.query.get_or_404(course_id)
        
        # Update payment status
        payment = Payment.query.filter_by(
            user_id=current_user.id,
            course_id=course.id,
            status='pending'
        ).first()
        
        if payment:
            payment.status = 'completed'
            
            # Create enrollment
            enrollment = Enrollment(
                student_id=current_user.id,
                course_id=course.id
            )
            db.session.add(enrollment)
            db.session.commit()
            
            flash('Payment successful! You are now enrolled in the course.', 'success')
        else:
            flash('Course enrollment processed', 'info')
        
        return render_template('payment/success.html', course=course)
    
    @app.route('/payment/cancel/<int:course_id>')
    @login_required
    def payment_cancel(course_id):
        course = Course.query.get_or_404(course_id)
        
        # Update payment status to failed
        payment = Payment.query.filter_by(
            user_id=current_user.id,
            course_id=course.id,
            status='pending'
        ).first()
        
        if payment:
            payment.status = 'failed'
            db.session.commit()
        
        flash('Payment was cancelled.', 'warning')
        return render_template('payment/cancel.html', course=course)
    
    # Admin routes
    @app.route('/admin/users')
    @admin_required
    def admin_users():
        users = User.query.all()
        return render_template('dashboard/admin.html', users=users, active_tab='users')
    
    @app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_user(user_id):
        user = User.query.get_or_404(user_id)
        form = AdminUserForm()
        
        if form.validate_on_submit():
            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        elif request.method == 'GET':
            form.username.data = user.username
            form.email.data = user.email
            form.role.data = user.role
        
        return render_template('dashboard/admin.html', form=form, user=user, active_tab='edit_user')
    
    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_user(user_id):
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('You cannot delete your own account!', 'danger')
            return redirect(url_for('admin_users'))
        
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/courses')
    @admin_required
    def admin_courses():
        courses = Course.query.all()
        return render_template('dashboard/admin.html', courses=courses, active_tab='courses')
    
    @app.route('/admin/payments')
    @admin_required
    def admin_payments():
        payments = Payment.query.all()
        return render_template('dashboard/admin.html', payments=payments, active_tab='payments')
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', error_code=404, error_message='Page not found'), 404
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', error_code=403, error_message='Forbidden'), 403
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error_code=500, error_message='Server error'), 500
    
    # Helper route for file uploads
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
