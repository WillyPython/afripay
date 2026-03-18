import secrets
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import streamlit as st

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

# Numéro WhatsApp Business AfriPay (format international sans + ni espaces)
AFRIPAY_WHATSAPP_NUMBER = "316XXXXXXXX"

# OTP anti-spam
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_REQUESTS = 3
OTP_WINDOW_MINUTES = 5

LANG_FR = "FR"
LANG_EN = "EN"

ORDER_TYPE_PHYSICAL = "Produit physique"
ORDER_TYPE_SERVICE = "Service / paiement digital"

ORDER_TYPE_PHYSICAL_EN = "Physical product"
ORDER_TYPE_SERVICE_EN = "Digital service / payment"

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
### 🌍 Que pouvez-vous payer avec AfriPay ?

AfriPay permet de payer vos **achats et services internationaux** avec Mobile Money depuis l’Afrique.

**Exemples :**

• 🛒 Produits : Amazon, Temu, AliExpress  
• 🎓 Études : certifications de diplômes, universités, examens  
• 💻 Digital : logiciels, hébergement, abonnements  
• 📦 Commerce : achats pour revente locale
""",
        "page_login_intro_2": """
### 🔒 Pourquoi faire confiance à AfriPay ?

✅ Connexion sécurisée par OTP  
✅ Vérification humaine anti-bot  
✅ Suivi des commandes directement dans AfriPay  
✅ Paiements internationaux facilités
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
        "pricing_info": "Tarification AfriPay v1 : {percent} % du montant marchand, sans frais fixe",
        "create_order_title": "Créer commande",
        "need_login_create_order": "Tu dois être connecté.",
        "create_order_step_info": "📌 Étape principale après connexion : crée d’abord ta commande. Tu pourras ensuite vérifier le résultat dans « Mes commandes » puis dans le Dashboard Client.",
        "create_order_info": "📌 AfriPay facilite le paiement international. Pour un produit physique, le transitaire reste sous la responsabilité du client. Pour un service ou paiement digital, aucun transitaire n’est requis.",
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
        "legal_warning": "Message juridique : AfriPay agit comme facilitateur de paiement international. AfriPay n'assure pas le dédouanement ni la livraison finale des produits physiques. Le client demeure responsable de son transitaire, de l'adresse de réception finale et des formalités éventuelles liées à l'importation.",
        "practical_tip": "Conseil pratique : saisissez le montant total final affiché par le marchand. Ce montant peut être en XAF ou en EUR selon le site ou le vendeur.",
        "payment_parameters": "### 💳 Paramètres de paiement",
        "order_type": "Type de commande *",
        "order_type_help": "Choisissez « Produit physique » pour un achat à livrer, ou « Service / paiement digital » pour une certification, un abonnement, un logiciel, etc.",
        "merchant_total_displayed": "Montant total affiché par le marchand *",
        "merchant_currency": "Devise du marchand *",
        "merchant_currency_help": "Choisissez la devise réellement affichée par le site marchand ou le service.",
        "main_information": "### 🔗 Informations principales",
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
        "send_payment_proof_whatsapp": "📲 Envoyer preuve de paiement WhatsApp",
        "see_payment_proof_message": "Voir le message de preuve de paiement",
        "payment_proof_help": "Après paiement Mobile Money, cliquez sur ce bouton pour ouvrir WhatsApp avec un message déjà préparé. Ajoutez ensuite votre capture d’écran avant l’envoi.",
        "payment_proof_message_intro": "Bonjour AfriPay,",
        "payment_proof_message_confirm": "Je confirme le paiement de ma commande.",
        "payment_proof_message_reference": "Référence : {order_code}",
        "payment_proof_message_amount": "Montant payé : {amount_xaf} XAF",
        "payment_proof_message_operator": "Opérateur : {provider}",
        "payment_proof_message_screenshot": "Vous trouverez ci-joint la capture d’écran du paiement.",
        "payment_proof_message_thanks": "Merci.",
        "my_orders_title": "Mes commandes",
        "need_login_my_orders": "Tu dois être connecté.",
        "no_orders_short": "Aucune commande.",
        "created_on": "Créée le",
        "merchant_org_label": "Marchand / Organisme",
        "amount_xaf_label": "Montant XAF",
        "amount_eur_label": "Montant EUR",
        "seller_fee_label": "Frais vendeur",
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
        "whatsapp_order_created": "Votre commande AfriPay a bien été créée ✅",
        "whatsapp_financial_summary": "Résumé financier estimatif :",
        "whatsapp_origin_currency": "Devise d'origine du marchand : {currency}",
        "whatsapp_product_link_title": "Lien du produit / service :",
        "whatsapp_track_order": "Vous pouvez suivre votre commande directement dans AfriPay.",
        "whatsapp_marketing_1": "🚀 AfriPay permet de payer vos achats et services internationaux depuis l’Afrique avec Mobile Money.",
        "whatsapp_marketing_2": "Exemples : Amazon, Temu, certifications, universités, logiciels, abonnements, services en ligne.",
        "whatsapp_marketing_3": "💡 Essayez AfriPay pour vos prochains paiements internationaux :",
        "whatsapp_brand": "AfriPay Afrika",
        "whatsapp_tagline": "Facilitateur des paiements internationaux",
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
### 🌍 What can you pay with AfriPay?

