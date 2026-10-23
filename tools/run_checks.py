"""Named offline checks with retained per-command logs and a machine-readable manifest."""

import argparse
import hashlib
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from itertools import groupby
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from diagnostics import git_identity

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (
    3,
    12,
)  # CI's version; the runner and every check invoke python3 from PATH.
DEFAULT_JOBS = min(4, os.cpu_count() or 1)
# The default run covers the car models and the showcase that displays them. Every other check
# exists for game tooling or corpus re-derivation; fast tooling runs with --games,
# and bulk/private-input re-derivation requires --full or an explicit --only.
SHOWCASE = {
    "ruff",
    "test_viewer_scenes",
    "test_under_car_shadow",
    "test_viewer_materials",
    "test_model_load",
    "test_diagnostics",
    "test_inspection_state",
    "test_mc3_record_inspection",
    "test_mc3_record_ui",
    "test_verify_mc3_inspection_browser",
    "test_verify_inspection_browser",
    "test_diagnostics_store",
    "test_viewer_loading",
    "test_dealership",
    "test_editable_glb",
    "test_enhanced_presentation",
    "test_gt4_refinement",
    "test_gt4_materials",
    "test_native_catalog_ui",
    "test_factory_colours",
    "test_mc3_preview_ui",
    "test_mcla_preview_ui",
    "test_recovered_game_shading",
    "verify_recovered_asset_index",
    "verify_under_car_shadow",
    "test_export_materials",
    "test_bake_models",
    "test_model_png",
    "test_model_catalog",
    "test_build_showcase",
    "test_build_dealership",
    "test_build_game_shading_assignments",
    "game_shading_assignments_freshness",
    "dealership_freshness",
    "test_library_filter",
    "test_serve_library",
    "dealership_roundtrip",
    "redline_roundtrip",
    "mc3_roundtrip",
    "test_run_checks",
    "test_review_payload",
    "test_audit_stranded_worktrees",
    "test_check_advice",
    "test_mc3_tire_alpha",
    "test_mc3_tire_vu",
    "test_mc3_vehicle_vu",
    "test_mc3_vehicle_math_reference",
    "test_mc3_vehicle_lighting",
    "test_mc3_vehicle_texture",
    "test_mc3_vehicle_material",
    "test_mc3_vehicle_inputs",
    "test_mc3_vehicle_animation",
    "test_mc3_vehicle_bindings",
    "test_mc3_vehicle_deformation",
    "test_mc3_vehicle_fragment",
    "test_mc3_vehicle_raster",
    "test_mc3_vehicle_programs",
    "test_mc3_vehicle_gif",
    "test_mc3_vehicle_state",
    "test_mc3_vif_reference",
    "test_mc3_vehicle_sampler",
    "test_mc3_vehicle_sprite",
    "test_mc3_vehicle_paint",
    "test_mc3_panorama_angle",
    "test_mc3_vehicle_nearest",
    "test_mc3_vehicle_vram",
    "test_mc3_vehicle_depth32",
    "test_mc3_vehicle_uniforms",
    "test_mc3_vehicle_skeleton",
    "test_mc3_ee_cop2",
    "test_mc3_ee_mr32",
    "test_mc3_ee_full_add",
    "test_mc3_ee_mmi",
    "test_mc3_vehicle_dispatch",
    "test_mc3_vehicle_mip",
    "test_mc3_vehicle_paint_factory",
    "test_mc3_vehicle_mip_transport",
    "test_mc3_ee_mac",
    "test_mc3_ee_division",
    "test_mc3_vehicle_authored_draw",
    "test_mc3_vehicle_high_z",
    "test_mc3_vehicle_variable_mip",
    "test_mc3_vehicle_initialization",
    "test_mc3_vehicle_target",
    "test_mc3_vehicle_high_z_transport",
    "test_mc3_vehicle_depth_trace",
    "test_mc3_vehicle_variable_mip_transport",
    "test_mc3_texture_binding",
    "test_mc3_vehicle_transfer_reference",
    "test_mc3_tire_material",
    "test_mc3_vehicle_math",
    "test_mc3_vehicle_resources",
    "test_mc3_vu_interpreter",
    "test_mc3_vehicle_bindings_js",
    "test_mc3_vehicle_deformation_js",
    "test_mc3_vehicle_fragment_js",
    "test_mc3_vehicle_raster_js",
    "test_mc3_vehicle_programs_js",
    "test_mc3_vehicle_gif_js",
    "test_mc3_vehicle_state_js",
    "test_mc3_vif_decoder",
    "test_mc3_vehicle_pipeline",
    "test_mc3_vehicle_sampler_js",
    "test_mc3_vehicle_sprite_js",
    "test_mc3_ee",
    "test_mc3_ee_division_js",
    "test_mc3_vehicle_transfer_reference_js",
    "test_mc3_vehicle_nearest_js",
    "test_mc3_vehicle_vram_js",
    "test_mc3_vehicle_depth32_js",
    "test_mc3_vehicle_vram_pipeline",
    "test_mc3_vehicle_mip_js",
    "test_mc3_vehicle_paint_factory_js",
    "test_mc3_vehicle_mip_pipeline",
    "test_mc3_vehicle_paint_factory_pipeline",
    "test_mc3_vehicle_high_z_js",
    "test_mc3_vehicle_variable_mip_js",
    "test_mc3_vehicle_initialization_js",
    "test_mc3_vehicle_target_js",
    "test_mc3_vehicle_high_z_pipeline",
    "test_mc3_vehicle_depth_trace_js",
    "test_mc3_vehicle_variable_mip_pipeline",
    "test_mc3_specular_native",
    "test_mc3_environment_gs",
    "test_mc3_specular",
    "test_mc3_environment",
    "test_mc3_gs_raster",
    "test_mc3_environment_sky",
    "test_mc3_environment_native",
    "test_mc3_environment_pack",
    "test_mc3_environment_raster",
    "test_mc3_reference_runtime",
    "test_verify_mc3_raster_reference",
    "test_mc3_garage",
    "test_game_paint",
    "test_build_game_paints",
    "game_paints_freshness",
}

