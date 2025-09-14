import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import Post, Like, GenericComment, Reel, Community, CommunityMembership, User, Project, CreativeWork, follow, Notification, ReportedPost, Status, Challenge, Vote, Bookmark, PostImpression
from extensions import db
from utils import save_post_media, save_community_cover_image
from sqlalchemy import or_
from sqlalchemy.sql import func
from datetime import datetime, date, timedelta

feed_bp = Blueprint('feed', __name__, url_prefix='/feed')

@feed_bp.route('/')
@login_required
def home():
    """Main feed page with boosted posts."""
    following_ids = [u.id for u in current_user.followed]
    feed_user_ids = following_ids + [current_user.id]

    # 1. Fetch regular posts from followed users and self, respecting privacy
    regular_posts = Post.query.filter(
        Post.post_status == 'published',
        Post.is_boosted == False,
        (
            (Post.privacy == 'public') |
            (Post.privacy == 'followers')
        ),
        Post.user_id.in_(feed_user_ids)
    ).order_by(Post.timestamp.desc()).all()

    # 2. Fetch boosted posts from users not followed (must be public)
    boosted_posts = Post.query.filter(
        Post.post_status == 'published',
        Post.is_boosted == True,
        Post.privacy == 'public',
        Post.user_id.notin_(feed_user_ids)
    ).all()
    random.shuffle(boosted_posts)

    # 3. Inject boosted posts into the feed
    final_feed = []
    boost_interval = 5  # Inject a boosted post every 5 regular posts
    boosted_post_iterator = iter(boosted_posts)

    for i, post in enumerate(regular_posts):
        final_feed.append(post)
        if (i + 1) % boost_interval == 0:
            try:
                boosted_post = next(boosted_post_iterator)
                final_feed.append(boosted_post)
            except StopIteration:
                pass  # No more boosted posts to inject

    # Pre-process posts to include reaction data
    for post in final_feed:
        # Get reaction counts
        reaction_counts = db.session.query(
            Like.reaction_type, func.count(Like.reaction_type)
        ).filter_by(target_type='post', target_id=post.id).group_by(Like.reaction_type).all()
        post.reaction_summary = {r_type: count for r_type, count in reaction_counts}

        # Get current user's reaction
        user_reaction_obj = Like.query.filter_by(
            user_id=current_user.id, target_type='post', target_id=post.id
        ).first()
        post.user_reaction = user_reaction_obj.reaction_type if user_reaction_obj else None


    return render_template('feed/home.html', posts=posts)

@feed_bp.route('/create', methods=['GET'])
@login_required
def create_post_page():
    """Displays the dedicated page for creating a new post."""
    return render_template('feed/create_post.html')

@feed_bp.route('/create_post', methods=['POST'])
@login_required
def create_post():
    """Create a new post, with scheduling for premium users."""
    content = request.form.get('content')
    privacy = request.form.get('privacy', 'public')
    media_file = request.files.get('media')
    community_id = request.form.get('community_id', type=int)
    schedule_time_str = request.form.get('schedule_time')

    if not content:
        flash('Content is required to create a post.', 'danger')
        return redirect(url_for('feed.create_post_page'))

    media_url = None
    media_type = None
    if media_file:
        media_url, media_type = save_post_media(media_file)
        if not media_url:
            flash('Invalid file type or size for media.', 'danger')
            return redirect(url_for('feed.create_post_page'))

    scheduled_for_dt = None
    post_status = 'published'
    flash_message = 'Your post has been created!'

    if current_user.is_premium and schedule_time_str:
        try:
            scheduled_for_dt = datetime.strptime(schedule_time_str, '%Y-%m-%dT%H:%M')
            if scheduled_for_dt > datetime.utcnow():
                post_status = 'scheduled'
                flash_message = f"Your post has been scheduled for {scheduled_for_dt.strftime('%B %d, %Y at %I:%M %p')}."
            else:
                flash('Scheduled time is in the past. Posting immediately.', 'info')
        except ValueError:
            flash('Invalid date format for scheduling.', 'danger')
            return redirect(url_for('feed.create_post_page'))

    new_post = Post(
        user_id=current_user.id,
        content=content,
        media_url=media_url,
        media_type=media_type,
        privacy=privacy,
        community_id=community_id,
        post_status=post_status,
        scheduled_for=scheduled_for_dt
    )
    db.session.add(new_post)
    db.session.commit()

    flash(flash_message, 'success')
    if community_id:
        return redirect(url_for('feed.view_community', community_id=community_id))
    return redirect(url_for('feed.home'))

@feed_bp.route('/communities')
@login_required
def communities():
    """Communities page."""
    all_communities = Community.query.order_by(Community.name).all()
    return render_template('feed/communities.html', communities=all_communities)

