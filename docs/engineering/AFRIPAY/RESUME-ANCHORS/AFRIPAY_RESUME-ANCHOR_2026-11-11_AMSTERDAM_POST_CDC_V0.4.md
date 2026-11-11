# AFRIDIGID ENGINEERING — AFRIPAY AFRIKA
## RESUME-ANCHOR — OBJET, AMBITION, MODELE ECONOMIQUE, ARCHITECTURE ET PUBLICITE

**Date :** 11 novembre 2026 — Europe/Amsterdam  
**Version :** POST CDC V0.4 — nouveau checkpoint indépendant  
**Statut :** **POINT DE REPRISE DOCUMENTAIRE / NON CERTIFIÉ COMME LOGICIEL**  
**Périmètre :** AfriPay Afrika seulement ; **ORYSK indépendant**.  
**Autorité :** décisions métier humaines, historique README/GitHub et documents normatifs, comparés au code constaté ; une synthèse ne remplace ni l'ADL normative, ni une décision approuvée, ni les tests/certifications.

> **À LIRE EN PREMIER À CHAQUE REPRISE AFRIPAY.** Ce document est volontairement autonome : il évite les fouilles répétées dans GitHub et les anciennes conversations. Il indique les sources exactes lorsqu’un contrôle nouveau est réellement utile. Les ambiguïtés ouvertes sont inscrites, jamais remplacées par une hypothèse.

## 1. En une minute : qu'est-ce qu’AfriPay Afrika ?

**AfriPay Afrika est le premier logiciel développé par AfriDIGID.** Il a été conçu pour ouvrir aux clients africains l’accès à des **achats de biens et de services internationaux**, même sans carte bancaire internationale, à travers un service numérique de **facilitation d’achats**, avec paiement local notamment par Mobile Money et exécution vérifiée de l’achat chez le marchand étranger.

**AfriDIGID est l’entreprise** (marque/produit : **AfriPay Afrika**) : elle porte les contrats, les opérations commerciales, les relations avec opérateurs Mobile Money, partenaires et prestataires. Dans sa phase initiale, **AfriPay n’offre pas de portefeuille de fonds clients ni de service PSP autonome**. Cela ne prouve pas que les comptes marchands ne reçoivent pas temporairement les fonds de commandes : ce flux exige sa qualification contractuelle et juridique.

**Fonctionnement client ciblé :** choix du produit ou service sur un site international → connexion AfriPay → informations précises de commande → devis transparent (prix marchand, éventuels frais tiers, commission AfriPay, change, total) → paiement local auprès du prestataire/compte marchand autorisé → vérification réelle du paiement → commande exécutée auprès du fournisseur étranger → preuve, suivi et assistance. **Ne jamais traiter une simple capture client comme preuve suffisante de paiement.** Les dispositions de logistique/transitaire/douane sont explicitées ; le README historique plaçait la responsabilité de livraison et d’importation chez le client.

## 2. Ambition produit de long terme

1. **AfriPay SAFE / Facilitation d’achats internationaux :** identité sûre, commandes et paiements vérifiables, commissions transparentes, support, continuité des comptes.
2. **Vendeurs sociaux / partenariats :** services aux commerçants, visibilité des offres, développement du réseau et des relations entreprises.
3. **AfriMarketplace / AfriPost :** évolution graduelle de l'écosystème AfriDIGID ; la logistique AfriPost n’est pas implicitement assurée par AfriPay V1.
4. **PSP :** activité future **distincte**, à étudier et autoriser séparément ; pas une fonction automatiquement incluse dans le présent développement.
5. **Publicité :** AfriPay est également un **support attractif de diffusion pour les annonceurs**, sans devenir une régie publicitaire ou un outil comptable de publicité.

Le README GitHub décrit historiquement un pilote **Cameroun** ; les études de marchés ont considéré notamment **Sénégal et Kenya** pour la suite. **Aucun ordre de lancement ou pays de production n’est certifié dans cette synthèse.**

## 3. Économie : ce qui a changé depuis le premier README

