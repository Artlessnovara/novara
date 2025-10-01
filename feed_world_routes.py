from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Post, User, Like, GenericComment, Community, ReportedPost, follow as follow_table, Story, StoryView, CloseFriend, MutedStory, BlockedUser
from werkzeug.utils import secure_filename
import os
from utils import save_upload_file
from sqlalchemy.orm import aliased
from datetime import datetime

feed = Blueprint('feed', __name__)

@feed.route('/feed')
@login_required
def home_feed():
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = 'iphone' in user_agent or 'android' in user_agent or 'mobi' in user_agent

    followed_users_ids = [user.id for user in current_user.followed]
    posts = Post.query.filter(Post.user_id.in_(followed_users_ids)).order_by(Post.timestamp.desc()).all()

    # Story fetching logic
    muted_story_user_ids = [m.muted_id for m in current_user.muted_stories_users]
    blocked_user_ids = [b.blocked_id for b in current_user.blocking]
    blocked_by_user_ids = [b.blocker_id for b in current_user.blocked_by]

    exclude_user_ids = set(muted_story_user_ids + blocked_user_ids + blocked_by_user_ids)

    # Subquery for friends
    friends_subquery = db.session.query(follow_table.c.followed_id).filter(follow_table.c.follower_id == current_user.id).subquery()

    # Subquery for close friends
    close_friends_subquery = db.session.query(CloseFriend.close_friend_id).filter(CloseFriend.user_id == current_user.id).subquery()

    # Fetch stories based on privacy
    stories_query = Story.query.filter(
        Story.expires_at > datetime.utcnow(),
        Story.user_id.notin_(exclude_user_ids),
        (
            (Story.privacy == 'public') |
            (Story.privacy == 'friends' and Story.user_id.in_(friends_subquery)) |
            (Story.privacy == 'close_friends' and Story.user_id.in_(close_friends_subquery)) |
            (Story.user_id == current_user.id) # Always see your own stories
        )
    ).order_by(Story.created_at.desc()).all()

    # Group stories by user
    stories_by_user = {}
    for story in stories_query:
        if story.author not in stories_by_user:
            stories_by_user[story.author] = []
        stories_by_user[story.author].append(story)

    if is_mobile:
        return render_template('feed/home_mobile.html', posts=posts, stories_by_user=stories_by_user)
    else:
        return render_template('feed/home.html', posts=posts, stories_by_user=stories_by_user)

@feed.route('/feed/search_mobile')
@login_required
def search_mobile():
    return render_template('feed/search_mobile.html')

@feed.route('/feed/create_post', methods=['GET'])
@login_required
def create_post_page():
    # This route will display the form for creating a post on mobile
    return render_template('feed/create_post_mobile.html')

@feed.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    media_files = request.files.getlist('media')
    if not content and not media_files:
        flash('Post cannot be empty.', 'danger')
        return redirect(url_for('feed.home_feed'))

    media_urls = []
    media_type = None
    if media_files and media_files[0].filename != '':
        for file in media_files:
            folder = 'images' if file.mimetype.startswith('image') else 'videos'
            saved_path = save_upload_file(file, folder)
            media_urls.append(saved_path)
        if len(media_urls) > 1:
            media_type = 'images'
        elif len(media_urls) == 1:
            media_type = 'image' if media_files[0].mimetype.startswith('image') else 'video'

    new_post = Post(user_id=current_user.id, content=content, media_type=media_type, media_url=media_urls)
    db.session.add(new_post)
    db.session.commit()
    flash('Your post has been created!', 'success')
    return redirect(url_for('feed.home_feed'))

@feed.route('/create_story', methods=['POST'])
@login_required
def create_story():
    media_file = request.files.get('story_media')
    privacy = request.form.get('privacy', 'public')

    if not media_file:
        flash('Please upload a file for your story.', 'danger')
        return redirect(url_for('feed.home_feed'))

    media_type = 'image' if media_file.mimetype.startswith('image') else 'video'
    folder = 'images' if media_type == 'image' else 'videos'
    saved_path = save_upload_file(media_file, folder)

    new_story = Story(
        user_id=current_user.id,
        media_type=media_type,
        media_url=saved_path,
        privacy=privacy
    )
    db.session.add(new_story)
    db.session.commit()
    flash('Your story has been added!', 'success')
    return redirect(url_for('feed.home_feed'))

