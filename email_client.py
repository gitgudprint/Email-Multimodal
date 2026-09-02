import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_ADDRESS

REPLY_TEMPLATES = {
    "password_reset": {
        "subject": "Re: Password Reset Instructions",
        "html": """
<html>
  <body>
    <p>Hi,</p>
    <p>We received your request to reset your password. Please follow the steps below:</p>
    <ol>
      <li>Go to the login page and click <strong>"Forgot Password"</strong>.</li>
      <li>Enter your registered email address and click <strong>"Send Reset Link"</strong>.</li>
      <li>Check your inbox for a password reset email (check spam if needed).</li>
      <li>Click the link in the email — it expires in <strong>30 minutes</strong>.</li>
      <li>Enter and confirm your new password.</li>
      <li>Log in with your new password.</li>
    </ol>
    <p>If you did not request a password reset, please ignore this email.</p>
    <p>Best regards,<br>Adira Support Team</p>
  </body>
</html>
"""
    },
    "tech_issue": {
        "subject": "Re: Troubleshooting Your Reported Issue",
        "html": """
<html>
  <body>
    <p>Hi,</p>
    <p>Thank you for reporting this issue. We take technical problems seriously and our support team is looking into it.</p>
    <p><strong>In the meantime, here are some troubleshooting steps:</strong></p>
    <ol>
      <li>Refresh your browser or restart the app.</li>
      <li>Clear your browser cache and cookies (or app cache for mobile).</li>
      <li>Try using a different browser or device if available.</li>
      <li>Check if you're using the latest version of our app.</li>
      <li>Ensure your internet connection is stable.</li>
    </ol>
    <p><strong>What we're doing:</strong> Our engineers are investigating your report and working on a fix. We'll update you as soon as we know more.</p>
    <p>If the issue persists or you have additional details, please reply to this email.</p>
    <p>Best regards,<br>Adira Support Team</p>
  </body>
</html>
"""
    },
    "escalated": {
        "subject": "Re: We're Looking Into This",
        "html": """
<html>
  <body>
    <p>Hi,</p>
    <p>Thank you for your follow-up. We understand this issue is still unresolved and we take that very seriously.</p>
    <p><strong>Here's what we're doing:</strong></p>
    <ul>
      <li>Your issue has been escalated to our senior support team for immediate investigation.</li>
      <li>Our engineers are prioritizing your case to find a solution.</li>
      <li>You will be contacted within the next 24 hours with an update or potential fix.</li>
    </ul>
    <p>We apologize for the inconvenience and appreciate your patience. Your issue is important to us.</p>
    <p>Best regards,<br>Adira Support Team</p>
  </body>
</html>
"""
    },
}


def get_template(category):
    return REPLY_TEMPLATES.get(category, REPLY_TEMPLATES["tech_issue"])


def decode_subject(raw_subject):
    if not raw_subject:
        return ""
    parts = email.header.decode_header(raw_subject)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type in ("text/plain", "text/html"):
                try:
                    body += part.get_payload(decode=True).decode(errors="replace")
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="replace")
        except Exception:
            pass
    return body


def send_reply(smtp_server, to_address, message_id, subject, category):
    template = get_template(category)

    reply = MIMEMultipart("alternative")
    reply["From"] = GMAIL_ADDRESS
    reply["To"] = to_address
    reply["Subject"] = template["subject"] if not subject.lower().startswith("re:") else subject
    reply["In-Reply-To"] = message_id
    reply["References"] = message_id
    reply.attach(MIMEText(template["html"], "html"))
    smtp_server.sendmail(GMAIL_ADDRESS, to_address, reply.as_string())
