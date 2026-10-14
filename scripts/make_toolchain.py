"""Genera la tarjeta de herramientas del README (solo stdlib, sin red).

Salida:
  assets/toolchain-dark.svg          960 px: cabecera de capa a la izquierda y 5 nodos en línea
  assets/toolchain-light.svg
  assets/toolchain-mobile-dark.svg   480 px: cabecera arriba y nodos en 3 + 2 unidos por un cable en U
  assets/toolchain-mobile-light.svg

Los iconos vienen de Simple Icons 13.21.0 (licencia CC0) y están guardados en
scripts/toolchain_icons.json como {slug: {"title", "path"}} (viewBox 0 0 24 24),
así que la generación es offline y reproducible. Power BI no existe en Simple
Icons: se dibuja un glifo propio de barras (POWERBI_GLYPH). Las marcas
pertenecen a sus respectivos propietarios.

Para cambiar el contenido, edita ROWS y vuelve a ejecutar:  python scripts/make_toolchain.py

scripts/make_cards.py importa este módulo (THEMES, LAYOUTS, columnas y geometría:
wide_columns, stack_columns, wide_geometry, stack_geometry; piezas de dibujo: layer_head, cable,
box, tile_svg, row_svg, frame) para las tarjetas "Lo que hago" y "Sobre mí"; si cambias el
estilo o la rejilla aquí, vuelve a ejecutar también make_cards.py.
"""

import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets"
ICONS = json.loads((HERE / "toolchain_icons.json").read_text(encoding="utf-8"))

# Glifo propio (24x24, monocromo): marco redondeado con un gráfico de barras dentro.
POWERBI_GLYPH = (
    "M6 2h12a4 4 0 0 1 4 4v12a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V6a4 4 0 0 1 4-4z"
    "M6 3.8A2.2 2.2 0 0 0 3.8 6v12A2.2 2.2 0 0 0 6 20.2h12a2.2 2.2 0 0 0 2.2-2.2V6A2.2 2.2 0 0 0 18 3.8z"
    "M5.9 17.2h2.4v-6h-2.4z"
    "M9.6 17.2H12V7.6H9.6z"
    "M13.3 17.2h2.4v-4.4h-2.4z"
    "M17 17.2h2.4V9.8H17z"
)

TITLE = "Del dato a la decisión"
TAGLINE = "4 capas · 20 herramientas"

ROWS = [
    dict(n="01", name="DATOS", plain="Datos", sub="Analizar y predecir", hue="violet",
         tools=[("python", "Python"), ("pandas", "pandas"), ("numpy", "NumPy"),
                ("scikitlearn", "scikit-learn"), ("jupyter", "Jupyter")]),
    dict(n="02", name="AUTOMATIZACIÓN + IA", plain="Automatización e IA", sub="Que funcione solo", hue="pink",
         tools=[("n8n", "n8n"), ("openai", "OpenAI"), ("langchain", "LangChain"),
                ("meta", "Meta API"), ("slack", "Slack")]),
    dict(n="03", name="BACKEND + APIs", plain="Backend y APIs", sub="Conectar sistemas", hue="cyan",
         tools=[("fastapi", "FastAPI"), ("flask", "Flask"), ("postgresql", "PostgreSQL"),
                ("sqlite", "SQLite"), ("docker", "Docker")]),
    dict(n="04", name="DASHBOARDS + FLUJO", plain="Dashboards y flujo", sub="Contarlo con datos", hue="green",
         tools=[("powerbi", "Power BI"), ("streamlit", "Streamlit"), ("plotly", "Plotly"),
                ("git", "Git"), ("githubactions", "GitHub Actions")]),
]

# hue: acento (barra, cable, pulso). ink: mismo tono para iconos y títulos; en claro es un
# paso más oscuro para que el texto pequeño supere 4.5:1 sobre blanco.
THEMES = {
    "dark": dict(bg="#0d1117", panel="#161b22", border="#30363d", text="#e6edf3", muted="#8b949e",
                 hue=dict(violet="#a78bfa", pink="#e879f9", cyan="#22d3ee", green="#34d399"),
                 ink=dict(violet="#a78bfa", pink="#e879f9", cyan="#22d3ee", green="#34d399"),
                 cable=".45", halo=".28"),
    "light": dict(bg="#ffffff", panel="#f6f8fa", border="#d0d7de", text="#1f2328", muted="#59636e",
                  hue=dict(violet="#7c3aed", pink="#c026d3", cyan="#0891b2", green="#059669"),
                  ink=dict(violet="#6d28d9", pink="#a21caf", cyan="#0e7490", green="#047857"),
                  cable=".55", halo=".18"),
}