@feed_bp.route('/community/create', methods=['POST'])
@login_required
def create_community():
    """Create a new community."""
    name = request.form.get('name')
    description = request.form.get('description')
    cover_image_file = request.files.get('cover_image')

    if not name or not description:
        flash('Name and description are required.', 'danger')
        return redirect(url_for('feed.communities'))

    cover_image_path = None
    if cover_image_file:
        cover_image_path = save_community_cover_image(cover_image_file)
        if not cover_image_path:
            flash('Invalid file type or size for cover image.', 'danger')
            return redirect(url_for('feed.communities'))

    new_community = Community(
        name=name,
        description=description,
        cover_image=cover_image_path,
        created_by_id=current_user.id
    )
    db.session.add(new_community)
    db.session.commit()

    # The creator automatically becomes an admin member
    new_membership = CommunityMembership(
        user_id=current_user.id,
        community_id=new_community.id,
        role='admin'
    )
    db.session.add(new_membership)
    db.session.commit()

    flash('Community created successfully!', 'success')
    return redirect(url_for('feed.view_community', community_id=new_community.id))

@feed_bp.route('/community/<int:community_id>')
@login_required
def view_community(community_id):
    """View a single community and its posts."""
    community = Community.query.get_or_404(community_id)
    posts = community.posts.order_by(Post.timestamp.desc()).all()
    return render_template('feed/view_community.html', community=community, posts=posts)

@feed_bp.route('/community/<int:community_id>/join', methods=['POST'])
@login_required
def join_community(community_id):
    """Join a community."""
    community = Community.query.get_or_404(community_id)

    existing_membership = CommunityMembership.query.filter_by(
        user_id=current_user.id,
        community_id=community.id
    ).first()

    if existing_membership:
        flash('You are already a member of this community.', 'info')
    else:
        new_membership = CommunityMembership(
            user_id=current_user.id,
            community_id=community.id
        )
        db.session.add(new_membership)
        db.session.commit()
        flash(f'You have successfully joined {community.name}!', 'success')

    return redirect(url_for('feed.view_community', community_id=community_id))

@feed_bp.route('/innovation')
@login_required
def innovation():
    """Innovation page."""
    projects = Project.query.order_by(Project.timestamp.desc()).all()
    return render_template('feed/innovation.html', projects=projects)

@feed_bp.route('/project/create', methods=['POST'])
@login_required
def create_project():
    """Create a new project."""
    title = request.form.get('title')
    description = request.form.get('description')

    if not title or not description:
        flash('Title and description are required.', 'danger')
        return redirect(url_for('feed.innovation'))

    new_project = Project(
        title=title,
        description=description,
        user_id=current_user.id
    )
    db.session.add(new_project)
    db.session.commit()

    flash('Your project has been created!', 'success')
    return redirect(url_for('feed.view_project', project_id=new_project.id))

@feed_bp.route('/project/<int:project_id>')
@login_required
def view_project(project_id):
    """View a single project."""
    project = Project.query.get_or_404(project_id)
    return render_template('feed/view_project.html', project=project)

@feed_bp.route('/creativity')
@login_required
def creativity():
    """Creativity page with filtering and search."""
    category = request.args.get('category', 'all')
    query = request.args.get('q', '')
    tag = request.args.get('tag', '')

    works = []
    reels = []
    challenges = []
    top_creators = {}

    # Base query for creative works
    works_query = CreativeWork.query.order_by(CreativeWork.timestamp.desc())

    # Category filtering
    if category == 'art_design':
        works_query = works_query.filter(CreativeWork.work_type.in_(['image', 'video']))
    elif category == 'writing':
        works_query = works_query.filter_by(work_type='writing')
    elif category == 'music_audio':
        works_query = works_query.filter_by(work_type='audio')

    # Search query filtering
    if query:
        search_term = f"%{query}%"
        works_query = works_query.filter(
            or_(
                CreativeWork.title.ilike(search_term),
                CreativeWork.description.ilike(search_term),
                CreativeWork.tags.ilike(search_term)
            )
        )

    # Tag filtering
    if tag:
        works_query = works_query.filter(CreativeWork.tags.ilike(f"%{tag}%"))

    works = works_query.all()

    # Special handling for other tabs
    if category == 'reels':
        reels_query = Reel.query.order_by(Reel.timestamp.desc())
        if query:
            reels_query = reels_query.filter(Reel.caption.ilike(f"%{query}%"))
        reels = reels_query.all()

    elif category == 'challenges':
        challenges = Challenge.query.order_by(Challenge.end_date.desc()).all()

    elif category == 'top_creators':
        # Most Liked Creators
        most_liked = db.session.query(
            User, func.count(Like.id).label('total_likes')
        ).join(CreativeWork, User.id == CreativeWork.user_id)\
         .join(Like, Like.target_id == CreativeWork.id)\
         .filter(Like.target_type == 'creative_work')\
         .group_by(User)\
         .order_by(func.count(Like.id).desc())\
         .limit(10).all()

        # Most Active Creators
        most_active = db.session.query(
            User, func.count(CreativeWork.id).label('total_works')
        ).join(CreativeWork, User.id == CreativeWork.user_id)\
         .group_by(User)\
         .order_by(func.count(CreativeWork.id).desc())\
         .limit(10).all()

        top_creators = {
            'most_liked': most_liked,
            'most_active': most_active
        }

    return render_template('feed/creativity.html',
                           works=works,
                           reels=reels,
                           challenges=challenges,
                           top_creators=top_creators,
                           active_category=category,
                           search_query=query,
                           active_tag=tag)

