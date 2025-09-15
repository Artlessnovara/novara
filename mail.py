from flask import current_app, render_template
from flask_mail import Message
from extensions import mail
from itsdangerous import URLSafeTimedSerializer

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(
        app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[to]
    )
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    mail.send(msg)

def send_verification_email(user):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = s.dumps(user.email, salt='email-verification-salt')
    send_email(
        user.email,
        'Confirm Your Account',
        'email/verify',
        user=user,
        token=token
    )
