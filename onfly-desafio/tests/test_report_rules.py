"""Testes adicionais: regras de negócio de ponta a ponta, executando o CLI."""

import re

from helpers import run_cli

MONEY = re.compile(r"^-?\d+\.\d{2}$")


# --- Contrato do relatório ------------------------------------------------------------------


def test_report_schema(tmp_path):
    report = run_cli(tmp_path, [{}])

    assert set(report) == {"report_version", "generated_at", "summary", "by_month", "top_hotels"}
    assert report["report_version"] == "1.0"
    assert report["generated_at"].endswith("-03:00")
    assert set(report["summary"]) == {
        "total_reservations",
        "confirmed_reservations",
        "cancelled_reservations",
        "no_show_reservations",
        "total_room_nights",
        "total_amount_brl",
        "average_nightly_rate_brl",
    }
    assert set(report["by_month"][0]) == {"month", "reservations", "room_nights", "total_brl"}
    assert set(report["top_hotels"][0]) == {"hotel_id", "hotel_name", "room_nights", "total_brl"}


def test_money_fields_are_strings_with_two_decimals(tmp_path):
    report = run_cli(tmp_path, [{"amount": "1234.5"}, {"reservation_id": "R-2", "currency": "USD", "amount": "7"}])

    summary = report["summary"]
    for value in (summary["total_amount_brl"], summary["average_nightly_rate_brl"]):
        assert isinstance(value, str) and MONEY.match(value)
    for item in report["by_month"] + report["top_hotels"]:
        assert isinstance(item["total_brl"], str) and MONEY.match(item["total_brl"])


# --- Status ---------------------------------------------------------------------------------


def test_status_counts_and_totals(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "status": "CONFIRMED", "amount": "100.00"},
            {"reservation_id": "R-2", "status": "CONFIRMED", "amount": "50.00"},
            {"reservation_id": "R-3", "status": "CANCELLED", "amount": "999.00"},
            {"reservation_id": "R-4", "status": "NO_SHOW", "amount": "888.00"},
            {"reservation_id": "R-5", "status": "NO_SHOW", "amount": "777.00"},
        ],
    )
    summary = report["summary"]
    assert summary["total_reservations"] == 5
    assert summary["confirmed_reservations"] == 2
    assert summary["cancelled_reservations"] == 1
    assert summary["no_show_reservations"] == 2
    assert summary["total_room_nights"] == 2
    assert summary["total_amount_brl"] == "150.00"