@feed_bp.route('/creative_work/create', methods=['POST'])
@login_required
def create_creative_work():
    """Create a new creative work."""
    title = request.form.get('title')
    description = request.form.get('description')
    category = request.form.get('category')
    sub_category = request.form.get('sub_category')
    tags = request.form.get('tags')

    if not title:
        flash('Title is required.', 'danger')
        return redirect(url_for('feed.creativity', category=category))

    if category == 'writing':
        if not description:
            flash('Text content is required for a writing post.', 'danger')
            return redirect(url_for('feed.creativity', category=category))

        bg_style = request.form.get('bg_style', 'default')
        style_map = {
            'default': {'bg_color': '#ffffff', 'text_color': '#000000'},
            'dark': {'bg_color': '#333333', 'text_color': '#ffffff'},
            'parchment': {'bg_color': '#fdf5e6', 'text_color': '#5d4037'},
            'blue': {'bg_color': '#e7f3ff', 'text_color': '#0d47a1'}
        }

        new_work = CreativeWork(
            title=title,
            description=description,
            work_type='writing',
            sub_category=sub_category,
            style_options=style_map.get(bg_style),
            tags=tags,
            user_id=current_user.id
        )
    elif category == 'music_audio':
        media_file = request.files.get('media')
        if not media_file:
            flash('An audio file is required.', 'danger')
            return redirect(url_for('feed.creativity', category=category))

        media_url, media_type = save_post_media(media_file)
        if media_type != 'audio':
            flash('Invalid file type. Please upload an audio file.', 'danger')
            return redirect(url_for('feed.creativity', category=category))

        cover_image_url = None
        cover_image_file = request.files.get('cover_image')
        if cover_image_file:
            cover_image_url, _ = save_post_media(cover_image_file)

        new_work = CreativeWork(
            title=title,
            description=description,
            media_url=media_url,
            work_type='audio',
            genre=request.form.get('genre'),
            cover_image_url=cover_image_url,
            tags=tags,
            user_id=current_user.id
        )
    else: # Assumes art_design
        media_file = request.files.get('media')
        if not media_file:
            flash('A media file is required.', 'danger')
            return redirect(url_for('feed.creativity', category=category))

        watermark = request.form.get('watermark')
        watermark_text = current_user.name if watermark else None
        media_url, media_type = save_post_media(media_file, watermark_text=watermark_text)

        if not media_url or media_type not in ['image', 'video']:
            flash('Invalid file type or size for media.', 'danger')
            return redirect(url_for('feed.creativity', category=category))

        new_work = CreativeWork(
            title=title,
            description=description,
            media_url=media_url,
            work_type=media_type,
            sub_category=sub_category,
            tags=tags,
            user_id=current_user.id
        )

    db.session.add(new_work)
    db.session.commit()

    flash('Your creative work has been uploaded!', 'success')
    return redirect(url_for('feed.creativity', category=category))

@feed_bp.route('/creative_work/<int:work_id>')
@login_required
def view_creative_work(work_id):
    """View a single creative work."""
    work = CreativeWork.query.get_or_404(work_id)
    return render_template('feed/view_creative_work.html', work=work)

@feed_bp.route('/profile/')
@feed_bp.route('/profile/<int:user_id>')
@login_required
def profile(user_id=None):
    """User profile page."""
    if user_id is None:
        user = current_user
    else:
        user = User.query.get_or_404(user_id)

    # Fetch user's posts
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()

    return render_template('feed/profile.html', user=user, posts=posts)

