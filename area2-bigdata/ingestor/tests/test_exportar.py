from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from ingestor.exportar import formatar

BRT = timezone(timedelta(hours=-3))


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, ""),
        (True, "true"),
        (False, "false"),
        (Decimal("2.87"), "2.87"),
        (Decimal("300.00"), "300"),
        (Decimal("0.5"), "0.5"),
        (42, "42"),
        (datetime(2026, 11, 7, 12, 0, tzinfo=BRT), "2026-11-07 15:00:00"),  # convertido para UTC
        (datetime(2026, 11, 7, 12, 0), "2026-11-07 12:00:00"),  # horário local fica como está
        (datetime(2026, 11, 7, 15, 0, tzinfo=UTC), "2026-11-07 15:00:00"),
        (date(2026, 11, 7), "2026-11-07"),
    ],
)
def test_formatar_para_csv(valor, esperado):
    assert formatar(valor) == esperado
