# utils.py
from django.core.mail import send_mail
from .models import SMTPConfig

def send_email(subject, message, to_email):
    smtp = SMTPConfig.objects.filter(active=True).first()
    if not smtp:
        raise Exception("No active SMTP configuration found!")

    from django.core.mail import EmailMessage
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=smtp.username,
        to=[to_email]
    )
    email.send(fail_silently=False)