@feed_bp.route('/suggestions')
@login_required
def suggestions():
    """Suggestions page."""
    # Suggest users to follow (friends of friends)
    following_ids = [u.id for u in current_user.followed]
    suggested_users = []
    if following_ids:
        suggested_users = db.session.query(User).join(follow, User.id == follow.c.followed_id).filter(
            follow.c.follower_id.in_(following_ids),
            User.id != current_user.id,
            ~User.id.in_(following_ids)
        ).limit(5).all()

    # Suggest communities to join
    suggested_communities = []
    if following_ids:
        suggested_communities = db.session.query(Community).join(CommunityMembership).filter(
            CommunityMembership.user_id.in_(following_ids)
        ).limit(5).all()

    # Suggest projects to view (random for now)
    suggested_projects = Project.query.order_by(func.random()).limit(5).all()

    return render_template('feed/suggestions.html',
                           suggested_users=suggested_users,
                           suggested_communities=suggested_communities,
                           suggested_projects=suggested_projects)

@feed_bp.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    if user_to_follow == current_user:
        flash("You cannot follow yourself.", "warning")
        return redirect(url_for('feed.profile', user_id=user_id))

    current_user.follow(user_to_follow)

    # Create notification
    notification = Notification(
        user_id=user_to_follow.id,
        actor_id=current_user.id,
        type='follow'
    )
    db.session.add(notification)

    db.session.commit()
    flash(f"You are now following {user_to_follow.name}.", "success")
    return redirect(url_for('feed.profile', user_id=user_id))

@feed_bp.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    user_to_unfollow = User.query.get_or_404(user_id)
    if user_to_unfollow == current_user:
        flash("You cannot unfollow yourself.", "warning")
        return redirect(url_for('feed.profile', user_id=user_id))

    current_user.unfollow(user_to_unfollow)
    db.session.commit()
    flash(f"You have unfollowed {user_to_unfollow.name}.", "success")
    return redirect(url_for('feed.profile', user_id=user_id))

@feed_bp.route('/notifications')
@login_required
def notifications():
    """Display user notifications, grouped by date."""
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()

    grouped_notifications = {
        "Today": [],
        "Yesterday": [],
        "Older": []
    }

    today = date.today()
    yesterday = today - timedelta(days=1)

    for n in user_notifications:
        # Generate descriptive text
        if n.type == 'follow':
            n.text = f"{n.actor.name} started following you."
        elif n.type == 'like_post':
            n.text = f"{n.actor.name} liked your post."
        elif n.type == 'comment_post':
            n.text = f"{n.actor.name} commented on your post."
        else:
            n.text = "You have a new notification."

        # Group by date
        if n.timestamp.date() == today:
            grouped_notifications["Today"].append(n)
        elif n.timestamp.date() == yesterday:
            grouped_notifications["Yesterday"].append(n)
        else:
            grouped_notifications["Older"].append(n)

        # Mark as read
        n.is_read = True

    db.session.commit()
    return render_template('feed/notifications.html', grouped_notifications=grouped_notifications)

@feed_bp.route('/reels')
@login_required
def reels():
    """Reels feed page."""
    reels = Reel.query.order_by(Reel.timestamp.desc()).all()
    return render_template('feed/reels.html', reels=reels)

@feed_bp.route('/reels/viewer')
@login_required
def reels_viewer():
    """Displays the immersive Reels viewer page."""
    return render_template('feed/reels_viewer.html')

@feed_bp.route('/search')
@login_required
def search():
    """Search for users, posts, and communities."""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('feed.home'))

    # Search users
    users = User.query.filter(User.name.ilike(f'%{query}%')).limit(10).all()

    # Search posts
    posts = Post.query.filter(Post.content.ilike(f'%{query}%')).limit(10).all()

    # Search communities
    communities = Community.query.filter(Community.name.ilike(f'%{query}%')).limit(10).all()

    return render_template('feed/search_results.html',
                           query=query,
                           users=users,
                           posts=posts,
                           communities=communities)

@feed_bp.route('/create_reel', methods=['POST'])
@login_required
def create_reel():
    """Create a new reel."""
    caption = request.form.get('caption')
    video_file = request.files.get('video')

    if not video_file:
        flash('A video file is required to create a reel.', 'danger')
        return redirect(url_for('feed.reels'))

    # We can reuse save_post_media, but should check the type
    video_url, media_type = save_post_media(video_file)
    if not video_url or media_type != 'video':
        flash('Invalid file type or size for reel. Please upload a video.', 'danger')
        return redirect(url_for('feed.reels'))

    new_reel = Reel(
        user_id=current_user.id,
        caption=caption,
        video_url=video_url
    )
    db.session.add(new_reel)
    db.session.commit()

    flash('Your reel has been uploaded!', 'success')
    return redirect(url_for('feed.reels'))

