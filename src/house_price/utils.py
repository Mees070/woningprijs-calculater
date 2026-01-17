import re

import numpy as np


def coerce_number(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    digits = re.sub(r"[^\d.,]", "", text)
    if digits == "":
        return np.nan
    digits = digits.replace(".", "").replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return np.nan


def parse_rooms(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    text = str(value)
    match = re.search(r"(\d+)", text)
    return float(match.group(1)) if match else np.nan


def normalize_energy_label(label):
    if not label or (isinstance(label, float) and np.isnan(label)):
        return ""
    text = str(label).upper().strip()
    text = text.replace("++++", "4").replace("+++", "3").replace("++", "2").replace("+", "1")
    return text


def normalize_house_type(value: str) -> str:
    text = str(value).lower()
    if "appartement" in text:
        return "Apartment"
    if "hoekwoning" in text:
        return "Corner"
    if "tussenwoning" in text or "eindwoning" in text:
        return "Terraced"
    if "2-onder-1-kap" in text or "halfvrijstaande" in text or "geschakelde" in text:
        return "Semi-detached"
    if "vrijstaande" in text or "villa" in text or "landhuis" in text or "woonboerderij" in text or "bungalow" in text:
        return "Detached"
    if "herenhuis" in text:
        return "Townhouse"
    return "Other"


def normalize_garden(value: str) -> str:
    text = str(value).lower()
    has_back = "achtertuin" in text
    has_front = "voortuin" in text
    has_side = "zijtuin" in text
    has_around = "tuin rondom" in text
    has_terrace = "zonneterras" in text or "patio" in text or "atrium" in text

    flags = [has_back, has_front, has_side, has_around]
    if has_around:
        return "Around"
    if sum(flags) >= 2:
        return "Multiple"
    if has_back:
        return "Back"
    if has_front:
        return "Front"
    if has_side:
        return "Side"
    if has_terrace:
        return "Terrace/Patio"
    return "Other/Unknown"


def normalize_roof(value: str) -> str:
    text = str(value).lower()
    if "plat dak" in text:
        return "Flat"
    if "zadeldak" in text:
        return "Gable"
    if "schilddak" in text:
        return "Hip"
    if "mansarde" in text:
        return "Mansard"
    if "lessenaardak" in text:
        return "Shed"
    if "tentdak" in text:
        return "Tent"
    if "samengesteld" in text:
        return "Composite"
    if "riet" in text:
        return "Thatched"
    return "Other/Unknown"


def normalize_position(value: str) -> str:
    text = str(value).lower()
    if "drukke weg" in text:
        return "Busy road"
    if "in centrum" in text:
        return "Center"
    if "aan water" in text:
        return "Water"
    if "bosrijke" in text:
        return "Forest"
    if "aan park" in text:
        return "Park"
    if "vrij uitzicht" in text or "open ligging" in text:
        return "View/Open"
    if "beschutte ligging" in text or "aan rustige weg" in text:
        return "Quiet/Sheltered"
    if "in woonwijk" in text:
        return "Residential"
    return "Other/Unknown"


def normalize_toilet(value: str) -> str:
    text = str(value).lower()
    bath = 0
    toilet = 0
    for part in text.split("en"):
        if "badkamer" in part:
            bath = max(bath, int("".join([c for c in part if c.isdigit()]) or 0))
        if "toilet" in part:
            toilet = max(toilet, int("".join([c for c in part if c.isdigit()]) or 0))
    bath_label = "2+ bath" if bath >= 2 else "1 bath"
    toilet_label = "2+ toilet" if toilet >= 2 else ("1 toilet" if toilet == 1 else "0 toilet")
    return f"{bath_label}, {toilet_label}"


def normalize_floors(value: str) -> str:
    text = str(value).lower()
    digits = [int(s) for s in re.findall(r"\\d+", text)]
    if not digits:
        return "Unknown"
    floors = digits[0]
    if floors >= 4:
        return "4+"
    return str(floors)
