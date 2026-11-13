"""Genera los SVG del README con la identidad de jlandaeta.dev.

Uso:
    pip install fonttools brotli pillow
    python3 scripts/gen-cards.py

Lee las fuentes de scripts/fonts y las imágenes del repo del portafolio, que se
espera al lado de este (../nuevo-portfolio) o en la variable PORTFOLIO_DIR. Escribe en assets/.
El texto se convierte a trazados, así que los SVG se ven igual en GitHub sin cargar fuentes.
Paleta y tipografías: las mismas del portafolio (app/globals.css y lib/fonts.ts).
"""
import base64
import io
import os
import re
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "scripts", "fonts")
PORTFOLIO = os.environ.get("PORTFOLIO_DIR", os.path.join(os.path.dirname(ROOT), "nuevo-portfolio"))
SRC = os.path.join(PORTFOLIO, "public")
OUT = os.path.join(ROOT, "assets")

# Paleta del portafolio
BG = "#000000"
SURFACE = "#161616"
HOVER = "#242424"
LINE = "#353535"
FRAME = "#5e594e"
INK = "#ffffff"
MUTED = "#b3b3b3"
DIM = "#7a7a7a"
ACCENT = "#fe5101"
ACCENT_HOVER = "#ff6b26"
ACCENT_DEPTH = "#8a2c00"
PAPER_INK = "#f0e6ce"


# ------------------------------------------------------------------ fuentes
class Font:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.upm = self.tt["head"].unitsPerEm
        self.cmap = self.tt.getBestCmap()
        self.gs = self.tt.getGlyphSet()
        self.hmtx = self.tt["hmtx"]
        self.ascent = self.tt["hhea"].ascent
        self._paths = {}

    def glyph(self, ch):
        name = self.cmap.get(ord(ch))
        if name is None:
            raise SystemExit(f"falta el glifo {ch!r}")
        if name not in self._paths:
            pen = SVGPathPen(self.gs)
            self.gs[name].draw(pen)
            self._paths[name] = pen.getCommands()
        return name, self._paths[name], self.hmtx[name][0]

    def width(self, s, size, tracking=0):
        w = sum(self.glyph(c)[2] for c in s)
        return w * size / self.upm + tracking * size * max(len(s) - 1, 0)


PIXELIFY = Font(os.path.join(FONTS, "PixelifySans-SemiBold.ttf"))
PRESS = Font(os.path.join(FONTS, "PressStart2P-latin.woff2"))


class Doc:
    """Junta los glifos usados y los define una sola vez en <defs>."""

    def __init__(self):
        self.defs = {}

    def text(self, s, x, y, size, fill, font=PIXELIFY, anchor="start", tracking=0, max_w=None, extra=""):
        """Texto con la línea base en y."""
        w = font.width(s, size, tracking)
        if max_w and w > max_w:
            size *= max_w / w
            w = max_w
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        k = size / font.upm
        uses, cx = [], 0.0
        prefix = "p" if font is PRESS else "g"
        for ch in s:
            if font is PRESS and ch in "ÁÉÍÓÚ":
                # El subconjunto latino de Press Start 2P dibuja las mayúsculas con tilde como minúsculas
                ch_base = "AEIOU"["ÁÉÍÓÚ".index(ch)]
                adv = font.glyph(ch_base)[2]
                uses.append(f'<rect x="{cx + adv * 0.375:g}" y="{font.upm * 1.06:g}" width="{font.upm * 0.25:g}" height="{font.upm * 0.125:g}"/>')
                ch = ch_base
            name, d, adv = font.glyph(ch)
            gid = f"{prefix}{re.sub(r'[^A-Za-z0-9]', '_', name)}"
            if d:
                self.defs[gid] = d
                uses.append(f'<use href="#{gid}" x="{cx:g}"/>')
            cx += adv + tracking * font.upm
        return (
            f'<g transform="translate({x:.2f} {y:.2f}) scale({k:.5f} {-k:.5f})" fill="{fill}"{extra}>'
            + "".join(uses)
            + "</g>"
        )

    def svg(self, w, h, title, desc, body, style=""):
        defs = "".join(f'<path id="{k}" d="{v}"/>' for k, v in sorted(self.defs.items()))
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d">\n'
            f"  <title id=\"t\">{escape(title)}</title>\n"
            f"  <desc id=\"d\">{escape(desc)}</desc>\n"
            + (f"  <style>{style}</style>\n" if style else "")
            + f"  <defs>{defs}</defs>\n{body}\n</svg>\n"
        )


def write(name, content, binary=False):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as f:
        f.write(content)
    print(f"escrito {os.path.relpath(path, ROOT)}  ({os.path.getsize(path) // 1024} KB)")


