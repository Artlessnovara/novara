from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Post, Like, GenericComment, Reel, Community, CommunityMembership, User, Project, CreativeWork, follow, Notification, ReportedPost, Status, Challenge, ChallengeSubmission, Bookmark, Vote
from extensions import db
from utils import save_post_media, save_community_cover_image
from sqlalchemy.sql import func, desc
from datetime import datetime, date, timedelta

feed_bp = Blueprint('feed', __name__, url_prefix='/feed')

@feed_bp.route('/')
@login_required
def home():
    """Main feed page."""
    following_ids = [u.id for u in current_user.followed]

    # Also include the user's own ID to see their own posts
    following_ids.append(current_user.id)

    posts = Post.query.filter(
        (Post.privacy == 'public') |
        ( (Post.privacy == 'followers') & (Post.user_id.in_(following_ids)) ) |
        ( (Post.privacy == 'private') & (Post.user_id == current_user.id) )
    ).order_by(Post.timestamp.desc()).all()

    # Pre-process posts to include reaction data
    for post in posts:
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
    """Create a new post."""
    content = request.form.get('content')
    privacy = request.form.get('privacy', 'public')
    media_file = request.files.get('media')
    community_id = request.form.get('community_id', type=int)

    if not content:
        flash('Content is required to create a post.', 'danger')
        if community_id:
            return redirect(url_for('feed.view_community', community_id=community_id))
        return redirect(url_for('feed.home'))

    media_url = None
    media_type = None

    if media_file:
        media_url, media_type = save_post_media(media_file)
        if not media_url:
            flash('Invalid file type or size for media.', 'danger')
            return redirect(url_for('feed.home'))

    new_post = Post(
        user_id=current_user.id,
        content=content,
        media_url=media_url,
        media_type=media_type,
        privacy=privacy,
        community_id=community_id
    )
    db.session.add(new_post)
    db.session.commit()

    flash('Your post has been created!', 'success')
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

@feed_bp.route('/creativity', defaults={'category': 'all'})
@feed_bp.route('/creativity/<category>')
@login_required
def creativity(category):
    """Creativity page with categories."""
    categories = ["all", "art_design", "writing", "music_audio", "reels", "challenges", "top_creators"]
    if category not in categories:
        return redirect(url_for('feed.creativity', category='all'))

    works = []
    if category == 'all':
        creative_works = CreativeWork.query.all()
        reels = Reel.query.all()
        works = sorted(creative_works + reels, key=lambda x: x.timestamp, reverse=True)
    elif category == 'art_design':
        query = CreativeWork.query.filter_by(work_type='image')
        sub_cat_filter = request.args.get('filter')
        if sub_cat_filter and sub_cat_filter != 'all':
            query = query.filter_by(sub_category=sub_cat_filter)
        works = query.order_by(CreativeWork.timestamp.desc()).all()
    elif category == 'writing':
        query = CreativeWork.query.filter_by(work_type='writing')
        sub_cat_filter = request.args.get('filter')
        if sub_cat_filter and sub_cat_filter != 'all':
            query = query.filter_by(sub_category=sub_cat_filter)
        works = query.order_by(CreativeWork.timestamp.desc()).all()
    elif category == 'music_audio':
        works = CreativeWork.query.filter_by(work_type='audio').order_by(CreativeWork.timestamp.desc()).all()
    elif category == 'reels':
        works = Reel.query.order_by(Reel.timestamp.desc()).all()
    elif category == 'challenges':
        works = Challenge.query.order_by(Challenge.deadline.desc()).all()
    elif category == 'top_creators':
        most_liked = db.session.query(
            User, func.count(Like.id).label('total_likes')
        ).join(CreativeWork, User.id == CreativeWork.user_id)\
         .join(Like, Like.target_id == CreativeWork.id)\
         .filter(Like.target_type == 'creative_work')\
         .group_by(User.id)\
         .order_by(desc('total_likes'))\
         .limit(10).all()
        most_active = db.session.query(
            User, func.count(CreativeWork.id).label('work_count')
        ).join(CreativeWork, User.id == CreativeWork.user_id)\
         .group_by(User.id)\
         .order_by(desc('work_count'))\
         .limit(10).all()
        spotlight_creators = [user for user, likes in most_liked[:3]]
        works = {
            'most_liked': most_liked,
            'most_active': most_active,
            'spotlight': spotlight_creators
        }

    return render_template('feed/creativity.html', works=works, active_category=category)

