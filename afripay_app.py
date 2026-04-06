import os
import secrets
import urllib.parse

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image

from services.order_service import _round_xaf
from services.user_service import get_user_by_id

import streamlit as st


st.set_page_config(
    page_title="AfriPay Afrika",
    page_icon="🌍",
    layout="wide",
)

st.markdown("""
<style>

/* SIDEBAR BACKGROUND */
[data-testid="stSidebar"] {
    background-color: #0f172a; /* bleu foncé fintech */
}

/* TEXTES SIDEBAR PROPRES */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] .stMarkdown {
    color: white !important;
}

/* SELECTBOX */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: white !important;
    color: #0f172a !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #0f172a !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] svg {
    fill: #0f172a !important;
}

/* TITRES SIDEBAR */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: white !important;
}

/* SELECTBOX */
[data-testid="stSidebar"] .stSelectbox label {
    color: #cbd5f5 !important;
}

/* MENU RADIO */
[data-testid="stSidebar"] .stRadio label {
    color: white !important;
}

/* BUTTON */
[data-testid="stSidebar"] .stButton button {
    background-color: #10b981;
    color: white;
    border-radius: 10px;
}

/* BADGES PLAN */
.afripay-plan-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    margin: 8px 0 10px 0;
    letter-spacing: 0.02em;
}

.afripay-plan-free {
    background: rgba(59, 130, 246, 0.16);
    color: #bfdbfe;
    border: 1px solid rgba(191, 219, 254, 0.30);
}

.afripay-plan-premium {
    background: rgba(251, 191, 36, 0.14);
    color: #fde68a;
    border: 1px solid rgba(253, 230, 138, 0.30);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* Palette AfriPay */
:root {
    --afripay-green: #1ABC9C;
    --afripay-green-hover: #17A589;
    --afripay-sidebar-bg: #0F172A;
    --afripay-white: #FFFFFF;
    --afripay-black: #111827;
}

/* Boutons */
.stButton > button {
    background-color: var(--afripay-green);
    color: var(--afripay-white);
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: 600;
    border: none;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background-color: var(--afripay-green-hover);
    color: var(--afripay-white);
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(16,185,129,0.25);
}

/* Container */
.block-container {
    padding-top: 2rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: var(--afripay-sidebar-bg);
}

/* Texte sidebar */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] span {
    color: var(--afripay-white) !important;
}

/* Correction visibilité texte bloc sidebar (Connected / Not connected) */
section[data-testid="stSidebar"] [data-testid="stAlert"] {
    background-color: var(--afripay-white) !important;
    color: #0F172A !important;
}

section[data-testid="stSidebar"] [data-testid="stAlert"] * {
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
}

/* Selectbox sidebar */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: var(--afripay-white) !important;
    color: var(--afripay-black) !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] span {
    color: var(--afripay-black) !important;
    -webkit-text-fill-color: var(--afripay-black) !important;
}

/* Fond principal plus doux */
[data-testid="stAppViewContainer"] {
    background-color: #F4F7FB !important;
}

/* Zone centrale */
.main .block-container {
    background: rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border-radius: 20px;
    padding: 2rem 2rem 3rem 2rem !important;
    margin: 2rem auto !important;
    max-width: 900px;
    border: 1px solid rgba(255, 255, 255, 0.35);
    box-shadow: 0 12px 35px rgba(15, 23, 42, 0.10);
}

/* Fond global légèrement plus neutre */
[data-testid="stAppViewContainer"] {
    background-color: #EEF2F7 !important;
}

/* Inputs plus nets */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
div[data-baseweb="input"] input {
    background-color: #FFFFFF !important;
    color: #111827 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}

/* Focus input */
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus,
div[data-baseweb="input"] input:focus {
    border: 1px solid #1ABC9C !important;
    box-shadow: 0 0 0 1px #1ABC9C !important;
}

/* Titres */
h1, h2, h3 {
    color: #0F172A !important;
}

/* Texte courant */
p, label, div {
    color: #1F2937;
}

/* Alertes plus premium */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    padding: 14px 16px !important;
    font-size: 15px !important;
    font-weight: 500;
}

/* INFO (bleu) */
[data-testid="stAlert"] div[role="alert"] {
    background-color: #E8F1FF !important;
    color: #1E293B !important;
}

/* WARNING (jaune) */
[data-testid="stAlert"][class*="warning"] div {
    background-color: #FFF7E6 !important;
    color: #78350F !important;
}

/* SUCCESS (vert futur) */
[data-testid="stAlert"][class*="success"] div {
    background-color: #ECFDF5 !important;
    color: #065F46 !important;
}

/* Cartes glass (messages, captcha, info) */
.stAlert,
div[data-testid="stNotification"] {
    background: rgba(255,255,255,0.65) !important;
    backdrop-filter: blur(8px);
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.3);
}
</style>
""", unsafe_allow_html=True)

lang = st.session_state.get("language", "fr")

if lang == "en":
    meta_description = "AfriPay Afrika is an international purchase service provided by AfriDIGID, enabling users to order products and services from Africa easily. Payments are made via Mobile Money to AfriDIGID’s merchant accounts or its partners."
else:
    meta_description = "AfriPay Afrika est un service d’achat international proposé par AfriDIGID, permettant de commander des produits et services depuis l’Afrique en toute simplicité. Le règlement s’effectue via Mobile Money sur les comptes marchands d’AfriDIGID ou de ses partenaires."

st.markdown(
    f"""
    <meta name="description" content="{meta_description}">
    """,
    unsafe_allow_html=True,
)

from config.settings import APP_TITLE
from data.database import init_db
from core.session import (
    init_session,
    logout_user,
    logout_admin,
    login_user,
    restore_user_session,
)
from services.user_service import upsert_user
from services.auth_session_service import (
    create_user_session,
    get_active_session,
    touch_session,
    deactivate_session,
)
from services.order_service import (
    create_order_for_user,
    list_orders_for_user,
    get_order_by_code,
    get_payment_status_label,
    mark_payment_proof_sent,
    render_order_status_badge,
)
from services.admin_service import (
    admin_is_configured,
    verify_admin_password,
)
from services.settings_service import ensure_defaults
from ui.branding import render_sidebar_branding


AFRIPAY_PUBLIC_URL = "https://afripayafrika.com"
EUR_TO_XAF_RATE = 655.957
AFRIPAY_PERCENT_FEE = 0.20

FREE_ORDERS_LIMIT = 2
FREE_ORDER_MAX_XAF = 50000

# WhatsApp numbers from Render environment variables
WHATSAPP_DEFAULT = os.getenv("WHATSAPP_DEFAULT", "31620361841")
WHATSAPP_CM = os.getenv("WHATSAPP_CM", WHATSAPP_DEFAULT)

# OTP anti-spam
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_REQUESTS = 3
OTP_WINDOW_MINUTES = 5

LANG_FR = "FR"
LANG_EN = "EN"

# Internal stable keys
MENU_LOGIN = "login"
MENU_DASHBOARD = "dashboard"
MENU_TRACKING = "tracking"
MENU_SIMULATE = "simulate"
MENU_CREATE_ORDER = "create_order"
MENU_MY_ORDERS = "my_orders"
MENU_ADMIN = "admin"

ORDER_TYPE_PHYSICAL_KEY = "PHYSICAL"
ORDER_TYPE_SERVICE_KEY = "SERVICE"

STATUS_LABELS_FR = {
    "CREEE": "Créée",
    "PAYEE": "Payée",
    "EN_COURS": "En cours",
    "LIVREE": "Livrée",
    "ANNULEE": "Annulée",
}

STATUS_LABELS_EN = {
    "CREEE": "Created",
    "PAYEE": "Paid",
    "EN_COURS": "In progress",
    "LIVREE": "Delivered",
    "ANNULEE": "Cancelled",
}


