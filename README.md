# Signature pad

A one-page tool to sign with your finger on a phone and send the signature to your own email.
Nothing is stored or uploaded: the page has no server, loads nothing from other sites and the signature leaves the
phone only through the email you send.

Open: `https://<user>.github.io/<repo>/?to=you@example.com&id=abc123`

* `index.html` — the page.
* `FORMAT.md` — what the email contains.
* `decode_signature.py` — reference decoder (Python 3; Pillow for the PNG).
* `example-email.txt` — a sample email body (`python decode_signature.py example-email.txt out.png`).