AfriPay helps you pay for **international purchases and services** with Mobile Money from Africa.

**Examples:**

• 🛒 Products: Amazon, Temu, AliExpress  
• 🎓 Studies: diploma certifications, universities, exams  
• 💻 Digital: software, hosting, subscriptions  
• 📦 Business: purchases for local resale
""",
        "page_login_intro_2": """
### 🔒 Why trust AfriPay?

✅ Secure OTP login  
✅ Anti-bot human verification  
✅ Order tracking directly in AfriPay  
✅ International payments made easier
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
        "summary_client_info": "AfriPay facilitates your international payments. Customs clearance and final delivery remain your responsibility through your forwarder / agent for physical products.",
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
        "pricing_info": "AfriPay v1 pricing: {percent}% of the merchant amount, no fixed fee",
        "create_order_title": "Create order",
        "need_login_create_order": "You must be logged in.",
        "create_order_step_info": "📌 Main step after login: first create your order. You can then check the result in “My orders” and in the Client Dashboard.",
        "create_order_info": "📌 AfriPay facilitates international payment. For a physical product, the forwarder remains the client’s responsibility. For a digital service or payment, no forwarder is required.",
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
        "legal_warning": "Legal notice: AfriPay acts as an international payment facilitator. AfriPay does not handle customs clearance or final delivery of physical products. The client remains responsible for their forwarder, final delivery address, and any import-related formalities.",
        "practical_tip": "Practical advice: enter the final total amount displayed by the merchant. This amount may be in XAF or EUR depending on the site or seller.",
        "payment_parameters": "### 💳 Payment settings",
        "order_type": "Order type *",
        "order_type_help": "Choose “Physical product” for a delivered purchase, or “Digital service / payment” for a certification, subscription, software, etc.",
        "merchant_total_displayed": "Total amount displayed by the merchant *",
        "merchant_currency": "Merchant currency *",
        "merchant_currency_help": "Choose the currency actually displayed by the merchant site or service.",
        "main_information": "### 🔗 Main information",
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
        "ack_required": "You must validate the legal and operational information before creating the order.",
        "order_created": "Order created ✅ Number: **{order_code}**",
        "order_saved_info": "Your order has been recorded successfully. You can now check the result in “My orders” and in the Client Dashboard.",
        "estimated_summary": "Estimated summary retained: Merchant amount {merchant_xaf} XAF ({merchant_eur} EUR) | AfriPay fee {fee_xaf} XAF ({fee_eur} EUR) | Total {total_xaf} XAF ({total_eur} EUR)",
        "share_order_title": "### 📲 Share your order",
        "share_whatsapp": "Share AfriPay on WhatsApp",
        "see_whatsapp_message": "View WhatsApp message",
        "payment_proof_title": "### 💳 Send your payment proof",
        "send_payment_proof_whatsapp": "📲 Send payment proof via WhatsApp",
        "see_payment_proof_message": "View payment proof message",
        "payment_proof_help": "After Mobile Money payment, click this button to open WhatsApp with a prefilled message. Then add your payment screenshot before sending.",
        "payment_proof_message_intro": "Hello AfriPay,",
        "payment_proof_message_confirm": "I confirm the payment of my order.",
        "payment_proof_message_reference": "Reference: {order_code}",
        "payment_proof_message_amount": "Amount paid: {amount_xaf} XAF",
        "payment_proof_message_operator": "Operator: {provider}",
        "payment_proof_message_screenshot": "Please find attached the payment screenshot.",
        "payment_proof_message_thanks": "Thank you.",
        "my_orders_title": "My orders",
        "need_login_my_orders": "You must be logged in.",
        "no_orders_short": "No orders.",
        "created_on": "Created on",
        "merchant_org_label": "Merchant / Organization",
        "amount_xaf_label": "Amount XAF",
        "amount_eur_label": "Amount EUR",
        "seller_fee_label": "Seller fee",
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
        "whatsapp_order_created": "Your AfriPay order has been created successfully ✅",
        "whatsapp_financial_summary": "Estimated financial summary:",
        "whatsapp_origin_currency": "Original merchant currency: {currency}",
        "whatsapp_product_link_title": "Product / service link:",
        "whatsapp_track_order": "You can track your order directly in AfriPay.",
        "whatsapp_marketing_1": "🚀 AfriPay helps you pay for your international purchases and services from Africa with Mobile Money.",
        "whatsapp_marketing_2": "Examples: Amazon, Temu, certifications, universities, software, subscriptions, online services.",
        "whatsapp_marketing_3": "💡 Try AfriPay for your next international payments:",
        "whatsapp_brand": "AfriPay Afrika",
        "whatsapp_tagline": "International payment facilitator",
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


