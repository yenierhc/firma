"""Reference decoder for the signature email (format: FORMAT.md).

Usage:
    python decode_signature.py email.txt out.png      # needs Pillow for the PNG
    python decode_signature.py email.txt              # only checks and prints the summary

parse(text) -> dict(id, w, h, strokes=[[(x, y), ...], ...]) or raises ValueError.
render_png(sig, path, width=1500) draws a transparent PNG (black ink) with a FIXED size: width x width/aspect
    (aspect = the box shape sent by the page, 3 by default). The signature is scaled to fit inside with a small
    margin and centered, so every signature comes out with the same dimensions.
"""
import base64
import re
import sys
import zlib

_HDR = re.compile(r"^\s*SIGN\s+v1\s*$", re.M)


def _field(text, name):
    m = re.search(r"^\s*" + name + r"\s*:\s*(.+?)\s*$", text, re.M | re.I)
    return m.group(1) if m else None


def parse(text):
    # Mail apps may add quoting (">"), soft line breaks or HTML; tolerate all of that.
    text = text.replace("\r", "")
    text = re.sub(r"^[ \t]*>+[ \t]?", "", text, flags=re.M)
    m = _HDR.search(text)
    if not m:
        raise ValueError("no 'SIGN v1' block")
    block = text[m.start():]
    sig_id = _field(block, "id") or ""
    length = int(_field(block, "length") or 0)
    crc = (_field(block, "crc32") or "").lower()
    dm = re.search(r"^\s*data\s*:\s*$(.*?)^\s*end\s*$", block, re.M | re.S | re.I)
    if not dm:
        raise ValueError("no data ... end section")
    data = re.sub(r"[^A-Za-z0-9_-]", "", dm.group(1))
    if length and len(data) != length:
        raise ValueError("data truncated: %d of %d characters" % (len(data), length))
    raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    if crc and "%08x" % (zlib.crc32(raw) & 0xFFFFFFFF) != crc:
        raise ValueError("crc32 mismatch (data damaged)")
    pos = [0]

    def varint():
        shift = n = 0
        while True:
            if pos[0] >= len(raw):
                raise ValueError("data ends early")
            b = raw[pos[0]]
            pos[0] += 1
            n |= (b & 127) << shift
            if b < 128:
                return n
            shift += 7

    def unzz(n):
        return (n >> 1) if not n & 1 else -((n + 1) >> 1)

    if varint() != 1:
        raise ValueError("unknown version")
    w, h, ns = varint(), varint(), varint()
    strokes = []
    for _ in range(ns):
        npts = varint()
        x = y = 0
        pts = []
        for _ in range(npts):
            x += unzz(varint())
            y += unzz(varint())
            pts.append((x, y))
        strokes.append(pts)
    try:
        aspect = float(_field(block, "aspect") or 0) or (w / h if h else 3.0)
    except ValueError:
        aspect = w / h if h else 3.0
    return {"id": sig_id, "w": w, "h": h, "aspect": aspect, "strokes": strokes}


def _smooth(q, rounds=3):
    """Chaikin corner cutting: rounds the corners left by the point reduction (ends stay fixed)."""
    for _ in range(rounds):
        if len(q) < 3:
            return q
        out = [q[0]]
        for (x0, y0), (x1, y1) in zip(q, q[1:]):
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        out.append(q[-1])
        q = out
    return q


def render_png(sig, path, width=1500, aspect=None, margin=0.06, ink=(0, 0, 0, 255)):
    from PIL import Image, ImageDraw  # Pillow

    pts = [p for s in sig["strokes"] for p in s]
    if not pts:
        raise ValueError("empty signature")
    aspect = float(aspect or sig.get("aspect") or 3.0)
    W, H = int(width), int(round(width / aspect))
    minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
    miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
    bw, bh = max(1, maxx - minx), max(1, maxy - miny)
    ss = 4                                   # draw 4x bigger, then shrink: smooth edges
    lw = max(2, int(round(H * 0.018))) * ss  # stroke width follows the output height (9 px at 500 px)
    m = margin * H * ss + lw
    k = min((W * ss - 2 * m) / bw, (H * ss - 2 * m) / bh)
    ox = (W * ss - bw * k) / 2 - minx * k
    oy = (H * ss - bh * k) / 2 - miny * k
    im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for s in sig["strokes"]:
        q = _smooth([(x * k + ox, y * k + oy) for x, y in s])
        # Round pen: a disc at every point plus straight pieces between them. No seams at the joints.
        r = lw / 2
        for i, (x, y) in enumerate(q):
            d.ellipse([x - r, y - r, x + r, y + r], fill=ink)
            if i:
                d.line([q[i - 1], (x, y)], fill=ink, width=lw)
    im = im.resize((W, H), Image.LANCZOS)
    im.save(path, dpi=(600, 600))
    return path


if __name__ == "__main__":
    txt = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    sig = parse(txt)
    print("id=%s grid=%dx%d aspect=%.2f strokes=%d points=%d" % (sig["id"], sig["w"], sig["h"], sig["aspect"], len(sig["strokes"]),
                                                     sum(len(s) for s in sig["strokes"])))
    if len(sys.argv) > 2:
        print("png:", render_png(sig, sys.argv[2]))
