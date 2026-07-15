"""CLI-contract tests for the performance registry fetcher (issue 26).

The Orchestrator invokes this repo as ``python run.py --output <path>`` from the
``performance/`` directory (see the orchestrator's ``refresh_performance``
StageCommand). These tests pin that published argv surface so a flag rename or a
relative-import regression fails a named test here instead of silently breaking
the daily chain / Control Panel "Refresh now".

Two adapters justify the seam:
  * in-process ``main([...])`` with the network stubbed — asserts the file lands
    at the exact contract path;
  * a subprocess ``python run.py --help`` from the repo's own cwd — asserts the
    script runs with no relative-import crash and exposes ``--output``.
"""

import csv
import subprocess
import sys
from pathlib import Path

PERF_DIR = Path(__file__).resolve().parent.parent
if str(PERF_DIR) not in sys.path:
    sys.path.insert(0, str(PERF_DIR))

import run  # noqa: E402


def _stub_network(monkeypatch):
    """Stub every AMFI network seam run_download reaches through."""
    monkeypatch.setattr(
        run,
        "fetch_filters",
        lambda: {
            "maturityTypeList": [{"id": 1, "name": "Open Ended"}],
            "investmentTypeList": [{"id": 10, "name": "Equity"}],
            "reportDate": "01-Jan-2026",
        },
    )
    monkeypatch.setattr(run, "is_holiday", lambda report_date: False)
    monkeypatch.setattr(
        run, "fetch_subcategories", lambda category_id: [{"id": 100, "name": "Large Cap"}]
    )
    monkeypatch.setattr(
        run,
        "fetch_performance",
        lambda **kwargs: [{"schemeName": "ABC Bluechip Fund", "return1y": 12.3}],
    )


def test_output_flag_writes_to_exact_contract_path(tmp_path, monkeypatch):
    """The exact argv the Orchestrator emits lands the CSV at the given path."""
    _stub_network(monkeypatch)
    out = tmp_path / "data" / "reference" / "performance_data.csv"

    run.main(["--output", str(out)])

    assert out.exists(), "performance_data.csv must land at the --output path"
    with out.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "dataset must contain the fetched records"
    assert rows[0]["Report_Date"] == "01-Jan-2026"
    assert rows[0]["Category"] == "Equity"


def test_output_flag_does_not_write_off_contract_default(tmp_path, monkeypatch):
    """With --output given, the in-repo default path is never written."""
    _stub_network(monkeypatch)
    default_path = PERF_DIR.parent / "data" / "performance_data.csv"
    existed_before = default_path.exists()

    out = tmp_path / "performance_data.csv"
    run.main(["--output", str(out)])

    assert out.exists()
    if not existed_before:
        assert not default_path.exists(), "must not write the off-contract default when --output is given"


def test_runs_as_plain_script_without_relative_import_crash():
    """`python run.py --help` from the repo's own cwd exits 0 (no import crash)."""
    result = subprocess.run(
        [sys.executable, "run.py", "--help"],
        cwd=str(PERF_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"run.py crashed: {result.stderr}"
    assert "--output" in result.stdout
