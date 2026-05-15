from data.database import get_cursor


def list_invoice_history(
    limit: int = 200,
) -> list[dict]:
    """
    Returns latest invoices for AfriBooks history UI.
    """

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                invoice_number,
                invoice_type,
                invoice_date,
                partner_name,
                partner_vat_number,
                currency,
                total_net_eur,
                total_vat_eur,
                total_gross_eur,
                payment_status,
                source,
                note
            FROM invoices
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )

        rows = cur.fetchall()

    return [dict(row) for row in rows]