@feed.route('/api/stories/<int:user_id>')
@login_required
def get_stories(user_id):
    # This function should now check privacy before returning stories
    user = User.query.get_or_404(user_id)

    # Basic privacy check: are you the user, or are you friends?
    # More complex logic will be needed for 'close_friends'
    can_view = (user.id == current_user.id) or current_user.is_following(user)

    if not can_view:
        # Check if there are any public stories
        stories = Story.query.filter_by(user_id=user_id, privacy='public').filter(Story.expires_at > datetime.utcnow()).order_by(Story.created_at.asc()).all()
    else:
        # A more comprehensive check is needed here, similar to the main feed
        stories = Story.query.filter_by(user_id=user_id).filter(Story.expires_at > datetime.utcnow()).order_by(Story.created_at.asc()).all()

    stories_data = [{'id': story.id, 'user_id': story.user_id, 'media_type': story.media_type, 'media_url': url_for('static', filename=story.media_url)} for story in stories]

    # Mark stories as viewed
    for story in stories:
        if not StoryView.query.filter_by(story_id=story.id, user_id=current_user.id).first():
            view = StoryView(story_id=story.id, user_id=current_user.id)
            db.session.add(view)
    db.session.commit()

    user_data = {'name': user.name, 'avatar_url': url_for('static', filename='profile_pics/' + user.profile_pic)}
    return jsonify({'user': user_data, 'stories': stories_data})

@feed.route('/api/stories/<int:story_id>/viewers')
@login_required
def get_story_viewers(story_id):
    story = Story.query.get_or_404(story_id)
    if story.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    viewers = User.query.join(StoryView).filter(StoryView.story_id == story_id).all()
    viewers_data = [{'id': v.id, 'name': v.name, 'avatar_url': url_for('static', filename='profile_pics/' + v.profile_pic)} for v in viewers]

    return jsonify({'status': 'success', 'viewers': viewers_data})

@feed.route('/stories/mute/<int:user_id>', methods=['POST'])
@login_required
def mute_story(user_id):
    if user_id == current_user.id:
        return jsonify({'status': 'error', 'message': 'You cannot mute yourself.'}), 400

    muted_link = MutedStory.query.filter_by(muter_id=current_user.id, muted_id=user_id).first()
    if not muted_link:
        muted_link = MutedStory(muter_id=current_user.id, muted_id=user_id)
        db.session.add(muted_link)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'User stories muted.'})
    return jsonify({'status': 'info', 'message': 'User stories already muted.'})

@feed.route('/stories/unmute/<int:user_id>', methods=['POST'])
@login_required
def unmute_story(user_id):
    muted_link = MutedStory.query.filter_by(muter_id=current_user.id, muted_id=user_id).first()
    if muted_link:
        db.session.delete(muted_link)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'User stories unmuted.'})
    return jsonify({'status': 'info', 'message': 'User stories were not muted.'})

@feed.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    if user_to_follow == current_user:
        flash('You cannot follow yourself.', 'warning')
        return redirect(request.referrer or url_for('feed.home_feed'))
    current_user.follow(user_to_follow)
    db.session.commit()
    flash(f'You are now following {user_to_follow.name}.', 'success')
    return redirect(request.referrer or url_for('feed.home_feed'))

@feed.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    user_to_unfollow = User.query.get_or_404(user_id)
    if user_to_unfollow == current_user:
        flash('You cannot unfollow yourself.', 'warning')
        return redirect(request.referrer or url_for('feed.home_feed'))
    current_user.unfollow(user_to_unfollow)
    db.session.commit()
    flash(f'You have unfollowed {user_to_unfollow.name}.', 'success')
    return redirect(request.referrer or url_for('feed.home_feed'))

@feed.route('/community/create', methods=['POST'])
@login_required
def create_community():
    name = request.form.get('name')
    description = request.form.get('description')
    if not name:
        flash('Community name is required.', 'danger')
        return redirect(request.referrer or url_for('feed.home_feed'))
    community = Community(name=name, description=description, creator=current_user)
    db.session.add(community)
    db.session.commit()
    flash('Community created successfully!', 'success')
    return redirect(url_for('feed.home_feed')) # Or a new community page

@feed.route('/report_post', methods=['POST'])
@login_required
def report_post():
    post_id = request.form.get('post_id')
    reason = request.form.get('reason')
    post = Post.query.get_or_404(post_id)
    report = ReportedPost(post_id=post.id, reported_by_id=current_user.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Post has been reported.', 'success')
    return redirect(url_for('feed.home_feed'))

@feed.route('/search')
@login_required
def search():
    query = request.args.get('q')
    if not query:
        return redirect(url_for('feed.home_feed'))

    # Simple search for users and posts
    users = User.query.filter(User.name.ilike(f'%{query}%')).all()
    posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()

    return render_template('feed/search_results.html', query=query, users=users, posts=posts)
