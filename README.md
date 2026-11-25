# Support Email Auto-Reply Bot

A Python bot that answers routine support emails in a Gmail inbox. It recognizes two kinds of requests, password resets and technical problems, and replies with the matching step-by-step instructions. When a user writes back that the problem is still there, the bot stops replying, stars the email and logs it so a person can take over.

It understands emails written in English and Indonesian, including informal Indonesian such as "gak bisa login" or "aplikasinya error terus".

## Built with

Python 3.9+ and the standard library only for the core logic: `imaplib` to read the inbox, `smtplib` to send HTML replies, and `re` for matching. Configuration comes from a `.env` file through `python-dotenv`.

## How it works

1. Every few seconds the bot reads the inbox over IMAP.
2. It removes quoted replies from each email, then normalizes the text (accents, punctuation, spacing) so small differences in spelling still match.
3. It skips messages from automated senders such as `no-reply@` and `mailer-daemon@` so it never answers system mail or gets into a reply loop.
4. It classifies the email as a password reset or a technical issue and sends the matching HTML reply.
5. If a later message in the same conversation says the issue is not fixed, the bot escalates instead of replying again: it marks the email as starred and writes the sender, subject and category to `unsolved_escalations.log`.

## What makes it more than a keyword filter

- About 110 regular expressions in English and Indonesian cover password resets, technical issues, "still not working" replies, thank-you messages and blocked senders.
- It tracks conversations by sender, subject and email thread headers, so replies in one thread are handled as one case.
- The IDs of replied, escalated and closed messages are saved to files. After a restart the bot does not answer the same email twice.
- A failed inbox check is logged and retried on the next cycle instead of stopping the bot.

The code is about 620 lines of Python, split into the main loop (`auto.py`), classification (`classifier.py`, `patterns.py`), text cleanup (`text_utils.py`), sending (`email_client.py`) and saved state (`state_store.py`).

## Example

An email that says `I forgot my password and can't log in` gets the password reset reply. If the sender answers `It still doesn't work`, the bot escalates it:

```text
[INFO] Matched category: PASSWORD_RESET
[INFO] Reply sent and Message-ID stored
[WARN] Unresolved reply detected, escalated for human review
```

## Running it

You need a Gmail account with IMAP enabled and a Google App Password, which requires 2-Step Verification.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set GMAIL_ADDRESS and APP_PASSWORD
python auto.py
```

Optional settings in `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `CHECK_INTERVAL` | `5` | Seconds between inbox checks |
| `REPLIED_FILE` | `replied_ids.txt` | Message IDs that already got a reply |
| `ESCALATED_FILE` | `escalated_ids.txt` | Message IDs that were escalated |
| `CLOSED_FILE` | `closed_threads.txt` | Conversations closed after escalation |
| `CLOSED_MESSAGE_IDS_FILE` | `closed_message_ids.txt` | Message IDs in closed conversations |

Check `unsolved_escalations.log` regularly for emails that need a person.
