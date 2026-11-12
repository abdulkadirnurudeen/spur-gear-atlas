"""Conditional climate break-even for a same-blank solid/perforated gear pair.

Geometry is in mm, machine time in min and steel density in kg/mm³.
Each milling leg is specified by its volume share and cutter settings. No
reference energy, carbon total or break-even distance is an input.
"""

import argparse
import json
import math
from pathlib import Path


KM_PER_MILE = 1.609344


def milling_terms(volume_mm3, legs, machine, coefficients):
    """Return cutting work, elapsed cutting time and noncut time."""
    exponent = coefficients["cutting_exponent_1_minus_m"] - 1
    if not math.isclose(math.fsum(leg["volume_fraction"] for leg in legs), 1.0, abs_tol=1e-12):
        raise ValueError("Milling volume fractions must sum to one")
    cut = []
    minutes = []
    for leg in legs:
        d = leg["diameter_mm"]
        ae = leg["radial_engagement_mm"]
        ap = leg["axial_depth_mm"]
        feed = leg["feed_mm_min"]
        if not (0 < ae <= d / 2 and ap > 0 and feed > 0 and leg["volume_fraction"] > 0):
            raise ValueError("Milling pass outside the positive machining domain")
        arc = math.acos(1 - 2 * ae / d)
        chip = 2 * ae / d / arc * feed / (leg["flutes"] * leg["rpm"])
        material = leg["volume_fraction"] * volume_mm3
        cut.append(material * coefficients["kc_1_1_N_per_mm2"] * chip**exponent / 3.6e9)
        minutes.append(max(material / (ap * ae * feed), leg.get("contour_floor_min", 0.0)))
    idle = machine["allocated_noncut_minutes"] * machine["allocated_setup_count"]
    return math.fsum(cut), math.fsum(minutes), idle


def manufacturing(gear, process, coefficients):
    """Compute route energy, waste partition and carbon per removed kg."""
    z, module = gear["teeth"], gear["module_mm"]
    if type(z) is not int or z < 1:
        raise ValueError("Teeth must be a positive integer")
    pitch = z * module
    b = gear["face_mm"]
    area = gear["total_opening_area_mm2"]
    perimeter = gear["total_opening_perimeter_mm"]
    n = gear["opening_count"]
    if type(n) is not int or n < 1 or not all(math.isfinite(x) and x > 0 for x in (pitch, b, area, perimeter)):
        raise ValueError("Positive face width, pitch and through-opening dimensions are required")
    density = coefficients["density_kg_mm3"]
    capture = coefficients["added_steel_capture_fraction"]
    volume = b * area
    mass = volume * density
    # Dimensionless planform and path coefficients, evaluated from the given gear.
    xi = area / pitch**2
    ell = perimeter / pitch
    process_scale = process.get("electricity_correction", 1.0)
    if not math.isfinite(process_scale) or process_scale <= 0:
        raise ValueError("Process electricity correction must be positive")
    route = process["method"]
    water = None
    wire = None
    if route == "milling":
        machine = process["machine"]
        work, time, idle = milling_terms(volume, process["legs"], machine, coefficients)
        electricity = work / machine["incremental_drive_efficiency"] + machine["energized_base_kW"] * (time + idle) / 60
        pressed_mass = capture * mass
        transported_mass = pressed_mass
    elif route == "wire_edm":
        edm = coefficients["edm"]
        lead = n * process.get("lead_mm_per_opening", edm["lead_mm_per_opening_at_200"] * pitch / 200)
        ell += lead / pitch
        kerf_volume = process["kerf_mm"] * b * pitch * ell
        drill_volume = n * math.pi * (edm["start_hole_diameter_mm"] / 2)**2 * b
        if kerf_volume <= 0 or kerf_volume + drill_volume >= volume:
            raise ValueError("Wire EDM kerf/start-hole partition exceeds the opening")
        electricity = edm["electricity_kJ_per_mm3_kerf"] * kerf_volume / 3600
        time = kerf_volume / edm["material_removal_mm3_min"]
        idle = 0.0
        pressed_mass = capture * density * drill_volume
        transported_mass = capture * (mass - density * kerf_volume)
        water = edm["allocated_deionised_water_input_L_h"] * time / 60
        wire = edm["wire_feed_m_min"] * time
    else:
        raise ValueError(f"Unknown method {route!r}")
    press_rate = process["press_dry_feed_kg_h"]
    if not math.isfinite(press_rate) or press_rate <= 0:
        raise ValueError("Chip press feed rate must be positive")
    hole_electricity = process_scale * electricity
    site_electricity = hole_electricity + coefficients["press_power_kW"] * pressed_mass / press_rate
    climate = math.fsum((coefficients["grid_kg_CO2e_kWh"] * site_electricity,
                        coefficients["scrap_transport_kg_CO2e_kg"] * transported_mass))
    return {
        "method": route, "teeth": z, "pitch_mm": pitch, "xi": xi, "ell": ell,
        "mass_removed_kg": mass, "active_minutes": time, "allocated_noncut_minutes": idle,
        "hole_electricity_kWh": hole_electricity, "site_electricity_delta_kWh": site_electricity,
        "initial_climate_delta_kg_CO2e": climate, "initial_climate_per_removed_kg": climate / mass,
        "manufacturing_steel_dispatched_delta_kg": transported_mass,
        "documented_process_water_input_L": water, "estimated_wire_use_m": wire,
    }


