"""Vérifie chaque jour que le site répond et qu'aucun lien n'est cassé.
En cas de problème, le script échoue : GitHub envoie alors un e-mail."""
import re, sys, urllib.request, urllib.parse
BASE = "https://www.cabinetdentairedubourg.fr"
UA = {"User-Agent": "Mozilla/5.0 (verification-site-cabinet)"}

def fetch(url, method="GET"):
    req = urllib.request.Request(url, headers=UA, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, (r.read().decode("utf-8", "replace") if method == "GET" else "")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)

problems = []
code, sm = fetch(BASE + "/sitemap.xml")
pages = re.findall(r"<loc>(.*?)</loc>", sm) if code == 200 else []
if not pages:
    problems.append(f"Plan du site inaccessible ({code})")
    pages = [BASE + "/"]

seen = set()
for page in pages:
    code, html = fetch(page)
    if code != 200:
        problems.append(f"{page} → {code}")
        continue
    html_sans_js = re.sub(r"<script>.*?</script>", "", html, flags=re.S)
    for ref in re.findall(r'(?:href|src)="([^"#]+)', html_sans_js):
        if ref.startswith(("tel:", "mailto:", "data:", "javascript:")):
            continue
        url = urllib.parse.urljoin(page, ref)
        if url in seen:
            continue
        seen.add(url)
        host = urllib.parse.urlparse(url).netloc
        if host.endswith("cabinetdentairedubourg.fr"):
            c, _ = fetch(url, "HEAD")
            if c != 200:
                problems.append(f"Lien cassé sur {page} : {url} → {c}")
        elif any(h in host for h in ("doctolib.fr", "rcpt.ai")):
            c, _ = fetch(url, "GET")
            # Doctolib peut refuser les robots (403) : seul un 404 ou une absence de réponse compte
            if c in (0, 404, 410):
                problems.append(f"Lien externe cassé sur {page} : {url} → {c}")

print(f"{len(pages)} pages et {len(seen)} liens vérifiés.")
if problems:
    print("PROBLÈMES :")
    print("\n".join(problems))
    sys.exit(1)
print("Tout est en ordre.")
