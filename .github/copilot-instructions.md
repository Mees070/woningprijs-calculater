# GitHub Copilot Instructions

Project: Woningprijs-calculator (Streamlit app + pricing logic).

## Context
- UI is in Dutch; keep labels and help texts in Dutch.
- Core logic lives in `src/house_price/` and should stay UI-agnostic.
- Keep calculations deterministic and explainable.

## Style
- Prefer clear, small functions with type hints where helpful.
- Use standard library first; add dependencies only if needed.
- Keep data validation near the boundary (UI or CLI).

## Testing
- If you add non-trivial logic, add a unit test (use `tests/` if created).
- Aim for readable tests over full coverage.

## Do/Don't
- Do not hardcode secrets or API keys.
- Do not rewrite UI copy to English unless requested.
- Do not change model assumptions without documenting them in README.
