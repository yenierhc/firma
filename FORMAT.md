# Signature email format (v1)

The page never uploads anything. It opens the phone's mail app with this text as the body:

```
SIGN v1
id: AB12cd            <- the id from the QR (or a random one if the QR had none)
size: 1000x271        <- drawing grid: the longest side is 1000
strokes: 4
points: 137
length: 396           <- number of base64url characters in data (detects truncation)
crc32: 1a2b3c4d       <- CRC-32 of the decoded bytes (detects damage)
data:
<base64url, 76 characters per line>
end
```

Subject: `Signature SIGN-<id>`. Search the mailbox for `SIGN-<id>`.

## QR link

`https://<user>.github.io/<repo>/?to=<email>&id=<id>`

* `to`: where the email goes (the user's own Outlook address). If missing, the page asks for it.
* `id`: letters, digits, `_` or `-`, up to 40. Use a fresh random id per request so the app can find *that* email.

## data bytes

All integers are unsigned LEB128 varints. Coordinates use zigzag (`0,-1,1,-2,2…` → `0,1,2,3,4…`).

```
version (=1)
grid width, grid height
number of strokes
for each stroke:
    number of points
    for each point: zigzag(x - previous x), zigzag(y - previous y)   (previous starts at 0,0 for each stroke)
```

Points are on the integer grid (origin top-left, y grows down). Strokes are already simplified (Ramer–Douglas–Peucker),
so draw them with smoothing. A stroke with one point is a dot.

`decode_signature.py` is the reference decoder (`parse()` validates length and crc and tolerates `>` quoting and
broken lines; `render_png()` makes a transparent, trimmed PNG with Pillow).
