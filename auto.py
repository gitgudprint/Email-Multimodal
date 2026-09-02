import imaplib
import smtplib
import email
import email.header
import email.utils
import html
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
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))  # seconds between inbox checks
REPLIED_FILE   = os.getenv("REPLIED_FILE", "replied_ids.txt")
ESCALATED_FILE = os.getenv("ESCALATED_FILE", "escalated_ids.txt")
CLOSED_FILE     = os.getenv("CLOSED_FILE", "closed_threads.txt")
CLOSED_MESSAGE_IDS_FILE = os.getenv("CLOSED_MESSAGE_IDS_FILE", "closed_message_ids.txt")
# ── Classification patterns ────────────────────────────────────────────────────
RESET_PATTERNS = [
    # English
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
    # Indonesian
    r"reset.{0,10}(password|kata\s+sandi|sandi|pw|pass)",
    r"(kata\s+sandi|sandi|pw|pass).{0,10}reset",
    r"lupa.{0,10}(password|kata\s+sandi|sandi|pw|pass|kata)",
    r"lupa.{0,10}(login|masuk|akun)",
    r"ubah.{0,10}(password|kata\s+sandi|sandi|pw|pass)",
    r"(tidak\s+bisa|gak\s+bisa|nggak\s+bisa|tidak\s+bisa).{0,15}(login|masuk|log\s+in)",
    r"(akun|account).{0,10}(terkunci|kunci|locked)",
    r"(password|sandi|kata\s+sandi|pk).{0,10}(kadaluarsa|expired|kedaluwarsa)",
    r"recover.{0,10}(akun|account|password|sandi)",
]
COMPILED_RESET_PATTERNS = [re.compile(p, re.IGNORECASE) for p in RESET_PATTERNS]

THANK_YOU_PATTERNS = [
    r"\bthank(s| you)\b",
    r"\bthanks?\s+for\b",
    r"\bterima\s+kasih\b",
    r"\bmakasih\b",
    r"\bappreciate(d|s)?\b",
]
COMPILED_THANK_YOU_PATTERNS = [re.compile(p, re.IGNORECASE) for p in THANK_YOU_PATTERNS]

REQUEST_INTENT_PATTERNS = [
    r"\bplease\b",
    r"\bkindly\b",
    r"\btolong\b",
    r"\bmohon\b",
    r"\bbantu(?:in)?\b",
    r"\bhelp\s+me\b",
    r"\bneed\s+help\b",
    r"\bneed\b",
    r"\bcan(?:'| )?t\b",
    r"\bcannot\b",
    r"\bunable\b",
    r"\blupa\b",
    r"\btidak\s+bisa\b",
    r"\bgak\s+bisa\b",
    r"\bnggak\s+bisa\b",
]
COMPILED_REQUEST_INTENT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in REQUEST_INTENT_PATTERNS]

TECH_ISSUE_PATTERNS = [
    # English
    r"error\b",
    r"bug\b",
    r"crash\b",
    r"not\s+work|doesn'?t\s+work",
    r"broken\b",
    r"failed?\b",
    r"issue\b",
    r"problem\b",
    r"can't\s+access|cannot\s+access|unable\s+to\s+access",
    r"connection",
    r"timeout\b",
    r"500|404|502|503",  # HTTP error codes
    r"slow\b",
    r"lag\b",
    r"freeze\b",
    r"unresponsive\b",
    r"hitam|blank\s+screen",
    r"login\s+failed|authentication\s+failed",
    r"putih\s+screen|white\s+screen",
    r"data\s+loss|lost\s+data",
    # Indonesian
    r"galat\b|kesalahan\b",
    r"bug\b|kutu\b",
    r"(error|crash).{0,10}(fatal|berat|parah)",
    r"(tidak\s+bisa|gak\s+bisa|nggak\s+bisa|tidak).{0,15}(bekerja|jalan|nge?run|work)",
    r"(tidak\s+bisa|gak\s+bisa|nggak\s+bisa|tidak).{0,15}(buka|akses|login|masuk|connect)",
    r"rusak\b",
    r"gagal\b|failed\b",
    r"(masalah|problem|kendala|gangguan|isu|issue)\b",
    r"lambat\b|lelet\b|slow\b",
    r"lag\b|putus\b|delay\b|putus\s+koneksi",
    r"(gak\s+|nggak\s+)?(bisa|bisa).{0,20}(akses|buka|login)\b",
    r"(tidak\s+|gak\s+|nggak\s+)?(bisa|jalan|bekerja)",
    r"eror\b",
    r"koneksi",
    r"timeout\b|time.{0,5}out",
    r"hang\b|hanging\b|freeze\b",
    r"(layar|screen).{0,10}(hitam|blank|putih|white|error|eror)",
]
COMPILED_TECH_PATTERNS = [re.compile(p, re.IGNORECASE) for p in TECH_ISSUE_PATTERNS]

