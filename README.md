# Auto-Reply Bot

Automatically detects password-reset and tech-issue emails in a Gmail inbox and sends a helpful reply — continuously, with duplicate-reply protection.

## Features

- Scans all emails (read and unread) every 30 seconds
- Classifies emails into two categories: **Password Reset** and **Tech Issue**
- Detects common password-reset and support-issue intent using normalized regex matching
- Sends an HTML auto-reply with step-by-step reset instructions or troubleshooting steps
- Detects unresolved issues and escalates replies indicating the problem persists
- Blocks automated senders (Google, Outlook, no-reply, mailer-daemon, etc.) to avoid replying to system emails
- Persists replied Message-IDs so the same email is never replied to twice, even across restarts
- Graceful error recovery — a failed scan cycle is logged and retried

## Requirements

- Python 3.9+
- A Gmail account with **IMAP enabled** and a **Google App Password** (requires 2-Step Verification)
- Supports emails in English and Indonesian (Bahasa Indonesia)

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

## Generated Files

The bot creates or maintains these files:

| File | Purpose |
|---|---|
| `.env` | Your credentials (gitignored) |
| `replied_ids.txt` | Tracks Message-IDs that have already been replied to |
| `escalated_ids.txt` | Tracks Message-IDs that have already been escalated |
| `closed_threads.txt` | Tracks closed sender + subject conversation threads after escalation |
| `closed_message_ids.txt` | Tracks closed Message-IDs and reply-chain references after escalation |
| `unsolved_escalations.log` | Logs unresolved issues requiring human review |

Check `unsolved_escalations.log` regularly to review escalated tickets.

## Configuration

All options live in `.env`:

| Variable | Default | Description |
|---|---|---|
| `GMAIL_ADDRESS` | *(required)* | Gmail address to monitor and send from |
| `APP_PASSWORD` | *(required)* | 16-character Google App Password |
| `CHECK_INTERVAL` | `30` | Seconds between inbox scans |
| `REPLIED_FILE` | `replied_ids.txt` | File to persist replied Message-IDs |

## How matching works

The bot normalizes email text by stripping accents, punctuation, and extra whitespace, then checks it against patterns for two categories. It supports both English and Indonesian languages.

### Password Reset Patterns

**English:**
- `reset password`, `password reset`
- `forgot password`, `forgot my pass`
- `change password`
- `can't log in`, `unable to login`
- `lost password`
- `recover account/password/access`
- `account locked`, `password expired`

**Indonesian (Bahasa Indonesia):**
- `reset kata sandi`, `reset sandi`, `reset pw`
- `lupa password`, `lupa kata sandi`, `lupa sandi`, `lupa pw`
- `ubah password`, `ubah sandi`
- `gak bisa login`, `nggak bisa login`, `tidak bisa masuk`
- `akun terkunci`, `akun kunci`
- `password kadaluarsa`, `sandi kedaluwarsa`
- `recover akun`, `recover account`

### Tech Issue Patterns

**English:**
- `error`, `bug`, `crash`
- `not working`, `doesn't work`, `broken`
- `failed`, `issue`, `problem`
- `can't access`, `cannot access`
- `connection`, `timeout`
- HTTP error codes: `500`, `404`, `502`, `503`
- `slow`, `lag`, `freeze`, `unresponsive`
- `login failed`, `authentication failed`
- `blank screen`, `white screen`, etc.

**Indonesian (Bahasa Indonesia):**
- `galat`, `kesalahan` (error)
- `bug`, `kutu` (bug)
- `tidak bisa bekerja`, `gak bisa jalan` (not working)
- `tidak bisa buka`, `gak bisa akses` (can't access)
- `rusak` (broken)
- `gagal` (failed)
- `masalah`, `problem`, `kendala`, `gangguan` (issue/problem)
- `lambat`, `lelet` (slow)
- `lag`, `putus`, `delay` (lag)
- `layar hitam`, `layar putih` (black/white screen)
- `eror` (error - common typo)
- `koneksi` (connection)

### Unresolved Detection Patterns

These patterns trigger escalation when a reply indicates the issue is still not fixed.

**English:**
- `still not working`, `still doesn't work`
- `still have error`, `still getting error`
- `not yet fixed`, `problem persists`
- `hasn't fixed`, `still broken`
- `same problem`, `same issue`

**Indonesian (Bahasa Indonesia):**
- `masih tidak bisa`, `tetap rusak`
- `masih dapat error`, `masih dapat eror`
- `belum selesai`, `belum diperbaiki`
- `masalah masih ada`, `sama masalah`
- `udah coba tapi masih gak bisa`

### Automated Sender Blocking

The bot automatically skips emails from automated systems to avoid spam loops.

Blocked patterns include:
- `no-reply@`, `noreply@`
- `@google.com`, `@microsoft.com`, `@amazon.com`, `@outlook.com`
- `mailer-daemon@`, `postmaster@`, `admin@`
- `security-alert@`, `verify@`
- And more system sender patterns

Works with user emails from any client (Outlook, Yahoo, Apple Mail, etc.) while stopping system notifications.

## Escalation & Unsolved Issues

If a customer replies to any category saying the issue is still not fixed, the bot automatically:

1. Detects the unresolved reply using the patterns above
2. Classifies the original issue category
3. Flags the email as starred in Gmail
4. Logs the escalation to `unsolved_escalations.log` with category, timestamp, sender, and subject

This allows support staff to quickly understand the context and prioritize unresolved issues by type.

## License

Add your license information here if needed.
