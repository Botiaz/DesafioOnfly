"""Testes adicionais: contrato do CLI (argumentos, códigos de saída, dataset real)."""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import BASE, COLUMNS, PROJECT_ROOT, SRC_DIR

DATA_DIR = PROJECT_ROOT / "data"
RATES = DATA_DIR / "taxas_cambio.csv"


def run(args: list[str]) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "onfly_report", *args],
        cwd=str(PROJECT_ROOT),
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str] = COLUMNS) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows({**BASE, **row} for row in rows)
    return path


# --- Sucesso --------------------------------------------------------------------------------


def test_success_exit_code_creates_output_dir_and_prints_summary(tmp_path):
    output = tmp_path / "nested" / "dir" / "report.json"
    process = run(["--input", str(DATA_DIR / "exemplo-validacao.csv"), "--rates", str(RATES), "--output", str(output)])

    assert process.returncode == 0, process.stderr
    assert output.is_file()
    assert "Reservas: 12" in process.stdout
    assert "Confirmadas: 9" in process.stdout


def test_full_dataset_matches_file_counts(tmp_path):
    """O relatório do dataset real conta todas as linhas do arquivo e respeita as regras."""
    with (DATA_DIR / "reservas_hoteis.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    output = tmp_path / "report.json"
    process = run(["--input", str(DATA_DIR / "reservas_hoteis.csv"), "--rates", str(RATES), "--output", str(output)])
    assert process.returncode == 0, process.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert summary["total_reservations"] == len(rows)
    assert summary["confirmed_reservations"] == sum(r["status"] == "CONFIRMED" for r in rows)
    assert summary["cancelled_reservations"] == sum(r["status"] == "CANCELLED" for r in rows)
    assert summary["no_show_reservations"] == sum(r["status"] == "NO_SHOW" for r in rows)
    assert summary["total_room_nights"] > 0
    assert all(m["room_nights"] > 0 for m in report["by_month"])

    totals = [float(h["total_brl"]) for h in report["top_hotels"]]
    assert totals == sorted(totals, reverse=True)
    assert len(report["top_hotels"]) == 5


# --- Erros de argumento (código 2) ----------------------------------------------------------


@pytest.mark.parametrize("top", ["0", "-1", "abc"])
def test_invalid_top_exits_2(tmp_path, top):
    input_path = write_csv(tmp_path / "in.csv", [{}])
    process = run(
        ["--input", str(input_path), "--rates", str(RATES), "--output", str(tmp_path / "r.json"), "--top", top]
    )

    assert process.returncode == 2


def test_missing_required_argument_exits_2():
    process = run(["--rates", str(RATES)])

    assert process.returncode == 2


# --- Erros de entrada (código 2) ------------------------------------------------------------


def test_missing_input_file_exits_2(tmp_path):
    process = run(
        ["--input", str(tmp_path / "nao-existe.csv"), "--rates", str(RATES), "--output", str(tmp_path / "r.json")]
    )

    assert process.returncode == 2
    assert not (tmp_path / "r.json").exists()


def test_missing_rates_file_exits_2(tmp_path):
    input_path = write_csv(tmp_path / "in.csv", [{}])
    process = run(
        ["--input", str(input_path), "--rates", str(tmp_path / "x.csv"), "--output", str(tmp_path / "r.json")]
    )

    assert process.returncode == 2


def test_missing_column_exits_2(tmp_path):
    columns = [c for c in COLUMNS if c != "amount"]
    input_path = write_csv(tmp_path / "in.csv", [{}], columns=columns)
    process = run(["--input", str(input_path), "--rates", str(RATES), "--output", str(tmp_path / "r.json")])

    assert process.returncode == 2


@pytest.mark.parametrize(
    "row",
    [
        {"checkin_date": "10/01/2025"},
        {"rooms": "dois"},
        {"amount": "abc"},
    ],
)
def test_malformed_row_exits_2(tmp_path, row):
    input_path = write_csv(tmp_path / "in.csv", [row])
    process = run(["--input", str(input_path), "--rates", str(RATES), "--output", str(tmp_path / "r.json")])

    assert process.returncode == 2