# ── Unsolved/Unresolved patterns (for escalation) ─────────────────────────────
UNSOLVED_PATTERNS = [
    # English
    r"still\s+(not|doesn'?t).{0,15}(work|working|fixed|resolved)",
    r"(still|still\s+have|still\s+getting).{0,10}(error|problem|issue|bug)",
    r"not\s+(yet\s+)?(fixed|resolved|solved)",
    r"(problem|issue).{0,10}(persists|remains|still\s+there)",
    r"hasn'?t.{0,10}(worked|fixed|resolved)",
    r"(trying|tried).{0,15}(but|still|yet).{0,10}(not|no|doesn'?t).{0,10}work",
    r"same.{0,10}(problem|issue|error)",
    r"still\s+broken\b",
    r"not.{0,10}working.{0,10}yet",
    # Indonesian
    r"(tidak|gak|nggak).{0,15}(bisa|bekerja|jalan)",  # Catches: "tidak bisa reset password", "gak bisa login", etc.
    r"(masih|tetap).{0,10}(error|eror|rusak|gagal)",
    r"(masalah|problema|issue).{0,10}(masih|tetap)\s+(ada|terjadi|berlangsung)",
    r"belum.{0,10}(selesai|diperbaiki|fixed|resolved)",
    r"(sudah|udah).{0,15}(coba|try).{0,10}(tapi|but|masih).{0,10}(tidak|gak|nggak)",
    r"sama.{0,10}(masalah|problema|error|eror)",
    r"masih\s+dapat\s+(error|eror|masalah)",
    r"(gak\s+|nggak\s+)?(bisa|bekerja|jalan)\s+(juga|juga\s+enggak)",
]
COMPILED_UNSOLVED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in UNSOLVED_PATTERNS]

# ── Blocked senders (no auto-reply) ────────────────────────────────────────────
BLOCKED_SENDER_PATTERNS = [
    r"^no-?reply@",
    r"^noreply@",
    r"^notification@",
    r"^alert@",
    r"^support@google\.com$",
    r"@google\.com$",
    r"accounts-team@.*\.google\.com",
    r"@mail\.google\.com$",
    r"^mailer-daemon@",
    r"^postmaster@",
    r"^admin@",
    r"@outlook\.com$",  # Block Outlook system emails
    r"@microsoft\.com$",
    r"@amazon\.com$",
    r"security-?alert@",
    r"verify.{0,20}@",
    r"no-?reply",
    r"please-do-not-reply",
]
COMPILED_BLOCKED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in BLOCKED_SENDER_PATTERNS]

def is_blocked_sender(email_address):
    """Return True if the sender email matches a blocked pattern (automated systems)."""
    if not email_address:
        return True
    return any(p.search(email_address) for p in COMPILED_BLOCKED_PATTERNS)

def is_unsolved_reply(subject, body):
    """Return True if email indicates the issue is still not resolved."""
    combined = normalize(subject + " " + body)
    return any(p.search(combined) for p in COMPILED_UNSOLVED_PATTERNS)

