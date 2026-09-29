from pathlib import Path

import pytest

from jev_review.config import ConfigError, load_config

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "jev_review" / "default_rules.yaml"


def test_loads_two_validated_rules_and_overlay(tmp_path: Path):
    config, digest = load_config(BASE)
    assert set(config["rules"]) == {"Consumer contract asserted", "Product logic exercised"}
    assert len(digest) == 64
    overlay = tmp_path / "overlay.yaml"
    overlay.write_text(
        'schema_version: 1\nrules:\n  "Product logic exercised":\n    flag_probability: 0.97\n'
    )
    config, _ = load_config(BASE, [str(overlay)], ["Product logic exercised"])
    assert list(config["rules"]) == ["Product logic exercised"]
    assert config["rules"]["Product logic exercised"]["flag_probability"] == 0.97


@pytest.mark.parametrize(
    "body",
    [
        "schema_version: 1\nschema_version: 1\n",
        'schema_version: 1\nrules: {x: !!python/object/apply:os.system ["true"]}\n',
        'schema_version: 1\nrules: {"Product logic exercised": {warning_probability: 2}}\n',
    ],
)
def test_rejects_unsafe_or_invalid_overlays(tmp_path: Path, body: str):
    overlay = tmp_path / "bad.yaml"
    overlay.write_text(body)
    with pytest.raises(ConfigError):
        load_config(BASE, [str(overlay)])