@feed_bp.route('/report_post', methods=['POST'])
@login_required
def report_post():
    """Reports a post with a given reason."""
    post_id = request.form.get('post_id', type=int)
    reason = request.form.get('reason')
    other_reason = request.form.get('reason_other')

    if not post_id or not reason:
        flash('Invalid report submission.', 'danger')
        return redirect(url_for('feed.home'))

    post = Post.query.get_or_404(post_id)

    final_reason = reason
    if reason == 'Other' and other_reason:
        final_reason = other_reason.strip()

    new_report = ReportedPost(
        post_id=post.id,
        reported_by_id=current_user.id,
        reason=final_reason
    )
    db.session.add(new_report)
    db.session.commit()
    flash('Post has been reported. Thank you for your feedback.', 'success')
    return redirect(url_for('feed.home'))

# --- API Routes for Likes and Comments ---

@feed_bp.route('/api/post/<int:post_id>/react', methods=['POST'])
@login_required
def react_to_post(post_id):
    """Adds, updates, or removes a reaction on a post."""
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    reaction_type = data.get('reaction_type', 'like')

    # Validate reaction_type
    allowed_reactions = {'like', 'love', 'haha', 'wow', 'sad', 'angry'}
    if reaction_type not in allowed_reactions:
        return jsonify({'status': 'error', 'message': 'Invalid reaction type.'}), 400

    existing_reaction = Like.query.filter_by(
        user_id=current_user.id,
        target_type='post',
        target_id=post.id
    ).first()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # User is toggling off the same reaction
            db.session.delete(existing_reaction)
            user_reaction = None
        else:
            # User is changing their reaction
            existing_reaction.reaction_type = reaction_type
            user_reaction = reaction_type
    else:
        # User is adding a new reaction
        new_reaction = Like(
            user_id=current_user.id,
            target_type='post',
            target_id=post.id,
            reaction_type=reaction_type
        )
        db.session.add(new_reaction)
        user_reaction = reaction_type

    db.session.commit()

    # Get updated reaction counts
    reaction_counts = db.session.query(
        Like.reaction_type, func.count(Like.reaction_type)
    ).filter_by(target_type='post', target_id=post.id).group_by(Like.reaction_type).all()

    counts_dict = {r_type: count for r_type, count in reaction_counts}

    return jsonify({
        'status': 'success',
        'reaction_counts': counts_dict,
        'total_reactions': post.likes.count(),
        'user_reaction': user_reaction
    })

@feed_bp.route('/api/post/<int:post_id>/comments', methods=['GET'])
@login_required
def get_comments(post_id):
    """Fetches all comments for a post."""
    post = Post.query.get_or_404(post_id)
    comments = post.comments.order_by(GenericComment.timestamp.asc()).all()

    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'timestamp': comment.timestamp.isoformat(),
            'author': {
                'id': comment.author.id,
                'name': comment.author.name,
                'profile_pic': url_for('static', filename='profile_pics/' + comment.author.profile_pic),
                'is_premium': comment.author.is_premium
            }
        })

    return jsonify(comments_data)

@feed_bp.route('/api/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    """Adds a new comment to a post."""
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    content = data.get('content')

    if not content or not content.strip():
        return jsonify({'status': 'error', 'message': 'Comment content cannot be empty.'}), 400

    new_comment = GenericComment(
        user_id=current_user.id,
        target_type='post',
        target_id=post.id,
        content=content.strip()
    )
    db.session.add(new_comment)
    db.session.commit()

    comment_data = {
        'id': new_comment.id,
        'content': new_comment.content,
        'timestamp': new_comment.timestamp.isoformat(),
        'author': {
            'id': new_comment.author.id,
            'name': new_comment.author.name,
            'profile_pic': url_for('static', filename='profile_pics/' + new_comment.author.profile_pic)
        }
    }

    return jsonify({'status': 'success', 'comment': comment_data}), 201


@feed_bp.route('/api/post/<int:post_id>/impression', methods=['POST'])
@login_required
def record_impression(post_id):
    post = Post.query.get_or_404(post_id)

    # Don't record an impression if the user is the author of the post
    if current_user.id == post.user_id:
        return jsonify({'status': 'ignored', 'message': 'Author view'}), 200

    # A simple implementation could add a check here to not record an impression
    # if one was already recorded recently for this user and post.
    # For now, we record every impression call.

    impression = PostImpression(
        post_id=post.id,
        viewer_id=current_user.id
    )
    db.session.add(impression)
    db.session.commit()

    return jsonify({'status': 'success'}), 201


@feed_bp.route('/api/post/<int:post_id>/analytics')
@login_required
def get_post_analytics(post_id):
    post = Post.query.get_or_404(post_id)

    # Security check: only the author can view analytics, and they must be premium
    if post.user_id != current_user.id or not current_user.is_premium:
        abort(403)

    impressions = post.impressions.count()
    reach = db.session.query(func.count(PostImpression.viewer_id.distinct())).filter_by(post_id=post.id).scalar()
    likes = post.likes.count()
    comments = post.comments.count()
    engagement = likes + comments

    # Simple demographics based on likers' roles
    demographics = db.session.query(
        User.role, func.count(User.role)
    ).join(Like, User.id == Like.user_id).filter(
        Like.target_type == 'post',
        Like.target_id == post.id
    ).group_by(User.role).all()

    demographics_data = {role: count for role, count in demographics}

    return jsonify({
        'impressions': impressions,
        'reach': reach,
        'engagement': engagement,
        'likes': likes,
        'comments': comments,
        'demographics': demographics_data
    })


@feed_bp.route('/api/post/<int:post_id>/boost', methods=['POST'])
@login_required
def boost_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Security checks
    if not current_user.is_premium:
        return jsonify({'status': 'error', 'message': 'This feature is for premium members only.'}), 403
    if post.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'You can only boost your own posts.'}), 403
    if post.is_boosted:
        return jsonify({'status': 'error', 'message': 'This post is already boosted.'}), 400

    post.is_boosted = True
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Post boosted successfully!'})

