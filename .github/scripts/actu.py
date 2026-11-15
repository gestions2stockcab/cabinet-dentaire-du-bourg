"""Publie chaque mois un « conseil du mois » sur la fiche Google du cabinet (Google Business Profile, localPosts).
Les fiches viennent de actu.json (généré par build.py à partir des fiches conseils validées par le Dr Atlan).
actu_last.json mémorise le dernier mois publié (pas de doublon). Secrets : ceux de avis.yml."""
import datetime as dt, json, os, sys, urllib.parse, urllib.request

def env(k): return os.environ.get(k, "").strip().strip('"').strip("'").strip()
def call(url, data=None, token=None, method=None):
    h = {"Accept": "application/json"}
    body = None
    if token: h["Authorization"] = f"Bearer {token}"
    if isinstance(data, dict) and token:
        h["Content-Type"] = "application/json"; body = json.dumps(data).encode()
    elif data: body = urllib.parse.urlencode(data).encode()
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method), timeout=40))
    except urllib.error.HTTPError as e:
        sys.exit(f"Erreur Google {e.code} : {e.read().decode()[:600]}")

SITE = "https://www.cabinetdentairedubourg.fr"
# ordre de publication : prévention d'abord, puis les suites de soins
ORDRE = ["gencives", "enfants", "sensibilite", "mauvaise-haleine", "tabac", "diabete", "sport-protege-dents", "grossesse",
         "apres-detartrage", "blanchiment", "gouttiere-bruxisme", "apres-soin-carie", "couronne-provisoire",
         "apres-devitalisation", "apres-implant", "apres-extraction", "prothese-amovible"]
fiches = {f["slug"]: f for f in json.load(open("actu.json", encoding="utf-8"))}
liste = [fiches[s] for s in ORDRE if s in fiches] + [f for s, f in fiches.items() if s not in ORDRE]

MODE = os.environ.get("MODE", "")
if MODE in ("etat", "nettoyer"):
    tok = call("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
               "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
    base = f"https://mybusiness.googleapis.com/v4/accounts/{env('GBP_ACCOUNT_ID')}/locations/{env('GBP_LOCATION_ID')}/localPosts"
    for p_ in call(base + "?pageSize=10", token=tok).get("localPosts", []):
        print("ACTU", p_.get("createTime"), p_.get("state"), "|", (p_.get("summary") or "")[:70].replace("\n", " "))
        if MODE == "nettoyer" and p_.get("state") == "REJECTED":
            urllib.request.urlopen(urllib.request.Request("https://mybusiness.googleapis.com/v4/" + p_["name"], headers={"Authorization": f"Bearer {tok}"}, method="DELETE"), timeout=40)
            print("   supprimée")
    sys.exit(0)
mois = dt.date.today().strftime("%Y-%m")
last = json.load(open("actu_last.json")) if os.path.exists("actu_last.json") else {"mois": None, "n": -1}
if last.get("mois") == mois and os.environ.get("FORCER") != "1":
    print("Déjà publié ce mois-ci :", mois); sys.exit(0)
n = (last.get("n", -1) + 1) % len(liste)
f = liste[n]
url = f"{SITE}/conseils-patients/{f['slug']}/"
puces = "\n".join("• " + c for c in f.get("conseils", [])[:3])
texte = (f"Conseil du mois : {f['accroche']}\n\n{f['resume']}\n\n{puces}\n\n"
         "La fiche complète, à lire en ligne ou à télécharger en PDF, est sur notre site. "
         "Une question ? Le cabinet est joignable 24 h/24 au 01 83 86 97 81.")[:1450]

tok = call("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
           "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
base = f"https://mybusiness.googleapis.com/v4/accounts/{env('GBP_ACCOUNT_ID')}/locations/{env('GBP_LOCATION_ID')}/localPosts"
post = {"languageCode": "fr", "topicType": "STANDARD", "summary": texte,
        "callToAction": {"actionType": "LEARN_MORE", "url": url},
        "media": [{"mediaFormat": "PHOTO", "sourceUrl": f"{SITE}/img/actu.jpg"}]}
r = call(base, post, tok, "POST")
print("Publié :", f["titre"], "→", r.get("searchUrl") or r.get("name"), "| état :", r.get("state"))
json.dump({"mois": mois, "n": n, "slug": f["slug"], "post": r.get("name")}, open("actu_last.json", "w"))
