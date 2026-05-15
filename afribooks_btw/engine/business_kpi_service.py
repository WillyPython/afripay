from data.database import get_cursor


def get_business_kpis() -> dict:
    """
    Returns real business KPIs from invoices table
    for AfriBooks Smart Business OS.
    """

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) AS invoices_count,
                COALESCE(SUM(total_gross_eur), 0) AS gross,
                COALESCE(SUM(total_vat_eur), 0) AS vat,
                COALESCE(SUM(total_net_eur), 0) AS net
            FROM invoices
            """
        )

        row = cur.fetchone()

    data = dict(row) if row else {}

    invoices_count = int(data.get("invoices_count") or 0)
    gross = float(data.get("gross") or 0.0)
    vat = float(data.get("vat") or 0.0)
    net = float(data.get("net") or 0.0)

    return {
        "invoices_count": invoices_count,
        "gross": round(gross, 2),
        "vat": round(vat, 2),
        "other_charges": 0.0,
        "net": round(net, 2),
    }

