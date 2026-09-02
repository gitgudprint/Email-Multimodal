from datetime import datetime

from config import CLOSED_FILE, CLOSED_MESSAGE_IDS_FILE, ESCALATED_FILE, REPLIED_FILE


def load_id_set(file_path):
    try:
        with open(file_path, "r") as file_handle:
            return set(line.strip() for line in file_handle if line.strip())
    except FileNotFoundError:
        return set()


def append_id(file_path, value):
    with open(file_path, "a") as file_handle:
        file_handle.write(value + "\n")


def load_replied_ids():
    return load_id_set(REPLIED_FILE)


def save_replied_id(message_id):
    append_id(REPLIED_FILE, message_id)


def load_escalated_ids():
    return load_id_set(ESCALATED_FILE)


def save_escalated_id(message_id):
    append_id(ESCALATED_FILE, message_id)


def load_closed_threads():
    return load_id_set(CLOSED_FILE)


def save_closed_thread(conversation_key):
    append_id(CLOSED_FILE, conversation_key)


def load_closed_message_ids():
    return load_id_set(CLOSED_MESSAGE_IDS_FILE)


def save_closed_message_id(message_id):
    append_id(CLOSED_MESSAGE_IDS_FILE, message_id)


def load_runtime_state():
    replied_ids = load_replied_ids()
    escalated_ids = load_escalated_ids()
    closed_threads = load_closed_threads()
    closed_message_ids = load_closed_message_ids()
    return replied_ids, escalated_ids, closed_threads, closed_message_ids


def log_unsolved_escalation(sender, subject, message_id, category="unknown"):
    escalation_file = "unsolved_escalations.log"
    with open(escalation_file, "a") as file_handle:
        timestamp = datetime.now().isoformat()
        file_handle.write(f"{timestamp} | [{category.upper()}] | {sender} | {subject} | MsgID: {message_id}\n")


def close_conversation(imap, eid, sender, subject, message_id, category, conv_key, thread_ids, escalated_ids, closed_threads, closed_message_ids):
    imap.store(eid, "+FLAGS", "\\Seen")
    imap.store(eid, "+FLAGS", "\\Flagged")
    log_unsolved_escalation(sender, subject, message_id, category)
    escalated_ids.add(message_id)
    save_escalated_id(message_id)
    closed_threads.add(conv_key)
    save_closed_thread(conv_key)
    closed_message_ids.add(message_id)
    save_closed_message_id(message_id)
    for thread_id in thread_ids:
        if thread_id not in closed_message_ids:
            closed_message_ids.add(thread_id)
            save_closed_message_id(thread_id)
