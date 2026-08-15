import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
from jinja2 import Template

logger = logging.getLogger("gmail_helper")

BRANDED_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6; color: #1f2937; margin: 0; padding: 20px; }
        .container { max-width: 600px; background: #ffffff; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin: 0 auto; border-top: 8px solid #4F46E5; }
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { font-size: 24px; color: #4F46E5; margin: 0; }
        .content { font-size: 16px; line-height: 1.6; color: #374151; }
        .footer { text-align: center; font-size: 12px; color: #9ca3af; margin-top: 30px; border-top: 1px solid #e5e7eb; padding-top: 15px; }
        .badge { display: inline-block; background-color: #EEF2F6; color: #4F46E5; padding: 6px 12px; border-radius: 6px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Aetheris HR Services</h1>
        </div>
        <div class="content">
            {{ body_content }}
        </div>
        <div class="footer">
            This is an automated notification from Aetheris HR AI Assistant.<br>
            &copy; 2026 Aetheris HR Services Ltd. All rights reserved.
        </div>
    </div>
</body>
</html>
"""

class GmailHelper:
    def __init__(self):
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL", "hr@company.com")
        self.app_password = os.getenv("GMAIL_APP_PASSWORD", "mock-app-password")
        self.is_mock = self.app_password == "mock-app-password" or self.sender_email == "hr@company.com"

    def send_email(self, to: str, subject: str, body: str, placeholders: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Process placeholders if any
        if placeholders:
            template = Template(body)
            try:
                body = template.render(**placeholders)
            except Exception as e:
                logger.error(f"Error rendering placeholders: {e}")

        # Wrap body in the branded template
        html_template = Template(BRANDED_EMAIL_TEMPLATE)
        html_body = html_template.render(body_content=body.replace("\n", "<br>"))

        if self.is_mock:
            logger.info(f"[MOCK EMAIL] Send to: {to} | Subject: {subject}")
            return {
                "status": "success",
                "mode": "mock",
                "to": to,
                "subject": subject,
                "body": body,
                "html_body": html_body,
                "message": "Email simulation successful. (Mock Mode Active)"
            }

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to

            part1 = MIMEText(body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Gmail SMTP connection
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, to, msg.as_string())

            return {
                "status": "success",
                "mode": "live",
                "to": to,
                "subject": subject,
                "message": "Email sent successfully via Gmail SMTP."
            }
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return {
                "status": "error",
                "message": f"Failed to send email: {str(e)}",
                "fallback_preview": {
                    "to": to,
                    "subject": subject,
                    "body": body
                }
            }
