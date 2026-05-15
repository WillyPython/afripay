from dataclasses import dataclass


@dataclass
class NotificationMessage:
    code: str
    level: str
    title: str
    message: str


def build_security_notifications() -> list[NotificationMessage]:
    return [
        NotificationMessage(
            code="SECURITY_PASSWORD",
            level="info",
            title="Security reminder",
            message="Aucun agent AfriBooks ne vous demandera votre mot de passe.",
        ),
        NotificationMessage(
            code="SECURITY_EXTRA_FEES",
            level="info",
            title="Payment safety",
            message="Aucun agent AfriBooks ne vous demandera des frais supplémentaires non affichés dans l'application.",
        ),
    ]


def build_vat_notifications(days_before_deadline: int | None = None) -> list[NotificationMessage]:
    notifications: list[NotificationMessage] = []

    if days_before_deadline is None:
        return notifications

    if days_before_deadline <= 7:
        notifications.append(
            NotificationMessage(
                code="VAT_DEADLINE_SOON",
                level="warning",
                title="VAT deadline soon",
                message="Votre échéance TVA approche. Préparez votre déclaration sans stress.",
            )
        )

    return notifications
