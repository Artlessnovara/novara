from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Optional, URL, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired

class PageCreationStep1Form(FlaskForm):
    name = StringField('Page Name', validators=[DataRequired(), Length(min=3, max=100)])
    category = StringField('Category', validators=[DataRequired(), Length(max=100)])
    bio = TextAreaField('Short Bio', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Next Step')

class PageCreationStep2Form(FlaskForm):
    profile_pic = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    cover_banner = FileField('Cover Banner', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Next Step')

class PageCreationStep3Form(FlaskForm):
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    email = StringField('Public Email', validators=[Optional(), Email()])
    website = StringField('Website', validators=[Optional(), URL()])
    action_button = SelectField('Action Button', choices=[
        ('', '--- None ---'),
        ('message', 'Message Us'),
        ('call', 'Call Now'),
        ('email', 'Email Us'),
        ('website', 'Visit Website')
    ], validators=[Optional()])
    submit = SubmitField('Next Step')

class ReportProblemForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired()])
    details = TextAreaField('Details', validators=[DataRequired()])
    submit = SubmitField('Submit Report')

class ContactForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    email = StringField('Your Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')

class FeedbackForm(FlaskForm):
    feedback_text = TextAreaField('Your Feedback', validators=[DataRequired()], render_kw={"placeholder": "Tell us what you think..."})
    submit = SubmitField('Submit Feedback')

class PremiumUpgradeForm(FlaskForm):
    proof_of_payment = FileField('Proof of Payment', validators=[FileRequired()])
    submit = SubmitField('Submit for Review')

class ProfileAppearanceForm(FlaskForm):
    profile_banner = FileField('Profile Banner', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    profile_theme = SelectField('Profile Theme', choices=[
        ('default', 'Default'),
        ('ocean', 'Ocean Blue'),
        ('forest', 'Forest Green'),
        ('sunset', 'Sunset Orange')
    ])
    bio_links = TextAreaField('Bio Links (JSON format)',
                              description='e.g., [{"title": "My Blog", "url": "https://..."}]',
                              validators=[Optional()])
    pinned_post = SelectField('Pinned Post', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Changes')
