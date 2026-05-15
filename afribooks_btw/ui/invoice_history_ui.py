import streamlit as st
from datetime import date, timedelta

from afribooks_btw.engine.expense_summary_service import (
    get_operating_expense_summary,
)
from afribooks_btw.engine.invoice_history_service import list_invoice_history
from afribooks_btw.engine.trend_period_service import (
    get_current_and_previous_period_metrics,
)
from afribooks_btw.ui.manager_widget_ui import render_manager_widget_ui
from afribooks_btw.ui.result_widget_ui import render_result_widget_ui
from afribooks_btw.ui.smart_trend_widget_ui import render_smart_trend_widget_ui
from afribooks_btw.engine.session_service import get_afribooks_language


TEXTS = {
    "nl": {
        "title": "Factuurgeschiedenis",
        "caption": "Zoek, filter, analyseer en exporteer uw facturen.",
        "access": "Financial Companion toegang",
        "test_plan": "Testplan",
        "mode": "Financial Companion modus",
        "trend_settings": "Trendvergelijking",
        "free_msg": "Voor meer comfort, opvolging en vertrouwen in uw beheer kunt u de PREMIUM-plannen ontdekken.",
        "premium_msg": "Zet uw Financial Companion AI-ervaring voort met PREMIUM PLUS.",
        "premium_trend_msg": "Slimme vergelijkingen zijn beschikbaar in PREMIUM om uw activiteit beter te sturen.",
        "comparison_period": "Vergelijkingsperiode",
        "filters": "Dynamische filters",
        "fiscal_periodicity": "Fiscale periode",
        "payment_status": "Betalingsstatus",
        "country": "Land",
        "search_period": "Zoekperiode",
        "start_date": "Startdatum",
        "end_date": "Einddatum",
        "search": "Zoek klant, factuur, BTW, omschrijving...",
        "vat_filters": "BTW- en bedrijfsfilters",
        "partner_type": "Partnertype",
        "vat_treatment": "BTW-behandeling",
        "invoice_type": "Factuurtype",
        "load_error": "Kan factuurgeschiedenis niet laden",
        "invoices": "FACTUREN",
        "gross": "OMZET",
        "vat": "BTW",
        "charges": "ANDERE KOSTEN",
        "net": "NETTO RESULTAAT",
        "no_results": "Geen facturen gevonden voor de geselecteerde filters.",
        "results": "Resultaten",
        "exports": "Geplande globale exports",
        "pdf": "Globale PDF-export",
        "csv": "Globale CSV-export",
        "active_filters": "Actieve filters",
        "trend_mode": "Trendvergelijking",
        "to": "tot",
    },
    "fr": {
        "title": "Historique des factures",
        "caption": "Recherchez, filtrez, analysez et exportez vos factures.",
        "access": "Acces Financial Companion",
        "test_plan": "Plan de test",
        "mode": "Mode Financial Companion",
        "trend_settings": "Comparaison des tendances",
        "free_msg": "Pour plus de confort, de suivi et de confiance dans votre gestion, decouvrez les plans PREMIUM.",
        "premium_msg": "Continuez votre experience Financial Companion AI avec PREMIUM PLUS.",
        "premium_trend_msg": "Les comparaisons intelligentes sont disponibles dans les plans PREMIUM pour mieux piloter votre activite.",
        "comparison_period": "Periode de comparaison",
        "filters": "Filtres dynamiques",
        "fiscal_periodicity": "Periodicite fiscale",
        "payment_status": "Statut de paiement",
        "country": "Pays",
        "search_period": "Periode de recherche",
        "start_date": "Date de debut",
        "end_date": "Date de fin",
        "search": "Rechercher client, facture, TVA, designation...",
        "vat_filters": "Filtres TVA et business",
        "partner_type": "Type de partenaire",
        "vat_treatment": "Traitement TVA",
        "invoice_type": "Type de facture",
        "load_error": "Impossible de charger l'historique des factures",
        "invoices": "FACTURES",
        "gross": "CHIFFRE D'AFFAIRES",
        "vat": "TVA",
        "charges": "AUTRES CHARGES",
        "net": "RESULTAT NET",
        "no_results": "Aucune facture trouvee pour les filtres selectionnes.",
        "results": "Resultats",
        "exports": "Exports globaux prevus",
        "pdf": "Export PDF global",
        "csv": "Export CSV global",
        "active_filters": "Filtres actifs",
        "trend_mode": "Mode de comparaison",
        "to": "a",
    },
    "en": {
        "title": "Invoice History",
        "caption": "Search, filter, analyze and export invoices.",
        "access": "Financial Companion Access",
        "test_plan": "Test plan",
        "mode": "Financial Companion Mode",
        "trend_settings": "Trend Comparison Settings",
        "free_msg": "For more comfort, tracking and confidence in your management, discover the PREMIUM plans.",
        "premium_msg": "Continue your Financial Companion AI experience with PREMIUM PLUS.",
        "premium_trend_msg": "Smart comparisons are available in PREMIUM plans to better manage your activity.",
        "comparison_period": "Comparison period",
        "filters": "Dynamic filters",
        "fiscal_periodicity": "Fiscal periodicity",
        "payment_status": "Payment status",
        "country": "Country",
        "search_period": "Search period",
        "start_date": "Start date",
        "end_date": "End date",
        "search": "Search client, invoice, VAT, designation...",
        "vat_filters": "VAT and business filters",
        "partner_type": "Partner type",
        "vat_treatment": "VAT treatment",
        "invoice_type": "Invoice type",
        "load_error": "Unable to load invoice history",
        "invoices": "INVOICES",
        "gross": "TURNOVER",
        "vat": "VAT",
        "charges": "OTHER CHARGES",
        "net": "NET RESULT",
        "no_results": "No invoices found for the selected filters.",
        "results": "Results",
        "exports": "Planned global exports",
        "pdf": "Global PDF Export",
        "csv": "Global CSV Export",
        "active_filters": "Active filters",
        "trend_mode": "Trend comparison mode",
        "to": "to",
    },
}

