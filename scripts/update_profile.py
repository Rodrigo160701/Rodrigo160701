"""Regenera las partes automáticas del perfil.

- assets/activity-{dark,light}.svg : tarjeta de actividad de los últimos 12 meses
- README.md                       : proyectos destacados (PROJECTS) y actividad reciente (RECENT)

Qué sale en el perfil (opt-in, nada más):
- tus repos públicos con el topic "perfil"
- los repos de otras cuentas u organizaciones listados en EXTRA_REPOS
La actividad reciente solo muestra esos mismos repos.

Privacidad: solo usa datos públicos. De los repos privados únicamente llega el
número de contribuciones (si "Include private contributions" está activado en el
perfil); nunca nombres, descripciones ni código.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

LOGIN = os.environ.get("PROFILE_LOGIN", "Rodrigo160701")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
ASSETS = ROOT / "assets"

MAX_PROJECTS = 6
MAX_EVENTS = 5
FEATURED_TOPIC = "perfil"  # topic que hay que poner a un repo público tuyo para destacarlo

# Repos de organizaciones o de otras personas en los que has participado: "dueño/repo": descripción
EXTRA_REPOS = {
    "thomas-more-devops/taskflow-group-3-IADI3":
        "TaskFlow · proyecto de DevOps en equipo: flujo Git con ramas, pull requests, issues "
        "y revisión de código.",
}

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

THEMES = {
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "text": "#e6edf3", "muted": "#8b949e",
        "empty": "#21262d", "a1": "#34d399", "a2": "#22d3ee",
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "text": "#1f2328", "muted": "#59636e",
        "empty": "#eaeef2", "a1": "#059669", "a2": "#0891b2",
    },
}


# ---------------------------------------------------------------- GitHub API

def _request(url: str, body: dict | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{LOGIN}-profile"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 50,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        nameWithOwner description url homepageUrl stargazerCount isArchived isPrivate pushedAt
        primaryLanguage { name color }
        repositoryTopics(first: 10) { nodes { topic { name } } }
      }
    }
  }
}
"""


REPO_FIELDS = """
  nameWithOwner description url homepageUrl stargazerCount isArchived isPrivate pushedAt
  primaryLanguage { name color }
  repositoryTopics(first: 10) { nodes { topic { name } } }
"""


def _graphql(query: str, variables: dict | None = None) -> dict:
    res = _request("https://api.github.com/graphql", {"query": query, "variables": variables or {}})
    if "errors" in res:
        sys.exit(f"GraphQL error: {res['errors']}")
    return res["data"]


def fetch_profile() -> dict:
    return _graphql(QUERY, {"login": LOGIN})["user"]


def fetch_extra_repos() -> list[dict]:
    if not EXTRA_REPOS:
        return []
    parts = []
    for i, full in enumerate(EXTRA_REPOS):
        owner, name = full.split("/", 1)
        parts.append(f'r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {REPO_FIELDS} }}')
    data = _graphql("query {" + " ".join(parts) + "}")
    repos = []
    for i, full in enumerate(EXTRA_REPOS):
        r = data.get(f"r{i}")
        if r and not r["isPrivate"]:
            repos.append({**r, "description": EXTRA_REPOS[full] or r["description"]})
    return repos


def fetch_events() -> list[dict]:
    return _request(f"https://api.github.com/users/{LOGIN}/events/public?per_page=100")



# ---------------------------------------------------------------- Métricas

def streaks(days: list[dict]) -> tuple[int, int]:
    today = datetime.now(timezone.utc).date()
    counts = [(date.fromisoformat(d["date"]), d["contributionCount"]) for d in days]
    counts = [c for c in counts if c[0] <= today]

    longest = run = 0
    for _, n in counts:
        run = run + 1 if n else 0
        longest = max(longest, run)

    current = 0
    items = list(reversed(counts))
    if items and items[0][1] == 0:  # hoy todavía sin contribuciones: la racha sigue viva
        items = items[1:]
    for _, n in items:
        if not n:
            break
        current += 1
    return current, longest


# ---------------------------------------------------------------- SVG

def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def fecha_es(d: date) -> str:
    return f"{d.day} {MESES[d.month - 1]} {d.year}"


