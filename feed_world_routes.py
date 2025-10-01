from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Post, User, Status, Like, GenericComment, Community, ReportedPost, follow
from werkzeug.utils import secure_filename
import os
from utils import save_upload_file

feed = Blueprint('feed', __name__)

@feed.route('/feed')
@login_required
def home_feed():
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = 'iphone' in user_agent or 'android' in user_agent or 'mobi' in user_agent

    followed_users_ids = [user.id for user in current_user.followed]
    posts = Post.query.filter(Post.user_id.in_(followed_users_ids)).order_by(Post.timestamp.desc()).all()

    if is_mobile:
        return render_template('feed/home_mobile.html', posts=posts)
    else:
        active_stories_users = db.session.query(User).join(Status).filter(Status.is_story == True, Status.expires_at > db.func.now()).distinct().all()
        return render_template('feed/home.html', posts=posts, stories_by_user=active_stories_users)

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

@feed.route('/add_story', methods=['POST'])
@login_required
def add_story():
    story_text = request.form.get('story_text')
    media_file = request.files.get('story_media')

    if not story_text and not media_file:
        flash('Please enter text or upload a file for your story.', 'danger')
        return redirect(url_for('feed.home_feed'))

    if story_text:
        new_story = Status(user_id=current_user.id, content_type='text', content=story_text, is_story=True)
    else:
        folder = 'images' if media_file.mimetype.startswith('image') else 'videos'
        saved_path = save_upload_file(media_file, folder)
        new_story = Status(user_id=current_user.id, content_type=media_file.mimetype, content=saved_path, is_story=True)

    db.session.add(new_story)
    db.session.commit()
    flash('Your story has been added!', 'success')
    return redirect(url_for('feed.home_feed'))

@feed.route('/api/stories/<int:user_id>')
@login_required
def get_stories(user_id):
    user = User.query.get_or_404(user_id)
    stories = Status.query.filter(Status.user_id == user_id, Status.is_story == True, Status.expires_at > db.func.now()).order_by(Status.created_at.asc()).all()
    stories_data = [{'id': story.id, 'content_type': story.content_type, 'content_url': url_for('static', filename=story.content)} for story in stories]
    user_data = {'name': user.name, 'avatar_url': url_for('static', filename='profile_pics/' + user.profile_pic)}
    return jsonify({'user': user_data, 'stories': stories_data})

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
