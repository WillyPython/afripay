from datetime import date, timedelta

from afribooks_btw.engine.expense_summary_service import (
    get_operating_expense_summary,
)
from afribooks_btw.engine.invoice_history_service import list_invoice_history


def _filter_rows_by_period(
    rows: list[dict],
    start_date: date,
    end_date: date,
) -> list[dict]:
    filtered_rows = []

    for row in rows:
        row_date = row.get("invoice_date")

        if row_date and start_date <= row_date <= end_date:
            filtered_rows.append(row)

    return filtered_rows


def get_period_metrics(
    start_date: date,
    end_date: date,
) -> dict:
    rows = list_invoice_history(limit=1000)

    filtered_rows = _filter_rows_by_period(
        rows=rows,
        start_date=start_date,
        end_date=end_date,
    )

    total_vat = sum(float(row.get("total_vat_eur") or 0) for row in filtered_rows)
    total_gross = sum(float(row.get("total_gross_eur") or 0) for row in filtered_rows)

    expense_summary = get_operating_expense_summary(
        start_date=start_date,
        end_date=end_date,
    )

    other_charges = float(expense_summary.get("total_expenses") or 0)
    real_net = total_gross - total_vat - other_charges

    return {
        "invoices_count": len(filtered_rows),
        "gross": round(total_gross, 2),
        "vat": round(total_vat, 2),
        "other_charges": round(other_charges, 2),
        "net": round(real_net, 2),
    }


def get_previous_period(
    start_date: date,
    end_date: date,
) -> tuple[date, date]:
    period_length = end_date - start_date

    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - period_length

    return previous_start, previous_end


def get_current_and_previous_period_metrics(
    start_date: date,
    end_date: date,
) -> dict:
    previous_start, previous_end = get_previous_period(
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "current": get_period_metrics(start_date, end_date),
        "previous": get_period_metrics(previous_start, previous_end),
        "current_period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "previous_period": {
            "start_date": previous_start,
            "end_date": previous_end,
        },
    }