| Source/date | Donnée | Statut |
|---|---|---|
| README GitHub publié le 03/03/2026 | Commission **10 %** avec minimum **10 €** ; Mobile Money et achat après validation | **Historique, non barème actuel** |
| `services/settings_service.py` consulté le 11/11/2026 | Valeur `service_fee_percent = "20"` | Paramètre de code, pas contrat commercial universel |
| `services/order_service.py` consulté le 11/11/2026 | `FREE`: 0 XAF de frais, limites de commandes ; `PREMIUM`: 20 % ; `PREMIUM_PLUS` actif: 0 XAF, sinon comportement PREMIUM | Comportement GitHub constaté, préserver jusqu’à arbitrage |
| Responsable humain, 11/11/2026 | **20 % de commission de référence** pour tenir compte des frais d’exploitation, personnel, téléphonie et transferts | **Décision humaine validée** ; ne pas effacer les exceptions existantes sans revue |

**Règle capitale :** la **commission** est la rémunération AfriDIGID pour le service, distincte du **prix du fournisseur**, des **frais de tiers** et des **montants encaissés**. Le code calcule historiquement un total incluant prix marchand + frais vendeur + commission AfriPay. L’expression « AfriPay ne garde pas l’argent du client » signifie ici **absence de portefeuille client**, et non une conclusion juridique sur les comptes marchands. Le transfert réel, le mandat d’achat/revente, la partie facturante et les remboursements restent à contracter.

**À ne pas oublier :** les plans `FREE`, `PREMIUM` et `PREMIUM_PLUS`, les quotas, abonnements, commandes, montants historiques et identifiants clients sont des actifs à préserver.

## 4. Publicité — décisions humaines du 11/11/2026

**AfriPay diffuse des publicités, il ne les fabrique pas et ne gère pas une régie commerciale interne.** Les annonceurs (entreprises/marques/partenaires) contactent le service compétent d’AfriDIGID et fournissent leurs propres visuels. **AfriDIGID** conduit la relation, l’approbation, la programmation et la diffusion ; **sa comptabilité** gère contrats, factures et recettes publicitaires dans ses outils. AfriPay **affiche** les campagnes validées.

- **`AFR-UI-ADS-01` :** deux emplacements cibles : **`ADS-SIDEBAR`** (vertical à droite ou en zone adaptée) et **`ADS-FOOTER`** (horizontal dans le bas du contenu). Responsive mobile.
- **`AFR-UI-ADS-02` :** **rotation automatique** de plusieurs annonceurs, indépendamment dans chaque emplacement, sans rechargement de la page et **sans changement de code ni redéploiement** à chaque campagne. Durée/fréquence restent configurables.
- **`AFR-UI-ADS-03` :** annonces **créées par les entreprises**, livrées aux formats autorisés ; seul le service habilité AfriDIGID les valide et les programme. **Pas de studio créatif, pas de facturation ni régie/enchères dans AfriPay.**
- **`AFR-UI-ADS-04` :** page/lien public **« Faire de la publicité sur AfriPay »** pour présenter les emplacements et contacter AfriDIGID.
- **Protection forte :** étiquette « Publicité », validation médias/URL, aucune exécution de scripts publicitaires arbitraires, séparation des parcours OTP/paiement, pause de rotation accessible, aucun accès annonceur aux commandes ou données personnelles. Une marque citée à titre d’exemple (Amazon, Nike, Roomba) n’est pas présumée partenaire.

**Moteur envisagé (non codé/certifié) :** configuration d’emplacements et campagnes en stockage serveur, dates, statut, média, lien, intervalle, contrôle d’habilitation et historique ; le navigateur ne détient aucun pouvoir de publication. Les ratios `300×600` et `970×250` restent **illustratifs et non validés** ; le guide annonceur doit être approuvé.

## 5. Architecture cible, migration et sécurité

