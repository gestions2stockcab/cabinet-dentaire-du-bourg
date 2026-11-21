"""Publication hebdomadaire sur la fiche Google de l'ESPACE DENTAIRE MALAKOFF (accord du Dr Atlan le 21/11/2026).
Source : flux public du site de Malakoff https://www.espacedentairemalakoff.fr/actu-malakoff.json
({"image", "items": [{"date","titre","texte","url"}]}, du plus récent au plus ancien).
Publie le plus récent article pas encore publié (mémoire : actu_last_malakoff.json), au nom de la fiche de Malakoff uniquement.
Aucun lien avec le site ni la fiche de Savigny. Pas de numéro de téléphone dans le texte (refusé par Google).
Modes : MODE=etat (liste des publications de la fiche), MODE=nettoyer (supprime les refusées)."""
import json, os, re, sys, urllib.error, urllib.parse, urllib.request

FEED = "https://www.espacedentairemalakoff.fr/actu-malakoff.json"
def env(k): return os.environ.get(k, "").strip().strip('"').strip("'").strip()
def call(url, data=None, token=None, method=None, form=False):
    h = {"Accept": "application/json", "User-Agent": "actu-malakoff"}
    if token: h["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        if form: body = urllib.parse.urlencode(data).encode()
        else: h["Content-Type"] = "application/json"; body = json.dumps(data).encode()
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method), timeout=40))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} sur {urllib.parse.urlparse(url).path} : {e.read()[:300].decode('utf-8', 'replace')}")

fiche = json.load(open("malakoff_fiche.json"))
assert "malakoff" in fiche.get("title", "").lower(), "malakoff_fiche.json ne désigne pas la fiche de Malakoff"
tok = call("https://oauth2.googleapis.com/token", {"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
           "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"}, form=True)["access_token"]
base = f"https://mybusiness.googleapis.com/v4/accounts/{fiche['account']}/locations/{fiche['location']}/localPosts"
print("Fiche :", fiche["title"], "|", fiche.get("adresse", ""))

MODE = env("MODE")
if MODE in ("etat", "nettoyer"):
    for p in call(base + "?pageSize=10", token=tok).get("localPosts", []):
        print("ACTU", p.get("createTime"), p.get("state"), "|", (p.get("summary") or "")[:80].replace("\n", " "))
        if MODE == "nettoyer" and p.get("state") == "REJECTED":
            urllib.request.urlopen(urllib.request.Request("https://mybusiness.googleapis.com/v4/" + p["name"],
                                   headers={"Authorization": f"Bearer {tok}"}, method="DELETE"), timeout=40)
            print("   supprimée")
    sys.exit(0)

flux = call(FEED)
items = sorted(flux.get("items", []), key=lambda x: x.get("date", ""), reverse=True)
LAST = "actu_last_malakoff.json"
last = json.load(open(LAST)) if os.path.exists(LAST) else {"publies": []}
faits = set(last.get("publies", []))
a_faire = [it for it in items if it.get("url") and it["url"] not in faits]
if not a_faire:
    print("Rien de nouveau à publier."); sys.exit(0)
it = a_faire[0]
if not it["url"].startswith("https://www.espacedentairemalakoff.fr/"):
    sys.exit("Lien hors du site de Malakoff : refusé.")
texte = f"{it['titre']} : {it['texte']}"
texte = re.sub(r"(\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}", "", texte)            # jamais de numéro de téléphone
texte = re.sub(r"\s{2,}", " ", texte).strip()[:1450]
if re.search(r"savigny|du bourg", texte, re.I):
    sys.exit("Le texte mentionne Savigny : refusé (les deux structures restent séparées).")
post = {"languageCode": "fr", "topicType": "STANDARD", "summary": texte,
        "callToAction": {"actionType": "LEARN_MORE", "url": it["url"]}}
if flux.get("image"): post["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": flux["image"]}]
r = call(base, post, tok, "POST")
print("Publié sur la fiche de Malakoff :", it["titre"], "| état :", r.get("state"))
last["publies"] = sorted(faits | {it["url"]})
last.update({"dernier": it["url"], "date": it.get("date"), "post": r.get("name")})
json.dump(last, open(LAST, "w"), ensure_ascii=False, indent=1)
