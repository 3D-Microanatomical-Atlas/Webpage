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

  const viewer = OpenSeadragon({
    id: "osd",
    prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
    showNavigator: true,
    navigatorPosition: "BOTTOM_RIGHT",
    maxZoomPixelRatio: 2,
    minZoomImageRatio: 0.8,
    visibilityRatio: 1,
    constrainDuringPan: true,
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
    fallback.style.display = "none";
    viewer.open(dziUrl(s));
  }

  document.getElementById("prevBtn").onclick = () => load(Math.max(1, i - 1));
  document.getElementById("nextBtn").onclick = () =>
    load(Math.min(series.slides.length, i + 1));
  select.onchange = () => load(parseInt(select.value, 10));
  document.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft") document.getElementById("prevBtn").click();
    if (e.key === "ArrowRight") document.getElementById("nextBtn").click();
  });

  load(isNaN(i) ? 1 : i);
})();
