"""Genera assets/dino-{dark,light}.svg: "Commit Runner", un dino de píxeles que corre y salta
cactus hechos con las contribuciones semanales de docs/contributions.json.

Uso:
  python scripts/make_dino.py                          # datos y salida por defecto
  python scripts/make_dino.py --data otro.json --out carpeta/
  python scripts/make_dino.py --selftest               # casos límite sintéticos, no escribe nada
  python scripts/make_dino.py --strict                 # código 1 si falla la autocomprobación

Cada semana con contribuciones es un cactus (3 alturas por cuartiles de las semanas activas);
las semanas sin actividad son suelo vacío. La pista se dibuja dos o más veces y se desplaza
exactamente su longitud, así que el bucle no tiene saltos. El dino tiene una animación de la
misma duración con un salto centrado en el instante en que pasa cada cactus. Bajo el suelo van
los meses (con el año completo en el primero, en enero y en el último) y, al final de la pista,
una marca "↻ otra vuelta" antes de volver a empezar.

Los textos tienen tres tamaños según el ancho con el que se muestra la imagen (@media dentro
del SVG): en el móvil se agrandan para seguir siendo legibles con el README a width=100%.

Autocomprobación (siempre, antes de escribir): lee los keyframes del salto del CSS generado,
calcula la altura del dino en cada instante y, durante el intervalo en que cada cactus solapa
al dino en horizontal (con margen), exige que vaya por encima del cactus (con margen). También
comprueba la separación entre saltos, que el bucle cierra, que el SVG es XML válido sin
<script> ni recursos externos, que los textos no se solapan en ningún tamaño y el contraste de
"clic para jugar". Si algo falla no escribe nada (se conservan los SVG anteriores), lo cuenta
por stderr y sale con 0 para no bloquear el resto del workflow; con --strict sale con 1.

Solo usa la biblioteca estándar (Python 3.9+).
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import random
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "contributions.json"
OUT = ROOT / "assets"

# ------------------------------------------------------------------ escena
W, H = 880, 220
GROUND = 184          # y de la línea del suelo
PX = 3                # px de pantalla por píxel del pixel art
DINO_X = 72           # x del borde izquierdo de la rejilla del dino

# ------------------------------------------------------------------ movimiento
SPEED = 300           # px/s de la pista
JUMP = 0.5            # s que dura cada salto
JUMP_H = 72           # px de altura máxima del salto
JUMP_STEPS = 10       # tramos lineales con los que se aproxima la parábola
MIN_SEP = 0.72        # s mínimos entre dos cactus (> JUMP + 0.1)
WEEK = 40             # px que ocupa una semana sin actividad
JITTER = 6            # px por paso de la pequeña variación entre cactus seguidos (0..6 pasos)
FIRST_AT = 620        # x del primer cactus al empezar, para que se vea uno nada más cargar
MARGIN_X = 4          # px de holgura horizontal en la autocomprobación
MARGIN_Y = 4          # px de holgura vertical en la autocomprobación
SKY_PARALLAX = 0.1    # fracción de la velocidad de la pista para los nodos del fondo
SPECKS = 150          # periodo del dibujo de piedrecitas del suelo

MONO = "'Cascadia Code',Consolas,'Liberation Mono',monospace"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
CHAR = 0.6            # avance de un carácter monoespaciado, en em (estimación conservadora)

# Tamaños según el ancho con el que se muestra la imagen. En un SVG servido como <img>, las
# @media se evalúan con el tamaño de la imagen, así que en el móvil (README a width=100%, unos
# 343px) se activa "vs" y los textos se agrandan en unidades del SVG para seguir siendo legibles.
#   vd: > 720px (escritorio)   vm: 481-720px (tableta)   vs: <= 480px (móvil)
BUCKETS = ("vd", "vm", "vs")
BP_M, BP_S = 720, 480
HEAD = {   # título (tamaño, letter-spacing, y), estadística (tamaño), "clic para jugar" (tamaño, y)
    "vd": dict(ttl=15, ls=2.5, y1=36, st=12, play=11.5, y2=56),
    "vm": dict(ttl=22, ls=3, y1=40, st=19, play=18, y2=68),
    "vs": dict(ttl=30, ls=3.5, y1=46, st=26, play=26, y2=84),
}
MONTH = {"vd": (10, GROUND + 24), "vm": (17, GROUND + 26), "vs": (26, GROUND + 26)}  # (tamaño, y)
LABEL_PAD = 10        # px mínimos entre etiquetas de mes (medido con el tamaño más grande)
SEAM_TXT = "otra vuelta"
SEAM_GAP = 140         # px entre la marca de fin de vuelta y la primera semana de la siguiente
SUBTITLE = "el dino salta un cactus por cada semana con contribuciones"

THEMES = {
    "dark": dict(bg="#0d1117", panel="#161b22", border="#30363d", text="#e6edf3", muted="#8b949e",
                 violet="#a78bfa", purple="#7c3aed", pink="#e879f9", cyan="#22d3ee", green="#34d399",
                 play="#22d3ee", glow=True),
    # play: cian más oscuro que #0891b2 para pasar AA (4,5:1) sobre el fondo claro
    "light": dict(bg="#ffffff", panel="#f6f8fa", border="#d0d7de", text="#1f2328", muted="#59636e",
                  violet="#7c3aed", purple="#6d28d9", pink="#c026d3", cyan="#0891b2", green="#059669",
                  play="#0e7490", glow=False),
}

# Dino propio (16x16, mira a la derecha). X cuerpo, E ojo, S púas.
DINO = [
    "........XXXXXX..",
    ".......XXXXXXXX.",
    ".......XXEXXXXX.",
    ".......XXXXXXXX.",
    ".......XXXXX....",
    ".....S.XXXXXXX..",
    "X..S..XXXXX.....",
    "X.S..XXXXXXXX...",
    "XX..XXXXXXX.X...",
    "XXXXXXXXXXX.....",
    ".XXXXXXXXXX.....",
    "..XXXXXXXX......",
    "...XXXXXXX......",
]
LEGS_A = ["....XXX.XX......", "....XX...X......", "....X....XX....."]
LEGS_B = ["....XX.XXX......", "....X...XX......", "....XX...X......"]

# Cactus de píxeles con brazos: pequeño, mediano y grande.
CACTI = {
    "s": [
        "...X...",
        "..XXX..",
        "X.XXX..",
        "X.XXX.X",
        "XXXXX.X",
        "..XXXXX",
        "..XXX..",
        "..XXX..",
    ],
    "m": [
        "....X....",
        "...XXX...",
        "X..XXX...",
        "X..XXX..X",
        "X..XXX..X",
        "XX.XXX.XX",
        ".XXXXXXX.",
        "...XXX...",
        "...XXX...",
        "...XXX...",
        "...XXX...",
    ],
    "l": [
        "....X....",
        "...XXX...",
        "...XXX..X",
        "X..XXX..X",
        "X..XXX..X",
        "X..XXX.XX",
        "XX.XXXXX.",
        ".XXXXX...",
        "...XXX...",
        "...XXX...",
        "...XXX...",
        "...XXX...",
        "...XXX...",
        "...XXX...",
    ],
}
SIZE_NAME = {"s": "pequeño", "m": "mediano", "l": "grande"}


# ------------------------------------------------------------------ utilidades
def art_path(rows: list[str], chars: str, ox: int = 0, oy: int = 0) -> str:
    """Convierte filas de pixel art en un path con un rectángulo por cada tramo horizontal."""
    d = []
    for r, line in enumerate(rows):
        c = 0
        while c < len(line):
            if line[c] in chars:
                start = c
                while c < len(line) and line[c] in chars:
                    c += 1
                w = (c - start) * PX
                d.append(f"M{ox + start * PX} {oy + r * PX}h{w}v{PX}h-{w}z")
            else:
                c += 1
    return "".join(d)


def art_cols(rows: list[str]) -> tuple[int, int]:
    cols = [c for line in rows for c, ch in enumerate(line) if ch != "."]
    return min(cols), max(cols)


def fmt(x: float, nd: int = 2) -> str:
    s = f"{x:.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def quantile(vals: list[int], q: float) -> float:
    """Cuantil con interpolación lineal (método 'inclusive'), válido con un solo valor."""
    v = sorted(vals)
    pos = (len(v) - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


DINO_ROWS = DINO + LEGS_A
D_MIN, D_MAX = art_cols(DINO + LEGS_A + LEGS_B)
DINO_H = len(DINO_ROWS) * PX
DINO_LEFT = DINO_X + D_MIN * PX                 # caja del dino en pantalla (sin salto)
DINO_RIGHT = DINO_X + (D_MAX + 1) * PX
DINO_CX = (DINO_LEFT + DINO_RIGHT) / 2


@dataclass
class Cactus:
    s: int        # posición (centro de la rejilla) dentro de la pista
    size: str
    count: int
    start: str

    @property
    def rows(self) -> list[str]:
        return CACTI[self.size]

    @property
    def w(self) -> int:
        return len(self.rows[0]) * PX

    @property
    def h(self) -> int:
        return len(self.rows) * PX

    @property
    def x0(self) -> int:              # desplazamiento del borde izquierdo respecto a s
        return -(self.w // 2)


@dataclass
class Model:
    total: int
    generated: str
    cacti: list[Cactus]
    labels: dict[str, list[tuple[int, str]]]   # por tamaño: [(posición en la pista, texto)]
    L: int                            # longitud de la pista (px)
    T: str                            # duración del bucle (s), tal cual va al CSS
    X0: int                           # x en pantalla del origen de la pista al empezar
    seam: int | None = None           # posición de la marca "otra vuelta" (fin de la pista)
    ticks: list[int] | None = None    # inicio de cada mes en la pista

    @property
    def period(self) -> float:
        return float(self.T)

    @property
    def v(self) -> float:             # velocidad real: la pista recorre L en T
        return self.L / self.period


# ------------------------------------------------------------------ datos -> pista
def load(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    weeks = []
    for w in data.get("weeks", []):
        days = [int(x) for x in w.get("days", [])]
        count = int(w.get("count", sum(days)))
        weeks.append({"start": str(w["start"]), "count": max(0, count)})
    total = data.get("total")
    total = int(total) if total is not None else sum(w["count"] for w in weeks)
    return {"weeks": weeks, "total": total, "generated": str(data.get("generated", ""))}


def build(data: dict) -> Model:
    weeks = data["weeks"]
    active = [w["count"] for w in weeks if w["count"] > 0]
    if active:
        q1, q3 = quantile(active, 0.25), quantile(active, 0.75)
        flat = min(active) == max(active)
    else:
        q1 = q3 = 0.0
        flat = True

    def size(c: int) -> str:
        if flat:
            return "m"
        if c <= q1:
            return "s"
        if c > q3:
            return "l"
        return "m"

    gap = int(math.ceil(SPEED * MIN_SEP))
    cacti: list[Cactus] = []
    months: list[tuple[int, date]] = []      # (posición, semana en que empieza el mes)
    cursor = 0
    prev_month = None
    for i, wk in enumerate(weeks):
        s = cursor
        if wk["count"] > 0:
            if cacti:
                d = date.fromisoformat(wk["start"])
                jitter = ((d.toordinal() * 37 + wk["count"] * 11) % 7) * JITTER
                s = max(s, cacti[-1].s + gap + jitter)
            cacti.append(Cactus(s, size(wk["count"]), wk["count"], wk["start"]))
        d = date.fromisoformat(wk["start"])
        if (d.year, d.month) != prev_month:
            months.append((s, d))
            prev_month = (d.year, d.month)
        cursor = s + WEEK

    # Al final de la pista queda hueco para la marca "otra vuelta", a 3,5 semanas de la siguiente
    # vuelta y al menos a 3,5 semanas de la última etiqueta de mes.
    L = cursor + 6 * WEEK
    if cacti:
        # separación también entre el último cactus y el primero de la siguiente vuelta
        L = max(L, cacti[-1].s - cacti[0].s + gap)
    L = max(L, W + 2 * WEEK)
    T = f"{L / SPEED:.4f}"
    X0 = FIRST_AT - cacti[0].s if cacti else 0
    seam = L - SEAM_GAP if weeks else None
    labels = {b: month_labels(months, MONTH[b][0]) for b in BUCKETS}
    return Model(data["total"], data["generated"], cacti, labels, L, T, X0, seam, [s for s, _ in months])


def month_labels(months: list[tuple[int, date]], fs: float) -> list[tuple[int, str]]:
    """Etiquetas de mes para un tamaño de letra. Llevan el año completo ("oct 2025", nunca
    "oct 25", que parece un día) la primera, la última y la de enero. Si el primer mes es parcial
    y su etiqueta pisaría la del siguiente, se quita la del primero (el año pasa a la siguiente)."""
    widest = text_w("mmm 0000", fs) / 2
    kept: list[tuple[int, date]] = []
    for s, d in months:
        if kept and s - kept[-1][0] < 2 * widest + LABEL_PAD:
            if len(kept) == 1:
                kept[-1] = (s, d)      # el primer mes era parcial: manda el siguiente
            continue
        kept.append((s, d))
    out = []
    for i, (s, d) in enumerate(kept):
        txt = MESES[d.month - 1]
        if i == 0 or i == len(kept) - 1 or d.month == 1:
            txt += f" {d.year}"
        out.append((s, txt))
    return out


# ------------------------------------------------------------------ animación del dino
def align_times(m: Model) -> list[float]:
    """Instante (en [0, T)) en que el centro de cada cactus pasa por el centro del dino."""
    out = []
    for c in m.cacti:
        cx = m.X0 + c.s + c.x0 + c.w / 2
        out.append(((cx - DINO_CX) / m.v) % m.period)
    return out


def lift_true(t: float, centers: list[float], T: float) -> float:
    """Altura de la parábola de salto en t (uno o ningún salto activo)."""
    best = 0.0
    for c in centers:
        for k in (-1, 0, 1):
            u = (t - (c + k * T)) / JUMP + 0.5
            if 0 < u < 1:
                best = max(best, JUMP_H * 4 * u * (1 - u))
    return best


def pct(t: float, T: float) -> str:
    return f"{t / T * 100:.4f}".rstrip("0").rstrip(".")


def jump_keyframes(m: Model) -> list[tuple[str, str]]:
    """[(porcentaje, altura px)] para @keyframes dj (interpolación lineal entre ellos)."""
    T = m.period
    centers = align_times(m)
    times = {0.0, T}
    for c in centers:
        for k in (-1, 0, 1):
            for i in range(JUMP_STEPS + 1):
                t = c + k * T + JUMP * (i / JUMP_STEPS - 0.5)
                if 0 <= t <= T:
                    times.add(t)
    frames: dict[str, str] = {}
    for t in sorted(times):
        frames[pct(t, T)] = fmt(lift_true(t, centers, T), 2)
    frames["0"] = frames["100"] = fmt(lift_true(0.0, centers, T), 2)
    return sorted(frames.items(), key=lambda kv: float(kv[0]))


def air_keyframes(m: Model, in_air: bool) -> list[tuple[str, str]]:
    """Opacidad de las patas que corren (in_air=False) o de las patas de salto (in_air=True)."""
    T = m.period
    edges = []
    for c in align_times(m):
        a, b = c - JUMP / 2, c + JUMP / 2
        for k in (-1, 0, 1):
            edges.append((a + k * T, b + k * T))

    def air(t: float) -> bool:
        return any(a <= t < b for a, b in edges)

    pts = sorted({0.0} | {x for e in edges for x in e if 0 < x < T})
    on, off = ("1", "0") if in_air else ("0", "1")
    frames = [(pct(t, T), on if air(t) else off) for t in pts]
    frames.append(("100", frames[0][1]))
    return frames


def keyframes_css(name: str, frames: list[tuple[str, str]], prop) -> str:
    return f"@keyframes {name}{{" + "".join(f"{p}%{{{prop(v)}}}" for p, v in frames) + "}"


def static_frame(m: Model) -> tuple[int, bool]:
    """Desplazamiento de la pista para el estado estático (reduced motion) y si el dino salta."""
    if not m.cacti:
        return 0, False
    best = None
    for c, t in zip(m.cacti, align_times(m)):
        tau = (m.v * t) % m.L
        seen = 0                       # altura total de los cactus a la vista: mejor si hay variedad
        for o in m.cacti:
            for k in (-1, 0, 1):
                x = m.X0 + o.s + k * m.L - tau
                if 40 <= x <= W - 40:
                    seen += o.h
        key = (seen, -t)
        if best is None or key > best[0]:
            best = (key, tau)
    return int(round(best[1])), True


# ------------------------------------------------------------------ SVG
def text_w(txt: str, size: float, ls: float = 0) -> float:
    return len(txt) * (size * CHAR + ls)


def halo(t: dict) -> str:
    """Color del degradado de fondo a la altura de "clic para jugar" (un tercio de la tarjeta)."""
    a, b = (int(t["bg"][i:i + 2], 16) for i in (1, 3, 5)), (int(t["panel"][i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(x + (y - x) / 3):02x}" for x, y in zip(a, b))


def seam_layout(bucket: str) -> tuple[float, float, float, float, bool]:
    """(tamaño de letra, radio del icono, grosor, anchura total, con texto) de la marca de vuelta.
    En el móvil solo va el icono: el texto no cabría con el tamaño grande."""
    fs, _ = MONTH[bucket]
    with_text = bucket != "vs"
    r = fs * (0.38 if with_text else 0.42)
    sw = max(1.2, fs * 0.12)
    total = 2 * r + sw + (fs * 0.5 + text_w(SEAM_TXT, fs) if with_text else 0)
    return fs, r, sw, total, with_text


def loop_icon(cx: float, cy: float, r: float, sw: float, col: str) -> str:
    """Flecha circular en sentido horario (↻) dibujada: Cascadia y Consolas no tienen el glifo."""
    a0, a1 = math.radians(-60), math.radians(250)
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    tx, ty = -math.sin(a1), math.cos(a1)          # tangente en el final del arco
    nx, ny = math.cos(a1), math.sin(a1)
    h, w = r * 0.95, r * 0.62
    tip = (x1 + tx * h * 0.75, y1 + ty * h * 0.75)
    b1 = (x1 - tx * h * 0.25 + nx * w, y1 - ty * h * 0.25 + ny * w)
    b2 = (x1 - tx * h * 0.25 - nx * w, y1 - ty * h * 0.25 - ny * w)
    pts = " ".join(f"{fmt(px)} {fmt(py)}" for px, py in (tip, b1, b2))
    return (f'<path d="M{fmt(x0)} {fmt(y0)}A{fmt(r)} {fmt(r)} 0 1 1 {fmt(x1)} {fmt(y1)}" fill="none" '
            f'stroke="{col}" stroke-width="{fmt(sw)}" stroke-linecap="round"/>'
            f'<path d="M{pts}z" fill="{col}"/>')


def seam_marker(x: int, t: dict) -> str:
    """Marca al final de la pista: línea discontinua y "↻ otra vuelta" antes de volver a empezar."""
    out = [f'<g class="seam"><path d="M{x} {GROUND - 22}V{GROUND + 8}" stroke="{t["muted"]}" '
           f'stroke-opacity=".7" stroke-width="1.5" stroke-dasharray="3 3"/>']
    for b in BUCKETS:
        fs, y = MONTH[b]
        _, r, sw, total, with_text = seam_layout(b)
        left = x - total / 2
        cx, cy = left + r + sw / 2, y - fs * 0.33
        part = loop_icon(cx, cy, r, sw, t["muted"])
        if with_text:
            part += (f'<text x="{fmt(left + 2 * r + sw + fs * 0.5, 1)}" y="{y}" font-size="{fs}" '
                     f'text-anchor="start">{SEAM_TXT}</text>')
        out.append(f'<g class="{b}">{part}</g>')
    out.append("</g>")
    return "".join(out)


def header_layout(m: Model, bucket: str) -> dict:
    """Posiciones de la cabecera en cada tamaño. Si la cifra no cabe, se acorta el texto de la
    derecha (o se quita el subtítulo en escritorio) en vez de solapar."""
    h = HEAD[bucket]
    pl = "contribución" if m.total == 1 else "contribuciones"
    title = "COMMIT RUNNER"
    title_r = 24 + text_w(title, h["ttl"], h["ls"])
    left = title_r
    sub = None
    if bucket == "vd":
        sub_x = round(title_r + 22)
        sub = (sub_x, SUBTITLE)
        left = sub_x + text_w(SUBTITLE, 11)
    stat_tail = f" {pl} · 12 meses"
    stat_w = text_w(miles(m.total) + stat_tail, h["st"])
    if W - 24 - stat_w - left < 16 and sub:
        sub, left = None, title_r
    if W - 24 - stat_w - left < 16:
        stat_tail = f" {pl}"
        stat_w = text_w(miles(m.total) + stat_tail, h["st"])
    play_w = text_w("clic para jugar", h["play"])
    return dict(h, title=title, title_r=title_r, sub=sub, stat_tail=stat_tail, stat_l=W - 24 - stat_w,
                left=left, play_x=W - 24 - play_w, play_w=play_w)


def header(m: Model, t: dict) -> str:
    out = []
    for b in BUCKETS:
        g = header_layout(m, b)
        part = [f'<g class="{b}">',
                f'<text class="ttl" x="24" y="{g["y1"]}" font-size="{g["ttl"]}" letter-spacing="{g["ls"]}">'
                f'{g["title"]}</text>']
        if g["sub"]:
            part.append(f'<text class="leg" x="{g["sub"][0]}" y="{g["y1"]}" font-size="11">{g["sub"][1]}</text>')
        part.append(f'<text class="st" x="{W - 24}" y="{g["y1"]}" font-size="{g["st"]}" text-anchor="end">'
                    f'<tspan class="n">{miles(m.total)}</tspan>{g["stat_tail"]}</text>')
        fs, y, px = g["play"], g["y2"], g["play_x"]
        s = 0.7 * fs
        # solo parpadea el triángulo: el texto se queda fijo para no perder contraste
        part.append(f'<path class="blink" d="M{fmt(px - 1.3 * fs, 1)} {fmt(y - 0.78 * fs, 1)}l{fmt(s, 1)} '
                    f'{fmt(s / 2, 1)}l-{fmt(s, 1)} {fmt(s / 2, 1)}z" fill="{t["play"]}"/>')
        part.append(f'<text class="play" x="{fmt(px, 1)}" y="{y}" font-size="{fs}" textLength="{fmt(g["play_w"], 1)}" '
                    f'lengthAdjust="spacing">clic para jugar</text>')
        part.append("</g>")
        out.append("".join(part))
    return "\n".join(out)


def sky_group(t: dict) -> str:
    rng = random.Random(160701)
    n = 16
    nodes = []
    for i in range(n):
        x = (i + rng.uniform(0.15, 0.85)) * W / n
        y = rng.uniform(70, 128)       # por encima del dino cuando corre: no ensucia la pista
        r = rng.choice([1.2, 1.5, 1.9])
        col = rng.choice(["violet", "cyan", "violet", "pink"])
        nodes.append((x, y, r, col))
    lines = []
    for i, (x, y, _, _) in enumerate(nodes):
        for j in (1, 2):
            k = i + j
            x2, y2 = nodes[k % n][0] + W * (k // n), nodes[k % n][1]
            if math.hypot(x2 - x, y2 - y) < 120:
                lines.append(f"M{fmt(x, 1)} {fmt(y, 1)}L{fmt(x2, 1)} {fmt(y2, 1)}")
    out = [f'<g id="sky"><path d="{"".join(lines)}" stroke="{t["border"]}" stroke-width="1" fill="none"/>']
    for i, (x, y, r, col) in enumerate(nodes):
        tw = f' class="tw" style="animation-delay:-{i * 0.37:.2f}s"' if i % 3 == 0 else ""
        out.append(f'<circle{tw} cx="{fmt(x, 1)}" cy="{fmt(y, 1)}" r="{r}" fill="{t[col]}" fill-opacity=".75"/>')
    out.append("</g>")
    return "".join(out)


def specks_pattern(t: dict) -> str:
    rng = random.Random(1607)
    rects = []
    for _ in range(7):
        x = rng.randrange(0, SPECKS - 6)
        y = rng.choice([3, 5, 7, 9])
        w = rng.choice([2, 3, 3, 4, 6])
        rects.append(f'<rect x="{x}" y="{y}" width="{w}" height="1.5"/>')
    return (f'<pattern id="sp" width="{SPECKS}" height="12" patternUnits="userSpaceOnUse">'
            f'<g fill="{t["muted"]}" fill-opacity=".55">{"".join(rects)}</g></pattern>')


def svg(m: Model, theme: str) -> str:
    t = THEMES[theme]
    n = len(m.cacti)
    T = m.T
    v = m.v
    pl = "contribución" if m.total == 1 else "contribuciones"
    tau, jumping = static_frame(m)

    title = "Commit Runner: un dino salta mis contribuciones de GitHub"
    if n:
        desc = (f"Animación tipo juego del dinosaurio: un dino de píxeles corre y salta {n} "
                f"cactus, uno por cada semana con contribuciones en los "
                f"últimos 12 meses ({miles(m.total)} {pl}). Cuantas más contribuciones tiene la "
                f"semana, más alto es el cactus.")
    else:
        desc = ("Animación tipo juego del dinosaurio: un dino de píxeles corre por un suelo sin "
                "cactus porque no hay semanas con contribuciones en los últimos 12 meses.")

    # ---- definiciones
    defs = [
        "<defs>",
        f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["bg"]}"/>'
        f'<stop offset="1" stop-color="{t["panel"]}"/></linearGradient>',
        f'<linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["violet"]}"/>'
        f'<stop offset="1" stop-color="{t["cyan"]}"/></linearGradient>',
        f'<linearGradient id="cg" gradientUnits="userSpaceOnUse" x1="0" y1="{GROUND}" x2="0" y2="{GROUND - 42}">'
        f'<stop offset="0" stop-color="{t["green"]}"/><stop offset="1" stop-color="{t["cyan"]}"/></linearGradient>',
        f'<linearGradient id="gl" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0"><stop offset="0" stop-color="{t["muted"]}" stop-opacity="0"/>'
        f'<stop offset=".08" stop-color="{t["muted"]}" stop-opacity=".7"/>'
        f'<stop offset=".92" stop-color="{t["muted"]}" stop-opacity=".7"/>'
        f'<stop offset="1" stop-color="{t["muted"]}" stop-opacity="0"/></linearGradient>',
        '<linearGradient id="fg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".06" stop-color="#fff"/><stop offset=".94" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
        f'<mask id="fade" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="url(#fg)"/></mask>',
        specks_pattern(t),
    ]
    if t["glow"]:
        defs.append('<filter id="glow" x="-40%" y="-40%" width="180%" height="180%">'
                    '<feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="b"/>'
                    '<feComponentTransfer in="b" result="g"><feFuncA type="linear" slope=".55"/></feComponentTransfer>'
                    '<feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    for key, rows in CACTI.items():
        w = len(rows[0]) * PX
        defs.append(f'<path id="c{key}" d="{art_path(rows, "X", -(w // 2), GROUND - len(rows) * PX)}"/>')
    defs.append(sky_group(t))

    track = [f'<g id="tk"><g fill="url(#cg)" shape-rendering="crispEdges">']
    for c in m.cacti:
        track.append(f'<use href="#c{c.size}" x="{c.s}"/>')
    track.append(f'</g><g fill="{t["muted"]}" text-anchor="middle">')
    ticks = "".join(f"M{s} {GROUND + 3}v5" for s in m.ticks or [])
    if ticks:
        track.append(f'<path class="tks" d="{ticks}" stroke="{t["border"]}" stroke-width="1.5"/>')
    for b in BUCKETS:
        if m.labels[b]:
            fs, y = MONTH[b]
            track.append(f'<g class="{b}" font-size="{fs}">'
                         + "".join(f'<text x="{s}" y="{y}">{html.escape(txt)}</text>' for s, txt in m.labels[b])
                         + "</g>")
    if m.seam is not None:
        track.append(seam_marker(m.seam, t))
    track.append("</g></g>")
    defs.append("".join(track))
    defs.append("</defs>")

    # ---- CSS
    sky_p = W / (SPEED * SKY_PARALLAX)
    css = [
        f"text{{font-family:{MONO}}}",
        ".ttl{font-weight:700;fill:url(#ac)}",
        f".leg{{fill:{t['muted']}}}",
        f".st{{fill:{t['muted']}}}",
        f".st .n{{fill:{t['text']};font-weight:700}}",
        # halo del color del fondo: en tableta y móvil el texto cae sobre las líneas de los nodos
        f".play{{fill:{t['play']};paint-order:stroke;stroke:{halo(t)};stroke-width:4px;stroke-linejoin:round}}",
        # tamaños según el ancho de la imagen (ver BUCKETS)
        ".vm,.vs{display:none}",
        f"@media (max-width:{BP_M}px){{.vd{{display:none}}.vm{{display:inline}}}}",
        # en el móvil, sin piedrecitas ni marcas de mes: tocarían las etiquetas, que son más grandes
        f"@media (max-width:{BP_S}px){{.vm{{display:none}}.vs{{display:inline}}.gnd,.tks{{display:none}}}}",
        ".blink{animation:bl 2.4s ease-in-out infinite}",
        f".trk{{animation:trk {T}s linear infinite}}",
        f".gnd{{animation:gnd {fmt(SPECKS / v, 4)}s linear infinite}}",
        f".sky{{animation:sky {fmt(sky_p, 3)}s linear infinite}}",
        ".tw{animation:tw 3.2s ease-in-out infinite}",
        ".la{animation:la .24s step-end infinite}",
        ".lb{opacity:0;animation:lb .24s step-end infinite}",
        ".jl{opacity:0}",
        "@keyframes bl{0%,100%{opacity:1}50%{opacity:.3}}",
        f"@keyframes trk{{from{{transform:translateX(0)}}to{{transform:translateX(-{m.L}px)}}}}",
        f"@keyframes gnd{{from{{transform:translateX(0)}}to{{transform:translateX(-{SPECKS}px)}}}}",
        f"@keyframes sky{{from{{transform:translateX(0)}}to{{transform:translateX(-{W}px)}}}}",
        "@keyframes tw{0%,100%{opacity:1}50%{opacity:.25}}",
        "@keyframes la{0%{opacity:1}50%{opacity:0}100%{opacity:0}}",
        "@keyframes lb{0%{opacity:0}50%{opacity:1}100%{opacity:1}}",
    ]
    if n:
        css += [
            f".dj{{animation:dj {T}s linear infinite}}",
            f".rl{{animation:rl {T}s step-end infinite}}",
            f".jl{{animation:jl {T}s step-end infinite}}",
            keyframes_css("dj", jump_keyframes(m), lambda y: f"transform:translateY(-{y}px)"),
            keyframes_css("rl", air_keyframes(m, False), lambda o: f"opacity:{o}"),
            keyframes_css("jl", air_keyframes(m, True), lambda o: f"opacity:{o}"),
        ]
    reduce = [".blink,.trk,.gnd,.sky,.tw,.la,.lb,.dj,.rl,.jl{animation:none}",
              f".trk{{transform:translateX(-{tau}px)}}"]
    if jumping:
        reduce += [f".dj{{transform:translateY(-{JUMP_H}px)}}", ".rl{opacity:0}", ".jl{opacity:1}"]
    css.append("@media (prefers-reduced-motion:reduce){" + "".join(reduce) + "}")

    # ---- dibujo
    body = [
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="url(#bg)" stroke="{t["border"]}"/>',
        # nodos lejanos con parallax lento
        f'<g mask="url(#fade)" opacity=".9"><g class="sky">'
        + "".join(f'<use href="#sky" x="{k * W}"/>' for k in (-1, 0, 1, 2)) + "</g></g>",
        # suelo
        f'<path d="M0 {GROUND + .5}H{W}" stroke="url(#gl)" stroke-width="1.5"/>',
        f'<g mask="url(#fade)"><rect class="gnd" x="0" y="{GROUND + 3}" width="{W + SPECKS}" height="12" fill="url(#sp)"/>',
    ]
    k_lo = math.floor((-60 - m.X0) / m.L) - 1
    k_hi = math.ceil((W + 60 - m.X0) / m.L) + 1
    body.append('<g class="trk">' + "".join(f'<use href="#tk" x="{m.X0 + k * m.L}"/>'
                                           for k in range(k_lo, k_hi + 1)) + "</g></g>")
    # dino
    glow = ' filter="url(#glow)"' if t["glow"] else ""
    body += [
        f'<g transform="translate({DINO_X} {GROUND - DINO_H})" shape-rendering="crispEdges"><g class="dj"><g{glow}>',
        f'<path fill="{t["violet"]}" d="{art_path(DINO, "X")}"/>',
        f'<path fill="{t["pink"]}" d="{art_path(DINO, "S")}"/>',
        f'<g fill="{t["violet"]}"><g class="rl"><path class="la" d="{art_path(LEGS_A, "X", 0, len(DINO) * PX)}"/>'
        f'<path class="lb" d="{art_path(LEGS_B, "X", 0, len(DINO) * PX)}"/></g>'
        f'<path class="jl" d="{art_path(LEGS_A, "X", 0, len(DINO) * PX)}"/></g>',
        f'</g><path fill="{t["bg"]}" d="{art_path(DINO, "E")}"/></g></g>',
    ]
    # textos: una cabecera por tamaño de pantalla, solo se ve la que toca
    body.append(header(m, t))

    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="dino-title dino-desc">',
        f'<title id="dino-title">{html.escape(title)}</title>',
        f'<desc id="dino-desc">{html.escape(desc)}</desc>',
        "\n".join(defs),
        "<style>" + "\n".join(css) + "</style>",
        "\n".join(body),
        "</svg>",
    ]) + "\n"


# ------------------------------------------------------------------ autocomprobación
def parse_keyframes(css: str, name: str) -> list[tuple[float, str]]:
    block = re.search(r"@keyframes " + name + r"\{(.*?\})\}", css)
    if not block:
        return []
    return [(float(p), body) for p, body in re.findall(r"([\d.]+)%\{([^}]*)\}", block.group(1))]


def lift_from_css(css: str) -> list[tuple[float, float]]:
    out = []
    for p, body in parse_keyframes(css, "dj"):
        mt = re.search(r"translateY\((-?[\d.]+)px\)", body)
        out.append((p, -float(mt.group(1)) if mt else 0.0))
    return out


def interp(frames: list[tuple[float, float]], t: float, T: float) -> float:
    """Valor de una animación lineal en t (s), con frames [(porcentaje, valor)]."""
    if not frames:
        return 0.0
    x = (t % T) / T * 100
    for (p0, v0), (p1, v1) in zip(frames, frames[1:]):
        if p0 <= x <= p1:
            return v0 if p1 == p0 else v0 + (v1 - v0) * (x - p0) / (p1 - p0)
    return frames[-1][1]


def check(m: Model, doc: str) -> list[str]:
    errs = []
    try:
        ET.fromstring(doc)
    except ET.ParseError as e:
        errs.append(f"XML no válido: {e}")
    low = doc.lower()
    if "<script" in low or "@import" in low or "<foreignobject" in low:
        errs.append("el SVG contiene <script>, @import o foreignObject")
    for ref in re.findall(r'(?:href|src)\s*=\s*"([^"]*)"', doc):
        if not ref.startswith("#"):
            errs.append(f"referencia externa: {ref}")
    for ref in re.findall(r"url\(([^)]*)\)", doc):
        if not ref.startswith("#"):
            errs.append(f"url externa: {ref}")
    if "prefers-reduced-motion" not in doc:
        errs.append("falta @media (prefers-reduced-motion)")

    css = re.search(r"<style>(.*?)</style>", doc, re.S).group(1)
    T = m.period
    for name in ("trk", "dj", "rl", "jl"):
        mt = re.search(r"\." + name + r"\{animation:" + name + r" ([\d.]+)s", css)
        if mt and float(mt.group(1)) != T:
            errs.append(f"la animación {name} dura {mt.group(1)}s y la pista {T}s")
    mt = re.search(r"@keyframes trk\{from\{transform:translateX\(0\)\}to\{transform:translateX\(-(\d+)px\)\}\}", css)
    if not mt or int(mt.group(1)) != m.L:
        errs.append("la pista no se desplaza exactamente su longitud")

    frames = lift_from_css(css)
    if m.cacti:
        if not frames or frames[0][0] != 0 or frames[-1][0] != 100:
            errs.append("los keyframes del salto no cubren 0%-100%")
        elif abs(frames[0][1] - frames[-1][1]) > 1e-9:
            errs.append("el salto no cierra el bucle (0% != 100%)")
        if any(b[0] < a[0] for a, b in zip(frames, frames[1:])):
            errs.append("keyframes del salto desordenados")

    v = m.v
    dl, dr = DINO_LEFT - MARGIN_X, DINO_RIGHT + MARGIN_X
    kf_times = [p / 100 * T for p, _ in frames]
    for c in m.cacti:
        a = m.X0 + c.s + c.x0              # borde izquierdo del cactus en t = 0
        b = a + c.w
        t0, t1 = (a - dr) / v, (b - dl) / v  # intervalo de solape horizontal (con margen)
        shift = math.floor(t0 / T) * T
        t0, t1 = t0 - shift, t1 - shift
        cand = [t0, t1] + [kt + k * T for kt in kf_times for k in (0, 1) if t0 < kt + k * T < t1]
        need = c.h + MARGIN_Y
        worst = min(cand, key=lambda x: interp(frames, x, T))
        lift = interp(frames, worst, T)
        if lift < need:
            errs.append(f"choque con el cactus de la semana {c.start} ({c.count}): en t={worst % T:.3f}s "
                        f"el dino va a {lift:.1f}px y hacen falta {need}px")

    # estado estático (prefers-reduced-motion): el dino tampoco puede quedar dentro de un cactus
    tau, jumping = static_frame(m)
    for c in m.cacti:
        for k in (-1, 0, 1):
            a = m.X0 + c.s + c.x0 + k * m.L - tau
            if a < dr and a + c.w > dl and (not jumping or c.h + MARGIN_Y > JUMP_H):
                errs.append(f"en el estado estático el dino queda dentro del cactus de la semana {c.start}")

    times = sorted(align_times(m))
    if len(times) >= 1:
        gaps = [b - a for a, b in zip(times, times[1:])] + [times[0] + T - times[-1]]
        if min(gaps) <= JUMP + 0.1:
            errs.append(f"dos cactus a solo {min(gaps):.3f}s (mínimo {JUMP + 0.1:.2f}s)")
    return errs + check_layout(m)


def contrast(fg: str, bg: str) -> float:
    def lum(c: str) -> float:
        ch = [int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        ch = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    a, b = sorted((lum(fg), lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def check_layout(m: Model) -> list[str]:
    """Textos: sin solapes en ninguno de los tres tamaños y "clic para jugar" con contraste AA."""
    errs = []
    for b in BUCKETS:
        fs, _ = MONTH[b]
        items = [(s, text_w(txt, fs) / 2, txt) for s, txt in m.labels[b]]
        if m.seam is not None:
            items.append((m.seam, seam_layout(b)[3] / 2, SEAM_TXT))
        items.sort()
        if items:                                   # cierre del bucle: la primera de la vuelta siguiente
            items.append((items[0][0] + m.L, items[0][1], items[0][2]))
        for (a, ha, ta), (c, hc, tc) in zip(items, items[1:]):
            if c - a < ha + hc + 4:
                errs.append(f"[{b}] etiquetas solapadas en la pista: {ta!r} ({a}) y {tc!r} ({c})")
        g = header_layout(m, b)
        if g["stat_l"] - g["left"] < 16:
            errs.append(f"[{b}] la cifra de contribuciones pisa el título")
        if g["y2"] - 0.8 * g["play"] < g["y1"] + 0.25 * g["st"] + 4:
            errs.append(f"[{b}] «clic para jugar» pisa la cifra de contribuciones")
    for name, t in THEMES.items():
        # peor caso: el fondo más claro (oscuro) o más oscuro (claro) del degradado
        for bg in (t["bg"], t["panel"]):
            if contrast(t["play"], bg) < 4.5:
                errs.append(f"[{name}] «clic para jugar» con contraste {contrast(t['play'], bg):.2f}:1 sobre {bg}")
    return errs


# ------------------------------------------------------------------ main
def synthetic(kind: str) -> dict:
    start = date(2025, 10, 12)
    rng = random.Random(kind)
    counts = {
        "cero": [0] * 53,
        "una": [0] * 30 + [7] + [0] * 22,
        "todas": [rng.randint(1, 60) for _ in range(53)],
        "extremos": [12] + [0] * 51 + [3],
        "iguales": [5 if i % 2 else 0 for i in range(53)],
        "aleatoria": [rng.choice([0, 0, rng.randint(1, 40)]) for _ in range(53)],
    }[kind]
    weeks = [{"start": date.fromordinal(start.toordinal() + 7 * i).isoformat(), "count": c}
             for i, c in enumerate(counts)]
    return {"weeks": weeks, "total": sum(counts), "generated": "2026-10-13"}


def render_all(data: dict) -> tuple[Model, dict[str, str], list[str]]:
    m = build(data)
    docs = {theme: svg(m, theme) for theme in THEMES}
    errs = [f"[{theme}] {e}" for theme, doc in docs.items() for e in check(m, doc)]
    return m, docs, errs


def summary(m: Model) -> str:
    sizes = {k: sum(1 for c in m.cacti if c.size == k) for k in CACTI}
    return (f"{len(m.cacti)} cactus (s={sizes['s']} m={sizes['m']} l={sizes['l']}), "
            f"pista {m.L}px, bucle {m.T}s")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=DATA, help="JSON de contribuciones")
    ap.add_argument("--out", type=Path, default=OUT, help="carpeta donde escribir dino-{dark,light}.svg")
    ap.add_argument("--selftest", action="store_true", help="prueba casos límite sintéticos sin escribir nada")
    ap.add_argument("--strict", action="store_true",
                    help="sale con código 1 si falla la autocomprobación (por defecto avisa, conserva los "
                         "SVG anteriores y sale con 0 para no frenar el resto del workflow)")
    args = ap.parse_args()

    if args.selftest:
        bad = 0
        for kind in ("cero", "una", "todas", "extremos", "iguales", "aleatoria"):
            m, _, errs = render_all(synthetic(kind))
            print(f"{kind:10s} {'OK ' if not errs else 'MAL'} {summary(m)}")
            for e in errs:
                print("   ", e)
            bad += bool(errs)
        sys.exit(1 if bad else 0)

    try:
        m, docs, errs = render_all(load(args.data))
    except Exception as e:                     # datos rotos: mismo trato que una comprobación fallida
        m, docs, errs = None, {}, [f"no se pudo generar: {type(e).__name__}: {e}"]
    if errs:
        print("Autocomprobación del dino FALLIDA; no se escribe nada y se conservan los SVG anteriores:",
              file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=make_dino.py::Autocomprobación del dino fallida ({len(errs)} "
                  f"problemas); se conservan dino-dark.svg y dino-light.svg anteriores")
        sys.exit(1 if args.strict else 0)
    args.out.mkdir(parents=True, exist_ok=True)
    for theme, doc in docs.items():
        (args.out / f"dino-{theme}.svg").write_text(doc, encoding="utf-8", newline="\n")
    print(f"Dino generado: {summary(m)} -> {args.out}")


if __name__ == "__main__":
    main()
