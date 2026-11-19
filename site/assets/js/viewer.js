// OpenSeadragon virtual slide viewer for bioatlas.io.
// URL: /viewer/?age=<ageId>&plane=<coronal|sagittal|transverse>&i=<slideNumber>
(function () {
  const cfg = BIOATLAS_CONFIG;
  const q = new URLSearchParams(location.search);
  const ageId = q.get("age");
  const plane = q.get("plane");
  let i = parseInt(q.get("i") || "1", 10);

  const age = ATLAS_DATA.ages.find(a => a.id === ageId);
  const series = age && age.planes[plane];
  const fallback = document.getElementById("fallback");

  if (!series) {
    fallback.style.display = "flex";
    document.getElementById("psuLink").href = cfg.PSU_BASE + "progress.php";
    document.getElementById("slideTitle").textContent = "Unknown slide";
    return;
  }

  if (typeof OpenSeadragon === "undefined") {
    // CDN unreachable — show the fallback link instead of a blank page
    document.getElementById("psuLink").href = psuFallbackUrl();
    fallback.style.display = "flex";
    return;
  }

  function psuFallbackUrl() {
    const s = series.slides.find(x => x.n === i) || series.slides[0];
    return cfg.PSU_BASE + "view.php?atlas=" + s.atlas + "&s=" + s.s;
  }

  const planeName = plane.charAt(0).toUpperCase() + plane.slice(1);
  const select = document.getElementById("slideSelect");
  series.slides.forEach(s => {
    const o = document.createElement("option");
    o.value = s.n;
    o.textContent = "Slide " + s.n + " / " + series.slides.length;
    select.appendChild(o);
  });

  function slideByN(n) { return series.slides.find(s => s.n === n); }
  function dziUrl(s) {
    return cfg.TILE_BASE + "/" + age.id + "/" + plane + "/" + s.atlas + "_" + s.s + ".dzi";
  }
  function psuUrl(s) {
    return cfg.PSU_BASE + "view.php?atlas=" + s.atlas + "&s=" + s.s;
  }

  const TILES = typeof BIOATLAS_TILES !== "undefined" ? BIOATLAS_TILES : {};
  const tiled = TILES[age.id + "/" + plane] || [];
  function hasTiles(s) { return tiled.indexOf(s.s) !== -1; }

  // Original Bio-Atlas tile pyramids (slides-index.js, written by
  // scripts/build_slide_index.py), shown as stored: level 0 is full
  // resolution, each further level is half the size, tiles are numbered row by
  // row, and the last levels are single images.
  const SLIDES = typeof BIOATLAS_SLIDES !== "undefined" ? BIOATLAS_SLIDES : {};
  function originalInfo(s) { return cfg.ORIGINAL_TILE_BASE ? SLIDES[s.s] : null; }
  function originalSource(s, info) {
    const w = info[0], h = info[1], tw = info[2], th = info[3];
    const levels = info[4], single = info[5];
    const top = Math.ceil(Math.log2(Math.max(w, h)));   // OpenSeadragon's full-resolution level
    const base = cfg.ORIGINAL_TILE_BASE + "/" + String(s.s).padStart(10, "0") + "/";
    function levelWidth(L) { return Math.ceil(w / Math.pow(2, L)); }
    function levelHeight(L) { return Math.ceil(h / Math.pow(2, L)); }
    return {
      width: w, height: h, tileWidth: tw, tileHeight: th, tileOverlap: 0,
      minLevel: top - (levels - 1), maxLevel: top,
      getTileWidth: function (level) {
        const L = top - level;
        return L >= single ? levelWidth(L) : tw;
      },
      getTileHeight: function (level) {
        const L = top - level;
        return L >= single ? levelHeight(L) : th;
      },
      getTileUrl: function (level, x, y) {
        const L = top - level;
        const cols = L >= single ? 1 : Math.ceil(levelWidth(L) / tw);
        return base + L + "/" + (y * cols + x) + ".jpg";
      },
    };
  }

  const viewer = OpenSeadragon({
    id: "osd",
    prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
    showNavigator: true,
    navigatorPosition: "BOTTOM_RIGHT",
    navigatorBackground: "#fff",
    showZoomControl: true,
    showHomeControl: true,
    showFullPageControl: true,
    maxZoomPixelRatio: 2,
    minZoomImageRatio: 0.8,
    visibilityRatio: 1,
    constrainDuringPan: true,
    gestureSettingsTouch: { pinchRotate: false },
  });

  viewer.addHandler("open-failed", function () {
    const s = slideByN(i);
    document.getElementById("psuLink").href = s ? psuUrl(s) : cfg.PSU_BASE;
    fallback.style.display = "flex";
  });
  viewer.addHandler("open", function () { fallback.style.display = "none"; });

  function load(n) {
    const s = slideByN(n);
    if (!s) return;
    i = n;
    select.value = String(n);
    document.getElementById("slideTitle").textContent =
      age.label + " · " + planeName + " · slide " + n + " of " + series.slides.length;
    document.title = age.label + " " + planeName + " " + n + " — BioAtlas";
    history.replaceState(null, "",
      "?age=" + encodeURIComponent(age.id) + "&plane=" + plane + "&i=" + n);
    const info = originalInfo(s);
    if (cfg.USE_PSU_FALLBACK && !info && !hasTiles(s)) {
      // Not migrated yet: offer the Penn State viewer without a failed load.
      viewer.close();
      document.getElementById("psuLink").href = psuUrl(s);
      fallback.style.display = "flex";
      return;
    }
    fallback.style.display = "none";
    viewer.open(info ? originalSource(s, info) : dziUrl(s));
  }

  const last = series.slides.length;
  document.getElementById("firstBtn").onclick = () => load(1);
  document.getElementById("prevBtn").onclick = () => load(Math.max(1, i - 1));
  document.getElementById("nextBtn").onclick = () => load(Math.min(last, i + 1));
  document.getElementById("lastBtn").onclick = () => load(last);
  select.onchange = () => load(parseInt(select.value, 10));
  document.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft") document.getElementById("prevBtn").click();
    if (e.key === "ArrowRight") document.getElementById("nextBtn").click();
  });

  load(isNaN(i) ? 1 : i);
})();