TRANSLATIONS = {
    "fr": {
        "menu_connexion": "Connexion",
        "menu_dashboard": "Dashboard Client",
        "menu_tracking": "Suivre commande",
        "menu_simulate": "Simuler",
        "menu_create_order": "Créer commande",
        "menu_my_orders": "Mes commandes",
        "menu_admin": "Admin",
        "connected": "Connecté ✅",
        "not_connected": "Non connecté",
        "phone_caption": "Téléphone : {phone}",
        "logout": "Déconnexion",
        "menu": "Menu",
        "language": "Langue",
        "page_login_title": "Connexion",
        "page_login_intro_1": """
### 🌍 Que pouvez-vous commander avec AfriPay ?

AfriPay vous aide à commander des **produits et services internationaux** depuis l’Afrique, via un processus simple et guidé avec le Mobile Money.

**Exemples :**

• 🛒 Produits : plateformes e-commerce internationales  
• 🎓 Études : certifications de diplômes, universités, examens  
• 💻 Digital : logiciels, hébergement, abonnements  
• 📦 Commerce : achats pour revente locale
""",
        "page_login_intro_2": """
### 🔒 Pourquoi faire confiance à AfriPay ?

✅ Connexion sécurisée par OTP  
✅ Vérification humaine anti-bot  
✅ Suivi des commandes directement dans AfriPay  
✅ Commandes internationaux facilités
""",
        "login_info": "Connexion privée de test AfriPay. Après connexion, vous serez redirigé vers « Créer commande » pour commencer votre opération.",
        "phone": "Téléphone",
        "otp_none": "Aucun OTP de test généré pour le moment. Clique sur « Envoyer OTP » pour générer un code visible à l’écran.",
        "otp_other_phone": "Un OTP de test existe déjà pour un autre numéro. Utilise le même numéro ou demande un nouvel OTP.",
        "otp_test_mode": "## 🔐 MODE TEST AFRIPAY",
        "otp_test_warning": "Ce code OTP est visible à l’écran uniquement pour le test privé. Il n’est pas encore envoyé par SMS ni par WhatsApp.",
        "otp_linked_phone": "NUMÉRO DE TÉLÉPHONE LIÉ",
        "otp_test_code": "CODE OTP DE TEST",
        "otp_keep_info": "Conserve ce code et ce numéro tels qu’affichés ci-dessus. Ils resteront visibles tant qu’un nouvel OTP n’est pas demandé ou que la connexion n’est pas validée.",
        "otp_wait_before_retry": "Veuillez attendre encore {seconds} seconde(s) avant de demander un nouveau code OTP.",
        "otp_too_many_requests": "Trop de demandes OTP pour ce numéro. Réessayez dans {minutes} minute(s).",
        "otp_limit_info": "Protection OTP : 1 code toutes les 60 secondes, maximum 3 codes sur 5 minutes.",
        "captcha_title": "Vérification humaine",
        "captcha_required": "Captcha obligatoire : vous devez saisir le résultat exact pour continuer.",
        "captcha_info": "Protection anti-bot AfriPay : veuillez résoudre l'opération suivante avant de continuer : **{a} + {b} = ?**",
        "captcha_input": "Résultat de l'opération *",
        "captcha_placeholder": "Captcha obligatoire : entrez le résultat exact",
        "captcha_help": "Ce captcha est obligatoire. Sans le bon résultat, vous ne pourrez pas continuer.",
        "captcha_ok": "Captcha correct ✅",
        "captcha_bad": "Captcha incorrect ❌",
        "captcha_refresh": "🔄 Nouveau calcul",
        "captcha_caption": "Saisissez le résultat exact du captcha, puis cliquez sur le bouton de validation de cette page.",
        "send_otp": "Envoyer OTP",
        "enter_phone": "Entre ton numéro.",
        "captcha_empty_otp": "Captcha obligatoire : veuillez entrer le résultat de l'opération avant d'envoyer l'OTP.",
        "captcha_invalid_otp": "Captcha incorrect : veuillez entrer le résultat exact de l'opération pour envoyer l'OTP.",
        "otp_success": "OTP de test généré avec succès ✅",
        "enter_otp": "Entrer OTP",
        "otp_placeholder": "Entrez ici le code OTP affiché ci-dessus",
        "name": "Nom",
        "optional": "Optionnel",
        "email": "Email",
        "login_button": "Se connecter",
        "ask_otp_first": "Demande d'abord un OTP.",
        "phone_used_for_otp": "Entre le numéro de téléphone utilisé pour demander l’OTP.",
        "phone_different": "Téléphone différent de celui utilisé pour l’OTP.",
        "otp_incorrect": "OTP incorrect.",
        "login_success": "Connexion réussie ✅",
        "dashboard_title": "Dashboard Client",
        "need_login_dashboard": "Tu dois être connecté pour accéder à ton tableau de bord.",
        "my_orders_metric": "Mes commandes",
        "paid_metric": "Payées",
        "in_progress_metric": "En cours",
        "delivered_metric": "Livrées",
        "cancelled_metric": "Annulées",
        "cumulated_xaf": "Montant cumulé XAF",
        "cumulated_eur": "Montant cumulé EUR",
        "summary_client": "Résumé client",
        "summary_client_info": "AfriPay facilite vos paiements internationaux. Le dédouanement et la livraison finale restent sous votre responsabilité via votre transitaire / agent lorsqu’il s’agit d’un produit physique.",
        "no_orders": "Aucune commande pour le moment.",
        "status_chart": "### 📊 Répartition des commandes par statut",
        "status_chart_empty": "Pas assez de données pour afficher le graphique des statuts.",
        "monthly_evolution": "### 📈 Évolution mensuelle des commandes",
        "monthly_evolution_empty": "Pas assez de données pour afficher l’évolution mensuelle.",
        "monthly_volume": "### 💰 Volume financier mensuel XAF",
        "monthly_volume_empty": "Pas assez de données pour afficher le volume financier.",
        "latest_order": "Dernière commande",
        "reference": "Référence",
        "product_service": "Produit / Service",
        "merchant": "Marchand",
        "total_xaf": "Total XAF",
        "total_eur": "Total EUR",
        "order_status": "Statut commande",
        "payment_status": "Statut paiement",
        "forwarder_address": "Adresse transitaire",
        "merchant_info": "Informations marchand",
        "merchant_order_number": "Numéro commande marchand",
        "purchase_date": "Date d'achat",
        "merchant_status": "Statut marchand",
        "confirmation_link": "Lien confirmation",
        "tracking_link": "Lien suivi",
        "tracking_title": "Suivre une commande",
        "tracking_caption": "Entre ton numéro de commande. Exemple : CMD-2026-001",
        "order_number": "Numéro de commande",
        "search": "Rechercher",
        "enter_order_number": "Entre un numéro de commande.",
        "order_not_found": "Commande introuvable.",
        "merchant_info_not_available": "Les informations marchand ne sont pas encore disponibles.",
        "simulate_title": "Simuler paiement",
        "merchant_amount_xaf": "Montant marchand (XAF)",
        "seller_fee_xaf": "Frais vendeur / site (XAF)",
        "afripay_fee_xaf": "Frais de service AfriPay (XAF)",
        "total_to_pay_xaf": "Total à payer (XAF)",
        "financial_summary": "### 🧾 Résumé financier AfriPay",
        "values_xaf": "#### Valeurs en XAF",
        "values_eur": "#### Valeurs en EUR",
        "merchant_amount": "Montant marchand",
        "afripay_fee": "Frais AfriPay",
        "total_to_pay": "Total à payer",
        "total_paid": "Total payé",
        "pricing_info": "Tarification AfriPay v1 : {percent} % du montant marchand, sans frais fixe",
        "create_order_title": "Créer commande",
        "need_login_create_order": "Tu dois être connecté.",
        "create_order_step_info": "📌 Étape principale après connexion : crée d’abord ta commande. Tu pourras ensuite vérifier le résultat dans « Mes commandes » puis dans le Dashboard Client.",
        "create_order_info": "📌  AfriPay facilite les commandes internationales. Pour un produit physique, le transitaire reste sous la responsabilité du client. Pour un service ou commande digitale, aucun transitaire n’est requis.",
        "how_to_create": "### Comment créer votre commande",
        "create_steps": """
        1. Choisissez le **type de commande**  
        2. Collez le **lien du produit ou du service**  
        3. Indiquez le **nom du produit ou du service**  
        4. Saisissez le **montant total affiché par le marchand**  
        5. Choisissez la **devise du marchand**  
        6. Vérifiez le **résumé financier AfriPay**  
        7. Si c’est un produit physique, renseignez l'**adresse du transitaire / agence**  
        8. Choisissez votre **opérateur Mobile Money**
        """,
        "legal_warning": " Message juridique : AfriPay est une plateforme technologique et un service d’achat international proposé par AfriDIGID. AfriDIGID se charge du traitement des commandes et du règlement auprès des marchands dans le cadre du service proposé. AfriPay n’assure pas le dédouanement ni la livraison finale des produits physiques. Le client reste responsable de son transitaire, de l’adresse de réception finale et des formalités liées à son achat.",
        "practical_tip": "Conseil pratique : saisissez le montant total final affiché par le marchand. Ce montant peut être en XAF ou en EUR selon le site ou le vendeur.",
        "payment_parameters": "### 💳 Paramètres de paiement",
        "order_type": "Type de commande *",
        "order_type_help": "Choisissez « Produit physique » pour un achat à livrer, ou « Service / paiement digital » pour une certification, un abonnement, un logiciel, etc.",
        "main_information": "### 🔗 Informations principales",
        "merchant_total_displayed": "Montant total affiché par le marchand *",
        "merchant_currency": "Devise du marchand *",
        "merchant_currency_help": "Choisissez la devise réellement affichée par le site marchand ou le service.",
        "product_service_link": "🔗 Lien du produit ou du service *",
        "product_link_placeholder": "Collez ici le lien Amazon, Temu, WES, logiciel, hébergement, université, etc.",
        "product_link_tip": "💡 Astuce : Collez ici le lien du produit ou du service. Si votre commande contient plusieurs éléments, saisissez simplement le montant total affiché par le marchand.",
        "product_service_name": "🛍 Nom du produit ou du service *",
        "product_service_name_placeholder": "Exemple : Routeur Wi-Fi, Certification diplôme, Hébergement web annuel...",
        "merchant_org": "🏪 Site marchand / organisme *",
        "merchant_org_placeholder": "Exemple : Amazon, Temu, WES, IELTS, Hostinger, Université...",
        "details_useful": "📋 Caractéristiques / détails utiles",
        "details_useful_placeholder": "Exemple : taille, couleur, quantité, numéro de dossier, type de service...",
        "delivery_payment": "### 🚚 Livraison et paiement",
        "forwarder_address_label": "📦 Adresse du transitaire / agence *",
        "forwarder_address_placeholder": "Exemple : nom de l'agence, ville, quartier, contact utile...",
        "forwarder_address_help": "Cette adresse doit correspondre à l'adresse utilisée pour la réception de la commande physique.",
        "no_forwarder_required": "Aucun transitaire requis ✅",
        "momo_provider": "📱 Opérateur Mobile Money",
        "momo_selected": "Mode de paiement sélectionné : {provider} Mobile Money",
        "momo_choose": "Choisissez votre opérateur Mobile Money pour finaliser votre commande.",
        "captcha_validated_above": "Le captcha se valide au-dessus. Une fois correct, cliquez ici sur « Créer la commande ».",
        "client_ack": "Je confirme avoir lu et accepté les informations juridiques et opérationnelles ci-dessus.",
        "create_order_button": "Créer la commande",
        "captcha_empty_order": "Captcha obligatoire : veuillez entrer le résultat de l'opération avant de créer la commande.",
        "captcha_invalid_order": "Captcha incorrect : veuillez entrer le résultat exact de l'opération avant de créer la commande.",
        "product_link_required": "Le lien du produit ou du service est obligatoire.",
        "product_name_required": "Le nom du produit ou du service est obligatoire.",
        "merchant_required": "Le site marchand / organisme est obligatoire.",
        "amount_required": "Le montant total affiché par le marchand doit être supérieur à 0.",
        "forwarder_required": "L'adresse du transitaire / agence est obligatoire pour un produit physique.",
        "ack_required": "Tu dois valider les informations juridiques et opérationnelles avant de créer la commande.",
        "order_created": "Commande créée ✅ Numéro : **{order_code}**",
        "order_saved_info": "Votre commande a bien été enregistrée. Vous pouvez maintenant vérifier le résultat dans « Mes commandes » puis dans le Dashboard Client.",
        "estimated_summary": "Résumé estimatif retenu : Montant marchand {merchant_xaf} XAF ({merchant_eur} EUR) | Frais AfriPay {fee_xaf} XAF ({fee_eur} EUR) | Total {total_xaf} XAF ({total_eur} EUR)",
        "share_order_title": "### 📲 Partager votre commande",
        "share_whatsapp": "Partager AfriPay sur WhatsApp",
        "see_whatsapp_message": "Voir le message WhatsApp",
        "payment_proof_title": "### 💳 Envoyer votre preuve de paiement",
        "send_payment_proof_whatsapp": "📲 Envoyer ma preuve via WhatsApp",
        "prepare_payment_proof": "📲 J’ai préparé mon message de paiement",
        "payment_proof_status_updated": "Statut mis à jour : message de preuve de paiement préparé.",
        "payment_proof_status_already": "Le statut de paiement a déjà été préparé pour cette commande.",
        "see_payment_proof_message": "Voir le message WhatsApp de paiement",
        "payment_proof_help": "Après votre paiement Mobile Money, cliquez sur ce bouton pour ouvrir WhatsApp avec votre message déjà préparé.",
        "payment_proof_message_intro": "Bonjour AfriPay 👋",
        "payment_proof_message_confirm": "Je confirme le paiement de ma commande.",
        "payment_proof_message_reference": "Référence : {order_code}",
        "payment_proof_message_amount": "Montant : {amount_xaf} XAF",
        "payment_proof_message_operator": "Opérateur : {provider}",
        "payment_proof_message_screenshot": "Vous trouverez ci-joint la capture du paiement.",
        "payment_proof_message_thanks": "Merci.",
        "referral_title": "### 🎁 Inviter un proche sur WhatsApp",
        "referral_button": "📲 Inviter via WhatsApp",
        "referral_help": "Partagez AfriPay avec un proche, parent, collègue ou commerçant directement sur WhatsApp.",
        "see_referral_message": "Voir le message WhatsApp",
        "referral_hello": "Bonjour 👋",
        "referral_intro": "Je viens de découvrir AfriPay Afrika CM et j’ai pensé que cela pourrait t’intéresser.",
        "referral_body_1": "👉 Une solution simple pour acheter des produits et services à l’international depuis l’Afrique, sans complications.",
        "referral_examples_title": "Exemples :",
        "referral_examples": "Amazon, Temu, certifications, universités, logiciels, abonnements",
        "referral_cta": "Tu peux découvrir ici :",
        "my_orders_title": "Mes commandes",
        "need_login_my_orders": "Tu dois être connecté.",
        "no_orders_short": "Aucune commande.",
        "created_on": "Créée le",
        "merchant_org_label": "Marchand / Organisme",
        "amount_xaf_label": "Montant XAF",
        "amount_eur_label": "Montant EUR",
        "seller_fee_label": "Frais vendeur",
        "merchant_amount_label": "Montant marchand",
        "total_paid_label": "Total payé",
        "forwarder_address_expander": "Adresse agence / transitaire",
        "payment_label": "Paiement",
        "status_label": "Statut",
        "timeline_title": "Timeline logistique",
        "timeline_order_title": "Timeline logistique de la commande",
        "step_created": "Commande créée",
        "step_payment_confirmed": "Paiement AfriPay confirmé",
        "step_merchant_order": "Commande passée chez le marchand",
        "step_shipped": "Commande expédiée",
        "step_delivered_forwarder": "Livrée au transitaire",
        "step_reference": "Référence : {ref}",
        "step_payment_status": "Statut paiement : {status}",
        "step_merchant_status": "Statut marchand : {status}",
        "step_tracking_link": "Lien suivi : {link}",
        "step_forwarder_address": "Adresse transitaire : {address}",
        "waiting": "En attente",
        "not_available": "Non disponible",
        "admin_title": "Administration AfriPay",
        "admin_login_subtitle": "Connexion Admin",
        "admin_password": "Mot de passe admin",
        "admin_login_button": "Se connecter (Admin)",
        "admin_not_configured": "Admin non configuré.",
        "admin_connected": "Admin connecté ✅",
        "admin_bad_password": "Mot de passe incorrect.",
        "admin_password_caption": "Le mot de passe admin est chargé depuis ADMIN_PASSWORD sur Render.",
        "admin_welcome": "Bienvenue dans l'espace administration",
        "open_admin_dashboard": "Ouvrir le Dashboard Admin",
        "logout_admin": "Déconnexion Admin",
        "admin_info": "Clique sur « Ouvrir le Dashboard Admin » pour accéder directement à la page sécurisée admin_dashboard.",
        "whatsapp_hello": "Bonjour 👋",
        "whatsapp_order_created": "Votre commande AfriPay a été créée avec succès ✅",
        "whatsapp_financial_summary": "💰 Résumé de votre commande :",
        "whatsapp_origin_currency": "Devise d’origine du marchand : {currency}",
        "whatsapp_product_link_title": "🔗 Lien du produit / service :",
        "whatsapp_track_order": "👉 Suivez votre commande directement dans AfriPay.",
        "how_it_works_title": "🌍 Que pouvez-vous commander avec AfriPay ?",
        "whatsapp_marketing_1": "🌍 AfriPay vous permet d’acheter facilement des produits et services à l’international depuis l’Afrique.",
        "whatsapp_marketing_2": "🛒 Amazon, Temu, formations, abonnements, services en ligne…",
        "whatsapp_marketing_3": "✨ Une solution simple, rapide et sécurisée pour vos achats internationaux.",
        "whatsapp_brand": "AfriPay Afrika",
        "whatsapp_tagline": "Solution numérique pour vos commandes internationales",
        "product_or_service_unspecified": "Produit ou service non précisé",
        "jan": "Jan",
        "feb": "Fév",
        "mar": "Mar",
        "apr": "Avr",
        "may": "Mai",
        "jun": "Juin",
        "jul": "Juil",
        "aug": "Aoû",
        "sep": "Sep",
        "oct": "Oct",
        "nov": "Nov",
        "dec": "Déc",
    },
    "en": {
        "menu_connexion": "Login",
        "menu_dashboard": "Client Dashboard",
        "menu_tracking": "Track order",
        "menu_simulate": "Simulate",
        "menu_create_order": "Create order",
        "menu_my_orders": "My orders",
        "menu_admin": "Admin",
        "connected": "Connected ✅",
        "not_connected": "Not connected",
        "phone_caption": "Phone: {phone}",
        "logout": "Logout",
        "menu": "Menu",
        "language": "Language",
        "page_login_title": "Login",
        "page_login_intro_1": """
### 🌍 What can you order with AfriPay?

AfriPay allows you to order **international products and services** from Africa using Mobile Money.

**Examples:**

• 🛒 Products: international e-commerce platforms  
• 🎓 Studies: diploma certifications, universities, exams  
• 💻 Digital: software, hosting, subscriptions  
• 📦 Business: purchases for local resale
""",
        "page_login_intro_2": """
### 🔒 Why trust AfriPay?

✅ Secure OTP login  
✅ Anti-bot human verification  
✅ Order tracking directly in AfriPay  
✅ International purchases made easier
""",
        "login_info": "Private AfriPay test login. After login, you will be redirected to “Create order” to start your operation.",
        "phone": "Phone",
        "otp_none": "No test OTP has been generated yet. Click “Send OTP” to generate a visible code on screen.",
        "otp_other_phone": "A test OTP already exists for another phone number. Use the same number or request a new OTP.",
        "otp_test_mode": "## 🔐 AFRIPAY TEST MODE",
        "otp_test_warning": "This OTP code is displayed on screen only for private testing. It is not yet sent by SMS or WhatsApp.",
        "otp_linked_phone": "LINKED PHONE NUMBER",
        "otp_test_code": "TEST OTP CODE",
        "otp_keep_info": "Keep this code and phone number exactly as shown above. They remain visible until a new OTP is requested or the login is validated.",
        "otp_wait_before_retry": "Please wait {seconds} more second(s) before requesting a new OTP code.",
        "otp_too_many_requests": "Too many OTP requests for this phone number. Please try again in {minutes} minute(s).",
        "otp_limit_info": "OTP protection: 1 code every 60 seconds, maximum 3 codes within 5 minutes.",
        "captcha_title": "Human verification",
        "captcha_required": "Required captcha: you must enter the exact result to continue.",
        "captcha_info": "AfriPay anti-bot protection: please solve the following operation before continuing: **{a} + {b} = ?**",
        "captcha_input": "Operation result *",
        "captcha_placeholder": "Required captcha: enter the exact result",
        "captcha_help": "This captcha is required. Without the correct result, you cannot continue.",
        "captcha_ok": "Captcha correct ✅",
        "captcha_bad": "Captcha incorrect ❌",
        "captcha_refresh": "🔄 New calculation",
        "captcha_caption": "Enter the exact captcha result, then click the validation button on this page.",
        "send_otp": "Send OTP",
        "enter_phone": "Enter your phone number.",
        "captcha_empty_otp": "Required captcha: please enter the operation result before sending the OTP.",
        "captcha_invalid_otp": "Incorrect captcha: please enter the exact operation result to send the OTP.",
        "otp_success": "Test OTP generated successfully ✅",
        "enter_otp": "Enter OTP",
        "otp_placeholder": "Enter the OTP code displayed above here",
        "name": "Name",
        "optional": "Optional",
        "email": "Email",
        "login_button": "Login",
        "ask_otp_first": "Request an OTP first.",
        "phone_used_for_otp": "Enter the phone number used to request the OTP.",
        "phone_different": "Phone number is different from the one used for the OTP.",
        "otp_incorrect": "Incorrect OTP.",
        "login_success": "Login successful ✅",
        "dashboard_title": "Client Dashboard",
        "need_login_dashboard": "You must be logged in to access your dashboard.",
        "my_orders_metric": "My orders",
        "paid_metric": "Paid",
        "in_progress_metric": "In progress",
        "delivered_metric": "Delivered",
        "cancelled_metric": "Cancelled",
        "cumulated_xaf": "Total amount XAF",
        "cumulated_eur": "Total amount EUR",
        "summary_client": "Client summary",
        "summary_client_info": "AfriPay facilitates your international purchases. Customs clearance and final delivery remain your responsibility through your forwarder / agent for physical products.",
        "no_orders": "No orders yet.",
        "status_chart": "### 📊 Orders by status",
        "status_chart_empty": "Not enough data to display the status chart.",
        "monthly_evolution": "### 📈 Monthly order evolution",
        "monthly_evolution_empty": "Not enough data to display monthly evolution.",
        "monthly_volume": "### 💰 Monthly financial volume XAF",
        "monthly_volume_empty": "Not enough data to display financial volume.",
        "latest_order": "Latest order",
        "reference": "Reference",
        "product_service": "Product / Service",
        "merchant": "Merchant",
        "total_xaf": "Total XAF",
        "total_eur": "Total EUR",
        "order_status": "Order status",
        "payment_status": "Payment status",
        "forwarder_address": "Forwarder address",
        "merchant_info": "Merchant information",
        "merchant_order_number": "Merchant order number",
        "purchase_date": "Purchase date",
        "merchant_status": "Merchant status",
        "confirmation_link": "Confirmation link",
        "tracking_link": "Tracking link",
        "tracking_title": "Track an order",
        "tracking_caption": "Enter your order number. Example: CMD-2026-001",
        "order_number": "Order number",
        "search": "Search",
        "enter_order_number": "Enter an order number.",
        "order_not_found": "Order not found.",
        "merchant_info_not_available": "Merchant information is not yet available.",
        "simulate_title": "Simulate payment",
        "merchant_amount_xaf": "Merchant amount (XAF)",
        "seller_fee_xaf": "Seller / site fee (XAF)",
        "afripay_fee_xaf": "AfriPay service fee (XAF)",
        "total_to_pay_xaf": "Total to pay (XAF)",
        "financial_summary": "### 🧾 AfriPay financial summary",
        "values_xaf": "#### Values in XAF",
        "values_eur": "#### Values in EUR",
        "merchant_amount": "Merchant amount",
        "afripay_fee": "AfriPay fee",
        "total_to_pay": "Total to pay",
        "total_paid": "Total paid",
        "pricing_info": "AfriPay v1 pricing: {percent}% of the merchant amount, no fixed fee",
        "create_order_title": "Create order",
        "need_login_create_order": "You must be logged in.",
        "create_order_step_info": "📌 Main step after login: first create your order. You can then check the result in “My orders” and in the Client Dashboard.",
        "create_order_info": "📌 AfriPay facilitates international orders. For physical products, the freight forwarder remains the client's responsibility. For digital services or orders, no freight forwarder is required.",
        "how_to_create": "### How to create your order",
        "create_steps": """
        1. Choose the **order type**  
        2. Paste the **product or service link**  
        3. Enter the **product or service name**  
        4. Enter the **total amount displayed by the merchant**  
        5. Choose the **merchant currency**  
        6. Check the **AfriPay financial summary**  
        7. If it is a physical product, enter the **forwarder / agency address**  
        8. Choose your **Mobile Money operator**
        """,
        "legal_warning": "Legal notice: AfriPay is a technological platform and an international purchasing service provided by AfriDIGID. AfriDIGID handles order processing and payments to merchants within the scope of the service. AfriPay does not handle customs clearance or final delivery of physical products. The customer remains responsible for their freight forwarder, final delivery address, and any procedures related to their purchase.",
        "practical_tip": "Practical advice: enter the final total amount displayed by the merchant. This amount may be in XAF or EUR depending on the site or seller.",
        "payment_parameters": "### 💳 Payment settings",
        "order_type": "Order type *",
        "order_type_help": "Choose “Physical product” for a delivered purchase, or “Digital service / payment” for a certification, subscription, software, etc.",
        "main_information": "### 🔗 Main information",
        "merchant_total_displayed": "Total amount displayed by the merchant *",
        "merchant_currency": "Merchant currency *",
        "merchant_currency_help": "Choose the currency actually displayed by the merchant site or service.",
        "product_service_link": "🔗 Product or service link *",
        "product_link_placeholder": "Paste here the Amazon, Temu, WES, software, hosting, university, etc. link.",
        "product_link_tip": "💡 Tip: Paste the product or service link here. If your order contains several items, simply enter the total amount displayed by the merchant.",
        "product_service_name": "🛍 Product or service name *",
        "product_service_name_placeholder": "Example: Wi-Fi router, diploma certification, annual web hosting...",
        "merchant_org": "🏪 Merchant site / organization *",
        "merchant_org_placeholder": "Example: Amazon, Temu, WES, IELTS, Hostinger, University...",
        "details_useful": "📋 Specifications / useful details",
        "details_useful_placeholder": "Example: size, color, quantity, file number, service type...",
        "delivery_payment": "### 🚚 Delivery and payment",
        "forwarder_address_label": "📦 Forwarder / agency address *",
        "forwarder_address_placeholder": "Example: agency name, city, district, useful contact...",
        "forwarder_address_help": "This address must match the address used for receiving the physical order.",
        "no_forwarder_required": "No forwarder required ✅",
        "momo_provider": "📱 Mobile Money operator",
        "momo_selected": "Selected payment mode: {provider} Mobile Money",
        "momo_choose": "Choose your Mobile Money operator to finalize your order.",
        "captcha_validated_above": "The captcha is validated above. Once correct, click here on “Create order”.",
        "client_ack": "I confirm that I have read and accepted the legal and operational information above.",
        "create_order_button": "Create order",
        "captcha_empty_order": "Required captcha: please enter the operation result before creating the order.",
        "captcha_invalid_order": "Incorrect captcha: please enter the exact operation result before creating the order.",
        "product_link_required": "The product or service link is required.",
        "product_name_required": "The product or service name is required.",
        "merchant_required": "The merchant site / organization is required.",
        "amount_required": "The total amount displayed by the merchant must be greater than 0.",
        "forwarder_required": "The forwarder / agency address is required for a physical product.",
        "ack_required": "You must validate the legal and operational information above before creating the order.",
        "order_created": "Order created ✅ Number: **{order_code}**",
        "order_saved_info": "Your order has been recorded successfully. You can now check the result in “My orders” and in the Client Dashboard.",
        "estimated_summary": "Estimated summary retained: Merchant amount {merchant_xaf} XAF ({merchant_eur} EUR) | AfriPay fee {fee_xaf} XAF ({fee_eur} EUR) | Total {total_xaf} XAF ({total_eur} EUR)",
        "share_order_title": "### 📲 Share your order",
        "share_whatsapp": "Share AfriPay on WhatsApp",
        "see_whatsapp_message": "View WhatsApp message",
        "payment_proof_title": "### 💳 Send your payment proof",
        "send_payment_proof_whatsapp": "📲 Send payment proof via WhatsApp",
        "prepare_payment_proof": "📲 I have prepared my payment proof",
        "payment_proof_status_updated": "Status updated: payment proof initiated.",
        "payment_proof_status_already": "The payment status has already been updated for this order.",
        "see_payment_proof_message": "View payment proof message",
        "payment_proof_help": "After Mobile Money payment, click this button to open WhatsApp with a prefilled message. Then add your payment screenshot before sending.",
        "payment_proof_message_intro": "Hello AfriPay,",
        "payment_proof_message_confirm": "I confirm the payment of my order.",
        "payment_proof_message_reference": "Reference: {order_code}",
        "payment_proof_message_amount": "Amount paid: {amount_xaf} XAF",
        "payment_proof_message_operator": "Operator: {provider}",
        "payment_proof_message_screenshot": "Please find attached the payment screenshot.",
        "payment_proof_message_thanks": "Thank you.",
        "referral_title": "### 🎁 Invite someone on WhatsApp",
        "referral_button": "📲 Invite someone on WhatsApp",
        "referral_help": "Share AfriPay with a friend, relative, colleague or merchant directly on WhatsApp.",
        "see_referral_message": "View referral message",
        "referral_hello": "Hello 👋",
        "referral_intro": "I’m sharing AfriPay Afrika with you.",
        "referral_body_1": "The platform helps people order for some international purchases and services from Africa using Mobile Money.",
        "referral_examples_title": "Examples:",
        "referral_examples": "Amazon, Temu, certifications, universities, software, subscriptions",
        "referral_cta": "You can check it here:",
        "my_orders_title": "My orders",
        "need_login_my_orders": "You must be logged in.",
        "no_orders_short": "No orders.",
        "created_on": "Created on",
        "merchant_org_label": "Merchant / Organization",
        "amount_xaf_label": "Amount XAF",
        "amount_eur_label": "Amount EUR",
        "seller_fee_label": "Seller fee",
        "merchant_amount_label": "Merchant amount",
        "total_paid_label": "Total paid",
        "forwarder_address_expander": "Agency / forwarder address",
        "payment_label": "Payment",
        "status_label": "Status",
        "timeline_title": "Logistics timeline",
        "timeline_order_title": "Order logistics timeline",
        "step_created": "Order created",
        "step_payment_confirmed": "AfriPay payment confirmed",
        "step_merchant_order": "Order placed with merchant",
        "step_shipped": "Order shipped",
        "step_delivered_forwarder": "Delivered to forwarder",
        "step_reference": "Reference: {ref}",
        "step_payment_status": "Payment status: {status}",
        "step_merchant_status": "Merchant status: {status}",
        "step_tracking_link": "Tracking link: {link}",
        "step_forwarder_address": "Forwarder address: {address}",
        "waiting": "Pending",
        "not_available": "Not available",
        "admin_title": "AfriPay Administration",
        "admin_login_subtitle": "Admin Login",
        "admin_password": "Admin password",
        "admin_login_button": "Login (Admin)",
        "admin_not_configured": "Admin not configured.",
        "admin_connected": "Admin connected ✅",
        "admin_bad_password": "Incorrect password.",
        "admin_password_caption": "The admin password is loaded from ADMIN_PASSWORD on Render.",
        "admin_welcome": "Welcome to the administration area",
        "open_admin_dashboard": "Open Admin Dashboard",
        "logout_admin": "Logout Admin",
        "admin_info": "Click “Open Admin Dashboard” to access the secure admin_dashboard page directly.",
        "whatsapp_hello": "Hello 👋",
        "whatsapp_order_created": "Your AfriPay order has been successfully created ✅",
        "whatsapp_financial_summary": "💰 Order summary:",
        "whatsapp_origin_currency": "Merchant original currency: {currency}",
        "whatsapp_product_link_title": "🔗 Product / service link:",
        "whatsapp_track_order": "👉 Track your order directly in AfriPay.",
        "whatsapp_marketing_1": "🌍 AfriPay lets you easily purchase products and services internationally from Africa.",
        "whatsapp_marketing_2": "🛒 Amazon, Temu, courses, subscriptions, online services…",
        "whatsapp_marketing_3": "✨ A simple, fast and secure solution for your international purchases.",
        "whatsapp_brand": "AfriPay Afrika",
        "whatsapp_tagline": "Digital solution for your international orders",
        "product_or_service_unspecified": "Unspecified product or service",
        "jan": "Jan",
        "feb": "Feb",
        "mar": "Mar",
        "apr": "Apr",
        "may": "May",
        "jun": "Jun",
        "jul": "Jul",
        "aug": "Aug",
        "sep": "Sep",
        "oct": "Oct",
        "nov": "Nov",
        "dec": "Dec",
    },
}


