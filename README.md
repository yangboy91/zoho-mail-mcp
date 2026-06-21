# Zoho Mail MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-compatible-8A2BE2.svg)](https://modelcontextprotocol.io)

A tiny [MCP](https://modelcontextprotocol.io) server that lets an AI assistant
read, search, send, and reply to mail on a Zoho mailbox over standard IMAP/SMTP.
No OAuth — it authenticates with a Zoho **application-specific password**.

MCP is an open standard, so this works with **any MCP-compatible client** —
Claude Code, Claude Desktop, Cursor, Cline, Continue, and others. Setup is the
same everywhere: point your client at `.venv/bin/python server.py` and pass the
two env vars. Client-specific examples are in
[§5 Register with an MCP client](#5-register-with-an-mcp-client).

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
   `zoho-mcp`, and copy the password Zoho shows you.

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

## 5. Register with an MCP client

Every client needs the same three things: the **command**
(`.venv/bin/python`), the **server path** (`server.py`), and the two **env
vars**. Use absolute paths — most clients don't run from the repo directory.

### Claude Code

Run from the cloned repo directory:

```bash
claude mcp add zoho-mail \
  --env ZOHO_EMAIL="you@example.com" \
  --env ZOHO_APP_PASSWORD="xxxx-xxxx-xxxx" \
  -- "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

Then restart Claude Code and ask: *"search my Zoho inbox for invoices"*.

### Claude Desktop

Add to `claude_desktop_config.json` under `mcpServers`:

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

### Cursor

Add to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per-project) — the
block is identical to Claude Desktop's:

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

### Any other MCP client (Cline, Continue, custom, …)

This is a standard **stdio** MCP server. Whatever the client's config format,
give it these values:

| Field | Value |
|-------|-------|
| Transport | `stdio` |
| Command | `/absolute/path/to/zoho-mail-mcp/.venv/bin/python` |
| Args | `["/absolute/path/to/zoho-mail-mcp/server.py"]` |
| Env | `ZOHO_EMAIL`, `ZOHO_APP_PASSWORD` (+ optional host overrides) |
