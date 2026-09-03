// bioatlas.io site configuration
const BIOATLAS_CONFIG = {
  // Where the migrated DZI tile pyramids are served from.
  // While tiles live inside this repo use "/tiles".
  // If you move them to a bucket/CDN (recommended — see README), put its base
  // URL here, e.g. "https://tiles.bioatlas.io" or an R2/S3 public URL.
  TILE_BASE: "/tiles",

  // true  = slide pills open the original PSU viewer (works on day 1,
  //         before any image data has been migrated).
  // false = slide pills open the local OpenSeadragon viewer at /viewer/,
  //         which loads DZI tiles from TILE_BASE. Flip this to false once
  //         scripts/download_slides.py has produced your tiles.
  USE_PSU_FALLBACK: true,

  PSU_BASE: "https://bio-atlas.psu.edu/zf/",

  // Neuroglancer clients used by the /3d/ page.
  //
  // NG_CLIENT — the stock Google Neuroglancer build bundled in this repo
  // (self-hosted). Used for the "3D (basic)" and "Slice view" buttons.
  // Fallback if you delete that folder: "https://neuroglancer-demo.appspot.com".
  NG_CLIENT: "/neuroglancer/",

  // NG_CLIENT_FULL — a client that supports the extended volume-rendering
  // options (volumeRenderingShading / ambient occlusion, sortedCompositing,
  // progressiveLod, emptySkipThreshold). These come from the Cheng Lab /
  // cephalopod.team "webXR" fork of Neuroglancer, which has no public repo,
  // so by default we open full renders in their hosted client. If you obtain
  // the fork's static build, put it in site/neuroglancer-xr/ and change this
  // to "/neuroglancer-xr/" — the generated links stay identical.
  NG_CLIENT_FULL:
    "https://cephalopod.team/histotomography/webXR/08062026_v1/client/",

  SITE_NAME: "BioAtlas",
};
