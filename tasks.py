from app import db
from models import Post, Community, CommunityAnalytics, GenericComment
from datetime import datetime, date, time
from sqlalchemy import func

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


def snapshot_community_analytics(app):
    """
    Takes a snapshot of key metrics for all communities for the day.
    """
    with app.app_context():
        print(f"[{datetime.now()}] --- Running Community Analytics Snapshot ---")

        try:
            communities = Community.query.all()
            today = date.today()

            for community in communities:
                member_count = community.memberships.count()

                # Calculate posts and comments for today
                start_of_day = datetime.combine(today, time.min)
                end_of_day = datetime.combine(today, time.max)

                daily_posts = Post.query.filter(
                    Post.community_id == community.id,
                    Post.timestamp.between(start_of_day, end_of_day)
                ).count()

                daily_comments = GenericComment.query.join(Post).filter(
                    Post.community_id == community.id,
                    GenericComment.timestamp.between(start_of_day, end_of_day)
                ).count()

                # Create or update the snapshot for today
                snapshot = CommunityAnalytics.query.filter_by(community_id=community.id, date=today).first()
                if not snapshot:
                    snapshot = CommunityAnalytics(community_id=community.id, date=today)
                    db.session.add(snapshot)

                snapshot.member_count = member_count
                snapshot.daily_posts = daily_posts
                snapshot.daily_comments = daily_comments

            db.session.commit()
            print(f"Successfully snapshotted analytics for {len(communities)} communities.")

        except Exception as e:
            print(f"An error occurred during community analytics snapshot: {e}")
            db.session.rollback()
        finally:
            print("--- Community Analytics Snapshot finished ---")