def activity_svg(user: dict, theme: str) -> str:
    t = THEMES[theme]
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    all_days = [d for w in weeks for d in w["contributionDays"]]
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    current, longest = streaks(all_days)
    active_days = sum(1 for d in all_days if d["contributionCount"])
    private = cc["restrictedContributionsCount"]

    kpis = [
        (f"{cal['totalContributions']:,}".replace(",", "."), "contribuciones"),
        (f"{private:,}".replace(",", "."), "en repos privados") if private
        else (str(active_days), "días activos"),
        (str(current), "días de racha actual"),
        (str(longest), "días de racha máxima"),
    ]

    W, H, P = 880, 270, 28
    inner = W - 2 * P
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="Actividad en GitHub de los últimos 12 meses">',
        "<defs>",
        f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["a1"]}"/>'
        f'<stop offset="1" stop-color="{t["a2"]}"/></linearGradient>',
        f'<linearGradient id="gv" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{t["a1"]}"/>'
        f'<stop offset="1" stop-color="{t["a2"]}"/></linearGradient>',
        "</defs>",
        "<style>",
        "text{font-family:-apple-system,'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif}",
        f".t{{font-size:17px;font-weight:700;fill:{t['text']}}}",
        f".s{{font-size:12px;fill:{t['muted']}}}",
        ".v{font-size:30px;font-weight:800;fill:url(#g)}",
        f".l{{font-size:12px;fill:{t['muted']}}}",
        f".m{{font-size:10px;fill:{t['muted']}}}",
        ".b{transform-box:fill-box;transform-origin:50% 100%;animation:grow .9s cubic-bezier(.2,.8,.2,1) both}",
        ".k{animation:fade .8s ease-out both}",
        "@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}",
        "@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}",
        "@media (prefers-reduced-motion:reduce){.b,.k{animation:none}}",
        "</style>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<text class="t" x="{P}" y="42">Actividad en GitHub</text>',
        f'<text class="s" x="{W - P}" y="42" text-anchor="end">últimos 12 meses · '
        f'actualizado el {fecha_es(datetime.now(timezone.utc).date())}</text>',
    ]

    col = inner / len(kpis)
    for i, (value, label) in enumerate(kpis):
        x = P + i * col
        out.append(f'<g class="k" style="animation-delay:{i * 90}ms">'
                   f'<text class="v" x="{x:.1f}" y="96">{esc(value)}</text>'
                   f'<text class="l" x="{x:.1f}" y="116">{esc(label)}</text></g>')

    top, bottom = 140, 228
    gap = 3
    n = len(weekly)
    bw = (inner - gap * (n - 1)) / n
    peak = max(weekly) or 1
    for i, v in enumerate(weekly):
        x = P + i * (bw + gap)
        h = max(3.0, (bottom - top) * v / peak)
        fill = "url(#gv)" if v else t["empty"]
        out.append(f'<rect class="b" style="animation-delay:{i * 14}ms" x="{x:.1f}" y="{bottom - h:.1f}" '
                   f'width="{bw:.1f}" height="{h:.1f}" rx="2.5" fill="{fill}">'
                   f'<title>{v} contribuciones</title></rect>')

    last_month = None
    for i, w in enumerate(weeks):
        d = date.fromisoformat(w["contributionDays"][0]["date"])
        if d.month != last_month and i < n - 2:
            if last_month is not None:
                out.append(f'<text class="m" x="{P + i * (bw + gap):.1f}" y="248">{MESES[d.month - 1]}</text>')
            last_month = d.month
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- README

def topics(repo: dict) -> list[str]:
    return [n["topic"]["name"] for n in repo["repositoryTopics"]["nodes"]]


def featured_repos(user: dict, extra: list[dict]) -> list[dict]:
    own = [r for r in user["repositories"]["nodes"] if FEATURED_TOPIC in topics(r)]
    repos = [r for r in own + extra if not r["isArchived"]]
    return sorted(repos, key=lambda r: r["pushedAt"], reverse=True)[:MAX_PROJECTS]


