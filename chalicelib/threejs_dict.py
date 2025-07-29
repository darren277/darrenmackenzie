""""""

WALKING_CONTROLS_TOGGLE = """
<!-- Walking Controls Toggle Button -->
<button id="walking-toggle-btn" style="display: block; width: 120px; margin-bottom: 0.5em; cursor: pointer;">Walking: OFF</button>
"""

ADVENTURE_NAVIGATION_OVERLAY = """
<!-- Adventure Navigation Overlay -->
<!--        <div id="overlayText" style="position: absolute; top: 20px; left: 20px; max-width: 300px; padding: 10px; background: rgba(0,0,0,0.7); color: white; font-family: sans-serif;">-->
<div id="overlayText" style="position: absolute; top: 20px; left: 20px; max-width: 300px; padding: 10px; background: rgba(0,0,0,0.7); color: white; font-family: sans-serif;">
    <!-- The dynamic text goes here -->
    <p id="overlayTextContent">Adventure Navigation</p>
    <p>To go Left, hit the Left Arrow.</p>
    <p>To go Right, hit the Right Arrow.</p>
    <p>To go Up, hit the Up Arrow.</p>
    <p>To go Down, hit the Down Arrow.</p>
</div>
"""

LIBRARY_CUSTOM_CSS = """
    #resourceOverlay {
        position: fixed;
        bottom:  20px;
        right:   20px;
        max-width: 300px;
        max-height: 60vh;
        overflow: auto;
        padding: 16px;
        border-radius: 8px;
        background: #222;
        color: #fff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        display: none;                /* hidden by default */
    }

    #resourceOverlay h2 { margin-top: 0; font-size: 1.1rem; }

    #resourceOverlay .close {
        float: right; cursor: pointer; font-weight: bold; margin-left: 8px;
    }

    .label {
        background: rgba(255,0,0,0.7);   /* bright red for debugging */
        padding: 2px 4px;
        border-radius: 3px;
        color: #fff;
        font-size: 12px;
        white-space: nowrap;             /* prevent wrap‑around */
        pointer-events: none;
    }
"""

LIBRARY_RESOURCE_OVERLAYS = """
<div id="resourceOverlay">
    <span class="close" onclick="() => {document.getElementById('resourceOverlay').style.display = 'none';}">✕</span>
    <h2 id="overlayTitle"></h2>
    <p id="overlayAuthorYear"></p>
    <div id="overlayBody"></div>
</div>
"""

CSS3D_PREIODIC_TABLE_CSS = """
a {
    color: #8ff;
}

#menu {
    position: absolute;
    bottom: 20px;
    width: 100%;
    text-align: center;
}

.element {
    width: 120px;
    height: 160px;
    box-shadow: 0px 0px 12px rgba(0,255,255,0.5);
    border: 1px solid rgba(127,255,255,0.25);
    font-family: Helvetica, sans-serif;
    text-align: center;
    line-height: normal;
    cursor: default;
}

.element:hover {
    box-shadow: 0px 0px 12px rgba(0,255,255,0.75);
    border: 1px solid rgba(127,255,255,0.75);
}

    .element .number {
        position: absolute;
        top: 20px;
        right: 20px;
        font-size: 12px;
        color: rgba(127,255,255,0.75);
    }

    .element .symbol {
        position: absolute;
        top: 40px;
        left: 0px;
        right: 0px;
        font-size: 60px;
        font-weight: bold;
        color: rgba(255,255,255,0.75);
        text-shadow: 0 0 10px rgba(0,255,255,0.95);
    }

    .element .details {
        position: absolute;
        bottom: 15px;
        left: 0px;
        right: 0px;
        font-size: 12px;
        color: rgba(127,255,255,0.75);
    }

button {
    color: rgba(127,255,255,0.75);
    background: transparent;
    outline: 1px solid rgba(127,255,255,0.75);
    border: 0px;
    padding: 5px 10px;
    cursor: pointer;
}

button:hover {
    background-color: rgba(0,255,255,0.5);
}

button:active {
    color: #000000;
    background-color: rgba(0,255,255,0.75);
}
"""

EMBEDDED_CSS = """
.threejs-container {
    position: relative;
    width: 100%;
    height: 600px;
    background: #000;
    z-index: 9999;
}
"""

FULLSCREEN_CSS = """
html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden; /* prevents scroll bars if scene is bigger than window */
}

/* 2) This container #c is our Three.js “stage” */
#c {
    position: absolute; /* let it fill the entire window */
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: block;
}

/* 3) If needed, override the default canvas background or styling: */
#c canvas {
    display: block; /* remove any default inline-block spacing */
    background-color: #000; /* or transparent if you prefer */
}

/* 4) If you have an overlay UI, it must be position: absolute as well */
#ui-container {
    position: absolute;
    top: 1em;
    right: 1em;
    z-index: 9999;
    background-color: rgba(255, 255, 255, 0.2);
    padding: 0.5em;
}

.threejs-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: #000;
    z-index: 9999;
}

/* The CSS selector for element name (`<section>`) and class (`.threejs`) is: */
main.threejs {
    position: fixed; /* let it fill the entire window */
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: block;
}

.threejs-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: #000;
    z-index: 9999;
}

#c {
    position: absolute; /* let it fill the entire window */
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: block;
    background-color: #000; /* or transparent if you prefer */
    /* remove any default inline-block spacing */
    display: block;
}
"""

