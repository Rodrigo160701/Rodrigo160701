"""Genera las tarjetas "Lo que hago" y "Sobre mí" del README (solo stdlib, sin red).

Salida (mismo lenguaje visual que la tarjeta de tecnologías de make_toolchain.py):
  assets/work-dark.svg   assets/work-light.svg   assets/work-mobile-dark.svg   assets/work-mobile-light.svg
  assets/about-dark.svg  assets/about-light.svg  assets/about-mobile-dark.svg  assets/about-mobile-light.svg

Reutiliza de make_toolchain.py la paleta (THEMES), las fuentes, las rejillas (LAYOUTS), la
geometría de las capas y las piezas de dibujo (cabecera de capa, cable con pulso, baldosas y
marco), así que un cambio de estilo allí se refleja aquí al volver a generar.

Iconos:
- Marcas (n8n, OpenAI, pandas, Streamlit): Simple Icons 13.21.0 (CC0), de scripts/toolchain_icons.json,
  de relleno. Las marcas pertenecen a sus respectivos propietarios.
- Genéricos: Lucide (lucide-static 0.469.0, licencia ISC, https://lucide.dev), guardados en
  scripts/card_icons.json como {nombre: {"inner": "<elementos internos del svg>"}} (viewBox 0 0 24 24).
  Son iconos de trazo: se pintan con fill none, stroke del color de la capa, stroke-width 2 y
  extremos redondeados. Simple Icons ocupa las 24 unidades del viewBox; en Lucide el borde
  exterior del trazo llega de 1 a 23 (22 unidades), así que su caja se amplía 24/22
  (LUCIDE_SCALE) para que el borde exterior de ambos mida lo mismo en la baldosa.

Licencia de Lucide (ISC), copiada de lucide-static@0.469.0/LICENSE:

  Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT).
  All other copyright (c) for Lucide are held by Lucide Contributors 2022.

  Permission to use, copy, modify, and/or distribute this software for any purpose with or without
  fee is hereby granted, provided that the above copyright notice and this permission notice appear
  in all copies.

  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
  SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
  AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
  NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
  OF THIS SOFTWARE.

Para cambiar el contenido, edita WORK / ABOUT y vuelve a ejecutar:  python scripts/make_cards.py
Los textos largos van partidos a mano (una lista de líneas por variante, ancha y móvil) para
que quepan con margen incluso con una sans de reserva ancha (DejaVu Sans).

Ritmo y animación iguales a los de la tarjeta de tecnologías:
- Las capas de texto reservan debajo la misma banda que las etiquetas (label_gap), así las barras
  de acento quedan siempre a la misma distancia entre capas.
- En móvil el cable de una capa de texto es más corto que el de las capas con giro en U: el
  punto de datos lo recorre a la misma velocidad y con el mismo periodo (cable(travel=...)).
- Si dos etiquetas vecinas quedan a menos de MIN_LABEL_GAP (estimando 0,6 em por carácter), se
  separan lo justo sin mover las baldosas (spread_labels).
"""

import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True                 # sin __pycache__ al importar make_toolchain
sys.path.insert(0, str(HERE))                  # importable desde cualquier cwd
import make_toolchain as tc                    # noqa: E402
from make_toolchain import (FADE_STEP, LAYOUTS, PULSE_DUR, PULSE_START, PULSE_STEP,  # noqa: E402
                            THEMES, f)

OUT = HERE.parent / "assets"
LUCIDE = json.loads((HERE / "card_icons.json").read_text(encoding="utf-8"))

LUCIDE_SCALE = 24 / 22     # borde exterior del trazo de Lucide: 1..23 de las 24 unidades del viewBox
LUCIDE_STROKE = 2
MONO_EM = .6               # ancho estimado de un carácter mono (reserva ancha: DejaVu/Courier)
MIN_LABEL_GAP = 28         # px mínimos entre dos etiquetas vecinas de la misma fila

