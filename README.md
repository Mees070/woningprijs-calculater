# Woningprijs-calculator

Eenvoudige Streamlit-app om woningwaarde te schatten en renovatie + markttrend
door te rekenen. De logica is transparant en instelbaar via
`configs/market_profile.json`.

## Kenmerken

- Prijsinschatting op basis van woningkenmerken, stad en buurtprijs
- Renovatie-effect met ROI en energielabelverbetering
- Markttrends via jaarlijkse groei en referentiejaar
- Kalibratie op basis van je eigen dataset
- Micro‑locatie en onderhoudsstaat als expliciete correcties
- Afnemende meerwaarde van extra m²

## Snel starten (lokaal)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Kalibreren met je dataset

Gebruik je dataset om basis €/m² per stad en categorie-aanpassingen te vullen:

```bash
python -m src.house_price.cli calibrate \
  --data data/raw_data.csv \
  --output configs/market_profile.json
```

## Markttrends aanpassen

Bewerk `configs/market_profile.json`:

- `annual_growth_rate`
- `current_year` en `reference_year`
- `base_price_m2` of `city_base_price_m2`
- renovatie: `renovation_roi`, `renovation_cap`, `renovation_label_step_uplift`
- `build_year_buckets` voor leeftijdsaanpassingen

## Deployen op Streamlit Community Cloud

De app moet in een GitHub-repository staan. Kort stappenplan:

1. Maak een repository op GitHub.
2. Zet je lokale code in Git:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

3. Ga naar <https://share.streamlit.io> en koppel de repo.
4. Kies `app.py` als entrypoint.
5. Streamlit Cloud gebruikt automatisch `requirements.txt` en `runtime.txt`.

## Projectstructuur

- `app.py` — Streamlit UI
- `src/house_price/` — domeinlogica (config, estimator, renovatie)
- `configs/market_profile.json` — marktprofiel
- `data/` — voorbeelddata voor kalibratie

## Copilot-instructies

Voor consistente suggesties staat er een korte richtlijn in
`.github/copilot-instructions.md`.

## Begrippen

- **Basisprijs per m²**: uitgangsprijs per m² voor de gekozen stad.
- **Aanpassing**: procentuele correctie op basis van kenmerken.
- **Jaarlijkse groei**: verwachte marktgroei per jaar (bijv. 0,035 = 3,5%).
- **Bandbreedte**: geschatte waarde ± onzekerheidsmarge.

## Gebruikstips (kort)

- **Buurtprijs per m²**: gebruik een breed buurtgemiddelde; geen “perfecte match”-prijs.
- **Extra vraag (straat/segment)**: alleen voor het effect dat niet al in tuin/ligging/type zit.
- **Tuinoppervlak**: <10 m² telt niet mee; effect verschilt voor appartement vs woonhuis.
- **Onderhoudsstaat**: kies de huidige staat; renovatie kan de staat automatisch verbeteren.
- **Renovatiebudget**: als de staat verbetert, telt budget niet dubbel mee.
