"""Screen sector access and estimate a conditional two-face milling inventory."""

import json
import math

import numpy as np
from scipy.ndimage import distance_transform_edt, label

from process_inventory import quantified_process


def representative_opening(curves):
    """Verify that the five stored openings are rotated copies."""
    first = np.asarray(curves[0]).T
    origin_angle = np.angle(complex(*first.mean(axis=0)))
    for curve in curves[1:]:
        other = np.asarray(curve).T
        if other.shape != first.shape:
            raise ValueError("Sector opening samples differ")
        theta = np.angle(complex(*other.mean(axis=0))) - origin_angle
        cosine, sine = math.cos(theta), math.sin(theta)
        rotated = first @ np.array([[cosine, sine], [-sine, cosine]])
        shift = np.argmin(np.linalg.norm(rotated - other[0], axis=1))
        if np.max(np.linalg.norm(np.roll(rotated, -shift, axis=0) - other, axis=1)) > 1e-8:
            raise ValueError("Sector openings are not identical under rotation")
    return first


def sample_opening(points, step):
    """Build a centre-sampled interior mask from the original polygon."""
    following = np.roll(points, -1, axis=0)
    x, y = points.T
    next_x, next_y = following.T
    cols = np.arange(x.min() - 2*step, x.max() + 2*step, step)
    rows = np.arange(y.min() - 2*step, y.max() + 2*step, step)
    mask = np.zeros((len(rows), len(cols)), dtype=bool)
    for index, height in enumerate(rows):
        crossing = (y > height) != (next_y > height)
        intersections = x[crossing] + (height - y[crossing]) * (
            next_x[crossing] - x[crossing]) / (next_y[crossing] - y[crossing])
        mask[index] = np.searchsorted(np.sort(intersections), cols, side="right") % 2
    return mask, distance_transform_edt(mask, sampling=step), step


def swept_fraction(raster, radius, wall_allowance):
    """Estimate the swept area of a disk with a connected interior centre region."""
    mask, distance, step = raster
    centres = distance > radius + wall_allowance + step / 2
    if label(centres)[1] != 1:
        return 0.0
    swept = mask & (distance_transform_edt(~centres, sampling=step) <= radius)
    return np.count_nonzero(swept) / np.count_nonzero(mask)


def cutting_leg(phase1, inputs1, volume, side_depth, axial_limit, engagement, cutter):
    levels = math.ceil(side_depth / axial_limit)
    tool = {
        **inputs1["perforation_milling"],
        "tool_diameter_mm": cutter["diameter_mm"],
        "catalogue_table_feed_mm_per_min": cutter["feed_mm_min"],
    }
    fz = cutter["feed_mm_min"] / (4 * cutter["rpm"])
    return phase1.milling_leg(volume, side_depth / levels, engagement, tool, fz), levels