# --- API Route for Reels ---

@feed_bp.route('/api/reels')
@login_required
def get_reels():
    """Fetches all reels for the viewer."""
    reels = Reel.query.order_by(func.random()).all() # Random order for now

    reels_data = [{
        'id': reel.id,
        'video_url': url_for('static', filename=reel.video_url),
        'caption': reel.caption,
        'author': {
            'id': reel.author.id,
            'name': reel.author.name,
            'profile_pic': url_for('static', filename='profile_pics/' + reel.author.profile_pic)
        },
        'likes_count': reel.likes.count(),
        'comments_count': reel.comments.count(),
        'liked_by_user': current_user.id in reel.likes|map(attribute='user_id')|list
    } for reel in reels]

    return jsonify(reels_data)

@feed_bp.route('/api/reels/<int:reel_id>/like', methods=['POST'])
@login_required
def like_reel(reel_id):
    """Toggles a like on a reel."""
    reel = Reel.query.get_or_404(reel_id)
    like = Like.query.filter_by(user_id=current_user.id, target_type='reel', target_id=reel.id).first()

    if like:
        db.session.delete(like)
        liked = False
    else:
        new_like = Like(user_id=current_user.id, target_type='reel', target_id=reel.id)
        db.session.add(new_like)
        liked = True

    db.session.commit()

    return jsonify({
        'status': 'success',
        'likes_count': reel.likes.count(),
        'liked_by_user': liked
    })

# Note: Commenting on reels is not implemented in this version, but the endpoint could be added here.


# --- API Routes for Creative Work Likes and Comments ---

@feed_bp.route('/api/post/<int:post_id>/share', methods=['POST'])
@login_required
def share_post(post_id):
    """Shares a post."""
    original_post = Post.query.get_or_404(post_id)
    data = request.get_json()
    content = data.get('content', '') # Optional comment from the user

    # Prevent sharing a post that is already a share
    if original_post.original_post_id:
        flash('You cannot share a post that is already a share.', 'danger')
        return jsonify({'status': 'error', 'message': 'Cannot share a share.'}), 400

    # Create the new shared post
    new_post = Post(
        user_id=current_user.id,
        content=content,
        privacy='public', # Shares are always public
        original_post_id=original_post.id
    )
    db.session.add(new_post)
    db.session.commit()

    flash('Post successfully shared!', 'success')
    return jsonify({'status': 'success', 'message': 'Post shared.'})


@feed_bp.route('/api/creative_work/<int:work_id>/like', methods=['POST'])
@login_required
def like_creative_work(work_id):
    """Toggles a like on a creative work."""
    work = CreativeWork.query.get_or_404(work_id)
    like = Like.query.filter_by(user_id=current_user.id, target_type='creative_work', target_id=work.id).first()

    if like:
        db.session.delete(like)
        liked = False
    else:
        new_like = Like(user_id=current_user.id, target_type='creative_work', target_id=work.id)
        db.session.add(new_like)
        liked = True

    db.session.commit()

    return jsonify({
        'status': 'success',
        'likes_count': work.likes.count(),
        'liked_by_user': liked
    })