@feed_bp.route('/creative_work/create', methods=['POST'])
@login_required
def create_creative_work():
    """Create a new creative work."""
    title = request.form.get('title')
    description = request.form.get('description')
    category = request.form.get('category')

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
            sub_category=request.form.get('sub_category'),
            style_options=style_map.get(bg_style),
            tags=request.form.get('tags'),
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
            tags=request.form.get('tags'),
            user_id=current_user.id
        )
    else: # Assumes art_design or other file-based types
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
            sub_category=request.form.get('sub_category'),
            tags=request.form.get('tags'),
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

@feed_bp.route('/challenge/<int:challenge_id>')
@login_required
def view_challenge(challenge_id):
    """View a single challenge and its submissions."""
    challenge = Challenge.query.get_or_404(challenge_id)
    # A more complex app might paginate submissions
    return render_template('feed/challenge_detail.html', challenge=challenge)

@feed_bp.route('/challenge/<int:challenge_id>/submit', methods=['POST'])
@login_required
def submit_to_challenge(challenge_id):
    """Submit a creative work to a challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)
    creative_work_id = request.form.get('creative_work_id', type=int)

    if not challenge.is_active:
        flash("This challenge has ended and is no longer accepting submissions.", "danger")
        return redirect(url_for('feed.view_challenge', challenge_id=challenge_id))

    if not creative_work_id:
        flash("You must select one of your creative works to submit.", "danger")
        return redirect(url_for('feed.view_challenge', challenge_id=challenge_id))

    work = CreativeWork.query.get_or_404(creative_work_id)
    if work.user_id != current_user.id:
        flash("You can only submit your own creative works.", "danger")
        return redirect(url_for('feed.view_challenge', challenge_id=challenge_id))

    # Check if the user has already submitted this work to this challenge
    existing_submission = ChallengeSubmission.query.filter_by(
        challenge_id=challenge.id,
        submission_id=work.id,
        submission_type='creative_work'
    ).first()

    if existing_submission:
        flash("You have already submitted this work to this challenge.", "info")
        return redirect(url_for('feed.view_challenge', challenge_id=challenge_id))

    new_submission = ChallengeSubmission(
        challenge_id=challenge.id,
        user_id=current_user.id,
        submission_id=work.id,
        submission_type='creative_work'
    )
    db.session.add(new_submission)
    db.session.commit()

    flash("Your work has been submitted to the challenge!", "success")
    return redirect(url_for('feed.view_challenge', challenge_id=challenge_id))

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

@feed_bp.route('/more')
@login_required
def more():
    """More options page."""
    return render_template('feed/more.html')

@feed_bp.route('/saved')
@login_required
def saved():
    """Display user's saved/bookmarked items."""
    bookmarks = current_user.bookmarks.order_by(Bookmark.timestamp.desc()).all()

    saved_items = []
    for bookmark in bookmarks:
        item = None
        if bookmark.target_type == 'creative_work':
            item = CreativeWork.query.get(bookmark.target_id)
        elif bookmark.target_type == 'reel':
            item = Reel.query.get(bookmark.target_id)

        if item:
            saved_items.append(item)

    return render_template('feed/saved.html', items=saved_items)

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
    """Search for users, posts, communities, and creative content."""
    query = request.args.get('q', '')
    category = request.args.get('c', None) # Creativity category

    if not query:
        return redirect(url_for('feed.home'))

    results = {}
    if category:
        if category == 'all':
            results['art_design'] = CreativeWork.query.filter(
                CreativeWork.work_type == 'image',
                CreativeWork.title.ilike(f'%{query}%')
            ).limit(10).all()
            results['writing'] = CreativeWork.query.filter(
                CreativeWork.work_type == 'writing',
                (CreativeWork.title.ilike(f'%{query}%') | CreativeWork.description.ilike(f'%{query}%'))
            ).limit(10).all()
            results['music_audio'] = CreativeWork.query.filter(
                CreativeWork.work_type == 'audio',
                (CreativeWork.title.ilike(f'%{query}%') | CreativeWork.genre.ilike(f'%{query}%'))
            ).limit(10).all()
            results['reels'] = Reel.query.filter(Reel.caption.ilike(f'%{query}%')).limit(10).all()
        elif category == 'art_design':
            results['art_design'] = CreativeWork.query.filter(
                CreativeWork.work_type == 'image',
                (CreativeWork.title.ilike(f'%{query}%') | CreativeWork.tags.ilike(f'%{query}%'))
            ).limit(20).all()
        elif category == 'writing':
            results['writing'] = CreativeWork.query.filter(
                CreativeWork.work_type == 'writing',
                (CreativeWork.title.ilike(f'%{query}%') | CreativeWork.description.ilike(f'%{query}%') | CreativeWork.tags.ilike(f'%{query}%'))
            ).limit(20).all()
        elif category == 'music_audio':
            results['music_audio'] = CreativeWork.query.filter(
                CreativeWork.work_type == 'audio',
                (CreativeWork.title.ilike(f'%{query}%') | CreativeWork.genre.ilike(f'%{query}%') | CreativeWork.tags.ilike(f'%{query}%'))
            ).limit(20).all()
        elif category == 'reels':
            results['reels'] = Reel.query.filter(
                (Reel.caption.ilike(f'%{query}%') | Reel.tags.ilike(f'%{query}%'))
            ).limit(20).all()
        elif category == 'challenges':
            results['challenges'] = Challenge.query.filter(Challenge.title.ilike(f'%{query}%')).limit(20).all()
    else:
        # Generic search
        results['users'] = User.query.filter(User.name.ilike(f'%{query}%')).limit(10).all()
        results['posts'] = Post.query.filter(Post.content.ilike(f'%{query}%')).limit(10).all()
        results['communities'] = Community.query.filter(Community.name.ilike(f'%{query}%')).limit(10).all()

    return render_template('feed/search_results.html',
                           query=query,
                           results=results,
                           category=category)

