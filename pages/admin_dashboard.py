import html
import urllib.parse

import streamlit as st
import streamlit.components.v1 as components

from core.session import logout_admin
from services.admin_service import (
    admin_is_configured,
    verify_admin_password,
)
from services.order_service import list_orders_all, update_merchant_info
from ui.branding import render_sidebar_branding


st.set_page_config(page_title="Dashboard Admin - AfriPay", layout="wide")
render_sidebar_branding()


STATUS_LABELS = {
    "CREEE": "Créée",
    "PAYEE": "Payée",
    "EN_COURS": "En cours",
    "LIVREE": "Livrée",
    "ANNULEE": "Annulée",
}

MERCHANT_STATUS_OPTIONS = [
    "",
    "Commande passée",
    "Paiement effectué",
    "Confirmée par le marchand",
    "En préparation",
    "Expédiée",
    "En transit",
    "Livrée au transitaire",
    "Annulée",
]


def format_xaf(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0

    rounded = int(value) if float(value).is_integer() else int(value) + 1
    return f"{rounded:,}".replace(",", ".")


def format_eur(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0

    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def safe_get(row, key, default=""):
    try:
        value = row[key]
        return value if value not in (None, "") else default
    except Exception:
        return default


def clean_product_url(url):
    if not url:
        return ""
    return str(url).split("?")[0].strip()


def get_product_label(row, default="—"):
    value = safe_get(row, "product_title", "")
    if value:
        return value

    value = safe_get(row, "product_name", "")
    if value:
        return value

    return default


def format_original_merchant_amount(order):
    merchant_total_amount = float(safe_get(order, "merchant_total_amount", 0) or 0)
    merchant_currency = str(
        safe_get(order, "merchant_currency", "EUR") or "EUR"
    ).strip().upper()

    if merchant_currency == "XAF":
        return f"{format_xaf(merchant_total_amount)} XAF"

    if merchant_currency == "EUR":
        return f"{format_eur(merchant_total_amount)} €"

    return f"{format_eur(merchant_total_amount)} {merchant_currency}"


def format_merchant_amount(order):
    merchant_total_amount = float(safe_get(order, "merchant_total_amount", 0) or 0)
    merchant_currency = str(
        safe_get(order, "merchant_currency", "EUR") or "EUR"
    ).strip().upper()
    total_xaf = float(safe_get(order, "total_xaf", 0) or 0)
    total_eur = float(safe_get(order, "total_to_pay_eur", 0) or 0)

    if merchant_currency == "XAF":
        return (
            f"{format_xaf(merchant_total_amount)} XAF "
            f"({format_eur(total_eur)} EUR)"
        )

    if merchant_currency == "EUR":
        return (
            f"{format_xaf(total_xaf)} XAF "
            f"({format_eur(merchant_total_amount)} EUR)"
        )

    return (
        f"{format_xaf(total_xaf)} XAF "
        f"({format_eur(merchant_total_amount)} {merchant_currency})"
    )


def build_notification_message(order):
    client_name = safe_get(order, "user_name", "Client")
    order_code = safe_get(order, "order_code", "")
    site_name = safe_get(order, "site_name", "Marchand")

    product_url = clean_product_url(safe_get(order, "product_url", ""))
    merchant_confirmation_url = clean_product_url(
        safe_get(order, "merchant_confirmation_url", "")
    )

    merchant_order_number = safe_get(order, "merchant_order_number", "")
    merchant_tracking_url = safe_get(order, "merchant_tracking_url", "")
    merchant_purchase_date = safe_get(order, "merchant_purchase_date", "")
    merchant_status = safe_get(order, "merchant_status", "")
    merchant_notes = safe_get(order, "merchant_notes", "")

    merchant_amount_text = format_merchant_amount(order)

    lines = [
        f"Bonjour {client_name},",
        "",
        "Votre commande AfriPay a été mise à jour ✅",
    ]

    if order_code:
        lines.append(f"Référence AfriPay : {order_code}")

    if site_name:
        lines.append(f"Marchand : {site_name}")

    if merchant_amount_text:
        lines.append(f"Montant marchand : {merchant_amount_text}")

    if merchant_order_number:
        lines.append(f"Numéro de commande marchand : {merchant_order_number}")

    if merchant_purchase_date:
        lines.append(f"Date d'achat : {merchant_purchase_date}")

    if merchant_status:
        lines.append(f"Statut marchand : {merchant_status}")

    if product_url:
        lines.append(f"Lien produit : {product_url}")

    if merchant_confirmation_url and merchant_confirmation_url != product_url:
        lines.append(f"Lien de confirmation : {merchant_confirmation_url}")

    if merchant_tracking_url:
        lines.append(f"Lien de suivi : {merchant_tracking_url}")

    if merchant_notes:
        lines.append(f"Note AfriPay : {merchant_notes}")

    lines.append("")
    lines.append(
        "Rappel : le dédouanement et la livraison finale restent sous la responsabilité de votre transitaire / agent."
    )
    lines.append("Merci de suivre votre commande avec votre transitaire.")
    lines.append("")
    lines.append("Équipe AfriPay")
    lines.append("")
    lines.append("🌍 AfriPay Afrika")
    lines.append("Facilitateur des paiements internationaux")
    lines.append("Essayez AfriPay pour vos prochaines commandes :")
    lines.append("https://afripay-kvty.onrender.com")

    whatsapp_message = "\n".join(lines)

    sms_parts = [f"AfriPay {order_code}" if order_code else "AfriPay"]

    if merchant_status:
        sms_parts.append(f"Statut: {merchant_status}")

    if merchant_order_number:
        sms_parts.append(f"N° marchand: {merchant_order_number}")

    if merchant_tracking_url:
        sms_parts.append(f"Suivi: {merchant_tracking_url}")

    sms_message = " | ".join(sms_parts)

    return whatsapp_message, sms_message


def build_whatsapp_link(phone, message):
    if not phone:
        return None

    normalized_phone = (
        str(phone)
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{normalized_phone}?text={encoded_message}"


def render_copy_box(title, text_value, box_id, button_label):
    escaped_text = html.escape(text_value)

    html_block = f"""
    <div style="border:1px solid rgba(250,250,250,0.12); border-radius:12px; padding:14px; background:rgba(255,255,255,0.02);">
        <div style="font-weight:700; font-size:18px; margin-bottom:10px; color:white;">
            {html.escape(title)}
        </div>

        <textarea id="{box_id}" readonly
            style="
                width:100%;
                height:260px;
                padding:12px;
                border-radius:10px;
                border:1px solid rgba(250,250,250,0.12);
                background:#0f172a;
                color:white;
                resize:vertical;
                font-size:14px;
                line-height:1.45;
                box-sizing:border-box;
            ">{escaped_text}</textarea>

        <button
            onclick="
                const text = document.getElementById('{box_id}').value;
                navigator.clipboard.writeText(text).then(() => {{
                    const msg = document.getElementById('{box_id}_msg');
                    msg.innerText = 'Copié dans le presse-papiers ✅';
                    setTimeout(() => msg.innerText = '', 2200);
                }});
            "
            style="
                margin-top:10px;
                background:#16a34a;
                color:white;
                border:none;
                padding:10px 14px;
                border-radius:10px;
                cursor:pointer;
                font-weight:700;
            "
        >
            {html.escape(button_label)}
        </button>

        <div id="{box_id}_msg" style="margin-top:8px; color:#4ade80; font-size:14px;"></div>
    </div>
    """

    components.html(html_block, height=380)


def render_notification_block(order):
    merchant_order_number = safe_get(order, "merchant_order_number", "")
    merchant_confirmation_url = safe_get(order, "merchant_confirmation_url", "")
    merchant_tracking_url = safe_get(order, "merchant_tracking_url", "")
    merchant_purchase_date = safe_get(order, "merchant_purchase_date", "")
    merchant_status = safe_get(order, "merchant_status", "")
    merchant_notes = safe_get(order, "merchant_notes", "")

    has_notification_content = any(
        [
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
            merchant_status,
            merchant_notes,
        ]
    )

    st.markdown("## Notifications client")

    if not has_notification_content:
        st.info("Aucune notification AfriPay prête à envoyer. Ajoutez au moins une information marchand.")
        return

    whatsapp_message, sms_message = build_notification_message(order)
    client_phone = safe_get(order, "user_phone", "")
    whatsapp_link = build_whatsapp_link(client_phone, whatsapp_message)

    st.success("Notification AfriPay prête à envoyer")

    col1, col2 = st.columns(2)

    with col1:
        render_copy_box(
            title="Message WhatsApp",
            text_value=whatsapp_message,
            box_id=f"wa_box_{safe_get(order, 'id', '0')}",
            button_label="📋 Copier WhatsApp",
        )

        if whatsapp_link:
            st.link_button(
                "📲 Ouvrir WhatsApp avec le message",
                whatsapp_link,
                use_container_width=True,
            )

    with col2:
        render_copy_box(
            title="Message SMS",
            text_value=sms_message,
            box_id=f"sms_box_{safe_get(order, 'id', '0')}",
            button_label="📋 Copier SMS",
        )


def render_order_card(order):
    order_id = safe_get(order, "id", "")
    order_code = safe_get(order, "order_code", f"CMD-{order_id}")

    user_name = safe_get(order, "user_name", "Client")
    user_phone = safe_get(order, "user_phone", "—")
    user_email = safe_get(order, "user_email", "—")

    site_name = safe_get(order, "site_name", "—")
    product_title = get_product_label(order)
    product_url = clean_product_url(safe_get(order, "product_url", ""))
    delivery_address = safe_get(order, "delivery_address", "—")

    total_to_pay_eur = safe_get(order, "total_to_pay_eur", 0)
    total_xaf = safe_get(order, "total_xaf", 0)

    order_status = safe_get(order, "order_status", "")
    status_label = STATUS_LABELS.get(order_status, order_status or "—")

    merchant_order_number = safe_get(order, "merchant_order_number", "")
    merchant_confirmation_url = safe_get(order, "merchant_confirmation_url", "")
    merchant_tracking_url = safe_get(order, "merchant_tracking_url", "")
    merchant_purchase_date = safe_get(order, "merchant_purchase_date", "")
    merchant_status = safe_get(order, "merchant_status", "")
    merchant_notes = safe_get(order, "merchant_notes", "")

    title = f"{order_code} — {user_name}"

    with st.expander(title):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(f"**Client :** {user_name}")
            st.markdown(f"**Téléphone :** {user_phone}")
            st.markdown(f"**Email :** {user_email}")
            st.markdown(f"**Statut AfriPay :** {status_label}")

        with c2:
            st.markdown(f"**Marchand :** {site_name}")
            st.markdown(f"**Produit :** {product_title}")
            st.markdown(f"**Montant XAF :** {format_xaf(total_xaf)} XAF")
            st.markdown(f"**Montant EUR :** {format_eur(total_to_pay_eur)} €")

        with c3:
            st.markdown(
                f"**Montant d'origine marchand :** {format_original_merchant_amount(order)}"
            )
            st.markdown("**Adresse transitaire :**")
            st.write(delivery_address)

            if product_url:
                st.markdown(f"**Lien produit :** {product_url}")

        st.markdown("---")
        st.markdown("## Informations marchand")

        with st.form(f"merchant_form_{order_id}"):
            f1, f2 = st.columns(2)

            with f1:
                merchant_order_number_input = st.text_input(
                    "Numéro commande marchand",
                    value=merchant_order_number,
                )
                merchant_confirmation_url_input = st.text_input(
                    "Lien confirmation",
                    value=merchant_confirmation_url,
                )
                merchant_tracking_url_input = st.text_input(
                    "Lien suivi",
                    value=merchant_tracking_url,
                )

            with f2:
                merchant_purchase_date_input = st.text_input(
                    "Date d'achat",
                    value=merchant_purchase_date,
                    placeholder="YYYY-MM-DD",
                )

                index = 0
                if merchant_status in MERCHANT_STATUS_OPTIONS:
                    index = MERCHANT_STATUS_OPTIONS.index(merchant_status)

                merchant_status_input = st.selectbox(
                    "Statut marchand",
                    MERCHANT_STATUS_OPTIONS,
                    index=index,
                )

            merchant_notes_input = st.text_area(
                "Notes marchand / AfriPay",
                value=merchant_notes,
                placeholder="Exemple : commande confirmée par email, colis annoncé pour la semaine prochaine...",
            )

            submitted = st.form_submit_button(
                "Enregistrer les informations marchand",
                use_container_width=True,
            )

            if submitted:
                update_merchant_info(
                    order_id=order_id,
                    merchant_order_number=merchant_order_number_input,
                    merchant_confirmation_url=merchant_confirmation_url_input,
                    merchant_tracking_url=merchant_tracking_url_input,
                    merchant_purchase_date=merchant_purchase_date_input,
                    merchant_status=merchant_status_input,
                    merchant_notes=merchant_notes_input,
                )
                st.success("Informations marchand enregistrées avec succès.")
                st.rerun()

        st.markdown("---")
        render_notification_block(
            {
                **order,
                "product_url": product_url,
                "merchant_order_number": merchant_order_number_input if "merchant_order_number_input" in locals() else merchant_order_number,
                "merchant_confirmation_url": merchant_confirmation_url_input if "merchant_confirmation_url_input" in locals() else merchant_confirmation_url,
                "merchant_tracking_url": merchant_tracking_url_input if "merchant_tracking_url_input" in locals() else merchant_tracking_url,
                "merchant_purchase_date": merchant_purchase_date_input if "merchant_purchase_date_input" in locals() else merchant_purchase_date,
                "merchant_status": merchant_status_input if "merchant_status_input" in locals() else merchant_status,
                "merchant_notes": merchant_notes_input if "merchant_notes_input" in locals() else merchant_notes,
            }
        )


def admin_gate():
    if st.session_state.get("admin_logged_in"):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.success("Admin connecté ✅")

        with col2:
            if st.button("Déconnexion Admin"):
                logout_admin()
                st.rerun()

        return True

    st.title("Connexion Dashboard Admin")
    password = st.text_input("Mot de passe admin", type="password")

    if st.button("Se connecter au Dashboard Admin"):
        if not admin_is_configured():
            st.error("Admin non configuré.")
            return False

        if verify_admin_password(password):
            st.session_state["admin_logged_in"] = True
            st.success("Admin connecté ✅")
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")

    st.info("Cette page est réservée à l'administration AfriPay.")
    return False


def main():
    if not admin_gate():
        return

    st.title("Dashboard Admin AfriPay")

    orders = list_orders_all()

    total_orders = len(orders)
    paid_orders = 0
    in_progress_orders = 0
    delivered_orders = 0

    total_volume_xaf = 0.0
    total_volume_eur = 0.0

    for order in orders:
        status = str(safe_get(order, "order_status", "")).strip().upper()
        total_volume_xaf += float(safe_get(order, "total_xaf", 0) or 0)
        total_volume_eur += float(safe_get(order, "total_to_pay_eur", 0) or 0)

        if status == "PAYEE":
            paid_orders += 1
        elif status == "EN_COURS":
            in_progress_orders += 1
        elif status == "LIVREE":
            delivered_orders += 1

    average_basket_xaf = 0
    average_basket_eur = 0.0
    if total_orders > 0:
        average_basket_xaf = total_volume_xaf / total_orders
        average_basket_eur = total_volume_eur / total_orders

    max_order_xaf = 0
    max_order_eur = 0.0
    if orders:
        max_order_xaf = max(float(safe_get(order, "total_xaf", 0) or 0) for order in orders)
        max_order_eur = max(float(safe_get(order, "total_to_pay_eur", 0) or 0) for order in orders)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total commandes", total_orders)
    c2.metric("Payées", paid_orders)
    c3.metric("En cours", in_progress_orders)
    c4.metric("Livrées", delivered_orders)
    c5.metric("Volume XAF", f"{format_xaf(total_volume_xaf)} XAF")

    c6, c7 = st.columns(2)
    c6.metric("Panier moyen XAF", f"{format_xaf(average_basket_xaf)} XAF")
    c7.metric("Commande max XAF", f"{format_xaf(max_order_xaf)} XAF")

    st.markdown("### Ligne financière EUR")

    c8, c9, c10 = st.columns(3)
    c8.metric("Volume EUR", f"{format_eur(total_volume_eur)} €")
    c9.metric("Panier moyen EUR", f"{format_eur(average_basket_eur)} €")
    c10.metric("Commande max EUR", f"{format_eur(max_order_eur)} €")

    st.markdown("---")
    st.subheader("Liste des commandes")

    if not orders:
        st.info("Aucune commande disponible.")
        return

    for order in orders:
        render_order_card(order)


if __name__ == "__main__":
    main()