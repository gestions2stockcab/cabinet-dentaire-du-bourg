"""Récupère la note, le nombre d'avis et les derniers avis de la fiche Google
(API Google Business Profile) et écrit avis.json à la racine du site.
Secrets GitHub nécessaires : GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
GOOGLE_REFRESH_TOKEN, GBP_ACCOUNT_ID, GBP_LOCATION_ID."""
import json, os, sys, urllib.parse, urllib.request, datetime

env = os.environ.get
need = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "GBP_ACCOUNT_ID", "GBP_LOCATION_ID"]
if not all(env(k) for k in need):
    print("Secrets manquants : rien à faire pour l'instant.")
    sys.exit(0)

def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    return json.load(urllib.request.urlopen(req, timeout=30))

def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req, timeout=30))

token = post("https://oauth2.googleapis.com/token", {
    "client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
    "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]

base = f"https://mybusiness.googleapis.com/v4/accounts/{env('GBP_ACCOUNT_ID')}/locations/{env('GBP_LOCATION_ID')}/reviews"
data = get(base + "?pageSize=50&orderBy=updateTime%20desc", token)

STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
# Avis affichés sur le site : les plus récents, 4 ou 5 étoiles, avec au moins MIN_LEN caractères
MIN_STARS = 4
MIN_LEN = 60
def original(t):
    # Google ajoute parfois une traduction : on garde le texte d'origine
    if "(Original)" in t:
        return t.split("(Original)", 1)[1].strip()
    return t.split("(Translated by Google)", 1)[0].strip()

reviews = []
for v in sorted(data.get("reviews", []), key=lambda v: v.get("createTime", ""), reverse=True):
    if not v.get("comment") or STARS.get(v.get("starRating"), 0) < MIN_STARS:
        continue
    if len(original(v["comment"])) < MIN_LEN:
        continue
    r = v.get("reviewer", {})
    reviews.append({
        "rating": STARS.get(v.get("starRating")),
        "text": original(v["comment"]),
        "author": "Patient" if r.get("isAnonymous") else r.get("displayName", "Patient"),
        "date": v.get("createTime"),
    })
    if len(reviews) == 6:
        break

out = {
    "rating": round(data["averageRating"], 1) if data.get("averageRating") else None,
    "count": data.get("totalReviewCount"),
    "reviews": reviews,
    "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
}
json.dump(out, open("avis.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{out['count']} avis, note {out['rating']}, {len(reviews)} avis affichés")
