import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a plain-text email using the configured SMTP server."""

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    message["To"] = to_email
    message.set_content(body)

    mail_server = current_app.config["MAIL_SERVER"]
    mail_port = int(current_app.config["MAIL_PORT"])
    mail_username = current_app.config["MAIL_USERNAME"]
    mail_password = current_app.config["MAIL_PASSWORD"]
    use_tls = current_app.config["MAIL_USE_TLS"]

    if not mail_username or not mail_password:
        current_app.logger.error("SMTP credentials are not configured.")
        return False

    try:
        with smtplib.SMTP(mail_server, mail_port, timeout=15) as server:
            server.ehlo()

            if use_tls:
                server.starttls()
                server.ehlo()

            server.login(mail_username, mail_password)
            server.send_message(message)

        return True

    except (smtplib.SMTPException, OSError):
        current_app.logger.exception("Email delivery failed.")
        return False