def get_whatsapp_number(country="CM"):
    if str(country or "").upper() == "CM":
        return WHATSAPP_CM
    return WHATSAPP_DEFAULT


def init_language_state() -> None:
    if "language" not in st.session_state:
        st.session_state["language"] = "fr"


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("language", "fr")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def to_float(value, default=0.0):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def format_xaf(value):
    value = to_float(value, 0.0)
    rounded = int(value) if float(value).is_integer() else int(value) + 1
    return f"{rounded:,}".replace(",", ".")


def format_eur(value):
    value = to_float(value, 0.0)
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def eur_to_xaf(value_eur):
    value_eur = to_float(value_eur, 0.0)
    return value_eur * EUR_TO_XAF_RATE


def xaf_to_eur(value_xaf):
    value_xaf = to_float(value_xaf, 0.0)
    return value_xaf / EUR_TO_XAF_RATE if EUR_TO_XAF_RATE else 0.0


def safe_get(row, key, default=""):
    value = row.get(key, default)
    return value if value not in (None, "") else default


def get_product_label(row, default="—"):
    value = safe_get(row, "product_title", "")
    if value:
        return value

    value = safe_get(row, "product_name", "")
    if value:
        return value

    return default


def parse_date(value):
    if not value:
        return None

    text = str(value).strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def normalize_status(status):
    lang = st.session_state.get("language", "fr")
    status = str(status or "").strip().upper()

    if lang == "en":
        return STATUS_LABELS_EN.get(status, str(status or "—"))
    return STATUS_LABELS_FR.get(status, str(status or "—"))


