"""Vérifie la fiche Google (titre, site web, catégories) et l'accès Search Console. N'affiche aucun secret."""
import json, os, urllib.parse, urllib.request, urllib.error
def post(url, data):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST"), timeout=30))
def get(url, token):
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=30))
    except urllib.error.HTTPError as e:
        return {"erreur": e.code, "detail": e.read().decode()[:400]}
token = post("https://oauth2.googleapis.com/token", {
    "client_id": os.environ["GOOGLE_CLIENT_ID"].strip(), "client_secret": os.environ["GOOGLE_CLIENT_SECRET"].strip(),
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"].strip(), "grant_type": "refresh_token"})["access_token"]
loc = os.environ["GBP_LOCATION_ID"].strip()
f = get(f"https://mybusinessbusinessinformation.googleapis.com/v1/locations/{loc}?readMask=title,websiteUri,categories,phoneNumbers,storefrontAddress", token)
print("FICHE GOOGLE")
print(json.dumps(f, ensure_ascii=False, indent=1))
info = get("https://oauth2.googleapis.com/tokeninfo?access_token=" + token, token)
print("SCOPES :", info.get("scope", info))
sc = get("https://www.googleapis.com/webmasters/v3/sites", token)
print("SEARCH CONSOLE :", json.dumps(sc, ensure_ascii=False)[:600])