# Ajustes propios de estas tarjetas sobre la rejilla de make_toolchain.LAYOUTS.
#   body_fs/note_fs: texto de los paneles (principal y apagado), lh: interlínea, text_pad: margen
#   interior del panel, base_off: línea base respecto al centro (con 2 líneas coincide con el título
#   y el subtítulo de la capa), panel_gap: tramo de cable entre baldosa, panel y nodo final (móvil).
CARD_LAYOUT = {
    "wide": dict(body_fs=14, note_fs=13, lh=20, text_pad=16, base_off=5),
    "stack": dict(body_fs=13, note_fs=12.5, lh=19, text_pad=14, base_off=5, panel_gap=28),
}

# Iconos: "si:<slug>" = Simple Icons (relleno), "lu:<nombre>" = Lucide (trazo).
WORK = dict(
    uid="work",
    heading="Lo que hago",
    tagline="trabajo real en producción · sin código ni datos",
    title="Lo que hago: trabajo real en producción, por capas",
    rows=[
        dict(n="01", name="PROYECTOS A MEDIDA", sub="Sistemas de gran escala", hue="cyan",
             tools=[("lu:webhook", "Eventos"), ("lu:layers", "Colas"), ("lu:database", "Migración"),
                    ("lu:plug", "Integraciones"), ("lu:shield-check", "RGPD")],
             alt="Proyectos a medida, sistemas de gran escala: arquitectura de eventos, colas, "
                 "migración de datos, integraciones y RGPD"),
        dict(n="02", name="AUTOMATIZACIÓN", sub="+80 flujos en n8n", hue="pink",
             tools=[("si:n8n", "n8n"), ("lu:bot", "Agentes IA"), ("lu:message-square-reply", "Moderación"),
                    ("lu:inbox", "Clasificación"), ("lu:target", "Leads")],
             alt="Automatización, más de 80 flujos en n8n: agentes de IA, moderación, "
                 "clasificación y captación de leads"),
        dict(n="03", name="BÚSQUEDA CON IA", sub="Preguntas en lenguaje natural", hue="violet",
             tools=[("lu:message-circle-question", "Pregunta"), ("si:openai", "LLM"),
                    ("lu:database", "Fuentes"), ("lu:list-checks", "Explicación"), ("lu:lock", "Privacidad")],
             alt="Búsqueda con IA, preguntas en lenguaje natural: la pregunta pasa por un LLM, se cruzan "
                 "las fuentes de datos, se explica cada resultado y se preserva la privacidad"),
        dict(n="04", name="ANÁLISIS DE DATOS", sub="Dashboards de uso diario", hue="green",
             tools=[("si:pandas", "pandas"), ("lu:hard-drive", "Caché"), ("lu:refresh-cw", "Auto-refresco"),
                    ("lu:chart-column", "Por canal"), ("si:streamlit", "Streamlit")],
             alt="Análisis de datos, dashboards de uso diario: lógica de DAX pasada a pandas, caché, "
                 "refresco automático, análisis por canal y Streamlit"),
    ],
)

