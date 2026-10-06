"""Zoho Mail MCP server.

Exposes four tools over IMAP/SMTP so Claude can read, search, send and
reply to mail on a Zoho mailbox. Auth uses a Zoho *application-specific
password* (not your login password) — no OAuth required.

Required environment variables:
  ZOHO_EMAIL         your full address, e.g. you@example.com
  ZOHO_APP_PASSWORD  an app-specific password generated in Zoho settings

Optional (defaults target the .com data center; change for EU/IN/etc.):
  ZOHO_IMAP_HOST     default imap.zoho.com
  ZOHO_SMTP_HOST     default smtp.zoho.com
  ZOHO_SMTP_PORT     default 465
"""

import email
import imaplib
import os
import smtplib
import ssl
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, formatdate, getaddresses, make_msgid, parseaddr

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("zoho-mail")


# --- config -----------------------------------------------------------------

def _cfg():
    email_addr = os.environ.get("ZOHO_EMAIL")
    password = os.environ.get("ZOHO_APP_PASSWORD")
    if not email_addr or not password:
        raise RuntimeError(
            "ZOHO_EMAIL and ZOHO_APP_PASSWORD must be set in the environment."
        )
    return {
        "email": email_addr,
        "password": password,
        "imap_host": os.environ.get("ZOHO_IMAP_HOST", "imap.zoho.com"),
        "smtp_host": os.environ.get("ZOHO_SMTP_HOST", "smtp.zoho.com"),
        "smtp_port": int(os.environ.get("ZOHO_SMTP_PORT", "465")),
    }


# --- connections ------------------------------------------------------------

# Must be passed explicitly: left to their own defaults, IMAP4_SSL and SMTP_SSL
# fall back to ssl._create_stdlib_context(), which verifies neither the
# certificate nor the hostname.
_SSL_CONTEXT = ssl.create_default_context()


def _imap(cfg):
    conn = imaplib.IMAP4_SSL(cfg["imap_host"], ssl_context=_SSL_CONTEXT)
    conn.login(cfg["email"], cfg["password"])
    return conn


def _smtp(cfg):
    conn = smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"],
                            context=_SSL_CONTEXT)
    conn.login(cfg["email"], cfg["password"])
    return conn


# --- helpers ----------------------------------------------------------------

def _dh(value):
    """Decode a possibly RFC2047-encoded header to a plain str."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _imap_quote(s):
    """Escape a string for use inside an IMAP quoted literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _body_text(msg):
    """Extract a best-effort plain-text body from an email.message.Message."""
    if msg.is_multipart():
        # Prefer text/plain that isn't an attachment.
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and \
                    "attachment" not in str(part.get("Content-Disposition", "")):
                return _decode_part(part)
        # Fall back to any text/html.
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return _decode_part(part)
        return ""
    return _decode_part(msg)


