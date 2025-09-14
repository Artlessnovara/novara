import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import User, UserPage, Draft, Wallet, Subscription, BlockedUser, Community, CommunityMembership, Feedback, Referral
from extensions import db
from forms import UserPageForm, ReportProblemForm, ContactForm, FeedbackForm

more_bp = Blueprint('more', __name__, url_prefix='/more')

@more_bp.route('/')
@login_required
def more_page():
    """The main 'More' page / menu."""
    return render_template('more/index.html')

# --- My Pages ---
@more_bp.route('/my_pages')
@login_required
def my_pages():
    pages = UserPage.query.filter_by(user_id=current_user.id).order_by(UserPage.created_at.desc()).all()
    return render_template('more/my_pages.html', pages=pages)

@more_bp.route('/page/create', methods=['GET', 'POST'])
@login_required
def create_page():
    form = UserPageForm()
    if form.validate_on_submit():
        new_page = UserPage(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data
        )
        db.session.add(new_page)
        db.session.commit()
        flash('Your page has been created!', 'success')
        return redirect(url_for('more.my_pages'))
    return render_template('more/create_edit_page.html', form=form, legend='Create New Page')

@more_bp.route('/page/<int:page_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_page(page_id):
    page = UserPage.query.get_or_404(page_id)
    if page.owner != current_user:
        abort(403)
    form = UserPageForm(obj=page)
    if form.validate_on_submit():
        page.title = form.title.data
        page.description = form.description.data
        db.session.commit()
        flash('Your page has been updated!', 'success')
        return redirect(url_for('more.my_pages'))
    return render_template('more/create_edit_page.html', form=form, legend='Edit Page')

@more_bp.route('/pages/explore')
@login_required
def explore_pages():
    pages = UserPage.query.order_by(UserPage.created_at.desc()).limit(20).all()
    return render_template('more/explore_pages.html', pages=pages)

# --- Drafts ---
@more_bp.route('/drafts')
@login_required
def drafts():
    user_drafts = Draft.query.filter_by(user_id=current_user.id).order_by(Draft.updated_at.desc()).all()
    return render_template('more/drafts.html', drafts=user_drafts)

# --- Wallet & Subscriptions ---
@more_bp.route('/wallet')
@login_required
def wallet():
    user_wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    if not user_wallet:
        user_wallet = Wallet(user_id=current_user.id)
        db.session.add(user_wallet)
        db.session.commit()
    return render_template('more/wallet.html', wallet=user_wallet)

@more_bp.route('/subscriptions')
@login_required
def subscriptions():
    sub = Subscription.query.filter_by(user_id=current_user.id).first()
    return render_template('more/subscriptions.html', subscription=sub)

# --- Settings ---
@more_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name)
        current_user.bio = request.form.get('bio', current_user.bio)
        current_user.privacy_last_seen = request.form.get('privacy_last_seen', current_user.privacy_last_seen)
        current_user.privacy_profile_pic = request.form.get('privacy_profile_pic', current_user.privacy_profile_pic)
        current_user.privacy_about = request.form.get('privacy_about', current_user.privacy_about)
        current_user.message_notifications_enabled = 'message_notifications' in request.form
        current_user.group_notifications_enabled = 'group_notifications' in request.form
        db.session.commit()
        flash('Your settings have been updated.', 'success')
        return redirect(url_for('more.settings'))
    return render_template('more/settings.html')

@more_bp.route('/api/toggle_theme', methods=['POST'])
@login_required
def toggle_theme():
    current_user.theme = 'dark' if current_user.theme == 'light' else 'light'
    db.session.commit()
    return jsonify({'status': 'success', 'new_theme': current_user.theme})

# --- Support ---
@more_bp.route('/support/help')
@login_required
def help_center():
    return render_template('more/help_center.html')

@more_bp.route('/support/report', methods=['GET', 'POST'])
@login_required
def report_problem():
    form = ReportProblemForm()
    if form.validate_on_submit():
        # Here you would typically email the report or save it to a database
        flash('Thank you for your report. We will look into it shortly.', 'success')
        return redirect(url_for('more.more_page'))
    return render_template('more/report_problem.html', form=form)

@more_bp.route('/support/contact', methods=['GET', 'POST'])
@login_required
def contact_support():
    form = ContactForm()
    if form.validate_on_submit():
        flash('Your message has been sent to our support team.', 'success')
        return redirect(url_for('more.more_page'))
    return render_template('more/contact_support.html', form=form)

@more_bp.route('/support/feedback', methods=['GET', 'POST'])
@login_required
def give_feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        new_feedback = Feedback(
            user_id=current_user.id,
            feedback_text=form.feedback_text.data
        )
        db.session.add(new_feedback)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('more.more_page'))
    return render_template('more/give_feedback.html', form=form)

# --- Legal & Info ---
@more_bp.route('/about')
def about():
    return render_template('more/about.html')

@more_bp.route('/terms')
def terms():
    return render_template('more/terms.html')

# --- Blocked Users ---
@more_bp.route('/settings/blocked_users')
@login_required
def blocked_users():
    """Page to view and manage blocked users."""
    blocked_list = BlockedUser.query.filter_by(blocker_id=current_user.id).all()
    return render_template('more/blocked_users.html', blocked_list=blocked_list)

@more_bp.route('/settings/unblock_user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    """Endpoint to unblock a user."""
    user_to_unblock = User.query.get_or_404(user_id)
    blocked_entry = BlockedUser.query.filter_by(
        blocker_id=current_user.id,
        blocked_id=user_to_unblock.id
    ).first()

    if blocked_entry:
        db.session.delete(blocked_entry)
        db.session.commit()
        flash(f'You have unblocked {user_to_unblock.name}.', 'success')
    else:
        flash('You had not blocked this user.', 'info')

    return redirect(url_for('more.blocked_users'))

# --- Manage Communities ---
@more_bp.route('/communities/manage')
@login_required
def managed_communities():
    """Page to view and manage communities run by the user."""
    # Find communities created by the user
    created_communities = Community.query.filter_by(created_by_id=current_user.id).all()

    # Find communities where the user is an admin or moderator
    managed_memberships = CommunityMembership.query.filter(
        CommunityMembership.user_id == current_user.id,
        CommunityMembership.role.in_(['admin', 'moderator'])
    ).all()

    # Get the community objects from the memberships
    managed_communities_from_role = [membership.community for membership in managed_memberships]

    # Combine the lists and remove duplicates using a dictionary
    all_managed_communities_dict = {comm.id: comm for comm in created_communities}
    all_managed_communities_dict.update({comm.id: comm for comm in managed_communities_from_role})

    all_managed_communities = list(all_managed_communities_dict.values())

    return render_template('more/managed_communities.html', communities=all_managed_communities)

# --- Invite Friends ---
@more_bp.route('/invite')
@login_required
def invite_friends():
    """Page to display user's referral code."""
    referral = Referral.query.filter_by(user_id=current_user.id).first()
    if not referral:
        # Generate a new unique code
        while True:
            new_code = secrets.token_hex(8)
            if not Referral.query.filter_by(code=new_code).first():
                break

        referral = Referral(user_id=current_user.id, code=new_code)
        db.session.add(referral)
        db.session.commit()

    referral_link = url_for('main.register', ref=referral.code, _external=True)

    return render_template('more/invite_friends.html', referral_code=referral.code, referral_link=referral_link)