def init_language_state() -> None:
    if "language" not in st.session_state:
        st.session_state["language"] = "fr"


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("language", "fr")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def get_menu_options():
    return [
        t("menu_connexion"),
        t("menu_dashboard"),
        t("menu_tracking"),
        t("menu_simulate"),
        t("menu_create_order"),
        t("menu_my_orders"),
        t("menu_admin"),
    ]


def get_menu_key(key_name: str) -> str:
    mapping = {
        "login": t("menu_connexion"),
        "dashboard": t("menu_dashboard"),
        "tracking": t("menu_tracking"),
        "simulate": t("menu_simulate"),
        "create_order": t("menu_create_order"),
        "my_orders": t("menu_my_orders"),
        "admin": t("menu_admin"),
    }
    return mapping[key_name]


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
    try:
        value = row[key]
        return value if value not in (None, "") else default
    except Exception:
        return default


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

    merchant_step = merchant_status_to_step(merchant_status)

    steps = [
        {
            "title": t("step_created"),
            "done": order_status in {"CREEE", "PAYEE", "EN_COURS", "LIVREE"},
            "detail": t("step_reference", ref=safe_get(order, "order_code", "—")),
        },
        {
            "title": t("step_payment_confirmed"),
            "done": payment_status in {"PAYE", "PAYÉ", "PAYEE", "PAYÉE", "CONFIRMED"},
            "detail": t("step_payment_status", status=safe_get(order, "payment_status", "—")),
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

    for index, step in enumerate(steps, start=1):
        step_position = index - 1

        if step_position < current_index:
            icon = "🟢"
        elif step_position == current_index:
            icon = "🟡"
        else:
            icon = "⚪"

        st.markdown(f"**{icon} Étape {index} — {step['title']}**")
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
    fee_xaf = eur_to_xaf(fee_eur)
    return fee_xaf, fee_eur


def compute_payment_preview(merchant_total_amount, merchant_currency):
    merchant_xaf, merchant_eur = compute_dual_amounts(
        merchant_total_amount,
        merchant_currency,
    )

    afripay_fee_xaf, afripay_fee_eur = calculate_afripay_fee(merchant_eur)

    total_to_pay_xaf = merchant_xaf + afripay_fee_xaf
    total_to_pay_eur = merchant_eur + afripay_fee_eur

    return {
        "merchant_xaf": merchant_xaf,
        "merchant_eur": merchant_eur,
        "afripay_fee_xaf": afripay_fee_xaf,
        "afripay_fee_eur": afripay_fee_eur,
        "total_to_pay_xaf": total_to_pay_xaf,
        "total_to_pay_eur": total_to_pay_eur,
    }


def build_whatsapp_order_message(
    order_code,
    product_title,
    merchant_total_amount,
    merchant_currency,
    product_url,
):
    clean_product_title = str(product_title or "").strip() or t("product_or_service_unspecified")
    clean_product_url = str(product_url or "").strip()
    currency = str(merchant_currency or "").strip().upper() or "EUR"

    preview = compute_payment_preview(merchant_total_amount, currency)

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
        t("payment_proof_message_thanks"),
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


def init_navigation_state() -> None:
    if "main_menu" not in st.session_state:
        st.session_state["main_menu"] = get_menu_key("login")


def schedule_menu_redirect(menu_name: str) -> None:
    if menu_name in get_menu_options():
        st.session_state["pending_main_menu"] = menu_name


def apply_pending_menu_redirect() -> None:
    pending_menu = st.session_state.pop("pending_main_menu", None)
    if pending_menu in get_menu_options():
        st.session_state["main_menu"] = pending_menu


def refresh_menu_labels_after_language_change() -> None:
    current = st.session_state.get("main_menu")
    mapping_fr_to_key = {
        TRANSLATIONS["fr"]["menu_connexion"]: "login",
        TRANSLATIONS["fr"]["menu_dashboard"]: "dashboard",
        TRANSLATIONS["fr"]["menu_tracking"]: "tracking",
        TRANSLATIONS["fr"]["menu_simulate"]: "simulate",
        TRANSLATIONS["fr"]["menu_create_order"]: "create_order",
        TRANSLATIONS["fr"]["menu_my_orders"]: "my_orders",
        TRANSLATIONS["fr"]["menu_admin"]: "admin",
    }
    mapping_en_to_key = {
        TRANSLATIONS["en"]["menu_connexion"]: "login",
        TRANSLATIONS["en"]["menu_dashboard"]: "dashboard",
        TRANSLATIONS["en"]["menu_tracking"]: "tracking",
        TRANSLATIONS["en"]["menu_simulate"]: "simulate",
        TRANSLATIONS["en"]["menu_create_order"]: "create_order",
        TRANSLATIONS["en"]["menu_my_orders"]: "my_orders",
        TRANSLATIONS["en"]["menu_admin"]: "admin",
    }

    key_name = mapping_fr_to_key.get(current) or mapping_en_to_key.get(current) or "login"
    st.session_state["main_menu"] = get_menu_key(key_name)


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
        refresh_menu_labels_after_language_change()
        st.rerun()

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
            schedule_menu_redirect(get_menu_key("login"))
            st.rerun()
    else:
        st.sidebar.info(t("not_connected"))

    st.sidebar.markdown("---")

    st.sidebar.radio(
        t("menu"),
        get_menu_options(),
        key="main_menu",
    )

    return st.session_state["main_menu"]


def page_connexion() -> None:
    st.title(t("page_login_title"))
    consume_flash_message()

    st.markdown(t("page_login_intro_1"))
    st.markdown(t("page_login_intro_2"))
    st.info(t("login_info"))

    default_phone = str(st.session_state.get("otp_phone", "") or "")
    phone = st.text_input(t("phone"), value=default_phone, placeholder="+2376...")

    render_test_otp_panel(current_phone=phone)
    st.caption(t("otp_limit_info"))

    captcha_input = render_captcha_block("login", title=t("captcha_title"), allow_refresh=True)

    if st.button(t("send_otp"), use_container_width=True):
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

        record_otp_request(clean_phone)

        st.success(t("otp_success"))
        st.rerun()

    otp_input = st.text_input(
        t("enter_otp"),
        key="login_otp_input",
        placeholder=t("otp_placeholder"),
    )
    name = st.text_input(t("name"), placeholder=t("optional"))
    email = st.text_input(t("email"), placeholder=t("optional"))

    if st.button(t("login_button"), use_container_width=True):
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

        st.session_state["flash_message"] = t("login_success")
        schedule_menu_redirect(get_menu_key("create_order"))
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
            st.bar_chart(status_data, x="Statut", y="Commandes", use_container_width=True)
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
            st.line_chart(evolution_data, x="Mois", y="Commandes", use_container_width=True)
        else:
            st.info(t("monthly_evolution_empty"))

    st.markdown(t("monthly_volume"))
    if monthly_volume:
        sorted_keys = sorted(monthly_volume.keys())
        volume_data = {
            "Mois": [month_label(datetime.strptime(k, "%Y-%m")) for k in sorted_keys],
            "Montant_XAF": [monthly_volume[k] for k in sorted_keys],
        }
        st.area_chart(volume_data, x="Mois", y="Montant_XAF", use_container_width=True)
    else:
        st.info(t("monthly_volume_empty"))

    st.markdown("---")

    latest = rows[0]

    st.subheader(t("latest_order"))
    info1, info2 = st.columns(2)

    with info1:
        st.write(f"**{t('reference')} :** {safe_get(latest, 'order_code', '—')}")
        st.write(f"**{t('product_service')} :** {get_product_label(latest)}")
        st.write(f"**{t('merchant')} :** {safe_get(latest, 'site_name', '—')}")
        st.write(f"**{t('total_xaf')} :** {format_xaf(safe_get(latest, 'total_xaf', 0))} XAF")
        st.write(f"**{t('total_eur')} :** {format_eur(safe_get(latest, 'total_to_pay_eur', 0))} €")

    with info2:
        st.write(f"**{t('order_status')} :** {normalize_status(safe_get(latest, 'order_status', '—'))}")
        st.write(f"**{t('payment_status')} :** {safe_get(latest, 'payment_status', '—')}")
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

        st.success(f"{t('order_number')} : **{safe_get(row, 'order_code', '')}**")
        st.write(f"**{t('product_service')} :**", get_product_label(row))
        st.write(f"**{t('merchant')} :**", safe_get(row, "site_name", "—"))
        st.write(f"**{t('total_xaf')} :**", f"{format_xaf(safe_get(row, 'total_xaf', 0))} XAF")
        st.write(f"**{t('total_eur')} :**", f"{format_eur(safe_get(row, 'total_to_pay_eur', 0))} €")
        st.write(f"**{t('order_status')} :**", normalize_status(safe_get(row, "order_status", "—")))
        st.write(f"**{t('payment_status')} :**", safe_get(row, "payment_status", "—"))
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


def get_order_type_options():
    if st.session_state.get("language", "fr") == "en":
        return [ORDER_TYPE_PHYSICAL_EN, ORDER_TYPE_SERVICE_EN]
    return [ORDER_TYPE_PHYSICAL, ORDER_TYPE_SERVICE]


def is_physical_order(order_type_value: str) -> bool:
    return order_type_value in {ORDER_TYPE_PHYSICAL, ORDER_TYPE_PHYSICAL_EN}


def page_creer_commande() -> None:
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
        help=t("order_type_help"),
    )

    merchant_total_amount = st.number_input(
        t("merchant_total_displayed"),
        min_value=0.0,
        value=0.0,
        step=1.0,
        key="create_order_amount",
    )

    merchant_currency = st.selectbox(
        t("merchant_currency"),
        ["XAF", "EUR"],
        index=0,
        key="create_order_currency",
        help=t("merchant_currency_help"),
    )

    payment_preview = compute_payment_preview(
        merchant_total_amount,
        merchant_currency,
    )

    render_payment_summary(payment_preview)

    with st.form("create_order_form"):
        st.markdown(t("main_information"))

        product_url = st.text_input(
            t("product_service_link"),
            placeholder=t("product_link_placeholder"),
        )

        st.caption(t("product_link_tip"))

        product_title = st.text_input(
            t("product_service_name"),
            placeholder=t("product_service_name_placeholder"),
        )

        site_name = st.text_input(
            t("merchant_org"),
            placeholder=t("merchant_org_placeholder"),
        )

        product_specs = st.text_area(
            t("details_useful"),
            placeholder=t("details_useful_placeholder"),
        )

        st.markdown(t("delivery_payment"))

        requires_forwarder = is_physical_order(order_type)

        if requires_forwarder:
            delivery_address = st.text_area(
                t("forwarder_address_label"),
                placeholder=t("forwarder_address_placeholder"),
                help=t("forwarder_address_help"),
            )
        else:
            delivery_address = ""
            st.success(t("no_forwarder_required"))

        momo_provider = st.selectbox(
            t("momo_provider"),
            ["", "MTN", "Orange"],
            index=0,
        )

        if momo_provider.strip():
            st.caption(t("momo_selected", provider=momo_provider.strip()))
        else:
            st.caption(t("momo_choose"))

        st.caption(t("captcha_validated_above"))

        client_ack = st.checkbox(t("client_ack"))

        submitted = st.form_submit_button(t("create_order_button"), use_container_width=True)

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

        if str(merchant_currency).strip().upper() == "EUR":
            product_price_eur = to_float(merchant_total_amount, 0.0)
            shipping_estimate_eur = 0.0
        else:
            product_price_eur = final_preview["merchant_eur"]
            shipping_estimate_eur = 0.0

        order_code = create_order_for_user(
            user_id=int(st.session_state["user_id"]),
            site_name=site_name.strip(),
            product_url=product_url.strip(),
            product_title=product_title.strip(),
            product_specs=product_specs.strip(),
            product_price_eur=float(product_price_eur),
            shipping_estimate_eur=float(shipping_estimate_eur),
            delivery_address=delivery_address.strip() if requires_forwarder else "",
            momo_provider=momo_provider.strip() or None,
        )

        st.success(t("order_created", order_code=order_code))
        st.info(t("order_saved_info"))

        st.success(
            t(
                "estimated_summary",
                merchant_xaf=format_xaf(final_preview["merchant_xaf"]),
                merchant_eur=format_eur(final_preview["merchant_eur"]),
                fee_xaf=format_xaf(final_preview["afripay_fee_xaf"]),
                fee_eur=format_eur(final_preview["afripay_fee_eur"]),
                total_xaf=format_xaf(final_preview["total_to_pay_xaf"]),
                total_eur=format_eur(final_preview["total_to_pay_eur"]),
            )
        )

        whatsapp_message = build_whatsapp_order_message(
            order_code=order_code,
            product_title=product_title.strip(),
            merchant_total_amount=merchant_total_amount,
            merchant_currency=merchant_currency,
            product_url=product_url.strip(),
        )
        whatsapp_url = build_whatsapp_share_url(whatsapp_message)

        st.markdown(t("share_order_title"))
        st.link_button(
            t("share_whatsapp"),
            whatsapp_url,
            use_container_width=True,
        )

        with st.expander(t("see_whatsapp_message")):
            st.code(whatsapp_message)

        payment_proof_message = build_payment_proof_whatsapp_message(
            order_code=order_code,
            amount_xaf=final_preview["total_to_pay_xaf"],
            momo_provider=momo_provider.strip() or "MTN MoMo / Orange Money",
        )
        payment_proof_url = build_whatsapp_direct_url(
            AFRIPAY_WHATSAPP_NUMBER,
            payment_proof_message,
        )

        st.markdown(t("payment_proof_title"))
        st.info(t("payment_proof_help"))
        st.link_button(
            t("send_payment_proof_whatsapp"),
            payment_proof_url,
            use_container_width=True,
        )

        with st.expander(t("see_payment_proof_message")):
            st.code(payment_proof_message)

        clear_captcha_error("order")
        refresh_captcha("order")


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
        total_eur = safe_get(row, "total_to_pay_eur", 0)
        status = safe_get(row, "order_status", "—")

        expander_title = f"{code} — {normalize_status(status)} — {format_xaf(total)} XAF"

        with st.expander(expander_title):
            st.write(f"**{t('created_on')} :** {safe_get(row, 'created_at', '—')}")
            st.write(f"**{t('product_service')} :** {get_product_label(row)}")
            st.write(f"**{t('merchant_org_label')} :** {safe_get(row, 'site_name', '—')}")
            st.write(f"**{t('amount_xaf_label')} :** {format_xaf(total)} XAF")
            st.write(f"**{t('amount_eur_label')} :** {format_eur(total_eur)} €")
            st.write(f"**{t('seller_fee_label')} :** {format_xaf(safe_get(row, 'seller_fee_xaf', 0))} XAF")
            st.write(f"**{t('afripay_fee')} :** {format_xaf(safe_get(row, 'afripay_fee_xaf', 0))} XAF")
            st.write(f"**{t('forwarder_address_expander')} :** {safe_get(row, 'delivery_address', '—')}")
            st.write(f"**{t('payment_label')} :** {safe_get(row, 'payment_status', '—')}")
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
        if st.button(t("open_admin_dashboard"), use_container_width=True):
            st.switch_page("pages/admin_dashboard.py")

    with col2:
        if st.button(t("logout_admin"), use_container_width=True):
            logout_admin()
            st.rerun()

    st.info(t("admin_info"))


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    init_db()
    ensure_defaults()
    init_session()
    init_language_state()
    init_navigation_state()
    init_otp_rate_limit_state()
    restore_session_from_query_params()
    apply_pending_menu_redirect()

    menu = render_sidebar()

    if menu == get_menu_key("login"):
        page_connexion()
    elif menu == get_menu_key("dashboard"):
        page_dashboard_client()
    elif menu == get_menu_key("tracking"):
        page_tracking()
    elif menu == get_menu_key("simulate"):
        page_simuler()
    elif menu == get_menu_key("create_order"):
        page_creer_commande()
    elif menu == get_menu_key("my_orders"):
        page_mes_commandes()
    elif menu == get_menu_key("admin"):
        page_admin()


if __name__ == "__main__":
    main()