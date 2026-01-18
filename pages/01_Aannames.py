import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.house_price.config import MarketProfile


CONFIG_PATH = Path("configs/market_profile.json")
DEFAULT_PATH = Path("configs/market_profile.default.json")


def load_profile(path: Path) -> MarketProfile:
    if path.exists():
        return MarketProfile.load(path)
    return MarketProfile()


def save_profile(profile: MarketProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile.save(path)


def ensure_default_profile() -> None:
    if not DEFAULT_PATH.exists() and CONFIG_PATH.exists():
        DEFAULT_PATH.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")


st.set_page_config(page_title="Aannames", layout="centered")

st.title("Aannames aanpassen")
st.caption("Pas de modelaannames aan en sla ze op voor de hele app.")

with st.expander("Hoe kies je goede aannames?"):
    st.markdown(
        "- **Wees conservatief**: kies liever iets lager dan te optimistisch.\n"
        "- **Werk in stappen**: verander één onderdeel, controleer het effect.\n"
        "- **Gebruik lokale data**: als je die hebt, is die betrouwbaarder dan algemene gemiddelden.\n"
        "- **Vermijd dubbel tellen**: extra vraag is los van tuin/ligging/type."
    )

ensure_default_profile()
profile = load_profile(CONFIG_PATH)

with st.form("assumptions_form"):
    st.subheader("Markt & locatie")
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
        help="Basisniveau per m² als er geen stads- of buurtprijs is.",
    )
    profile.neighborhood_price_weight = st.slider(
        "Weging buurtprijs",
        min_value=0.0,
        max_value=1.0,
        value=profile.neighborhood_price_weight,
        step=0.05,
        help="Hoeveel de buurtprijs meeweegt t.o.v. stadsbasis.",
    )
    profile.reference_year = st.number_input(
        "Referentiejaar",
        value=profile.reference_year,
        step=1,
        help="Basisjaar (YYYY) van de prijsniveaus.",
    )
    profile.current_year = st.number_input(
        "Huidig jaar",
        value=profile.current_year,
        step=1,
        help="Jaar (YYYY) waarnaar je waarde wilt kijken.",
    )

    st.subheader("Extra vraag (straat/segment)")
    st.caption("Effect bovenop buurtprijs en woningkenmerken.")
    updated_micro = {}
    for label, value in profile.micro_segment_base_uplift.items():
        updated_micro[label] = st.number_input(
            label,
            value=float(value),
            step=0.01,
            format="%.2f",
            help="Fractie, bijv. 0,04 = +4%.",
        )
    profile.micro_segment_base_uplift = updated_micro

    st.subheader("Onderhoudsstaat")
    st.caption("Effect van huidige staat van onderhoud.")
    updated_condition = {}
    for label, value in profile.condition_adjustments.items():
        updated_condition[label] = st.number_input(
            label,
            value=float(value),
            step=0.01,
            format="%.2f",
            help="Fractie, bijv. -0,05 = -5%.",
        )
    profile.condition_adjustments = updated_condition

    st.subheader("Tuin (appartement)")
    st.caption("Alleen van toepassing bij tuinoppervlak ≥ 10 m².")
    updated_garden_apartment = {}
    for label, value in profile.garden_adjustments_apartment.items():
        updated_garden_apartment[label] = st.number_input(
            label,
            value=float(value),
            step=0.01,
            format="%.2f",
            help="Fractie, bijv. 0,10 = +10%.",
        )
    profile.garden_adjustments_apartment = updated_garden_apartment

    st.subheader("Tuin (woonhuis)")
    st.caption("Conservatiever dan appartement; effect vaak kleiner.")
    updated_garden_house = {}
    for label, value in profile.garden_adjustments_house.items():
        updated_garden_house[label] = st.number_input(
            label,
            value=float(value),
            step=0.01,
            format="%.2f",
            help="Fractie, bijv. 0,02 = +2%.",
        )
    profile.garden_adjustments_house = updated_garden_house

    st.subheader("Kleine woningen (m²‑opslag)")
    st.caption("Kleine woningen krijgen vaak hogere €/m². Dit model doet dat via een opslag.")
    profile.small_home_reference_m2 = st.number_input(
        "Vanaf hoeveel m² geldt géén opslag meer?",
        value=float(profile.small_home_reference_m2),
        step=5.0,
        format="%.0f",
        help="Boven deze m² is de opslag 0%.",
    )
    profile.small_home_uplift_at_50m2 = st.number_input(
        "Opslag bij 50 m²",
        value=float(profile.small_home_uplift_at_50m2),
        step=0.01,
        format="%.2f",
        help="Bij 50 m²: 0,10 = +10%. Tussen 50 m² en de referentie loopt dit lineair af.",
    )
    profile.small_home_uplift_cap = st.number_input(
        "Maximale opslag",
        value=float(profile.small_home_uplift_cap),
        step=0.01,
        format="%.2f",
        help="Bovengrens van de opslag, ook als de formule hoger uitkomt.",
    )

    st.subheader("Kamers")
    st.caption("Meer kamers helpen tot een logisch punt; te veel kamers voor het oppervlak werkt negatief.")
    profile.room_area_m2 = st.number_input(
        "Hoeveel m² per kamer is ‘normaal’?",
        value=float(profile.room_area_m2),
        step=1.0,
        format="%.0f",
        help="Wordt gebruikt om het ‘verwachte’ aantal kamers te berekenen.",
    )
    profile.room_adjustment_per_room = st.number_input(
        "Effect per kamer afwijking",
        value=float(profile.room_adjustment_per_room),
        step=0.01,
        format="%.2f",
        help="0,02 = +2% per kamer boven verwachting; negatief bij minder kamers.",
    )
    profile.room_overcrowding_threshold = st.number_input(
        "Wanneer voelt het ‘opgehokt’?",
        value=float(profile.room_overcrowding_threshold),
        step=1.0,
        format="%.0f",
        help="Aantal kamers boven verwachting waarna de penalty start.",
    )
    profile.room_overcrowding_penalty_per_room = st.number_input(
        "Penalty per kamer boven die grens",
        value=float(profile.room_overcrowding_penalty_per_room),
        step=0.01,
        format="%.2f",
        help="0,03 = -3% per extra kamer boven de drempel.",
    )
    profile.room_adjustment_cap = st.number_input(
        "Maximale impact van kamers",
        value=float(profile.room_adjustment_cap),
        step=0.01,
        format="%.2f",
        help="Maximaal effect van kamers (positief of negatief).",
    )

    st.subheader("Renovatie‑effecten")
    profile.renovation_roi = st.number_input(
        "Renovatie‑ROI",
        value=float(profile.renovation_roi),
        step=0.05,
        format="%.2f",
    )
    profile.renovation_roi_saturation = st.number_input(
        "ROI‑verzadiging",
        value=float(profile.renovation_roi_saturation),
        step=0.01,
        format="%.2f",
    )
    profile.renovation_cap = st.number_input(
        "Max. renovatie‑uplift",
        value=float(profile.renovation_cap),
        step=0.02,
        format="%.2f",
    )
    profile.renovation_label_step_uplift = st.number_input(
        "Label‑uplift per stap",
        value=float(profile.renovation_label_step_uplift),
        step=0.005,
        format="%.3f",
    )
    profile.renovation_label_cap = st.number_input(
        "Max. label‑uplift",
        value=float(profile.renovation_label_cap),
        step=0.01,
        format="%.2f",
    )

    st.subheader("Staat‑stappen o.b.v. budget per m²")
    profile.condition_step1_budget_per_m2 = st.number_input(
        "Drempel stap 1 (€/m²)",
        value=float(profile.condition_step1_budget_per_m2),
        step=10.0,
        format="%.0f",
    )
    profile.condition_step2_budget_per_m2 = st.number_input(
        "Drempel stap 2 (€/m²)",
        value=float(profile.condition_step2_budget_per_m2),
        step=10.0,
        format="%.0f",
    )
    profile.condition_step3_budget_per_m2 = st.number_input(
        "Drempel stap 3 (€/m²)",
        value=float(profile.condition_step3_budget_per_m2),
        step=10.0,
        format="%.0f",
    )
    profile.condition_step4_budget_per_m2 = st.number_input(
        "Drempel stap 4 (€/m²)",
        value=float(profile.condition_step4_budget_per_m2),
        step=10.0,
        format="%.0f",
    )

    st.subheader("Onzekerheid")
    profile.estimate_uncertainty_base = st.number_input(
        "Basis‑onzekerheid",
        value=float(profile.estimate_uncertainty_base),
        step=0.01,
        format="%.2f",
    )
    profile.estimate_uncertainty_per_adjustment = st.number_input(
        "Onzekerheid per aanpassing",
        value=float(profile.estimate_uncertainty_per_adjustment),
        step=0.05,
        format="%.2f",
    )

    with st.expander("Stadprijzen (€/m²)"):
        st.caption("Pas basisprijzen per stad aan. Dit zijn €/m² op het referentiejaar.")
        city_df = pd.DataFrame(
            sorted(profile.city_base_price_m2.items(), key=lambda item: item[0]),
            columns=["Stad", "Prijs_per_m2"],
        )
        edited_city_df = st.data_editor(
            city_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Stad": st.column_config.TextColumn(required=True),
                "Prijs_per_m2": st.column_config.NumberColumn(format="%.0f", required=True),
            },
        )
        profile.city_base_price_m2 = {
            row["Stad"]: float(row["Prijs_per_m2"])
            for _, row in edited_city_df.iterrows()
            if str(row["Stad"]).strip()
        }

    with st.expander("Kenmerken‑correcties (percenten)"):
        st.caption("Deze waarden zijn fracties: 0,04 = +4%, -0,02 = -2%.")

        st.markdown("**Energielabel**")
        updated_energy = {}
        for label, value in profile.energy_label_adjustments.items():
            updated_energy[label] = st.number_input(
                f"{label}",
                value=float(value),
                step=0.005,
                format="%.3f",
            )
        profile.energy_label_adjustments = updated_energy

        st.markdown("**Bouwtype**")
        updated_build = {}
        for label, value in profile.build_type_adjustments.items():
            updated_build[label] = st.number_input(
                f"{label}",
                value=float(value),
                step=0.01,
                format="%.2f",
            )
        profile.build_type_adjustments = updated_build

        st.markdown("**Woningtype**")
        updated_house = {}
        for label, value in profile.house_type_adjustments.items():
            updated_house[label] = st.number_input(
                f"{label}",
                value=float(value),
                step=0.01,
                format="%.2f",
            )
        profile.house_type_adjustments = updated_house

        st.markdown("**Ligging**")
        updated_position = {}
        for label, value in profile.position_adjustments.items():
            updated_position[label] = st.number_input(
                f"{label}",
                value=float(value),
                step=0.01,
                format="%.2f",
            )
        profile.position_adjustments = updated_position

        st.markdown("**Badkamers**")
        updated_bath = {}
        for label, value in profile.bathroom_adjustments.items():
            updated_bath[label] = st.number_input(
                f"{label} badkamers",
                value=float(value),
                step=0.01,
                format="%.2f",
            )
        profile.bathroom_adjustments = updated_bath

        st.markdown("**Toiletten**")
        updated_toilet = {}
        for label, value in profile.toilet_count_adjustments.items():
            updated_toilet[label] = st.number_input(
                f"{label} toiletten",
                value=float(value),
                step=0.01,
                format="%.2f",
            )
        profile.toilet_count_adjustments = updated_toilet

    with st.expander("Perceel & oppervlak"):
        st.caption("Perceel werkt via ratio; extra m² krijgen afnemende meerwaarde.")
        profile.lot_size_ratio_median = st.number_input(
            "Median ratio perceel / woonoppervlak",
            value=float(profile.lot_size_ratio_median),
            step=0.05,
            format="%.2f",
        )
        profile.lot_size_ratio_weight = st.number_input(
            "Effect van ratio",
            value=float(profile.lot_size_ratio_weight),
            step=0.01,
            format="%.2f",
        )
        profile.lot_size_ratio_clamp = st.number_input(
            "Max. clamp op ratio‑effect",
            value=float(profile.lot_size_ratio_clamp),
            step=0.01,
            format="%.2f",
        )
        profile.area_full_price_m2 = st.number_input(
            "m² met volle waarde",
            value=float(profile.area_full_price_m2),
            step=5.0,
            format="%.0f",
        )
        profile.area_extra_weight = st.number_input(
            "Weging extra m²",
            value=float(profile.area_extra_weight),
            step=0.05,
            format="%.2f",
            help="0,70 = extra m² tellen voor 70%.",
        )

    with st.expander("Grenzen & caps"):
        profile.max_adjustment = st.number_input(
            "Maximale totale correctie",
            value=float(profile.max_adjustment),
            step=0.01,
            format="%.2f",
        )
        profile.min_adjustment = st.number_input(
            "Minimale totale correctie",
            value=float(profile.min_adjustment),
            step=0.01,
            format="%.2f",
        )

    with st.expander("Renovatie‑gewichten per categorie"):
        st.caption("Weging per budget‑post; 1,0 = gemiddeld.")
        updated_weights = {}
        for label, value in profile.renovation_category_weights.items():
            updated_weights[label] = st.number_input(
                label,
                value=float(value),
                step=0.1,
                format="%.1f",
            )
        profile.renovation_category_weights = updated_weights

    with st.expander("Micro‑segment regels"):
        st.caption("Hier kun je uitzonderingen per segment instellen.")
        micro_labels = list(profile.micro_segment_base_uplift.keys())
        profile.micro_location_disable_lot_size_adjustment = st.multiselect(
            "Uitschakelen perceel‑effect voor:",
            options=micro_labels,
            default=profile.micro_location_disable_lot_size_adjustment,
        )
        profile.micro_location_disable_position_adjustment = st.multiselect(
            "Uitschakelen ligging‑effect voor:",
            options=micro_labels,
            default=profile.micro_location_disable_position_adjustment,
        )
        updated_neutralize = {}
        for label in micro_labels:
            updated_neutralize[label] = st.multiselect(
                f"Neutraliseer woningtype voor: {label}",
                options=list(profile.house_type_adjustments.keys()),
                default=profile.micro_location_house_type_neutralize.get(label, []),
            )
        profile.micro_location_house_type_neutralize = updated_neutralize

    saved = st.form_submit_button("Opslaan")
    if saved:
        save_profile(profile, CONFIG_PATH)
        st.success("Aannames opgeslagen.")
        st.info(
            "Nieuwe steden verschijnen in de hoofdapp na herladen van de pagina "
            "(of herstart van de app)."
        )

    reset = st.form_submit_button("Reset naar defaults")
    if reset:
        if DEFAULT_PATH.exists():
            default_profile = load_profile(DEFAULT_PATH)
            save_profile(default_profile, CONFIG_PATH)
            st.success("Aannames teruggezet naar huidige defaults.")
        else:
            st.warning("Geen defaults gevonden. Sla eerst aannames op.")
