# Product extraction evals

Each `*.json` case lists photos (relative paths), seller notes and expectations. **The photos shipped here are
synthetic placeholders** that test the harness only; replace them with consented, real seller photos (with the
seller's permission) to measure model quality. Run: `uv run python -m app.cli run-evals product_extraction`.

Gates (any failure scores the case 0): output matches schema; no unsupported commercial claims.
