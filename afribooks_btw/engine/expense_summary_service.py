from decimal import Decimal

from data.database import get_cursor


def get_operating_expense_summary(
    start_date,
    end_date,
) -> dict:
    """
    Returns operating expense summary for AfriBooks dashboard.

    OTHER CHARGES = operating expenses from ledger_entries.
    """

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(ABS(amount_eur)), 0) AS total_expenses,
                COALESCE(SUM(net_amount_eur), 0) AS total_net_expenses,
                COALESCE(SUM(vat_amount), 0) AS total_expense_vat
            FROM ledger_entries
            WHERE entry_date >= %s
              AND entry_date <= %s
              AND type = 'EXPENSE'
              AND is_operating = TRUE
              AND cash_flow_group = 'OPERATING_EXPENSE'
            """,
            (start_date, end_date),
        )

        row = cur.fetchone()

    return {
        "total_expenses": Decimal(row["total_expenses"] or 0),
        "total_net_expenses": Decimal(row["total_net_expenses"] or 0),
        "total_expense_vat": Decimal(row["total_expense_vat"] or 0),
    }