# Keep whole-corpus and captured/private-input checks out of routine tooling runs.
FULL_ONLY = {
    "gt_models",
    "gt_extraction",
    "mc3_tire_alpha_native",
    "mc3_raster_reference_native",
    "gt4_refinement_corpus",
    "gt4_materials_corpus",
    "gt4_catalog",
    "gt4_extraction",
    "mcla_extraction",
    "mcla_resources",
    "mcla_decoding",
    "mcla_names",
    "mcla_catalog",
    "line_coverage",
    "verify_config_data_sound",
    "verify_sound_bank_index",
    "verify_vu_dispatch_map",
    "test_vu_dispatch_map",
    "test_vu1_decode",
    "verify_vu_pass_handlers",
    "test_vu_pass_handlers",
    "verify_vu_handler_dump",
    "test_vu_handler_dump",
    "recover_dump_reference_frame",
    "test_recover_dump_reference_frame",
    "verify_pass_source_join",
    "test_pass_source_join",
}

GAMES = {
    "gran-turismo": (
        "test_gt_",
        "test_import_gt_",
        "test_refine_gt_",
        "test_build_gt_counterparts",
        "gt_",
    ),
    "gran-turismo-4": (
        "test_gt4_",
        "test_extract_gt4_",
        "test_import_gt4_",
        "gt4_",
        "test_build_gt_counterparts",
        "gt_counterparts",
    ),
    "redline": (
        "test_redline_",
        "test_extract_redline_",
        "test_export_redline_",
        "test_import_redline_",
    ),
    "midnight-club-3-remix": (
        "test_mc3_",
        "test_extract_mc3_",
        "test_import_mc3_",
        "test_export_mc3_",
        "mc3_",
    ),
    "midnight-club-los-angeles": (
        "test_mcla_",
        "test_extract_mcla_",
        "test_import_mcla_",
        "test_verify_mcla_",
        "mcla_",
        "test_aes_decrypt",
        "test_xdvdfs",
        "test_xex2",
        "line_coverage",
        "test_line_coverage",
    ),
    "ford-racing-2": (
        "test_static_inputs",
        "test_recovery_inputs",
        "verify_",
        "test_vu",
        "recover_dump_reference_frame",
        "test_recover_dump_reference_frame",
        "test_pass_source_join",
    ),
}

