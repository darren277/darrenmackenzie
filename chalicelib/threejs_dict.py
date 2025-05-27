""""""
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

ANIMATIONS_DICT = {
    'multiaxis':
        {
            'name': 'Multiaxis',
            'data_sources': ['data', 'experimental', 'experimental_1'],
            'custom_meta': dict(),
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
            """]
        },
    'adventure':
        {
            'name': 'Adventure',
            'data_sources': ['adventure1', 'adventure2'],
            'custom_overlays': [ADVENTURE_NAVIGATION_OVERLAY],
            'custom_meta': dict(),
        },
    'room':
        {
            'name': 'Room',
            'data_sources': [],
            'custom_meta': dict(),
        },
    'cayley':
        {
            'name': 'Cayley',
            'data_sources': ['cayley'],
            'custom_meta': dict(),
        },
    'force':
        {
            'name': 'Force',
            'data_sources': [],
            'custom_meta': dict(),
        },
    'geo':
        {
            'name': 'Geo',
            'data_sources': ['geo'],
            'custom_meta': dict(),
        },
    'geo3d':
        {
            'name': 'Geo3D',
            'data_sources': ['geo3d'],
            'custom_meta': dict(),
        },
    'quantum':
        {
            'name': 'Quantum',
            'data_sources': [],
            'custom_meta': dict(),
        },
    'svg':
        {
            'name': 'SVG',
            'data_sources': ['OpenProject', 'Knowledge'],
            'custom_meta': dict(),
        },
    'library':
        {
            'name': 'Library',
            'data_sources': ['library'],
            'custom_meta': dict(),
        },
    'plot':
        {
            'name': 'Plot',
            'data_sources': ['plot'],
            'custom_meta': dict(),
        },
    'rubiks':
        {
            'name': 'Rubiks',
            'data_sources': ['rubiks'],
            'custom_meta': dict(),
        },
    'chess':
        {
            'name': 'Chess',
            'data_sources': ['chess'],
            'custom_meta': dict(),
        },
}