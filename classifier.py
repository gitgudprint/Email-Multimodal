from patterns import (
    COMPILED_BLOCKED_PATTERNS,
    COMPILED_REQUEST_INTENT_PATTERNS,
    COMPILED_RESET_PATTERNS,
    COMPILED_TECH_PATTERNS,
    COMPILED_THANK_YOU_PATTERNS,
    COMPILED_UNSOLVED_PATTERNS,
)
from text_utils import normalize


def is_blocked_sender(email_address):
    if not email_address:
        return True
    return any(pattern.search(email_address) for pattern in COMPILED_BLOCKED_PATTERNS)


def is_unsolved_reply(subject, body):
    combined = normalize(subject + " " + body)
    return any(pattern.search(combined) for pattern in COMPILED_UNSOLVED_PATTERNS)


def is_acknowledgement_email(subject, body):
    combined = normalize(subject + " " + body)
    has_thanks = any(pattern.search(combined) for pattern in COMPILED_THANK_YOU_PATTERNS)
    if not has_thanks:
        return False

    has_request_intent = any(pattern.search(combined) for pattern in COMPILED_REQUEST_INTENT_PATTERNS)
    return not has_request_intent


def classify_email(subject, body):
    combined = normalize(subject + " " + body)

    has_thanks = any(pattern.search(combined) for pattern in COMPILED_THANK_YOU_PATTERNS)
    has_request_intent = any(pattern.search(combined) for pattern in COMPILED_REQUEST_INTENT_PATTERNS)

    if has_thanks and not has_request_intent:
        if any(pattern.search(combined) for pattern in COMPILED_TECH_PATTERNS):
            return "tech_issue"
        return None

    if any(pattern.search(combined) for pattern in COMPILED_RESET_PATTERNS):
        return "password_reset"
    if any(pattern.search(combined) for pattern in COMPILED_TECH_PATTERNS):
        return "tech_issue"

    return None