# Audited read-only checks or tests whose mutations are confined to private temporary
# directories. Opt in by exact name after auditing transitive calls, not by test_* prefix.
# All other checks are barriers: drain running checks, run alone, then resume. This protects
# shared receipts and readers as well as whole-corpus work, Blender and existing process pools.
# GT4 catalog tests derive only two fixture cars, below its 16-car pool threshold; MCLA
# catalog tests use the default single worker. Re-audit these when their fixtures change.
PARALLEL_SAFE = {
    "ruff",
    "test_viewer_scenes",
    "test_under_car_shadow",
    "test_viewer_materials",
    "test_model_load",
    "test_viewer_loading",
    "test_dealership",
    "test_editable_glb",
    "test_enhanced_presentation",
    "test_gt4_refinement",
    "test_gt4_materials",
    "test_native_catalog_ui",
    "test_factory_colours",
    "test_mc3_preview_ui",
    "test_mcla_preview_ui",
    "test_recovered_game_shading",
    "test_build_game_shading_assignments",
    "test_export_materials",
    "test_build_showcase",
    "test_bake_models",
    "test_model_catalog",
    "test_model_png",
    "test_review_payload",
    "test_audit_stranded_worktrees",
    "test_check_advice",
    "test_static_inputs",
    "test_recovery_inputs",
    "test_gt_archive",
    "test_gt_asset_judgments",
    "test_gt_callback_triage",
    "test_gt_wheels",
    "test_gt_model",
    "test_import_gt_dealership",
    "test_library_filter",
    "test_serve_library",
    "test_redline_archive",
    "test_extract_redline_cars",
    "test_mc3_archive",
    "test_extract_mc3_cars",
    "test_import_mc3_catalogs",
    "test_mc3_pck",
    "test_mc3_wheels",
    "test_mc3_materials",
    "test_mc3_textures",
    "test_mc3_model",
    "test_export_mc3_models",
    "test_mc3_preview",
    "test_import_mc3_previews",
    "test_mc3_preview_experiments",
    "test_redline_mesh",
    "test_redline_texture",
    "test_redline_model",
    "test_export_redline_models",
    "test_import_redline_dealership",
    "test_gt4_volume",
    "test_extract_gt4_cars",
    "test_gt4_model",
    "test_gt4_specdb",
    "test_gt4_glb",
    "test_import_gt4_catalog",
    "test_import_gt4_dealership",
    "test_aes_decrypt",
    "test_xdvdfs",
    "test_xex2",
    "test_mcla_rpf",
    "test_extract_mcla_cars",
    "test_mcla_lzx",
    "test_mcla_resource",
    "test_mcla_model",
    "test_mcla_texture",
    "test_mcla_tuning",
    "test_mcla_names",
    "test_mcla_preview",
    "test_mcla_preview_geometry",
    "test_import_mcla_catalog",
    "test_import_mcla_dealership",
    "test_mcla_preview_experiments",
    "test_line_coverage",
    "test_mc3_tire_alpha",
    "test_mc3_tire_vu",
    "test_mc3_vehicle_vu",
    "test_mc3_vehicle_math_reference",
    "test_mc3_vehicle_lighting",
    "test_mc3_vehicle_texture",
    "test_mc3_vehicle_material",
    "test_mc3_vehicle_inputs",
    "test_mc3_vehicle_animation",
    "test_mc3_vehicle_bindings",
    "test_mc3_vehicle_deformation",
    "test_mc3_vehicle_fragment",
    "test_mc3_vehicle_raster",
    "test_mc3_vehicle_programs",
    "test_mc3_vehicle_gif",
    "test_mc3_vehicle_state",
    "test_mc3_vif_reference",
    "test_mc3_vehicle_sampler",
    "test_mc3_vehicle_sprite",
    "test_mc3_vehicle_paint",
    "test_mc3_panorama_angle",
    "test_mc3_vehicle_nearest",
    "test_mc3_vehicle_vram",
    "test_mc3_vehicle_depth32",
    "test_mc3_vehicle_uniforms",
    "test_mc3_vehicle_skeleton",
    "test_mc3_ee_cop2",
    "test_mc3_ee_mr32",
    "test_mc3_ee_full_add",
    "test_mc3_ee_mmi",
    "test_mc3_vehicle_dispatch",
    "test_mc3_vehicle_mip",
    "test_mc3_vehicle_paint_factory",
    "test_mc3_vehicle_mip_transport",
    "test_mc3_ee_mac",
    "test_mc3_ee_division",
    "test_mc3_vehicle_authored_draw",
    "test_mc3_vehicle_high_z",
    "test_mc3_vehicle_variable_mip",
    "test_mc3_vehicle_initialization",
    "test_mc3_vehicle_target",
    "test_mc3_vehicle_high_z_transport",
    "test_mc3_vehicle_depth_trace",
    "test_mc3_vehicle_variable_mip_transport",
    "test_mc3_texture_binding",
    "test_mc3_vehicle_transfer_reference",
    "test_mc3_tire_material",
    "test_mc3_vehicle_math",
    "test_mc3_vehicle_resources",
    "test_mc3_vu_interpreter",
    "test_mc3_vehicle_bindings_js",
    "test_mc3_vehicle_deformation_js",
    "test_mc3_vehicle_fragment_js",
    "test_mc3_vehicle_raster_js",
    "test_mc3_vehicle_programs_js",
    "test_mc3_vehicle_gif_js",
    "test_mc3_vehicle_state_js",
    "test_mc3_vif_decoder",
    "test_mc3_vehicle_pipeline",
    "test_mc3_vehicle_sampler_js",
    "test_mc3_vehicle_sprite_js",
    "test_mc3_ee",
    "test_mc3_ee_division_js",
    "test_mc3_vehicle_transfer_reference_js",
    "test_mc3_vehicle_nearest_js",
    "test_mc3_vehicle_vram_js",
    "test_mc3_vehicle_depth32_js",
    "test_mc3_vehicle_vram_pipeline",
    "test_mc3_vehicle_mip_js",
    "test_mc3_vehicle_paint_factory_js",
    "test_mc3_vehicle_mip_pipeline",
    "test_mc3_vehicle_paint_factory_pipeline",
    "test_mc3_vehicle_high_z_js",
    "test_mc3_vehicle_variable_mip_js",
    "test_mc3_vehicle_initialization_js",
    "test_mc3_vehicle_target_js",
    "test_mc3_vehicle_high_z_pipeline",
    "test_mc3_vehicle_depth_trace_js",
    "test_mc3_vehicle_variable_mip_pipeline",
    "test_mc3_specular_native",
    "test_mc3_environment_gs",
    "test_mc3_specular",
    "test_mc3_environment",
    "test_mc3_gs_raster",
    "test_mc3_environment_sky",
    "test_mc3_environment_native",
    "test_mc3_environment_pack",
    "test_mc3_environment_raster",
    "test_mc3_reference_runtime",
    "test_verify_mc3_raster_reference",
    "test_mc3_garage",
    "test_game_paint",
    "test_build_game_paints",
    "test_mc3_paint",
    "test_mcla_paint",
    "game_paints_freshness",
}