def log_unsolved_escalation(sender, subject, message_id, category="unknown"):
    """Log unresolved issues for human review with category context."""
    escalation_file = "unsolved_escalations.log"
    with open(escalation_file, "a") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"{timestamp} | [{category.upper()}] | {sender} | {subject} | MsgID: {message_id}\n")

# ── Reply templates ────────────────────────────────────────────────────────────
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
    }
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_replied_ids():
    """Load the set of Message-IDs we have already replied to from disk."""
    return load_id_set(REPLIED_FILE)

def save_replied_id(message_id):
    """Append a Message-ID to the persistent replied log."""
    append_id(REPLIED_FILE, message_id)

def load_escalated_ids():
    """Load the set of Message-IDs we have already escalated to disk."""
    return load_id_set(ESCALATED_FILE)

def save_escalated_id(message_id):
    """Append a Message-ID to the persistent escalated log."""
    append_id(ESCALATED_FILE, message_id)

def load_closed_threads():
    """Load the set of closed conversation keys from disk."""
    return load_id_set(CLOSED_FILE)

def save_closed_thread(conversation_key):
    """Append a closed conversation key to the persistent thread log."""
    append_id(CLOSED_FILE, conversation_key)

def load_closed_message_ids():
    """Load the set of closed Message-IDs / thread references from disk."""
    return load_id_set(CLOSED_MESSAGE_IDS_FILE)

def save_closed_message_id(message_id):
    """Append a closed Message-ID / thread reference to disk."""
    append_id(CLOSED_MESSAGE_IDS_FILE, message_id)

def load_id_set(file_path):
    """Load a newline-delimited file into a set of stripped values."""
    try:
        with open(file_path, "r") as file_handle:
            return set(line.strip() for line in file_handle if line.strip())
    except FileNotFoundError:
        return set()

def append_id(file_path, value):
    """Append a single newline-delimited value to a state file."""
    with open(file_path, "a") as file_handle:
        file_handle.write(value + "\n")

def load_runtime_state():
    """Load all persistent runtime state containers used by the bot."""
    replied_ids = load_replied_ids()
    escalated_ids = load_escalated_ids()
    closed_threads = load_closed_threads()
    closed_message_ids = load_closed_message_ids()
    return replied_ids, escalated_ids, closed_threads, closed_message_ids

def close_conversation(imap, eid, sender, subject, message_id, category, conv_key, thread_ids, escalated_ids, closed_threads, closed_message_ids):
    """Mark an escalated conversation as closed everywhere we track it."""
    imap.store(eid, "+FLAGS", "\\Seen")
    imap.store(eid, "+FLAGS", "\\Flagged")
    log_unsolved_escalation(sender, subject, message_id, category)
    escalated_ids.add(message_id)
    save_escalated_id(message_id)
    closed_threads.add(conv_key)
    save_closed_thread(conv_key)
    for thread_id in thread_ids:
        if thread_id not in closed_message_ids:
            closed_message_ids.add(thread_id)
            save_closed_message_id(thread_id)

def strip_quoted_content(text):
    """Remove quoted reply/forward content so classification focuses on the new message."""
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r"(?is)<blockquote\b[^>]*>.*?</blockquote>", " ", text)
    text = re.sub(r"(?is)<div[^>]*class=['\"]gmail_quote['\"][^>]*>.*", " ", text)
    text = re.sub(r"(?is)<div[^>]*class=['\"]gmail_extra['\"][^>]*>.*", " ", text)

    lines = []
    quote_marker_patterns = (
        re.compile(r"^on\b.*\bwrote:\s*$", re.IGNORECASE),
        re.compile(r"^from:\s*", re.IGNORECASE),
        re.compile(r"^sent:\s*", re.IGNORECASE),
        re.compile(r"^to:\s*", re.IGNORECASE),
        re.compile(r"^subject:\s*", re.IGNORECASE),
        re.compile(r"original message", re.IGNORECASE),
        re.compile(r"forwarded message", re.IGNORECASE),
        re.compile(r"pesan asli", re.IGNORECASE),
        re.compile(r"pesan diteruskan", re.IGNORECASE),
    )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            continue
        if any(pattern.search(line) for pattern in quote_marker_patterns):
            break
        lines.append(raw_line)

    return "\n".join(lines)

