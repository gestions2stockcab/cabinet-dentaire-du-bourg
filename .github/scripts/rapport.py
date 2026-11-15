"""Rapport hebdomadaire : visiteurs et clics (GoatCounter) + lien vers la Search Console.
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

# ---------- Google ----------
# (le jeton Search Console n'est pas configuré : les recherches Google se consultent directement dans la Search Console)
lines += ["### Recherches Google", "", "À consulter dans la [Search Console](https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain:cabinetdentairedubourg.fr) : recherches tapées, position du site, clics.", ""]

lines += ["---", "Détails : [GoatCounter](https://cabinetdentairedubourg.goatcounter.com) · [Search Console](https://search.google.com/search-console/performance/search-analytics?resource_id=sc-domain:cabinetdentairedubourg.fr)"]
body = "\n".join(lines)
print(body)

repo, gh = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
if repo and gh:
    req(f"https://api.github.com/repos/{repo}/issues",
        {"title": f"Rapport hebdomadaire du site – semaine du {fr(deb)}", "body": body},
        {"Authorization": f"Bearer {gh}", "Content-Type": "application/json", "Accept": "application/vnd.github+json"}, "POST")
    print("Rapport publié.")