def _git_field(root, *args):
    """One git lookup, trimmed; None when git is missing or the checkout has no value."""
    try:
        found = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return found.stdout.strip() or None if found.returncode == 0 else None


def run_identity(root):
    """Self-describing stamp for results.json so a stale evidence dir maps to its commit."""
    from datetime import datetime, timezone

    try:
        node_version = (
            subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=10
            ).stdout.strip()
            or None
        )
    except (OSError, subprocess.TimeoutExpired):
        node_version = None
    identity = git_identity(root)
    catalogs = {}
    for name in (
        "dealership/public/models.json",
        "dealership/public/dealership/cars.json",
    ):
        path = Path(root) / name
        if path.is_file():
            catalogs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "run_id": str(uuid.uuid4()),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "git_sha": _git_field(root, "rev-parse", "HEAD"),
        "branch": _git_field(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "working_tree_sha256": identity["working_tree_sha256"],
        "dirty": identity["dirty"],
        "catalog_sha256": catalogs,
        "incident_id": os.environ.get("CARMODELS_INCIDENT_ID"),
        "runner": {
            "python": "%d.%d.%d" % sys.version_info[:3],
            "node": shutil.which("node") is not None,
            "node_version": node_version,
            "platform": sys.platform,
        },
    }


def registry():
    checks = [
        {"name": "ruff", "command": ["ruff", "check", "tools"], "requires": "ruff"}
    ]
    checks += [
        {
            "name": n,
            "command": ["node", f"tools/{n.removesuffix('_js')}.mjs"],
            "requires": "node",
        }
        for n in [
            "test_viewer_scenes",
            "test_under_car_shadow",
            "test_viewer_materials",
            "test_model_load",
            "test_diagnostics",
            "test_inspection_state",
            "test_mc3_record_inspection",
            "test_mc3_record_ui",
            "test_viewer_loading",
            "test_dealership",
            "test_editable_glb",
            "test_enhanced_presentation",
            "test_gt4_refinement",
            "test_gt4_materials",
            "test_native_catalog_ui",
            "test_factory_colours",
            "test_mc3_preview_ui",
            "test_mcla_preview_ui",
            "test_recovered_game_shading",
            "test_mc3_tire_material",
            "test_mc3_vehicle_math",
            "test_mc3_vehicle_resources",
            "test_mc3_vu_interpreter",
            "test_mc3_vehicle_bindings_js",
            "test_mc3_vehicle_deformation_js",
            "test_mc3_vehicle_fragment_js",
            "test_mc3_vehicle_raster_js",
            "test_mc3_vehicle_programs_js",
            "test_mc3_vehicle_gif_js",
            "test_mc3_vehicle_state_js",
            "test_mc3_vif_decoder",
            "test_mc3_vehicle_pipeline",
            "test_mc3_vehicle_sampler_js",
            "test_mc3_vehicle_sprite_js",
            "test_mc3_ee",
            "test_mc3_ee_division_js",
            "test_mc3_vehicle_transfer_reference_js",
            "test_mc3_vehicle_nearest_js",
            "test_mc3_vehicle_vram_js",
            "test_mc3_vehicle_depth32_js",
            "test_mc3_vehicle_vram_pipeline",
            "test_mc3_vehicle_mip_js",
            "test_mc3_vehicle_paint_factory_js",
            "test_mc3_vehicle_mip_pipeline",
            "test_mc3_vehicle_paint_factory_pipeline",
            "test_mc3_vehicle_high_z_js",
            "test_mc3_vehicle_variable_mip_js",
            "test_mc3_vehicle_initialization_js",
            "test_mc3_vehicle_target_js",
            "test_mc3_vehicle_high_z_pipeline",
            "test_mc3_vehicle_depth_trace_js",
            "test_mc3_vehicle_variable_mip_pipeline",
            "test_mc3_specular",
            "test_mc3_environment",
            "test_mc3_gs_raster",
            "test_game_paint",
        ]
    ]
    names = [
        "verify_recovered_asset_index",
        "verify_under_car_shadow",
        "test_export_materials",
        "test_build_showcase",
        "test_bake_models",
        "test_build_dealership",
        "test_build_game_shading_assignments",
        "test_model_catalog",
        "test_model_png",
        "test_run_checks",
        "test_diagnostics_store",
        "test_verify_inspection_browser",
        "test_verify_mc3_inspection_browser",
        "test_review_payload",
        "test_audit_stranded_worktrees",
        "test_check_advice",
        "test_static_inputs",
        "test_recovery_inputs",
        "test_gt_archive",
        "test_gt_asset_judgments",
        "test_gt_callback_triage",
        "test_gt_wheels",
        "test_gt_metadata",
        "test_gt_native_data",
        "test_gt_model",
        "test_refine_gt_model",
        "test_build_gt_counterparts",
        "test_import_gt_dealership",
        "test_library_filter",
        "test_serve_library",
        "test_redline_archive",
        "test_extract_redline_cars",
        "test_mc3_archive",
        "test_extract_mc3_cars",
        "test_import_mc3_catalogs",
        "test_mc3_tire_alpha",
        "test_mc3_tire_vu",
        "test_mc3_vehicle_vu",
        "test_mc3_vehicle_math_reference",
        "test_mc3_vehicle_lighting",
        "test_mc3_vehicle_texture",
        "test_mc3_vehicle_material",
        "test_mc3_vehicle_inputs",
        "test_mc3_vehicle_animation",
        "test_mc3_vehicle_bindings",
        "test_mc3_vehicle_deformation",
        "test_mc3_vehicle_fragment",
        "test_mc3_vehicle_raster",
        "test_mc3_vehicle_programs",
        "test_mc3_vehicle_gif",
        "test_mc3_vehicle_state",
        "test_mc3_vif_reference",
        "test_mc3_vehicle_sampler",
        "test_mc3_vehicle_sprite",
        "test_mc3_vehicle_paint",
        "test_mc3_panorama_angle",
        "test_mc3_vehicle_nearest",
        "test_mc3_vehicle_vram",
        "test_mc3_vehicle_depth32",
        "test_mc3_vehicle_uniforms",
        "test_mc3_vehicle_skeleton",
        "test_mc3_ee_cop2",
        "test_mc3_ee_mr32",
        "test_mc3_ee_full_add",
        "test_mc3_ee_mmi",
        "test_mc3_vehicle_dispatch",
        "test_mc3_vehicle_mip",
        "test_mc3_vehicle_paint_factory",
        "test_mc3_vehicle_mip_transport",
        "test_mc3_ee_mac",
        "test_mc3_ee_division",
        "test_mc3_vehicle_authored_draw",
        "test_mc3_vehicle_high_z",
        "test_mc3_vehicle_variable_mip",
        "test_mc3_vehicle_initialization",
        "test_mc3_vehicle_target",
        "test_mc3_vehicle_high_z_transport",
        "test_mc3_vehicle_depth_trace",
        "test_mc3_vehicle_variable_mip_transport",
        "test_mc3_texture_binding",
        "test_mc3_vehicle_transfer_reference",
        "test_mc3_specular_native",
        "test_mc3_environment_gs",
        "test_mc3_environment_sky",
        "test_mc3_environment_native",
        "test_mc3_environment_pack",
        "test_mc3_environment_raster",
        "test_mc3_reference_runtime",
        "test_verify_mc3_raster_reference",
        "test_mc3_garage",
        "test_mc3_pck",
        "test_mc3_wheels",
        "test_mc3_materials",
        "test_mc3_textures",
        "test_mc3_model",
        "test_export_mc3_models",
        "test_mc3_preview",
        "test_import_mc3_previews",
        "test_mc3_preview_experiments",
        "test_redline_mesh",
        "test_redline_texture",
        "test_redline_model",
        "test_export_redline_models",
        "test_import_redline_dealership",
        "test_gt4_volume",
        "test_extract_gt4_cars",
        "test_gt4_model",
        "test_gt4_specdb",
        "test_gt4_glb",
        "test_import_gt4_catalog",
        "test_import_gt4_dealership",
        "test_aes_decrypt",
        "test_xdvdfs",
        "test_xex2",
        "test_mcla_rpf",
        "test_extract_mcla_cars",
        "test_mcla_lzx",
        "test_mcla_resource",
        "test_mcla_model",
        "test_mcla_texture",
        "test_mcla_tuning",
        "test_verify_mcla_resources",
        "test_verify_mcla_decoding",
        "test_mcla_names",
        "test_mcla_preview",
        "test_mcla_preview_geometry",
        "test_mc3_paint",
        "test_mcla_paint",
        "test_build_game_paints",
        "test_import_mcla_catalog",
        "test_import_mcla_dealership",
        "test_mcla_preview_experiments",
        "test_line_coverage",
    ]
    checks += [{"name": n, "command": ["python3", f"tools/{n}.py"]} for n in names]
    # Full source-disc rederivation is a serial barrier; the offline test above is read-only.
    checks.append(
        {
            "name": "mc3_tire_alpha_native",
            "command": ["python3", "tools/verify_mc3_tire_alpha.py", "--disc"],
            "availability": [
                "python3",
                "tools/verify_mc3_tire_alpha.py",
                "--available",
            ],
        }
    )
    checks.append(
        {
            "name": "mc3_raster_reference_native",
            "command": ["python3", "tools/verify_mc3_raster_reference.py"],
            "availability": [
                "python3",
                "tools/verify_mc3_raster_reference.py",
                "--available",
            ],
        }
    )
    checks.append(
        {
            "name": "gt4_materials_corpus",
            "command": ["node", "tools/audit_gt4_materials.mjs"],
            "requires": "node",
        }
    )
    checks.append(
        {
            "name": "gt4_refinement_corpus",
            "command": ["node", "tools/audit_gt4_refinement.mjs"],
            "requires": "node",
        }
    )
    checks.append(
        {
            "name": "game_paints_freshness",
            "command": ["python3", "tools/build_game_paints.py", "--check"],
        }
    )
    checks.append(
        {
            "name": "dealership_freshness",
            "command": ["python3", "tools/build_dealership.py", "--check"],
        }
    )
    # The candidate game-shading Header table and the retained preview copy are derived, never hand-edited.
    checks.append(
        {
            "name": "game_shading_assignments_freshness",
            "command": [
                "python3",
                "tools/build_game_shading_assignments.py",
                "--check",
            ],
        }
    )
    checks.append(
        {
            "name": "gt_models",
            "command": ["python3", "tools/export_gt_models.py", "--check"],
        }
    )
    checks.append(
        {
            "name": "gt_enhanced_pilot",
            "command": ["python3", "tools/refine_gt_model.py", "--check"],
        }
    )
    checks.append(
        {
            "name": "gt_counterparts",
            "command": ["python3", "tools/build_gt_counterparts.py", "--check"],
        }
    )
    checks.append(
        {
            "name": "gt_extraction",
            "command": ["python3", "tools/extract_gt_cars.py", "--check"],
            "availability": [
                "python3",
                "-c",
                "from pathlib import Path; import sys; sys.exit(0 if any(Path(p).is_file() for p in ["
                "'games/gran-turismo/game-files/gran-turismo.bin', 'games/source-data/PS1/gran-turismo/gran-turismo.bin']) else 1)",
            ],
        }
    )
    # The full GT4 extraction and native ZIPs stay local; the re-derivation runs only where they exist.
    checks.append(
        {
            "name": "gt4_catalog",
            "command": ["python3", "tools/import_gt4_catalog.py", "--check"],
            "availability": ["python3", "tools/import_gt4_catalog.py", "--available"],
        }
    )
    # The disc is never committed; its re-derivation runs only where the pinned ISO is supplied.
    checks.append(
        {
            "name": "gt4_extraction",
            "command": ["python3", "tools/extract_gt4_cars.py", "--check"],
            "availability": [
                "python3",
                "-c",
                "from pathlib import Path; import sys; sys.exit(0 if Path("
                "'games/gran-turismo-4/game-files/Gran Turismo 4 (axekin.com).iso').is_file() else 1)",
            ],
        }
    )
    # Line coverage of the MCLA readers and the review bundle builder under their own tests (stdlib trace).
    covered = [
        "aes_decrypt",
        "xdvdfs",
        "xex2",
        "mcla_rpf",
        "extract_mcla_cars",
        "review_payload",
        "mcla_lzx",
        "mcla_resource",
        "mcla_model",
        "mcla_texture",
        "mcla_tuning",
        "verify_mcla_resources",
        "verify_mcla_decoding",
        "mcla_preview_geometry",
    ]
    checks.append(
        {
            "name": "line_coverage",
            "command": [
                "python3",
                "tools/line_coverage.py",
                "--minimum",
                "95",
                "--modules",
                *[f"tools/{n}.py" for n in covered],
                "--tests",
                *[f"tools/test_{n}.py" for n in covered],
            ],
        }
    )
    # The MCLA disc is never committed either; the same skip applies when it is absent.
    checks.append(
        {
            "name": "mcla_extraction",
            "command": ["python3", "tools/extract_mcla_cars.py", "--check"],
            "availability": [
                "python3",
                "-c",
                "from pathlib import Path; import sys; sys.exit(0 if Path("
                "'games/midnight-club-los-angeles/game-files/Midnight Club - Los Angeles - Complete Edition "
                "(USA, Europe).iso').is_file() else 1)",
            ],
        }
    )
    # Every RSC5 resource of the disc decompressed to its declared size (needs the ISO), then every car model,
    # texture, tuning and streaming map of the local extraction decoded (needs the extraction).
    checks.append(
        {
            "name": "mcla_resources",
            "command": ["python3", "tools/verify_mcla_resources.py"],
            "availability": [
                "python3",
                "tools/verify_mcla_resources.py",
                "--available",
            ],
        }
    )
    checks.append(
        {
            "name": "mcla_decoding",
            "command": ["python3", "tools/verify_mcla_decoding.py"],
            "availability": ["python3", "tools/verify_mcla_decoding.py", "--available"],
        }
    )
    checks.append(
        {
            "name": "mcla_names",
            "command": ["python3", "tools/mcla_names.py"],
            "availability": next(c for c in checks if c["name"] == "mcla_extraction")[
                "availability"
            ],
        }
    )
    checks.append(
        {
            "name": "mcla_catalog",
            "command": ["python3", "tools/import_mcla_catalog.py", "--check"],
            "availability": ["python3", "tools/import_mcla_catalog.py", "--available"],
        }
    )
    for name in [
        "verify_config_data_sound",
        "verify_sound_bank_index",
        "verify_vu_dispatch_map",
        "test_vu_dispatch_map",
        "test_vu1_decode",
        "verify_vu_pass_handlers",
        "test_vu_pass_handlers",
    ]:
        checks.append(
            {
                "name": name,
                "command": ["python3", f"tools/{name}.py"],
                "availability": ["python3", "tools/static_inputs.py", "--available"],
            }
        )
    for verifier, test in [
        ("verify_vu_handler_dump", "test_vu_handler_dump"),
        ("recover_dump_reference_frame", "test_recover_dump_reference_frame"),
    ]:
        for name in [verifier, test]:
            checks.append(
                {
                    "name": name,
                    "command": ["python3", f"tools/{name}.py"],
                    "availability": ["python3", f"tools/{verifier}.py", "--available"],
                }
            )
    for name in ["verify_pass_source_join", "test_pass_source_join"]:
        checks.append(
            {
                "name": name,
                "command": ["python3", f"tools/{name}.py"],
                "availability": [
                    "python3",
                    "tools/verify_pass_source_join.py",
                    "--available",
                ],
            }
        )
    blender = os.environ.get("CARMODELS_BLENDER") or shutil.which("blender")
    mounted = ROOT / ".scratch/blender-4.5.14/Blender.app/Contents/MacOS/Blender"
    if blender is None and mounted.is_file():
        blender = str(mounted)
    checks.append(
        {
            "name": "dealership_roundtrip",
            "command": [
                blender or "blender",
                "--background",
                "--python-exit-code",
                "1",
                "--python",
                "tools/test_dealership_roundtrip.py",
            ],
            "requires": blender or "blender",
        }
    )
    checks.append(
        {
            "name": "redline_roundtrip",
            "command": [
                blender or "blender",
                "--background",
                "--python-exit-code",
                "1",
                "--python",
                "tools/test_redline_roundtrip.py",
            ],
            "requires": blender or "blender",
            "availability": [
                "python3",
                "-c",
                "from pathlib import Path; import sys; sys.exit(0 if Path('dealership/public/redline/index.json').is_file() else 1)",
            ],
        }
    )
    checks.append(
        {
            "name": "mc3_roundtrip",
            "command": [
                blender or "blender",
                "--background",
                "--python-exit-code",
                "1",
                "--python",
                "tools/test_mc3_roundtrip.py",
            ],
            "requires": blender or "blender",
        }
    )
    for check in checks:
        check["parallel"] = check["name"] in PARALLEL_SAFE
    return checks