def projects_md(repos: list[dict]) -> str:
    if not repos:
        return ""  # sin repos destacados la sección no aparece

    cells = []
    for r in repos:
        lang = r["primaryLanguage"]
        meta = []
        if lang:
            meta.append(f'<img src="https://img.shields.io/badge/-{esc(lang["name"]).replace("-", "--").replace(" ", "%20")}'
                        f'-{(lang["color"] or "#8b949e").lstrip("#")}?style=flat-square" alt="{esc(lang["name"])}"/>')
        if r["stargazerCount"]:
            meta.append(f"⭐ {r['stargazerCount']}")
        pushed = datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00")).date()
        meta.append(f"<sub>actualizado {fecha_es(pushed)}</sub>")
        links = f'<a href="{esc(r["url"])}"><b>{esc(r["nameWithOwner"].split("/")[1])}</b></a>'
        if r["homepageUrl"]:
            links += f' · <a href="{esc(r["homepageUrl"])}">🌐 demo</a>'
        desc = esc(r["description"] or "Sin descripción todavía.")
        cells.append(f'<td width="50%" valign="top">{links}<br/><sub>{desc}</sub><br/><br/>{" ".join(meta)}</td>')

    rows = ["## 📂 Proyectos públicos y de formación", "", "<table>"]
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        if len(pair) == 1:
            pair.append('<td width="50%"></td>')
        rows.append("<tr>" + "".join(pair) + "</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def describe_event(e: dict) -> str | None:
    repo = e["repo"]["name"]
    link = f"[{repo.split('/')[1]}](https://github.com/{repo})"
    p = e.get("payload", {})
    kind = e["type"]
    if kind == "PushEvent":
        return f"⬆️ Commits en {link}"
    if kind == "CreateEvent" and p.get("ref_type") == "repository":
        return f"✨ Nuevo repositorio {link}"
    if kind == "PullRequestEvent":
        pr = p.get("pull_request", {})
        number = p.get("number") or pr.get("number")
        action = "merged" if p.get("action") == "closed" and pr.get("merged") else p.get("action")
        verb = {"opened": "Abierta", "merged": "Fusionada"}.get(action)
        if verb and number:
            return f"🔀 {verb} la PR [#{number}](https://github.com/{repo}/pull/{number}) en {link}"
        return None
    if kind == "PullRequestReviewEvent":
        number = p.get("pull_request", {}).get("number")
        if number:
            return f"👀 Revisada la PR [#{number}](https://github.com/{repo}/pull/{number}) en {link}"
        return None
    if kind == "IssuesEvent" and p.get("action") == "opened":
        number = p.get("issue", {}).get("number")
        return f"📝 Abierta la issue [#{number}](https://github.com/{repo}/issues/{number}) en {link}"
    if kind == "ReleaseEvent":
        return f"🏷️ Publicada la versión {p.get('release', {}).get('tag_name', '')} de {link}"
    return None


def recent_md(events: list[dict], repos: list[dict]) -> str:
    allowed = {r["nameWithOwner"].lower() for r in repos}
    lines, seen = [], set()
    for e in events:
        if e["repo"]["name"].lower() not in allowed:
            continue
        text = describe_event(e)
        key = (text, e["created_at"][:10])
        if not text or key in seen:
            continue
        seen.add(key)
        lines.append(f"- {text} <sub>· {fecha_es(date.fromisoformat(e['created_at'][:10]))}</sub>")
        if len(lines) == MAX_EVENTS:
            break
    if not lines:
        return ""
    return "### ⚡ Lo último\n\n" + "\n".join(lines)


def replace_block(text: str, name: str, content: str) -> str:
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"Falta el marcador {name} en el README")
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def main() -> None:
    user = fetch_profile()
    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        (ASSETS / f"activity-{theme}.svg").write_text(activity_svg(user, theme), encoding="utf-8")

    text = README.read_text(encoding="utf-8")
    repos = featured_repos(user, fetch_extra_repos())
    text = replace_block(text, "PROJECTS", projects_md(repos))
    text = replace_block(text, "RECENT", recent_md(fetch_events(), repos))
    README.write_text(text, encoding="utf-8", newline="\n")
    print("Perfil actualizado.")


if __name__ == "__main__":
    main()
