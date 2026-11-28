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
# descriptions (factuelles, sans téléphone) et catégorie de chaque service existant (Simon, 28/11/2026)
DESC = {
 "Urgence dentaire": ("emergency_dental_service", "Urgences dentaires reçues du lundi au vendredi, de 9 h à 19 h, selon les disponibilités : rage de dents, dent cassée, joue gonflée."),
 "Bilan et contrôle dentaire": (None, "Examen des dents et des gencives, radiographies si besoin, conseils d’hygiène."),
 "Détartrage": (None, "Retrait du tartre et polissage, conseillé une à deux fois par an."),
 "Traitement de canal (dévitalisation)": (None, "Traitement de canal (endodontie) d’une dent infectée ou très douloureuse."),
 "Parodontie : soins des gencives, surfaçage radiculaire": ("periodontist", "Gencives qui saignent, déchaussement : bilan parodontal et surfaçage radiculaire, avec le Dr Bénédicte Rioual Vergnol."),
 "Greffe osseuse et sinus lift": ("dental_implants_provider", "Reconstruction de l’os avant la pose d’un implant quand il manque de volume, avec le Dr Alicia Soussan."),
 "Implant dentaire": ("dental_implants_provider", "Pose d’implants et de couronnes sur implant, avec le Dr Alicia Soussan. Devis remis avant le traitement."),
 "Couronne dentaire": (None, "Couronne en céramique ou en zircone pour protéger une dent très abîmée."),
 "Inlay-core, inlay / onlay": (None, "Inlay et onlay en céramique ou en composite ; inlay-core pour reconstruire une dent dévitalisée."),
 "Bridge dentaire": (None, "Bridge en céramique ou en zircone pour remplacer une dent manquante en s’appuyant sur les dents voisines."),
 "Prothèse amovible (stellite) et prothèse complète": (None, "Prothèse partielle à châssis métallique (stellite) ou prothèse complète, éventuellement stabilisée sur implants."),
 "Facettes dentaires": (None, "Fines pellicules collées sur la face visible des dents, pour corriger leur forme ou leur teinte."),
 "Extraction dentaire": (None, "Extraction d’une dent qui ne peut pas être conservée, sous anesthésie locale."),
 "Orthodontie enfant et adolescent": (None, "Bilan orthodontique dès 6 ans, orthodontie préventive et appareils multi-attaches, avec le Dr Carla Levy, orthodontiste spécialiste."),
 "Orthodontie adulte": (None, "Aligneurs transparents, orthodontie linguale ou attaches en céramique, après un bilan des dents et des gencives, avec le Dr Carla Levy."),
 "Aligneurs invisibles": (None, "Gouttières transparentes sur mesure pour aligner les dents des adolescents et des adultes, avec le Dr Carla Levy."),
 "Orthodontie linguale": (None, "Appareil collé sur la face interne des dents, côté langue, invisible de face."),
 "Appareil multi-attaches (métal ou céramique)": (None, "Bagues métalliques ou en céramique couleur des dents, pour enfants, adolescents et adultes."),
}
if env("MODE") != "publier": sys.exit(0)
noms = {c.get("name") for c in [prim] + cats.get("additionalCategories", [])}
new = []
for it in items:
    f = it.get("freeFormServiceItem")
    if not f: new.append(it); continue
    t = f["label"]["displayName"]; cat, d = DESC.get(t, (None, None))
    c = f"categories/gcid:{cat}" if cat and f"categories/gcid:{cat}" in noms else prim["name"]
    lab = {"displayName": t, "languageCode": "fr"}
    if d: lab["description"] = d
    elif f["label"].get("description"): lab["description"] = f["label"]["description"]
    new.append({"freeFormServiceItem": {"category": c, "label": lab}})
r = call(U + "?updateMask=serviceItems", token, method="PATCH", js={"serviceItems": new})
print(f"Publié : {len(r.get('serviceItems', []))} service(s) sur la fiche.")
for it in r.get("serviceItems", []): print(" -", json.dumps(it, ensure_ascii=False))
