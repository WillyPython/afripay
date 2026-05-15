from afribooks_btw.engine.vat_engine import determine_vat_treatment


def build_vat_entry(form_data: dict, profile: dict, amount_eur: float) -> dict:
    decision = determine_vat_treatment(form_data, profile)

    vat_amount = round(amount_eur * decision.vat_rate, 2)

    return {
        "amount_eur": amount_eur,
        "vat_rate": decision.vat_rate,
        "vat_amount": vat_amount,
        "vat_type": decision.vat_type,
        "report_box": decision.report_box,
        "treatment": decision.treatment,
        "reason": decision.reason,
    }
