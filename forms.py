from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileField, FileRequired

class UserPageForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Save Page')

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
