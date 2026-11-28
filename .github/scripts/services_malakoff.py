"""Rubrique « Services » de la fiche Google de l'Espace dentaire Malakoff (Simon, 28/11/2026).
MODE=lire : affiche catégories et services ; MODE=publier : ajoute les services ci-dessous (garde ceux qui existent).
Textes factuels, sans numéro de téléphone ni promotion."""
import json, os, sys, urllib.parse, urllib.request, urllib.error
def env(k): return os.environ.get(k, "").strip()
def call(url, token=None, data=None, method=None, js=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    body = urllib.parse.urlencode(data).encode() if data else None
    if js is not None: body = json.dumps(js).encode(); h["Content-Type"] = "application/json"
    try: return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h, method=method), timeout=30))
    except urllib.error.HTTPError as e: sys.exit(f"HTTP {e.code} : {e.read()[:800].decode('utf-8','replace')}")
token = call("https://oauth2.googleapis.com/token", data={"client_id": env("GOOGLE_CLIENT_ID"), "client_secret": env("GOOGLE_CLIENT_SECRET"),
             "refresh_token": env("GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"})["access_token"]
LOC = json.load(open("malakoff_fiche.json"))["location"]
U = f"https://mybusinessbusinessinformation.googleapis.com/v1/locations/{LOC}"
loc = call(U + "?readMask=title,categories,serviceItems", token)
cats = loc.get("categories", {})
prim = cats.get("primaryCategory", {})
print("Catégorie principale :", prim.get("name"), prim.get("displayName"))
for c in cats.get("additionalCategories", []): print("Autre catégorie :", c.get("name"), c.get("displayName"))
items = loc.get("serviceItems", [])
print(f"{len(items)} service(s) actuel(s) :")
for it in items: print(" -", json.dumps(it, ensure_ascii=False))
for st in prim.get("serviceTypes", []) or []: print("Type proposé :", st.get("serviceTypeId"), st.get("displayName"))
S = [("Orthodontie enfants et adolescents", "Bilan orthodontique dès 6 ans, orthodontie préventive et appareils multi-attaches, avec le Dr Carla Levy, orthodontiste spécialiste."),
     ("Orthodontie adulte", "Aligneurs transparents, orthodontie linguale (côté langue) ou attaches en céramique, après un bilan des dents et des gencives."),
     ("Aligneurs transparents", "Gouttières transparentes sur mesure pour aligner les dents des adolescents et des adultes, avec le Dr Carla Levy."),
     ("Parodontie (soins des gencives)", "Gencives qui saignent, déchaussement : bilan parodontal, détartrage et surfaçage radiculaire, avec le Dr Bénédicte Rioual Vergnol."),
     ("Implants dentaires", "Pose d’implants et de couronnes sur implant, avec greffe osseuse ou sinus lift si l’os manque de volume, avec le Dr Alicia Soussan."),
     ("Urgences dentaires", "Urgences dentaires reçues du lundi au vendredi, de 9 h à 19 h, selon les disponibilités."),
     ("Détartrage et soins courants", "Contrôle, détartrage, soins des caries et radiographies."),
     ("Couronnes et bridges", "Couronnes et bridges en céramique ou en zircone, sur devis remis avant le traitement."),
     ("Dévitalisation", "Traitement de canal (endodontie) d’une dent infectée ou très douloureuse.")]
if env("MODE") != "publier": sys.exit(0)
deja = {(it.get("freeFormServiceItem", {}).get("label", {}).get("displayName") or "").lower() for it in items}
new = list(items) + [{"freeFormServiceItem": {"category": prim["name"], "label": {"displayName": t, "description": d, "languageCode": "fr"}}}
                     for t, d in S if t.lower() not in deja]
r = call(U + "?updateMask=serviceItems", token, method="PATCH", js={"serviceItems": new})
print(f"Publié : {len(r.get('serviceItems', []))} service(s) sur la fiche.")