# Capas de texto: una baldosa con icono unida por el cable a un panel de texto.
# text[modo] = lista de (línea, apagada). Partidas a mano para la anchura de cada variante.
ABOUT = dict(
    uid="about",
    heading="Sobre mí",
    tagline="datos · automatización · IA",
    title="Sobre mí: datos, automatización e IA",
    # 'Automatización' y 'Calidad del dato' son vecinas y largas: en la ancha, etiquetas 1 px más
    # pequeñas para que spread_labels apenas tenga que desplazarlas (~3 px).
    layout={"wide": dict(label_fs=12)},
    rows=[
        dict(n="01", name="AHORA", sub="En el trabajo", hue="violet", icon="lu:rocket",
             text={"wide": [("Proyectos grandes a medida para una empresa europea,", False),
                            ("y automatizando todo lo que se repite.", False)],
                   "stack": [("Proyectos grandes a medida para", False),
                             ("una empresa europea, y", False),
                             ("automatizando todo lo que se repite.", False)]},
             alt="Ahora, en el trabajo: proyectos grandes a medida para una empresa europea, "
                 "y automatizando todo lo que se repite"),
        dict(n="02", name="ESTUDIOS", sub="Thomas More · Bélgica", hue="cyan", icon="lu:graduation-cap",
             text={"wide": [("Bachelor International Business Management –", False),
                            ("Data Science, Protection & Security", False),
                            ("Data Science · ML & Forecasting · DevOps · Data as a Service", True)],
                   "stack": [("Bachelor International Business", False),
                             ("Management – Data Science,", False),
                             ("Protection & Security", False),
                             ("Data Science · ML & Forecasting", True),
                             ("DevOps · Data as a Service", True)]},
             alt="Estudios en Thomas More, Bélgica: Bachelor International Business Management – Data "
                 "Science, Protection & Security; Data Science, ML y Forecasting, DevOps y Data as a Service"),
        dict(n="03", name="INTERESES", sub="Lo que me engancha", hue="pink",
             tools=[("lu:chart-column", "Análisis"), ("lu:bot", "Agentes IA"), ("lu:workflow", "Automatización"),
                    ("lu:shield-check", "Calidad del dato"), ("lu:trending-up", "Forecasting")],
             alt="Intereses: análisis de datos, agentes de IA, automatización, calidad del dato y forecasting"),
        dict(n="04", name="PRIVADO", sub="Código de empresa", hue="green", icon="lu:eye-off",
             text={"wide": [("La mayor parte de mi trabajo vive", False),
                            ("en repos privados de empresa.", False),
                            ("Aquí cuento qué hago, sin enseñar código ni datos.", True)],
                   "stack": [("La mayor parte de mi trabajo vive", False),
                             ("en repos privados de empresa.", False),
                             ("Aquí cuento qué hago, sin enseñar", True),
                             ("código ni datos.", True)]},
             alt="Privado, código de empresa: la mayor parte de mi trabajo vive en repos privados de empresa; "
                 "aquí cuento qué hago, sin enseñar código ni datos"),
    ],
)

CARDS = (WORK, ABOUT)


def glyph(ref: str, x: float, y: float, size: float, ink: str) -> str:
    """Icono monocromo en la caja nominal size x size: de relleno (Simple Icons) o de trazo (Lucide)."""
    kind, name = ref.split(":", 1)
    if kind == "si":
        return tc.brand_glyph(name, x, y, size, ink)
    big = size * LUCIDE_SCALE
    d = (big - size) / 2
    return (f'<svg x="{f(x - d)}" y="{f(y - d)}" width="{f(big)}" height="{f(big)}" viewBox="0 0 24 24">'
            f'<g fill="none" stroke="{ink}" stroke-width="{LUCIDE_STROKE}" stroke-linecap="round" '
            f'stroke-linejoin="round">{LUCIDE[name]["inner"]}</g></svg>')


def layout(spec: dict, mode: str) -> dict:
    """Rejilla de make_toolchain + ajustes de estas tarjetas. Si título y tagline no caben en una
    línea (estimando 0,62 em por carácter en negrita y 0,6 em en mono), la tagline baja bajo el título."""
    L = dict(LAYOUTS[mode])
    L.update(CARD_LAYOUT[mode])
    L.update(spec.get("layout", {}).get(mode, {}))
    title_w = len(spec["heading"]) * L["title_fs"] * .62
    tag_w = len(spec["tagline"]) * L["tag_fs"] * .6
    if title_w + 24 + tag_w > L["W"] - 2 * L["pad"]:
        head_y = L["head_y"] - 2
        tag_y = head_y + 21
        rule_y = tag_y + 16
        L.update(head_y=head_y, tag_y=tag_y, rule_y=rule_y, top0=L["top0"] + (rule_y - L["rule_y"]))
    return L