**`AFR-ARCH-DIR-01` validé en principe :** remplacer progressivement l’interface publique Streamlit par **FastAPI/Starlette + HTML**, en **monolithe Python modulaire**, avec **PostgreSQL comme autorité transactionnelle**, sécurité des sessions et permissions côté serveur. Streamlit n’est pas effacé avant une parité fonctionnelle et une migration répétée/qualifiée.

Préserver sans exception : identifiants stables `users.id`, relations utilisateurs, commandes, historiques de paiements/preuves, abonnements et droits acquis, règles historiques des montants, preuves financières et parcours légitimes. Aucune réattribution arbitraire d’adresse e-mail ou fusion automatique de comptes. **L’UI ne constitue jamais une preuve de droit.**

Huit décisions historiques : `AFR-IDENT-DEC-01..06`, `AFR-SEC-DEC-07`, `AFR-MET-DEC-08`. V0.3 préserve **55 exigences** (`IDENT-01..08`, `OTP-01..07`, `SESS-01..07`, `ADMIN-01..06`, `MET-01..06`, `UI-01..06`, `INF-01..05`, `AC-01..10`). L’avis Codex AfriPay identifie **E1–E12** et propose **T01–T15**, **sans exécution de test dans cette mission**.

**Portes de preuve futures** : `G0` contrats métier/réglementaires → `G1` transactions/migrations/montants → `G2` identité/OTP/sessions → `G3` opérations métier/finances → `G4` nouvelle UI FastAPI/HTML et publicités → `G5` répétitions de migration, reprise et décision de production. **Aucun PASS n’est présumé.**

## 6. Ce qui a réellement été fait et vérifié

- Le 11/11/2026, PowerShell local **READ-ONLY** a listé **trois documents dans `afripay/docs`** ; leurs empreintes SHA-256 ont été vérifiées avec succès ; les contenus ont été affichés et relus : Référentiel V0.1, CDC V0.1, premier RESUME-ANCHOR. Aucun ADL commercial dédié n’y figurait alors.
- Le CDC V0.2 a été vérifié et lu par Codex ; le CDC V0.3 a été téléchargé dans `Downloads` et **contrôlé SHA-256 PASS par le responsable humain**, taille **43 910 octets**.
- La connexion GitHub a permis la **lecture seule** du README et de `services/order_service.py`, `services/settings_service.py` sur `main` ; cela explique la chronologie 10 % → 20 % et les exceptions liées aux plans. **La branche distante ne reflète pas nécessairement les modifications locales Windows.**
- Les décisions de publicité et de positionnement métier ont été **validées par le responsable humain dans la conversation**. Leur présence dans un fichier écrit et sa vérification SHA-256 ne valent pas **certification technique**.
- **Aucun code AfriPay modifié**, aucune base réelle touchée, aucun Git add/commit/push, aucune opération Render dans cette mission. Codex-ORYSK travaille dans un chantier **séparé**.

## 7. Sources de référence sans retour aux fouilles

