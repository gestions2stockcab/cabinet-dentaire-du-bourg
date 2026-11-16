"""Statistiques du site pour le tableau de bord privé (/tableau-de-bord/).
Récupère GoatCounter (+ Search Console si autorisé), chiffre le tout (AES-256-GCM, clé dérivée
du secret STATS_KEY par PBKDF2) et écrit stats.enc.json à la racine du dépôt.
Secrets : GOATCOUNTER_TOKEN, STATS_KEY ; facultatifs : GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN."""
import base64, datetime as dt, json, os, urllib.error, urllib.parse, urllib.request
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def env(k): return os.environ.get(k, "").strip().strip('"').strip("'").strip()
def req(url, data=None, headers=None, method=None):
    h = {"Accept": "application/json"}; h.update(headers or {})
    body = json.dumps(data).encode() if isinstance(data, dict) and h.get("Content-Type") == "application/json" else (urllib.parse.urlencode(data).encode() if data else None)
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method), timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} sur {urllib.parse.urlparse(url).path} : {e.read()[:200].decode('utf-8','replace')}")

today = dt.date.today(); end = today                     # jusqu'à aujourd'hui inclus
d90 = today - dt.timedelta(days=89); d365 = today - dt.timedelta(days=364); d7 = today - dt.timedelta(days=6); d30 = today - dt.timedelta(days=29)
p30e = d30 - dt.timedelta(days=1); p30s = p30e - dt.timedelta(days=29)
iso = lambda d: f"{d}T00:00:00Z"
endiso = f"{today + dt.timedelta(days=1)}T00:00:00Z"
out = {"updated": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z", "today": str(today)}

# deuxième site (Malakoff) : SITE=malakoff → GoatCounter espacedentairemalakoff, fiche malakoff_fiche.json, sortie stats-malakoff.enc.json
MK = env("SITE") == "malakoff"
base = f"https://{'espacedentairemalakoff' if MK else 'cabinetdentairedubourg'}.goatcounter.com/api/v0"
H = {"Authorization": f"Bearer {env('GOATCOUNTER_TOKEN')}", "Content-Type": "application/json"}

def total(a, b_iso):
    return req(f"{base}/stats/total?start={iso(a)}&end={b_iso}", headers=H)
def hits(a, b_iso, limit=50):
    return req(f"{base}/stats/hits?start={iso(a)}&end={b_iso}&limit={limit}&group=day", headers=H).get("hits", [])
def page(name, a, b_iso, limit=8):
    r = req(f"{base}/stats/{name}?start={iso(a)}&end={b_iso}&limit={limit}", headers=H)
    return [{"name": x.get("name") or "(direct)", "n": x.get("count", 0)} for x in (r.get("stats") or r.get("refs") or [])]

try:
    t = total(d365, endiso)
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
    h90 = hits(d365, endiso)
    for key, name in (("doctolib", "Clic Doctolib"), ("tel", "Clic téléphone")):
        out.setdefault("events_daily", {})[key] = [{"d": s["day"], "v": s.get("daily", 0)} for s in ev(h90, name).get("stats", [])]
    out["pages"] = [{"path": x.get("path"), "title": x.get("title", ""), "n": x.get("count", 0)} for x in h30 if not x.get("event")][:12]
    # tableaux par période : aujourd'hui (j), 7 jours (s), 30 jours (m)
    out["by"] = {}
    for per, a in (("j", today), ("s", d7), ("m", d30)):
        hh = h30 if per == "m" else hits(a, endiso)
        b = {"pages": [{"path": x.get("path"), "title": x.get("title", ""), "n": x.get("count", 0)} for x in hh if not x.get("event")][:12]}
        try: b["toprefs"] = page("toprefs", a, endiso)
        except Exception: b["toprefs"] = []
        out["by"][per] = b
    for name in ("toprefs", "sizes", "systems", "browsers", "locations"):
        try: out[name] = page(name, d30, endiso)
        except Exception as e: out[name] = []; out.setdefault("errors", []).append(f"{name}: {e}")
except Exception as e:
    out.setdefault("errors", []).append(f"GoatCounter : {e}")


# ---------- heures et jours de visite (30 jours, GoatCounter) ----------
try:
    tt = total(d30, endiso).get("stats", [])
    hrs = [0]*24; wd = [0]*7
    for x in tt:
        for i, v in enumerate(x.get("hourly") or []): hrs[i % 24] += v or 0
        wd[dt.date.fromisoformat(x["day"]).weekday()] += x.get("daily", 0) or 0
    out["hours"] = hrs; out["weekdays"] = wd
except Exception as e:
    out.setdefault("errors", []).append(f"heures : {e}")

# ---------- Google : jeton, fiche (performances) et avis ----------
STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
gtok = None
try:
    gtok = req("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
               "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
except Exception as e:
    out.setdefault("errors", []).append(f"Google (jeton) : {e}")
ACC, LOC = env("GBP_ACCOUNT_ID"), env("GBP_LOCATION_ID")
if MK:
    _f = json.load(open("malakoff_fiche.json")); ACC, LOC = _f["account"], _f["location"]
if gtok and LOC:
    GA = {"Authorization": f"Bearer {gtok}"}
    try:
        M = {"BUSINESS_IMPRESSIONS_DESKTOP_MAPS": "vues", "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH": "vues", "BUSINESS_IMPRESSIONS_MOBILE_MAPS": "vues",
             "BUSINESS_IMPRESSIONS_MOBILE_SEARCH": "vues", "CALL_CLICKS": "appels", "BUSINESS_DIRECTION_REQUESTS": "itin", "WEBSITE_CLICKS": "site"}
        a, b = d365, today
        q = "&".join(f"dailyMetrics={k}" for k in M) + (f"&dailyRange.startDate.year={a.year}&dailyRange.startDate.month={a.month}&dailyRange.startDate.day={a.day}"
             f"&dailyRange.endDate.year={b.year}&dailyRange.endDate.month={b.month}&dailyRange.endDate.day={b.day}")
        r = req(f"https://businessprofileperformance.googleapis.com/v1/locations/{LOC}:fetchMultiDailyMetricsTimeSeries?{q}", headers=GA)
        days = {}
        for grp in r.get("multiDailyMetricTimeSeries", []):
            for ser in grp.get("dailyMetricTimeSeries", []):
                k = M.get(ser.get("dailyMetric"))
                for dv in ser.get("timeSeries", {}).get("datedValues", []):
                    d = dv["date"]; key = f"{d['year']:04d}-{d['month']:02d}-{d['day']:02d}"
                    days.setdefault(key, {"d": key, "vues": 0, "appels": 0, "itin": 0, "site": 0})[k] += int(dv.get("value", 0) or 0)
        daily = [days[k] for k in sorted(days)]
        while daily and not any(daily[-1][k] for k in ("vues", "appels", "itin", "site")): daily.pop()  # Google a quelques jours de retard
        out["gbp"] = {"daily": daily}
    except Exception as e:
        out["gbp"] = {"error": str(e)[:300]}
    try:
        base_r = f"https://mybusiness.googleapis.com/v4/accounts/{ACC}/locations/{LOC}/reviews"
        allr, tokn, info = [], "", {}
        for _ in range(40):
            r = req(f"{base_r}?pageSize=50" + (f"&pageToken={tokn}" if tokn else ""), headers=GA)
            info = info or r; allr += r.get("reviews", []); tokn = r.get("nextPageToken")
            if not tokn: break
        rv = [{"d": v.get("createTime", "")[:10], "s": STARS.get(v.get("starRating"), 0), "rep": bool(v.get("reviewReply")),
               "nom": (v.get("reviewer") or {}).get("displayName", ""), "txt": (v.get("comment") or "")[:280]} for v in allr]
        low = [x for x in sorted(rv, key=lambda x: x["d"], reverse=True) if x["s"] and x["s"] <= 3][:6]
        out["avis"] = {"note": round(info.get("averageRating") or 0, 2), "total": info.get("totalReviewCount", len(rv)),
                       "sans_reponse": sum(1 for x in rv if not x["rep"]), "sans_reponse_bas": sum(1 for x in rv if not x["rep"] and x["s"] <= 3),
                       "dates": [[x["d"], x["s"]] for x in rv if x["d"] >= str(d365)], "bas": low}
    except Exception as e:
        out["avis"] = {"error": str(e)[:300]}

# ---------- état du site : automatisations, Lighthouse, conseil du mois ----------
if not MK:
    try:
        GHH = {"Authorization": f"Bearer {env('GH_TOKEN')}", "Accept": "application/vnd.github+json"}
        repo = env("GITHUB_REPOSITORY")
        etat = []
        for f, nom in (("verification.yml", "Vérification des pages et liens"), ("avis.yml", "Avis Google et réponses"), ("actu.yml", "Conseil du mois sur Google"),
                       ("qualite.yml", "Contrôle qualité (Lighthouse)"), ("rapport.yml", "Rapport du lundi"), ("indexnow.yml", "Signalement à Bing (IndexNow)")):
            try:
                runs = req(f"https://api.github.com/repos/{repo}/actions/workflows/{f}/runs?per_page=1", headers=GHH).get("workflow_runs", [])
                x = runs[0] if runs else {}
                etat.append({"nom": nom, "ok": x.get("conclusion"), "d": x.get("created_at"), "url": x.get("html_url")})
            except Exception as e:
                etat.append({"nom": nom, "ok": None, "err": str(e)[:120]})
        out["etat"] = etat
    except Exception as e:
        out.setdefault("errors", []).append(f"état : {e}")
    for fn, k in (("qualite.json", "qualite"), ("actu_last.json", "actu_last")):
        try: out[k] = json.load(open(fn))
        except Exception: pass
    try:
        fl0 = json.load(open("actu.json")); fd = {f["slug"]: f for f in fl0}
        ORDRE = [l for l in open(".github/scripts/actu.py").read().split("ORDRE = ", 1)[1].split("]", 1)[0].replace("[", "").replace("\n", " ").split(",")]
        ORDRE = [o.strip().strip('"') for o in ORDRE if o.strip()]
        fl = [fd[x] for x in ORDRE if x in fd] + [f for f in fl0 if f["slug"] not in ORDRE]
        al = out.get("actu_last") or {}
        out["actu"] = {"titre": next((f.get("titre") for f in fl if f.get("slug") == al.get("slug")), al.get("slug")),
                       "suivant": fl[(al.get("n", -1) + 1) % len(fl)].get("titre") if fl else None, "mois": al.get("mois")}
    except Exception as e:
        out.setdefault("errors", []).append(f"actu : {e}")

# Search Console (facultatif : nécessite le scope webmasters.readonly)
try:
    tok = req("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
              "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
    site = urllib.parse.quote("sc-domain:" + ("espace-dentaire-malakoff.fr" if MK else "cabinetdentairedubourg.fr"), safe="")
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

import unicodedata
print("Résumé :", {"jours": len(out.get("daily", [])), "heures": bool(out.get("hours")),
      "fiche": out.get("gbp", {}).get("error") or f'{len(out.get("gbp", {}).get("daily", []))} jours',
      "avis": out.get("avis", {}).get("error") or f'{out.get("avis", {}).get("total")} avis',
      "etat": [(x["nom"], x.get("ok"), x.get("err")) for x in out.get("etat", [])], "actu": out.get("actu"), "qualite": bool(out.get("qualite"))})
key_src = unicodedata.normalize("NFC", os.environ.get("STATS_KEY", "")).strip()
if not key_src: raise SystemExit("Secret STATS_KEY manquant : ajoutez-le dans Settings > Secrets and variables > Actions.")
OUTF = "stats-malakoff.enc.json" if MK else "stats.enc.json"
salt = os.urandom(16); iv = os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=250000).derive(key_src.encode())
ct = AESGCM(key).encrypt(iv, json.dumps(out, ensure_ascii=False).encode(), None)
b = lambda x: base64.b64encode(x).decode()
json.dump({"v": 1, "kdf": "PBKDF2-SHA256", "it": 250000, "salt": b(salt), "iv": b(iv), "ct": b(ct), "updated": out["updated"]}, open(OUTF, "w"))
print(OUTF, "écrit ;", "erreurs :", out.get("errors", "aucune"))