def panel_height(L: dict, n_lines: int) -> float:
    return max(L["tile"], n_lines * L["lh"] + 16)


def spread_labels(L: dict, nodes: list, labels: list) -> None:
    """Si dos etiquetas vecinas de una misma fila de baldosas quedan a menos de MIN_LABEL_GAP
    (anchos estimados a MONO_EM por carácter), las separa lo justo y a partes iguales, sin mover
    las baldosas ni salirse de la tarjeta. El centro desplazado se guarda en n["lx"]."""
    lo, hi = L["pad"], L["W"] - L["pad"]
    lines = {}
    for n, label in zip(nodes, labels):
        if label:
            lines.setdefault(n["top"], []).append((n, len(label) * L["label_fs"] * MONO_EM))
    for items in lines.values():
        items.sort(key=lambda it: it[0]["cx"])
        xs, ws = [n["cx"] for n, _ in items], [w for _, w in items]
        for _ in range(50):
            moved = False
            for k in range(len(xs) - 1):
                short = (ws[k] + ws[k + 1]) / 2 + MIN_LABEL_GAP - (xs[k + 1] - xs[k])
                if short > .01:
                    xs[k] -= short / 2
                    xs[k + 1] += short / 2
                    moved = True
            xs[0] = max(xs[0], lo + ws[0] / 2)
            xs[-1] = min(xs[-1], hi - ws[-1] / 2)
            if not moved:
                break
        for (n, _), x in zip(items, xs):
            if abs(x - n["cx"]) > .01:
                n["lx"] = x


def wide_text_geometry(L: dict, top: float, n_lines: int) -> dict:
    """[barra | 01 / NOMBRE] ●──[■]──[ panel de texto sobre las columnas 2-5 ]──○
    Debajo del panel queda libre la banda de las etiquetas (label_gap), como en las capas de
    baldosas: así las barras de acento de todas las capas quedan a la misma distancia."""
    tile, h = L["tile"], panel_height(L, n_lines)
    x0, x1, slot = tc.wide_columns(L)
    s0 = L["slots_x0"]
    cy = top + h / 2
    cx = s0 + slot * .5
    px = s0 + slot * 1.5 - tile / 2                     # alineado con las baldosas de las columnas 2 y 5
    pw = s0 + slot * 4.5 + tile / 2 - px
    return dict(nodes=[dict(cx=cx, cy=cy, top=cy - tile / 2, arrive=cx - tile / 2 - x0)],
                panel=dict(x=px, y=top, w=pw, h=h, arrive=px - x0),
                path=f"M{f(x0)},{f(cy)}H{f(x1)}", length=x1 - x0, pace=x1 - x0,
                start=(x0, cy), end=(x1 - 3, cy), cy=cy,
                bottom=top + h + L["label_gap"], content_bottom=top + h,
                head_cy=cy, bar=(top + 2, h - 4))


def stack_text_geometry(L: dict, top: float, n_lines: int) -> dict:
    """Móvil: cabecera arriba y debajo ●──[■]──[ panel de texto ]──○ (baldosa en la columna 1
    de stack_geometry). El cable es recto y más corto que el de giro en U: pace es la longitud
    de ese cable de referencia, para que el punto de datos vaya a la misma velocidad."""
    tile, h = L["tile"], panel_height(L, n_lines)
    x0, _, slot = tc.stack_columns(L)
    x1 = L["W"] - L["pad"]
    a_top = top + L["head_h"]
    cy = a_top + h / 2
    cx = x0 + slot * .5
    px = cx + tile / 2 + L["panel_gap"]
    pw = x1 - L["panel_gap"] - px
    return dict(nodes=[dict(cx=cx, cy=cy, top=cy - tile / 2, arrive=cx - tile / 2 - x0)],
                panel=dict(x=px, y=a_top, w=pw, h=h, arrive=px - x0),
                path=f"M{f(x0)},{f(cy)}H{f(x1)}", length=x1 - x0, pace=tc.stack_geometry(L, 0)["length"],
                start=(x0, cy), end=(x1 - 3, cy), cy=cy,
                bottom=a_top + h + L["label_gap"], content_bottom=a_top + h,
                head_cy=top + 11, bar=(top, a_top + h - top))