| Document ou source | Emplacement / référence | Utilité |
|---|---|---|
| **CDC V0.4 nouveau** | `docs/engineering/AFRIPAY/CAHIERS-DES-CHARGES/AFRIPAY_CDC_SECURITE_IDENTITE_UI_PUBLICITE_V0.4_CONSOLIDATION_DRAFT_2026-11-11.md` | Contrat de revue courant et publicité ; SHA-256 `30BAC0B962D76C64B93C48F7FF732481E7E02A97B7FC6B2C051E8E68B59C7054` |
| **Le présent RESUME-ANCHOR** | `docs/engineering/AFRIPAY/RESUME-ANCHORS/AFRIPAY_RESUME-ANCHOR_2026-11-11_AMSTERDAM_POST_CDC_V0.4.md` | Reprise autonome prioritaire |
| Référentiel AfriPay | `docs/engineering/AFRIPAY/REFERENTIEL.md` | Organisation et hiérarchie documentaire ; SHA-256 `3E4F2B0E52D69D3ADDDC133E5D326A1ADD7FF6DDB5C8170CB80138D93112561E` |
| CDC V0.1 | `docs/engineering/AFRIPAY/CAHIERS-DES-CHARGES/AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.1_DRAFT_2026-11-11.md` | 55 exigences historiques ; SHA-256 `1C8D28CA85B40E4E58EAE2D26C4253E6FBFBF56917FB55BF7033C9130B0BAD85` |
| Premier RESUME-ANCHOR | `docs/engineering/AFRIPAY/RESUME-ANCHORS/AFRIPAY_RESUME-ANCHOR_2026-11-11_AMSTERDAM.md` | Historique de reprise du matin ; SHA-256 `1B8D642D73D235E0589DB1CA3EC0997DB7F5EE00A116BAAAF2097633F1FC5AB5` |
| CDC V0.2 hors dépôt | `AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.2_CONSOLIDATION_DRAFT_2026-11-11.md` | Consolidation des décisions ; SHA-256 `C947982DF3D195F97DA2FDA2016930396DF6696E569BA81A7F952EA6937BC61C` |
| CDC V0.3 hors dépôt | `AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.3_ARCHITECTURE_MIGRATION_DRAFT_2026-11-11.md` | Architecture et E1–E12/T01–T15 ; SHA-256 `7265ADBEF42E5D6B12B7473936D189A8C85043455A0867D47171F172A090EE4E` |
| README GitHub historique | <https://github.com/WillyPython/afripay/blob/main/README.md> | Modèle initial 10 % min. 10 €, logique Mobile Money, logistique client ; commit README `ccdd6f874579bc9a3a851c6b5531362aae4b882e` |
| Code GitHub frais | <https://github.com/WillyPython/afripay/blob/main/services/order_service.py> et <https://github.com/WillyPython/afripay/blob/main/services/settings_service.py> | 20 % paramétrage et formule par plan ; HEAD consulté `a4a6c47e67474a5473a513e4d509143f6b4b4e40` |
| Rapport Codex AfriPay | Rapport final CODEX-AFRIPAY-01 du 11/11/2026, tenu séparément | 12 objections E1–E12, 15 tests T01–T15 ; non exécutés |

**Gouvernance :** le Référentiel organise, les décisions humaines approuvées arbitrent, le CDC une fois **globalement approuvé** établit les exigences, le code et les tests fournissent les preuves, le RESUME-ANCHOR permet la reprise. **Le présent résumé ne devient pas une norme supérieure aux décisions, aux contrats ou aux preuves.**

## 8. Point exact d'arrêt et suite sans fouilles

**Statut des documents du 11/11/2026 :** CDC V0.4 **DRAFT rédigé**, orientations économiques/publicitaires **validées dans la conversation**, revue globale et certification **non réalisées**. RESUME-ANCHOR **provisoire de référence** jusqu'à enregistrement/vérification par l'utilisateur. **La présence du fichier ne démontre aucun test logiciel.**

**Prochaine tâche AfriPay G0 (sans implémenter) :** rapprocher le rôle réel d'AfriDIGID dans l'achat (mandat ou achat-revente), le circuit du prix fournisseur à partir des comptes Mobile Money, les autorisations de prestations par pays, les conditions de remboursement et **le barème détaillé FREE/PREMIUM/PREMIUM_PLUS**. Puis produire le guide annonceur (formats, poids, validation, pages autorisées, intervalle accessible) et la matrice de permissions de paramétrage des publicités.

**À ne pas refaire :** ne pas relancer d’inventaires généraux du README, rechercher de nouveau le taux de mars, ou relire tout GitHub. Les constatations, sources et chemins sont ci-dessus ; ne rouvrir une source que si un changement mesurable, une contradiction ou une preuve manquante l’exige.

**Autorisations applicables :** **enregistrement local de nouveaux documents uniquement** dans `docs/engineering/AFRIPAY/` ; **aucun ajout/modification du code, aucun Git add/commit/push, aucun Render, aucune connexion ou écriture à PostgreSQL réel, aucun achat/installation, aucune intervention ORYSK** sans permission humaine dédiée. Aucun accès public ou déploiement n'est autorisé.

**Fin du RESUME-ANCHOR POST CDC V0.4.**