SMALL_HEADER_CSS = """
/* 1) Make the page and body fill the browser window */
html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
}

/* 2) Use flex layout on the body to have a fixed-height header + flexible main */
body {
    display: flex;
    flex-direction: column;
}

/* 3) A small header bar at the top */
header {
    height: 60px;           /* fixed height */
    background: #333;
    color: #fff;
    display: flex;
    align-items: center;
    padding-left: 1em;
    box-sizing: border-box; /* so padding doesn’t add extra height */
}

/* 4) The main area takes the remaining space */
main {
    flex: 1;               /* fill leftover vertical space */
    display: flex;         /* so that #c can fill it if needed */
    flex-direction: column;
    position: relative;    /* if you want absolutely positioned overlays inside */
}

/* 5) The Three.js container */
#c {
    flex: 1;              /* fill the rest of main */
    position: relative;
    width: 100%;          /* not strictly necessary, but often used for clarity */
    /* no hard-coded height; let flex fill the space */
}

/* 6) If you're directly putting <canvas> in #c: */
#c canvas {
    width: 100%;
    height: 100%;
    display: block;       /* remove default inline canvas spacing */
    background-color: black;
}


header {
    height: 60px;
    background: #333;
    color: #fff;
    display: flex;
    align-items: center;
    padding: 0 1em;
    box-sizing: border-box;
}
"""