MONO = "'Cascadia Code',Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,'Segoe UI',Ubuntu,sans-serif"

PULSE_DUR = 4.4      # s que tarda el punto de datos en recorrer el cable de una capa
PULSE_START = 1.2    # s antes del primer pulso (tras el fade-in)
PULSE_STEP = 1.1     # s de desfase entre capas: el dato "baja" de capa en capa
FADE_STEP = 140      # ms de desfase del fade-in entre capas

# Tamaños de letra pensados para la escala real en GitHub: la ancha se ve a ~0,64-0,88 entre
# 1012 y 1279 px de ventana y la móvil a ~0,7 en teléfonos de 360-414 px, así que ningún texto
# baja de ~8,5 px en pantalla. cable_x0/slots_x0 dejan sitio a '02 / AUTOMATIZACIÓN + IA' a
# 13,5 px incluso con una monoespaciada de reserva ancha (Menlo/Courier, ~0,6 em).
LAYOUTS = {
    # Escritorio: [barra | 01 / DATOS + subtítulo] ●──[■]──[■]──[■]──[■]──[■]──○
    "wide": dict(W=960, pad=24, head_y=42, rule_y=62, top0=84, gap=20, tile=56, icon=34, txt_x=40,
                 title_fs=18, tag_fs=13, row_fs=13.5, sub_fs=14, label_fs=13, label_gap=20,
                 cable_x0=264, slots_x0=288, bottom=22),
    # Móvil: cabecera arriba; 3 nodos, el cable gira en U y vuelve por 2 nodos intercalados.
    "stack": dict(W=480, pad=20, head_y=38, rule_y=56, top0=76, gap=24, tile=52, icon=32, txt_x=32,
                  title_fs=17, tag_fs=12.5, row_fs=14, sub_fs=14, label_fs=14, label_gap=20,
                  head_h=28, row2_gap=34, turn_r=14, bottom=20),
}