def select(checks, names, games=False, full=False, game=()):
    """Select explicit checks or the showcase with requested game coverage."""
    requested = set(names)
    unknown = requested - {c["name"] for c in checks}
    if unknown:
        raise ValueError("Unknown checks: " + ", ".join(sorted(unknown)))
    if requested:
        return [c for c in checks if c["name"] in requested]
    unknown_games = set(game) - GAMES.keys()
    if unknown_games:
        raise ValueError("Unknown game: " + ", ".join(sorted(unknown_games)))
    prefixes = tuple(prefix for slug in game for prefix in GAMES[slug])
    return [
        c
        for c in checks
        if c["name"] in SHOWCASE
        or (
            (c["name"].startswith(prefixes) if game else games or full)
            and (full or c["name"] not in FULL_ONLY)
        )
    ]


def _run_check(check, root, evidence, ci, started):
    """Run one check with a private log. Only the coordinator writes the manifest or prints."""
    name, command = check["name"], check["command"]
    start = time.monotonic()
    row = {
        "name": name,
        "command": command,
        "status": "pass",
        "exit_code": 0,
        "log": name + ".log",
        "parallel": check.get("parallel") is True,
        "started_seconds": round(start - started, 3),
    }
    log = evidence / row["log"]
    with log.open("w") as stream:
        try:
            requirement = check.get("requires")
            if requirement and not shutil.which(requirement):
                row.update(
                    status="fail" if ci else "skip",
                    exit_code=127 if ci else None,
                    reason=f"Required runtime unavailable: {requirement}",
                )
                stream.write(row["reason"] + "\n")
            else:
                available = (
                    subprocess.run(
                        check["availability"], cwd=root, capture_output=True, text=True
                    )
                    if "availability" in check
                    else None
                )
                if available is not None and available.returncode:
                    row.update(
                        status="skip" if available.returncode == 1 else "fail",
                        exit_code=None
                        if available.returncode == 1
                        else available.returncode,
                        reason="Optional pinned inputs unavailable"
                        if available.returncode == 1
                        else "Input availability check failed",
                    )
                    stream.write(
                        row["reason"] + "\n" + available.stdout + available.stderr
                    )
                else:
                    result = subprocess.run(
                        command, cwd=root, stdout=stream, stderr=subprocess.STDOUT
                    )
                    row.update(
                        exit_code=result.returncode,
                        status="pass" if result.returncode == 0 else "fail",
                    )
        except OSError as error:
            stream.write(str(error) + "\n")
            row.update(status="fail", exit_code=127)
    row["elapsed_seconds"] = round(time.monotonic() - start, 3)
    return row