# TODO: This is likely redundant when we have `THREEJS_DRAWINGS` in the JS library.
ANIMATIONS_DICT = {
    'multiaxis':
        {
            'name': 'Multiaxis',
            'data_sources': ['data', 'experimental', 'experimental_1'],
            'custom_meta': dict(),
            'category': 'Quantitative'
        },
    'music':
        {
            'name': 'Music',
            'data_sources': ['music'],
            'custom_meta': dict(music=True),
            'custom_overlays': ["""
<!-- Tempo Slider -->
<label for="tempo-slider">Tempo:</label>
<input id="tempo-slider" type="range" min="0.25" max="2.0" value="1" step="0.01"/>
<span id="tempo-value">1.00x</span>
            """],
            'category': 'Work in Progress'
        },
    'adventure':
        {
            'name': 'Adventure',
            'data_sources': ['adventure1', 'adventure2', 'forest'],
            'custom_meta': dict(),
            'category': 'Special'
        },
    'room':
        {
            'name': 'Room',
            'data_sources': [],
            'custom_meta': dict(),
            'category': 'Component'
        },
    'cayley':
        {
            'name': 'Cayley',
            'data_sources': ['cayley'],
            'custom_meta': dict(),
            'category': 'Quantitative'
        },
    'force':
        {
            'name': 'Force',
            'data_sources': [],
            'custom_meta': dict(),
            'category': 'Quantitative'
        },
    'geo':
        {
            'name': 'Geo',
            'data_sources': ['geo'],
            'custom_meta': dict(),
            'category': 'Spatial'
        },
    'geo3d':
        {
            'name': 'Geo3D',
            'data_sources': ['geo3d'],
            'custom_meta': dict(),
            'category': 'Spatial'
        },
    'quantum':
        {
            'name': 'Quantum',
            'data_sources': [],
            'custom_meta': dict(),
            # 'category': 'Educational'
            'category': 'Work in Progress',
        },
    'svg':
        {
            'name': 'SVG',
            'data_sources': ['OpenProject'],
            'custom_meta': dict(),
            'category': 'Component'
        },
    'multisvg':
        {
            'name': 'MultiSVG',
            'data_sources': ['OpenProject', 'Knowledge'],
            'custom_meta': dict(),
            'category': 'Work in Progress'
        },
    'library':
        {
            'name': 'Library',
            'data_sources': ['library'],
            'custom_meta': dict(),
            'custom_css': LIBRARY_CUSTOM_CSS,
            # 'custom_overlays': [LIBRARY_RESOURCE_OVERLAYS],
            'custom_js': """""",
            'category': 'Component'
        },
    'plot':
        {
            'name': 'Plot',
            'data_sources': ['plot'],
            'custom_meta': dict(),
            'category': 'Quantitative'
        },
    'rubiks':
        {
            'name': 'Rubiks',
            'data_sources': ['rubiks'],
            'custom_meta': dict(),
            'category': 'Work in Progress'
        },
    'chess':
        {
            'name': 'Chess',
            'data_sources': ['chess'],
            'custom_meta': dict(),
            'category': 'Work in Progress'
        },
    'clustering':
        {
            'name': 'Clustering',
            'data_sources': ['clustering'],
            'custom_meta': dict(),
            'category': 'Quantitative',
        },
    'orbits':
        {
            'name': 'Orbits',
            'data_sources': [],
            'custom_meta': dict(),
            'category': 'Educational',
        },
    'force3d':
        {
            'name': 'Force3D',
            'data_sources': ['force3d', 'philpapers', 'math'],
            'custom_meta': dict(),
            'category': 'Quantitative'
        },
    'cards':
        {
            'name': 'Cards',
            'data_sources': ['cards', 'thinkpak'],
            'custom_meta': dict(),
            'category': 'Special'
        },
    'gltf':
        {
            'name': 'GLTF',
            'data_sources': ['humanoid', 'dynamic_fighters'],
            'custom_meta': dict(),
            'category': 'Experimental'
        },
    'synapse':
        {
            'name': 'Synapse',
            'data_sources': [],
            'custom_meta': dict(),
            # 'category': 'Educational',
            'category': 'Work in Progress',
        },
    'brain':
        {
            'name': 'Brain',
            'data_sources': ['brain'],
            'custom_meta': dict(),
            'custom_css': """
.brain-label {
    font-family: sans-serif;
    color: white;
    padding: 2px 6px;
    background: rgba(0, 0, 0, 0.6);
    border-radius: 4px;
    font-size: 12px;
    pointer-events: none;
}
            """,
            'category': 'Educational',
        },
    'chemistry':
        {
            'name': 'Chemistry',
            'data_sources': ['chemistry'],
            'custom_meta': dict(),
            'category': 'Educational',
        },
    'game':
        {
            'name': 'Game',
            'data_sources': ['game'],
            'custom_meta': dict(),
            'category': 'Work in Progress',
        },
    'ammo':
        {
            'name': 'Ammo',
            'data_sources': ['ammo'],
            'custom_meta': dict(),
            'category': 'Attribution'
        },
    'periodic':
        {
            'name': 'Periodic',
            'data_sources': ['periodic'],
            'custom_meta': dict(),
            'custom_css': CSS3D_PREIODIC_TABLE_CSS,
            'custom_overlays': ["""
                <div id="menu">
                    <button id="table">TABLE</button>
                    <button id="sphere">SPHERE</button>
                    <button id="helix">HELIX</button>
                    <button id="grid">GRID</button>
                    <button id="cube">CUBE</button>
                </div>
            """],
            'category': 'Attribution'
        },
    'drive':
        {
            'name': 'Drive',
            'data_sources': ['drive'],
            'custom_meta': dict(),
            'category': 'Work in Progress'
        },
    # Currently not working??
    # 'tv':
    #     {
    #         'name': 'TV',
    #         'data_sources': ['tv_sony_trinitron'],
    #         'custom_meta': dict(),
    #     },
    'monitor':
        {
            'name': 'Monitor',
            'data_sources': ['monitor'],
            'custom_meta': dict(),
            # 'category': 'Attribution'
            'category': 'Work in Progress'
        },
    'farm':
        {
            'name': 'Farm',
            'data_sources': ['farm'],
            'custom_meta': dict(),
            'category': 'World Building'
        },
    'exr':
        {
            'name': 'EXR',
            'data_sources': ['golden_gate_hills_1k', 'OTHER_abandoned_workshop_02_4k'],
            'custom_meta': dict(),
            'category': 'Attribution',
        },
    'skibidi':
        {
            'name': 'Skibidi',
            'data_sources': ['skibidi'],
            'custom_meta': dict(),
            'category': 'Experimental'
        },
    'physics':
        {
            'name': 'Physics',
            'data_sources': ['physics'],
            'custom_meta': dict(),
            # 'category': 'Educational',
            'category': 'Work in Progress',
        },
    # TODO: Find a copyright free song or audio sample...
    # 'audioviz':
    #     {
    #         'name': 'AudioViz',
    #         'data_sources': ['audioviz'],
    #         'custom_meta': dict(),
    #     },
    'network':
        {
            'name': 'Network',
            'data_sources': ['network'],
            'custom_meta': dict(),
            'category': 'Work in Progress'
        },
    # Very early WIP:
    # 'smoke':
    #     {
    #         'name': 'Smoke',
    #         'data_sources': ['smoke'],
    #         'custom_meta': dict(),
    #     },
    'buildings':
        {
            'name': 'Buildings',
            'data_sources': ['buildings'],
            'custom_meta': dict(),
            'category': 'Spatial'
        },
    'town':
        {
            'name': 'Town',
            'data_sources': ['town'],
            'custom_meta': dict(),
            'category': 'World Building'
        },
    'complex':
        {
            'name': 'Complex',
            'data_sources': ['complex'],
            'custom_meta': dict(),
            'custom_css': LIBRARY_CUSTOM_CSS,
            'custom_overlays': [LIBRARY_RESOURCE_OVERLAYS],
            'custom_js': """""",
            'category': 'Special'
        },
    # VERY EARLY WIP...
    # 'city':
    #     {
    #         'name': 'City',
    #         'data_sources': ['city'],
    #         'custom_meta': dict(),
    #         #'wip': True,
    #         #'attribution': 'TBD'
    #     },
    'familytree':
        {
            'name': 'FamilyTree',
            'data_sources': ['familytree'],
            'custom_meta': dict(),
            # 'category': 'Special'
            'category': 'Work in Progress'
        },
}