"""Photos de la fiche Google « Espace dentaire Malakoff ».
mode=liste : affiche les photos déjà présentes (lecture seule)."""
import json, os, sys, urllib.parse, urllib.request, urllib.error
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
f = json.load(open("malakoff_fiche.json"))
base = f"https://mybusiness.googleapis.com/v4/accounts/{f['account']}/locations/{f['location']}/media"
items, tok = [], ""
while True:
    r = call(base + "?pageSize=100" + (f"&pageToken={tok}" if tok else ""), token)
    items += r.get("mediaItems", []); tok = r.get("nextPageToken")
    if not tok: break
print(f"Photos publiées par le propriétaire : {len(items)} (total annoncé : {r.get('totalMediaItemCount')})")
for m in items:
    print("PHOTO", m.get("locationAssociation", {}).get("category"), m.get("mediaFormat"), m.get("createTime"),
          (m.get("dimensions") or {}).get("widthPixels"), (m.get("dimensions") or {}).get("heightPixels"), m.get("thumbnailUrl") or m.get("googleUrl"))
try:
    c = call(base.replace("/media", "/media/customers") + "?pageSize=1", token)
    print("Photos ajoutées par les clients :", c.get("totalMediaItemCount"))
except Exception as e: print("Photos clients : non lisibles", e)
