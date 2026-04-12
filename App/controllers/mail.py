from flask_mail import Mail, Message
from flask import render_template, current_app

mail = Mail()

def init_mail(app):
    """Initialize mail with application config"""
    app.config['MAIL_SERVER'] = app.config.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = app.config.get('MAIL_PORT', 587)
    app.config['MAIL_USE_TLS'] = app.config.get('MAIL_USE_TLS', True)
    app.config['MAIL_USERNAME'] = app.config.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = app.config.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = app.config.get('MAIL_DEFAULT_SENDER', ('iGOVTT Asset Tracker', 'noreply@igov.tt'))
    
    mail.init_app(app)
    return mail

def send_email(subject, recipients, template, **kwargs):
    """Send an email using a template"""
    try:
        msg = Message(
            subject,
            recipients=recipients
        )
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending email: {str(e)}")
        return False

def send_password_reset_email(user_email, reset_url):
    """Send password reset email with reset link"""
    subject = "Password Reset Request"
    try:
        return send_email(
            subject,
            [user_email],
            'email/password_reset.html',
            reset_url=reset_url,
            user_email=user_email
        )
    except Exception as e:
        print(f"Error sending password reset email to {user_email}: {str(e)}")
        current_app.logger.error(f"Password reset email failed: {str(e)}")
        return False