def _match_search(row: dict, search_text: str) -> bool:
    if not search_text:
        return True

    needle = search_text.lower().strip()

    searchable = " ".join(
        str(row.get(key, "") or "")
        for key in [
            "invoice_number",
            "invoice_type",
            "partner_name",
            "partner_vat_number",
            "payment_status",
            "source",
            "note",
        ]
    ).lower()

    return needle in searchable


def _get_comparison_dates(
    end_date: date,
    comparison_period: str,
) -> tuple[date, date]:
    if comparison_period == "MONTHLY":
        return end_date - timedelta(days=30), end_date

    if comparison_period == "QUARTERLY":
        return end_date - timedelta(days=90), end_date

    if comparison_period == "ANNUAL":
        return end_date - timedelta(days=365), end_date

    return end_date - timedelta(days=30), end_date


def render_invoice_history_ui() -> None:
    lang = get_afribooks_language()
    labels = TEXTS.get(lang, TEXTS["nl"])

    st.markdown(f"## {labels['title']}")
    st.caption(labels["caption"])
    st.markdown(f"### {labels['access']}")

    plan = st.selectbox(
        labels["test_plan"],
        ["FREE", "PREMIUM", "PREMIUM_PLUS"],
        index=0,
    )

    if plan == "FREE":
        widget_mode = "COMPACT"
        st.info(labels["free_msg"])
    elif plan == "PREMIUM":
        widget_mode = st.selectbox(
            labels["mode"],
            ["COMPACT", "FULL"],
            index=1,
        )
    else:
        widget_mode = st.selectbox(
            labels["mode"],
            ["HIDDEN", "COMPACT", "FULL"],
            index=2,
        )

    st.markdown(f"### {labels['trend_settings']}")

    if plan == "FREE":
        comparison_period = "MONTHLY"
        st.info(labels["premium_trend_msg"])
    elif plan == "PREMIUM":
        comparison_period = "MONTHLY"
        st.info(labels["premium_msg"])
    else:
        comparison_period = st.selectbox(
            labels["comparison_period"],
            ["MONTHLY", "QUARTERLY", "ANNUAL"],
            index=0,
        )

    st.markdown(f"### {labels['filters']}")

    col_periodicity, col_status, col_country = st.columns(3)

    with col_periodicity:
        fiscal_periodicity = st.selectbox(
            labels["fiscal_periodicity"],
            ["ALL", "MONTHLY", "QUARTERLY", "ANNUAL"],
            index=0,
        )

    with col_status:
        payment_status = st.selectbox(
            labels["payment_status"],
            ["ALL", "PAID", "UNPAID", "PARTIAL"],
            index=0,
        )

    with col_country:
        country_filter = st.selectbox(
            labels["country"],
            ["ALL", "NL", "BE", "FR", "DE", "CM"],
            index=0,
        )

    st.markdown(f"### {labels['search_period']}")

    trend_start_date, trend_end_date = _get_comparison_dates(
        end_date=date.today(),
        comparison_period=comparison_period,
    )

    col_start, col_end = st.columns(2)

    with col_start:
        start_date = st.date_input(
            labels["start_date"],
            value=trend_start_date,
        )

    with col_end:
        end_date = st.date_input(
            labels["end_date"],
            value=trend_end_date,
        )

    search_text = st.text_input(
        labels["search"]
    )

    st.markdown(f"### {labels['vat_filters']}")

    col_partner, col_vat, col_type = st.columns(3)

    with col_partner:
        partner_type = st.selectbox(
            labels["partner_type"],
            ["ALL", "B2B", "B2C"],
            index=0,
        )

    with col_vat:
        vat_type = st.selectbox(
            labels["vat_treatment"],
            ["ALL", "21%", "9%", "0%", "REVERSE_CHARGE"],
            index=0,
        )

    with col_type:
        invoice_type = st.selectbox(
            labels["invoice_type"],
            ["ALL", "SALE", "PURCHASE"],
            index=0,
        )

    try:
        rows = list_invoice_history(limit=300)
        expense_summary = get_operating_expense_summary(
            start_date=start_date,
            end_date=end_date,
        )
        trend_metrics = get_current_and_previous_period_metrics(
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        st.error(f"{labels['load_error']}: {exc}")
        return

    filtered_rows = []

    for row in rows:
        row_date = row.get("invoice_date")

        if row_date and not (start_date <= row_date <= end_date):
            continue

        if payment_status != "ALL" and row.get("payment_status") != payment_status:
            continue

        if invoice_type != "ALL" and row.get("invoice_type") != invoice_type:
            continue

        if not _match_search(row, search_text):
            continue

        if vat_type == "0%" and float(row.get("total_vat_eur") or 0) != 0:
            continue

        if vat_type == "21%" and float(row.get("total_vat_eur") or 0) <= 0:
            continue

        if vat_type == "REVERSE_CHARGE":
            note = str(row.get("note") or "").upper()
            if "REVERSE" not in note and "VERLEGD" not in note:
                continue

        filtered_rows.append(row)

    st.markdown("---")

    total_vat = sum(float(row.get("total_vat_eur") or 0) for row in filtered_rows)
    total_gross = sum(float(row.get("total_gross_eur") or 0) for row in filtered_rows)

    other_charges = float(expense_summary.get("total_expenses") or 0)
    real_net = total_gross - total_vat - other_charges

    current_metrics = trend_metrics["current"]
    previous_metrics = trend_metrics["previous"]

    if widget_mode != "HIDDEN":
        render_manager_widget_ui(
            invoices_count=len(filtered_rows),
            gross=total_gross,
            vat=total_vat,
            other_charges=other_charges,
            net=real_net,
            compact=(widget_mode == "COMPACT"),
        )

    render_result_widget_ui(
        invoices_count=len(filtered_rows),
        gross=total_gross,
        vat=total_vat,
        other_charges=other_charges,
        net=real_net,
    )

    col_count, col_gross, col_vat_total, col_charges, col_net = st.columns(5)

    with col_count:
        st.metric(labels["invoices"], len(filtered_rows))

    with col_gross:
        st.metric(labels["gross"], f"{total_gross:.2f} EUR")

    with col_vat_total:
        st.metric(labels["vat"], f"{total_vat:.2f} EUR")

    with col_charges:
        st.metric(labels["charges"], f"{other_charges:.2f} EUR")

    with col_net:
        st.metric(labels["net"], f"{real_net:+.2f} EUR")

    if plan == "FREE":
        st.info(labels["premium_trend_msg"])
    else:
        render_smart_trend_widget_ui(
            current_gross=current_metrics["gross"],
            previous_gross=previous_metrics["gross"],
            current_vat=current_metrics["vat"],
            previous_vat=previous_metrics["vat"],
            current_charges=current_metrics["other_charges"],
            previous_charges=previous_metrics["other_charges"],
            current_net=current_metrics["net"],
            previous_net=previous_metrics["net"],
        )

    if not filtered_rows:
        st.info(labels["no_results"])
        return

    st.markdown(f"### {labels['results']}")

    st.dataframe(
        filtered_rows,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(f"### {labels['exports']}")

    col_pdf, col_csv = st.columns(2)

    with col_pdf:
        st.button(labels["pdf"], disabled=True)

    with col_csv:
        st.button(labels["csv"], disabled=True)

    previous_period = trend_metrics["previous_period"]

    st.caption(
        f"Active filters: periodicity={fiscal_periodicity}, country={country_filter}, "
        f"partner_type={partner_type}, vat_type={vat_type} | "
        f"Trend comparison mode={comparison_period}: "
        f"{previous_period['start_date']} to {previous_period['end_date']}"
    )


















