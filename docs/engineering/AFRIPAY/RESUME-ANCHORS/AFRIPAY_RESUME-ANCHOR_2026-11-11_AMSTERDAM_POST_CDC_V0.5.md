# AFRIDIGID ENGINEERING — AFRIPAY AFRIKA
## RESUME-ANCHOR — POST CDC V0.5 : FACILITATION INTERNATIONALE ET FUTUR PSP

**Date :** 11 novembre 2026 — Europe/Amsterdam  
**Statut :** POINT DE REPRISE DOCUMENTAIRE / NON CERTIFIÉ COMME LOGICIEL  
**CDC associé :** `docs/engineering/AFRIPAY/CAHIERS-DES-CHARGES/AFRIPAY_CDC_V0.5_FACILITATION_ET_PSP_ARCHITECTURE_EVOLUTIVE_DRAFT_2026-11-11.md`  
**Périmètre :** AfriPay Afrika, distinct d'ORYSK.  
**Gouvernance :** Trio Doré — arbitrage humain final ; Codex et ChatGPT interviennent dans leurs rôles d'expertise autorisés.

## 1. À LIRE EN PREMIER — Situation de l'entreprise et du produit

AfriDIGID est l'entreprise porteuse ; son responsable indique qu'elle possède son immatriculation néerlandaise KVK et son numéro BTW, qui ne constituent **pas** un agrément PSP. AfriDIGID développe des produits numériques distincts, dont ORYSK et AfriPay Afrika. ORYSK n'est pas impliqué dans ce dossier AfriPay.

AfriPay Afrika est **un produit unique à deux volets fonctionnels** :
- **Volet 1 — Facilitation des achats et services internationaux :** modèle initial, commandes et devis ; règlements locaux via comptes marchands autorisés d'AfriDIGID ou de partenaires, avec flux réels/qualification réglementaire à prouver.
- **Volet 2 — PSP futur :** activités de paiement à ajouter après sélection précise des services, conformité et obtention des autorisations/agréments applicables. L'intention de direction est qu'AfriDIGID soit l'entité titulaire et exploite ces services via AfriPay, dans la mesure où la juridiction et la forme juridique le permettent.

Il ne s'agit **ni** de deux sociétés présumées **ni** de reproduire Klarna ou Wise. Ces marques ont servi d'exemples pédagogiques.

## 2. Vision d'inclusion financière exprimée

À terme, permettre aux personnes **sans compte bancaire personnel** d'obtenir un instrument prépayé rechargeable et de payer auprès de commerçants compatibles **localement et potentiellement à l'international**. Exemple : un client charge **2 000 FCFA** sur un instrument AfriPay et effectue des achats en magasin et sur Internet. Ceci est un cas d'usage **exploratoire**, pas une offre commercialisée, ni un seuil, un tarif ou une autorisation.

Instruments envisagés : QR de paiement sécurisé, carte virtuelle, carte physique à puce/NFC, badge ou support électronique rechargeable. Il faudra séparer l'instrument, l'autorité de paiement, la source/tenue des fonds, l'acceptation réseau, l'authentification et les exigences de conformité. Une carte ou puce seule n'est pas universellement acceptée et ne permet pas automatiquement de payer sur Internet.

Le modèle prépayé ne suppose aucun crédit ; crédit/BNPL reste non choisi. D'autres services PSP (comptes de paiement, virements, transfert de fonds, acquisition, versement/retrait, change, émission d'instruments, initiation et agrégation de comptes, conformité, remboursements) restent **exploratoires** en attendant arbitrage.

## 3. Architecture évolutive recherchée

L'orientation V0.4 est un monolithe Python modulaire FastAPI/Starlette/HTML avec PostgreSQL comme autorité transactionnelle, sous réserve de qualification. Les deux volets AfriPay doivent être autonomes, intégrables par **contrats versionnés et contrôle d'autorité**, avec écritures et données financières correctement séparées. Les commandes du facilitateur ne donnent pas automatiquement accès aux soldes ou au grand livre PSP.

L'extension PSP devra viser l'**absence de reconstruction générale** du volet Facilitation tout en admettant, si nécessaire, des migrations de schéma, une infrastructure isolée, des partenariats ou une structure réglementaire différente.

## 4. Fondations du CDC V0.4 intégralement conservées

Le CDC V0.5 reprend son prédécesseur V0.4 et ses 55 exigences historiques (IDENT, OTP, SESS, ADMIN, MET, UI, INF, AC), les décisions d'identité, la migration progressive depuis Streamlit, les règles commerciales FREE/PREMIUM/PREMIUM_PLUS, la publicité/AC-ADS, les objections Codex E1–E12, les scénarios T01–T15 et les portes G0–G5.

Les exigences PSP supplémentaires sont un **DRAFT**, distinct du périmètre initial et de son statut de validation. Les documents V0.1–V0.4 et les anchors historiques restent inchangés.

## 5. Derniers arbitrages ouverts

1. Régime juridique actuel des comptes marchands et circuit réel des fonds Facilitation (mandat, achat/revente, change, remboursements, conformité par pays).
2. Pays, autorité, entité admissible et agréments requis pour l'éventuel PSP d'AfriDIGID ; la qualité KVK/BTW ne confère aucune habilitation.
3. Services PSP sélectionnés et modèle de revenus, partenaires, plafonds, capital, frais et réseaux réellement compatibles.
4. Puce/registre de valeur centralisé vs embarqué, utilisation online/offline, QR, cartes virtuelles et acceptation à distance.
5. Garanties comptables, KYC/KYB, LCB-FT, safeguarding des fonds, supervision, réconciliation, différenciation des domaines métier.
6. Comment le volet Facilitation pourrait utiliser le volet PSP **une fois autorisé**, sans confusion des permissions ou fonds.

## 6. Gouvernance et état réel

**Documentation :** V0.5 nouveau DRAFT publié dans le dépôt GitHub AfriPay ; demande de synchronisation documentaire à distinguer du poste Windows, qui n'est pas vérifié comme synchronisé.  
**Code :** aucune nouvelle implémentation PSP, aucun test PSP, aucun agrément constaté.  
**Autorisation :** les présents travaux documentaires ne permettent pas de modifier le code, les bases réelles, Render, DNS, secrets, ORYSK, ni de mettre en exploitation un moyen de paiement. Les autres opérations Git restent soumises au contrôle humain.

## 7. Point de reprise

Au retour, relire cet anchor puis la section d'extension PSP du CDC V0.5. Reprendre par une revue **G0 documentaire** du modèle initial et du périmètre futur PSP ; **ne pas lancer directement une implémentation Codex ou une opération réglementée**. Le responsable humain décide des étapes suivantes.

**FIN — RESUME-ANCHOR POST V0.5 — NON CERTIFIÉ.**
