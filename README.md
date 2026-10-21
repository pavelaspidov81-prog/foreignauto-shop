# Foreign Auto 5280 — foreignauto.shop

Website for **Foreign Auto 5280 LLC**, an auto repair shop in Aurora, Colorado.
Live at **https://foreignauto.shop** (served by GitHub Pages).

- Address: 3720 S Ouray Way, Aurora, CO 80013
- Phone and text: (720) 937-3445
- Languages: English and Russian

## What is in this repo

| Path | What it is |
| --- | --- |
| `index.html`, `about.html`, `*-repair.html` | English pages: home, about, one page per make |
| `ru/` | The same pages in Russian |
| `_src/` | Bilingual source of the home and about pages. Not published. |
| `_build.py`, `_brands.py` | Build script and make-page texts. Not published. |
| `robots.txt`, `sitemap.xml` | For search engines |
| `img/` | Photos used by the pages |
| `CNAME` | Tells GitHub Pages the site's domain (`foreignauto.shop`). Do not delete or rename it. |

The site is plain HTML. Whatever is in the `main` branch is what visitors see.

Text changes go into `_src/` (home, about) or `_brands.py` (make pages); then run `python3 _build.py` to regenerate the English and Russian pages. Files and folders starting with `_` are not published by GitHub Pages.

## How to update the site

1. Click **Add file → Upload files**.
2. Drop in the changed files with the same names. Photos go inside `img/`. To keep the folder, drag the whole `img` folder, not the loose photos.
3. Write a short note about the change and click **Commit changes**.
4. Open the **Actions** tab. When the "pages build and deployment" run shows a green tick, the change is live, usually within a couple of minutes.

Keep file names lowercase with no spaces, and leave `CNAME`, `index.html` and the `img` folder where they are.

## Hosting setup

- **Hosting:** GitHub Pages, deployed from `main`, folder `/ (root)`. Settings → Pages is available to the repo owner only.
- **Domain:** registered at Namecheap. Its nameservers point to Cloudflare.
- **DNS (Cloudflare):** four A records on `@` (185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153), four matching AAAA records (2606:50c0:8000::153 to 2606:50c0:8003::153), and `www` as a CNAME to `pavelaspidov81-prog.github.io`.
- **HTTPS:** a free certificate from GitHub, with Enforce HTTPS turned on.

## People

- Owner: @pavelaspidov81-prog
- Maintainer: @MariePerry