def road_projection(made, road):
    """Compare the quantified climate terms at any distance and at the test horizon."""
    scale = road.get("fuel_saving_correction", 1.0)
    fuel_rate = road["FRV_L_per_100km_per_100kg"]
    co2_litre = road["combustion_kg_CO2e_L"] + road["supply_kg_CO2e_L"]
    if not all(math.isfinite(v) for v in (scale, fuel_rate, co2_litre)) or scale <= 0 or min(fuel_rate, co2_litre) < 0:
        raise ValueError("Road savings terms are outside their declared domain")
    mass = made["mass_removed_kg"]
    litres_km = mass * scale * fuel_rate / 10000
    saving_km = litres_km * co2_litre
    upfront = made["initial_climate_delta_kg_CO2e"]
    if upfront == 0:
        distance = 0.0
        status = "already_at_parity"
    elif saving_km == 0:
        distance = None
        status = "no_finite_crossing_under_zero_running_saving"
    else:
        distance = upfront / saving_km
        status = "test_mileage_undetermined"
    horizon = road.get("test_distance_km")
    if horizon is not None:
        if not math.isfinite(horizon) or horizon < 0:
            raise ValueError("Test distance must be nonnegative")
        if distance is not None and upfront != 0:
            if math.isclose(distance, horizon, rel_tol=0, abs_tol=1e-8):
                status = "at_test_horizon"
            elif distance < horizon:
                status = "before_test_horizon"
            else:
                status = "after_test_horizon_projection"
    return {
        "test_distance_km": horizon, "break_even_km": distance,
        "break_even_miles": distance / KM_PER_MILE if distance is not None else None,
        "break_even_position": status, "fuel_saved_L_per_km": litres_km,
        "climate_saved_kg_CO2e_per_km": saving_km,
        "fuel_saved_L_at_test_end": litres_km * horizon if horizon is not None else None,
        "climate_delta_kg_CO2e_during_test": upfront - saving_km * horizon if horizon is not None else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path, help="Gear, road scenario and one or more feasible processes")
    parser.add_argument("--coefficients", type=Path, default=Path(__file__).with_name("break_even_coefficients.json"))
    args = parser.parse_args()
    request = json.loads(args.input_json.read_text())
    coefficients = json.loads(args.coefficients.read_text())
    output = []
    for process in request["processes"]:
        made = manufacturing(request["gear"], process, coefficients)
        output.append(made | road_projection(made, request["road"]))
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