def normalize_payment_status(status):
    return get_payment_status_label(status)


def month_label(dt):
    months = [
        t("jan"),
        t("feb"),
        t("mar"),
        t("apr"),
        t("may"),
        t("jun"),
        t("jul"),
        t("aug"),
        t("sep"),
        t("oct"),
        t("nov"),
        t("dec"),
    ]
    return f"{months[dt.month - 1]} {dt.year}"


def merchant_status_to_step(merchant_status):
    status = str(merchant_status or "").strip().lower()

    mapping = {
        "commande passée": 3,
        "paiement effectué": 3,
        "confirmée par le marchand": 3,
        "en préparation": 3,
        "expédiée": 4,
        "en transit": 4,
        "livrée au transitaire": 5,
        "order placed": 3,
        "payment completed": 3,
        "confirmed by merchant": 3,
        "preparing": 3,
        "shipped": 4,
        "in transit": 4,
        "delivered to forwarder": 5,
    }
    return mapping.get(status, 0)


def build_timeline_steps(order):
    order_status = str(safe_get(order, "order_status", "")).strip().upper()
    payment_status = str(safe_get(order, "payment_status", "")).strip().upper()
    merchant_status = safe_get(order, "merchant_status", "")
    payment_status_label = normalize_payment_status(payment_status)

    merchant_step = merchant_status_to_step(merchant_status)

    steps = [
        {
            "title": t("step_created"),
            "done": order_status in {"CREEE", "PAYEE", "EN_COURS", "LIVREE"},
            "detail": t("step_reference", ref=safe_get(order, "order_code", "—")),
        },
        {
            "title": t("step_payment_confirmed"),
            "done": payment_status in {"CONFIRMED", "PAYE", "PAYÉ", "PAYEE", "PAYÉE"},
            "detail": t("step_payment_status", status=payment_status_label),
        },
        {
            "title": t("step_merchant_order"),
            "done": merchant_step >= 3,
            "detail": t("step_merchant_status", status=merchant_status or t("waiting")),
        },
        {
            "title": t("step_shipped"),
            "done": merchant_step >= 4,
            "detail": t("step_tracking_link", link=safe_get(order, "merchant_tracking_url", t("not_available"))),
        },
        {
            "title": t("step_delivered_forwarder"),
            "done": merchant_step >= 5,
            "detail": t("step_forwarder_address", address=safe_get(order, "delivery_address", "—")),
        },
    ]

    current_index = None
    for i, step in enumerate(steps):
        if step["done"]:
            current_index = i

    if current_index is None:
        current_index = 0

    return steps, current_index


def render_logistics_timeline(order, title=None):
    st.markdown(f"### {title or t('timeline_title')}")
    steps, current_index = build_timeline_steps(order)

    step_word = "Step" if st.session_state.get("language", "fr") == "en" else "Étape"

    for index, step in enumerate(steps, start=1):
        step_position = index - 1

        if step_position < current_index:
            icon = "🟢"
        elif step_position == current_index:
            icon = "🟡"
        else:
            icon = "⚪"

        st.markdown(f"**{icon} {step_word} {index} — {step['title']}**")
        st.caption(step["detail"])


def save_session_token_in_query_params(token: str | None) -> None:
    if token:
        st.query_params["session_token"] = token
    else:
        try:
            del st.query_params["session_token"]
        except Exception:
            pass


def restore_session_from_query_params() -> None:
    if st.session_state.get("logged_in"):
        token = st.session_state.get("session_token")
        if token:
            touch_session(token)
        return

    token = st.query_params.get("session_token")

    if not token:
        return

    row = get_active_session(token)

    if not row:
        save_session_token_in_query_params(None)
        return

    restore_user_session(
        user_id=row["user_id"],
        phone=row["phone"] if "phone" in row.keys() else "",
        name=row["name"] if "name" in row.keys() else "",
        session_token=row["session_token"],
    )

    touch_session(token)


def compute_dual_amounts(merchant_total_amount, merchant_currency):
    currency = str(merchant_currency or "").strip().upper()
    amount = to_float(merchant_total_amount, 0.0)

    if currency == "XAF":
        merchant_xaf = amount
        merchant_eur = xaf_to_eur(amount)
    elif currency == "EUR":
        merchant_eur = amount
        merchant_xaf = eur_to_xaf(amount)
    else:
        merchant_xaf = 0.0
        merchant_eur = 0.0

    return merchant_xaf, merchant_eur


def calculate_afripay_fee(merchant_eur):
    merchant_eur = to_float(merchant_eur, 0.0)

    if merchant_eur <= 0:
        return 0.0, 0.0

    fee_eur = merchant_eur * AFRIPAY_PERCENT_FEE
    fee_xaf = _round_xaf(eur_to_xaf(fee_eur))
    return fee_xaf, fee_eur


def compute_payment_preview(merchant_total_amount, merchant_currency):
    merchant_xaf, merchant_eur = compute_dual_amounts(
        merchant_total_amount,
        merchant_currency,
    )

    afripay_fee_xaf, afripay_fee_eur = calculate_afripay_fee(merchant_eur)

    total_to_pay_xaf = _round_xaf(merchant_xaf + afripay_fee_xaf)
    total_to_pay_eur = merchant_eur + afripay_fee_eur

    return {
        "merchant_xaf": merchant_xaf,
        "merchant_eur": merchant_eur,
        "afripay_fee_xaf": afripay_fee_xaf,
        "afripay_fee_eur": afripay_fee_eur,
        "total_to_pay_xaf": total_to_pay_xaf,
        "total_to_pay_eur": total_to_pay_eur,
    }


def get_user_free_context():
    user = None
    free_orders_used = 0
    plan = "FREE"

    user_id = st.session_state.get("user_id")
    if user_id:
        user = get_user_by_id(user_id)

    if user:
        free_orders_used = int(user.get("free_orders_used", 0) or 0)
        plan = str(user.get("plan", "FREE") or "FREE").strip().upper()

    remaining_orders = max(0, FREE_ORDERS_LIMIT - free_orders_used)
    is_premium = plan == "PREMIUM"

    return {
        "user": user,
        "free_orders_used": free_orders_used,
        "remaining_orders": remaining_orders,
        "plan": plan,
        "is_premium": is_premium,
    }


def apply_freemium_to_preview(preview: dict):
    adjusted = dict(preview)
    free_context = get_user_free_context()

    merchant_xaf_rounded = _round_xaf(adjusted.get("merchant_xaf", 0))

    free_applied = (
        not free_context["is_premium"]
        and free_context["remaining_orders"] > 0
        and merchant_xaf_rounded <= FREE_ORDER_MAX_XAF
    )

    if free_applied:
        adjusted["afripay_fee_xaf"] = 0
        adjusted["afripay_fee_eur"] = 0.0
        adjusted["total_to_pay_xaf"] = _round_xaf(adjusted["merchant_xaf"])
        adjusted["total_to_pay_eur"] = adjusted["merchant_eur"]

    adjusted["free_applied"] = free_applied
    adjusted["free_remaining_orders"] = free_context["remaining_orders"]
    adjusted["user_plan"] = free_context["plan"]
    adjusted["is_premium"] = free_context["is_premium"]
    adjusted["free_orders_used"] = free_context["free_orders_used"]
    adjusted["free_order_max_xaf"] = FREE_ORDER_MAX_XAF

    return adjusted


