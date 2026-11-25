import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_TLS,
    SMTP_SSL,
    FRONTEND_URL,
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger(__name__)


def build_password_reset_html(username: str, reset_url: str, expire_minutes: int) -> str:
    """Build an HTML email template for password reset."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f8fafc;
      margin: 0;
      padding: 0;
      color: #1e293b;
    }}
    .container {{
      max-width: 560px;
      margin: 40px auto;
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .header {{
      background: #4f46e5;
      padding: 32px 40px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      color: #ffffff;
      font-size: 24px;
      letter-spacing: -0.5px;
    }}
    .header p {{
      margin: 4px 0 0;
      color: #c7d2fe;
      font-size: 14px;
    }}
    .content {{
      padding: 40px;
    }}
    .greeting {{
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #0f172a;
    }}
    .message {{
      font-size: 15px;
      line-height: 1.6;
      color: #475569;
      margin-bottom: 28px;
    }}
    .btn-container {{
      text-align: center;
      margin: 32px 0;
    }}
    .btn {{
      display: inline-block;
      background-color: #4f46e5;
      color: #ffffff !important;
      text-decoration: none;
      font-weight: 600;
      font-size: 15px;
      padding: 14px 32px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(79, 70, 229, 0.25);
    }}
    .btn:hover {{
      background-color: #4338ca;
    }}
    .link-fallback {{
      font-size: 13px;
      color: #64748b;
      word-break: break-all;
      line-height: 1.5;
      margin-top: 24px;
      padding: 16px;
      background: #f1f5f9;
      border-radius: 8px;
    }}
    .link-fallback a {{
      color: #4f46e5;
    }}
    .footer {{
      border-top: 1px solid #f1f5f9;
      padding: 24px 40px;
      background: #fafafa;
      font-size: 12px;
      color: #94a3b8;
      text-align: center;
      line-height: 1.5;
    }}
    .security-note {{
      font-size: 13px;
      color: #64748b;
      margin-top: 24px;
      border-left: 3px solid #cbd5e1;
      padding-left: 12px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>ChurnIQ</h1>
      <p>Customer Churn Prediction & Retention Analytics</p>
    </div>
    <div class="content">
      <div class="greeting">Hello {username},</div>
      <p class="message">
        We received a request to reset the password for your ChurnIQ account.
        Click the button below to choose a new password. This link is valid for <strong>{expire_minutes} minutes</strong>.
      </p>

      <div class="btn-container">
        <a href="{reset_url}" class="btn" target="_blank" rel="noopener noreferrer">Reset Password</a>
      </div>

      <div class="security-note">
        <strong>Didn't request this?</strong> If you did not make this request, you can safely ignore this email.
        Your password will remain unchanged and your account is secure.
      </div>

      <div class="link-fallback">
        If the button above doesn't work, copy and paste this link into your browser:<br>
        <a href="{reset_url}">{reset_url}</a>
      </div>
    </div>
    <div class="footer">
      This is an automated message from ChurnIQ. Please do not reply directly to this email.<br>
      &copy; ChurnIQ Analytics. All rights reserved.
    </div>
  </div>
</body>
</html>"""


def build_password_reset_text(username: str, reset_url: str, expire_minutes: int) -> str:
    """Build a plain-text email body for password reset."""
    return f"""Hello {username},

We received a request to reset the password for your ChurnIQ account.

Please visit the following link to choose a new password (valid for {expire_minutes} minutes):
{reset_url}

If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged and your account is secure.

Best regards,
The ChurnIQ Team
"""


class EmailService:
    """Service to deliver transactional emails such as password reset links."""

    @staticmethod
    def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
        """
        Send a password reset email to the specified recipient.
        Falls back to console/logger logging when SMTP is unconfigured so local
        testing and development environments work without an external SMTP server.
        """
        # Construct reset URL
        base_url = FRONTEND_URL.rstrip("/")
        reset_url = f"{base_url}/?token={reset_token}#reset-password"

        text_content = build_password_reset_text(username, reset_url, PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        html_content = build_password_reset_html(username, reset_url, PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        if not SMTP_HOST:
            logger.warning(
                "SMTP_HOST is not configured. Password reset link generated for user '%s' (%s):\n--> %s",
                username,
                to_email,
                reset_url,
            )
            # Return true to allow development/testing flow without an active mail server
            return True

        msg = EmailMessage()
        msg["Subject"] = "Reset Your ChurnIQ Password"
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype="html")

        try:
            if SMTP_SSL:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                    if SMTP_USER and SMTP_PASSWORD:
                        server.login(SMTP_USER, SMTP_PASSWORD)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                    if SMTP_TLS:
                        server.starttls()
                    if SMTP_USER and SMTP_PASSWORD:
                        server.login(SMTP_USER, SMTP_PASSWORD)
                    server.send_message(msg)

            logger.info("Password reset email successfully dispatched to %s", to_email)
            return True
        except Exception as exc:
            logger.error("Failed to send password reset email to %s: %s", to_email, str(exc), exc_info=True)
            # Re-log reset link for admin/operator visibility in case mail transport had an issue
            logger.warning("Fallback reset URL for %s: %s", to_email, reset_url)
            return False
