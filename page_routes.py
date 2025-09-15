from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from models import UserPage, db
from forms import PageCreationStep1Form, PageCreationStep2Form, PageCreationStep3Form
import os
import secrets
from werkzeug.utils import secure_filename

page_bp = Blueprint('pages', __name__, url_prefix='/page')

def save_page_asset(file, subfolder):
    """Saves a file to a specified subfolder within static/uploads/pages/"""
    filename = secure_filename(file.filename)
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    # Base path for page assets
    base_dir = os.path.join(current_app.root_path, 'static/uploads/pages', subfolder)
    os.makedirs(base_dir, exist_ok=True)

    filepath = os.path.join(base_dir, new_filename)
    file.save(filepath)

    # Return the path relative to the static folder
    return os.path.join('uploads/pages', subfolder, new_filename)

@page_bp.route('/create', methods=['GET'])
@login_required
def create_page_start():
    # Clear any previous session data
    session.pop('page_creation_data', None)
    return redirect(url_for('pages.create_page_step1'))

@page_bp.route('/create/step1', methods=['GET', 'POST'])
@login_required
def create_page_step1():
    form = PageCreationStep1Form()
    if form.validate_on_submit():
        session['page_creation_data'] = {
            'name': form.name.data,
            'category': form.category.data,
            'bio': form.bio.data
        }
        return redirect(url_for('pages.create_page_step2'))
    return render_template('pages/create/step1_details.html', form=form)

@page_bp.route('/create/step2', methods=['GET', 'POST'])
@login_required
def create_page_step2():
    if 'page_creation_data' not in session:
        flash('Please start from step 1.', 'warning')
        return redirect(url_for('pages.create_page_step1'))

    form = PageCreationStep2Form()
    if form.validate_on_submit():
        page_data = session['page_creation_data']

        if form.profile_pic.data:
            page_data['profile_pic_url'] = save_page_asset(form.profile_pic.data, 'profile_pics')

        if form.cover_banner.data:
            page_data['cover_banner_url'] = save_page_asset(form.cover_banner.data, 'banners')

        session['page_creation_data'] = page_data
        return redirect(url_for('pages.create_page_step3'))

    return render_template('pages/create/step2_branding.html', form=form)

@page_bp.route('/create/step3', methods=['GET', 'POST'])
@login_required
def create_page_step3():
    if 'page_creation_data' not in session:
        flash('Please start from step 1.', 'warning')
        return redirect(url_for('pages.create_page_step1'))

    form = PageCreationStep3Form()
    if form.validate_on_submit():
        page_data = session['page_creation_data']
        page_data['phone_number'] = form.phone_number.data
        page_data['email'] = form.email.data
        page_data['website'] = form.website.data
        page_data['action_button_type'] = form.action_button.data
        session['page_creation_data'] = page_data
        return redirect(url_for('pages.create_page_step4'))

    return render_template('pages/create/step3_contact.html', form=form)

@page_bp.route('/create/step4', methods=['GET', 'POST'])
@login_required
def create_page_step4():
    if 'page_creation_data' not in session:
        flash('Please start from step 1.', 'warning')
        return redirect(url_for('pages.create_page_step1'))

    page_data = session['page_creation_data']

    if request.method == 'POST':
        # Create the page in the database
        new_page = UserPage(
            owner=current_user,
            title=page_data.get('name'),
            description=page_data.get('bio'),
            category=page_data.get('category'),
            profile_pic_url=page_data.get('profile_pic_url'),
            cover_banner_url=page_data.get('cover_banner_url'),
            phone_number=page_data.get('phone_number'),
            email=page_data.get('email'),
            website=page_data.get('website'),
            action_button_type=page_data.get('action_button_type')
        )
        db.session.add(new_page)
        db.session.commit()

        # Clear session data
        session.pop('page_creation_data', None)

        flash('Your page has been created successfully!', 'success')
        # Redirect to the new public page view (which doesn't exist yet)
        # For now, redirect to the 'my_pages' list.
        return redirect(url_for('more.my_pages'))

    return render_template('pages/create/step4_preview.html', page_data=page_data)