@feed_bp.route('/api/creative_work/<int:work_id>/comments', methods=['GET'])
@login_required
def get_creative_work_comments(work_id):
    """Fetches all comments for a creative work."""
    work = CreativeWork.query.get_or_404(work_id)
    comments = work.comments.order_by(GenericComment.timestamp.asc()).all()

    comments_data = [{
        'id': comment.id,
        'content': comment.content,
        'timestamp': comment.timestamp.isoformat(),
        'author': {
            'id': comment.author.id,
            'name': comment.author.name,
            'profile_pic': url_for('static', filename='profile_pics/' + comment.author.profile_pic)
        }
    } for comment in comments]

    return jsonify(comments_data)

@feed_bp.route('/api/creative_work/<int:work_id>/comment', methods=['POST'])
@login_required
def add_creative_work_comment(work_id):
    """Adds a new comment to a creative work."""
    work = CreativeWork.query.get_or_404(work_id)
    data = request.get_json()
    content = data.get('content')

    if not content or not content.strip():
        return jsonify({'status': 'error', 'message': 'Comment content cannot be empty.'}), 400

    new_comment = GenericComment(
        user_id=current_user.id,
        target_type='creative_work',
        target_id=work.id,
        content=content.strip()
    )
    db.session.add(new_comment)
    db.session.commit()

    comment_data = {
        'id': new_comment.id,
        'content': new_comment.content,
        'timestamp': new_comment.timestamp.isoformat(),
        'author': {
            'id': new_comment.author.id,
            'name': new_comment.author.name,
            'profile_pic': url_for('static', filename='profile_pics/' + new_comment.author.profile_pic)
        }
    }

    return jsonify({'status': 'success', 'comment': comment_data}), 201


# --- Creativity Hub: Challenges, Voting, Bookmarking, Sharing ---

@feed_bp.route('/challenge/<int:challenge_id>')
@login_required
def view_challenge(challenge_id):
    """View a single challenge and its submissions."""
    challenge = Challenge.query.get_or_404(challenge_id)
    # Submissions are accessed via challenge.submissions relationship
    return render_template('feed/challenge_detail.html', challenge=challenge)

@feed_bp.route('/saved')
@login_required
def saved_items():
    """Display the user's saved/bookmarked items."""
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.timestamp.desc()).all()

    saved_items = []
    for bookmark in bookmarks:
        item = None
        if bookmark.target_type == 'creative_work':
            item = CreativeWork.query.get(bookmark.target_id)
        elif bookmark.target_type == 'reel':
            item = Reel.query.get(bookmark.target_id)
        elif bookmark.target_type == 'post':
            item = Post.query.get(bookmark.target_id)

        if item:
            # Add the type to the item so the template knows how to render it
            item.saved_item_type = bookmark.target_type
            saved_items.append(item)

    return render_template('feed/saved_items.html', saved_items=saved_items)

