// Shared navbar. Each page defines ROOT ("." at site root, ".." one level down)
// and includes <div id="nav"></div> before this script.
(function () {
  const R = typeof ROOT !== "undefined" ? ROOT : ".";
  const here = (typeof PAGE !== "undefined") ? PAGE : "";
  function cls(p) { return p === here ? ' class="active"' : ""; }
  document.getElementById("nav").innerHTML =
    '<div class="navbar">' +
    '<a class="brand" href="' + R + '/">BioAtlas</a>' +
    '<a' + cls("home") + ' href="' + R + '/">Home</a>' +
    '<div class="dropdown_nav">' +
      '<button class="dropbtn">Anatomy &#9662;</button>' +
      '<div class="dropdown_nav-content">' +
        '<a href="' + R + '/atlas/">Zebrafish Atlas</a>' +
        '<a href="' + R + '/atlas/#labeled">Labeled series</a>' +
        '<a href="' + R + '/3d/">3D Micro-CT</a>' +
      "</div>" +
    "</div>" +
    '<a' + cls("atlas") + ' style="font-weight:900" href="' + R + '/atlas/">Atlas</a>' +
    '<a' + cls("3d") + ' href="' + R + '/3d/">3D</a>' +
    '<a' + cls("references") + ' href="' + R + '/references/">References</a>' +
    '<a' + cls("resources") + ' href="' + R + '/resources/">Resources</a>' +
    '<a' + cls("updates") + ' href="' + R + '/updates/">Updates</a>' +
    "</div>";
})();
