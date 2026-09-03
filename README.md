# bioatlas.io — Zebrafish Atlas

A static, GitHub-Pages-ready rebuild of the Penn State Zebrafish Atlas
([bio-atlas.psu.edu/zf/progress.php](https://bio-atlas.psu.edu/zf/progress.php))
in the layout style of [daphnia.io/zf_temp](https://daphnia.io/zf_temp/):
dark parallax hero, stage-banded sample table with numbered slide pills, and an
in-browser OpenSeadragon virtual slide viewer.

## What's in this repo

```
site/                     <- everything that gets published to bioatlas.io
  index.html              <- home page
  atlas/index.html        <- the atlas table (progress.php equivalent)
  viewer/index.html       <- OpenSeadragon virtual slide viewer
  references|resources|updates/  <- placeholder section pages
  assets/css/style.css    <- all styling
  assets/js/atlas-data.js <- the full dataset: 630 slides, 17 stages, 3 planes
  assets/js/config.js     <- TILE_BASE + fallback switch (see below)
  assets/js/atlas.js      <- builds the table from the dataset
  assets/js/viewer.js     <- viewer logic (prev/next, keyboard, fallback)
  assets/js/nav.js        <- shared navbar
  CNAME                   <- "bioatlas.io" (required for the custom domain)
  .nojekyll               <- tells GitHub Pages to serve files as-is
scripts/
  download_slides.py      <- migrates slide imagery from PSU to DZI pyramids
build_data.py + raw_data.txt <- regenerate atlas-data.js if the dataset changes
```

The dataset in `atlas-data.js` was extracted from the PSU progress page on
2026-08-28 and contains every slide's PSU `atlas` and `s` identifiers, so both
the fallback links and the migration script know exactly what to fetch.

## Going live, step by step

### 1. Create the GitHub repo and push

```bash
cd bioatlas
git init
git add .
git commit -m "Initial bioatlas.io site"
# create a repo named e.g. bioatlas on github.com, then:
git remote add origin git@github.com:<YOUR-USERNAME>/bioatlas.git
git branch -M main
git push -u origin main
```

### 2. Turn on GitHub Pages

Repo **Settings → Pages**:
- Source: **Deploy from a branch**
- Branch: **main**, folder: **/site** is not offered by GitHub (it only offers
  `/ (root)` or `/docs`) — so either rename `site/` to `docs/` and pick
  **main /docs**, or keep `site/` and use the tiny Actions workflow below.

Option A (simplest): `git mv site docs && git commit -am "docs for Pages" && git push`,
then choose **main / docs** in the Pages settings.

Option B (keep `site/`): add `.github/workflows/pages.yml`:

```yaml
name: Deploy to GitHub Pages
on:
  push: { branches: [main] }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  deploy:
    environment: { name: github-pages, url: "${{ steps.deployment.outputs.page_url }}" }
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
      - id: deployment
        uses: actions/deploy-pages@v4
```
and in **Settings → Pages** set Source to **GitHub Actions**.

### 3. Point bioatlas.io at GitHub Pages

At your DNS provider for `bioatlas.io`:

| Type  | Name | Value |
|-------|------|-------|
| A     | @    | 185.199.108.153 |
| A     | @    | 185.199.109.153 |
| A     | @    | 185.199.110.153 |
| A     | @    | 185.199.111.153 |
| CNAME | www  | `<YOUR-USERNAME>.github.io` |

Then in **Settings → Pages** enter `bioatlas.io` as the custom domain (the
`CNAME` file in this repo keeps that setting across deploys) and tick
**Enforce HTTPS** once the certificate is issued (can take up to a day).

### 4. Publish updates

Every `git push` to `main` redeploys the site. Edit → commit → push → live.

## The slide imagery (the important caveat)

On day 1 the site works immediately: `USE_PSU_FALLBACK: true` in
`site/assets/js/config.js` makes every slide pill open the original PSU
viewer, exactly like the daphnia page links out to its own viewer.

To serve the images from bioatlas.io itself, run the migration:

```bash
pip install requests pillow pyvips
brew install vips        # or: sudo apt install libvips
python3 scripts/download_slides.py --dry-run     # see the size first
python3 scripts/download_slides.py --age 48hpf   # try one stage
python3 scripts/download_slides.py               # everything (hours!)
```

It writes DZI pyramids to `site/tiles/<age>/<plane>/<atlas>_<s>.dzi`, the
exact layout `viewer.js` expects. Then set `USE_PSU_FALLBACK: false` and the
pills open your own viewer at `/viewer/`.

**Size warning:** all 630 slides at full 40x resolution are far larger than
GitHub's ~1 GB Pages limit (think tens of GB). Options:

1. **Host tiles on object storage** (recommended): upload `site/tiles/` to
   Cloudflare R2 (free egress) or S3/B2, enable public access + CORS `GET *`,
   and set `TILE_BASE` in `config.js` to that URL, e.g.
   `https://tiles.bioatlas.io`. The daphnia.io site does exactly this
   (its DZIs are served from an S3-backed path).
2. **Reduced resolution**: `--level 1` (20x) or `--level 2` (10x) shrinks the
   dataset ~4x/16x — a small subset may then fit in the repo for testing.
3. **Subset in repo**: migrate only the most-used stages into the repo and
   keep the PSU fallback for the rest (the viewer automatically shows a
   fallback link for any slide whose tiles are missing).

Also check with the atlas's creators (Cheng Lab, Penn State) about permission
and citation before republishing the imagery — the original site asks users to
cite the atlas.

## 3D micro-CT (Neuroglancer)

The **/3d/** page lists volumetric datasets from `site/assets/js/volumes.js`
and opens them in Neuroglancer with three presets:

- **Full 3D render** — shaded volume rendering with ambient occlusion,
  sorted compositing, progressive LOD and 4096 depth samples, matching the
  cephalopod.team reference view. These options exist only in the Cheng Lab /
  cephalopod.team "webXR" Neuroglancer fork, so this preset opens in that
  team's hosted client (`NG_CLIENT_FULL` in `config.js`). The per-volume
  settings live under `fullRender` in `volumes.js`.
- **3D (basic)** — stock Neuroglancer volume rendering in the client bundled
  in this repo (adjust `opacity3d` / `alphaGamma` / contrast sliders in the
  layer's rendering tab to peel tissue away);
- **Slice view** — 4-panel view; hold `Shift` and drag in any cross-section
  panel to rotate the slicing plane in **any direction**.

The webXR fork has no public repository. Its deployed client is just static
files, so the durable move is to ask the cephalopod.team / Cheng Lab
collaborators for their client build (or its source), drop it into
`site/neuroglancer-xr/`, and set `NG_CLIENT_FULL: "/neuroglancer-xr/"` —
every generated link keeps working, now served from bioatlas.io. Until then,
be aware the Full-render links depend on their versioned URL
(`.../webXR/08062026_v1/client/`) staying up; the basic preset is fully
self-contained either way.

The atlas table also shows orange **3D** pills on stages that have a volume
(daphnia.io style). Shipping config includes the public 33dpf zebrafish
histotomography (Cheng Lab / ZeACCF, served from cephalopod.team) with its
anatomical annotation labels.

### The Neuroglancer client

`config.js` points `NG_CLIENT` at `/neuroglancer/` — a static build of the
Google Neuroglancer client living in `site/neuroglancer/`. If that folder is
missing (or you prefer not to host it), set
`NG_CLIENT: "https://neuroglancer-demo.appspot.com"` — Google's hosted client
works identically since all data loads client-side. To (re)build your own:

```bash
git clone https://github.com/google/neuroglancer.git
cd neuroglancer && npm install && npm run build
cp -r dist/client/* ../site/neuroglancer/
```

Note: advanced options in the cephalopod.team example (volume-rendering
shading/AO, WebXR) come from their custom Neuroglancer fork
(`cephalopod.team/histotomography/webXR/...`). The states this site generates
use only stock-Neuroglancer features so they work with the standard client;
if you later host that fork on bioatlas.io, point `NG_CLIENT` at it and the
same links keep working.

### Hosting your own 3D volumes

1. Convert your reconstruction (TIFF stack) to precomputed format:
   ```bash
   pip install cloud-volume igneous-pipeline tifffile
   python3 scripts/make_precomputed.py ./recon_slices ./volumes/myfish/image \
       --voxel-size 1.4 1.4 1.4
   ```
2. Upload the output folder to storage with public read + CORS
   (`Access-Control-Allow-Origin: *` on GET/HEAD). Cloudflare R2 is a good
   default (free egress). Volumes are usually many GB — do **not** put them in
   the GitHub repo.
3. Add an entry in `site/assets/js/volumes.js` pointing at the URL (a
   commented template is included), set `stageIds` to the atlas stage(s) it
   belongs to, commit, push — the /3d/ page and the atlas 3D pills update
   automatically.

## Local preview

```bash
cd site && python3 -m http.server 8000
# open http://localhost:8000
```

## Regenerating the dataset

If PSU adds slides, re-extract the table into `raw_data.txt`
(format: `age|planeIndex|n:atlas:s,...`) and run `python3 build_data.py`.