def render_freemium_order_info(preview: dict) -> None:
    is_fr = st.session_state.get("language", "fr") == "fr"

    if preview.get("is_premium"):
        if is_fr:
            st.success("✨ Compte PREMIUM détecté.")
        else:
            st.success("✨ PREMIUM account detected.")
        return

    merchant_xaf_rounded = _round_xaf(preview.get("merchant_xaf", 0))
    remaining_orders = int(preview.get("free_remaining_orders", 0) or 0)

    if preview.get("free_applied"):
        if is_fr:
            st.success(
                f"🎁 Offre FREE appliquée : les frais AfriPay sont offerts sur cette commande.\n\n"
                f"Le montant marchand reste payable.\n"
                f"Il vous restera {max(0, remaining_orders - 1)} commande(s) FREE après validation."
            )
        else:
            st.success(
                f"🎁 FREE offer applied: AfriPay fees are waived for this order.\n\n"
                f"The merchant amount remains payable.\n"
                f"You will have {max(0, remaining_orders - 1)} FREE order(s) left after validation."
            )
        return

    if remaining_orders <= 0:
        if is_fr:
            st.info("ℹ️ Offre FREE non appliquée : vos 2 commandes FREE sont déjà utilisées.")
        else:
            st.info("ℹ️ FREE offer not applied: your 2 FREE orders have already been used.")
        return

    if merchant_xaf_rounded > FREE_ORDER_MAX_XAF:
        if is_fr:
            st.info(
                f"ℹ️ Offre FREE non appliquée : une commande FREE est limitée à {format_xaf(FREE_ORDER_MAX_XAF)} XAF.\n\n"
                f"Le montant marchand reste payable et les frais AfriPay standards s’appliquent."
            )
        else:
            st.info(
                f"ℹ️ FREE offer not applied: one FREE order is limited to {format_xaf(FREE_ORDER_MAX_XAF)} XAF.\n\n"
                f"The merchant amount remains payable and standard AfriPay fees apply."
            )


def build_whatsapp_order_message(
    order_code,
    product_title,
    merchant_total_amount,
    merchant_currency,
    product_url,
    payment_preview=None,
):
    clean_product_title = str(product_title or "").strip() or t("product_or_service_unspecified")
    clean_product_url = str(product_url or "").strip()
    currency = str(merchant_currency or "").strip().upper() or "EUR"

    preview = payment_preview or compute_payment_preview(merchant_total_amount, currency)

    lines = [
        t("whatsapp_hello"),
        "",
        t("whatsapp_order_created"),
        "",
        f"{t('reference')} : {order_code}",
        f"{t('product_service')} : {clean_product_title}",
        "",
        t("whatsapp_financial_summary"),
        f"{t('merchant_amount')} : {format_xaf(preview['merchant_xaf'])} XAF ({format_eur(preview['merchant_eur'])} EUR)",
        f"{t('afripay_fee')} : {format_xaf(preview['afripay_fee_xaf'])} XAF ({format_eur(preview['afripay_fee_eur'])} EUR)",
        f"{t('total_to_pay')} : {format_xaf(preview['total_to_pay_xaf'])} XAF ({format_eur(preview['total_to_pay_eur'])} EUR)",
        t("whatsapp_origin_currency", currency=currency),
    ]

    if clean_product_url:
        lines.extend(
            [
                "",
                t("whatsapp_product_link_title"),
                clean_product_url,
            ]
        )

    lines.extend(
        [
            "",
            t("whatsapp_track_order"),
            "",
            t("whatsapp_marketing_1"),
            "",
            t("whatsapp_marketing_2"),
            "",
            t("whatsapp_marketing_3"),
            AFRIPAY_PUBLIC_URL,
            "",
            t("whatsapp_brand"),
            t("whatsapp_tagline"),
        ]
    )

    return "\n".join(lines)


def build_payment_proof_whatsapp_message(order_code, amount_xaf, momo_provider):
    provider = str(momo_provider or "").strip()
    if not provider:
        provider = "MTN MoMo / Orange Money"

    lines = [
        t("payment_proof_message_intro"),
        "",
        t("payment_proof_message_confirm"),
        "",
        t("payment_proof_message_reference", order_code=order_code),
        t("payment_proof_message_amount", amount_xaf=format_xaf(amount_xaf)),
        t("payment_proof_message_operator", provider=provider),
        "",
        t("payment_proof_message_screenshot"),
        "",
        t("payment_proof_message_thanks"),
    ]
    return "\n".join(lines)


def build_referral_whatsapp_message():
    lines = [
        t("referral_hello"),
        "",
        t("referral_intro"),
        "",
        t("referral_body_1"),
        "",
        t("referral_examples_title"),
        t("referral_examples"),
        "",
        t("referral_cta"),
        AFRIPAY_PUBLIC_URL,
        "",
        t("whatsapp_brand"),
        t("whatsapp_tagline"),
    ]
    return "\n".join(lines)


def build_whatsapp_share_url(message: str) -> str:
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/?text={encoded_message}"


def build_whatsapp_direct_url(phone_number: str, message: str) -> str:
    clean_phone = "".join(ch for ch in str(phone_number or "") if ch.isdigit())
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_message}"


def refresh_captcha(prefix: str) -> None:
    a = secrets.randbelow(8) + 2
    b = secrets.randbelow(8) + 1
    st.session_state[f"{prefix}_captcha_a"] = a
    st.session_state[f"{prefix}_captcha_b"] = b
    st.session_state[f"{prefix}_captcha_expected"] = str(a + b)


def ensure_captcha(prefix: str) -> None:
    expected_key = f"{prefix}_captcha_expected"
    if expected_key not in st.session_state:
        refresh_captcha(prefix)


def get_captcha_error(prefix: str) -> str:
    return str(st.session_state.get(f"{prefix}_captcha_error", "")).strip()


def set_captcha_error(prefix: str, message: str) -> None:
    st.session_state[f"{prefix}_captcha_error"] = str(message or "").strip()


def clear_captcha_error(prefix: str) -> None:
    st.session_state[f"{prefix}_captcha_error"] = ""


def get_captcha_status(prefix: str, user_input: str) -> str:
    expected = str(st.session_state.get(f"{prefix}_captcha_expected", "")).strip()
    provided = str(user_input or "").strip()

    if not provided:
        return "empty"

    if not expected:
        return "missing"

    if provided != expected:
        return "invalid"

    return "ok"


def render_captcha_block(prefix: str, title: str = None, allow_refresh: bool = True) -> str:
    ensure_captcha(prefix)

    a = st.session_state.get(f"{prefix}_captcha_a", 0)
    b = st.session_state.get(f"{prefix}_captcha_b", 0)

    st.markdown(f"### {title or t('captcha_title')}")
    st.warning(t("captcha_required"))
    st.info(t("captcha_info", a=a, b=b))

    existing_error = get_captcha_error(prefix)
    if existing_error:
        st.error(existing_error)

    if allow_refresh:
        col1, col2 = st.columns([3, 1])
    else:
        col1 = st.container()
        col2 = None

    with col1:
        captcha_input = st.text_input(
            t("captcha_input"),
            key=f"{prefix}_captcha_input",
            placeholder=t("captcha_placeholder"),
            help=t("captcha_help"),
        )

        status = get_captcha_status(prefix, captcha_input)
        if captcha_input.strip():
            if status == "ok":
                st.success(t("captcha_ok"))
            elif status in {"invalid", "missing"}:
                st.error(t("captcha_bad"))

    if allow_refresh and col2 is not None:
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(t("captcha_refresh"), key=f"{prefix}_captcha_refresh"):
                refresh_captcha(prefix)
                clear_captcha_error(prefix)
                st.rerun()

    st.caption(t("captcha_caption"))
    return captcha_input


def get_menu_options():
    return [
        MENU_LOGIN,
        MENU_DASHBOARD,
        MENU_TRACKING,
        MENU_SIMULATE,
        MENU_CREATE_ORDER,
        MENU_MY_ORDERS,
        MENU_ADMIN,
    ]


def get_menu_label(menu_key: str) -> str:
    mapping = {
        MENU_LOGIN: t("menu_connexion"),
        MENU_DASHBOARD: t("menu_dashboard"),
        MENU_TRACKING: t("menu_tracking"),
        MENU_SIMULATE: t("menu_simulate"),
        MENU_CREATE_ORDER: t("menu_create_order"),
        MENU_MY_ORDERS: t("menu_my_orders"),
        MENU_ADMIN: t("menu_admin"),
    }
    return mapping.get(menu_key, menu_key)


def init_navigation_state() -> None:
    if "main_menu" not in st.session_state:
        st.session_state["main_menu"] = MENU_LOGIN


def schedule_menu_redirect(menu_key: str) -> None:
    if menu_key in get_menu_options():
        st.session_state["pending_main_menu"] = menu_key


def apply_pending_menu_redirect() -> None:
    pending_menu = st.session_state.pop("pending_main_menu", None)
    if pending_menu in get_menu_options():
        st.session_state["main_menu"] = pending_menu


def consume_flash_message() -> None:
    flash_message = st.session_state.pop("flash_message", "")
    if flash_message:
        st.success(flash_message)


