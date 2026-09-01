# Auto-Reply Bot

Automatically detects password-reset-related emails in a Gmail inbox and sends a helpful reply — continuously, with duplicate-reply protection.

## Features

- Scans all emails (read and unread) every 30 seconds
- Detects password-reset intent using normalized regex matching (handles typos, varied phrasing, Outlook-encoded headers)
- Sends an HTML auto-reply with step-by-step reset instructions
- Persists replied Message-IDs so the same email is never replied to twice, even across restarts
- Graceful error recovery — a failed scan cycle is logged and retried

## Requirements

- Python 3.9+
- A Gmail account with **IMAP enabled** and a **Google App Password** (requires 2-Step Verification)

## Setup

### 1. Enable Gmail IMAP

Gmail Settings → **See all settings** → **Forwarding and POP/IMAP** → Enable IMAP → Save.

### 2. Generate a Google App Password

[myaccount.google.com](https://myaccount.google.com) → Security → 2-Step Verification → App passwords → create one for "Mail".

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your Gmail address and App Password:

```
GMAIL_ADDRESS=you@gmail.com
APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 5. Run

```bash
python auto.py
```

Press `Ctrl+C` to stop.

## Configuration

All options live in `.env`:

| Variable | Default | Description |
|---|---|---|
| `GMAIL_ADDRESS` | *(required)* | Gmail address to monitor and send from |
| `APP_PASSWORD` | *(required)* | 16-character Google App Password |
| `CHECK_INTERVAL` | `30` | Seconds between inbox scans |
| `REPLIED_FILE` | `replied_ids.txt` | File to persist replied Message-IDs |

## How matching works

The bot normalizes email text (strips accents, punctuation, extra whitespace) then checks it against patterns including:

- `reset password` / `password reset`
- `forgot password` / `forgot my pass`
- `change password`
- `can't log in` / `unable to login`
- `lost password`
- `recover account / password / access`
- `account locked`
- `password expired`

Works with senders using any email client (Outlook, Yahoo, Apple Mail, etc.).
