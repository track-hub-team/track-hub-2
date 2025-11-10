from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    
    msg = Message(subject, sender=app.config.get('MAIL_USERNAME'), recipients=[to])
    
    msg.body = render_template(f"email/{template}.txt", **kwargs)
    msg.html = render_template(f"email/{template}.html", **kwargs)
    
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr