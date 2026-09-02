import email
import imaplib
import smtplib
import time
from datetime import datetime

from classifier import classify_email, is_blocked_sender, is_unsolved_reply
from config import APP_PASSWORD, CHECK_INTERVAL, GMAIL_ADDRESS
from email_client import decode_subject, get_body, send_reply
from state_store import close_conversation, load_runtime_state
from text_utils import conversation_key, extract_thread_ids


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

        if message_id in replied_ids:
            continue
        if message_id in escalated_ids:
            continue
        if thread_ids & closed_message_ids:
            continue

        subject = decode_subject(msg.get("Subject", ""))
        body = get_body(msg)
        sender = email.utils.parseaddr(msg.get("From"))[1]
        conv_key = conversation_key(sender, subject)

        if conv_key in closed_threads:
            continue

        if is_unsolved_reply(subject, body):
            if not is_blocked_sender(sender) and message_id not in escalated_ids:
                category = classify_email(subject, body) or "other"
                unsolved.append((eid, sender, message_id, subject, category, conv_key, thread_ids))
            continue

        category = classify_email(subject, body)
        if category:
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
                    imap.store(eid, "+FLAGS", "\\Answered")
                    print(f"    → {category.upper().replace('_', ' ')}: Replied to {sender} | {subject}")
                except Exception as e:
                    print(f"    ✗ Failed to reply to {sender}: {e}")

    if unsolved:
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] ⚠ {len(unsolved)} UNSOLVED issue(s) — escalating for human review...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, APP_PASSWORD)
            for eid, sender, message_id, subject, category, conv_key, thread_ids in unsolved:
                try:
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