def write_run_index(evidence, status, ordered, not_run, identity):
    """Small listing record beside results.json so CI artifacts answer 'runs for commit X'."""
    counts = {"pass": 0, "fail": 0, "skip": 0}
    for row in ordered:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    index = {
        "schema": 1,
        "exit_code": status,
        "total": len(ordered),
        "passed": counts.get("pass", 0),
        "failed": counts.get("fail", 0),
        "skipped": counts.get("skip", 0),
        "not_run": list(not_run),
        "failed_checks": [row["name"] for row in ordered if row["status"] == "fail"],
        **identity,
    }
    (Path(evidence) / "run-index.json").write_text(json.dumps(index, indent=2) + "\n")
    return index


def append_history(
    ledger, root, evidence, status, ordered, elapsed_seconds, not_run, identity
):
    """One JSONL line per completed run: trends and flake counts without touching receipts."""
    line = {
        "schema": 1,
        "exit_code": status,
        "evidence": str(Path(evidence).resolve()),
        "checks": {row["name"]: row["status"] for row in ordered},
        "elapsed": {row["name"]: row.get("elapsed_seconds") for row in ordered},
        "elapsed_seconds": round(elapsed_seconds, 3),
        "not_run": list(not_run),
        **identity,
    }
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as stream:
        stream.write(json.dumps(line) + "\n")
    return line


