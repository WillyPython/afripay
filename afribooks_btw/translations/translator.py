from afribooks_btw.translations.vat_translations import VAT_TRANSLATIONS


SUPPORTED_LANGUAGES = {"fr", "en", "nl"}


def translate_vat_reason(reason_code: str, language: str = "fr") -> str:
    lang = (language or "fr").lower()

    if lang not in SUPPORTED_LANGUAGES:
        lang = "fr"

    item = VAT_TRANSLATIONS.get(reason_code)

    if not item:
        return reason_code

    return item.get(lang) or item.get("fr") or reason_code
