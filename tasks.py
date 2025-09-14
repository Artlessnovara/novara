from app import db
from models import Post
from datetime import datetime

def publish_scheduled_posts(app):
    """
    Checks for scheduled posts that are due and publishes them.
    This function is designed to be called by a scheduler within the app context.
    """
    with app.app_context():
        print(f"[{datetime.now()}] --- Running Scheduled Post Publisher ---")

        try:
            due_posts = Post.query.filter(
                Post.post_status == 'scheduled',
                Post.scheduled_for <= datetime.utcnow()
            ).all()

            if not due_posts:
                print("No posts to publish at this time.")
                return

            for post in due_posts:
                print(f"Publishing post ID: {post.id} (Scheduled for: {post.scheduled_for})")
                post.post_status = 'published'

            db.session.commit()
            print(f"Successfully published {len(due_posts)} posts.")

        except Exception as e:
            print(f"An error occurred: {e}")
            db.session.rollback()
        finally:
            print("--- Publisher finished ---")
