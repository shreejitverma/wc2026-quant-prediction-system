# Notebooks

## `epl_prediction.ipynb`

A working, fully-executed miniature of the WC2026 pipeline on a real public dataset:
EPL 2022-23 → 2024-25 (1,140 matches, `data/epl_matches.csv`, bundled from
football-data.co.uk so the notebook needs no network).

Cleaning contract → chronological (PIT-style) split → Poisson attack/defence GLM →
de-vigged Bet365 baseline → validation-chosen blend → log loss / Brier / RPS with
bootstrap CIs and a Diebold-Mariano test → calibration reliability with Wilson CIs →
edge-threshold betting simulation → per-match predictions with scoreline matrices.

Run interactively:

```bash
uv run --with matplotlib --with jupyter jupyter lab notebooks/epl_prediction.ipynb
```

Re-execute headless (what CI would do):

```bash
cd notebooks && uv run --with matplotlib --with nbclient --with nbformat --with ipykernel \
  python -c "import nbformat; from nbclient import NotebookClient; \
  nb = nbformat.read('epl_prediction.ipynb', as_version=4); \
  NotebookClient(nb, timeout=300).execute(); nbformat.write(nb, 'epl_prediction.ipynb')"
```

The committed copy is executed end-to-end (0 errors, 7 charts). The headline findings
are deliberately honest: the goals model alone does not beat the de-vigged closing
market, the validation blend collapses to the market, and betting the model's
disagreements loses more the more confident they are — the empirical version of the
terminal's "their-info" classification and the reason the real project's edge thesis
is coherence/settlement/timing, not out-modeling the closing line (ADR-0006).

`data/E0_*.csv` are the raw per-season downloads kept for provenance;
`data/epl_matches.csv` is the combined working file the notebook reads.
