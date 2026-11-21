"""Photos de la fiche Google « Espace dentaire Malakoff » (demandé par le Dr Atlan le 21/11/2026).
MODE=liste   : affiche les photos déjà présentes (lecture seule).
MODE=publier : publie la photo suivante de https://www.espacedentairemalakoff.fr/photos-google/liste.json
               (une par passage ; déjà publiées : photos_malakoff_vues.json). Ticket GitHub quand il n'en reste plus."""
import json, os, sys, urllib.parse, urllib.request, urllib.error
def env(k): return os.environ.get(k, "").strip().strip('"').strip("'").strip()
def call(url, token=None, data=None, js=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    body = urllib.parse.urlencode(data).encode() if data else None
    if js is not None: body = json.dumps(js).encode(); h["Content-Type"] = "application/json"
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h), timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} sur {urllib.parse.urlparse(url).path} : {e.read()[:400].decode('utf-8', 'replace')}")
token = call("https://oauth2.googleapis.com/token", data={"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
             "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
f = json.load(open("malakoff_fiche.json"))
base = f"https://mybusiness.googleapis.com/v4/accounts/{f['account']}/locations/{f['location']}/media"
MODE = env("MODE") or "liste"

if MODE == "fiche":   # lecture seule des infos de la fiche
    r = call(f"https://mybusinessbusinessinformation.googleapis.com/v1/locations/{f['location']}?readMask=title,websiteUri,categories,profile,regularHours,serviceItems,phoneNumbers,storefrontAddress,openInfo", token)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(0)

if MODE == "liste":
    items, tok = [], ""
    while True:
        r = call(base + "?pageSize=100" + (f"&pageToken={tok}" if tok else ""), token)
        items += r.get("mediaItems", []); tok = r.get("nextPageToken")
        if not tok: break
    print(f"Photos publiées par le propriétaire : {len(items)}")
    for m in items:
        print("PHOTO", m.get("locationAssociation", {}).get("category"), m.get("createTime"), m.get("description", ""), m.get("thumbnailUrl") or m.get("googleUrl"))
    sys.exit(0)

SITE = "https://www.espacedentairemalakoff.fr/photos-google/"
VUES = "photos_malakoff_vues.json"
vues = json.load(open(VUES)) if os.path.exists(VUES) else []
liste = json.load(urllib.request.urlopen(SITE + "liste.json", timeout=30))
reste = [p for p in liste if p["fichier"] not in vues]
def ticket(titre, corps):
    gh, repo = env("GH_TOKEN"), env("GITHUB_REPOSITORY")
    if not gh or not repo: return
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues", data=json.dumps({"title": titre, "body": corps}).encode(),
                                 headers={"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"})
    urllib.request.urlopen(req, timeout=30)
if not reste:
    print("Plus de photo à publier.")
    ticket("[Malakoff] Plus de photo à publier sur la fiche Google",
           "Toutes les photos prévues ont été publiées sur la fiche Google de l’Espace dentaire Malakoff.\n\nEnvoyez de nouvelles photos du centre pour continuer la publication mensuelle.")
    sys.exit(0)
p = reste[0]
r = call(base, token, js={"mediaFormat": "PHOTO", "locationAssociation": {"category": p.get("categorie", "INTERIOR")},
                          "sourceUrl": SITE + urllib.parse.quote(p["fichier"]), "description": p.get("description", "")})
print("Publiée :", p["fichier"], "→", r.get("name"), r.get("googleUrl"))
vues.append(p["fichier"]); json.dump(vues, open(VUES, "w"), ensure_ascii=False, indent=1)
if len(reste) == 2:
    ticket("[Malakoff] Plus qu’une photo en réserve pour la fiche Google",
           "Il ne reste qu’une photo à publier sur la fiche Google de l’Espace dentaire Malakoff (le mois prochain). Pensez à envoyer de nouvelles photos du centre.")
