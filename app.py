from flask import Flask
from extensions import db, login_manager, socketio
from models import User, ChatRoom, ChatMessage, Notification
import os
import click
from flask_login import current_user
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from markupsafe import Markup
from flask_migrate import Migrate
from push_notifications import initialize_firebase
from apscheduler.schedulers.background import BackgroundScheduler
from tasks import publish_scheduled_posts, snapshot_community_analytics
import atexit
import humanize

def secure_embeds_filter(html_content):
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    for embed_div in soup.find_all('div', class_='secure-embed'):
        data_type = embed_div.get('data-type')
        data_id = embed_div.get('data-id')

        iframe = None
        if data_type == 'youtube' and data_id:
            iframe_src = f"https://www.youtube-nocookie.com/embed/{data_id}"
            iframe = soup.new_tag('iframe', src=iframe_src, width="560", height="315", frameborder="0", allowfullscreen=True)
        elif data_type == 'gdrive' and data_id:
            iframe_src = f"https://drive.google.com/file/d/{data_id}/preview"
            iframe = soup.new_tag('iframe', src=iframe_src, width="100%", height="480")

        if iframe:
            embed_div.replace_with(iframe)

    return Markup(str(soup))

def create_app(config_object=None):
    print("Creating app...")
    app = Flask(__name__)
    print("Flask app created.")

    if config_object:
        app.config.from_object(config_object)
    else:
        # Default configuration
        app.config.from_mapping(
            SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(app.instance_path, 'app.db'),
            SQLALCHEMY_TRACK_MODIFICATIONS = False,
            SECRET_KEY = 'dev', # Change for production
            MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
        )

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    migrate = Migrate(app, db)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from instructor_routes import instructor_bp
    app.register_blueprint(instructor_bp)

    from admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    from feed_world_routes import feed as feed_blueprint
    app.register_blueprint(feed_blueprint, url_prefix='/feed')

    from more_routes import more_bp
    app.register_blueprint(more_bp)

    from page_routes import page_bp
    app.register_blueprint(page_bp)

    from glooba_routes import glooba_bp
    app.register_blueprint(glooba_bp)

    # Register chat events
    from chat_events import register_chat_events
    register_chat_events(socketio)

    # Register custom Jinja filters
    app.jinja_env.filters['secure_embeds'] = secure_embeds_filter
    app.jinja_env.filters['naturaltime'] = humanize.naturaltime

    # Initialize Firebase Admin SDK
    with app.app_context():
        initialize_firebase()

    @app.context_processor
    def inject_notifications():
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            return dict(unread_notification_count=unread_count)
        return dict(unread_notification_count=0)

    def from_json_filter(value, default=None):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default
    app.jinja_env.filters['fromjson'] = from_json_filter

    @app.cli.command("init-db")
    def init_db():
        """Creates the database and the general chat room."""
        db.create_all()
        general_room = ChatRoom.query.filter_by(name='General').first()
        if not general_room:
            general_room = ChatRoom(name='General', room_type='public', description='A place for everyone to chat.')
            db.session.add(general_room)
        elif general_room.room_type != 'public':
            general_room.room_type = 'public'
        db.session.commit()
        print("Database initialized.")

    @app.cli.command("reset-db")
    def reset_db():
        """Drops and creates all tables."""
        db.drop_all()
        db.create_all()
        print("Database reset.")

    @app.cli.command("clean-chat-history")
    @click.option("--days", default=30, type=int, help="Delete messages older than this many days.")
    def clean_chat_history(days):
        """Deletes old chat messages from the database."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        num_deleted = db.session.query(ChatMessage).filter(ChatMessage.timestamp < cutoff_date).delete()
        db.session.commit()

        print(f"Deleted {num_deleted} messages older than {days} days.")

    @app.cli.command("create-admin")
    @click.option("--name", required=True, help="The name of the admin user.")
    @click.option("--email", required=True, help="The email address of the admin user.")
    @click.option("--password", required=True, help="The password for the admin user.")
    def create_admin(name, email, password):
        """Creates a new admin user."""
        if User.query.filter_by(email=email).first():
            print(f"Error: User with email {email} already exists.")
            return

        admin = User(
            name=name,
            email=email,
            role='admin',
            approved=True
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user {name} ({email}) created successfully.")

    @app.cli.command("seed-db")
    def seed_db():
        """Seeds the database with sample data."""
        from models import Post, Category, Course, Module, Lesson, CourseComment, LibraryMaterial, GenericComment, Like, Share, Status, Assignment, AssignmentSubmission, Badge, Certificate, Enrollment
        # Clear existing data
        db.drop_all()
        db.create_all()

        # Create users
        admin_user = User(name='Admin User', email='admin@example.com', role='admin', approved=True)
        admin_user.set_password('password')
        instructor1 = User(name='John Doe', email='john@example.com', role='instructor', approved=True)
        instructor1.set_password('password')
        instructor2 = User(name='Jane Smith', email='jane@example.com', role='instructor', approved=False) # Unapproved
        instructor2.set_password('password')
        student1 = User(name='Test Student', email='student@example.com', role='student', approved=True)
        student1.set_password('password')
        db.session.add_all([admin_user, instructor1, instructor2, student1])
        db.session.commit()

        # Create posts for the feed
        long_post_content = "This is a very long post to test the 'See More' functionality. " * 10
        post1 = Post(content="This is a test post for the feed!", author=instructor1)
        post2 = Post(content=long_post_content, author=student1)
        post3 = Post(content="A post with a single image.", author=instructor1, media_type='image', media_url=['images/course1.jpg'])
        post4 = Post(content="A post with two images.", author=student1, media_type='images', media_url=['images/course2.jpg', 'images/course3.jpg'])
        post5 = Post(content="A post with three images.", author=instructor1, media_type='images', media_url=['images/course1.jpg', 'images/course2.jpg', 'images/course3.jpg'])
        db.session.add_all([post1, post2, post3, post4, post5])
        db.session.commit()

        # Add comments to posts
        comment1 = GenericComment(target_id=post1.id, target_type='post', user_id=student1.id, content='Great post!')
        comment2 = GenericComment(target_id=post1.id, target_type='post', user_id=instructor1.id, content='Thanks!')
        db.session.add_all([comment1, comment2])
        db.session.commit()

        # Add likes to posts
        like1 = Like(user_id=student1.id, target_type='post', target_id=post1.id)
        like2 = Like(user_id=instructor1.id, target_type='post', target_id=post2.id)
        db.session.add_all([like1, like2])
        db.session.commit()

        # Add shares to posts
        share1 = Share(user_id=student1.id, post_id=post1.id)
        db.session.add(share1)
        db.session.commit()

        # Add a text story
        story1 = Status(user_id=student1.id, content_type='text', content='This is a text story!', is_story=True)
        db.session.add(story1)
        db.session.commit()

        # Create categories
        cat1 = Category(name='Web Development')
        cat2 = Category(name='Data Science')
        cat3 = Category(name='Business')
        db.session.add_all([cat1, cat2, cat3])
        db.session.commit()

        # Create courses
        c1 = Course(title='Introduction to Flask', description='A beginner friendly course on Flask.', instructor_id=instructor1.id, category_id=cat1.id, price_naira=10000, approved=True)
        c2 = Course(title='Advanced Python', description='Take your Python skills to the next level.', instructor_id=instructor1.id, category_id=cat1.id, price_naira=15000, approved=True)
        c3 = Course(title='Data Analysis with Pandas', description='Learn data analysis.', instructor_id=instructor2.id, category_id=cat2.id, price_naira=20000, approved=True)
        c4 = Course(title='Marketing 101', description='Basics of marketing.', instructor_id=instructor2.id, category_id=cat3.id, price_naira=5000, approved=False)
        db.session.add_all([c1, c2, c3, c4])
        db.session.commit()

        # Create modules and lessons for Course 1
        mod1_c1 = Module(course_id=c1.id, title='Getting Started', order=1)
        mod2_c1 = Module(course_id=c1.id, title='Building a Basic App', order=2)
        db.session.add_all([mod1_c1, mod2_c1])
        db.session.commit()

        les1_m1 = Lesson(module_id=mod1_c1.id, title='Installation', video_url='https://www.youtube.com/embed/xxxxxxxxxxx', notes='Some notes here.')
        les2_m1 = Lesson(module_id=mod1_c1.id, title='Project Structure', notes='More notes.')
        les1_m2 = Lesson(module_id=mod2_c1.id, title='Hello World', drive_link='https://docs.google.com/document/d/xxxxxxxxxxx/edit?usp=sharing')
        db.session.add_all([les1_m1, les2_m1, les1_m2])
        db.session.commit()

        # Add a course comment
        comment1 = CourseComment(course_id=c1.id, user_id=student1.id, body='This is a great course!', rating=5)
        db.session.add(comment1)
        db.session.commit()

        # Add library materials
        lib1 = LibraryMaterial(uploader_id=instructor1.id, category_id=cat1.id, title='Flask Cheatsheet', price_naira=500, file_path='flask_cheatsheet.pdf', approved=True)
        lib2 = LibraryMaterial(uploader_id=instructor2.id, category_id=cat2.id, title='Data Science Intro', price_naira=1000, file_path='ds_intro.pdf', approved=False)
        db.session.add_all([lib1, lib2])
        db.session.commit()

        # Enroll student in the course
        enrollment1 = Enrollment(user_id=student1.id, course_id=c1.id, status='approved')
        db.session.add(enrollment1)
        db.session.commit()

        # Add an assignment and submission for testing
        assignment1 = Assignment(module_id=mod1_c1.id, title='Setup Your Environment', description='<p>Follow the installation guide to set up your Flask environment.</p>', due_date=datetime.utcnow() + timedelta(days=7))
        db.session.add(assignment1)
        db.session.commit()

        submission1 = AssignmentSubmission(assignment_id=assignment1.id, student_id=student1.id, text_submission='Environment setup complete.', grade='A')
        db.session.add(submission1)
        db.session.commit()

        # Add a badge for the test student
        badge1 = Badge(name='Course Completer', icon_url='https://img.icons8.com/color/48/000000/medal.png', user_id=student1.id)
        db.session.add(badge1)
        db.session.commit()

        # Add a certificate for testing
        certificate1 = Certificate(user_id=student1.id, course_id=c2.id, certificate_uid='test-cert-123', file_path='certificates/sample.pdf')
        db.session.add(certificate1)
        db.session.commit()

        print('Database has been cleared and re-seeded with sample data.')

    # --- Background Scheduler for Scheduled Posts ---
    # This check prevents the scheduler from running twice in debug mode
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(func=publish_scheduled_posts, args=[app], trigger='interval', minutes=1)
        scheduler.add_job(func=snapshot_community_analytics, args=[app], trigger='cron', hour=0) # Run daily at midnight
        scheduler.start()

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

    return app

# Create a default app instance for discoverability by Flask CLI
app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