def _decode_part(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except (LookupError, TypeError):
        return payload.decode("utf-8", errors="replace")


def _fetch_message(conn, uid):
    typ, data = conn.uid("fetch", uid, "(RFC822)")
    if typ != "OK" or not data or data[0] is None:
        raise RuntimeError(f"Could not fetch message uid={uid}")
    return email.message_from_bytes(data[0][1])


def _summary(conn, uid):
    typ, data = conn.uid(
        "fetch", uid,
        "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])",
    )
    if typ != "OK" or not data or data[0] is None:
        return None
    hdr = email.message_from_bytes(data[0][1])
    return {
        "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
        "from": _dh(hdr.get("From")),
        "to": _dh(hdr.get("To")),
        "subject": _dh(hdr.get("Subject")),
        "date": _dh(hdr.get("Date")),
    }


# --- tools ------------------------------------------------------------------

@mcp.tool()
def search_emails(query: str = "", folder: str = "INBOX", limit: int = 20,
                  unseen_only: bool = False) -> list[dict]:
    """Search a mail folder and return the newest matching message summaries.

    Args:
        query: Free text matched against the whole message (headers + body).
            Leave empty to list the most recent messages in the folder.
        folder: IMAP folder name, e.g. "INBOX", "Sent", "Drafts".
        limit: Max number of messages to return (newest first).
        unseen_only: If true, only return unread messages.

    Returns:
        A list of {uid, from, to, subject, date} dicts, newest first.
    """
    cfg = _cfg()
    conn = _imap(cfg)
    try:
        conn.select(f'"{folder}"', readonly=True)
        criteria = []
        if unseen_only:
            criteria.append("UNSEEN")
        if query:
            criteria.extend(["TEXT", f'"{_imap_quote(query)}"'])
        if not criteria:
            criteria = ["ALL"]
        typ, data = conn.uid("search", None, *criteria)
        if typ != "OK":
            raise RuntimeError(f"IMAP search failed: {typ}")
        uids = data[0].split()
        uids = list(reversed(uids))[:limit]
        return [s for uid in uids if (s := _summary(conn, uid))]
    finally:
        try:
            conn.logout()
        except Exception:
            pass


@mcp.tool()
def read_email(uid: str, folder: str = "INBOX") -> dict:
    """Read the full content of one message by its UID.

    Args:
        uid: The message UID (as returned by search_emails).
        folder: IMAP folder the message lives in.

    Returns:
        {uid, from, to, cc, subject, date, body} with the plain-text body.
    """
    cfg = _cfg()
    conn = _imap(cfg)
    try:
        conn.select(f'"{folder}"', readonly=True)
        msg = _fetch_message(conn, uid.encode())
        return {
            "uid": uid,
            "from": _dh(msg.get("From")),
            "to": _dh(msg.get("To")),
            "cc": _dh(msg.get("Cc")),
            "subject": _dh(msg.get("Subject")),
            "date": _dh(msg.get("Date")),
            "body": _body_text(msg).strip(),
        }
    finally:
        try:
            conn.logout()
        except Exception:
            pass


@mcp.tool()
def send_email(to: str, subject: str, body: str,
               cc: str = "", bcc: str = "") -> str:
    """Send a new email from the Zoho mailbox.

    Args:
        to: Recipient address(es), comma-separated.
        subject: Subject line.
        body: Plain-text message body.
        cc: Optional CC address(es), comma-separated.
        bcc: Optional BCC address(es), comma-separated.

    Returns:
        A confirmation string.
    """
    cfg = _cfg()
    msg = EmailMessage()
    msg["From"] = cfg["email"]
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body)

    recipients = [a for _, a in getaddresses([to, cc, bcc]) if a]
    conn = _smtp(cfg)
    try:
        conn.send_message(msg, from_addr=cfg["email"], to_addrs=recipients)
    finally:
        try:
            conn.quit()
        except Exception:
            pass
    return f"Sent to {', '.join(recipients)} — subject: {subject!r}"


@mcp.tool()
def reply_email(uid: str, body: str, folder: str = "INBOX",
                reply_all: bool = False) -> str:
    """Reply to an existing message, preserving subject and threading.

    Args:
        uid: UID of the message to reply to.
        body: Plain-text reply body.
        folder: Folder the original message lives in.
        reply_all: If true, also CC the original To/Cc recipients (minus self).

    Returns:
        A confirmation string.
    """
    cfg = _cfg()
    conn_imap = _imap(cfg)
    try:
        conn_imap.select(f'"{folder}"', readonly=True)
        orig = _fetch_message(conn_imap, uid.encode())
    finally:
        try:
            conn_imap.logout()
        except Exception:
            pass

    orig_from = parseaddr(orig.get("From"))[1]
    orig_subject = _dh(orig.get("Subject"))
    reply_to = parseaddr(orig.get("Reply-To"))[1] or orig_from
    orig_msgid = orig.get("Message-ID")
    orig_refs = orig.get("References", "")

    subject = orig_subject
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject

    msg = EmailMessage()
    msg["From"] = cfg["email"]
    msg["To"] = reply_to
    if reply_all:
        me = cfg["email"].lower()
        cc_addrs = [
            formataddr((_dh(n), a))
            for n, a in getaddresses(
                [orig.get("To", ""), orig.get("Cc", "")]
            )
            if a and a.lower() != me and a.lower() != reply_to.lower()
        ]
        if cc_addrs:
            msg["Cc"] = ", ".join(cc_addrs)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    if orig_msgid:
        msg["In-Reply-To"] = orig_msgid
        msg["References"] = (orig_refs + " " + orig_msgid).strip()
    msg.set_content(body)

    recipients = [a for _, a in getaddresses(
        [msg.get("To", ""), msg.get("Cc", "")]) if a]
    conn = _smtp(cfg)
    try:
        conn.send_message(msg, from_addr=cfg["email"], to_addrs=recipients)
    finally:
        try:
            conn.quit()
        except Exception:
            pass
    return f"Replied to {reply_to} — subject: {subject!r}"


if __name__ == "__main__":
    mcp.run()
