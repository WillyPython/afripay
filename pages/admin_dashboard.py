import html
import urllib.parse

import streamlit as st
import streamlit.components.v1 as components

from core.session import logout_admin
from services.admin_service import (
    admin_is_configured,
    verify_admin_password,
)
from services.order_service import (
    ORDER_STATUS_OPTIONS,
    ORDER_STATUS_LABELS,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_PROOF_SENT,
    PAYMENT_STATUS_PROOF_RECEIVED,
    PAYMENT_STATUS_CONFIRMED,
    PAYMENT_STATUS_REJECTED,
    get_payment_status_label,
    list_orders_all,
    update_merchant_info,
    update_order_status,
    mark_payment_proof_received,
    confirm_payment,
    reject_payment,
)
from ui.branding import render_sidebar_branding


OFFICIAL_PUBLIC_URL = "https://afripayafrika.com"


st.set_page_config(page_title="Dashboard Admin - AfriPay", layout="wide")
render_sidebar_branding()


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


STATUS_STYLES = {
    "CREEE": {"label": "Créée", "color": "#94a3b8", "dot": "⚪"},
    "PAYEE": {"label": "Payée", "color": "#22c55e", "dot": "🟢"},
    "EN_COURS": {"label": "En cours", "color": "#facc15", "dot": "🟡"},
    "LIVREE": {"label": "Livrée", "color": "#3b82f6", "dot": "🔵"},
    "ANNULEE": {"label": "Annulée", "color": "#ef4444", "dot": "🔴"},
}


PAYMENT_STATUS_STYLES = {
    PAYMENT_STATUS_PENDING: {"label": "En attente de paiement", "color": "#94a3b8", "dot": "⚪"},
    PAYMENT_STATUS_PROOF_SENT: {"label": "Preuve en cours d'envoi", "color": "#f59e0b", "dot": "🟠"},
    PAYMENT_STATUS_PROOF_RECEIVED: {"label": "Preuve reçue - vérification en cours", "color": "#3b82f6", "dot": "🔵"},
    PAYMENT_STATUS_CONFIRMED: {"label": "Paiement confirmé", "color": "#22c55e", "dot": "🟢"},
    PAYMENT_STATUS_REJECTED: {"label": "Paiement rejeté", "color": "#ef4444", "dot": "🔴"},
}


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


def get_status_meta(order_status):
    status = str(order_status or "").strip().upper()
    return STATUS_STYLES.get(
        status,
        {"label": status or "—", "color": "#94a3b8", "dot": "⚪"},
    )


def get_payment_status_meta(payment_status):
    status = str(payment_status or "").strip().upper()
    if status in PAYMENT_STATUS_STYLES:
        return PAYMENT_STATUS_STYLES[status]

    label = get_payment_status_label(status or "PENDING")
    return {"label": label, "color": "#94a3b8", "dot": "⚪"}


