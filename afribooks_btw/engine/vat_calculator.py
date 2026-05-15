from decimal import Decimal


def to_decimal(value) -> Decimal:
    return Decimal(str(value or "0.00"))


def compute_vat_from_net(net_amount, vat_rate) -> dict:
    """
    Calcule TVA et TTC à partir d'un montant HT.
    Exemple : 100 HT + 21% = 121 TTC
    """

    net = to_decimal(net_amount).quantize(Decimal("0.01"))
    rate = to_decimal(vat_rate)

    if rate <= 0:
        return {
            "net_amount": net,
            "vat_amount": Decimal("0.00"),
            "gross_amount": net,
            "vat_rate": rate,
            "amount_type": "HT",
        }

    vat = (net * rate).quantize(Decimal("0.01"))
    gross = (net + vat).quantize(Decimal("0.01"))

    return {
        "net_amount": net,
        "vat_amount": vat,
        "gross_amount": gross,
        "vat_rate": rate,
        "amount_type": "HT",
    }


def compute_vat_from_gross(gross_amount, vat_rate) -> dict:
    """
    Calcule HT et TVA à partir d'un montant TTC.
    Exemple : 121 TTC avec 21% = 100 HT + 21 TVA
    """

    gross = to_decimal(gross_amount).quantize(Decimal("0.01"))
    rate = to_decimal(vat_rate)

    if rate <= 0:
        return {
            "net_amount": gross,
            "vat_amount": Decimal("0.00"),
            "gross_amount": gross,
            "vat_rate": rate,
            "amount_type": "TTC",
        }

    net = (gross / (Decimal("1.00") + rate)).quantize(Decimal("0.01"))
    vat = (gross - net).quantize(Decimal("0.01"))

    return {
        "net_amount": net,
        "vat_amount": vat,
        "gross_amount": gross,
        "vat_rate": rate,
        "amount_type": "TTC",
    }
