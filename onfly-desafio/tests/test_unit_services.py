"""Testes adicionais: unidades de serviço isoladas (sem subprocess)."""

from datetime import date
from decimal import Decimal

import pytest

from onfly_report.services.currency_converter import convert_to_brl
from onfly_report.services.report_builder import format_money
from onfly_report.services.status_policy import is_billable
from onfly_report.services.stay_calculator import calculate_room_nights

RATES = {"BRL": Decimal("1.000000"), "USD": Decimal("5.420000"), "EUR": Decimal("5.880000")}


# --- Noites ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("checkin", "checkout", "rooms", "expected"),
    [
        (date(2025, 1, 10), date(2025, 1, 13), 1, 3),  # exemplo do enunciado
        (date(2025, 1, 30), date(2025, 2, 2), 1, 3),  # virada de mês
        (date(2024, 12, 30), date(2025, 1, 2), 1, 3),  # virada de ano
        (date(2024, 2, 28), date(2024, 3, 1), 1, 2),  # ano bissexto
        (date(2025, 2, 28), date(2025, 3, 1), 1, 1),  # ano não bissexto
        (date(2025, 1, 10), date(2025, 1, 13), 3, 9),  # multiplica pelos quartos
        (date(2025, 1, 10), date(2025, 1, 11), 1, 1),  # diária única
    ],
)
def test_room_nights(checkin, checkout, rooms, expected):
    assert calculate_room_nights(checkin, checkout, rooms) == expected


# --- Câmbio ---------------------------------------------------------------------------------


def test_brl_keeps_amount():
    assert convert_to_brl(Decimal("123.45"), "BRL", RATES) == Decimal("123.45")


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("100.00", "USD", "542.00"),
        ("100.00", "EUR", "588.00"),
        ("0.10", "USD", "0.542"),
    ],
)
def test_conversion_multiplies_by_rate(amount, currency, expected):
    assert convert_to_brl(Decimal(amount), currency, RATES) == Decimal(expected)


def test_conversion_returns_exact_decimal():
    """Sem float: o resultado é Decimal e não perde casas antes da serialização."""
    result = convert_to_brl(Decimal("19.99"), "USD", RATES)
    assert isinstance(result, Decimal)
    assert result == Decimal("108.3458")


# --- Serialização de dinheiro ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", "0.00"),
        ("1234.5", "1234.50"),
        ("1234567.891", "1234567.89"),  # sem separador de milhar
        ("0.005", "0.01"),  # half-up, não half-even
        ("0.015", "0.02"),
        ("0.025", "0.03"),  # half-even daria 0.02
        ("2.675", "2.68"),  # com float daria 2.67
        ("10.004", "10.00"),
    ],
)
def test_format_money_half_up(value, expected):
    assert format_money(Decimal(value)) == expected


# --- Status ---------------------------------------------------------------------------------


def test_only_confirmed_is_billable():
    assert is_billable("CONFIRMED") is True
    assert is_billable("CANCELLED") is False
    assert is_billable("NO_SHOW") is False


@pytest.mark.parametrize("status", ["PENDING", "REFUNDED", ""])
def test_unknown_status_is_not_billable(status):
    """Regra: só CONFIRMED é faturável. Qualquer outro status fica fora dos totais."""
    assert is_billable(status) is False
