# Examples

This directory contains sample input/output pairs showing what `png2svg` can
produce. All outputs are generated with the same input image (`scene.png`,
a 200×200 procedural scene) and four different presets.

## Input

- **`scene.png`** — A simple 200×200 procedural scene with sky, a sun, a
  mountain, and a tree. Useful for comparing presets without the visual
  complexity of real photographs.

## Outputs

| File | Preset | Use case | File size |
|------|--------|----------|-----------|
| `scene_fast.svg` | `fast` | Quick preview, low fidelity. 4 colors, wide hatch, no optimization. | ~15KB |
| `scene_portrait.svg` | `portrait` | Soft gradients, fine detail, arc smoothing. | ~24KB |
| `scene_logo.svg` | `logo` | Flat colors with separate outline paths for crisp edges. | ~24KB |
| `scene_sketch.svg` | `sketch` | Hand-drawn feel with larger arc U-turns. | ~24KB |

## Reproducing

```bash
# Fast preview
png2svg examples/scene.png /tmp/out.svg --preset fast --max-palette 4 --line-step 6

# Portrait (faces, soft gradients)
png2svg examples/scene.png /tmp/out.svg --preset portrait --max-palette 6 \
    --line-step 3 --continuous-paths --arc-radius 3

# Logo (bold flat colors, crisp edges)
png2svg examples/scene.png /tmp/out.svg --preset logo --max-palette 5 \
    --line-step 5 --separate-outline

# Sketch (hand-drawn aesthetic)
png2svg examples/scene.png /tmp/out.svg --preset sketch --max-palette 5 \
    --line-step 4 --continuous-paths --arc-radius 4
```

## Opening the SVGs

The generated SVGs are valid vector files. Open them in:

- **Inkscape** — `inkscape examples/scene_logo.svg` (best for inspection)
- **A web browser** — `firefox examples/scene_portrait.svg` (quick preview)
- **Cricut Design Space** — Upload via "Upload" → "SVG" (production target)

The files use semantic Inkscape layer names (e.g. `dark_gray (RGB: 80,80,90)`)
so each color can be selected separately in Inkscape.
