"""Avis Google de la fiche « Espace dentaire Malakoff » (autre fiche, gérée par le même compte Google).
Écrit avis-malakoff.json à la racine du site, lu UNIQUEMENT par le site de Malakoff (jamais affiché sur Savigny).
Pas de réponses automatiques ni d'alertes pour Malakoff (non demandées par le Dr Atlan).
Secrets : GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN (les mêmes que Savigny)."""
import datetime, json, os, sys, urllib.parse, urllib.request, urllib.error

def env(k): return os.environ.get(k, "").strip().strip('"').strip("'").strip()
def call(url, token=None, data=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    body = urllib.parse.urlencode(data).encode() if data else None
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h), timeout=30))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} sur {urllib.parse.urlparse(url).path} : {e.read()[:300].decode('utf-8', 'replace')}")

token = call("https://oauth2.googleapis.com/token", data={"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
             "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]

# 1. trouver la fiche (mémorisée dans malakoff_fiche.json après la première recherche)
CACHE = "malakoff_fiche.json"
fiche = json.load(open(CACHE)) if os.path.exists(CACHE) else None
if not fiche:
    trouvees = []
    accs = call("https://mybusinessaccountmanagement.googleapis.com/v1/accounts?pageSize=20", token).get("accounts", [])
    for a in accs:
        tok = ""
        while True:
            r = call(f"https://mybusinessbusinessinformation.googleapis.com/v1/{a['name']}/locations?readMask=name,title,storefrontAddress&pageSize=100"
                     + (f"&pageToken={tok}" if tok else ""), token)
            for l in r.get("locations", []):
                adr = " ".join((l.get("storefrontAddress") or {}).get("addressLines", [])) + " " + (l.get("storefrontAddress") or {}).get("locality", "")
                print("Fiche accessible :", l.get("title"), "|", adr.strip())
                if "malakoff" in (l.get("title", "") + adr).lower():
                    trouvees.append({"account": a["name"].split("/")[-1], "location": l["name"].split("/")[-1], "title": l.get("title"), "adresse": adr.strip()})
            tok = r.get("nextPageToken")
            if not tok: break
    if not trouvees:
        sys.exit("Fiche de Malakoff introuvable parmi les fiches accessibles (voir la liste ci-dessus).")
    fiche = trouvees[0]
    json.dump(fiche, open(CACHE, "w"), ensure_ascii=False, indent=1)
print("Fiche :", fiche["title"], "|", fiche["adresse"])

# 2. avis (mêmes règles que Savigny : 4-5 étoiles, au moins 60 caractères, les plus récents)
data = call(f"https://mybusiness.googleapis.com/v4/accounts/{fiche['account']}/locations/{fiche['location']}/reviews?pageSize=50&orderBy=updateTime%20desc", token)
STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
def original(t):
    if "(Original)" in t: return t.split("(Original)", 1)[1].strip()
    return t.split("(Translated by Google)", 1)[0].strip()
reviews = []
for v in sorted(data.get("reviews", []), key=lambda v: v.get("createTime", ""), reverse=True):
    if not v.get("comment") or STARS.get(v.get("starRating"), 0) < 4 or len(original(v["comment"])) < 60: continue
    r = v.get("reviewer", {})
    reviews.append({"rating": STARS.get(v.get("starRating")), "text": original(v["comment"]),
                    "author": "Patient" if r.get("isAnonymous") else r.get("displayName", "Patient"), "date": v.get("createTime"), "authorUrl": None})
    if len(reviews) == 6: break
out = {"rating": round(data["averageRating"], 1) if data.get("averageRating") else None, "count": data.get("totalReviewCount"),
       "reviews": reviews, "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
json.dump(out, open("avis-malakoff.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"Malakoff : {out['count']} avis, note {out['rating']}, {len(reviews)} avis retenus")