@feed_bp.route('/create_reel', methods=['POST'])
@login_required
def create_reel():
    """Create a new reel."""
    caption = request.form.get('caption')
    video_file = request.files.get('video')
    tags = request.form.get('tags')

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
        video_url=video_url,
        tags=tags
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
                'profile_pic': url_for('static', filename='profile_pics/' + comment.author.profile_pic)
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

@feed_bp.route('/api/bookmark', methods=['POST'])
@login_required
def bookmark():
    """Toggles a bookmark on an item."""
    data = request.get_json()
    target_id = data.get('target_id')
    target_type = data.get('target_type')

    if not target_id or not target_type:
        return jsonify({'status': 'error', 'message': 'Missing target information.'}), 400

    existing_bookmark = Bookmark.query.filter_by(
        user_id=current_user.id,
        target_type=target_type,
        target_id=target_id
    ).first()

    if existing_bookmark:
        db.session.delete(existing_bookmark)
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

    return jsonify({'status': 'success', 'bookmarked': bookmarked, 'message': message})

@feed_bp.route('/api/share', methods=['POST'])
@login_required
def share():
    """Shares a creative work or reel."""
    data = request.get_json()
    target_id = data.get('target_id')
    target_type = data.get('target_type')

    if not target_id or not target_type:
        return jsonify({'status': 'error', 'message': 'Missing target information.'}), 400

    shared_creative_work_id = None
    shared_reel_id = None

    if target_type == 'creative_work':
        shared_creative_work_id = target_id
    elif target_type == 'reel':
        shared_reel_id = target_id
    else:
        return jsonify({'status': 'error', 'message': 'Invalid target type.'}), 400

    new_post = Post(
        user_id=current_user.id,
        content=data.get('content', ''), # Optional comment
        shared_creative_work_id=shared_creative_work_id,
        shared_reel_id=shared_reel_id,
        privacy='public' # Shares are always public
    )
    db.session.add(new_post)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Successfully shared.'})

@feed_bp.route('/api/vote', methods=['POST'])
@login_required
def vote():
    """Toggles a vote on a challenge submission."""
    data = request.get_json()
    submission_id = data.get('submission_id')

    if not submission_id:
        return jsonify({'status': 'error', 'message': 'Missing submission information.'}), 400

    submission = ChallengeSubmission.query.get_or_404(submission_id)

    # Users cannot vote for their own submissions
    if submission.user_id == current_user.id:
        return jsonify({'status': 'error', 'message': 'You cannot vote for your own submission.'}), 403

    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        submission_id=submission_id
    ).first()

    if existing_vote:
        db.session.delete(existing_vote)
        voted = False
        message = 'Vote removed.'
    else:
        new_vote = Vote(
            user_id=current_user.id,
            submission_id=submission_id
        )
        db.session.add(new_vote)
        voted = True
        message = 'Vote cast.'

    db.session.commit()

    return jsonify({'status': 'success', 'voted': voted, 'message': message, 'vote_count': submission.votes.count()})

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

# --- API Routes for Project Likes and Comments ---

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
