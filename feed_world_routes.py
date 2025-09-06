from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Post, Reel, Community, CommunityMembership, User, Project, CreativeWork, follow, Notification, ReportedPost
from extensions import db
from utils import save_post_media, save_community_cover_image
from sqlalchemy.sql import func

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

    return render_template('feed/home.html', posts=posts)

@feed_bp.route('/create_post', methods=['POST'])
@login_required
def create_post():
    """Create a new post."""
    content = request.form.get('content')
    privacy = request.form.get('privacy', 'public')
    media_file = request.files.get('media')

    if not content:
        flash('Content is required to create a post.', 'danger')
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
        privacy=privacy
    )
    db.session.add(new_post)
    db.session.commit()

    flash('Your post has been created!', 'success')
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
    """View a single community."""
    community = Community.query.get_or_404(community_id)
    # You can add logic here to fetch posts specific to this community
    return render_template('feed/view_community.html', community=community)

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
    """Creativity page."""
    works = CreativeWork.query.order_by(CreativeWork.timestamp.desc()).all()
    return render_template('feed/creativity.html', works=works)

@feed_bp.route('/creative_work/create', methods=['POST'])
@login_required
def create_creative_work():
    """Create a new creative work."""
    title = request.form.get('title')
    description = request.form.get('description')
    media_file = request.files.get('media')

    if not title or not media_file:
        flash('Title and a media file are required.', 'danger')
        return redirect(url_for('feed.creativity'))

    media_url, media_type = save_post_media(media_file)
    if not media_url:
        flash('Invalid file type or size for media.', 'danger')
        return redirect(url_for('feed.creativity'))

    new_work = CreativeWork(
        title=title,
        description=description,
        media_url=media_url,
        work_type=media_type,
        user_id=current_user.id
    )
    db.session.add(new_work)
    db.session.commit()

    flash('Your creative work has been uploaded!', 'success')
    return redirect(url_for('feed.view_creative_work', work_id=new_work.id))

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

@feed_bp.route('/more')
@login_required
def more():
    """More options page."""
    return render_template('feed/more.html')

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
    """Display user notifications."""
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    # Mark notifications as read
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return render_template('feed/notifications.html', notifications=notifications)

@feed_bp.route('/reels')
@login_required
def reels():
    """Reels feed page."""
    reels = Reel.query.order_by(Reel.timestamp.desc()).all()
    return render_template('feed/reels.html', reels=reels)

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

@feed_bp.route('/report_post/<int:post_id>')
@login_required
def report_post(post_id):
    post = Post.query.get_or_404(post_id)
    # For simplicity, we'll just create the report directly.
    # A real implementation would have a form for the reason.
    new_report = ReportedPost(
        post_id=post.id,
        reported_by_id=current_user.id,
        reason="Reported from post feed."
    )
    db.session.add(new_report)
    db.session.commit()
    flash('Post has been reported.', 'success')
    return redirect(url_for('feed.home'))