def test_non_confirmed_do_not_create_months_or_hotels(tmp_path):
    """Um mês/hotel que só tem cancelamento ou no-show não aparece no relatório."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H01", "checkin_date": "2025-01-10", "checkout_date": "2025-01-11"},
            {
                "reservation_id": "R-2",
                "hotel_id": "H02",
                "status": "CANCELLED",
                "checkin_date": "2025-03-10",
                "checkout_date": "2025-03-11",
            },
            {
                "reservation_id": "R-3",
                "hotel_id": "H03",
                "status": "NO_SHOW",
                "checkin_date": "2025-04-10",
                "checkout_date": "2025-04-11",
            },
        ],
    )
    assert [m["month"] for m in report["by_month"]] == ["2025-01"]
    assert [h["hotel_id"] for h in report["top_hotels"]] == ["H01"]
    assert report["by_month"][0]["reservations"] == 1


def test_no_confirmed_reservations(tmp_path):
    report = run_cli(tmp_path, [{"status": "CANCELLED"}, {"reservation_id": "R-2", "status": "NO_SHOW"}])

    summary = report["summary"]
    assert summary["total_reservations"] == 2
    assert summary["total_room_nights"] == 0
    assert summary["total_amount_brl"] == "0.00"
    assert summary["average_nightly_rate_brl"] == "0.00"
    assert report["by_month"] == []
    assert report["top_hotels"] == []


# --- Noites e meses -------------------------------------------------------------------------


def test_month_uses_checkin_date(tmp_path):
    """Estadia que cruza o mês conta inteira no mês do check-in."""
    report = run_cli(tmp_path, [{"checkin_date": "2025-01-30", "checkout_date": "2025-02-02", "rooms": "2"}])

    assert report["by_month"] == [{"month": "2025-01", "reservations": 1, "room_nights": 6, "total_brl": "100.00"}]
    assert report["summary"]["total_room_nights"] == 6


def test_by_month_sorted_ascending_across_years(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "checkin_date": "2025-02-01", "checkout_date": "2025-02-02"},
            {"reservation_id": "R-2", "checkin_date": "2024-12-30", "checkout_date": "2025-01-02"},
            {"reservation_id": "R-3", "checkin_date": "2025-01-15", "checkout_date": "2025-01-16"},
        ],
    )
    assert [m["month"] for m in report["by_month"]] == ["2024-12", "2025-01", "2025-02"]
    assert report["by_month"][0]["room_nights"] == 3


def test_by_month_totals_add_up_to_summary(tmp_path):
    rows = [
        {
            "reservation_id": f"R-{i}",
            "checkin_date": f"2025-0{1 + i % 3}-10",
            "checkout_date": f"2025-0{1 + i % 3}-12",
            "currency": ("BRL", "USD", "EUR")[i % 3],
            "amount": f"{100 + i}.33",
        }
        for i in range(9)
    ]
    report = run_cli(tmp_path, rows)

    summary = report["summary"]
    assert sum(m["reservations"] for m in report["by_month"]) == summary["confirmed_reservations"]
    assert sum(m["room_nights"] for m in report["by_month"]) == summary["total_room_nights"]


# --- Exatidão -------------------------------------------------------------------------------


def test_rounding_only_at_serialization(tmp_path):
    """3 x 0.005 = 0.015 -> "0.02". Arredondar linha a linha daria 0.01 x 3 = "0.03"."""
    report = run_cli(tmp_path, [{"reservation_id": f"R-{i}", "amount": "0.005"} for i in range(3)])

    assert report["summary"]["total_amount_brl"] == "0.02"


def test_conversion_is_summed_before_rounding(tmp_path):
    """0.001 USD = 0.00542 BRL; somando 3 vezes = 0.01626 -> "0.02" (arredondar antes daria "0.03")."""
    report = run_cli(tmp_path, [{"reservation_id": f"R-{i}", "currency": "USD", "amount": "0.001"} for i in range(3)])
    assert report["summary"]["total_amount_brl"] == "0.02"


def test_average_nightly_rate(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "amount": "100.00", "checkout_date": "2025-01-12"},  # 2 noites
            {"reservation_id": "R-2", "amount": "100.00", "checkout_date": "2025-01-11"},  # 1 noite
        ],
    )
    assert report["summary"]["total_room_nights"] == 3
    assert report["summary"]["average_nightly_rate_brl"] == "66.67"  # 200 / 3, half-up


def test_average_uses_exact_total_not_rounded(tmp_path):
    """Total exato 0.0299 / 2 noites = 0.01495 -> "0.01".

    Se a média usasse o total já arredondado (0.03 / 2 = 0.015), daria "0.02".
    """
    report = run_cli(
        tmp_path,
        [{"reservation_id": f"R-{i}", "amount": "0.01495", "checkout_date": "2025-01-11"} for i in range(2)],
    )
    assert report["summary"]["total_amount_brl"] == "0.03"
    assert report["summary"]["average_nightly_rate_brl"] == "0.01"


# --- Ranking de hotéis ----------------------------------------------------------------------


def test_top_hotels_tie_breaks_by_hotel_id_ascending(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H03", "amount": "100.00"},
            {"reservation_id": "R-2", "hotel_id": "H01", "amount": "100.00"},
            {"reservation_id": "R-3", "hotel_id": "H02", "amount": "100.00"},
            {"reservation_id": "R-4", "hotel_id": "H04", "amount": "500.00"},
        ],
    )
    assert [h["hotel_id"] for h in report["top_hotels"]] == ["H04", "H01", "H02", "H03"]


def test_top_hotels_aggregates_same_hotel(tmp_path):
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H01", "amount": "100.00", "rooms": "2"},
            {"reservation_id": "R-2", "hotel_id": "H01", "currency": "USD", "amount": "10.00"},
            {"reservation_id": "R-3", "hotel_id": "H02", "amount": "150.00"},
        ],
    )
    assert report["top_hotels"][0] == {
        "hotel_id": "H01",
        "hotel_name": "Hotel Teste",
        "room_nights": 3,
        "total_brl": "154.20",
    }


def test_top_respects_limit(tmp_path):
    rows = [{"reservation_id": f"R-{i}", "hotel_id": f"H{i:02d}", "amount": f"{i}00.00"} for i in range(1, 8)]
    report = run_cli(tmp_path, rows, top=3)

    assert [h["hotel_id"] for h in report["top_hotels"]] == ["H07", "H06", "H05"]


def test_top_larger_than_hotel_count_returns_all(tmp_path):
    rows = [{"reservation_id": f"R-{i}", "hotel_id": f"H{i:02d}"} for i in range(1, 3)]
    report = run_cli(tmp_path, rows, top=10)

    assert len(report["top_hotels"]) == 2


# --- Volume ---------------------------------------------------------------------------------


def test_reads_every_reservation_in_file(tmp_path):
    """total_reservations = número de reservas no arquivo, sem limite de linhas."""
    rows = [{"reservation_id": f"R-{i}"} for i in range(350)]
    report = run_cli(tmp_path, rows)

    assert report["summary"]["total_reservations"] == 350
    assert report["summary"]["confirmed_reservations"] == 350
    assert report["summary"]["total_amount_brl"] == "35000.00"


def test_hotel_name_with_comma_is_preserved(tmp_path):
    report = run_cli(tmp_path, [{"hotel_name": "Hotel Madrid, Gran Vía"}])

    assert report["top_hotels"][0]["hotel_name"] == "Hotel Madrid, Gran Vía"