def normalize(text):
    if not text:
        return ""
    text = strip_quoted_content(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def normalize_subject(subject):
    """Normalize a subject and remove common reply/forward prefixes."""
    subject = (subject or "").strip()
    subject = re.sub(r"^(?:re|fw|fwd)\s*:\s*", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"^(?:re|fw|fwd)\s*\[\d+\]\s*:\s*", "", subject, flags=re.IGNORECASE)
    return normalize(subject)

def conversation_key(sender, subject):
    """Build a stable key for a sender + subject thread."""
    return f"{(sender or '').strip().lower()}|{normalize_subject(subject)}"

def extract_thread_ids(msg):
    """Collect all message IDs that identify a thread for the current email."""
    thread_ids = set()

    message_id = (msg.get("Message-ID", "") or "").strip()
    if message_id:
        thread_ids.add(message_id)

    in_reply_to = (msg.get("In-Reply-To", "") or "").strip()
    if in_reply_to:
        thread_ids.update(re.findall(r"<[^>]+>", in_reply_to) or [in_reply_to])

    references = (msg.get("References", "") or "").strip()
    if references:
        thread_ids.update(re.findall(r"<[^>]+>", references) or [references])

    return {thread_id for thread_id in thread_ids if thread_id}

def is_acknowledgement_email(subject, body):
    """Return True for thank-you/follow-up emails that should not trigger auto-replies."""
    combined = normalize(subject + " " + body)
    has_thanks = any(p.search(combined) for p in COMPILED_THANK_YOU_PATTERNS)
    if not has_thanks:
        return False

    has_request_intent = any(p.search(combined) for p in COMPILED_REQUEST_INTENT_PATTERNS)
    return not has_request_intent

def classify_email(subject, body):
    """Classify the email into a category.
    Returns: 'password_reset', 'tech_issue', or None.
    """
    combined = normalize(subject + " " + body)

    has_thanks = any(p.search(combined) for p in COMPILED_THANK_YOU_PATTERNS)
    has_request_intent = any(p.search(combined) for p in COMPILED_REQUEST_INTENT_PATTERNS)

    if has_thanks and not has_request_intent:
        if any(p.search(combined) for p in COMPILED_TECH_PATTERNS):
            return "tech_issue"
        return None
    
    if any(p.search(combined) for p in COMPILED_RESET_PATTERNS):
        return "password_reset"
    elif any(p.search(combined) for p in COMPILED_TECH_PATTERNS):
        return "tech_issue"
    
    return None

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

def send_reply(smtp_server, to_address, message_id, subject, category):
    """Send an auto-reply using the appropriate template for the category."""
    template = REPLY_TEMPLATES.get(category, REPLY_TEMPLATES["tech_issue"])
    
    reply = MIMEMultipart("alternative")
    reply["From"]        = GMAIL_ADDRESS
    reply["To"]          = to_address
    reply["Subject"]     = template["subject"] if not subject.lower().startswith("re:") else subject
    reply["In-Reply-To"] = message_id
    reply["References"]  = message_id
    reply.attach(MIMEText(template["html"], "html"))
    smtp_server.sendmail(GMAIL_ADDRESS, to_address, reply.as_string())

# ── Main loop ─────────────────────────────────────────────────────────────────

def check_and_reply(replied_ids, escalated_ids, closed_threads, closed_message_ids):
    """One inbox scan cycle. Returns updated replied_ids, escalated_ids, and closed state sets."""
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_ADDRESS, APP_PASSWORD)
    imap.select("INBOX")

    _, data = imap.search(None, "ALL")
    email_ids = data[0].split()

    matched = []
    unsolved = []
    for eid in email_ids:
        _, msg_data = imap.fetch(eid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        message_id = msg.get("Message-ID", "").strip()
        thread_ids = extract_thread_ids(msg)

        # Skip if already replied
        if message_id in replied_ids:
            continue

        # Skip if this exact message was already escalated and closed
        if message_id in escalated_ids:
            continue

        # Skip if any thread reference is already closed
        if thread_ids & closed_message_ids:
            continue

        subject = decode_subject(msg.get("Subject", ""))
        body    = get_body(msg)
        sender  = email.utils.parseaddr(msg.get("From"))[1]
        conv_key = conversation_key(sender, subject)

        # Skip closed conversation threads so follow-ups don't get auto-replied again
        if conv_key in closed_threads:
            continue

        # Check if this is an unsolved/unresolved reply (escalation) — check ALL categories
        if is_unsolved_reply(subject, body):
            if not is_blocked_sender(sender):
                # Skip if already escalated
                if message_id not in escalated_ids:
                    # Classify to get category context for escalation log
                    category = classify_email(subject, body) or "other"
                    unsolved.append((eid, sender, message_id, subject, category, conv_key, thread_ids))
            continue  # Don't auto-reply, flag for human review instead

        category = classify_email(subject, body)
        if category:  # 'password_reset' or 'tech_issue'
            # Skip automated/system senders
            if is_blocked_sender(sender):
                print(f"  ⊘ Skipped (automated sender): {sender}")
                continue
            
            matched.append((eid, sender, message_id, subject, category))

    if matched:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {len(matched)} new match(es) — sending replies...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, APP_PASSWORD)
            for eid, sender, message_id, subject, category in matched:
                try:
                    send_reply(smtp, sender, message_id, subject, category)
                    replied_ids.add(message_id)
                    save_replied_id(message_id)
                    # Tag the email with a custom Gmail label so it's easy to audit
                    imap.store(eid, "+FLAGS", "\\Answered")
                    print(f"    → {category.upper().replace('_', ' ')}: Replied to {sender} | {subject}")
                except Exception as e:
                    print(f"    ✗ Failed to reply to {sender}: {e}")
    
    # Handle unsolved/escalated emails
    if unsolved:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] ⚠ {len(unsolved)} UNSOLVED issue(s) — escalating for human review...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, APP_PASSWORD)
            for eid, sender, message_id, subject, category, conv_key, thread_ids in unsolved:
                try:
                    # Send escalation reply to customer
                    send_reply(smtp, sender, message_id, subject, "escalated")
                    close_conversation(
                        imap,
                        eid,
                        sender,
                        subject,
                        message_id,
                        category,
                        conv_key,
                        thread_ids,
                        escalated_ids,
                        closed_threads,
                        closed_message_ids,
                    )
                    print(f"    ⚠ ESCALATED [{category.upper()}]: {sender} | {subject} (reply sent)")
                except Exception as e:
                    print(f"    ✗ Failed to escalate {sender}: {e}")
    
    if not matched and not unsolved:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] No new matches.")

    imap.logout()
    return replied_ids, escalated_ids, closed_threads, closed_message_ids


def main():
    print("=== Adira Auto-Reply Bot started (Ctrl+C to stop) ===")
    replied_ids, escalated_ids, closed_threads, closed_message_ids = load_runtime_state()
    print(f"Loaded {len(replied_ids)} previously replied Message-ID(s).")
    print(f"Loaded {len(escalated_ids)} previously escalated Message-ID(s).\n")
    print(f"Loaded {len(closed_threads)} closed conversation(s).\n")
    print(f"Loaded {len(closed_message_ids)} closed thread Message-ID(s).\n")

    try:
        while True:
            try:
                replied_ids, escalated_ids, closed_threads, closed_message_ids = check_and_reply(
                    replied_ids, escalated_ids, closed_threads, closed_message_ids
                )
            except Exception as e:
                print(f"  [ERROR] {e} — akan coba lagi dalam {CHECK_INTERVAL}s...")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n=== Bot dihentikan. Sampai jumpa! ===")


if __name__ == "__main__":
    main()
