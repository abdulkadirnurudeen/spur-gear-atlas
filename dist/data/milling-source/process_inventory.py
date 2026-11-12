"""Same-blank inventories for the two declared perforation routes."""

import json
import math


DELTA = "delta_perforated_minus_solid"


def pair(solid, perforated):
    return {"solid": solid, "perforated": perforated, DELTA: perforated - solid}


def opening_shapes(db):
    """Read the original contours and summarize their two-dimensional envelopes."""
    profiles = {}
    for design_id, curves_json in db.execute("SELECT id,curves_json FROM designs ORDER BY id"):
        curves = json.loads(curves_json)["openings"]
        perimeter = 0.0
        minimum_radius = math.inf
        convex = True
        for xs, ys in curves:
            xy = list(zip(xs, ys, strict=True))
            following = xy[1:] + xy[:1]
            edges = [(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(xy, following, strict=True)]
            lengths = [math.hypot(*edge) for edge in edges]
            perimeter += math.fsum(lengths)
            orientation = math.copysign(1.0, math.fsum(x0*y1 - y0*x1
                                         for (x0, y0), (x1, y1) in zip(xy, following, strict=True)))
            for index, (dx, dy) in enumerate(edges):
                ex, ey = edges[index - 1]
                product = lengths[index] * lengths[index - 1]
                cross = orientation * (ex * dy - ey * dx)
                if cross < -1e-9 * product:
                    convex = False
                if cross > 1e-9 * product:
                    radius = product * math.hypot(ex + dx, ey + dy) / (2 * cross)
                    minimum_radius = min(minimum_radius, radius)
        if not math.isfinite(minimum_radius) or perimeter <= 0:
            raise ValueError(f"Opening contour cannot be characterized for {design_id}")
        profiles[design_id] = {
            "perimeter_mm": perimeter,
            "sampled_minimum_convex_radius_mm": minimum_radius,
            "convex": convex,
            "span_xy_mm": [max(max(v) for v in axis) - min(min(v) for v in axis)
                           for axis in zip(*curves, strict=True)],
        }
    return profiles


def stock_basis(row, shape, settings, density):
    scale = row["scale"]
    diameter = settings["reference_diameter_mm"] * scale
    length = settings["reference_length_mm"] * scale
    if diameter < shape["outside_diameter_mm"] or length < row["face_mm"]:
        raise ValueError(f"Stock envelope does not contain {row['id']}")
    blank = math.pi * (diameter / 2)**2 * length * density * 1e-9
    return {
        "nominal_diameter_mm": diameter,
        "nominal_length_mm": length,
        "allocated_stock_kg": pair(blank, blank),
        "finished_gear_kg": pair(shape["solid_finished_mass_kg"], shape["perforated_finished_mass_kg"]),
        "gross_removed_kg": pair(blank - shape["solid_finished_mass_kg"], blank - shape["perforated_finished_mass_kg"]),
    }


def quantified_process(stock, perforation_kWh, press_rate, chips_added, cutouts, sludge, inputs2, factors):
    """Close the steel flows and characterize their quantified processing burden."""
    chips = inputs2["chip_conditioning"]
    common = stock["gross_removed_kg"]["solid"]
    required = stock["gross_removed_kg"][DELTA]
    if not math.isclose(math.fsum((chips_added, cutouts, sludge)), required, abs_tol=1e-9):
        raise ValueError("Chip, cutout and kerf streams do not close")
    common_captured = common * chips["common_removal_capture_fraction"]
    added_captured = chips_added * chips["nominal_hole_removal_capture_fraction"]
    clean_cutout_capture = cutouts * chips["nominal_hole_removal_capture_fraction"]
    pressed = pair(common_captured, common_captured + added_captured)
    transported = pair(common_captured, common_captured + added_captured + clean_cutout_capture)
    press = pair(*(pressed[leg] * chips["listed_power_kW"] / press_rate for leg in ("solid", "perforated")))
    site = pair(press["solid"], press["perforated"] + perforation_kWh)
    scrap_factor = factors["scrap_kg_CO2e_per_kg"]
    climate = {
        "plant_electricity_generation_and_losses": site[DELTA] * factors["grid_direct"],
        "plant_electricity_supply": site[DELTA] * factors["grid_upstream"],
        "transport_to_first_steel_processing": transported["perforated"] * scrap_factor -
                                               transported["solid"] * scrap_factor,
    }
    return {
        "added_hole_operation_electricity_kWh": perforation_kWh,
        "press_dry_feed_kg_h": press_rate,
        "pressed_dry_steel_kg": pressed,
        "press_electricity_kWh": press,
        "site_electricity_for_hole_operation_and_chip_press_kWh": site,
        "steel_dispatched_to_first_processing_kg": transported,
        "manufacturing_steel_outside_accounted_collection_kg": pair(
            common - transported["solid"], stock["gross_removed_kg"]["perforated"] - transported["perforated"]),
        "added_chip_mass_kg": chips_added,
        "loose_cutout_mass_kg": cutouts,
        "kerf_steel_in_sludge_kg": sludge,
        "initial_climate_contributions_kg_CO2e": climate,
        "initial_climate_delta_kg_CO2e": math.fsum(climate.values()),
    }


def milling_route(row, shape, profile, stock, inputs, inputs1, inputs2, factors, phase1):
    settings = inputs["milling"]
    face = row["face_mm"]
    scale = row["scale"]
    radius = (row["equivalent_opening_diameter_mm"] / 2 if row["family"] == "circle"
              else profile["sampled_minimum_convex_radius_mm"] * scale)
    if row["family"] == "sector" or not profile["convex"]:
        return []
    for cutter in settings["tools"]:
        diameter = cutter["diameter_mm"]
        allowance = diameter * settings["analyst_finish_allowance_fraction_of_diameter"]
        setups = 1 if face < cutter["flute_length_mm"] else 2
        side_depth = face / setups
        if diameter / 2 + allowance < radius and side_depth < cutter["flute_length_mm"]:
            break
    else:
        return []
    max_ap = diameter * settings["analyst_axial_depth_limit_fraction_of_diameter"]
    axial_levels = math.ceil(side_depth / max_ap)
    ap = side_depth / axial_levels
    ae = diameter * settings["analyst_rough_radial_engagement_fraction_of_diameter"]
    total_volume = shape["volume_removed_mm3"]
    holes = shape["hole_count"]
    profile_perimeter = profile["perimeter_mm"] * scale
    if row["family"] == "circle":
        opening_diameter = math.sqrt(4 * total_volume / (math.pi * face * holes))
        finish_volume = math.pi * (opening_diameter * allowance - allowance**2) * face * holes
    else:
        finish_volume = (profile_perimeter * allowance - holes * math.pi * allowance**2) * face
    tool = {
        **inputs1["perforation_milling"],
        "tool_diameter_mm": diameter,
        "catalogue_table_feed_mm_per_min": cutter["feed_mm_min"],
    }
    fz = cutter["feed_mm_min"] / (cutter["rpm"] * tool["tool_flutes"])
    rough = phase1.milling_leg(total_volume - finish_volume, ap, ae, tool, fz)
    finish = phase1.milling_leg(finish_volume, ap, allowance, tool, fz)
    active = rough["modelled_active_min"] + finish["modelled_active_min"]
    net = rough["net_cutting_work_kWh"] + finish["net_cutting_work_kWh"]
    cases = []
    for machine in tool["machine_cases"]:
        case_name = machine["id"]
        overhead = machine["allocated_noncut_minutes"] * setups
        electric = (net / machine["incremental_drive_efficiency"]
                    + machine["energized_base_kW"] * (active + overhead) / 60)
        for rate in inputs2["chip_conditioning"]["modelled_dry_steel_feed_rates_kg_h"]:
            case = quantified_process(stock, electric, rate, shape["mass_removed_kg"], 0.0, 0.0, inputs2, factors)
            case.update({
                "process_id": f"mill_{case_name}_{rate:g}",
                "route": "volume_equivalent_milling",
                "case": case_name,
                "nominal": case_name == "nominal_assumption" and
                           rate == inputs2["chip_conditioning"]["nominal_dry_steel_feed_rate_kg_h"],
                "cutter": cutter,
                "sampled_fit_radius_mm": radius,
                "machining_faces": setups,
                "axial_levels_per_face": axial_levels,
                "axial_depth_mm": ap,
                "rough_radial_engagement_mm": ae,
                "finish_allowance_mm": allowance,
                "rough_volume_mm3": rough["volume_mm3"],
                "finish_volume_mm3": finish["volume_mm3"],
                "active_minutes": active,
                "allocated_noncut_minutes": overhead,
                "net_cutting_work_kWh": net,
                "allocated_MQL_oil_mL_if_used": active * inputs2["lubrication"]["minimum_quantity_reference_rate_mL_h"] / 60,
                "whole_cutter_equivalents_at_declared_engaged_minutes": {
                    str(life): active / life
                    for life in inputs2["cutting_tool"]["unreconditioned_service_life_assumptions_active_min"]
                },
                "documented_process_water_input_L": None,
            })
            cases.append(case)
    return cases


def wire_edm_route(row, shape, profile, stock, inputs, inputs2, factors, density):
    settings = inputs["wire_edm"]
    envelope = settings["workspace_benchmark"]
    scale = row["scale"]
    face = row["face_mm"]
    width, depth = (span * scale for span in profile["span_xy_mm"])
    blank_diameter = stock["nominal_diameter_mm"]
    blank_length = stock["nominal_length_mm"]
    if (width >= envelope["travel_xyz_mm"][0] or depth >= envelope["travel_xyz_mm"][1]
            or face >= envelope["travel_xyz_mm"][2]
            or blank_diameter >= min(envelope["stock_xyz_max_mm"][:2])
            or blank_length >= envelope["stock_xyz_max_mm"][2]):
        raise ValueError(f"EDM benchmark envelope cannot cover {row['id']}")
    count = shape["hole_count"]
    lead = count * settings["lead_from_start_hole_to_profile_mm_at_reference_size"] * scale
    length = profile["perimeter_mm"] * scale + lead
    cut_area = length * face
    drill_mass = count * math.pi * (settings["start_hole_diameter_mm"] / 2)**2 * face * density * 1e-9
    rate = inputs2["chip_conditioning"]["nominal_dry_steel_feed_rate_kg_h"]
    cases = []
    for case_name, kerf in settings["kerf_cases_mm"].items():
        volume = cut_area * kerf
        sludge = volume * density * 1e-9
        cutout = shape["mass_removed_kg"] - sludge - drill_mass
        if cutout <= 0:
            raise ValueError(f"EDM waste partition cannot cover {row['id']}")
        minutes = volume / settings["material_removal_mm3_min"]
        electric = volume * settings["electricity_kJ_per_mm3_kerf"] / 3600
        case = quantified_process(stock, electric, rate, drill_mass, cutout, sludge, inputs2, factors)
        case.update({
            "process_id": f"wire_edm_{case_name}",
            "route": "wire_edm_P20_kerf_volume_benchmark",
            "case": case_name,
            "nominal": case_name == "nominal",
            "kerf_width_mm": kerf,
            "profile_cut_and_lead_length_mm": length,
            "cut_area_mm2": cut_area,
            "kerf_volume_mm3": volume,
            "active_minutes": minutes,
            "estimated_wire_use_m": minutes * settings["wire_feed_m_min"],
            "documented_process_water_input_L": minutes * settings["allocated_deionised_water_input_L_h"] / 60,
        })
        cases.append(case)
    return cases
