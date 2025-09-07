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
    app = Flask(__name__)

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

    from feed_world_routes import feed_bp
    app.register_blueprint(feed_bp)

    # Register chat events
    from chat_events import register_chat_events
    register_chat_events(socketio)

    # Register custom Jinja filters
    app.jinja_env.filters['secure_embeds'] = secure_embeds_filter

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

    @app.cli.command("seed-departments")
    def seed_departments():
        """Seeds the database with the 14 official departments."""
        from models import Department
        department_names = [
            "Educational", "Innovation & Technology", "Health & Wellness",
            "Leadership & Governance", "Creativity & Arts", "Entrepreneurship & Enterprise",
            "Research & Development", "Community & Social Impact", "Ethics & Values",
            "Science & Environment", "Sports & Physical Development",
            "Spiritual & Moral Development", "Digital Media & Communication",
            "Campus Life & Student Affairs"
        ]
        for name in department_names:
            if not Department.query.filter_by(name=name).first():
                department = Department(name=name, description=f"The official {name} department.")
                db.session.add(department)
        db.session.commit()
        print("Departments seeded successfully.")

    @app.cli.command("verify-data")
    def verify_data():
        """Verifies that the initial data has been seeded."""
        from models import Department
        departments = Department.query.all()
        print(f"Found {len(departments)} departments:")
        for dept in departments:
            print(f"- {dept.name}")

    return app

# Create a default app instance for discoverability by Flask CLI
app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