def render_test_otp_panel(current_phone: str = "") -> None:
    current_phone = str(current_phone or "").strip()
    otp_code = str(st.session_state.get("otp_code", "") or "").strip()
    otp_phone = str(st.session_state.get("otp_phone", "") or "").strip()

    if not otp_code:
        st.info(t("otp_none"))
        return

    if current_phone and otp_phone and current_phone != otp_phone:
        st.warning(t("otp_other_phone"))

    st.markdown(t("otp_test_mode"))
    st.warning(t("otp_test_warning"))

    st.markdown(
        f"""
<div style="
    border: 3px solid #16a34a;
    border-radius: 16px;
    padding: 22px;
    margin: 12px 0 18px 0;
    background-color: rgba(22, 163, 74, 0.10);
    text-align: center;
">
    <div style="font-size: 18px; font-weight: 800; margin-bottom: 12px;">
        {t("otp_linked_phone")}
    </div>
    <div style="font-size: 28px; font-weight: 900; margin-bottom: 18px;">
        {otp_phone or "—"}
    </div>
    <div style="font-size: 18px; font-weight: 800; margin-bottom: 10px;">
        {t("otp_test_code")}
    </div>
    <div style="font-size: 46px; font-weight: 900; letter-spacing: 10px; line-height: 1.2;">
        {otp_code}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.info(t("otp_keep_info"))


def clear_login_test_otp() -> None:
    st.session_state.pop("otp_code", None)
    st.session_state.pop("otp_phone", None)


def request_login_form_reset() -> None:
    st.session_state["reset_login_form_pending"] = True


def apply_login_form_reset_if_needed() -> None:
    if not st.session_state.pop("reset_login_form_pending", False):
        return

    st.session_state["login_phone_input"] = ""
    st.session_state["login_otp_input"] = ""
    st.session_state["login_name_input"] = ""
    st.session_state["login_email_input"] = ""


def init_otp_rate_limit_state() -> None:
    if "otp_request_log" not in st.session_state:
        st.session_state["otp_request_log"] = {}


def get_now_utc() -> datetime:
    return datetime.utcnow()


def get_phone_otp_requests(phone: str):
    init_otp_rate_limit_state()

    clean_phone = str(phone or "").strip()
    if not clean_phone:
        return []

    raw_requests = st.session_state["otp_request_log"].get(clean_phone, [])
    now = get_now_utc()
    window_start = now - timedelta(minutes=OTP_WINDOW_MINUTES)

    valid_requests = []
    for item in raw_requests:
        if isinstance(item, datetime) and item >= window_start:
            valid_requests.append(item)

    st.session_state["otp_request_log"][clean_phone] = valid_requests
    return valid_requests


def record_otp_request(phone: str) -> None:
    init_otp_rate_limit_state()

    clean_phone = str(phone or "").strip()
    if not clean_phone:
        return

    requests = get_phone_otp_requests(clean_phone)
    requests.append(get_now_utc())
    st.session_state["otp_request_log"][clean_phone] = requests


def get_otp_rate_limit_status(phone: str) -> dict:
    clean_phone = str(phone or "").strip()
    if not clean_phone:
        return {
            "allowed": True,
            "reason": "",
            "wait_seconds": 0,
            "wait_minutes": 0,
        }

    requests = get_phone_otp_requests(clean_phone)
    now = get_now_utc()

    if requests:
        last_request = requests[-1]
        cooldown_end = last_request + timedelta(seconds=OTP_COOLDOWN_SECONDS)

        if now < cooldown_end:
            remaining_seconds = int((cooldown_end - now).total_seconds()) + 1
            return {
                "allowed": False,
                "reason": "cooldown",
                "wait_seconds": remaining_seconds,
                "wait_minutes": 0,
            }

    if len(requests) >= OTP_MAX_REQUESTS:
        oldest_relevant_request = requests[0]
        retry_at = oldest_relevant_request + timedelta(minutes=OTP_WINDOW_MINUTES)

        if now < retry_at:
            remaining_seconds = int((retry_at - now).total_seconds()) + 1
            remaining_minutes = max(1, (remaining_seconds + 59) // 60)
            return {
                "allowed": False,
                "reason": "window_limit",
                "wait_seconds": remaining_seconds,
                "wait_minutes": remaining_minutes,
            }

    return {
        "allowed": True,
        "reason": "",
        "wait_seconds": 0,
        "wait_minutes": 0,
    }


def get_order_type_options():
    return [ORDER_TYPE_PHYSICAL_KEY, ORDER_TYPE_SERVICE_KEY]


def get_order_type_label(order_type_key: str) -> str:
    if order_type_key == ORDER_TYPE_PHYSICAL_KEY:
        return "Physical product" if st.session_state.get("language", "fr") == "en" else "Produit physique"
    return "Digital service / payment" if st.session_state.get("language", "fr") == "en" else "Service / paiement digital"


def is_physical_order(order_type_value: str) -> bool:
    return order_type_value == ORDER_TYPE_PHYSICAL_KEY


def init_create_order_state() -> None:
    defaults = {
        "create_order_type": ORDER_TYPE_PHYSICAL_KEY,
        "create_order_amount": 0.0,
        "create_order_currency": "XAF",
        "create_order_product_url": "",
        "create_order_product_title": "",
        "create_order_site_name": "",
        "create_order_product_specs": "",
        "create_order_delivery_address": "",
        "create_order_momo_provider": "",
        "create_order_client_ack": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def request_create_order_form_reset() -> None:
    st.session_state["reset_create_order_form_pending"] = True


def apply_create_order_form_reset_if_needed() -> None:
    if not st.session_state.pop("reset_create_order_form_pending", False):
        return

    st.session_state["create_order_type"] = ORDER_TYPE_PHYSICAL_KEY
    st.session_state["create_order_amount"] = 0.0
    st.session_state["create_order_currency"] = "XAF"
    st.session_state["create_order_product_url"] = ""
    st.session_state["create_order_product_title"] = ""
    st.session_state["create_order_site_name"] = ""
    st.session_state["create_order_product_specs"] = ""
    st.session_state["create_order_delivery_address"] = ""
    st.session_state["create_order_momo_provider"] = ""
    st.session_state["create_order_client_ack"] = False


def has_create_order_draft_data() -> bool:
    return any([
        str(st.session_state.get("create_order_product_url", "")).strip(),
        str(st.session_state.get("create_order_product_title", "")).strip(),
        str(st.session_state.get("create_order_site_name", "")).strip(),
        str(st.session_state.get("create_order_product_specs", "")).strip(),
        str(st.session_state.get("create_order_delivery_address", "")).strip(),
        str(st.session_state.get("create_order_momo_provider", "")).strip(),
        bool(st.session_state.get("create_order_client_ack", False)),
        to_float(st.session_state.get("create_order_amount", 0.0), 0.0) > 0,
    ])


def render_sidebar() -> str:
    render_sidebar_branding()

    current_language = st.sidebar.selectbox(
        t("language"),
        options=[LANG_FR, LANG_EN],
        index=0 if st.session_state.get("language", "fr") == "fr" else 1,
        key="language_selector",
    )

    new_language = "fr" if current_language == LANG_FR else "en"
    if new_language != st.session_state.get("language", "fr"):
        st.session_state["language"] = new_language
        st.rerun()

    is_fr = st.session_state.get("language", "fr") == "fr"
    free_context = get_user_free_context()
    remaining_orders = free_context["remaining_orders"]
    is_premium = free_context["is_premium"]

    badge_label = "PREMIUM" if is_premium else "FREE"
    badge_class = "afripay-plan-premium" if is_premium else "afripay-plan-free"

    st.sidebar.markdown(
        f'<div class="afripay-plan-badge {badge_class}">{badge_label}</div>',
        unsafe_allow_html=True,
    )

    sidebar_free_plan_title = "🎁 OFFRE GRATUITE" if is_fr else "🎁 FREE OFFER"

    if is_premium:
        sidebar_free_plan_text = "✨ Compte Premium actif" if is_fr else "✨ Premium account active"
    else:
        if remaining_orders > 0:
            if is_fr:
                sidebar_free_plan_text = (
                    f"Il vous reste {remaining_orders} commande(s)<br>"
                    f"Max : 50 000 XAF par commande"
                )
            else:
                sidebar_free_plan_text = (
                    f"You have {remaining_orders} order(s) left<br>"
                    f"Max: 50,000 XAF per order"
                )
        else:
            if is_fr:
                sidebar_free_plan_text = (
                    "❌ Offre gratuite terminée<br>"
                    "<b>👉 Passez en Premium pour continuer vos commandes</b>"
                )
            else:
                sidebar_free_plan_text = (
                    "❌ Free offer exhausted<br>"
                    "<b>👉 Upgrade to Premium to continue ordering</b>"
                )


    st.sidebar.markdown(
    f"""
    <div style="
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 14px;
        padding: 12px 14px;
        margin: 10px 0 14px 0;
    ">
        <div style="color:#FACC15; font-weight:700;">
            {sidebar_free_plan_title}
        </div>
        <div style="color:#22C55E;">
            {sidebar_free_plan_text}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

    if st.session_state.get("logged_in"):
        st.sidebar.success(t("connected"))
        connected_phone = st.session_state.get("phone", "")
        if connected_phone:
            st.sidebar.caption(t("phone_caption", phone=connected_phone))

        if st.sidebar.button(t("logout")):
            token = st.session_state.get("session_token")

            if token:
                deactivate_session(token)

            save_session_token_in_query_params(None)
            clear_login_test_otp()
            logout_user()
            schedule_menu_redirect(MENU_LOGIN)
            st.rerun()
    else:
        st.sidebar.info(t("not_connected"))

    st.sidebar.markdown("---")

    st.sidebar.radio(
        t("menu"),
        options=get_menu_options(),
        key="main_menu",
        format_func=get_menu_label,
    )

    return st.session_state["main_menu"]


def page_connexion() -> None:
    apply_login_form_reset_if_needed()

    st.title(t("page_login_title"))

    lang = st.session_state.get("language", "fr")

    base_dir = Path(__file__).resolve().parent
    assets_dir = base_dir / "assets"

    hero_banner_fr = assets_dir / "hero_banner_fr.png"
    hero_banner_en = assets_dir / "hero_banner_en.png"
    logo_path = assets_dir / "logo.png"

    if lang == "fr":
        banner_path = hero_banner_fr if hero_banner_fr.exists() else hero_banner_en
    else:
        banner_path = hero_banner_en if hero_banner_en.exists() else hero_banner_fr

    if banner_path.exists():
        img = Image.open(banner_path)
        st.image(img, width="stretch")
    elif logo_path.exists():
        img = Image.open(logo_path)
        st.image(img, width="stretch")

    consume_flash_message()

    st.markdown(t("page_login_intro_1"))
    st.markdown(t("page_login_intro_2"))
    st.info(t("login_info"))

    default_phone = str(st.session_state.get("otp_phone", "") or "")
    if "login_phone_input" not in st.session_state:
        st.session_state["login_phone_input"] = default_phone
    elif default_phone and not str(st.session_state.get("login_phone_input", "")).strip():
        st.session_state["login_phone_input"] = default_phone

    phone = st.text_input(
        t("phone"),
        key="login_phone_input",
        placeholder="+2376...",
    )

    render_test_otp_panel(current_phone=phone)
    st.caption(t("otp_limit_info"))

    captcha_input = render_captcha_block("login", title=t("captcha_title"), allow_refresh=True)

    if st.button(t("send_otp"), width="stretch"):
        clean_phone = str(phone or "").strip()

        if not clean_phone:
            st.error(t("enter_phone"))
            return

        captcha_status = get_captcha_status("login", captcha_input)

        if captcha_status == "empty":
            set_captcha_error("login", t("captcha_empty_otp"))
            st.rerun()
            return

        if captcha_status in {"invalid", "missing"}:
            set_captcha_error("login", t("captcha_invalid_otp"))
            refresh_captcha("login")
            st.rerun()
            return

        clear_captcha_error("login")

        otp_limit_status = get_otp_rate_limit_status(clean_phone)

        if not otp_limit_status["allowed"]:
            if otp_limit_status["reason"] == "cooldown":
                st.error(
                    t(
                        "otp_wait_before_retry",
                        seconds=otp_limit_status["wait_seconds"],
                    )
                )
                return

            if otp_limit_status["reason"] == "window_limit":
                st.error(
                    t(
                        "otp_too_many_requests",
                        minutes=otp_limit_status["wait_minutes"],
                    )
                )
                return

        otp = f"{secrets.randbelow(900000) + 100000}"
        st.session_state["otp_code"] = otp
        st.session_state["otp_phone"] = clean_phone
        st.session_state["login_otp_input"] = ""

        record_otp_request(clean_phone)

        st.success(t("otp_success"))
        st.rerun()

    otp_input = st.text_input(
        t("enter_otp"),
        key="login_otp_input",
        placeholder=t("otp_placeholder"),
    )
    name = st.text_input(t("name"), key="login_name_input", placeholder=t("optional"))
    email = st.text_input(t("email"), key="login_email_input", placeholder=t("optional"))

    if st.button(t("login_button"), width="stretch"):
        stored_otp = str(st.session_state.get("otp_code", "") or "").strip()
        stored_phone = str(st.session_state.get("otp_phone", "") or "").strip()
        clean_phone = str(phone or "").strip()

        if not stored_otp:
            st.error(t("ask_otp_first"))
            return

        if not clean_phone:
            st.error(t("phone_used_for_otp"))
            return

        if clean_phone != stored_phone:
            st.error(t("phone_different"))
            return

        if str(otp_input or "").strip() != stored_otp:
            st.error(t("otp_incorrect"))
            return

        clean_name = str(name or "").strip()
        clean_email = str(email or "").strip()

        user_id = upsert_user(
            phone=clean_phone,
            name=clean_name,
            email=clean_email,
        )

        session_token = create_user_session(
            user_id=user_id,
            phone=clean_phone,
        )

        login_user(
            user_id=user_id,
            phone=clean_phone,
            name=clean_name,
            session_token=session_token,
        )

        save_session_token_in_query_params(session_token)

        clear_captcha_error("login")
        refresh_captcha("login")
        clear_login_test_otp()
        request_login_form_reset()

        st.session_state["flash_message"] = t("login_success")
        schedule_menu_redirect(MENU_CREATE_ORDER)
        st.rerun()


def page_dashboard_client() -> None:
    st.title(t("dashboard_title"))
    consume_flash_message()

    if not st.session_state.get("logged_in"):
        st.warning(t("need_login_dashboard"))
        return

    rows = list_orders_for_user(int(st.session_state["user_id"]))

    total_orders = len(rows)
    paid_orders = 0
    in_progress_orders = 0
    delivered_orders = 0
    cancelled_orders = 0

    total_xaf_sum = 0.0
    total_eur_sum = 0.0

    status_counter = Counter()
    monthly_orders = defaultdict(int)
    monthly_volume = defaultdict(float)

    for row in rows:
        raw_status = str(safe_get(row, "order_status", "")).upper()
        total_xaf = to_float(safe_get(row, "total_xaf", 0), 0.0)
        total_eur = to_float(safe_get(row, "total_to_pay_eur", 0), 0.0)

        total_xaf_sum += total_xaf
        total_eur_sum += total_eur

        if raw_status == "PAYEE":
            paid_orders += 1
        elif raw_status == "EN_COURS":
            in_progress_orders += 1
        elif raw_status == "LIVREE":
            delivered_orders += 1
        elif raw_status == "ANNULEE":
            cancelled_orders += 1

        status_counter[normalize_status(raw_status)] += 1

        created_at = parse_date(safe_get(row, "created_at", ""))
        if created_at:
            key = created_at.strftime("%Y-%m")
            monthly_orders[key] += 1
            monthly_volume[key] += total_xaf

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("my_orders_metric"), total_orders)
    c2.metric(t("paid_metric"), paid_orders)
    c3.metric(t("in_progress_metric"), in_progress_orders)
    c4.metric(t("delivered_metric"), delivered_orders)

    c5, c6, c7 = st.columns(3)
    c5.metric(t("cancelled_metric"), cancelled_orders)
    c6.metric(t("cumulated_xaf"), f"{format_xaf(total_xaf_sum)} XAF")
    c7.metric(t("cumulated_eur"), f"{format_eur(total_eur_sum)} €")

    st.markdown("---")
    st.subheader(t("summary_client"))
    st.info(t("summary_client_info"))

    if not rows:
        st.info(t("no_orders"))
        return

    col_chart_1, col_chart_2 = st.columns(2)

    with col_chart_1:
        st.markdown(t("status_chart"))
        if status_counter:
            status_data = {
                "Statut": list(status_counter.keys()),
                "Commandes": list(status_counter.values()),
            }
            st.bar_chart(status_data, x="Statut", y="Commandes", width="stretch")
        else:
            st.info(t("status_chart_empty"))

    with col_chart_2:
        st.markdown(t("monthly_evolution"))
        if monthly_orders:
            sorted_keys = sorted(monthly_orders.keys())
            evolution_data = {
                "Mois": [month_label(datetime.strptime(k, "%Y-%m")) for k in sorted_keys],
                "Commandes": [monthly_orders[k] for k in sorted_keys],
            }
            st.line_chart(evolution_data, x="Mois", y="Commandes", width="stretch")
        else:
            st.info(t("monthly_evolution_empty"))

    st.markdown(t("monthly_volume"))
    if monthly_volume:
        sorted_keys = sorted(monthly_volume.keys())
        volume_data = {
            "Mois": [month_label(datetime.strptime(k, "%Y-%m")) for k in sorted_keys],
            "Montant_XAF": [monthly_volume[k] for k in sorted_keys],
        }
        st.area_chart(volume_data, x="Mois", y="Montant_XAF", width="stretch")
    else:
        st.info(t("monthly_volume_empty"))

    st.markdown("---")

    latest = rows[0]

    merchant_total_amount = to_float(safe_get(latest, "merchant_total_amount", 0), 0.0)
    merchant_currency = safe_get(latest, "merchant_currency", "XAF")
    merchant_xaf, merchant_eur = compute_dual_amounts(merchant_total_amount, merchant_currency)

    st.subheader(t("latest_order"))
    info1, info2 = st.columns(2)

    with info1:
        st.write(f"**{t('reference')} :** {safe_get(latest, 'order_code', '—')}")
        st.write(f"**{t('product_service')} :** {get_product_label(latest)}")
        st.write(f"**{t('merchant')} :** {safe_get(latest, 'site_name', '—')}")
        st.write(f"**{t('merchant_amount')} :** {format_xaf(merchant_xaf)} XAF ({format_eur(merchant_eur)} €)")
        st.write(f"**{t('afripay_fee')} :** {format_xaf(safe_get(latest, 'afripay_fee_xaf', 0))} XAF")
        st.write(f"**{t('total_paid')} :** {format_xaf(safe_get(latest, 'total_xaf', 0))} XAF")

    with info2:
        st.write(f"**{t('total_eur')} :** {format_eur(safe_get(latest, 'total_to_pay_eur', 0))} €")
        st.write(f"**{t('order_status')} :** {normalize_status(safe_get(latest, 'order_status', '—'))}")
        st.write(f"**{t('payment_status')} :** {normalize_payment_status(safe_get(latest, 'payment_status', '—'))}")
        st.write(f"**{t('forwarder_address')} :** {safe_get(latest, 'delivery_address', '—')}")

    render_logistics_timeline(latest)

    merchant_order_number = safe_get(latest, "merchant_order_number", "")
    merchant_confirmation_url = safe_get(latest, "merchant_confirmation_url", "")
    merchant_tracking_url = safe_get(latest, "merchant_tracking_url", "")
    merchant_purchase_date = safe_get(latest, "merchant_purchase_date", "")
    merchant_status = safe_get(latest, "merchant_status", "")

    if any([
        merchant_order_number,
        merchant_confirmation_url,
        merchant_tracking_url,
        merchant_purchase_date,
        merchant_status,
    ]):
        st.markdown(f"### {t('merchant_info')}")
        if merchant_order_number:
            st.write(f"**{t('merchant_order_number')} :** {merchant_order_number}")
        if merchant_purchase_date:
            st.write(f"**{t('purchase_date')} :** {merchant_purchase_date}")
        if merchant_status:
            st.write(f"**{t('merchant_status')} :** {merchant_status}")
        if merchant_confirmation_url:
            st.write(f"**{t('confirmation_link')} :** {merchant_confirmation_url}")
        if merchant_tracking_url:
            st.write(f"**{t('tracking_link')} :** {merchant_tracking_url}")


