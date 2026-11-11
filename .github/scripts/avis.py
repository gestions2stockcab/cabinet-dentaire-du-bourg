"""Récupère la note, le nombre d'avis et les derniers avis de la fiche Google
(API Google Business Profile) et écrit avis.json à la racine du site.
Secrets GitHub nécessaires : GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
GOOGLE_REFRESH_TOKEN, GBP_ACCOUNT_ID, GBP_LOCATION_ID."""
import json, os, sys, urllib.parse, urllib.request, datetime

def env(k, d=None):
    v = os.environ.get(k, d)
    return v.strip().strip('"').strip("'").strip() if isinstance(v, str) else v
need = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "GBP_ACCOUNT_ID", "GBP_LOCATION_ID"]
manquants = [k for k in need if not env(k)]
if manquants:
    print("Secrets manquants : " + ", ".join(manquants) + ". Rien à faire pour l'instant.")
    sys.exit(0)
print("Longueur des secrets :", {k: len(env(k)) for k in need})

def fail(step, e):
    body = e.read().decode("utf-8", "replace")[:500] if hasattr(e, "read") else str(e)
    print(f"ERREUR à l'étape « {step} » : {getattr(e, 'code', '')} {body}")
    if "invalid_grant" in body:
        print("→ Le secret GOOGLE_REFRESH_TOKEN est invalide ou mal copié (il doit commencer par 1//).")
    if "invalid_client" in body:
        print("→ GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET est mal copié.")
    if "404" in str(getattr(e, "code", "")):
        print("→ GBP_ACCOUNT_ID ou GBP_LOCATION_ID est incorrect.")
    sys.exit(1)

def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        fail("connexion à Google", e)

def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        fail("lecture des avis", e)

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
