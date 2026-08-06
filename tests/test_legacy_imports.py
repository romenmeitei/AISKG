from __future__ import annotations

from aiskg.legacy import section1_engine, section2_engine


def test_legacy_engines_expose_canonical_entry_points():
    assert callable(section1_engine.run_snapshot_pipeline)
    assert callable(section2_engine.run_pipeline)
