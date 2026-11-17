"""Rubrique « Actualités » du site (demandée par le Dr Atlan le 17/11/2026).
Chaque mois, le conseil publié sur la fiche Google (actu.py) devient aussi un article du site.
actualites.json (racine du dépôt) = liste des articles {"mois","date","slug"} ; le contenu vient de actu.json (fiches validées).
Le gabarit actualites/_modele.html est produit par pages.py (build.py) avec l'en-tête et le pied de page du site.
Usage : python3 .github/scripts/actualites.py [dossier_du_site] [actualites.json]"""
import html, json, os, re, sys

U = "https://www.cabinetdentairedubourg.fr"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
def date_fr(d):
    a, m, j = d.split("-"); return f"{int(j)} {MOIS[int(m) - 1]} {a}"
def mois_fr(m):
    a, mm = m.split("-"); return f"{MOIS[int(mm) - 1]} {a}"

def render(root=".", entries_path="actualites.json"):
    modele = open(os.path.join(root, "actualites/_modele.html"), encoding="utf-8").read()
    fiches = {f["slug"]: f for f in json.load(open(os.path.join(root, "actu.json"), encoding="utf-8"))}
    arts = [a for a in (json.load(open(entries_path, encoding="utf-8")) if os.path.exists(entries_path) else []) if a.get("slug") in fiches]
    arts.sort(key=lambda a: a["date"], reverse=True)
    E = html.escape
    def page(path, title, desc, crumb, h1, lead, body, ld, otype="website"):
        h = (modele.replace("__TITLE__", E(title)).replace("__DESC__", E(desc)).replace("__CANON__", U + path)
             .replace("__OGTYPE__", otype).replace("__LD__", json.dumps(ld, ensure_ascii=False))
             .replace("__CRUMB__", crumb).replace("__H1__", E(h1)).replace("__LEAD__", E(lead)).replace("__BODY__", body))
        os.makedirs(os.path.join(root, path.strip("/")), exist_ok=True)
        open(os.path.join(root, path.strip("/"), "index.html"), "w", encoding="utf-8").write(h)
    urls = []
    for a in arts:
        f = fiches[a["slug"]]; path = f"/actualites/{a['mois']}-{a['slug']}/"
        titre = f"Conseil de {mois_fr(a['mois'])} : {f['titre']}"
        puces = "".join(f"<li>{E(c)}</li>" for c in f.get("conseils", [])[:3])
        body = (f'<p class="meta">Publié le {date_fr(a["date"])}</p>'
                f'<p>{E(f["accroche"])}{"" if f["accroche"].rstrip()[-1:] in "?!." else "."} {E(f["resume"])}</p>'
                f'<h2 class="h3">Les conseils essentiels</h2><ul>{puces}</ul>'
                f'<p>Tous les détails, ce qui est normal et quand consulter, sont dans la fiche complète, à lire en ligne ou à télécharger en PDF.</p>'
                f'<p><a class="btn arrow" href="/conseils-patients/{a["slug"]}/">Lire la fiche « {E(f["titre"])} »</a></p>')
        ld = [{"@context": "https://schema.org", "@type": "BlogPosting", "headline": titre, "datePublished": a["date"], "inLanguage": "fr",
               "url": U + path, "mainEntityOfPage": U + path, "image": U + "/img/actu.jpg", "description": f["resume"],
               "author": {"@id": U + "/#cabinet"}, "publisher": {"@id": U + "/#cabinet"}},
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Accueil", "item": U + "/"},
                  {"@type": "ListItem", "position": 2, "name": "Actualités", "item": U + "/actualites/"},
                  {"@type": "ListItem", "position": 3, "name": titre, "item": U + path}]}]
        page(path, titre + " – Cabinet Dentaire du Bourg", f["resume"], f'<a href="/">Accueil</a> › <a href="/actualites/">Actualités</a> › {E(f["titre"])}',
             f["titre"], f'Conseil du mois · {mois_fr(a["mois"])}', body, ld, "article")
        urls.append(U + path)
    cartes = "".join(
        f'<a class="act" href="/actualites/{a["mois"]}-{a["slug"]}/"><span class="meta">{mois_fr(a["mois"]).capitalize()}</span>'
        f'<h2 class="h3">{E(fiches[a["slug"]]["titre"])}</h2><p>{E(fiches[a["slug"]]["resume"])}</p><span class="more">Lire →</span></a>' for a in arts) \
        or '<p>Le premier article arrive bientôt.</p>'
    ld = {"@context": "https://schema.org", "@type": "Blog", "name": "Actualités du Cabinet Dentaire du Bourg", "url": U + "/actualites/", "inLanguage": "fr",
          "publisher": {"@id": U + "/#cabinet"}}
    page("/actualites/", "Actualités et conseil du mois – Cabinet Dentaire du Bourg, Savigny-le-Temple",
         "Chaque mois, un conseil de l’équipe du Cabinet Dentaire du Bourg à Savigny-le-Temple pour prendre soin de vos dents et de vos gencives.",
         '<a href="/">Accueil</a> › Actualités', "Actualités", "Chaque mois, un conseil de l’équipe pour prendre soin de vos dents.",
         f'<div class="acts">{cartes}</div>', ld)
    urls.append(U + "/actualites/")
    # plan du site
    sm_p = os.path.join(root, "sitemap.xml")
    if os.path.exists(sm_p):
        sm = open(sm_p, encoding="utf-8").read()
        add = "".join(f"  <url><loc>{u}</loc><priority>0.6</priority></url>\n" for u in urls if f"<loc>{u}</loc>" not in sm)
        if add: open(sm_p, "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    return len(arts)

if __name__ == "__main__":
    print(render(sys.argv[1] if len(sys.argv) > 1 else ".", sys.argv[2] if len(sys.argv) > 2 else "actualites.json"), "article(s)")
