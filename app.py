import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.house_price.config import MarketProfile
from src.house_price.estimator import PriceEstimator
from src.house_price.renovation import RenovationScenario
from src.house_price.utils import normalize_energy_label


st.set_page_config(page_title="Woningprijs-calculator", layout="centered")


def load_profile(path: Path) -> MarketProfile:
    if path.exists():
        return MarketProfile.load(path)
    return MarketProfile()


@st.cache_data(show_spinner=False)
def has_dataset(path: Path) -> bool:
    return path.exists()


def format_nl_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_compact_eur(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"€ {format_nl_number(value / 1_000_000, 2)}M"
    if abs_value >= 1_000:
        return f"€ {format_nl_number(value / 1_000, 0)}k"
    return f"€ {format_nl_number(value, 0)}"


def format_full_eur(value: float) -> str:
    return f"€ {format_nl_number(value, 0)}"


def format_delta_eur(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{format_compact_eur(abs(value))}"


def metric_value_with_band(value: float, spread: float) -> tuple[str, str]:
    metric_text = f"{format_compact_eur(value)} ± {format_compact_eur(spread)}"
    if len(metric_text) > 16:
        return format_compact_eur(value), f"± {format_compact_eur(spread)}"
    return metric_text, ""


def format_adjustment_impact(adjustment: float, base_value: float) -> str:
    sign = "+" if adjustment >= 0 else ""
    pct = format_nl_number(adjustment * 100, 1)
    euro = format_compact_eur(base_value * adjustment)
    return f"Effect nu: {sign}{pct}% (≈ {euro})"


def suggest_condition(
    current: str,
    budget: float,
    living_area: float,
    thresholds: list[float],
) -> str:
    if not current:
        return "Redelijk"
    if living_area <= 0:
        return current
    budget_per_m2 = budget / living_area if budget > 0 else 0.0
    steps = sum(1 for threshold in thresholds if budget_per_m2 >= threshold)
    order = ["Slecht", "Matig", "Redelijk", "Goed", "Uitstekend"]
    if current not in order:
        return current
    return order[min(len(order) - 1, order.index(current) + steps)]




st.title("Woningprijs-calculator")
st.caption(
    "Schat de woningwaarde en het renovatie-effect, inclusief marktgroei over tijd."
)
with st.expander("Hoe werkt deze calculator?"):
    st.markdown(
        "- **Stap 1 — Huidige woning**: vul de woningkenmerken in zoals ze nu zijn.\n"
        "- **Stap 2 — Renovatie & toekomst**: geef je renovatiebudget, gewenste energielabel en kijktermijn.\n"
        "- **Resultaat**: je ziet de waarde zonder renovatie en na renovatie, inclusief bandbreedte.\n"
        "- **Buurtprijs & extra vraag**: buurtprijs is het brede gemiddelde; extra vraag is het straat/segment‑effect.\n"
        "- **Tuinoppervlak**: <10 m² telt niet mee; effect verschilt voor appartement en woonhuis.\n"
        "- **Onderhoudsstaat**: beïnvloedt de waarde direct; renovatie kan de staat automatisch verbeteren."
    )
st.markdown(
    """
<style>
div[data-testid="stMetricValue"] {
  font-size: 1.45rem;
}
</style>
""",
    unsafe_allow_html=True,
)
with st.expander("Modelaannames en formule"):
    st.markdown(
        "- Basisprijs per m² is het uitgangsniveau van de markt; per stad als beschikbaar, anders algemeen.\n"
        "- Formule: prijs = woonoppervlak × basis_m2 × (1 + aanpassingen) × (1+g)^t.\n"
        "- Extra m² boven een drempel tellen minder mee (aflopende meerwaarde).\n"
        "- Aanpassingen zijn procentueel; renovatie-opslag is begrensd.\n"
        "- Onzekerheid neemt toe bij grotere aanpassingen."
    )
with st.expander("Begrippen"):
    st.markdown(
        "- **Basisprijs per m²**: uitgangsprijs per m²; per stad of algemeen niveau.\n"
        "- **Aanpassing**: procentuele correctie op basis van kenmerken.\n"
        "- **Jaarlijkse groei (g)**: verwachte marktgroei per jaar.\n"
        "- **Bandbreedte**: schatting plus/min een onzekerheidsmarge."
    )

profile_path = Path("configs/market_profile.json")
profile = load_profile(profile_path)
dataset_available = has_dataset(Path("data/raw_data.csv"))

if len(profile.city_base_price_m2) <= 1:
    st.warning(
        "Er is slechts één stad beschikbaar. Voer kalibratie uit om steden te laden: "
        "`python -m src.house_price.cli calibrate --data data/raw_data.csv "
        "--output configs/market_profile.json`"
    )

with st.sidebar:
    st.header("Marktinstellingen")
    st.caption("Houd dit eenvoudig. Geavanceerd is optioneel.")
    profile.annual_growth_rate = st.number_input(
        "Jaarlijkse groei",
        value=profile.annual_growth_rate,
        step=0.005,
        format="%.3f",
        help="Fractie per jaar, bijv. 0,035 = 3,5%.",
    )
    profile.base_price_m2 = st.number_input(
        "Basisprijs per m² (EUR)",
        value=profile.base_price_m2,
        step=50.0,
        format="%.0f",
        help="Euro per m² woonoppervlak (basisniveau).",
    )
    profile.neighborhood_price_weight = st.slider(
        "Weging buurtprijs",
        min_value=0.0,
        max_value=1.0,
        value=profile.neighborhood_price_weight,
        step=0.05,
        help="Hoeveel de buurtprijs meeweegt t.o.v. stadsbasis.",
    )
    with st.expander("Geavanceerde marktinstellingen"):
        profile.current_year = st.number_input(
            "Huidig jaar",
            value=profile.current_year,
            step=1,
            help="Jaar (YYYY) waarnaar je waarde wilt kijken.",
        )
        profile.reference_year = st.number_input(
            "Referentiejaar",
            value=profile.reference_year,
            step=1,
            help="Basisjaar (YYYY) van de prijsniveaus.",
        )
        profile.renovation_roi = st.slider(
            "Renovatie-ROI (waarde per EUR)",
            min_value=0.0,
            max_value=1.0,
            value=profile.renovation_roi,
            step=0.05,
            help="Waarde per €1 budget (ruwe inschatting).",
        )
        profile.renovation_roi_saturation = st.slider(
            "Verzadiging renovatie-ROI",
            min_value=0.02,
            max_value=0.2,
            value=profile.renovation_roi_saturation,
            step=0.01,
            help="Demping bij grote budgetten, als deel van woningwaarde.",
        )
        profile.renovation_cap = st.slider(
            "Max. renovatie-opslag",
            min_value=0.0,
            max_value=0.5,
            value=profile.renovation_cap,
            step=0.02,
            help="Maximale totale renovatie-uplift (fractie).",
        )
        profile.renovation_label_step_uplift = st.slider(
            "Opstap energielabel",
            min_value=0.0,
            max_value=0.05,
            value=profile.renovation_label_step_uplift,
            step=0.005,
            help="Opslag per labelstap (fractie).",
        )
        profile.renovation_label_cap = st.slider(
            "Max. opslag energielabel",
            min_value=0.0,
            max_value=0.2,
            value=profile.renovation_label_cap,
            step=0.01,
            help="Maximale opslag door labelverbetering (fractie).",
        )
        st.markdown("---")
        st.caption("Onzekerheid schatting:")
        profile.estimate_uncertainty_base = st.slider(
            "Basis-onzekerheid",
            min_value=0.02,
            max_value=0.2,
            value=profile.estimate_uncertainty_base,
            step=0.01,
            help="Basisbandbreedte, bijv. 0,08 = ±8%.",
        )
        profile.estimate_uncertainty_per_adjustment = st.slider(
            "Onzekerheid per aanpassing",
            min_value=0.0,
            max_value=1.0,
            value=profile.estimate_uncertainty_per_adjustment,
            step=0.05,
            help="Extra bandbreedte per totale aanpassing.",
        )

st.subheader("Huidige woning")
st.caption(
    "Beschrijf de woning zoals die nu is. Deze kenmerken blijven gelijk in het scenario."
)
energy_label_options = ["", "A4", "A3", "A2", "A1", "A", "B", "C", "D", "E", "F", "G"]
build_type_options = ["", "Bestaande bouw", "Nieuwbouw"]

house_type_display = {
    "Appartement": "Apartment",
    "Tussenwoning": "Terraced",
    "Hoekwoning": "Corner",
    "2-onder-1-kapwoning": "Semi-detached",
    "Vrijstaande woning": "Detached",
    "Herenhuis": "Townhouse",
    "Overig/onbekend": "Other",
}
position_display = {
    "Woonwijk": "Residential",
    "Rustig/beschut": "Quiet/Sheltered",
    "Centrum": "Center",
    "Aan water": "Water",
    "Aan park": "Park",
    "Bosrijk": "Forest",
    "Vrij uitzicht": "View/Open",
    "Drukke weg": "Busy road",
    "Overig/onbekend": "Other/Unknown",
}
condition_options = ["Slecht", "Matig", "Redelijk", "Goed", "Uitstekend"]
micro_location_options = [
    "Geen extra vraag",
    "Licht extra vraag",
    "Duidelijk extra vraag",
    "Zeer hoge extra vraag",
]
bathroom_options = ["0", "1", "2", "3+"]
toilet_count_options = ["1", "2", "3+"]
city_options = sorted(profile.city_base_price_m2.keys())
city_default = "Den Haag"
city_select_options = (city_options if city_options else []) + ["Other..."]
st.subheader("Locatie & basis")
col1, col2, col3 = st.columns(3)
with col1:
    living_area = st.number_input(
        "Woonoppervlak (m²)",
        min_value=20.0,
        max_value=600.0,
        value=108.0,
        step=1.0,
        format="%.0f",
        help="Bruikbaar woonoppervlak binnen (m²).",
    )
    rooms = st.number_input(
        "Kamers",
        min_value=1,
        max_value=15,
        value=5,
        step=1,
        help=(
            "Totaal aantal kamers (incl. woon-/slaapkamers). "
            "Meer kamers voegen waarde toe tot een logisch punt; te veel kamers voor "
            "het oppervlak verlaagt de waardering."
        ),
    )
    build_year = st.number_input(
        "Bouwjaar",
        min_value=1800,
        max_value=2035,
        value=1869,
        step=1,
        help="Bouwjaar; bepaalt ouderdomscorrectie.",
    )
with col2:
    city_choice = st.selectbox(
        "Stad",
        options=city_select_options,
        index=city_select_options.index(city_default)
        if city_default in city_select_options
        else 0,
        help="Stad voor basisprijs per m².",
    )
    if city_choice == "Other...":
        city = st.text_input("Andere stad", value=city_default)
        normalized_city = city.strip()
        if normalized_city not in profile.city_base_price_m2:
            st.info(
                "Deze stad staat nog niet in de lijst. De basisprijs per m² wordt nu "
                "het nationale basisniveau. Je kunt de stad toevoegen via de pagina "
                "‘Aannames’ onder ‘Stadprijzen’."
            )
    else:
        city = city_choice
    neighborhood_price_m2 = st.number_input(
        "Buurtprijs per m² (optioneel)",
        min_value=0.0,
        max_value=20000.0,
        value=5863.0,
        step=50.0,
        format="%.0f",
        help=(
            "Breed buurtgemiddelde; extra vraag corrigeer je apart. "
            "Gebruik geen ‘perfecte match’-prijs om dubbel tellen te voorkomen."
        ),
    )
with col3:
    micro_location = st.selectbox(
        "Extra vraag (straat/segment)",
        options=micro_location_options,
        index=micro_location_options.index("Zeer hoge extra vraag"),
        help=(
            "Alleen voor extra vraag die niet al door tuin/ligging/type/onderhoud wordt "
            "verklaard. Twijfel? Kies 0%."
        ),
    )
    hint_estimator = PriceEstimator(profile)
    base_price_m2_hint = hint_estimator.base_price_m2(
        {
            "city": city,
            "neighborhood_price_m2": neighborhood_price_m2,
            "micro_location": micro_location,
        }
    )
    base_value_hint = max(0.0, living_area) * base_price_m2_hint
    micro_adj = profile.micro_segment_base_uplift.get(micro_location, 0.0)
    st.caption(f"Huidige opslag: {format_nl_number(micro_adj*100, 1)}%")
    st.caption(format_adjustment_impact(micro_adj, base_value_hint))
    base_value_hint_effective = base_value_hint * (1.0 + micro_adj)
st.subheader("Woningkenmerken")
col4, col5 = st.columns(2)
with col4:
    energy_label = st.selectbox(
        "Energielabel",
        options=energy_label_options,
        index=energy_label_options.index("E"),
        help="A–G (of A+ varianten).",
    )
    energy_adj = profile.energy_label_adjustments.get(
        normalize_energy_label(energy_label), 0.0
    )
    st.caption(format_adjustment_impact(energy_adj, base_value_hint_effective))
    build_type = st.selectbox(
        "Bouwtype",
        options=build_type_options,
        index=build_type_options.index("Bestaande bouw"),
        help="Nieuwbouw of bestaande bouw.",
    )
    build_adj = profile.build_type_adjustments.get(build_type, 0.0)
    st.caption(format_adjustment_impact(build_adj, base_value_hint_effective))
with col5:
    house_type_label = st.selectbox(
        "Woningtype",
        options=list(house_type_display.keys()),
        index=list(house_type_display.keys()).index("Tussenwoning"),
        help="Woningtype (categorie).",
    )
    house_type = house_type_display[house_type_label]
    house_adj = profile.house_type_adjustments.get(house_type, 0.0)
    neutralize_house_types = profile.micro_location_house_type_neutralize.get(
        micro_location, []
    )
    if house_type in neutralize_house_types:
        house_adj = 0.0
    st.caption(format_adjustment_impact(house_adj, base_value_hint_effective))
    condition = st.selectbox(
        "Staat van onderhoud",
        options=condition_options,
        index=condition_options.index("Matig"),
        help=(
            "Kies op basis van de huidige staat van keuken, badkamer, installaties en "
            "afwerking. Slecht = duidelijke gebreken/achterstallig onderhoud; "
            "Matig = verouderd maar functioneel; Redelijk = oké maar gedateerd; "
            "Goed = netjes en up-to-date; Uitstekend = recent of hoogwaardig gerenoveerd."
        ),
    )
    condition_adj = profile.condition_adjustments.get(condition, 0.0)
    st.caption(format_adjustment_impact(condition_adj, base_value_hint_effective))
    garden_area = None
    bathrooms = None
    toilets = None

with st.expander("Aanvullende woningkenmerken (optioneel)"):
    st.caption("Deze kenmerken verfijnen de schatting als je ze weet.")
    lot_size = st.number_input(
        "Perceelgrootte (m²)",
        min_value=0.0,
        max_value=3000.0,
        value=108.0,
        step=10.0,
        format="%.0f",
        help="Totale perceelgrootte; laat 0 bij onbekend.",
    )
    garden_area = st.number_input(
        "Tuinoppervlak (m²)",
        min_value=0.0,
        max_value=1000.0,
        value=54.0,
        step=1.0,
        format="%.0f",
        help="Privé buitenruimte; <10 m² telt niet mee.",
    )
    garden_adj = hint_estimator.garden_adjustment(
        {"garden_area": garden_area, "house_type": house_type}
    )
    st.caption(format_adjustment_impact(garden_adj, base_value_hint_effective))
    bathrooms_label = st.selectbox(
        "Badkamers",
        options=bathroom_options,
        index=bathroom_options.index("2"),
        help="Aantal badkamers.",
    )
    bathrooms = bathrooms_label
    bathroom_adj = profile.bathroom_adjustments.get(bathrooms, 0.0)
    st.caption(format_adjustment_impact(bathroom_adj, base_value_hint_effective))
    toilets_label = st.selectbox(
        "Toiletten",
        options=toilet_count_options,
        index=toilet_count_options.index("2"),
        help="Aantal toiletten (incl. badkamer).",
    )
    toilets = toilets_label
    toilets_adj = profile.toilet_count_adjustments.get(toilets, 0.0)
    st.caption(format_adjustment_impact(toilets_adj, base_value_hint_effective))
    if dataset_available:
        position_label = st.selectbox(
            "Ligging",
            options=list(position_display.keys()),
            index=list(position_display.keys()).index("Rustig/beschut"),
            help="Hoofdsituatie van de ligging.",
        )
        position = position_display[position_label]
        position_adj = (
            0.0
            if micro_location in profile.micro_location_disable_position_adjustment
            else profile.position_adjustments.get(position, 0.0)
        )
        st.caption(format_adjustment_impact(position_adj, base_value_hint_effective))
    else:
        st.caption(
            "Ligging wordt zichtbaar na het inladen van een dataset via de kalibratie."
        )

st.subheader("Renovatie & toekomst")
st.caption("Dit is een scenario: wat je plant te doen en hoe ver vooruit je kijkt.")
st.info(
    "Renovatie-impact komt uit budget en energielabel-verbetering. "
    "Woningaanpassingen hieronder veranderen de kenmerken in het scenario."
)
col3, col4 = st.columns(2)
with col3:
    budget_input = st.number_input(
        "Renovatiebudget (EUR)",
        min_value=0.0,
        max_value=500000.0,
        value=72000.0,
        step=1000.0,
        format="%.0f",
        help="Totale kosten in euro's.",
    )
    energy_before = st.selectbox(
        "Energielabel vóór",
        options=energy_label_options,
        index=energy_label_options.index(energy_label) if energy_label in energy_label_options else 0,
        help="Huidig energielabel vóór renovatie.",
    )
with col4:
    energy_after = st.selectbox(
        "Energielabel ná",
        options=energy_label_options,
        index=energy_label_options.index("C"),
        help="Gewenst label ná renovatie (alleen effect als het verbetert).",
    )
    condition_after = None
    years_forward = st.number_input(
        "Kijktermijn (jaren)",
        min_value=0,
        max_value=30,
        value=0,
        step=1,
        help="Aantal jaren vooruit; geldt voor alle waarden.",
    )
    position = None

with st.expander("Renovatieplan (optioneel)"):
    st.caption(
        "Verdeel je budget om keuzes te verkennen. "
        "ROI-gewichten zijn vuistregels en zijn aanpasbaar in de configuratie."
    )
    col5, col6 = st.columns(2)
    with col5:
        kitchen_budget = st.number_input(
            "Keuken (lager rendement)",
            min_value=0.0,
            max_value=300000.0,
            value=0.0,
            step=1000.0,
            format="%.0f",
        )
        bathroom_budget = st.number_input(
            "Badkamer (lager rendement)",
            min_value=0.0,
            max_value=300000.0,
            value=0.0,
            step=1000.0,
            format="%.0f",
        )
        insulation_budget = st.number_input(
            "Isolatie (hoger rendement)",
            min_value=0.0,
            max_value=300000.0,
            value=0.0,
            step=1000.0,
            format="%.0f",
        )
    with col6:
        exterior_budget = st.number_input(
            "Buitenruimte/gevel (lager rendement)",
            min_value=0.0,
            max_value=300000.0,
            value=0.0,
            step=1000.0,
            format="%.0f",
        )
        other_budget = st.number_input(
            "Overig",
            min_value=0.0,
            max_value=300000.0,
            value=0.0,
            step=1000.0,
            format="%.0f",
        )
    allocation_total = (
        kitchen_budget
        + bathroom_budget
        + insulation_budget
        + exterior_budget
        + other_budget
    )
    weights = profile.renovation_category_weights
    weighted_total = (
        kitchen_budget * weights.get("kitchen", 1.0)
        + bathroom_budget * weights.get("bathroom", 1.0)
        + insulation_budget * weights.get("insulation", 1.0)
        + exterior_budget * weights.get("exterior", 1.0)
        + other_budget * weights.get("other", 1.0)
    )
    use_allocation = st.checkbox("Gebruik gewogen budget uit verdeling", value=False)
    st.metric("Totaal renovatieplan", f"€ {allocation_total:,.0f}")
    st.caption(
        f"Gewogen renovatiebudget (op basis van ROI-gewichten): € {weighted_total:,.0f}"
    )

renovation_budget = weighted_total if use_allocation else budget_input

with st.expander("Woningaanpassingen (optioneel)"):
    st.caption(
        "Geplande aanpassingen aan de woning. Dit beïnvloedt alleen het scenario, "
        "niet de huidige waarde."
    )
    adjust_living_area = st.checkbox("Ik vergroot het woonoppervlak", value=False)
    extra_living_area = 0.0
    if adjust_living_area:
        extra_living_area = st.number_input(
            "Extra woonoppervlak (m²)",
            min_value=0.0,
            max_value=400.0,
            value=20.0,
            step=1.0,
            format="%.0f",
        )
    adjust_rooms = st.checkbox("Ik voeg kamers toe", value=False)
    extra_rooms = 0
    if adjust_rooms:
        extra_rooms = st.number_input(
            "Extra kamers",
            min_value=0,
            max_value=10,
            value=1,
            step=1,
            help="Helpt alleen als het oppervlak dit ondersteunt.",
        )

features = {
    "living_area": living_area,
    "lot_size": lot_size or None,
    "rooms": rooms,
    "build_year": build_year,
    "city": city,
    "energy_label": energy_label,
    "build_type": build_type,
    "house_type": house_type,
    "condition": condition,
    "micro_location": micro_location,
    "garden_area": garden_area,
    "position": position,
    "bathrooms": bathrooms,
    "toilets": toilets,
    "neighborhood_price_m2": neighborhood_price_m2 or None,
}

estimator = PriceEstimator(profile)
condition_thresholds = [
    profile.condition_step1_budget_per_m2,
    profile.condition_step2_budget_per_m2,
    profile.condition_step3_budget_per_m2,
    profile.condition_step4_budget_per_m2,
]
condition_thresholds = sorted([value for value in condition_thresholds if value > 0])
suggested_condition = suggest_condition(
    condition,
    renovation_budget,
    living_area,
    condition_thresholds,
)
condition_after = suggested_condition
budget_per_m2 = renovation_budget / living_area if living_area > 0 else 0.0
thresholds_label = ", ".join(format_nl_number(value, 0) for value in condition_thresholds)
st.caption(
    f"Staat na renovatie (automatisch): {suggested_condition} "
    f"(budget: {format_full_eur(renovation_budget)} ≈ € {format_nl_number(budget_per_m2, 0)}/m²; "
    f"drempels: {thresholds_label} €/m²)."
)
effective_budget = renovation_budget if condition_after == condition else 0.0
scenario = RenovationScenario(
    budget=effective_budget,
    energy_label_before=energy_before,
    energy_label_after=energy_after,
)

current_result = estimator.estimate_with_renovation(features, scenario, years_forward=years_forward)
scenario_features = dict(features)
if adjust_living_area:
    scenario_features["living_area"] = scenario_features["living_area"] + extra_living_area
if adjust_rooms:
    scenario_features["rooms"] = scenario_features["rooms"] + extra_rooms
scenario_features["condition"] = condition_after
scenario_result = estimator.estimate_with_renovation(
    scenario_features, scenario, years_forward=years_forward
)

st.subheader("Resultaten")
years_label = "nu" if years_forward == 0 else f"over {years_forward} jaar"
st.caption(
    f"Alle waarden zijn inclusief marktgroei {years_label}. "
    "Voor een waarde van vandaag zet je de kijktermijn op 0."
)
current_value = current_result["estimate"]
renovated_value = scenario_result["renovation"]["renovated_value"]
renovation_delta = renovated_value - current_value
current_uncertainty_pct = current_result["estimate_range"]["uncertainty_pct"]
renovated_uncertainty_pct = scenario_result["renovation"]["renovated_range"]["uncertainty_pct"]
current_spread = current_value * current_uncertainty_pct
renovated_spread = renovated_value * renovated_uncertainty_pct
delta_pct = 0.0
if current_value > 0:
    delta_pct = renovation_delta / current_value
roi_value = None
if scenario_result["renovation"]["budget"] > 0:
    roi_value = renovation_delta / scenario_result["renovation"]["budget"]

col_results_1, col_results_2, col_results_3 = st.columns(3)
with col_results_1:
    current_metric, current_band = metric_value_with_band(current_value, current_spread)
    st.metric(
        f"Waarde zonder renovatie ({years_label})",
        current_metric,
    )
    if current_band:
        st.caption(current_band)
    st.caption(f"Onzekerheid: ±{format_nl_number(current_uncertainty_pct*100, 0)}%")
    st.caption(f"Volledig: {format_full_eur(current_value)}")
with col_results_2:
    renovated_metric, renovated_band = metric_value_with_band(
        renovated_value, renovated_spread
    )
    st.metric(
        f"Waarde na renovatie ({years_label})",
        renovated_metric,
    )
    if renovated_band:
        st.caption(renovated_band)
    st.caption(f"Onzekerheid: ±{format_nl_number(renovated_uncertainty_pct*100, 0)}%")
    st.caption(f"Volledig: {format_full_eur(renovated_value)}")
with col_results_3:
    arrow = "↑" if renovation_delta >= 0 else "↓"
    st.metric("Meerwaarde", f"{arrow} {format_compact_eur(renovation_delta)}")
    st.caption(f"Verschil t.o.v. zonder renovatie: {format_nl_number(delta_pct*100, 1)}%")
    if roi_value is not None:
        st.caption(f"Rendement: € {format_nl_number(roi_value, 2)} per €1 budget.")

with st.expander("Detailoverzicht"):
    st.code(
        json.dumps(
            {
                "current": current_result,
                "scenario": scenario_result,
            },
            indent=2,
        ),
        language="json",
    )
