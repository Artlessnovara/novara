from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, LibraryMaterial, Category
from werkzeug.utils import secure_filename
import os

more = Blueprint('more', __name__)

@more.route('/resources')
def resources():
    categories = Category.query.all()

    # Filtering logic
    query = LibraryMaterial.query.filter_by(approved=True)

    category_id = request.args.get('category')
    if category_id:
        query = query.filter_by(category_id=category_id)

    price = request.args.get('price')
    if price == 'free':
        query = query.filter(LibraryMaterial.price_naira == 0)
    elif price == 'paid':
        query = query.filter(LibraryMaterial.price_naira > 0)

    sort = request.args.get('sort', 'newest')
    if sort == 'popular':
        query = query.order_by(LibraryMaterial.download_count.desc())
    else:
        query = query.order_by(LibraryMaterial.id.desc())

    materials = query.all()

    return render_template('more/resources.html', materials=materials, categories=categories)

@more.route('/resource/<int:material_id>')
def resource_detail(material_id):
    material = LibraryMaterial.query.get_or_404(material_id)
    return render_template('more/resource_detail.html', material=material)

def save_library_file(file):
    from flask import current_app
    filename = secure_filename(file.filename)
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext
    filepath = os.path.join(current_app.root_path, 'static/library', new_filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)
    return os.path.join('library', new_filename)

@more.route('/post_resource', methods=['POST'])
@login_required
def post_resource():
    if current_user.role != 'instructor':
        flash('Only instructors can post resources.', 'danger')
        return redirect(url_for('more.resources'))

    title = request.form.get('title')
    description = request.form.get('description')
    category_id = request.form.get('category_id')
    price = request.form.get('price_naira')
    file = request.files.get('file')

    if not all([title, description, category_id, price, file]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('more.resources'))

    file_path = save_library_file(file)

    new_material = LibraryMaterial(
        uploader_id=current_user.id,
        title=title,
        description=description,
        category_id=category_id,
        price_naira=price,
        file_path=file_path,
        approved=False # Admin must approve
    )
    db.session.add(new_material)
    db.session.commit()

    flash('Your resource has been submitted for review.', 'success')
    return redirect(url_for('more.resources'))