def webp_data(path, box, size, quality=80):
    """Recorta box=(x0, y0, x1, y1) en píxeles de la imagen original y la lleva a size."""
    im = Image.open(path).convert("RGB").crop(box).resize(size, Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def logo(x, y, h):
    """Logo JL del portafolio (brand/jl-codigo.svg, 800x500)."""
    s = h / 500
    return (
        f'<g transform="translate({x} {y}) scale({s:.4f})">'
        '<path fill="#ffffff" d="M152 0h306v88h-36v26h-45v146L279 483H69v-33H34v-39H4V299h115v81h93v-30h29v-29h24V114H152zM554 115h49v265h149v-13h44v119H460V326z"/>'
        f'<path fill="{ACCENT}" d="M511 0h74L372 486h-72z"/></g>'
    )


def pixel_icon(x, y, s, fill=ACCENT):
    """El marcador ▸ en píxeles que usa el portafolio delante de los subtítulos."""
    cells = [(0, 0), (0, 1), (1, 1), (0, 2), (1, 2), (2, 2), (0, 3), (1, 3), (0, 4)]
    return "".join(f'<rect x="{x + cx * s:g}" y="{y + cy * s:g}" width="{s}" height="{s}" fill="{fill}"/>' for cx, cy in cells)


# ------------------------------------------------------------------ banner
def banner():
    d = Doc()
    W, H = 1000, 500
    # La ilustración (1536x1024) se recorta a 2:1 dejando la luna y el samurái
    img = webp_data(os.path.join(SRC, "ronin-night-pixel-v2.webp"), (0, 40, 1536, 808), (W, H), 82)
    body = [
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<image href="{img}" x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="none" style="image-rendering:pixelated"/>',
        '<linearGradient id="fade" x1="0" x2="1" y1="0" y2="0">'
        '<stop offset="0" stop-color="#000" stop-opacity=".94"/><stop offset=".42" stop-color="#000" stop-opacity=".78"/>'
        '<stop offset=".7" stop-color="#000" stop-opacity="0"/></linearGradient>',
        '<linearGradient id="floor" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset=".72" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".85"/></linearGradient>',
        f'<rect width="{W}" height="{H}" fill="url(#fade)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#floor)"/>',
        logo(48, 40, 34),
        d.text("jlandaeta.dev", 112, 66, 20, INK),
        pixel_icon(48, 132, 4),
        d.text("Software Developer · Frontend, Full Stack e integración de IA", 70, 150, 19, MUTED),
        d.text("JEREMY", 46, 232, 52, INK, font=PRESS, tracking=-0.04),
        d.text("LANDAETA", 46, 312, 52, INK, font=PRESS, tracking=-0.04),
        f'<rect class="cur" x="{46 + PRESS.width("LANDAETA", 52, -0.04) + 10:.1f}" y="262" width="14" height="50" fill="{ACCENT}"/>',
        d.text("React · Next.js · TypeScript", 48, 362, 22, PAPER_INK),
        d.text("Aplicaciones web y asistentes con IA,", 48, 404, 21, INK),
        d.text("desde la interfaz hasta el backend.", 48, 432, 21, INK),
        f'<rect x="48" y="456" width="168" height="2" fill="{ACCENT}"/>',
        d.text("SANTIAGO, CHILE", W - 40, H - 30, 11, MUTED, font=PRESS, anchor="end"),
    ]
    style = ".cur{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{50%{opacity:0}}"
    desc = (
        "Jeremy Landaeta, Software Developer en Santiago, Chile. Frontend, Full Stack e integración de IA con React, "
        "Next.js y TypeScript. Ilustración pixel art: un samurái con bufanda roja mira la ciudad bajo la luna llena."
    )
    write("banner.svg", d.svg(W, H, "Jeremy Landaeta · Software Developer", desc, "\n".join(body), style))


# ------------------------------------------------------------------ resumen
def resumen():
    d = Doc()
    tiles = [
        ("ROL", "Software Developer", "Frontend · Full Stack · IA aplicada", True),
        ("ACTUALMENTE", "GreenSoft, desde 2025", "Santiago, Chile", False),
        ("EN PRODUCCIÓN", "2 asistentes con IA", "Ley REP · Transporte Autorizado", False),
    ]
    W, H, gap, pad = 1000, 150, 16, 24
    tw = (W - 2 * gap) / 3
    parts = []
    for i, (label, value, sub, hot) in enumerate(tiles):
        x0 = i * (tw + gap)
        inner = tw - 2 * pad
        parts.append(
            f'<rect x="{x0 + 1:g}" y="1" width="{tw - 2:g}" height="{H - 2}" fill="{SURFACE}" '
            f'stroke="{ACCENT if hot else LINE}" stroke-width="2"/>'
        )
        if hot:
            parts.append(f'<rect x="{x0 + 2:g}" y="{H - 6}" width="{tw - 4:g}" height="4" fill="{ACCENT}"/>')
        parts.append(d.text(label, x0 + pad, 40, 11, ACCENT if hot else MUTED, font=PRESS, max_w=inner))
        parts.append(d.text(value, x0 + pad, 84, 28, INK, max_w=inner))
        parts.append(d.text(sub, x0 + pad, 118, 18, MUTED, max_w=inner))
    desc = "Resumen. " + " ".join(f"{l.capitalize()}: {v}, {s}." for l, v, s, _ in tiles)
    write("resumen.svg", d.svg(W, H, "Resumen profesional de Jeremy Landaeta", desc, "\n".join(parts)))


# ------------------------------------------------------------------ estados
def chips():
    for name, label, color, fill in (
        ("en-produccion", "EN PRODUCCIÓN", ACCENT, "#1a0a02"),
        ("backend-validado", "BACKEND VALIDADO", PAPER_INK, SURFACE),
        ("en-pausa", "EN PAUSA", MUTED, SURFACE),
        ("completado", "COMPLETADO", INK, SURFACE),
        ("mockup", "MOCKUP", DIM, SURFACE),
    ):
        d = Doc()
        size, h, px = 9, 24, 10
        w = PRESS.width(label, size) + 2 * px
        body = (
            f'<rect x="1" y="1" width="{w - 2:.1f}" height="{h - 2}" fill="{fill}" stroke="{color}" stroke-width="2"/>'
            + d.text(label, px, 16.5, size, color, font=PRESS)
        )
        write(f"estado/{name}.svg", d.svg(int(round(w)), h, label.capitalize(), f"Estado: {label.lower()}", body))


# ------------------------------------------------------------------ stack (El taller)
AREAS = [
    ("IA e integraciones", ["DeepSeek", "Vercel AI Gateway", "WhatsApp Cloud API", "Odoo"], ["OpenAI", "Mercado Pago"]),
    ("Frontend", ["React", "Next.js", "TypeScript"], ["MUI", "RTK Query", "Tailwind", "Framer Motion", "Ant Design"]),
    ("Backend y datos", ["Laravel", "MySQL", "PostgreSQL", "Prisma"], ["Python", "FastAPI", "SQLite FTS5", "MongoDB", "Supabase", "Better Auth"]),
    ("Herramientas y procesos", ["Git", "GitHub", "Vercel", "Scrum"], ["Docker", "ApiDOG", "Vitest", "ADRs", "Power BI"]),
]
EXPLORING = ["NestJS", "n8n", "Ollama", "Modelos locales"]


def flow_chips(d, items, x0, y, max_x, size, h, px, gap, kind):
    """Coloca chips en filas; devuelve (partes, y_final)."""
    parts, x = [], x0
    for label in items:
        w = PIXELIFY.width(label, size) + 2 * px
        if x + w > max_x and x > x0:
            x, y = x0, y + h + gap
        if kind == "core":
            parts.append(
                f'<rect x="{x + 1:g}" y="{y + 1:g}" width="{w - 2:g}" height="{h - 2}" fill="{BG}" stroke="{MUTED}" stroke-width="2"/>'
                f'<rect x="{x + 2:g}" y="{y + h - 6:g}" width="{w - 4:g}" height="4" fill="{ACCENT}"/>'
            )
            parts.append(d.text(label, x + px, y + h / 2 + size * 0.3, size, INK))
        elif kind == "also":
            parts.append(
                f'<rect x="{x + 1:g}" y="{y + 1:g}" width="{w - 2:g}" height="{h - 2}" fill="{SURFACE}" stroke="{LINE}" stroke-width="2"/>'
            )
            parts.append(d.text(label, x + px, y + h / 2 + size * 0.35, size, MUTED))
        else:
            parts.append(
                f'<rect x="{x + 1:g}" y="{y + 1:g}" width="{w - 2:g}" height="{h - 2}" fill="none" stroke="{FRAME}" '
                f'stroke-width="2" stroke-dasharray="6 4"/>'
            )
            parts.append(d.text(label, x + px, y + h / 2 + size * 0.35, size, MUTED))
        x += w + gap
    return parts, y + h


def stack():
    d = Doc()
    W, gap, pad = 1000, 16, 22
    cw = (W - gap) / 2
    parts, row_bottom, y0 = [], 0, 0
    for i, (name, core, also) in enumerate(AREAS):
        col, row = i % 2, i // 2
        x0 = col * (cw + gap)
        if col == 0:
            y0 = row_bottom + (gap if row else 0)
        inner = []
        inner.append(pixel_icon(x0 + pad, y0 + 26, 3))
        inner.append(d.text(name, x0 + pad + 16, y0 + 40, 24, INK))
        p, y = flow_chips(d, core, x0 + pad, y0 + 62, x0 + cw - pad, 19, 40, 14, 10, "core")
        inner += p
        p, y = flow_chips(d, also, x0 + pad, y + 12, x0 + cw - pad, 15, 30, 10, 8, "also")
        inner += p
        bottom = y + pad
        if col == 0:
            left_bottom, left_inner, left_x = bottom, inner, x0
        else:
            h = max(bottom, left_bottom) - y0
            for bx, content in ((left_x, left_inner), (x0, inner)):
                parts.append(f'<rect x="{bx + 1:g}" y="{y0 + 1:g}" width="{cw - 2:g}" height="{h - 2:g}" fill="{SURFACE}" stroke="{LINE}" stroke-width="2"/>')
                parts += content
            row_bottom = y0 + h
    y = row_bottom + 34
    parts.append(d.text("EN EXPLORACIÓN", 2, y, 10, MUTED, font=PRESS))
    p, y = flow_chips(d, EXPLORING, 200, y - 21, W, 15, 30, 10, 8, "explore")
    parts += p
    H = int(y + 4)
    desc = "El taller. " + " ".join(f"{n}: {', '.join(c)}; también {', '.join(a)}." for n, c, a in AREAS) + " En exploración: " + ", ".join(EXPLORING) + "."
    write("stack.svg", d.svg(W, H, "El taller: stack tecnológico", desc, "\n".join(parts)))


# ------------------------------------------------------------------ footer
def footer():
    d = Doc()
    W, H = 1000, 260
    img = webp_data(os.path.join(SRC, "moon-scene-selected.webp"), (0, 250, 1560, 656), (W, H), 80)
    body = [
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<image href="{img}" width="{W}" height="{H}" preserveAspectRatio="none" style="image-rendering:pixelated"/>',
        '<linearGradient id="v" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".9"/>'
        '<stop offset=".35" stop-color="#000" stop-opacity="0"/><stop offset=".8" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".9"/></linearGradient>',
        f'<rect width="{W}" height="{H}" fill="url(#v)"/>',
        d.text("¿Trabajamos juntos?", W / 2, 46, 26, INK, anchor="middle"),
        d.text("FORJADO EN SANTIAGO, CHILE", W / 2, H - 18, 10, MUTED, font=PRESS, anchor="middle"),
    ]
    desc = "¿Trabajamos juntos? Forjado en Santiago, Chile. Ilustración: un samurái junto a un farol mira la luna llena."
    write("footer.svg", d.svg(W, H, "¿Trabajamos juntos?", desc, "\n".join(body)))


# ------------------------------------------------------------------ capturas de proyectos
SHOTS = {
    "transporte.jpg": "transporte-chat.jpg",
    "restal.jpg": "restal-resumen-actual.png",
    "baoblue.jpg": "baoblue-hero.jpg",
}


def shots():
    for out, src in SHOTS.items():
        path = os.path.join(SRC, "projects", src)
        if not os.path.exists(path):
            print(f"omitido {out}: falta {path}")
            continue
        im = Image.open(path).convert("RGB")
        w, h = 960, 600  # 16:10, igual que las tarjetas del portafolio
        r = max(w / im.width, h / im.height)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        im = im.crop((0, 0, w, h))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
        write(f"proyectos/{out}", buf.getvalue(), binary=True)


# ------------------------------------------------------------------ recolor de la tarjeta animada de Ley REP
LEY_REP_MAP = {
    "#071120": "#0a0a0a", "#010813": "#000000", "#1b2a44": LINE, "#f3e7cf": INK,
    "#ff7a1a": ACCENT, "#ffb454": ACCENT_HOVER, "#c9a15a": MUTED, "#a89f8c": MUTED,
    "#5d6677": DIM, "#4fd8ff": ACCENT, "#2a1608": "#2a1206",
}


def ley_rep():
    path = os.path.join(OUT, "proyectos", "ley-rep.svg")
    src = open(path, encoding="utf-8").read()
    out = re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: LEY_REP_MAP.get(m.group(0).lower(), m.group(0)), src)
    if out != src:
        write("proyectos/ley-rep.svg", out)


if __name__ == "__main__":
    banner()
    resumen()
    chips()
    stack()
    footer()
    shots()
    ley_rep()
