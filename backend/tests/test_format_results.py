import numpy as np
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import format_results, LEVELS, LEVELS_, SEVERITIES

TARGETS = (
    [f"spinal_canal_stenosis_{l}" for l in LEVELS_]
    + [f"left_neural_foraminal_narrowing_{l}" for l in LEVELS_]
    + [f"right_neural_foraminal_narrowing_{l}" for l in LEVELS_]
    + [f"left_subarticular_stenosis_{l}" for l in LEVELS_]
    + [f"right_subarticular_stenosis_{l}" for l in LEVELS_]
)


def make_preds(severity_idx: int = 0) -> np.ndarray:
    """25 classes, shape (1, 25, 3). All predict severity_idx."""
    p = np.zeros((1, 25, 3))
    p[:, :, severity_idx] = 1.0
    return p


def test_returns_five_levels():
    results = format_results(make_preds(), TARGETS, [])
    assert len(results) == 5


def test_level_labels():
    results = format_results(make_preds(), TARGETS, [])
    assert [r["level"] for r in results] == ["L1-L2", "L2-L3", "L3-L4", "L4-L5", "L5-S1"]


def test_all_normal_mild():
    results = format_results(make_preds(0), TARGETS, [])
    for r in results:
        assert r["spinal_canal_stenosis"]["severity"] == "Normal/Mild"
        assert r["neural_foraminal_narrowing"]["left"]["severity"] == "Normal/Mild"
        assert r["neural_foraminal_narrowing"]["right"]["severity"] == "Normal/Mild"
        assert r["subarticular_stenosis"]["left"]["severity"] == "Normal/Mild"
        assert r["subarticular_stenosis"]["right"]["severity"] == "Normal/Mild"


def test_severe_scs_l3_l4():
    """Index 2 in the targets list is spinal_canal_stenosis_l3_l4."""
    preds = make_preds(0)
    preds[0, 2, 0] = 0.0
    preds[0, 2, 2] = 1.0  # Severe
    results = format_results(preds, TARGETS, [])
    assert results[2]["level"] == "L3-L4"
    assert results[2]["spinal_canal_stenosis"]["severity"] == "Severe"
    assert results[0]["spinal_canal_stenosis"]["severity"] == "Normal/Mild"


def test_left_right_nfn_differ():
    """Left NFN L1/L2 (index 5) = Moderate, right (index 10) = Normal/Mild."""
    preds = make_preds(0)
    preds[0, 5, 0] = 0.0
    preds[0, 5, 1] = 1.0  # Moderate
    results = format_results(preds, TARGETS, [])
    assert results[0]["neural_foraminal_narrowing"]["left"]["severity"] == "Moderate"
    assert results[0]["neural_foraminal_narrowing"]["right"]["severity"] == "Normal/Mild"


def test_none_preds_defaults_to_normal_mild():
    results = format_results(None, None, [])
    assert len(results) == 5
    for r in results:
        assert r["spinal_canal_stenosis"]["severity"] == "Normal/Mild"
        assert r["spinal_canal_stenosis"]["confidence"] == 0.0


def test_crops_info_coordinates_used():
    coords = [{"x": 0.1 * i, "y": 0.2 * i} for i in range(5)]
    crops_info = [{"study_series": "test", "coords": coords}]
    results = format_results(make_preds(), TARGETS, crops_info)
    assert results[0]["coordinates"] == {"x": 0.0, "y": 0.0}
    assert results[1]["coordinates"] == {"x": 0.1, "y": 0.2}
