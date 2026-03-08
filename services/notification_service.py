def build_tracking_notification(order_row) -> str:
    order_code = order_row["order_code"] or "-"
    product_title = order_row["product_title"] or "-"
    merchant_status = order_row["merchant_status"] or "Mise à jour disponible"
    merchant_tracking_url = order_row["merchant_tracking_url"] or ""
    merchant_order_number = order_row["merchant_order_number"] or "-"
    site_name = order_row["site_name"] or "-"
    user_name = order_row["user_name"] or "Client"

    lines = [
        "AfriPay",
        "",
        f"Bonjour {user_name},",
        "",
        f"Votre commande {order_code} a une nouvelle mise à jour.",
        f"Produit : {product_title}",
        f"Marchand : {site_name}",
        f"Numéro commande marchand : {merchant_order_number}",
        f"Statut marchand : {merchant_status}",
    ]

    if merchant_tracking_url:
        lines.append(f"Suivi : {merchant_tracking_url}")

    lines.extend(
        [
            "",
            "Merci de suivre votre commande via AfriPay.",
        ]
    )

    return "\n".join(lines)


def build_short_sms_notification(order_row) -> str:
    order_code = order_row["order_code"] or "-"
    merchant_status = order_row["merchant_status"] or "maj disponible"
    merchant_tracking_url = order_row["merchant_tracking_url"] or ""

    message = f"AfriPay: commande {order_code}, statut: {merchant_status}."
    if merchant_tracking_url:
        message += f" Suivi: {merchant_tracking_url}"

    return message