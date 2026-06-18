# hatchsvg — Tutorial Notebooks

Three Jupyter notebooks that walk through hatchsvg at increasing levels of
depth. **All three are tested to execute end-to-end on the shipped `tests/fixtures/test_image.png` (a small synthetic 4-color image).**

## Start here

**New to hatchsvg?** Open `quickstart.ipynb` first. 5 cells, ~5 minutes.

**Want to understand what's actually happening?** Open `explore.ipynb`. 6 code
cells, 30-60 minutes. Has the 4-stage walkthrough with explanations and 2a/2b/2c
branches for the color-matching stage.

**Already comfortable and want the advanced stuff?** Open `craft.ipynb`.
5 code cells, 1-2 hours. Custom palettes, per-color remap, session save/load,
batch processing, parameter deep-dive, comparison with adjacent tools.

You don't have to read them in order, but they build on each other: quickstart
is the simplest, craft assumes you've read at least quickstart.

## File layout

```
notebooks/
├── README.md                 # this file
├── notebook_helpers.py       # shared module used by all 3 notebooks
├── quickstart.ipynb          # 5-minute path
├── explore.ipynb             # 4-stage walkthrough with explanations
├── craft.ipynb               # advanced: custom palettes, sessions, batch
├── quickstart_executed.ipynb # last successful execution output
├── explore_executed.ipynb
├── craft_executed.ipynb
└── batch_output/             # created by the batch-processing cell in craft
```

The `*_executed.ipynb` files are committed so reviewers can see what the
notebooks produce without running them. They are regenerated whenever someone
runs the verification script (see "Verifying notebooks" below).

## Running the notebooks

1. Install with the notebook extras:
   ```bash
   pip install -e ".[notebook]"
   ```
2. Start Jupyter:
   ```bash
   jupyter lab
   ```
3. Open any of the three notebooks in the `notebooks/` directory.
4. Run the cells in order.

The default sample image is `../tests/fixtures/test_image.png` (a synthetic 4-color image shipped with the repo).
Change `IMAGE_PATH` in the first cell of `quickstart.ipynb` to point at your
own image.

## Verifying notebooks (for maintainers)

The notebooks are tested in CI by executing them with `nbconvert` and
comparing cell counts and error status:

```bash
# Quick smoke test: just check the notebooks parse and the helper imports work
pytest tests/integration/test_notebook_helpers.py

# Full execution test: actually run all 3 notebooks end-to-end
bash scripts/verify_notebooks.sh
```

The smoke tests catch import errors, signature changes, and missing
palette JSONs. The full execution catches anything that runs but produces
the wrong output.

## Why notebooks instead of a GUI?

This is a deliberate choice. A GUI is a long-lived commitment — every
release you have to maintain UI, worry about backward compat, and the
user can't see what the program is doing. Notebooks are different:

- **No magic.** Every cell shows exactly what code runs. Click into
  `notebook_helpers.py` to see what the helper does.
- **Bypassable.** Don't like the helper? Call `hatchsvg.core` directly.
  Edit the helper. Edit the cell. Whatever.
- **Forkable.** If you want a custom stage, copy a cell, modify it,
  save the modified notebook. We won't break your changes.
- **Diffable.** When hatchsvg updates, you can `git diff` the
  `.ipynb` file and see exactly what changed in the explanations.

The trade-off: notebooks require the user to be comfortable with Python.
That's the same audience as the existing CLI — crafters who tinker.

If you want a GUI, see `GUI_ARCHITECTURE.md` at the repo root for a
documented design we decided not to ship.

## Re-generating the notebooks

The `.ipynb` files are generated from a Python source file at
`scripts/build_notebooks.py`. This is so:

- The notebooks are reviewable as Python (not JSON) in PRs
- The cell source is linted with the same tools as the rest of the codebase
- We can regenerate the notebooks byte-for-byte

To re-generate after editing the build script:

```bash
python scripts/build_notebooks.py --out-dir notebooks
```

## Adding a new notebook

1. Add a `build_<name>()` function to `scripts/build_notebooks.py` that returns
   an `nbformat.v4.new_notebook()` with the cells you want.
2. Add it to the `builders` dict in `main()`.
3. Add a section to this README.
4. Run `python scripts/build_notebooks.py --out-dir notebooks` to generate the
   `.ipynb` file.
5. Run `jupyter nbconvert --to notebook --execute` on the new notebook to
   generate the `*_executed.ipynb` for reviewers.
6. Add smoke tests to `tests/integration/test_notebook_helpers.py` if you
   add new helpers.

## License

Same as the parent project: MIT.
