import email
import email.header
import re
import html
import unicodedata


def strip_quoted_content(text):
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
    subject = (subject or "").strip()
    subject = re.sub(r"^(?:re|fw|fwd)\s*:\s*", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"^(?:re|fw|fwd)\s*\[\d+\]\s*:\s*", "", subject, flags=re.IGNORECASE)
    return normalize(subject)


def conversation_key(sender, subject):
    return f"{(sender or '').strip().lower()}|{normalize_subject(subject)}"


def extract_thread_ids(msg):
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
