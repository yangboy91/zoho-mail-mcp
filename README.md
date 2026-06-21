# Zoho Mail MCP

A tiny [MCP](https://modelcontextprotocol.io) server that lets Claude read,
search, send, and reply to mail on a Zoho mailbox over standard IMAP/SMTP.
No OAuth — it authenticates with a Zoho **application-specific password**.

## Tools

| Tool | What it does |
|------|--------------|
| `search_emails` | Search/list a folder, newest first (free-text + unread filter) |
| `read_email`    | Read one message's full plain-text body by UID |
| `send_email`    | Send a new message (to / cc / bcc) |
| `reply_email`   | Reply to a message, preserving subject + threading headers |

## 1. Generate a Zoho app-specific password

1. Sign in at <https://accounts.zoho.com> → **Security**.
2. Enable **Two-Factor Authentication** if it isn't already (required for app
   passwords).
3. Under **App Passwords**, click **Generate New Password**, name it
   `claude-mcp`, and copy the password Zoho shows you.

> Use this generated password — **not** your normal login password.
> IMAP/SMTP access must also be enabled in Zoho Mail → Settings → Mail Accounts.

## 2. Install

```bash
git clone https://github.com/yangboy91/zoho-mail-mcp.git
cd zoho-mail-mcp
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## 3. Set credentials

The server reads these env vars:

| Var | Required | Default |
|-----|----------|---------|
| `ZOHO_EMAIL` | yes | — |
| `ZOHO_APP_PASSWORD` | yes | — |
| `ZOHO_IMAP_HOST` | no | `imap.zoho.com` |
| `ZOHO_SMTP_HOST` | no | `smtp.zoho.com` |
| `ZOHO_SMTP_PORT` | no | `465` |

> Non‑`.com` data centers: use `imap.zoho.eu` / `smtp.zoho.eu`,
> `imap.zoho.in` / `smtp.zoho.in`, etc.

## 4. Test the connection

```bash
ZOHO_EMAIL="you@example.com" \
ZOHO_APP_PASSWORD="xxxx-xxxx-xxxx" \
./.venv/bin/python test_connection.py
```

You should see your 5 most recent inbox subjects and `SMTP ... ok`.

## 5. Register with Claude Code

Run this from the cloned repo directory (use absolute paths to `.venv/bin/python`
and `server.py`):

```bash
claude mcp add zoho-mail \
  --env ZOHO_EMAIL="you@example.com" \
  --env ZOHO_APP_PASSWORD="xxxx-xxxx-xxxx" \
  -- "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

Then restart Claude Code. Ask: *"search my Zoho inbox for invoices"*.

For the Claude Desktop app, add the equivalent block to
`claude_desktop_config.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "zoho-mail": {
      "command": "/absolute/path/to/zoho-mail-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/zoho-mail-mcp/server.py"],
      "env": {
        "ZOHO_EMAIL": "you@example.com",
        "ZOHO_APP_PASSWORD": "xxxx-xxxx-xxxx"
      }
    }
  }
}
```
