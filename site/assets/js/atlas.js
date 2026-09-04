// Builds the atlas sample table (daphnia.io/zf_temp-style) from ATLAS_DATA.
(function () {
  const cfg = BIOATLAS_CONFIG;
  const tbody = document.getElementById("tableBody");
  const pending = [];

  function slideHref(age, plane, slide) {
    if (cfg.USE_PSU_FALLBACK) {
      return cfg.PSU_BASE + "view.php?atlas=" + slide.atlas + "&s=" + slide.s;
    }
    return "../viewer/?age=" + encodeURIComponent(age.id) +
           "&plane=" + plane + "&i=" + slide.n;
  }

  function stageRow(age, count) {
    const tr = document.createElement("tr");
    tr.className = "stage-row";
    const td = document.createElement("td");
    td.colSpan = 2;
    td.style.backgroundColor = (stageRow.k++ % 2 === 0) ? "#333" : "#555";
    td.innerHTML = age.label +
      (age.size ? '<span class="size">' + age.size + "</span>" : "") +
      '<span class="badge">' + count + " slides</span>";
    tr.appendChild(td);
    tbody.appendChild(tr);
  }
  stageRow.k = 0;

  function planeRow(age, plane, series) {
    const tr = document.createElement("tr");

    const name = plane.charAt(0).toUpperCase() + plane.slice(1);
    const o = document.createElement("td");
    o.className = "orientation";
    o.title = ATLAS_DATA.planeLabels[plane];
    o.innerHTML = name + (series.labeled
      ? '<span class="labeled-tag" title="This series contains annotated slides">labeled</span>'
      : "");
    tr.appendChild(o);

    const cell = document.createElement("td");
    cell.className = "samples";
    series.slides.forEach(function (slide) {
      const a = document.createElement("a");
      a.href = slideHref(age, plane, slide);
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = slide.n < 10 ? "0" + slide.n : String(slide.n);
      if (series.labeled) a.className = "labeled";
      a.title = age.label + " · " + name + " · slide " + slide.n;
      cell.appendChild(a);
    });
    tr.appendChild(cell);
    tbody.appendChild(tr);
  }

  // Orange "3D" pill row (Neuroglancer volumes attached to this stage),
  // in the style of the daphnia.io 3D links.
  function volumeRow(vols) {
    const tr = document.createElement("tr");
    const o = document.createElement("td");
    o.className = "orientation";
    o.innerHTML = "3D Micro-CT <span style='letter-spacing:1px;color:#999'>(Neuroglancer)</span>";
    tr.appendChild(o);
    const cell = document.createElement("td");
    cell.className = "samples";
    vols.forEach(function (vol) {
      const a = document.createElement("a");
      a.className = "pill3d";
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.href = vol.basic3dUrl || NG.url(vol, "full");
      a.innerHTML = "&#9632; 3D";
      a.title = vol.label;
      cell.appendChild(a);
    });
    tr.appendChild(cell);
    tbody.appendChild(tr);
  }

  const haveNG = typeof BIOATLAS_VOLUMES !== "undefined" && typeof NG !== "undefined";

  ATLAS_DATA.ages.forEach(function (age) {
    const planes = Object.keys(age.planes);
    const vols = haveNG
      ? BIOATLAS_VOLUMES.filter(v => (v.stageIds || []).indexOf(age.id) !== -1)
      : [];
    if (planes.length === 0 && vols.length === 0) { pending.push(age.label); return; }
    let count = 0;
    planes.forEach(function (p) { count += age.planes[p].slides.length; });
    stageRow(age, count);
    ["coronal", "sagittal", "transverse"].forEach(function (p) {
      if (age.planes[p]) planeRow(age, p, age.planes[p]);
    });
    if (vols.length) volumeRow(vols);
  });

  const totalEl = document.getElementById("slideTotal");
  if (totalEl) totalEl.textContent = ATLAS_DATA.totalSlides;

  const pendingEl = document.getElementById("pendingStages");
  if (pendingEl && pending.length) {
    pendingEl.textContent = "In preparation: " + pending.join(" · ");
  }
})();
