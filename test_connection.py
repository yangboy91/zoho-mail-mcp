"""Quick smoke test: verifies IMAP + SMTP login work with your env vars.

Run:  ./.venv/bin/python test_connection.py
It logs in to both servers and lists your most recent inbox subjects.
It does NOT send anything.
"""

import os
from server import _cfg, _imap, _smtp, _summary


def main():
    cfg = _cfg()
    print(f"Account: {cfg['email']}")

    print(f"IMAP  {cfg['imap_host']} ... ", end="", flush=True)
    conn = _imap(cfg)
    conn.select("INBOX", readonly=True)
    typ, data = conn.uid("search", None, "ALL")
    uids = list(reversed(data[0].split()))[:5]
    print("ok")
    for uid in uids:
        s = _summary(conn, uid)
        if s:
            print(f"   - [{s['date']}] {s['from']} :: {s['subject']}")
    conn.logout()

    print(f"SMTP  {cfg['smtp_host']}:{cfg['smtp_port']} ... ", end="", flush=True)
    s = _smtp(cfg)
    s.quit()
    print("ok")

    print("\nAll good. You can register the server with Claude now.")


if __name__ == "__main__":
    main()