def render_status_badge(order_status):
    meta = get_status_meta(order_status)
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:8px 12px;
            border-radius:999px;
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.10);
            font-weight:700;
            color:{meta['color']};
            margin-top:4px;
            margin-bottom:8px;
        ">
            {meta['dot']} {html.escape(meta['label'])}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_payment_status_badge(payment_status):
    meta = get_payment_status_meta(payment_status)
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:8px 12px;
            border-radius:999px;
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.10);
            font-weight:700;
            color:{meta['color']};
            margin-top:4px;
            margin-bottom:8px;
        ">
            {meta['dot']} {html.escape(meta['label'])}
        </div>
        """,
        unsafe_allow_html=True,
    )


def infer_tracking_label(tracking_url: str) -> str:
    url = str(tracking_url or "").strip().lower()

    if not url:
        return "Lien de suivi"

    carrier_keywords = [
        "dhl",
        "ups",
        "fedex",
        "colissimo",
        "chronopost",
        "gls",
        "dpd",
        "usps",
        "royalmail",
        "yanwen",
        "cainiao",
        "4px",
        "ems",
        "aramex",
    ]

    if any(keyword in url for keyword in carrier_keywords):
        return "Lien de suivi transporteur"

    return "Lien de suivi marchand"


def build_notification_message(order):
    client_name = safe_get(order, "user_name", "Client")
    order_code = safe_get(order, "order_code", "")
    order_status = str(safe_get(order, "order_status", "")).strip().upper()
    order_status_label = ORDER_STATUS_LABELS.get(order_status, order_status or "—")

    merchant_confirmation_url = clean_product_url(
        safe_get(order, "merchant_confirmation_url", "")
    )
    merchant_tracking_url = clean_product_url(
        safe_get(order, "merchant_tracking_url", "")
    )
    merchant_tracking_label = infer_tracking_label(merchant_tracking_url)

    merchant_order_number = safe_get(order, "merchant_order_number", "")
    merchant_status = safe_get(order, "merchant_status", "")
    merchant_notes = safe_get(order, "merchant_notes", "")

    lines = [
        f"Bonjour {client_name} 👋",
        "",
        "📦 Votre commande AfriPay a été mise à jour",
        "",
    ]

    if order_code:
        lines.append(f"🔖 Référence AfriPay : {order_code}")

    if merchant_status:
        lines.append(f"📍 Statut marchand : {merchant_status}")
    else:
        lines.append(f"📍 Statut AfriPay : {order_status_label}")

    if merchant_order_number:
        lines.append(f"🧾 N° marchand : {merchant_order_number}")

    if merchant_confirmation_url:
        lines.extend(
            [
                "",
                "🔗 Lien de confirmation :",
                merchant_confirmation_url,
            ]
        )

    if merchant_tracking_url:
        lines.extend(
            [
                "",
                f"🔗 {merchant_tracking_label} :",
                merchant_tracking_url,
            ]
        )

    if merchant_notes:
        lines.extend(
            [
                "",
                f"📝 Note AfriPay : {merchant_notes}",
            ]
        )

    lines.extend(
        [
            "",
            "⚠️ Rappel :",
            "Le dédouanement et la livraison finale restent sous la responsabilité de votre transitaire / agent.",
            "",
            "Merci pour votre confiance.",
            "AfriPay Afrika",
        ]
    )

    whatsapp_message = "\n".join(lines)

    sms_parts = [f"AfriPay {order_code}" if order_code else "AfriPay"]

    if merchant_status:
        sms_parts.append(f"Statut: {merchant_status}")
    elif order_status_label:
        sms_parts.append(f"Statut: {order_status_label}")

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
    merchant_status = safe_get(order, "merchant_status", "")
    merchant_notes = safe_get(order, "merchant_notes", "")

    has_notification_content = any(
        [
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
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


def render_payment_actions(order):
    order_code = safe_get(order, "order_code", "")
    payment_status = str(safe_get(order, "payment_status", "PENDING")).strip().upper()

    st.markdown("## Gestion paiement")

    render_payment_status_badge(payment_status)
    st.caption(get_payment_status_label(payment_status))

    note_default = safe_get(order, "payment_admin_note", "")
    admin_note = st.text_area(
        "Note admin paiement",
        value=note_default,
        key=f"payment_note_{order_code}",
        placeholder="Exemple : capture reçue sur WhatsApp, montant vérifié, preuve incomplète, etc.",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(f"📥 Preuve reçue #{order_code}", key=f"proof_received_{order_code}", use_container_width=True):
            if mark_payment_proof_received(order_code, admin_note):
                st.success(f"{order_code} → PROOF_RECEIVED")
                st.rerun()
            else:
                st.info("Transition non appliquée : vérifie le statut actuel de paiement.")

    with col2:
        if st.button(f"✅ Confirmer #{order_code}", key=f"confirm_{order_code}", use_container_width=True):
            if confirm_payment(order_code, admin_note):
                st.success(f"{order_code} → CONFIRMED")
                st.rerun()
            else:
                st.info("Transition non appliquée : vérifie le statut actuel de paiement.")

    with col3:
        if st.button(f"❌ Rejeter #{order_code}", key=f"reject_{order_code}", use_container_width=True):
            if reject_payment(order_code, admin_note):
                st.warning(f"{order_code} → REJECTED")
                st.rerun()
            else:
                st.info("Transition non appliquée : vérifie le statut actuel de paiement.")


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

    order_status = str(safe_get(order, "order_status", "")).strip().upper()
    status_label = ORDER_STATUS_LABELS.get(order_status, order_status or "—")
    payment_status = str(safe_get(order, "payment_status", "PENDING")).strip().upper()

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

            st.markdown("**Statut AfriPay :**")
            render_status_badge(order_status)
            st.caption(status_label)

            st.markdown("**Statut paiement :**")
            render_payment_status_badge(payment_status)
            st.caption(get_payment_status_label(payment_status))

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
        render_payment_actions(order)

        st.markdown("---")
        st.markdown("## Gestion commande et marchand")

        with st.form(f"merchant_form_{order_id}"):
            top_left, top_right = st.columns(2)

            with top_left:
                current_order_status_index = 0
                if order_status in ORDER_STATUS_OPTIONS:
                    current_order_status_index = ORDER_STATUS_OPTIONS.index(order_status)

                order_status_input = st.selectbox(
                    "Statut AfriPay",
                    ORDER_STATUS_OPTIONS,
                    index=current_order_status_index,
                )

                merchant_order_number_input = st.text_input(
                    "Numéro commande marchand",
                    value=merchant_order_number,
                )

                merchant_confirmation_url_input = st.text_input(
                    "Lien de confirmation",
                    value=merchant_confirmation_url,
                )

                merchant_tracking_url_input = st.text_input(
                    "Lien de suivi marchand / transporteur",
                    value=merchant_tracking_url,
                )

            with top_right:
                merchant_purchase_date_input = st.text_input(
                    "Date d'achat",
                    value=merchant_purchase_date,
                    placeholder="YYYY-MM-DD",
                )

                merchant_status_index = 0
                if merchant_status in MERCHANT_STATUS_OPTIONS:
                    merchant_status_index = MERCHANT_STATUS_OPTIONS.index(merchant_status)

                merchant_status_input = st.selectbox(
                    "Statut marchand",
                    MERCHANT_STATUS_OPTIONS,
                    index=merchant_status_index,
                )

            merchant_notes_input = st.text_area(
                "Notes marchand / AfriPay",
                value=merchant_notes,
                placeholder="Exemple : commande confirmée par email, colis annoncé pour la semaine prochaine...",
            )

            submitted = st.form_submit_button(
                "Enregistrer les informations",
                use_container_width=True,
            )

            if submitted:
                update_order_status(
                    order_id=order_id,
                    order_status=order_status_input,
                )

                update_merchant_info(
                    order_id=order_id,
                    merchant_order_number=merchant_order_number_input,
                    merchant_confirmation_url=merchant_confirmation_url_input,
                    merchant_tracking_url=merchant_tracking_url_input,
                    merchant_purchase_date=merchant_purchase_date_input,
                    merchant_status=merchant_status_input,
                    merchant_notes=merchant_notes_input,
                )

                st.success("Informations commande et marchand enregistrées avec succès.")
                st.rerun()

        st.markdown("---")
        render_notification_block(
            {
                **order,
                "order_status": order_status_input if "order_status_input" in locals() else order_status,
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