def f(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def icon_path(slug: str) -> str:
    return POWERBI_GLYPH if slug == "powerbi" else ICONS[slug]["path"]


def style(t: dict, L: dict, extra: tuple = ()) -> str:
    """Hoja de estilos común. extra: reglas adicionales (las usa make_cards.py)."""
    return "\n".join([
        "<style>",
        f"text{{font-family:{SANS}}}",
        f".mono{{font-family:{MONO}}}",
        f".tt{{font-size:{L['title_fs']}px;font-weight:700;fill:{t['text']};letter-spacing:-.2px}}",
        f".tg{{font-size:{L['tag_fs']}px;fill:{t['muted']}}}",
        f".rt{{font-size:{L['row_fs']}px;font-weight:700;letter-spacing:.8px}}",
        f".rs{{font-size:{L['sub_fs']}px;fill:{t['muted']}}}",
        f".lb{{font-size:{L['label_fs']}px;fill:{t['text']}}}",
        *extra,
        f".tile{{fill:{t['panel']};stroke:{t['border']}}}",
        f".port{{fill:{t['bg']};stroke-width:1.2}}",
        ".row{animation:rin .7s cubic-bezier(.2,.8,.2,1) both}",
        # El pulso y los destellos van enteros con SMIL (posición y opacidad en el mismo reloj),
        # así nunca se pinta un punto visible fuera del cable si los relojes CSS/SMIL se desfasan.
        ".ping{fill:none;stroke-width:1.5}",
        "@keyframes rin{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}",
        # SMIL no atiende a esta media query: con movimiento reducido se ocultan pulso y destellos.
        "@media (prefers-reduced-motion:reduce){.row{animation:none}.pulse,.ping{display:none}}",
        "</style>",
    ])


def wide_columns(L: dict) -> tuple:
    """Escritorio: inicio y fin del cable y ancho de cada una de las 5 columnas de baldosas
    (la columna j está centrada en slots_x0 + slot * (j + .5))."""
    x0, x1 = L["cable_x0"], L["W"] - L["pad"]
    return x0, x1, (x1 - L["slots_x0"]) / 5


def stack_columns(L: dict) -> tuple:
    """Móvil: inicio del cable, eje vertical de la U y ancho de cada una de las 3 columnas
    (la columna j está centrada en x0 + slot * (j + .5))."""
    x0, xu = L["txt_x"], L["W"] - L["pad"] - 4
    return x0, xu, (xu - 12 - x0) / 3


def wide_geometry(L: dict, top: float) -> dict:
    """Una línea: el cable va de izquierda a derecha por los 5 nodos."""
    x0, x1, slot = wide_columns(L)
    cy = top + L["tile"] / 2
    nodes = []
    for j in range(5):
        cx = L["slots_x0"] + slot * (j + .5)
        nodes.append(dict(cx=cx, cy=cy, top=top, arrive=cx - L["tile"] / 2 - x0))
    return dict(nodes=nodes, path=f"M{f(x0)},{f(cy)}H{f(x1)}", length=x1 - x0,
                start=(x0, cy), end=(x1 - 3, cy), bottom=top + L["tile"] + L["label_gap"],
                head_cy=cy, bar=(top + 2, L["tile"] - 4))


def stack_geometry(L: dict, top: float) -> dict:
    """3 + 2: el cable cruza 3 nodos, gira en U por la derecha y vuelve por 2 nodos intercalados."""
    tile, r = L["tile"], L["turn_r"]
    x0, xu, slot = stack_columns(L)                   # inicio del cable y eje vertical de la U
    a_top = top + L["head_h"]
    b_top = a_top + tile + L["row2_gap"]
    a_cy, b_cy = a_top + tile / 2, b_top + tile / 2
    xe = x0 + 28                                      # fin del cable en la vuelta
    a_cx = [x0 + slot * (j + .5) for j in range(3)]
    b_cx = [(a_cx[0] + a_cx[1]) / 2, (a_cx[1] + a_cx[2]) / 2]
    run1 = (xu - r) - x0
    turn = math.pi * r / 2 * 2 + (b_cy - a_cy - 2 * r)
    nodes = [dict(cx=cx, cy=a_cy, top=a_top, arrive=cx - tile / 2 - x0) for cx in a_cx]
    # En la vuelta el pulso viaja hacia la izquierda: llega antes al nodo de la derecha.
    nodes += [dict(cx=cx, cy=b_cy, top=b_top, arrive=run1 + turn + (xu - r) - (cx + tile / 2)) for cx in b_cx]
    path = (f"M{f(x0)},{f(a_cy)}H{f(xu - r)}A{r},{r} 0 0 1 {f(xu)},{f(a_cy + r)}"
            f"V{f(b_cy - r)}A{r},{r} 0 0 1 {f(xu - r)},{f(b_cy)}H{f(xe)}")
    return dict(nodes=nodes, path=path, length=run1 + turn + (xu - r) - xe,
                start=(x0, a_cy), end=(xe + 3, b_cy), bottom=b_top + tile + L["label_gap"],
                head_cy=top + 11, bar=(top, b_top + tile - top))


# --- Piezas de dibujo (las reutiliza make_cards.py para las tarjetas "work" y "about") ---

def brand_glyph(slug: str, x: float, y: float, size: float, ink: str) -> str:
    """Icono de marca de relleno (Simple Icons o el glifo de Power BI) en una caja size x size."""
    return (f'<svg x="{f(x)}" y="{f(y)}" width="{f(size)}" height="{f(size)}" viewBox="0 0 24 24">'
            f'<path fill="{ink}" fill-rule="evenodd" d="{icon_path(slug)}"/></svg>')


def layer_head(t: dict, L: dict, mode: str, row: dict, g: dict) -> list:
    """Barra de acento y cabecera de la capa: '01 / NOMBRE' en el color de la capa + subtítulo."""
    hue, ink = t["hue"][row["hue"]], t["ink"][row["hue"]]
    pad = L["pad"]
    title = f'{row["n"]} / {escape(row["name"])}'
    by, bh = g["bar"]
    s = [f'<rect x="{pad}" y="{f(by)}" width="3" height="{f(bh)}" rx="1.5" fill="{hue}"/>']
    if mode == "wide":
        cy = g["head_cy"]
        s.append(f'<text class="mono rt" x="{L["txt_x"]}" y="{f(cy - 5)}" fill="{ink}">{title}</text>')
        s.append(f'<text class="rs" x="{L["txt_x"]}" y="{f(cy + 15)}">{escape(row["sub"])}</text>')
    else:
        s.append(f'<text class="mono rt" x="{L["txt_x"]}" y="{f(g["head_cy"])}" fill="{ink}">{title}</text>')
        s.append(f'<text class="rs" x="{L["W"] - pad}" y="{f(g["head_cy"])}" text-anchor="end">'
                 f'{escape(row["sub"])}</text>')
    return s


def frac(v: float) -> str:
    """Fracción de 0 a 1 para keyTimes/keyPoints: '.481', '1', '0'."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s[1:] if s.startswith("0.") else s


def cable(t: dict, g: dict, hue: str, delay: float, travel: float = 1.0) -> list:
    """Cable con nodo de entrada (relleno) y de salida (hueco) y el punto de datos que lo recorre.
    Se dibuja antes que las baldosas: el pulso pasa por detrás de los nodos.
    travel < 1 (cable más corto que el de referencia, lo usa make_cards.py): el punto recorre el
    cable en esa fracción de PULSE_DUR y queda oculto el resto, así va a la misma velocidad que en
    las demás capas y conserva el mismo periodo (el desfase entre capas no se rompe)."""
    (sx, sy), (ex, ey) = g["start"], g["end"]
    if travel < 1:
        k = frac(travel)
        motion = f'calcMode="linear" keyPoints="0;1;1" keyTimes="0;{k};1"'
        fade = f'values="0;1;1;0;0" keyTimes="0;.04;{frac(travel - .04)};{k};1"'
    else:
        motion, fade = 'calcMode="paced"', 'values="0;1;1;0" keyTimes="0;.04;.96;1"'
    return [
        f'<path d="{g["path"]}" fill="none" stroke="{hue}" stroke-opacity="{t["cable"]}" stroke-width="1.25"/>',
        f'<circle cx="{f(sx)}" cy="{f(sy)}" r="3.5" fill="{hue}"/>',
        f'<circle class="port" cx="{f(ex)}" cy="{f(ey)}" r="3" stroke="{hue}"/>',
        # opacity="0" de base: si SMIL no corre, el punto (sin cx/cy, lo coloca animateMotion) no se ve.
        f'<g class="pulse" opacity="0">'
        f'<circle r="7" fill="{hue}" fill-opacity="{t["halo"]}"/><circle r="3" fill="{hue}"/>'
        f'<animateMotion path="{g["path"]}" dur="{PULSE_DUR}s" begin="{delay:.2f}s" '
        f'repeatCount="indefinite" {motion}/>'
        f'<animate attributeName="opacity" {fade} '
        f'dur="{PULSE_DUR}s" begin="{delay:.2f}s" repeatCount="indefinite"/></g>',
    ]


def box(hue: str, x: float, y: float, w: float, h: float, cy: float, arrive: float) -> list:
    """Baldosa (o panel) con borde, destello al paso del pulso y puertos laterales a la altura cy."""
    s = [f'<rect class="tile" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="12"/>',
         f'<rect class="ping" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="12" '
         f'stroke="{hue}" opacity="0"><animate attributeName="opacity" values="0;.9;0;0" '
         f'keyTimes="0;.03;.2;1" dur="{PULSE_DUR}s" begin="{arrive:.2f}s" '
         f'repeatCount="indefinite"/></rect>']
    for px in (x, x + w):
        s.append(f'<circle class="port" cx="{f(px)}" cy="{f(cy)}" r="2.5" stroke="{hue}"/>')
    return s


def tile_svg(L: dict, hue: str, ink: str, n: dict, slug: str, label, arrive: float,
             glyph=brand_glyph) -> list:
    """Baldosa cuadrada con icono monocromo centrado y, si hay label, etiqueta mono debajo
    (centrada en n["lx"] si existe; make_cards.py la usa para separar etiquetas largas vecinas)."""
    tile, icon = L["tile"], L["icon"]
    cx, cy, ty = n["cx"], n["cy"], n["top"]
    s = box(hue, cx - tile / 2, ty, tile, tile, cy, arrive)
    s.append(glyph(slug, cx - icon / 2, cy - icon / 2, icon, ink))
    if label:
        s.append(f'<text class="mono lb" x="{f(n.get("lx", cx))}" y="{f(ty + tile + L["label_gap"])}" '
                 f'text-anchor="middle">{escape(label)}</text>')
    return s


def row_svg(t: dict, L: dict, mode: str, row: dict, i: int, g: dict, glyph=brand_glyph) -> str:
    hue, ink = t["hue"][row["hue"]], t["ink"][row["hue"]]
    delay = PULSE_START + i * PULSE_STEP
    s = [f'<g class="row" style="animation-delay:{i * FADE_STEP}ms">']
    s += layer_head(t, L, mode, row, g)
    s += cable(t, g, hue, delay)
    for (slug, label), n in zip(row["tools"], g["nodes"]):
        arrive = delay + n["arrive"] / g["length"] * PULSE_DUR
        s += tile_svg(L, hue, ink, n, slug, label, arrive, glyph)
    s.append("</g>")
    return "\n".join(s)


def frame(t: dict, L: dict, *, uid: str, title: str, heading: str, tagline: str, desc: str,
          body: list, bus: list, H: int, extra_style: tuple = ()) -> str:
    """Marco común: fondo, cabecera (título + tagline + regla), bus punteado y capas.
    Si L trae tag_y, la tagline va bajo el título (alineada a la izquierda) en vez de a la derecha."""
    W, pad = L["W"], L["pad"]
    if L.get("tag_y"):
        tag = f'<text class="mono tg" x="{pad}" y="{L["tag_y"]}">{escape(tagline)}</text>'
    else:
        tag = f'<text class="mono tg" x="{W - pad}" y="{L["head_y"]}" text-anchor="end">{escape(tagline)}</text>'
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="{uid}-title {uid}-desc">',
        f'<title id="{uid}-title">{escape(title)}</title>',
        f'<desc id="{uid}-desc">{escape(desc)}</desc>',
        style(t, L, extra_style),
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<text class="tt" x="{pad}" y="{L["head_y"]}">{escape(heading)}</text>',
        tag,
        f'<line x1="{pad}" y1="{L["rule_y"] + .5}" x2="{W - pad}" y2="{L["rule_y"] + .5}" stroke="{t["border"]}"/>',
        # "Bus" punteado que une las cuatro capas por detrás de las barras de acento.
        f'<line x1="{pad + 1.5}" y1="{f(bus[0] + 2)}" x2="{pad + 1.5}" y2="{f(bus[-1] + 20)}" '
        f'stroke="{t["border"]}" stroke-dasharray="2 4"/>',
        *body,
        "</svg>",
    ]
    return "\n".join(out) + "\n"


def card(theme: str, mode: str) -> str:
    t, L = THEMES[theme], LAYOUTS[mode]
    geometry = wide_geometry if mode == "wide" else stack_geometry
    body, top, bus = [], L["top0"], []
    for i, row in enumerate(ROWS):
        g = geometry(L, top)
        body.append(row_svg(t, L, mode, row, i, g))
        bus.append(top)
        bottom = g["bottom"]                  # línea base de las últimas etiquetas de la capa
        top = bottom + L["gap"]
    H = int(round(bottom + 4 + L["bottom"]))

    desc = "; ".join(f'{r["plain"]} ({r["sub"].lower()}): ' + ", ".join(lbl for _, lbl in r["tools"])
                     for r in ROWS)
    return frame(t, L, uid="tc", title=f"{TITLE}: herramientas por capas", heading=TITLE, tagline=TAGLINE,
                 desc=f"{desc}.", body=body, bus=bus, H=H)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        # newline="\n": mismos bytes en Windows y en Linux/CI (LF, igual que make_dino.py).
        (OUT / f"toolchain-{theme}.svg").write_text(card(theme, "wide"), encoding="utf-8", newline="\n")
        (OUT / f"toolchain-mobile-{theme}.svg").write_text(card(theme, "stack"), encoding="utf-8",
                                                            newline="\n")
    print("Tarjetas de herramientas generadas en", OUT)
