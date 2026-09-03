// Builds Neuroglancer states + URLs for the datasets in volumes.js.
// Used by the /3d/ page and by atlas.js for the orange "3D" pills.

const NG = (function () {
  // Image shader with volume-rendering support: sliders for window (lo/hi),
  // brightness/contrast, and 3D opacity/gamma. Works in 2D cross-sections and
  // in the volume-rendered 3D view (VOLUME_RENDERING define).
  const IMAGE_SHADER = [
    '#uicontrol vec3 color color(default="white")',
    "#uicontrol float lo slider(default=0, min=0, max=1, step=0.01)",
    "#uicontrol float hi slider(default=1, min=0, max=1, step=0.01)",
    "#uicontrol float brightness slider(default=0, min=-1, max=1, step=0.01)",
    "#uicontrol float contrast slider(default=0, min=-3, max=3, step=0.01)",
    "#uicontrol float opacity3d slider(default=0.05, min=0, max=0.5, step=0.001)",
    "#uicontrol float alphaGamma slider(default=1.0, min=0.25, max=4.0, step=0.05)",
    "float rescale(float x) {",
    "  return (x - lo) / (hi - lo);",
    "}",
    "void main() {",
    "  float v = clamp(rescale(toNormalized(getDataValue())) + brightness, 0.0, 1.0) * exp(contrast);",
    "  vec3 rgb = color * v;",
    "#ifdef VOLUME_RENDERING",
    "  float a = pow(clamp(v, 0.0, 1.0), alphaGamma) * opacity3d;",
    "  emitRGBA(vec4(rgb, a));",
    "#else",
    "  emitRGB(rgb);",
    "#endif",
    "}",
  ].join("\n");

  // Volume-rendering shading used by the "full render" preset — matches the
  // cephalopod.team webXR client's look (ambient occlusion + diffuse/specular
  // + rim lighting). Only understood by NG_CLIENT_FULL; the stock client
  // ignores these extended options.
  const FULL_SHADING = {
    ambient: 1,
    aoDensity: 9.772372209558107,
    aoStrength: 0.49,
    diffuse: 0.93,
    fillStrength: 0.28,
    specular: 0.03,
    shininess: 34,
    rimStrength: 0.06,
    rimExponent: 6.6,
    lightAzimuth: -37,
    lightElevation: -68,
    boundary: 1,
    boundaryThreshold: 0.0019054607179632462,
    gradientSigma: 1.4091914656322275,
  };

  function layers(vol, mode) {
    const full = mode === "full";
    const fr = vol.fullRender || {};
    const img = {
      type: "image",
      source: {
        url: vol.image,
        subsources: { default: true, bounds: true },
        enableDefaultSubsources: false,
      },
      tab: "rendering",
      opacity: 1,
      shader: IMAGE_SHADER,
      shaderControls: full
        ? Object.assign({}, vol.imageControls, fr.controls || {})
        : vol.imageControls || {},
      volumeRendering: "on",
      volumeRenderingGain: (full && fr.gain) || vol.volumeRenderingGain || 3,
      volumeRenderingDepthSamples: full ? fr.depthSamples || 4096 : 512,
      name: vol.label,
    };
    if (full) {
      // Extended options of the webXR fork (NG_CLIENT_FULL)
      img.sortedCompositing = true;
      img.progressiveLod = true;
      img.emptySkipThreshold = 0.118;
      img.volumeRenderingShading = FULL_SHADING;
    }
    const ls = [img];
    if (vol.segmentation) {
      ls.push({
        type: "segmentation",
        source: vol.segmentation.url,
        tab: "rendering",
        notSelectedAlpha: 0.12,
        meshSilhouetteRendering: 0.7,
        segments: vol.segmentation.segments || [],
        segmentColors: vol.segmentation.segmentColors || {},
        name: vol.segmentation.name || "annotation labels",
        visible: false,
      });
    }
    return ls;
  }

  // mode:
  //   "full"  = full volume render with AO shading, opened in NG_CLIENT_FULL
  //             (the cephalopod.team-style look);
  //   "3d"    = stock volume rendering in the bundled client;
  //   "slice" = 4-panel view with freely rotatable cross-section planes.
  // In any view, hold Shift+drag (or use the rotation widgets) to re-orient
  // the slicing planes in any direction.
  function state(vol, mode) {
    const u = vol.voxelUnit || [0.001, "m"];
    const full = mode === "full";
    const s = {
      title: vol.label,
      dimensions: { x: u, y: u, z: u },
      layers: layers(vol, mode),
      layout: mode === "slice" ? "4panel" : "3d",
      showAxisLines: false,
      showDefaultAnnotations: false,
      crossSectionBackgroundColor: "#000000",
      projectionBackgroundColor: "#000000",
      gpuMemoryLimit: full ? 9000000000 : 2000000000,
      systemMemoryLimit: full ? 8000000000 : 2000000000,
      selectedLayer: { layer: vol.label, visible: false },
    };
    if (mode !== "slice") s.showSlices = false;
    if (full) {
      // Extended viewer options of the webXR fork
      s.hideCrossSectionBackground3D = true;
      s.depthWheelSensitivity = 0.01;
      s.absoluteProjectionDepth = true;
      s.adaptiveTargets = true;
    }
    return s;
  }

  function url(vol, mode) {
    const base = mode === "full"
      ? BIOATLAS_CONFIG.NG_CLIENT_FULL
      : BIOATLAS_CONFIG.NG_CLIENT;
    const client = base.replace(/\/$/, "") + "/";
    return client + "#!" + encodeURIComponent(JSON.stringify(state(vol, mode)));
  }

  function byId(id) {
    return BIOATLAS_VOLUMES.find(v => v.id === id);
  }

  return { state, url, byId, IMAGE_SHADER };
})();
