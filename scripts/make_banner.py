"""Genera assets/banner-{dark,light}.svg. Edita NAME / ROLE / PHRASES y vuelve a ejecutarlo."""

from pathlib import Path

NAME = "Rodrigo Alonso Moreno"
ROLE = "Data Analyst · Automatizaciones · Desarrollo con IA"
PROMPT = "~/rodrigo $ whoami"
PHRASES = [
    "Análisis de datos con Python, pandas y machine learning",
    "Automatizaciones e integraciones entre sistemas",
    "Desarrollo con IA: búsquedas en lenguaje natural",
    "CRMs a medida con leads en tiempo real",
]

THEMES = {
    "dark": dict(bg1="#0d1117", bg2="#0a1f1c", text="#e6edf3", muted="#8b949e", grid="#1f2a2e",
                 a1="#34d399", a2="#22d3ee", node="#0f1b1f", glow=".35"),
    "light": dict(bg1="#ffffff", bg2="#ecfdf5", text="#1f2328", muted="#59636e", grid="#d8eee6",
                  a1="#059669", a2="#0891b2", node="#ffffff", glow=".18"),
}

NODES = {
    "meta": (800, 78, "Meta"), "google": (800, 150, "Google"), "web": (800, 222, "Web"),
    "queue": (925, 150, "Webhooks"), "crm": (1040, 100, "CRM"), "bq": (1040, 200, "ERP"),
    "kpi": (1135, 150, "KPIs"),
}
EDGES = [("meta", "queue"), ("google", "queue"), ("web", "queue"), ("queue", "crm"),
         ("crm", "bq"), ("crm", "kpi"), ("bq", "kpi")]


def banner(t: dict) -> str:
    W, H = 1200, 300
    n = len(PHRASES)
    cycle = 3 * n
    slot = 100 / n
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="{NAME} — Data Analyst, automatizaciones y desarrollo con IA">',
        "<defs>",
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg1"]}"/>'
        f'<stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>',
        f'<linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["a1"]}"/>'
        f'<stop offset="1" stop-color="{t["a2"]}"/></linearGradient>',
        f'<radialGradient id="glow"><stop offset="0" stop-color="{t["a1"]}" stop-opacity="{t["glow"]}"/>'
        f'<stop offset="1" stop-color="{t["a1"]}" stop-opacity="0"/></radialGradient>',
        f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<circle cx="1.5" cy="1.5" r="1.2" fill="{t["grid"]}"/></pattern>',
        f'<clipPath id="r"><rect width="{W}" height="{H}" rx="18"/></clipPath>',
        "</defs>",
        "<style>",
        "text{font-family:-apple-system,'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif}",
        ".mono{font-family:ui-monospace,'SFMono-Regular','Cascadia Code',Consolas,monospace}",
        f".name{{font-size:52px;font-weight:800;fill:{t['text']};letter-spacing:-1px}}",
        ".role{font-size:26px;font-weight:700;fill:url(#ac)}",
        f".prompt{{font-size:16px;fill:{t['a1']}}}",
        f".ph{{font-size:19px;fill:{t['muted']};opacity:0;animation:rot {cycle}s infinite}}",
        f".cur{{fill:{t['a1']};animation:blink 1s steps(1) infinite}}",
        f".edge{{stroke:url(#ac);stroke-width:2;fill:none;stroke-dasharray:5 9;opacity:.75;"
        f"animation:flow 1.4s linear infinite}}",
        f".node{{fill:{t['node']};stroke:url(#ac);stroke-width:2}}",
        f".nl{{font-size:12px;font-weight:600;fill:{t['text']}}}",
        ".drift{animation:drift 14s ease-in-out infinite alternate}",
        ".in{animation:in .9s cubic-bezier(.2,.8,.2,1) both}",
        f"@keyframes rot{{0%{{opacity:0;transform:translateY(8px)}}{slot * .12:.1f}%{{opacity:1;transform:none}}"
        f"{slot * .88:.1f}%{{opacity:1;transform:none}}{slot:.1f}%{{opacity:0;transform:translateY(-8px)}}"
        f"100%{{opacity:0}}}}",
        "@keyframes blink{50%{opacity:0}}",
        "@keyframes flow{to{stroke-dashoffset:-28}}",
        "@keyframes drift{to{transform:translate(-60px,30px)}}",
        "@keyframes in{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}",
        "@media (prefers-reduced-motion:reduce){.ph,.edge,.drift,.in,.cur{animation:none}.ph:first-of-type{opacity:1}}",
        "</style>",
        '<g clip-path="url(#r)">',
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#dots)"/>',
        '<circle class="drift" cx="980" cy="120" r="260" fill="url(#glow)"/>',
        '<circle class="drift" cx="180" cy="320" r="200" fill="url(#glow)" style="animation-duration:18s"/>',
        "</g>",
        f'<g class="in"><text class="mono prompt" x="70" y="86">{PROMPT}</text>',
        f'<text class="name" x="68" y="146">{NAME}</text>',
        f'<text class="role" x="70" y="186">{ROLE}</text></g>',
    ]
    for i, p in enumerate(PHRASES):
        s.append(f'<text class="ph" x="70" y="236" style="animation-delay:{i * 3}s">'
                 f'<tspan class="mono" fill="{t["a1"]}">▸ </tspan>{p}</text>')

    for a, b in EDGES:
        (x1, y1, _), (x2, y2, _) = NODES[a], NODES[b]
        mx = (x1 + x2) / 2
        d = f"M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"
        s.append(f'<path id="e-{a}-{b}" class="edge" d="{d}"/>')
    for i, (a, b) in enumerate([("meta", "queue"), ("queue", "crm"), ("crm", "kpi"), ("web", "queue"), ("bq", "kpi")]):
        s.append(f'<circle r="3.5" fill="{t["a2"]}"><animateMotion dur="2.4s" begin="{i * .5}s" '
                 f'repeatCount="indefinite"><mpath href="#e-{a}-{b}"/></animateMotion></circle>')
    for key, (x, y, label) in NODES.items():
        w = 14 + 7.2 * len(label)
        s.append(f'<rect class="node" x="{x - w / 2:.1f}" y="{y - 15}" width="{w:.1f}" height="30" rx="15"/>')
        s.append(f'<text class="nl" x="{x}" y="{y + 4}" text-anchor="middle">{label}</text>')

    s.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17" fill="none" stroke="url(#ac)" '
             f'stroke-opacity=".45"/>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (out / f"banner-{name}.svg").write_text(banner(theme), encoding="utf-8")
    print("Banners generados.")
