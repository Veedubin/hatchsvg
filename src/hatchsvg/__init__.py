"""hatchsvg — Convert images to hatched SVG files for Cricut pen plotters.

A pure-Python hatch generator for pen plotters. Reads raster images
(PNG, JPG, WebP, BMP, GIF, TIFF), quantizes them to a small palette,
maps each color to the nearest real-world marker (Crayola, Jot, or
custom JSON palette), and traces each color layer into parallel
hatched SVG paths. Output is optimized for Cricut Design Space,
Axidraw, EggBot, and any pen plotter that reads SVG.

Originally released as ``png2svg`` (v1.0.0 - v1.2.0). Renamed to
``hatchsvg`` in v2.0.0 to match the GitHub repository name and to
better describe the algorithm (hatching, not tracing).
"""

__version__ = "2.1.1"
