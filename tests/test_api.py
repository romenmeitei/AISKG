from __future__ import annotations

import pytest

import aiskg
from aiskg.cli import build_parser


def test_public_api():
    assert aiskg.__version__ == "3.1.2"
    assert callable(aiskg.run_pipeline)


def test_cli_parser_accepts_expected_commands():
    parser = build_parser()
    assert parser.parse_args(["list-variants", "--config", "config.yaml"]).command == "list-variants"
    assert parser.parse_args(["stage", "ablation"]).name == "ablation"
    assert parser.parse_args(["additional-analyses"]).command == "additional-analyses"
    with pytest.raises(SystemExit):
        parser.parse_args(["additional-analyses", "--no-clean"])
