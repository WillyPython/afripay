# AfriPay

AfriPay is a secure international payment facilitation MVP enabling users in Cameroon to pay for global e-commerce products without a bank card.

This project is currently in test phase (Cameroon pilot).

---

## 🚀 Problem

Many users in Cameroon want to purchase products from international e-commerce platforms (Amazon, Temu, Shein, AliExpress) but do not have access to:

- International bank cards
- PayPal
- Reliable cross-border payment solutions

---

## 💡 Solution

AfriPay acts as a **payment facilitator**:

1. The user selects a product on an international e-commerce website.
2. The user submits product details and confirms delivery responsibility.
3. The user pays locally via Mobile Money.
4. AfriPay validates payment before initiating purchase.
5. Tracking and proof of purchase are provided.

⚠️ AfriPay does not handle logistics or customs responsibility.
The client assumes delivery risks and import-related costs.

---

## 🔐 Transparency & Validation

- Commission: 10% (minimum €10)
- Payment validation required before purchase
- Client must confirm product references (size/color/variant)
- Legal disclaimer clearly displayed

---

## 🛠 Tech Stack

- Python
- Streamlit
- SQLite

---

## 📦 How to Run Locally

```bash
pip install -r requirements.txt
streamlit run afripay_app.py

---

# 🇫🇷 Version Française

## 🚀 Problème

De nombreuses personnes au Cameroun souhaitent acheter des produits sur des plateformes internationales (Amazon, Temu, Shein, AliExpress) mais ne disposent pas :

- De carte bancaire internationale
- De PayPal
- D’un moyen fiable de paiement transfrontalier

---

## 💡 Solution

AfriPay agit comme **facilitateur de paiement international** :

1. Le client choisit un produit sur un site e-commerce.
2. Il soumet les références exactes (taille, couleur, variante).
3. Il confirme qu’il assume la livraison et les frais éventuels.
4. Il paie via Mobile Money.
5. AfriPay valide le paiement avant d’effectuer l’achat.

⚠️ AfriPay ne gère pas la logistique ni les frais de douane.  
La réception et les coûts d’importation restent sous la responsabilité du client.

---

## 🔐 Transparence

- Commission : 10% (minimum 10€)
- Validation obligatoire du paiement
- Confirmation explicite des références produit
- Disclaimer légal affiché dans l’application

---

## 📍 Vision

Construire un pont de paiement africain permettant l’accès au e-commerce international sans infrastructure bancaire internationale.