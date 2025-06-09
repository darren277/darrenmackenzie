""""""
from collections import defaultdict

from chalicelib.threejs_dict import ANIMATIONS_DICT


def populate_importmaps(animation: str, threejs_version: str):
    default_importmap = {
        "three": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/build/three.module.js",
        "textgeometry": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/geometries/TextGeometry.js",
        "fontloader": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/loaders/FontLoader.js",
        "orbitcontrols": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/controls/OrbitControls.js",
        "pointerlockcontrols": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/controls/PointerLockControls.js",
        "trackballcontrols": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/controls/TrackballControls.js",
        "svgloader": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/loaders/SVGLoader.js",
        "svgrenderer": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/renderers/SVGRenderer.js",
        "css2drenderer": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/renderers/CSS2DRenderer.js",
        "css3drenderer": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/renderers/CSS3DRenderer.js",
        "gltfloader": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/loaders/GLTFLoader.js",
        "pdbloader": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/loaders/PDBLoader.js",

        "tween": "https://unpkg.com/@tweenjs/tween.js@23.1.3/dist/tween.esm.js",

        "stats": "https://cdnjs.cloudflare.com/ajax/libs/stats.js/r17/Stats.min.js",
        "lil-gui": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/libs/lil-gui.module.min.js",

        'objloader': f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/loaders/OBJLoader.js",
        'plyloader': f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/loaders/PLYLoader.js",
        'exrloader': f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/loaders/EXRLoader.js",

        "d3-force-3d": "https://cdn.skypack.dev/d3-force-3d",
        "three-spritetext": "//unpkg.com/three-spritetext/dist/three-spritetext.mjs",
        "3d-force-graph": "https://cdn.jsdelivr.net/npm/3d-force-graph@1.77.0/+esm",
        "vrbutton": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/webxr/VRButton.js",

        "convex-object-breaker": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/misc/ConvexObjectBreaker.js",
        "convex-geometry": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/geometries/ConvexGeometry.js",

        "perlin-noise": "https://cdn.jsdelivr.net/npm/perlin-noise@0.0.1/+esm",
        "noisejs": "https://cdn.jsdelivr.net/npm/noisejs@2.1.0/+esm",

        "outline-effect": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/effects/OutlineEffect.js",

        "d3-hierarchy": "https://cdn.jsdelivr.net/npm/d3-hierarchy@3/+esm",

        "buffer-geometry-utils": f"https://cdn.jsdelivr.net/npm/three@{threejs_version}/examples/jsm/utils/BufferGeometryUtils.js",
    }

    # Force3d importmap:
    force3d_importmap = {
        "three": "https://esm.sh/three@0.175.0",
        "3d-force-graph": "https://esm.sh/3d-force-graph@1.77.0?bundle&deps=three@0.175.0",
        "three-spritetext": "https://esm.sh/three-spritetext@1.9.6?bundle&deps=three@0.175.0",
        "tween": "https://unpkg.com/@tweenjs/tween.js@23.1.3/dist/tween.esm.js",
        "outline-effect": "https://cdn.jsdelivr.net/npm/three@0.175.0/examples/jsm/effects/OutlineEffect.js",
    }

    return force3d_importmap if animation == 'force3d' else default_importmap


def grouped_nav_items(nav_item_ordering):
    grouped_nav_items = defaultdict(list)

    nav_items = [{'name': key, 'category': val['category']} for key, val in ANIMATIONS_DICT.items()]

    for item in nav_items:
        grouped_nav_items[item['category']].append(item)

    # Reorder grouped_nav_items using nav_item_ordering
    ordered_grouped_nav_items = {}
    for cat in nav_item_ordering:
        if cat in grouped_nav_items:
            ordered_grouped_nav_items[cat] = grouped_nav_items[cat]

    return ordered_grouped_nav_items

