"""Rapport hebdomadaire : visiteurs et clics (GoatCounter) + référencement (Search Console).
Publié sous forme de ticket GitHub (GitHub prévient par e-mail).
Secrets : GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN (scopes business.manage + webmasters.readonly),
GOATCOUNTER_TOKEN (droit « lire les statistiques »). GITHUB_TOKEN et GITHUB_REPOSITORY fournis par GitHub."""
import datetime as dt, json, os, urllib.parse, urllib.request

def env(k):
    v = os.environ.get(k, "")
    return v.strip().strip('"').strip("'").strip()

def req(url, data=None, headers=None, method=None):
    h = {"Accept": "application/json"}; h.update(headers or {})
    body = None
    if data is not None:
        if isinstance(data, dict) and h.get("Content-Type") == "application/json":
            body = json.dumps(data).encode()
        else:
            body = urllib.parse.urlencode(data).encode()
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    return json.load(urllib.request.urlopen(r, timeout=40))

today = dt.date.today()
fin = today - dt.timedelta(days=1)          # semaine écoulée : 7 jours jusqu'à hier
deb = fin - dt.timedelta(days=6)
p_fin = deb - dt.timedelta(days=1); p_deb = p_fin - dt.timedelta(days=6)
fr = lambda d: d.strftime("%d/%m")
lines = [f"## Semaine du {fr(deb)} au {fr(fin)}", ""]

def evol(a, b):
    if b in (None, 0) or a is None: return ""
    d = (a - b) / b * 100
    return f" ({'+' if d >= 0 else ''}{d:.0f} %)"

# ---------- GoatCounter ----------
gc = env("GOATCOUNTER_TOKEN")
lines += ["### Visites du site", ""]
if gc:
    base = "https://cabinetdentairedubourg.goatcounter.com/api/v0"
    H = {"Authorization": f"Bearer {gc}", "Content-Type": "application/json"}
    def total(a, b):
        r = req(f"{base}/stats/total?start={a}&end={b}", headers=H)
        return r.get("total") or r.get("total_unique") or 0
    def events(a, b):
        out = {}
        r = req(f"{base}/stats/hits?start={a}&end={b}&limit=100", headers=H)
        for h in r.get("hits", []):
            if h.get("event"):
                out[h.get("path")] = h.get("count", h.get("count_unique", 0))
        return out
    try:
        v, pv = total(deb, fin), total(p_deb, p_fin)
        e, pe = events(deb, fin), events(p_deb, p_fin)
        d, pd = e.get("Clic Doctolib", 0), pe.get("Clic Doctolib", 0)
        t, pt = e.get("Clic téléphone", 0), pe.get("Clic téléphone", 0)
        lines += ["| | Cette semaine | Semaine précédente |", "|---|---:|---:|",
                  f"| Visiteurs | **{v}**{evol(v, pv)} | {pv} |",
                  f"| Clics vers Doctolib | **{d}**{evol(d, pd)} | {pd} |",
                  f"| Clics sur le téléphone | **{t}**{evol(t, pt)} | {pt} |", ""]
    except Exception as ex:
        lines += [f"_Statistiques de visite indisponibles ({ex})._", ""]
else:
    lines += ["_Secret GOATCOUNTER_TOKEN manquant._", ""]

# ---------- Search Console ----------
lines += ["### Google (Search Console)", ""]
try:
    tok = req("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
              "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
    site = urllib.parse.quote("sc-domain:cabinetdentairedubourg.fr", safe="")
    url = f"https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
    H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    # Les données Google ont environ 3 jours de retard : on décale la fenêtre.
    g_fin = today - dt.timedelta(days=3); g_deb = g_fin - dt.timedelta(days=6)
    gp_fin = g_deb - dt.timedelta(days=1); gp_deb = gp_fin - dt.timedelta(days=6)
    def tot(a, b):
        rows = req(url, {"startDate": str(a), "endDate": str(b)}, H, "POST").get("rows", [])
        return rows[0] if rows else {"clicks": 0, "impressions": 0, "position": None}
    cur, prev = tot(g_deb, g_fin), tot(gp_deb, gp_fin)
    pos = f"{cur['position']:.1f}" if cur.get("position") else "–"
    ppos = f"{prev['position']:.1f}" if prev.get("position") else "–"
    lines += [f"_Du {fr(g_deb)} au {fr(g_fin)} (Google publie ses chiffres avec environ 3 jours de retard)._", "",
              "| | Cette semaine | Semaine précédente |", "|---|---:|---:|",
              f"| Affichages dans Google | **{int(cur['impressions'])}**{evol(cur['impressions'], prev['impressions'])} | {int(prev['impressions'])} |",
              f"| Clics depuis Google | **{int(cur['clicks'])}**{evol(cur['clicks'], prev['clicks'])} | {int(prev['clicks'])} |",
              f"| Position moyenne | **{pos}** | {ppos} |", ""]
    q = req(url, {"startDate": str(g_deb), "endDate": str(g_fin), "dimensions": ["query"], "rowLimit": 5}, H, "POST").get("rows", [])
    if q:
        lines += ["**Top 5 des recherches**", "", "| Recherche | Affichages | Clics | Position |", "|---|---:|---:|---:|"]
        lines += [f"| {r['keys'][0]} | {int(r['impressions'])} | {int(r['clicks'])} | {r['position']:.1f} |" for r in q]
        lines.append("")
    else:
        lines += ["_Pas encore assez de recherches enregistrées par Google._", ""]
except urllib.error.HTTPError as ex:
    msg = ex.read().decode("utf-8", "replace")[:300]
    hint = " Le jeton Google n’a pas l’autorisation Search Console : refaire l’étape du Playground avec les deux autorisations." if ("insufficient" in msg.lower() or ex.code == 403) else ""
    lines += [f"_Données Google indisponibles ({ex.code}).{hint}_", ""]
except Exception as ex:
    lines += [f"_Données Google indisponibles ({ex})._", ""]

lines += ["---", "Détails : [GoatCounter](https://cabinetdentairedubourg.goatcounter.com) · [Search Console](https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain:cabinetdentairedubourg.fr)"]
body = "\n".join(lines)
print(body)

repo, gh = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
if repo and gh:
    req(f"https://api.github.com/repos/{repo}/issues",
        {"title": f"Rapport hebdomadaire du site – semaine du {fr(deb)}", "body": body, "labels": ["rapport"]},
        {"Authorization": f"Bearer {gh}", "Content-Type": "application/json", "Accept": "application/vnd.github+json"}, "POST")
    print("Rapport publié.")