def plan_geometry(entry, profile, rasters, inputs, inputs1, phase1):
    settings = inputs["sector_rest_milling"]
    milling = inputs["milling"]
    row = entry["saved_atlas_geometry"]
    shape = entry["geometry_basis"]
    scale = row["scale"]
    side_depth = row["face_mm"] / 2
    reach = side_depth + settings["axial_reach_clearance_mm"]
    corner_radius = profile["sampled_minimum_convex_radius_mm"] * scale
    perimeter = profile["perimeter_mm"] * scale
    rough_grid, fine_grid = rasters
    volume = shape["volume_removed_mm3"]
    finish = None
    for cutter in sorted(settings["finish_tools"], key=lambda item: -item["diameter_mm"]):
        radius = cutter["diameter_mm"] / 2
        if radius + settings["radial_corner_clearance_mm"] >= corner_radius or cutter["neck_reach_mm"] < reach:
            continue
        access = swept_fraction(fine_grid, radius / scale, 0)
        if access >= settings["minimum_sampled_finish_sweep_fraction"]:
            finish = cutter
            break
    if finish is None:
        raise ValueError(f"No long-neck candidate clears the sector screen for {row['id']}")
    candidates = []
    for rough in milling["tools"]:
        diameter = rough["diameter_mm"]
        if rough["flute_length_mm"] < reach:
            continue
        radius = diameter / (2 * scale)
        allowance = diameter * milling["analyst_finish_allowance_fraction_of_diameter"]
        bulk = swept_fraction(fine_grid, radius, allowance / scale)
        if bulk < settings["minimum_bulk_swept_area_fraction"]:
            continue
        coarse_bulk = swept_fraction(rough_grid, radius, allowance / scale)
        if abs(coarse_bulk - bulk) > settings["maximum_rough_area_fraction_grid_difference"]:
            continue
        rough_leg, rough_levels = cutting_leg(
            phase1, inputs1, bulk * volume, side_depth,
            diameter * milling["analyst_axial_depth_limit_fraction_of_diameter"],
            diameter * milling["analyst_rough_radial_engagement_fraction_of_diameter"], rough)
        finish_leg, finish_levels = cutting_leg(
            phase1, inputs1, volume - rough_leg["volume_mm3"], side_depth,
            min(finish["catalogue_axial_limit_mm"], finish["flute_length_mm"]),
            finish["diameter_mm"] * settings["analyst_finishing_radial_engagement_fraction_of_diameter"], finish)
        finish_floor = 2 * finish_levels * perimeter / finish["feed_mm_min"]
        finishing_minutes = max(finish_floor, finish_leg["modelled_active_min"])
        candidates.append({
            "roughing_tool": rough,
            "finishing_tool": finish,
            "sampled_minimum_convex_corner_radius_mm": corner_radius,
            "minimum_required_reach_mm": reach,
            "finish_sampled_sweep_fraction": access,
            "rough_swept_area_fraction": bulk,
            "coarse_grid_rough_swept_area_fraction": coarse_bulk,
            "reference_grid_steps_mm": [rough_grid[2], fine_grid[2]],
            "machining_faces": 2,
            "rough_axial_levels_per_face": rough_levels,
            "finish_axial_levels_per_face": finish_levels,
            "rough_leg": rough_leg,
            "finish_leg": finish_leg,
            "minimum_contour_travel_time_min": finish_floor,
            "active_minutes": rough_leg["modelled_active_min"] + finishing_minutes,
            "net_cutting_work_kWh": rough_leg["net_cutting_work_kWh"] + finish_leg["net_cutting_work_kWh"],
        })
    if not candidates:
        raise ValueError(f"No bulk cutter passes the sector screen for {row['id']}")
    return min(candidates, key=lambda case: case["active_minutes"])


def sector_plans(db, catalog, profiles, inputs, inputs1, phase1):
    plans = {}
    for design_id, curves_json in db.execute("SELECT id,curves_json FROM designs WHERE family='sector' ORDER BY id"):
        polygon = representative_opening(json.loads(curves_json)["openings"])
        rasters = [sample_opening(polygon, step) for step in inputs["sector_rest_milling"]["grid_reference_steps_mm"]]
        for geometry_id, entry in catalog.items():
            if entry["saved_atlas_geometry"]["design_id"] == design_id:
                plans[geometry_id] = plan_geometry(entry, profiles[design_id], rasters, inputs, inputs1, phase1)
    return plans


def sector_milling_cases(plan, shape, stock, inputs1, inputs2, factors):
    cases = []
    machine_cases = inputs1["perforation_milling"]["machine_cases"]
    chip_settings = inputs2["chip_conditioning"]
    active = plan["active_minutes"]
    net = plan["net_cutting_work_kWh"]
    for machine in machine_cases:
        name = machine["id"]
        # Both a roughing setup and a finishing setup on each face.
        overhead = 4 * machine["allocated_noncut_minutes"]
        electricity = net / machine["incremental_drive_efficiency"] + machine["energized_base_kW"] * (active + overhead) / 60
        for press_rate in chip_settings["modelled_dry_steel_feed_rates_kg_h"]:
            process = quantified_process(stock, electricity, press_rate, shape["mass_removed_kg"], 0.0, 0.0,
                                         inputs2, factors)
            process.update({
                "process_id": f"sector_rest_mill_{name}_{press_rate:g}",
                "route": "two_face_sector_rest_milling",
                "case": name,
                "nominal": name == "nominal_assumption" and press_rate == chip_settings["nominal_dry_steel_feed_rate_kg_h"],
                "allocated_noncut_minutes": overhead,
                "sector_milling_plan": plan,
                "allocated_MQL_oil_mL_if_used": active * inputs2["lubrication"]["minimum_quantity_reference_rate_mL_h"] / 60,
                "documented_process_water_input_L": None,
            })
            cases.append(process)
    return cases
