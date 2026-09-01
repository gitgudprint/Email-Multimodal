import imaplib
import smtplib
import email
import email.header
import email.utils
import os
import re
import time
import unicodedata
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
GMAIL_ADDRESS  = os.environ["GMAIL_ADDRESS"]
APP_PASSWORD   = os.environ["APP_PASSWORD"]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))  # seconds between inbox checks
REPLIED_FILE   = os.getenv("REPLIED_FILE", "replied_ids.txt")

# ── Reset-intent patterns ─────────────────────────────────────────────────────
RESET_PATTERNS = [
    r"reset.{0,10}password",
    r"password.{0,10}reset",
    r"forgot.{0,10}password",
    r"forgot.{0,10}pass\b",
    r"change.{0,10}password",
    r"can.{0,5}t.{0,10}log.{0,5}in",
    r"unable.{0,10}log.{0,5}in",
    r"lost.{0,10}password",
    r"recover.{0,10}(account|password|access)",
    r"account.{0,10}locked",
    r"password.{0,10}expired",
]
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in RESET_PATTERNS]

# ── Auto-reply body ───────────────────────────────────────────────────────────
REPLY_SUBJECT = "Re: Password Reset Instructions"
REPLY_HTML = """
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
    <p>Best regards,<br>Adira Automation</p>
  </body>
</html>
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_replied_ids():
    """Load the set of Message-IDs we have already replied to from disk."""
    try:
        with open(REPLIED_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_replied_id(message_id):
    """Append a Message-ID to the persistent replied log."""
    with open(REPLIED_FILE, "a") as f:
        f.write(message_id + "\n")

def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def is_password_reset_request(subject, body):
    combined = normalize(subject + " " + body)
    return any(p.search(combined) for p in COMPILED_PATTERNS)

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
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
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

def send_reply(smtp_server, to_address, message_id, subject):
    reply = MIMEMultipart("alternative")
    reply["From"]        = GMAIL_ADDRESS
    reply["To"]          = to_address
    reply["Subject"]     = REPLY_SUBJECT if not subject.lower().startswith("re:") else subject
    reply["In-Reply-To"] = message_id
    reply["References"]  = message_id
    reply.attach(MIMEText(REPLY_HTML, "html"))
    smtp_server.sendmail(GMAIL_ADDRESS, to_address, reply.as_string())

# ── Main loop ─────────────────────────────────────────────────────────────────

def check_and_reply(replied_ids):
    """One inbox scan cycle. Returns updated replied_ids set."""
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_ADDRESS, APP_PASSWORD)
    imap.select("INBOX")

    _, data = imap.search(None, "ALL")
    email_ids = data[0].split()

    matched = []
    for eid in email_ids:
        _, msg_data = imap.fetch(eid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        message_id = msg.get("Message-ID", "").strip()

        # Skip if already replied
        if message_id in replied_ids:
            continue

        subject = decode_subject(msg.get("Subject", ""))
        body    = get_body(msg)

        if is_password_reset_request(subject, body):
            sender = email.utils.parseaddr(msg.get("From"))[1]
            matched.append((eid, sender, message_id, subject))

    if matched:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {len(matched)} new match(es) — sending replies...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, APP_PASSWORD)
            for eid, sender, message_id, subject in matched:
                try:
                    send_reply(smtp, sender, message_id, subject)
                    replied_ids.add(message_id)
                    save_replied_id(message_id)
                    # Tag the email with a custom Gmail label so it's easy to audit
                    imap.store(eid, "+FLAGS", "\\Answered")
                    print(f"    → Replied to {sender} | Subject: {subject}")
                except Exception as e:
                    print(f"    ✗ Failed to reply to {sender}: {e}")
    else:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] No new matches.")

    imap.logout()
    return replied_ids


print("=== Adira Auto-Reply Bot started (Ctrl+C to stop) ===")
replied_ids = load_replied_ids()
print(f"Loaded {len(replied_ids)} previously replied Message-ID(s).\n")

try:
    while True:
        try:
            replied_ids = check_and_reply(replied_ids)
        except Exception as e:
            print(f"  [ERROR] {e} — akan coba lagi dalam {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)
except KeyboardInterrupt:
    print("\n=== Bot dihentikan. Sampai jumpa! ===")
