"""Statistiques du site pour le tableau de bord privé (/tableau-de-bord/).
Récupère GoatCounter (+ Search Console si autorisé), chiffre le tout (AES-256-GCM, clé dérivée
du secret STATS_KEY par PBKDF2) et écrit stats.enc.json à la racine du dépôt.
Secrets : GOATCOUNTER_TOKEN, STATS_KEY ; facultatifs : GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN."""
import base64, datetime as dt, json, os, urllib.parse, urllib.request
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def env(k): return os.environ.get(k, "").strip().strip('"').strip("'").strip()
def req(url, data=None, headers=None, method=None):
    h = {"Accept": "application/json"}; h.update(headers or {})
    body = json.dumps(data).encode() if isinstance(data, dict) and h.get("Content-Type") == "application/json" else (urllib.parse.urlencode(data).encode() if data else None)
    return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method), timeout=60))

today = dt.date.today(); end = today                     # jusqu'à aujourd'hui inclus
d90 = today - dt.timedelta(days=89); d30 = today - dt.timedelta(days=29)
p30e = d30 - dt.timedelta(days=1); p30s = p30e - dt.timedelta(days=29)
iso = lambda d: f"{d}T00:00:00Z"
endiso = f"{today + dt.timedelta(days=1)}T00:00:00Z"
out = {"updated": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z", "today": str(today)}

base = "https://cabinetdentairedubourg.goatcounter.com/api/v0"
H = {"Authorization": f"Bearer {env('GOATCOUNTER_TOKEN')}", "Content-Type": "application/json"}
def total(a, b_iso):
    return req(f"{base}/stats/total?start={iso(a)}&end={b_iso}", headers=H)
def hits(a, b_iso, limit=50):
    return req(f"{base}/stats/hits?start={iso(a)}&end={b_iso}&limit={limit}&group=day", headers=H).get("hits", [])
def page(name, a, b_iso, limit=8):
    r = req(f"{base}/stats/{name}?start={iso(a)}&end={b_iso}&limit={limit}", headers=H)
    return [{"name": x.get("name") or "(direct)", "n": x.get("count", 0)} for x in (r.get("stats") or r.get("refs") or [])]

try:
    t = total(d90, endiso)
    out["daily"] = [{"d": s["day"], "v": s.get("daily", 0)} for s in t.get("stats", [])]
    h30 = hits(d30, endiso); hp = hits(p30s, iso(d30))
    def ev(hs, name):
        for x in hs:
            if x.get("event") and x.get("path") == name: return x
        return {}
    def cnt(hs, name): return ev(hs, name).get("count", 0)
    vis30 = total(d30, endiso).get("total", 0); visp = total(p30s, iso(d30)).get("total", 0)
    ev30 = total(d30, endiso).get("total_events", 0); evp = total(p30s, iso(d30)).get("total_events", 0)
    out["cur"] = {"visitors": vis30 - ev30, "doctolib": cnt(h30, "Clic Doctolib"), "tel": cnt(h30, "Clic téléphone")}
    out["prev"] = {"visitors": visp - evp, "doctolib": cnt(hp, "Clic Doctolib"), "tel": cnt(hp, "Clic téléphone")}
    h90 = hits(d90, endiso)
    for key, name in (("doctolib", "Clic Doctolib"), ("tel", "Clic téléphone")):
        out.setdefault("events_daily", {})[key] = [{"d": s["day"], "v": s.get("daily", 0)} for s in ev(h90, name).get("stats", [])]
    out["pages"] = [{"path": x.get("path"), "title": x.get("title", ""), "n": x.get("count", 0)} for x in h30 if not x.get("event")][:12]
    for name in ("toprefs", "sizes", "systems", "browsers", "locations"):
        try: out[name] = page(name, d30, endiso)
        except Exception as e: out[name] = []; out.setdefault("errors", []).append(f"{name}: {e}")
except Exception as e:
    out.setdefault("errors", []).append(f"GoatCounter : {e}")

# Search Console (facultatif : nécessite le scope webmasters.readonly)
try:
    tok = req("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
              "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
    site = urllib.parse.quote("sc-domain:cabinetdentairedubourg.fr", safe="")
    url = f"https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
    GH = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    ge = today - dt.timedelta(days=3); gs = ge - dt.timedelta(days=27)
    rows = req(url, {"startDate": str(gs), "endDate": str(ge)}, GH, "POST").get("rows", [])
    tot = rows[0] if rows else {"clicks": 0, "impressions": 0, "position": None, "ctr": 0}
    q = req(url, {"startDate": str(gs), "endDate": str(ge), "dimensions": ["query"], "rowLimit": 10}, GH, "POST").get("rows", [])
    out["gsc"] = {"start": str(gs), "end": str(ge), "clicks": tot.get("clicks", 0), "impressions": tot.get("impressions", 0),
                  "position": tot.get("position"), "queries": [{"q": r["keys"][0], "clicks": r["clicks"], "impr": r["impressions"], "pos": r["position"]} for r in q]}
except Exception as e:
    out["gsc"] = {"error": "Search Console non autorisée (refaire le jeton avec le scope webmasters.readonly)."}

key_src = env("STATS_KEY")
if not key_src: raise SystemExit("Secret STATS_KEY manquant : ajoutez-le dans Settings > Secrets and variables > Actions.")
salt = os.urandom(16); iv = os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=250000).derive(key_src.encode())
ct = AESGCM(key).encrypt(iv, json.dumps(out, ensure_ascii=False).encode(), None)
b = lambda x: base64.b64encode(x).decode()
json.dump({"v": 1, "kdf": "PBKDF2-SHA256", "it": 250000, "salt": b(salt), "iv": b(iv), "ct": b(ct), "updated": out["updated"]}, open("stats.enc.json", "w"))
print("stats.enc.json écrit ;", "erreurs :", out.get("errors", "aucune"))