def text_row_svg(t: dict, L: dict, mode: str, row: dict, i: int, g: dict) -> str:
    hue, ink = t["hue"][row["hue"]], t["ink"][row["hue"]]
    delay = PULSE_START + i * PULSE_STEP
    lines = row["text"][mode]
    s = [f'<g class="row" style="animation-delay:{i * FADE_STEP}ms">']
    s += tc.layer_head(t, L, mode, row, g)
    s += tc.cable(t, g, hue, delay, travel=g["length"] / g["pace"])
    n, p = g["nodes"][0], g["panel"]
    s += tc.tile_svg(L, hue, ink, n, row["icon"], None, delay + n["arrive"] / g["pace"] * PULSE_DUR, glyph)
    s += tc.box(hue, p["x"], p["y"], p["w"], p["h"], g["cy"], delay + p["arrive"] / g["pace"] * PULSE_DUR)
    tx = p["x"] + L["text_pad"]
    spans = []
    for k, (line, muted) in enumerate(lines):
        y = g["cy"] + L["base_off"] + (k - (len(lines) - 1) / 2) * L["lh"]
        cls = ' class="nt"' if muted else ""
        spans.append(f'<tspan x="{f(tx)}" y="{f(y)}"{cls}>{escape(line)}</tspan>')
    s.append(f'<text class="bd">{"".join(spans)}</text>')
    s.append("</g>")
    return "\n".join(s)


def card(spec: dict, theme: str, mode: str) -> str:
    t, L = THEMES[theme], layout(spec, mode)
    body, top, bus = [], L["top0"], []
    for i, row in enumerate(spec["rows"]):
        if "tools" in row:
            g = (tc.wide_geometry if mode == "wide" else tc.stack_geometry)(L, top)
            spread_labels(L, g["nodes"], [label for _, label in row["tools"]])
            body.append(tc.row_svg(t, L, mode, row, i, g, glyph))
        else:
            g = (wide_text_geometry if mode == "wide" else stack_text_geometry)(L, top, len(row["text"][mode]))
            body.append(text_row_svg(t, L, mode, row, i, g))
        bus.append(top)
        top = g["bottom"] + L["gap"]
    # Margen inferior medido desde lo último que se ve: la línea base de las etiquetas (como en
    # make_toolchain) o, si la última capa es de texto, el borde del panel.
    H = int(round(g.get("content_bottom", g["bottom"]) + 4 + L["bottom"]))
    extra = (f".bd{{font-size:{L['body_fs']}px;fill:{t['text']}}}",
             f".nt{{font-size:{L['note_fs']}px;fill:{t['muted']}}}")
    desc = ". ".join(r["alt"] for r in spec["rows"]) + "."
    return tc.frame(t, L, uid=spec["uid"], title=spec["title"], heading=spec["heading"],
                    tagline=spec["tagline"], desc=desc, body=body, bus=bus, H=H, extra_style=extra)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for spec in CARDS:
        for theme in THEMES:
            # newline="\n": mismos bytes en Windows y en Linux/CI.
            (OUT / f"{spec['uid']}-{theme}.svg").write_text(card(spec, theme, "wide"), encoding="utf-8",
                                                           newline="\n")
            (OUT / f"{spec['uid']}-mobile-{theme}.svg").write_text(card(spec, theme, "stack"),
                                                                  encoding="utf-8", newline="\n")
    print("Tarjetas 'work' y 'about' generadas en", OUT)
