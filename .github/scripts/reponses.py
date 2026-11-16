"""Réponses automatiques aux avis Google à 4 ou 5 étoiles sans réponse (validé par le Dr Atlan le 15/11/2026).
Règles : jamais de réponse automatique sous 4 étoiles ; aucun détail de soin, de praticien ni de situation (secret médical) ;
formulations variées ; prénom si disponible. Au plus MAX réponses par passage (rattrapage progressif des anciens avis)."""
import hashlib, json, os, re, sys, time, urllib.parse, urllib.request

def env(k): return os.environ.get(k, "").strip().strip('"').strip("'").strip()
def call(url, data=None, token=None, method=None, form=False):
    h = {"Accept": "application/json"}
    if token: h["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        if form: body = urllib.parse.urlencode(data).encode()
        else: h["Content-Type"] = "application/json"; body = json.dumps(data).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method), timeout=40))

MAX = int(env("MAX") or 40)
# fiche : Savigny par défaut ; Malakoff avec FICHE_JSON=malakoff_fiche.json (activé par le Dr Atlan le 16/11/2026)
DU = env("DU") or "du Cabinet Dentaire du Bourg"
FICHE = json.load(open(env("FICHE_JSON"))) if env("FICHE_JSON") else {"account": env("GBP_ACCOUNT_ID"), "location": env("GBP_LOCATION_ID")}
REFAIRE = env("REFAIRE") != "0"   # Malakoff : ne jamais toucher aux réponses déjà publiées
MODELES = [
    "Merci beaucoup pour votre message, il fait plaisir à toute l’équipe !",
    "Merci pour votre confiance et pour ce retour. Toute l’équipe {DU} vous remercie.",
    "Un grand merci pour ces mots, toute l’équipe est ravie.",
    "Merci d’avoir pris le temps de laisser cet avis. Toute l’équipe y est très sensible.",
    "Merci beaucoup ! Ce retour fait chaud au cœur à toute l’équipe.",
    "Merci pour ce très beau retour, il est partagé avec toute l’équipe {DU}.",
    "Nous vous remercions chaleureusement pour votre confiance et pour ce message.",
    "Merci infiniment pour votre avis, toute l’équipe vous remercie.",
    "Merci pour votre message, il est très apprécié par toute l’équipe.",
    "Un grand merci pour votre confiance et pour ces quelques mots.",
]
# formulations retirées (elles laissaient entendre une relation de soin) : réponses à refaire si déjà publiées
A_REFAIRE = ("accueillir", "vous revoir", "fidélité", "au cabinet.", "à bientôt")
STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}

def prenom(v):
    r = v.get("reviewer", {})
    if r.get("isAnonymous"): return ""
    p = (r.get("displayName") or "").strip().split(" ")[0]
    # prénom plausible uniquement (lettres, tirets, accents ; pas d'initiale seule, pas de pseudo)
    return p if re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ][a-zà-öø-ÿ'’-]{1,20}", p) else ""

def texte(v):
    k = int(hashlib.md5((v.get("reviewId") or v.get("name", "")).encode()).hexdigest(), 16)
    t = MODELES[k % len(MODELES)].replace("{DU}", DU)
    p = prenom(v)
    return (f"Bonjour {p}, " + t[0].lower() + t[1:]) if p else ("Bonjour, " + t[0].lower() + t[1:])

tok = call("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
           "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"}, form=True)["access_token"]
base = f"https://mybusiness.googleapis.com/v4/accounts/{FICHE['account']}/locations/{FICHE['location']}/reviews"
a_faire, page = [], ""
while True:
    d = call(base + "?pageSize=50&orderBy=updateTime%20desc" + (f"&pageToken={page}" if page else ""), token=tok)
    for v in d.get("reviews", []):
        rep = (v.get("reviewReply") or {}).get("comment", "")
        if STARS.get(v.get("starRating"), 0) >= 4 and (not rep or (REFAIRE and rep.startswith("Bonjour") and any(x in rep.lower() for x in A_REFAIRE) and "équipe" in rep)):
            a_faire.append(v)
    page = d.get("nextPageToken")
    if not page: break
print(f"{len(a_faire)} avis à 4-5 étoiles sans réponse ; {min(MAX, len(a_faire))} réponses ce passage")
n = 0
for v in a_faire[:MAX]:
    t = texte(v)
    try:
        call(f"https://mybusiness.googleapis.com/v4/{v['name']}/reply", {"comment": t}, tok, "PUT")
        n += 1; print("✓", v.get("createTime", "")[:10], STARS.get(v.get("starRating")), "★ →", t)
    except urllib.error.HTTPError as e:
        print("✗", e.code, e.read().decode()[:200])
    time.sleep(2)
print(f"{n} réponse(s) publiée(s)")