def page_tracking() -> None:
    st.title(t("tracking_title"))
    st.caption(t("tracking_caption"))

    order_code = st.text_input(t("order_number"), placeholder="CMD-2026-001")

    if st.button(t("search")):
        if not order_code.strip():
            st.error(t("enter_order_number"))
            return

        row = get_order_by_code(order_code.strip())

        if not row:
            st.error(t("order_not_found"))
            return

        merchant_total_amount = to_float(safe_get(row, "merchant_total_amount", 0), 0.0)
        merchant_currency = safe_get(row, "merchant_currency", "XAF")
        merchant_xaf, merchant_eur = compute_dual_amounts(merchant_total_amount, merchant_currency)

        st.success(f"{t('order_number')} : **{safe_get(row, 'order_code', '')}**")
        st.write(f"**{t('product_service')} :**", get_product_label(row))
        st.write(f"**{t('merchant')} :**", safe_get(row, "site_name", "—"))
        st.write(f"**{t('merchant_amount')} :**", f"{format_xaf(merchant_xaf)} XAF ({format_eur(merchant_eur)} €)")
        st.write(f"**{t('afripay_fee')} :**", f"{format_xaf(safe_get(row, 'afripay_fee_xaf', 0))} XAF")
        st.write(f"**{t('total_paid')} :**", f"{format_xaf(safe_get(row, 'total_xaf', 0))} XAF")
        st.write(f"**{t('total_eur')} :**", f"{format_eur(safe_get(row, 'total_to_pay_eur', 0))} €")
        st.write(f"**{t('order_status')} :**", normalize_status(safe_get(row, "order_status", "—")))
        st.write(f"**{t('payment_status')} :**", normalize_payment_status(safe_get(row, "payment_status", "—")))
        st.write(f"**{t('forwarder_address')} :**", safe_get(row, "delivery_address", "—"))

        render_logistics_timeline(row)

        merchant_status = safe_get(row, "merchant_status", "")
        merchant_order_number = safe_get(row, "merchant_order_number", "")
        merchant_confirmation_url = safe_get(row, "merchant_confirmation_url", "")
        merchant_tracking_url = safe_get(row, "merchant_tracking_url", "")
        merchant_purchase_date = safe_get(row, "merchant_purchase_date", "")

        if any([
            merchant_status,
            merchant_order_number,
            merchant_confirmation_url,
            merchant_tracking_url,
            merchant_purchase_date,
        ]):
            st.subheader(t("merchant_info"))
            if merchant_order_number:
                st.write(f"**{t('merchant_order_number')} :**", merchant_order_number)
            if merchant_purchase_date:
                st.write(f"**{t('purchase_date')} :**", merchant_purchase_date)
            if merchant_status:
                st.write(f"**{t('merchant_status')} :**", merchant_status)
            if merchant_confirmation_url:
                st.write(f"**{t('confirmation_link')} :**", merchant_confirmation_url)
            if merchant_tracking_url:
                st.write(f"**{t('tracking_link')} :**", merchant_tracking_url)
        else:
            st.info(t("merchant_info_not_available"))


def page_simuler() -> None:
    st.title(t("simulate_title"))

    amount_xaf = st.number_input(t("merchant_amount_xaf"), min_value=0.0, value=0.0, step=1000.0)
    seller_fee = st.number_input(t("seller_fee_xaf"), min_value=0.0, value=0.0, step=500.0)
    afripay_fee = st.number_input(t("afripay_fee_xaf"), min_value=0.0, value=0.0, step=500.0)

    total = amount_xaf + seller_fee + afripay_fee
    st.metric(t("total_to_pay_xaf"), f"{format_xaf(total)} XAF")


def render_payment_summary(preview):
    st.markdown(t("financial_summary"))

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(t("values_xaf"))
        st.metric(t("merchant_amount"), f"{format_xaf(preview['merchant_xaf'])} XAF")
        st.metric(t("afripay_fee"), f"{format_xaf(preview['afripay_fee_xaf'])} XAF")
        st.metric(t("total_to_pay"), f"{format_xaf(preview['total_to_pay_xaf'])} XAF")

    with c2:
        st.markdown(t("values_eur"))
        st.metric(t("merchant_amount"), f"{format_eur(preview['merchant_eur'])} EUR")
        st.metric(t("afripay_fee"), f"{format_eur(preview['afripay_fee_eur'])} EUR")
        st.metric(t("total_to_pay"), f"{format_eur(preview['total_to_pay_eur'])} EUR")

    st.info(t("pricing_info", percent=int(AFRIPAY_PERCENT_FEE * 100)))


def render_post_order_actions(order_data: dict) -> None:
    order_code = str(order_data.get("order_code", "")).strip()
    product_title = str(order_data.get("product_title", "")).strip()
    product_url = str(order_data.get("product_url", "")).strip()
    merchant_total_amount = to_float(order_data.get("merchant_total_amount", 0.0), 0.0)
    merchant_currency = str(order_data.get("merchant_currency", "EUR")).strip().upper() or "EUR"
    momo_provider = str(order_data.get("momo_provider", "")).strip() or "MTN MoMo / Orange Money"
    total_to_pay_xaf = to_float(order_data.get("total_to_pay_xaf", 0.0), 0.0)

    st.success(t("order_created", order_code=order_code))
    st.info(t("order_saved_info"))

    if "merchant_xaf" in order_data:
        preview = {
            "merchant_xaf": to_float(order_data.get("merchant_xaf", 0.0), 0.0),
            "merchant_eur": to_float(order_data.get("merchant_eur", 0.0), 0.0),
            "afripay_fee_xaf": to_float(order_data.get("afripay_fee_xaf", 0.0), 0.0),
            "afripay_fee_eur": to_float(order_data.get("afripay_fee_eur", 0.0), 0.0),
            "total_to_pay_xaf": to_float(order_data.get("total_to_pay_xaf", 0.0), 0.0),
            "total_to_pay_eur": to_float(order_data.get("total_to_pay_eur", 0.0), 0.0),
        }
    else:
        preview = compute_payment_preview(
            merchant_total_amount,
            merchant_currency,
        )

    st.success(
        t(
            "estimated_summary",
            merchant_xaf=format_xaf(preview["merchant_xaf"]),
            merchant_eur=format_eur(preview["merchant_eur"]),
            fee_xaf=format_xaf(preview["afripay_fee_xaf"]),
            fee_eur=format_eur(preview["afripay_fee_eur"]),
            total_xaf=format_xaf(preview["total_to_pay_xaf"]),
            total_eur=format_eur(preview["total_to_pay_eur"]),
        )
    )

    whatsapp_message = build_whatsapp_order_message(
        order_code=order_code,
        product_title=product_title,
        merchant_total_amount=merchant_total_amount,
        merchant_currency=merchant_currency,
        product_url=product_url,
        payment_preview=preview,
    )
    whatsapp_url = build_whatsapp_share_url(whatsapp_message)

    st.markdown(t("share_order_title"))
    st.link_button(
        t("share_whatsapp"),
        whatsapp_url,
        width="stretch",
    )

    with st.expander(t("see_whatsapp_message")):
        st.code(whatsapp_message)

    payment_proof_message = build_payment_proof_whatsapp_message(
        order_code=order_code,
        amount_xaf=total_to_pay_xaf,
        momo_provider=momo_provider,
    )
    payment_proof_url = build_whatsapp_direct_url(
        get_whatsapp_number("CM"),
        payment_proof_message,
    )

    st.markdown(t("payment_proof_title"))
    st.info(t("payment_proof_help"))

    if st.button(
        t("prepare_payment_proof"),
        key=f"prepare_proof_{order_code}",
        width="stretch",
    ):
        updated = mark_payment_proof_sent(order_code, momo_provider)
        if updated:
            st.success(t("payment_proof_status_updated"))
        else:
            st.info(t("payment_proof_status_already"))

    st.link_button(
        t("send_payment_proof_whatsapp"),
        payment_proof_url,
        width="stretch",
    )

    with st.expander(t("see_payment_proof_message")):
        st.code(payment_proof_message)

    referral_message = build_referral_whatsapp_message()
    referral_url = build_whatsapp_share_url(referral_message)

    st.markdown(t("referral_title"))
    st.info(t("referral_help"))
    st.link_button(
        t("referral_button"),
        referral_url,
        width="stretch",
    )

    with st.expander(t("see_referral_message")):
        st.code(referral_message)