def run_checks(checks, root, evidence, ci=False, not_run=(), jobs=1, ledger=None):
    """Bound subprocess concurrency within each audited group; other checks run alone."""
    if type(jobs) is not int or jobs < 1:
        raise ValueError("jobs must be a positive integer")
    if len({c["name"] for c in checks}) != len(checks):
        raise ValueError("Check names must be unique; each log has one owner")
    root, evidence = Path(root), Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    if any(evidence.iterdir()):
        raise ValueError(
            "Evidence directory must be empty; previous logs are preserved"
        )
    started = time.monotonic()
    identity = run_identity(root)
    rows = {}

    def manifest():
        ordered = [rows[c["name"]] for c in checks if c["name"] in rows]
        status = 1 if any(r["status"] == "fail" for r in ordered) else 0
        # Atomic replacement lets readers inspect a complete JSON document during execution.
        temporary = evidence / ".results.json.tmp"
        temporary.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "exit_code": status,
                    "checks": ordered,
                    "jobs": jobs,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "pending": [c["name"] for c in checks if c["name"] not in rows],
                    "not_run": list(not_run),
                    **identity,
                    "claim_limits": [
                        "Only listed checks ran; skips are not passes. Logs record execution, not shader fidelity."
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        temporary.replace(evidence / "results.json")
        return status

    def record(row):
        rows[row["name"]] = row
        manifest()
        print(f"{row['status']:4}  {row['name']}  ({row['log']})", flush=True)
        if row["status"] == "fail":
            print(
                "\n".join(
                    (evidence / row["log"])
                    .read_text(errors="replace")
                    .splitlines()[-20:]
                ),
                flush=True,
            )

    manifest()
    with ThreadPoolExecutor(max_workers=min(jobs, len(checks) or 1)) as pool:
        for parallel, group in groupby(checks, key=lambda c: c.get("parallel") is True):
            if not parallel or jobs == 1:
                for check in group:
                    record(_run_check(check, root, evidence, ci, started))
                continue
            pending = set()
            exhausted = False
            while pending or not exhausted:
                while len(pending) < jobs and not exhausted:
                    check = next(group, None)
                    if check is None:
                        exhausted = True
                    else:
                        pending.add(
                            pool.submit(_run_check, check, root, evidence, ci, started)
                        )
                if pending:
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        record(future.result())
    status = manifest()
    ordered = [rows[c["name"]] for c in checks if c["name"] in rows]
    write_run_index(evidence, status, ordered, not_run, identity)
    if ledger is not None:
        append_history(
            ledger,
            root,
            evidence,
            status,
            ordered,
            time.monotonic() - started,
            not_run,
            identity,
        )
    return status


def main():
    if sys.version_info < MIN_PYTHON:
        print(
            "ERROR: tools/check.sh needs Python %d.%d or newer; python3 is %d.%d (%s)"
            % (*MIN_PYTHON, *sys.version_info[:2], sys.executable)
        )
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Check names, comma separated; repeatable",
    )
    parser.add_argument(
        "--games",
        action="store_true",
        help="Also run game-tool tests; bulk re-derivation requires --full",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include bulk corpus, disc and private-input checks (optionally restricted by --game)",
    )
    parser.add_argument(
        "--game",
        action="append",
        choices=tuple(GAMES),
        default=[],
        help="Include checks for this game plus the showcase; repeatable, add --full for re-derivation",
    )
    parser.add_argument("--list", action="store_true")
    parser.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"Maximum concurrent audited checks (default {DEFAULT_JOBS}); 1 runs serially",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="Empty directory for full logs and results.json",
    )
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be a positive integer")
    checks = registry()
    try:
        if args.only and (args.games or args.full or args.game):
            parser.error("--only cannot be combined with --games, --game or --full")
        if args.games and args.game:
            parser.error("choose --games for all games or --game for selected games")
        selected = select(
            checks,
            [n for group in args.only for n in group.split(",")],
            games=args.games,
            full=args.full,
            game=args.game,
        )
        if args.list:
            listed = (
                selected
                if args.only or args.games or args.full or args.game
                else checks
            )
            print("\n".join(c["name"] for c in listed))
            return 0
        not_run = [c["name"] for c in checks if c not in selected]
        checks = selected
        if args.evidence_dir is None:
            parent = ROOT / ".scratch/checks"
            parent.mkdir(parents=True, exist_ok=True)
            evidence = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
        else:
            evidence = args.evidence_dir.resolve()
        print(f"Evidence: {evidence}", flush=True)
        if not_run and not args.only:
            print(
                f"{len(not_run)} checks not run (tools/check.sh --full runs every check)",
                flush=True,
            )
        print(f"Jobs: {args.jobs} (exclusive checks run alone)", flush=True)
        ledger = ROOT / ".scratch/check-history.jsonl"
        return run_checks(
            checks,
            ROOT,
            evidence,
            ci=bool(os.environ.get("CI")),
            not_run=not_run,
            jobs=args.jobs,
            ledger=ledger,
        )
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
