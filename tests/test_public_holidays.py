import copy
from datetime import date

import pytest

from app.services.public_holidays import is_known_state, is_public_holiday
from seed.build_db import validate_tariff_fields
from tests.test_demand_model import VALID_SEED

SEEDED_STATES = ["NSW", "VIC", "QLD", "SA", "ACT", "NT"]


@pytest.mark.parametrize("state", SEEDED_STATES)
def test_christmas_every_seeded_state(state):
    assert is_public_holiday(state, date(2026, 12, 25)) is True


def test_melbourne_cup_is_victoria_only():
    assert is_public_holiday("VIC", date(2026, 11, 3)) is True
    assert is_public_holiday("NSW", date(2026, 11, 3)) is False


@pytest.mark.parametrize("state", SEEDED_STATES)
def test_ordinary_day_is_not_a_holiday(state):
    assert is_public_holiday(state, date(2026, 3, 10)) is False


def test_known_states():
    assert all(is_known_state(state) for state in SEEDED_STATES)
    assert is_known_state("XX") is False


def test_seed_load_rejects_unknown_state():
    seed = copy.deepcopy(VALID_SEED)
    seed["dnsps"][0]["state"] = "XX"
    with pytest.raises(ValueError, match="XX"):
        validate_tariff_fields([seed])
