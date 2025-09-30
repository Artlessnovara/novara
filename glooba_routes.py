from flask import Blueprint, render_template
from flask_login import login_required

glooba_bp = Blueprint('glooba', __name__)

@glooba_bp.route('/glooba')
@login_required
def glooba_home():
    """
    Renders the main GloobaApp interface.
    """
    return render_template('glooba/glooba.html')