@feed_bp.route('/api/challenge/<int:challenge_id>/submit', methods=['POST'])
@login_required
def submit_to_challenge(challenge_id):
    """Submit a creative work to a challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)
    data = request.get_json()
    work_id = data.get('work_id')

    if not work_id:
        return jsonify({'status': 'error', 'message': 'Work ID is required.'}), 400

    work = CreativeWork.query.get_or_404(work_id)

    if work.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'You can only submit your own work.'}), 403

    if work in challenge.submissions:
        return jsonify({'status': 'error', 'message': 'This work has already been submitted to this challenge.'}), 400

    challenge.submissions.append(work)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Work submitted to challenge successfully.'})

@feed_bp.route('/api/vote', methods=['POST'])
@login_required
def cast_vote():
    """Vote for a submission in a challenge."""
    data = request.get_json()
    challenge_id = data.get('challenge_id')
    submission_id = data.get('submission_id')

    if not challenge_id or not submission_id:
        return jsonify({'status': 'error', 'message': 'Challenge ID and Submission ID are required.'}), 400

    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        challenge_id=challenge_id,
        submission_id=submission_id
    ).first()

    if existing_vote:
        # For simplicity, we don't allow changing votes. Could be extended.
        return jsonify({'status': 'error', 'message': 'You have already voted for this submission.'}), 400

    new_vote = Vote(
        user_id=current_user.id,
        challenge_id=challenge_id,
        submission_id=submission_id
    )
    db.session.add(new_vote)
    db.session.commit()

    # Return new vote count for the submission
    vote_count = Vote.query.filter_by(submission_id=submission_id).count()

    return jsonify({'status': 'success', 'message': 'Vote cast successfully.', 'vote_count': vote_count})


@feed_bp.route('/api/bookmark', methods=['POST'])
@login_required
def toggle_bookmark():
    """Toggles a bookmark on an item (CreativeWork, Reel, etc.)."""
    data = request.get_json()
    target_type = data.get('target_type')
    target_id = data.get('target_id')

    if not target_type or not target_id:
        return jsonify({'status': 'error', 'message': 'Target type and ID are required.'}), 400

    bookmark = Bookmark.query.filter_by(
        user_id=current_user.id,
        target_type=target_type,
        target_id=target_id
    ).first()

    if bookmark:
        db.session.delete(bookmark)
        bookmarked = False
        message = 'Bookmark removed.'
    else:
        new_bookmark = Bookmark(
            user_id=current_user.id,
            target_type=target_type,
            target_id=target_id
        )
        db.session.add(new_bookmark)
        bookmarked = True
        message = 'Item bookmarked.'

    db.session.commit()

    return jsonify({'status': 'success', 'message': message, 'bookmarked': bookmarked})


@feed_bp.route('/api/creative_work/<int:work_id>/share', methods=['POST'])
@login_required
def share_creative_work(work_id):
    """Shares a creative work to the main feed by creating a new Post."""
    work = CreativeWork.query.get_or_404(work_id)
    data = request.get_json()
    content = data.get('content', '')  # Optional comment from the user sharing

    # Create a new Post that references the creative work
    # We can create a rich content string for the post
    share_content = f"""
    <div class="shared-creative-work">
        <p>Shared from the Creativity Hub:</p>
        <div class="card">
            <div class="card-body">
                <h5 class="card-title">{work.title}</h5>
                <p class="card-text">by {work.artist.name}</p>
                <a href="{url_for('feed.view_creative_work', work_id=work.id)}" class="btn btn-primary">View Original</a>
            </div>
        </div>
    </div>
    """

    if content:
        # Prepend the user's personal comment to the shared content
        content = f"<p>{content}</p><hr>{share_content}"
    else:
        content = share_content

    new_post = Post(
        user_id=current_user.id,
        content=content,
        privacy='public', # Shares are typically public
    )
    db.session.add(new_post)
    db.session.commit()

    flash('Successfully shared to your feed!', 'success')
    return jsonify({'status': 'success', 'message': 'Work shared successfully.'})


# --- API Routes for Project Likes and Comments ---

@feed_bp.route('/api/get_form/<category>', methods=['GET'])
@login_required
def get_form(category):
    """Returns the HTML for the specified upload form."""
    if category == 'art_design':
        return render_template('feed/forms/art_design.html')
    elif category == 'writing':
        return render_template('feed/forms/writing.html')
    elif category == 'music_audio':
        return render_template('feed/forms/music_audio.html')
    elif category == 'reels':
        return render_template('feed/forms/reels.html')
    else:
        return '', 404

@feed_bp.route('/api/project/<int:project_id>/like', methods=['POST'])
@login_required
def like_project(project_id):
    """Toggles a like on a project."""
    project = Project.query.get_or_404(project_id)
    like = Like.query.filter_by(user_id=current_user.id, target_type='project', target_id=project.id).first()

    if like:
        db.session.delete(like)
        liked = False
    else:
        new_like = Like(user_id=current_user.id, target_type='project', target_id=project.id)
        db.session.add(new_like)
        liked = True

    db.session.commit()

    return jsonify({
        'status': 'success',
        'likes_count': project.likes.count(),
        'liked_by_user': liked
    })

@feed_bp.route('/api/project/<int:project_id>/comments', methods=['GET'])
@login_required
def get_project_comments(project_id):
    """Fetches all comments for a project."""
    project = Project.query.get_or_404(project_id)
    comments = project.comments.order_by(GenericComment.timestamp.asc()).all()

    comments_data = [{
        'id': comment.id,
        'content': comment.content,
        'timestamp': comment.timestamp.isoformat(),
        'author': {
            'id': comment.author.id,
            'name': comment.author.name,
            'profile_pic': url_for('static', filename='profile_pics/' + comment.author.profile_pic)
        }
    } for comment in comments]

    return jsonify(comments_data)

@feed_bp.route('/api/project/<int:project_id>/comment', methods=['POST'])
@login_required
def add_project_comment(project_id):
    """Adds a new comment to a project."""
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    content = data.get('content')

    if not content or not content.strip():
        return jsonify({'status': 'error', 'message': 'Comment content cannot be empty.'}), 400

    new_comment = GenericComment(
        user_id=current_user.id,
        target_type='project',
        target_id=project.id,
        content=content.strip()
    )
    db.session.add(new_comment)
    db.session.commit()

    comment_data = {
        'id': new_comment.id,
        'content': new_comment.content,
        'timestamp': new_comment.timestamp.isoformat(),
        'author': {
            'id': new_comment.author.id,
            'name': new_comment.author.name,
            'profile_pic': url_for('static', filename='profile_pics/' + new_comment.author.profile_pic)
        }
    }

    return jsonify({'status': 'success', 'comment': comment_data}), 201