def page_creer_commande() -> None:
    init_create_order_state()
    apply_create_order_form_reset_if_needed()

    st.title(t("create_order_title"))
    consume_flash_message()

    if not st.session_state.get("logged_in"):
        st.warning(t("need_login_create_order"))
        return

    st.info(t("create_order_step_info"))
    st.info(t("create_order_info"))

    st.markdown(t("how_to_create"))
    st.markdown(t("create_steps"))

    st.warning(t("legal_warning"))
    st.info(t("practical_tip"))

    captcha_input = render_captcha_block("order", title=t("captcha_title"), allow_refresh=True)

    st.markdown(t("payment_parameters"))
    order_type = st.selectbox(
        t("order_type"),
        get_order_type_options(),
        key="create_order_type",
        format_func=get_order_type_label,
        help=t("order_type_help"),
    )

    merchant_total_amount = st.number_input(
        t("merchant_total_displayed"),
        min_value=0.0,
        step=1.0,
        key="create_order_amount",
    )

    merchant_currency = st.selectbox(
        t("merchant_currency"),
        ["XAF", "EUR"],
        key="create_order_currency",
        help=t("merchant_currency_help"),
    )

    payment_preview = compute_payment_preview(
        merchant_total_amount,
        merchant_currency,
    )
    payment_preview = apply_freemium_to_preview(payment_preview)

    render_payment_summary(payment_preview)
    render_freemium_order_info(payment_preview)

    with st.form("create_order_form"):
        st.markdown(t("main_information"))

        product_url = st.text_input(
            t("product_service_link"),
            key="create_order_product_url",
            placeholder=t("product_link_placeholder"),
        )

        st.caption(t("product_link_tip"))

        product_title = st.text_input(
            t("product_service_name"),
            key="create_order_product_title",
            placeholder=t("product_service_name_placeholder"),
        )

        site_name = st.text_input(
            t("merchant_org"),
            key="create_order_site_name",
            placeholder=t("merchant_org_placeholder"),
        )

        product_specs = st.text_area(
            t("details_useful"),
            key="create_order_product_specs",
            placeholder=t("details_useful_placeholder"),
        )

        st.markdown(t("delivery_payment"))

        requires_forwarder = is_physical_order(order_type)

        if requires_forwarder:
            delivery_address = st.text_area(
                t("forwarder_address_label"),
                key="create_order_delivery_address",
                placeholder=t("forwarder_address_placeholder"),
                help=t("forwarder_address_help"),
            )
        else:
            delivery_address = ""
            st.success(t("no_forwarder_required"))

        momo_provider = st.selectbox(
            t("momo_provider"),
            ["", "MTN", "Orange"],
            key="create_order_momo_provider",
        )

        if momo_provider.strip():
            st.caption(t("momo_selected", provider=momo_provider.strip()))
        else:
            st.caption(t("momo_choose"))

        st.caption(t("captcha_validated_above"))

        client_ack = st.checkbox(
            t("client_ack"),
            key="create_order_client_ack",
        )

        lang = st.session_state.get("language", "fr")

        if lang == "en":
            st.info(
                "🎁 Exclusive offer: FREE means AfriPay service fees are waived only.\n\n"
                "The merchant amount remains fully payable.\n"
                "Maximum: 2 FREE orders, and 50,000 XAF per FREE order."
            )
        else:
            st.info(
                "🎁 Offre exclusive : FREE signifie que seuls les frais de service AfriPay sont offerts.\n\n"
                "Le montant marchand reste entièrement payable.\n"
                "Maximum : 2 commandes FREE, et 50.000 XAF par commande FREE."
            )

        submitted = st.form_submit_button(t("create_order_button"), width="stretch")

    if submitted:
        captcha_status = get_captcha_status("order", captcha_input)

        if captcha_status == "empty":
            set_captcha_error("order", t("captcha_empty_order"))
            st.rerun()
            return

        if captcha_status in {"invalid", "missing"}:
            set_captcha_error("order", t("captcha_invalid_order"))
            refresh_captcha("order")
            st.rerun()
            return

        clear_captcha_error("order")

        if not product_url.strip():
            st.error(t("product_link_required"))
            return

        if not product_title.strip():
            st.error(t("product_name_required"))
            return

        if not site_name.strip():
            st.error(t("merchant_required"))
            return

        if merchant_total_amount <= 0:
            st.error(t("amount_required"))
            return

        if requires_forwarder and not delivery_address.strip():
            st.error(t("forwarder_required"))
            return

        if not client_ack:
            st.error(t("ack_required"))
            return

        final_preview = compute_payment_preview(
            merchant_total_amount,
            merchant_currency,
        )
        final_preview = apply_freemium_to_preview(final_preview)

        if str(merchant_currency).strip().upper() == "EUR":
            product_price_eur = to_float(merchant_total_amount, 0.0)
            shipping_estimate_eur = 0.0
        else:
            product_price_eur = final_preview["merchant_eur"]
            shipping_estimate_eur = 0.0

        order_code = create_order_for_user(
            user_id=int(st.session_state["user_id"]),
            client_name=st.session_state.get("name", "").strip(),
            client_phone=st.session_state.get("phone", "").strip(),
            client_email=st.session_state.get("email", "").strip(),
            site_name=site_name.strip(),
            product_url=product_url.strip(),
            product_title=product_title.strip(),
            product_specs=product_specs.strip(),
            product_price_eur=float(product_price_eur),
            shipping_estimate_eur=float(shipping_estimate_eur),
            delivery_address=delivery_address.strip() if requires_forwarder else "",
            momo_provider=momo_provider.strip() or None,
            merchant_total_amount=float(merchant_total_amount),
            merchant_currency=merchant_currency,
            seller_fee_xaf=0,
            afripay_fee_xaf=float(final_preview["afripay_fee_xaf"]),
            total_xaf=float(final_preview["total_to_pay_xaf"]),
            total_to_pay_eur=float(final_preview["total_to_pay_eur"]),
        )

        st.session_state["last_created_order"] = {
            "order_code": order_code,
            "product_title": product_title.strip(),
            "product_url": product_url.strip(),
            "merchant_total_amount": float(merchant_total_amount),
            "merchant_currency": merchant_currency,
            "momo_provider": momo_provider.strip() or "MTN MoMo / Orange Money",
            "merchant_xaf": float(final_preview["merchant_xaf"]),
            "merchant_eur": float(final_preview["merchant_eur"]),
            "afripay_fee_xaf": float(final_preview["afripay_fee_xaf"]),
            "afripay_fee_eur": float(final_preview["afripay_fee_eur"]),
            "total_to_pay_xaf": float(final_preview["total_to_pay_xaf"]),
            "total_to_pay_eur": float(final_preview["total_to_pay_eur"]),
            "free_applied": bool(final_preview.get("free_applied", False)),
        }

        clear_captcha_error("order")
        refresh_captcha("order")
        request_create_order_form_reset()
        st.rerun()

    last_created_order = st.session_state.get("last_created_order")
    if last_created_order and not has_create_order_draft_data():
        render_post_order_actions(last_created_order)


def page_mes_commandes() -> None:
    st.title(t("my_orders_title"))
    consume_flash_message()

    if not st.session_state.get("logged_in"):
        st.warning(t("need_login_my_orders"))
        return

    rows = list_orders_for_user(int(st.session_state["user_id"]))

    if not rows:
        st.info(t("no_orders_short"))
        return

    for row in rows:
        code = safe_get(row, "order_code", f"#{safe_get(row, 'id', '')}")
        total = safe_get(row, "total_xaf", 0)
        status = safe_get(row, "order_status", "—")

        expander_title = f"{code} — {format_xaf(total)} XAF"

        status_badge = render_order_status_badge(status)

        merchant_total_amount = to_float(safe_get(row, "merchant_total_amount", 0), 0.0)
        merchant_currency = safe_get(row, "merchant_currency", "XAF")
        merchant_xaf, merchant_eur = compute_dual_amounts(merchant_total_amount, merchant_currency)

        with st.expander(expander_title):
            st.markdown(status_badge, unsafe_allow_html=True)
            st.write("")

            st.write(f"**{t('created_on')} :** {safe_get(row, 'created_at', '—')}")
            st.write(f"**{t('product_service')} :** {get_product_label(row)}")
            st.write(f"**{t('merchant_org_label')} :** {safe_get(row, 'site_name', '—')}")
            st.write(f"**{t('merchant_amount_label')} :** {format_xaf(merchant_xaf)} XAF ({format_eur(merchant_eur)} €)")
            st.write(f"**{t('afripay_fee')} :** {format_xaf(safe_get(row, 'afripay_fee_xaf', 0))} XAF")
            st.write(f"**{t('total_paid_label')} :** {format_xaf(safe_get(row, 'total_xaf', 0))} XAF ({format_eur(safe_get(row, 'total_to_pay_eur', 0))} €)")
            st.write(f"**{t('seller_fee_label')} :** {format_xaf(safe_get(row, 'seller_fee_xaf', 0))} XAF")
            st.write(f"**{t('forwarder_address_expander')} :** {safe_get(row, 'delivery_address', '—')}")
            st.write(f"**{t('payment_label')} :** {normalize_payment_status(safe_get(row, 'payment_status', '—'))}")
            st.write(f"**{t('status_label')} :** {normalize_status(status)}")

            render_logistics_timeline(row, title=t("timeline_order_title"))

            merchant_order_number = safe_get(row, "merchant_order_number", "")
            merchant_confirmation_url = safe_get(row, "merchant_confirmation_url", "")
            merchant_tracking_url = safe_get(row, "merchant_tracking_url", "")
            merchant_purchase_date = safe_get(row, "merchant_purchase_date", "")
            merchant_status = safe_get(row, "merchant_status", "")

            if any([
                merchant_order_number,
                merchant_confirmation_url,
                merchant_tracking_url,
                merchant_purchase_date,
                merchant_status,
            ]):
                st.markdown(f"### {t('merchant_info')}")
                if merchant_order_number:
                    st.write(f"**{t('merchant_order_number')} :** {merchant_order_number}")
                if merchant_purchase_date:
                    st.write(f"**{t('purchase_date')} :** {merchant_purchase_date}")
                if merchant_status:
                    st.write(f"**{t('merchant_status')} :** {merchant_status}")
                if merchant_confirmation_url:
                    st.write(f"**{t('confirmation_link')} :** {merchant_confirmation_url}")
                if merchant_tracking_url:
                    st.write(f"**{t('tracking_link')} :** {merchant_tracking_url}")


def page_admin() -> None:
    st.title(t("admin_title"))

    if not st.session_state.get("admin_logged_in"):
        st.subheader(t("admin_login_subtitle"))
        password = st.text_input(t("admin_password"), type="password")

        if st.button(t("admin_login_button")):
            if not admin_is_configured():
                st.error(t("admin_not_configured"))
                return

            if verify_admin_password(password):
                st.session_state["admin_logged_in"] = True
                st.success(t("admin_connected"))
                st.switch_page("pages/admin_dashboard.py")
            else:
                st.error(t("admin_bad_password"))

        st.caption(t("admin_password_caption"))
        return

    st.success(t("admin_welcome"))

    col1, col2 = st.columns(2)

    with col1:
        if st.button(t("open_admin_dashboard"), width="stretch"):
            st.switch_page("pages/admin_dashboard.py")

    with col2:
        if st.button(t("logout_admin"), width="stretch"):
            logout_admin()
            st.rerun()

    st.info(t("admin_info"))


def main() -> None:
    init_db()
    ensure_defaults()
    init_session()
    init_language_state()
    init_navigation_state()
    init_otp_rate_limit_state()
    init_create_order_state()
    restore_session_from_query_params()
    apply_pending_menu_redirect()

    menu = render_sidebar()

    if menu == MENU_LOGIN:
        page_connexion()
    elif menu == MENU_DASHBOARD:
        page_dashboard_client()
    elif menu == MENU_TRACKING:
        page_tracking()
    elif menu == MENU_SIMULATE:
        page_simuler()
    elif menu == MENU_CREATE_ORDER:
        page_creer_commande()
    elif menu == MENU_MY_ORDERS:
        page_mes_commandes()
    elif menu == MENU_ADMIN:
        page_admin()


if __name__ == "__main__":
    main()
