# AFRIDIGID ENGINEERING — AFRIPAY AFRIKA
## CAHIER DES CHARGES CONSOLIDÉ — ACHATS INTERNATIONAUX, SÉCURITÉ, IDENTITÉ, UI/UX ET ESPACES PUBLICITAIRES

**Version :** V0.4 — consolidation métier, architecture, migration et publicité validée en principe  
**Date :** 11 novembre 2026 — Europe/Amsterdam  
**Statut :** **DRAFT DE REVUE — décisions métier et publicitaires humaines intégrées ; CDC V0.4 global non encore approuvé / non certifié**  
**Périmètre :** AfriPay Afrika exclusivement  
**Gouvernance :** Trio Doré — responsable humain (décision finale), ChatGPT (analyse et coordination), Codex (expertise et implémentation autorisées).

> **Principe de conservation.** Cette V0.4 est un nouveau document autonome dérivé de la V0.3 vérifiée (SHA-256 `7265ADBEF42E5D6B12B7473936D189A8C85043455A0867D47171F172A090EE4E`). Elle préserve les 55 exigences, E1–E12, T01–T15 et les contrats G0–G5. Elle ne remplace ni ne modifie matériellement les V0.1/V0.2/V0.3, le Référentiel, les RESUME-ANCHOR historiques, le code ou les ressources Git/Render/PostgreSQL. Les décisions approuvées dans la conversation demeurent des orientations métier ; le document entier et le logiciel ne sont **pas** certifiés.


### SYNTHÈSE EXÉCUTIVE V0.4 — LIRE EN PREMIER

- **Produit :** AfriPay Afrika est le premier logiciel de l’entreprise **AfriDIGID**. Il débute comme **facilitateur d’achats internationaux de biens et de services**, avec paiement local par Mobile Money sur des comptes marchands autorisés d’AfriDIGID ou de partenaires, puis exécution de l’achat international. **Il n’est pas initialement un portefeuille client ni une offre PSP autonome.** La phase PSP reste distincte et conditionnelle.
- **Économie :** le README GitHub publié en mars 2026 annonçait **10 % avec minimum 10 €** ; le responsable humain a confirmé aujourd’hui le passage ultérieur à **20 % de commission de référence** pour supporter les charges. Le code métier GitHub comporte des **exceptions liées aux plans** : elles ne doivent pas être écrasées sans arbitrage explicite. Prix marchand, frais tiers et commission AfriPay restent ventilés séparément.
- **Publicité :** la plateforme doit offrir **deux emplacements** (latéral vertical et horizontal bas de page), avec **rotation autonome, automatique, multi-annonceurs**. Les annonceurs fournissent leurs créations ; **AfriDIGID** valide, programme et gère commercialement la diffusion et la comptabilité ; AfriPay ne devient ni studio de création, ni régie comptable. Un lien public **« Faire de la publicité sur AfriPay »** permet de contacter AfriDIGID.
- **Technique :** migration progressive de Streamlit vers **FastAPI/Starlette et HTML**, monolithe Python modulaire, **PostgreSQL** comme autorité transactionnelle, sans perte d’identifiants, commandes, paiements, abonnements ou preuves. **Pas de Git, Render, base réelle ou mise en production par la présente décision.**
- **Ordre normatif :** la V0.4 complète la base V0.3 ; ses sections **16 à 23** précisent les décisions prises après rédaction de la V0.3. Pour la reprise, consulter **la section 23 et le RESUME-ANCHOR POST-CDCV0.4** ; la section 15 retrace la situation avant les nouvelles validations.

## 1. Objet et objectif de la consolidation

Définir les exigences d'évolution professionnelle d'AfriPay, en donnant la priorité à la sécurité des identités, des sessions et des opérations sensibles tout en préservant les comptes, les commandes, les plans d'abonnement, la cohérence des montants et la continuité de service. Préparer ensuite une modernisation UI/UX fondée sur une véritable autorité serveur, non sur un simple état de présentation.

La V0.4 conserve **l'ensemble des 55 identifiants de la V0.1, V0.2 et V0.3** : IDENT-01 à 08 (8), OTP-01 à 07 (7), SESS-01 à 07 (7), ADMIN-01 à 06 (6), MET-01 à 06 (6), UI-01 à 06 (6), INF-01 à 05 (5), AC-01 à 10 (10). Elle ajoute une traçabilité explicite des décisions validées et précise les conditions de qualification sans inventer de preuves.

## 2. Références et statut des sources

| Référence | Statut / fonction |
|---|---|
| `docs/engineering/AFRIPAY/REFERENTIEL.md` | Référentiel organisationnel V0.1, vérifié le 11/11/2026 ; SHA-256 `3E4F2B0E52D69D3ADDDC133E5D326A1ADD7FF6DDB5C8170CB80138D93112561E` |
| `docs/engineering/AFRIPAY/RESUME-ANCHORS/AFRIPAY_RESUME-ANCHOR_2026-11-11_AMSTERDAM.md` | Premier checkpoint, vérifié ; SHA-256 `1B8D642D73D235E0589DB1CA3EC0997DB7F5EE00A116BAAAF2097633F1FC5AB5` |
| `docs/engineering/AFRIPAY/CAHIERS-DES-CHARGES/AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.1_DRAFT_2026-11-11.md` | Source historique V0.1, 6 904 octets ; SHA-256 communiqué `1C8D28CA85B40E4E58EAE2D26C4253E6FBFBF56917FB55BF7033C9130B0BAD85` |
| Relevés PowerShell READ-ONLY du 11/11/2026 | Observations ciblées sur sessions, OTP, administration et modules ; **pas** un audit complet certifié |
| Décisions humaines DEC-01 à DEC-08 du 11/11/2026 | Principes de conception approuvés dans la conversation, à intégrer au registre de décisions lors de la formalisation documentaire |

**Hiérarchie :** le Référentiel gouverne l'organisation ; les décisions approuvées établissent les arbitrages ; le CDC fixe les exigences après approbation de sa version ; les sources, les tests et les preuves démontrent les réalisations ; les RESUME-ANCHOR servent à reprendre les sessions, sans remplacer les autorités normatives ni la certification.

### 2.1. Références supplémentaires de la V0.3

- **CDC V0.2 intégral, base de la présente révision :** `AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.2_CONSOLIDATION_DRAFT_2026-11-11.md` — 20 229 octets — SHA-256 `C947982DF3D195F97DA2FDA2016930396DF6696E569BA81A7F952EA6937BC61C`.
- **CODEX-AFRIPAY-01 :** rapport consolidé du 11/11/2026, **dernière restitution** après accès effectif au CDC V0.2 ; expertise READ-ONLY ; 12 objections E1–E12 et 15 scénarios T01–T15 proposés, **aucun test exécuté**.
- **Décision humaine de conception post-rapport :** adoption **de principe** d’un monolithe Python modulaire et d’une nouvelle interface HTTP FastAPI/Starlette/HTML, avec PostgreSQL comme autorité transactionnelle et retrait progressif de Streamlit **après qualification**. Validation humaine de la conservation fonctionnelle, des identifiants et de l’historique, de la migration séparée et du non-déploiement avant preuve.

La recommandation FastAPI est un **choix de cible**, pas une garantie de sécurité native et pas une permission d’écrire dans le dépôt.


## 3. État initial — constats et limites

| Identifiant | Constat établi / limite |
|---|---|
| **AFR-SEC-01** | `afripay_app.py` écrit et lit un jeton authentifiant via `st.query_params["session_token"]` ; le jeton retrouvé peut déclencher `restore_user_session`. Exposition potentielle d'un secret d'authentification par URL ; correction de conception prioritaire. |
| **AFR-SEC-02** | `core/session.py` conserve `otp_code`, `otp_phone` et `otp_verified` dans `st.session_state`. Génération, validation, expiration, consommation et concurrence ne sont pas établies par ces extraits. |
| **AFR-SEC-03** | Le parcours admin observé dépend de `admin_logged_in` dans `st.session_state` ; `verify_admin_password()` emploie `hmac.compare_digest()`. L'autorisation métier indépendante n'est pas démontrée. |
| **AFR-SEC-04** | `generate_session_token()` utilise `secrets.token_urlsafe(48)` ; le jeton brut apparaît dans l'INSERT/SELECT de `user_sessions`. Les garanties complètes d'expiration, révocation et conservation ne sont pas qualifiées. |
| **AFR-SEC-05** | Plusieurs services métier et scripts existent. La couverture globale des vérifications de permissions à chaque frontière sensible n'est pas encore démontrée. |

Les références trouvées dans `archives/` ou dans d'autres scripts par recherche textuelle ne constituent **pas**, à elles seules, des chemins de code actifs ou des vulnérabilités. Pas de preuve d'exploitation ni de certification de sécurité dans les contrôles réalisés.

## 4. Registre consolidé des décisions humaines validées

| Décision | Principe validé le 11/11/2026 | Conséquences et limites |
|---|---|---|
| **AFR-IDENT-DEC-01** | Continuité des comptes existants et maintien de l’identifiant utilisateur stable. | Préserver commandes, abonnements, relations et historique ; mécanismes de migration à définir. La cible Email OTP est tracée séparément comme exigence IDENT-02, sans élargir le libellé de DEC-01. |
| **AFR-IDENT-DEC-02** | Rattacher ou remplacer un e-mail exige la preuve de contrôle de la nouvelle adresse **et** une preuve fraîche d'autorité sur le compte historique ; à défaut, récupération contrôlée. | La possession du nouvel e-mail seule n'autorise pas la reprise du compte. |
| **AFR-IDENT-DEC-03** | Aucune fusion automatique des comptes ; suspendre les rattachements e-mail conflictuels ; confidentialité des autres comptes ; résolution exceptionnelle sécurisée et traçable. | Aucune fusion ni réattribution sans contrat spécifique approuvé. |
| **AFR-IDENT-DEC-04** | Récupération sécurisée préservant l'identité, avec preuve d'autorité suffisante et assistance humaine encadrée ; jamais par seul OTP au nouvel e-mail. | En l'absence de preuve suffisante, refuser l'opération ; modalités du support à qualifier. |
| **AFR-IDENT-DEC-05** | Session Authority indépendante de l'interface ; sessions sûres, expirables et révocables ; aucun jeton authentifiant dans les URL ; migration contrôlée des sessions historiques. | Transport navigateur et stratégie de révocation à sélectionner et tester. |
| **AFR-IDENT-DEC-06** | Autorité administrative indépendante de l'UI ; identités individuelles, authentification renforcée, permissions par opération et révocation contrôlée. | Définition des rôles, facteurs, transitions et procédures encore ouverte. |
| **AFR-SEC-DEC-07** | Moteur OTP autonome et sécurisé : cycle complet, preuve protégée, limites durables, usage unique, résistance à la concurrence, pas d'OTP de test comme autorité de production. | Contrats transactionnels et critères opérationnels à spécifier/qualifier avant implémentation. |
| **AFR-MET-DEC-08** | Autorisations métier indépendantes de l'interface et de la seule connexion ; protection des commandes, paiements, montants et abonnements ; traçabilité des changements sensibles. | Matrice exacte des rôles, permissions, opérations et preuves à établir. |

**Portée de la validation :** ces huit principes sont approuvés ; aucune bibliothèque, durée chiffrée, schéma SQL, procédure de rapprochement ou infrastructure précise n'a été approuvée implicitement.

### 4.1. Clarification normative DEC-01 / IDENT-02

Codex a relevé une attribution trop large à **AFR-IDENT-DEC-01** dans la V0.2. La présente révision dissocie :

1. **DEC-01 (décision historique) :** continuité des sujets et des données de comptes, conservation de l’identifiant stable.
2. **IDENT-02 (objectif de produit) :** Email OTP comme méthode de connexion principale envisagée, avec niveau d’assurance explicitement borné ; les modalités et les éventuelles exigences d’authentification renforcée demeurent à qualifier.

Cette correction n’annule aucune décision humaine antérieure. Elle évite simplement de faire approuver rétroactivement des mécanismes sous un numéro de décision plus large que sa formulation d’origine. Un futur numéro de décision distinct peut être attribué à la politique d’authentification après arbitrage formel.

### 4.2. Nouvelle décision de direction — AFR-ARCH-DIR-01 (11/11/2026)

**Orientation approuvée :** abandon progressif de Streamlit comme interface publique cible ; application HTTP Python modulaire avec priorité à FastAPI/Starlette et vues HTML ; PostgreSQL comme moteur transactionnel durable. **Le périmètre est une migration contrôlée, pas une réécriture aveugle.**

**Garde-fous approuvés :** conserver les identifiants des utilisateurs, toutes les relations métier, commandes, souscriptions, preuves financières et fonctionnalités utiles ; tester dans un environnement distinct ; ne supprimer l’ancien chemin qu’après démonstration de parité et validation humaine ; aucun accès réel Git/Render/DB ou effet production autorisé par cet accord de principe.

**Toujours ouverts :** architecture détaillée des cookies, interface (templates/progressive enhancement), choix du framework de tests navigateur, politique de facteurs pour opérations sensibles, rôle des workers, prestataires, objectifs de disponibilité et modèle économique territorial.


## 5. Identity Center AfriPay — exigences conservées

- **IDENT-01 —** Préserver la continuité des comptes existants. *Liens : DEC-01, DEC-03, DEC-04.*
- **IDENT-02 —** Concevoir Email OTP comme méthode primaire cible. *Orientation de produit conservée ; ne pas l’attribuer implicitement à DEC-01 ; migration progressive et niveau d’assurance à qualifier.*
- **IDENT-03 —** Prévoir Google et Microsoft comme méthodes alternatives, avec vérification du fournisseur. *Aucun fournisseur externe n'est automatiquement une autorité de session.*
- **IDENT-04 —** Permettre des passkeys optionnelles lorsque les exigences de sécurité seront satisfaites.
- **IDENT-05 —** Séparer la preuve d'authentification, l'identité, l'autorité de session et les permissions. *Liens : DEC-05 et DEC-08.*
- **IDENT-06 —** Un changement d'e-mail ou de téléphone ne doit pas créer implicitement une nouvelle identité. *Liens : DEC-01 à 04 ; conflit = suspension, jamais fusion automatique.*
- **IDENT-07 —** Prévoir les parcours de récupération, de changement d'identifiant et de révocation. *Liens : DEC-02 et DEC-04.*
- **IDENT-08 —** Les contrats ORYSK servent de référence de qualité ; aucune dépendance directe non approuvée n'est créée. *Les produits restent isolés.*

**Critère transversal à préciser :** la valeur et la stabilité de l'identifiant historique AfriPay doivent être constatées dans le schéma réel avant de choisir un mécanisme de migration. L'identité ne se déduit ni d'une adresse e-mail ni d'un numéro de téléphone mutable.

### 5.1. Contrats d’identité proposés — à qualifier

- `users.id` demeure l’ancrage d’identité **si l’inventaire du schéma réel confirme sa stabilité** ; un contact historique non vérifié ne devient jamais automatiquement un facteur d’accès.
- Un rattachement de courriel lie une preuve de contrôle du nouvel e-mail **et** une preuve fraîche sur le compte historique à la **même opération serveur**, avec portée, durée et consommation unique. Aucune adresse seule ne permet d’adopter un compte.
- Unicité et conflit sont résolus de façon transactionnelle ; deux demandes concurrentes ne créent jamais deux rattachements actifs pour le même objet approuvé. Aucun autre identifiant de compte n’est divulgué au demandeur.
- OIDC Google/Microsoft : identité durable basée sur `(issuer, subject)` validés, et non sur l’égalité des e-mails ; flux Authorization Code avec PKCE, `state` et `nonce` selon les paramètres approuvés. Le **code protocolaire de retour** doit être traité explicitement face à l’interdiction des jetons d’URL, qui vise l’autorité réutilisable.
- Passkeys WebAuthn : domaine/RP ID, challenge, origine et authentification utilisateur vérifiés côté serveur ; optionnelles pour l’usage général, mais potentiellement requises pour des privilèges élevés après arbitrage.
- La récupération est une procédure distincte et auditée ; aucune prise de contrôle administrative implicite, aucun rattachement sans preuves suffisantes. Les cas non démontrables restent non résolus.

**Critères associés :** T01, T02 ; IDENT-01 à IDENT-08, AC-07.


## 6. OTP et authentification — exigences conservées

- **OTP-01 —** Génération cryptographiquement sûre.
- **OTP-02 —** Expiration, usage unique et consommation atomique.
- **OTP-03 —** Limitation des demandes et tentatives selon une autorité serveur adaptée à la concurrence.
- **OTP-04 —** Aucun code OTP en clair ne doit constituer une autorité durable accessible par l'interface.
- **OTP-05 —** Protections contre rejeu, énumération et abus.
- **OTP-06 —** Aucun parcours OTP de test accessible comme autorité d'authentification en production.
- **OTP-07 —** Journalisation sans divulgation des preuves.

**Consolidation DEC-07 :** séparer demande/émission/livraison et vérification/consommation ; l'interface ne possède pas les secrets et ne proclame pas seule une preuve réussie. Le moteur doit traiter la concurrence, les interruptions et les résultats indéterminés sans admettre une nouvelle tentative comme prolongement d'une autorité expirée. L'émission d'une session exige une décision explicitement autorisée, distincte du seul résultat visuel OTP. Les paramètres concrets (durées, quotas, canaux, mécanismes cryptographiques) restent à établir.

### 6.1. Contrat OTP transactionnel — proposé

- États explicites : créé, émission planifiée, remis/état de livraison indéterminé, tenté, vérifié/consommé, expiré, révoqué. Les états de livraison ne sont **pas** des preuves de vérification.
- Génération par CSPRNG et HMAC/équivalent protégé pour vérifier les codes courts ; secrets du serveur hors code et hors journaux. Une simple empreinte non salée d’un OTP court ne suffit pas à protéger une base divulguée.
- Liaison au sujet ou contexte provisoire, à la cible, à la finalité, au tenant et à l’opération. Les preuves sont limitées à leur finalité : un OTP de changement de contact ne crée pas automatiquement une session.
- Compteurs partagés (cible, compte et contextes nécessaires) et consommation atomique au point serveur. Renvoi, changement d’onglet, redémarrage ou concurrence ne remettent pas abusivement les limites à zéro.
- Échecs conservés même lorsqu’une tentative d’authentification est rejetée. Gestion des erreurs et interruptions sans faux succès.
- Si un worker doit assurer la remise, le code en transit est chiffré/protégé, de durée brève, non journalisé et supprimé à terme. Le contrat doit distinguer reprise de livraison et répétition de génération.

**Paramètres à arbitrer :** longueur, validité, nombre d’essais, limites de demandes, politique de renvoi, rétention des traces, prestataire d’e-mail et coûts.

**Critères associés :** T03, T13 ; OTP-01 à OTP-07, AC-02 à AC-03.


## 7. Sessions et accès — exigences conservées

- **SESS-01 —** Aucun jeton de session authentifiant dans une URL.
- **SESS-02 —** Stockage des vérificateurs de session protégé ; absence de stockage brut inutile des jetons.
- **SESS-03 —** Expiration imposée par l'autorité serveur.
- **SESS-04 —** Révocation effective, déconnexion et invalidation.
- **SESS-05 —** Les opérations protégées doivent contrôler l'autorité de session indépendamment de l'UI.
- **SESS-06 —** Prévenir fixation, rejeu et réutilisation de sessions invalidées.
- **SESS-07 —** Prévoir des tests de concurrence, de restauration et de redémarrage lorsque pertinents.

**Consolidation DEC-05 :** une Session Authority serveur établit et gouverne les sessions après authentification ; les indicateurs Streamlit ne sont que des états de présentation. Un privilège administrateur est distinct d'une session client. La suppression des liens à jeton historiques nécessite un plan d'invalidation/réauthentification, un transport navigateur qualifié et des tests de non-régression. **Aucun cookie, paquet ou schéma exact n'est choisi par ce document.**

### 7.1. Transport HTTP et Session Authority — proposé

- Le navigateur détient un jeton opaque, transmis par **cookie serveur `Secure`, `HttpOnly`**, portée restreinte et politique `SameSite` adaptée. La valeur du jeton de session, les access tokens et ID tokens ne sont jamais placés en URL.
- Conserver en base un vérificateur du jeton et non une copie brute durable ; expiration absolue **obligatoire**, délai d’inactivité, état de révocation et éventuelle version de sécurité. Aucun succès de `touch_session()` ne remplace une résolution d’autorité.
- Contrôle serveur avant chaque commande métier protégée **et au point d’effet transactionnel** pour les actions financières ; permissions de l’acteur sur l’objet et niveau d’assurance nécessaires à l’action. Une session client ne donne pas l’autorité admin.
- Protection CSRF et contrôles d’origine adaptés aux opérations mutantes ; `SameSite` seul n’est pas une preuve suffisante.
- Rotation de session après authentification/élévation ; révocation globale ou ciblée, dont la sémantique garantit le refus de la **prochaine commande protégée** après achèvement de la révocation. Les opérations externes déjà engagées sont rapprochées indépendamment.
- Invalidation contrôlée des jetons historiques stockés/transmis en URL et réauthentification de transition. Aucun fallback de l’ancien token ne demeure dans les chemins exposés après bascule.

**Critères associés :** T04, T05, T06 ; SESS-01 à SESS-07, AC-01 et AC-04 à AC-06.


## 8. Administration — exigences conservées

- **ADMIN-01 —** Autorité administrateur distincte d'un simple booléen d'interface.
- **ADMIN-02 —** Permissions explicites par opération sensible.
- **ADMIN-03 —** Protections renforcées et réauthentification pour les changements critiques.
- **ADMIN-04 —** Révocation, expiration et journalisation des actions administratives.
- **ADMIN-05 —** Protection des secrets et des configurations.
- **ADMIN-06 —** Aucun privilège métier obtenu uniquement par l'affichage du dashboard administrateur.

**Consolidation DEC-06 :** identités individuelles, authentification renforcée (facteur indépendant adapté), principe du moindre privilège et validation serveur pour les opérations sensibles. L'ancien mot de passe administrateur partagé, s'il est encore utilisé en exploitation, appelle un plan de transition contrôlé ; ni sa suppression immédiate ni l'existence d'un mécanisme de remplacement qualifié ne sont présumées.

### 8.1. Administration et accès support — proposé

Identités administratives nominatives, rôles/permissions par opération et objet, authentification renforcée adaptée au risque, journalisation et révocation. L’élévation est courte et explicitement enregistrée. Les actions de support sont limitées à une demande, une justification, une permission, une durée et des preuves ; le support ne peut ni fabriquer une session client ni attribuer arbitrairement un compte.

Le remplacement d’un mot de passe administrateur historique partagé doit être ordonné et vérifié sans coupure non maîtrisée. Les accès techniques directs à PostgreSQL et aux secrets sont **une frontière distincte**, à réduire par séparation des fonctions, comptes limités, contrôles de changements et journal protégé.

**Critères associés :** T05, T14 ; ADMIN-01 à ADMIN-06.


## 9. Continuité métier et autorisation — exigences conservées

- **MET-01 —** Préserver les utilisateurs et leurs relations.
- **MET-02 —** Préserver les commandes et historiques.
- **MET-03 —** Préserver les plans `FREE`, `PREMIUM` et `PREMIUM_PLUS`.
- **MET-04 —** Contrôler les changements d'abonnement et les opérations financières par permissions explicites.
- **MET-05 —** Conserver la cohérence des montants XAF/EUR.
- **MET-06 —** Aucune migration irréversible sans sauvegarde, tests et autorisation appropriée.

**Consolidation DEC-08 :** toute modification sensible des commandes, paiements, paramètres financiers ou abonnements doit relever d'une décision d'autorisation serveur liée à l'acteur et à l'objet. La matrice exacte des rôles et actions est **à concevoir**, avec tests d'accès refusé, d'escalade de privilège, de concurrence, d'intégrité et de traçabilité. Aucun changement financier ni migration SQL réelle n'est autorisé par ce CDC.

### 9.1. Contrats d’opérations financières — proposés

**Toutes les commandes sensibles reçoivent une autorité vérifiée sur serveur**, et ne doivent pas accepter un `user_id`, un `is_admin`, un solde ou un montant comme preuve de permission venant du navigateur.

- **Commandes / quota FREE :** une transaction PostgreSQL vérifie la session et les droits, réserve le quota, écrit la commande, l’idempotence et l’audit/outbox. Deux tentatives concurrentes pour la dernière unité autorisée entraînent au plus une réussite. **Les limites FREE historiques observées (2 commandes et 50 000 XAF) sont à confirmer commercialement**, y compris leur période.
- **Paiement :** états fermés et commandes métier typées, authentification des événements fournisseur, montant/devise/commerçant/référence conformes, dédoublonnage et idempotence. Une preuve d’interface ou un retour navigateur ne justifie pas un encaissement confirmé.
- **Résultat externe indéterminé :** intention durable et rapprochement avant réémission. Ne pas maintenir une transaction SQL durant l’appel réseau ; l’outbox est une garantie de reprise locale, pas une promesse d’exécution exactement une fois chez un tiers.
- **Remboursement :** somme réservée + déjà remboursée bornée par les sommes effectivement capturées et remboursables, dans la devise et suivant les clauses du paiement initial. Contrôles simultanés et permissions exigés.
- **Montants :** unités mineures entières avec devise explicite, `Decimal` pour conversion intermédiaire et `NUMERIC` pour les taux SQL ; ne pas présumer l’exposant d’une devise. Figement des taux, frais et versions tarifaires au devis/paiement initial. L’arrondi au multiple de cinq XAF est une **règle commerciale à approuver**, pas une propriété universelle de la monnaie.
- **Abonnements :** historique durable et calcul unique des droits à partir d’une politique versionnée ; renouvellement et expiration concurrents ne doivent ni retirer un droit acquis ni en octroyer artificiellement.
- **Audit :** événements critiques durables liés aux transactions ; sauvegardes, restauration, contrôles anti-rejeu des événements et rapprochement financier.

**Critères associés :** T06–T11, T13–T14 ; MET-01 à MET-06, AC-06 à AC-08.


## 10. Modernisation UI/UX — exigences conservées

- **UI-01 —** Interface cohérente et professionnelle.
- **UI-02 —** Navigation claire entre espaces client et admin.
- **UI-03 —** Formulaires accessibles et validation explicite.
- **UI-04 —** Affichage adapté aux écrans desktop et mobile.
- **UI-05 —** Messages d'erreur utiles sans divulguer d'informations de sécurité sensibles.
- **UI-06 —** Ne pas confondre succès visuel de connexion et authentification effectivement autorisée.

La refonte visuelle devra s'appuyer sur les contrats d'identité, de session et de permission effectivement implémentés et qualifiés. La qualité esthétique ne constitue pas une preuve de sécurité.

### 10.1. Architecture de présentation décidée en principe

La cible privilégiée est **FastAPI/Starlette + HTML/CSS accessible**, dans un monolithe Python modulaire. Les pages client, vendeur (si le modèle commercial le requiert), support et administrateur utilisent **les mêmes services d’autorité et commandes métier**. Aucune logique d’autorisation ne demeure uniquement dans les vues.

**Proposition de couches**, à valider par preuve d’intégration :

```text
Navigateur (HTTPS, cookies, CSRF, accessibilité)
    -> Routes HTTP FastAPI / Starlette (validation des entrées)
       -> Identity / OTP / Session Authority / Autorisation
       -> Services de commandes métier typées
          -> Unité de travail PostgreSQL, contraintes, journaux, inbox/outbox
             -> Workers et adaptateurs prestataires autorisés
```

**Ce qui doit être préservé** avant toute suppression de Streamlit : inventaire des pages et parcours effectivement actifs, calculs et règles métier confirmés, images/identité visuelle autorisées, messages et flux d’accompagnement utilisateur, fonctionnalités client et administration, exports/imports et historiques, usages mobiles et accessibilité. Ne pas recopier les erreurs de sécurité des anciens chemins.

**Qualité de service UI :** cible de travail WCAG 2.2 AA, clavier, lecteurs d’écran, états d’erreur sans fuite, fuseaux horaires/devises localisés, formulaires utilisables sur mobile et parcours de réauthentification transparents.

**Critères associés :** T04–T06, T15 ; UI-01 à UI-06, AC-09.


## 11. Infrastructure et exploitation — exigences conservées

- **INF-01 —** Préserver la séparation AfriPay / ORYSK.
- **INF-02 —** Documenter les frontières Render / PostgreSQL.
- **INF-03 —** Protéger credentials, secrets et journaux.
- **INF-04 —** Définir sauvegardes, restauration et surveillance.
- **INF-05 —** Aucun changement de production avant qualification et autorisation humaine.

Les services et la base attribués à AfriPay sont hors périmètre des travaux ORYSK. Ce document n'autorise aucune modification de Render, des bases réelles, des DNS, des comptes ou des secrets.

### 11.1. Déploiement contrôlé, migration et récupération

- Séparer dev/test de la production ; PostgreSQL de test représentatif pour les essais de concurrence et de restauration. Les doubles et mocks ne prouvent pas les verrous réels.
- Migrations de schéma **versionnées et distinctes du démarrage HTTP**. Le démarrage ne crée ni ne normalise silencieusement le schéma ; incompatibilité = refus sûr.
- Rôles PostgreSQL distincts pour application, migration, opérations privilégiées et lecture ; politiques d’accès minimales et secrets hors dépôt.
- Workers durables pour e-mails, événements et rapprochements ; surveillance, délais, limites de reprise et sorties d’échec explicites.
- Sauvegardes chiffrées **et restauration exercée** ; vérification des identifiants, relations et montants ; invalidation des anciennes preuves/session après restauration ; rapprochement des paiements externes avant réouverture.
- **Modèle d’ouverture internationale** à définir par entité juridique × pays × service × devise × prestataire × circulation des fonds. Aucune qualification juridique/agrément n’est présumée.
- RPO/RTO, disponibilité, rétention, prestataires e-mail, contraintes données personnelles, fiscalité, support et budgets restent des arbitrages réels à mesurer.

**Critères associés :** T12–T14 ; INF-01 à INF-05, AC-07, AC-08, AC-10.


## 12. Critères d'acceptation — les dix critères conservés

| ID | Critère conservé | Type de preuve attendu, à spécifier |
|---|---|---|
| **AC-01** | Un jeton d'URL ne permet plus d'ouvrir une session. | Test négatif de restauration depuis une URL et contrôle des liens anciens. |
| **AC-02** | Un OTP expiré ou consommé ne peut être réutilisé. | Tests d'expiration, rejeu et concurrence. |
| **AC-03** | Les limites de tentatives résistent aux sessions multiples et aux accès concurrents. | Tests parallèles avec autorité durable. |
| **AC-04** | Une session expirée ou révoquée est refusée. | Tests serveur après déconnexion, révocation et redémarrage pertinent. |
| **AC-05** | Un client ne peut pas obtenir des privilèges admin par modification de l'état de présentation. | Tests négatifs de privilèges et de contrôle au point d'effet. |
| **AC-06** | Les opérations métier refusent les sujets non autorisés. | Matrice d'accès négative : commandes, paiements, abonnements. |
| **AC-07** | Les migrations conservent comptes, commandes et abonnements selon les règles validées. | Réconciliation des données et tests de continuité. |
| **AC-08** | Les tests automatisés prouvent les garanties et détectent les régressions essentielles. | Résultats réels, versions du code et périmètre précisés. |
| **AC-09** | L'interface reste utilisable et accessible. | Scénarios utilisateur desktop/mobile et accessibilité. |
| **AC-10** | La livraison est refusée si une exigence de sécurité bloquante n'est pas satisfaite. | Rapport de blocages, décision d'acceptation et preuve de qualification. |

Les preuves indiquées sont des **objectifs** ; elles ne sont pas des tests déjà exécutés.

### 12.1. Catalogue de preuves complémentaires T01–T15 — proposé par Codex, non exécuté

Les dix identifiants **AC-01 à AC-10 sont conservés sans substitution**. Les scénarios ci-dessous sont une **décomposition opérationnelle complémentaire**, à faire approuver et automatiser sous des versions de code identifiées.

| ID | Vérification reproductible attendue | Domaine |
|---|---|---|
| **T01** | Rattachement d’un e-mail : nouvelle adresse seule, ancienne preuve seule ou preuve hors parcours = refus ; deux preuves liées et fraîches = même sujet, même historique. | Identité |
| **T02** | Deux rattachements concurrents : au plus un actif ; aucun accès au compte d’autrui, aucune fusion. | Identité |
| **T03** | OTP : une seule preuve sous forte concurrence ; expiration, mauvaise finalité, rejeu, renvois et compteurs durables. | OTP |
| **T04** | Session : refus de la prochaine commande après révocation/expiration, même sur onglet ouvert ; aucune restauration par URL ; cookie et CSRF. | Session |
| **T05** | Administration : permission serveur et niveau d’assurance ; falsification UI et fallback SQL refusés. | Administration |
| **T06** | Propriété : identifiant ou code de commande d’autrui ne révèle pas ses détails privés. | Confidentialité |
| **T07** | Quota FREE : un seul succès pour la dernière unité ; panne ne laisse pas de réservation/commande séparée ; idempotence. | Commande |
| **T08** | Paiement : signature, montant, devise, ordre et unicité des événements ; rapprochement après réponse indéterminée. | Paiement |
| **T09** | Remboursement : dépassement et concurrence refusés ; cumul borné par l’autorité financière. | Remboursement |
| **T10** | Monétaire : valeurs limites, exposants, arrondis, devis figés et refus d’entrées incohérentes. | Finances |
| **T11** | Abonnement : expiration/renouvellement simultanés, droits justifiés et historique conservé. | Abonnements |
| **T12** | Migration : comptes, clés, commandes, états et montants rapprochés ; aucune différence inexpliquée. | Migration |
| **T13** | Pannes : refus sûr, absence de faux succès, reprise bornée après PG, e-mail ou paiement indisponible. | Résilience |
| **T14** | Restauration : état ancien d’autorisation inopérant, rapprochement des paiements avant reprise, aucun doublon outbox. | Continuité |
| **T15** | Parcours client/admin, mobile, clavier, lecteur d’écran, langues et devises ; aucun droit fondé sur l’UI. | UI/UX |

Le test ne devient une **preuve** que lorsqu’il comporte environnement, données, version de code, résultat, limites et reproduction. Un test simulé ne démontre pas la sûreté PostgreSQL réelle. Toute exigence bloquante sans preuve empêche le passage en production.

### 12.2. Traçabilité initiale des objections E1–E12

| Objection Codex | Exigences historiques liées (proposition) | Tests cibles |
|---|---|---|
| E1 — Rattachement d’identité | IDENT-01, IDENT-06, IDENT-07 | T01, T02 |
| E2 — Niveau d’assurance Email OTP | IDENT-02, IDENT-04, ADMIN-03 | T01, T05 |
| E3 — OTP et concurrence | OTP-01 à OTP-07 | T03 |
| E4 — Session ouverte révoquée | SESS-03, SESS-04, SESS-05 | T04 |
| E5 — Propriété des objets métier | MET-04, SESS-05 | T06 |
| E6 — Quotas FREE non atomiques | MET-03, MET-04 | T07 |
| E7 — Paiements et remboursements | MET-04, MET-05 | T08, T09 |
| E8 — Montants et change | MET-05 | T10 |
| E9 — Abonnements | MET-03, MET-04 | T11 |
| E10 — Chemins SQL de secours | MET-04, ADMIN-02 | T05, T07–T09 |
| E11 — Migration au démarrage | INF-02, INF-05, MET-06 | T12, T13 |
| E12 — Journalisation et restauration | ADMIN-04, INF-03, INF-04 | T14 |

**Cette cartographie est une proposition AfriDIGID à valider ;** Codex a formulé E1–E12 et T01–T15, mais chaque association précise aux identifiants historiques ne doit pas être présentée comme une validation acquise.


## 13. Arbitrages encore ouverts — ne pas présumer une décision

1. **Migration téléphone → e-mail :** preuve d'autorité historique réellement disponible, enrôlement progressif, doublons, indisponibilité du téléphone et prévention des prises de contrôle.
2. **Récupération :** facteurs acceptables, rôle du support, validation indépendante, restrictions après récupération et traitement des litiges.
3. **Identité et fournisseurs :** format de l'identifiant stable, liens fournisseurs, déliaison, récupération, politique passkeys et cas de comptes préexistants.
4. **Sessions :** transport navigateur compatible avec Streamlit/Render, rotation, expiration, invalidation des sessions historiques, protection des vérificateurs et exigences anti-CSRF selon la solution retenue.
5. **OTP :** durées, seuils, canaux de livraison, schéma transactionnel et gestion des résultats incertains.
6. **Administration :** rôle et matrice de permissions, authentification renforcée, transition depuis les credentials historiques, procédures d'urgence et contrôle des actions critiques.
7. **Métier :** catalogue des opérations financières et commerciales à protéger, responsabilités de chaque acteur, granularité des permissions et exigences de réconciliation.
8. **Infrastructure :** frontières réelles Render/PostgreSQL, sauvegardes, risques, coûts et calendrier de migration.
9. **Écosystème AfriDIGID :** éventuelle identité transverse entre produits soumise à un arbitrage ultérieur ; aucune mutualisation implicite.
10. **UI/UX :** critères de design, parcours, accessibilité, ergonomie et ordre de livraison après les fondations de sécurité.

L'existence de ces questions **n'invalide pas** les huit principes déjà approuvés ; elle empêche seulement d'affirmer qu'une implémentation précise est entièrement décidée.

### 13.1. Arbitrages supplémentaires de la V0.3

| Domaine | Décision acquise | Arbitrage encore requis |
|---|---|---|
| Interface cible | Migration progressive hors Streamlit vers FastAPI/Starlette + HTML approuvée en principe | Templates, stratégie d’interaction, parcours exacts, qualification HTTP/CSRF |
| PostgreSQL | Autorité transactionnelle cible | Version, schémas, migrations, rôles, sauvegardes et contrat d’exploitation |
| Utilisateurs | Continuité des identifiants et relations | Politique détaillée de rattachement, récupération et migration téléphone/e-mail |
| OTP | Autorité serveur autonome exigée | Paramètres, livraison, isolation, secrets et assurance pour opérations sensibles |
| Administration | Autorité nominative et permissions | Matrice des rôles, MFA résistant à l’hameçonnage et procédures d’urgence |
| Commerce | Conserver commandes, souscriptions et états | Périodes FREE, règles tarifaires, devises, arrondis, remboursements |
| Paiements | Aucun faux succès, rapprochement, idempotence | Nature du service, prestataires, territoires, flux économiques et obligations |
| Exploitation | Aucune bascule sans preuve | RPO/RTO/SLO, coûts réels, procédures d’incident et restauration |

**Aucune catégorie de paiement, juridiction, banque, taux de change, prestataire ou licence n’est approuvée par défaut.**


## 14. Gouvernance, traçabilité et autorisations

**Suivi documentaire indépendant :** prévu → rédigé → relu → validé → certifié si pertinent → consolidation Git autorisée.  
**Suivi logiciel indépendant :** prévu → implémenté → compilé → testé → certifié → prêt production sous décision.  
**Statut :** V0.4 DRAFT préparée hors dépôt pour relecture ; aucune validation globale V0.4, aucun test applicatif ni certification nouveaux.

- Ne pas rouvrir les audits déjà suffisants ; approfondir uniquement les contrats, risques ou preuves réellement manquants.
- Préparer **une seule mission Codex AfriPay consolidée** lorsque le CDC aura été suffisamment arbitré ; ne pas confondre avec la mission ORYSK en cours.
- Ne pas inclure de secrets dans les documents, RESUME-ANCHOR ou rapports partageables.
- L'enregistrement documentaire de cette nouvelle V0.4, autorisé exclusivement dans le périmètre documentaire, ne permet **aucun** changement du code, de Git, de PostgreSQL, de Render, des DNS, des secrets ou de la production.
- Le Référentiel, la V0.1 et le premier RESUME-ANCHOR conservent leurs empreintes et leur historique.

### 14.1. Ordre de réalisation — six portes de preuve

| Gate | Travail de conception/développement futur | Preuve exigée pour passer |
|---|---|---|
| **G0 — Contrats** | Approuver les acteurs, preuves, flux financiers, pays initiaux, permissions, états et règles monétaires | Matrice décisions → exigences → scénarios, arbitrages bloquants tranchés |
| **G1 — Fondations transactionnelles** | Gestion de transactions, montants exacts, migrations, journal, inbox/outbox | Tests PostgreSQL isolés, panne/rollback, contraintes et invariants reproductibles |
| **G2 — Identité et accès** | OTP, rattachement, récupération, Session Authority, administration | T01–T05 avec preuves et tests adversariaux |
| **G3 — Métier financier** | Commandes, quotas, paiements, remboursements, abonnements | T06–T11, concurrence et rapprochement vérifiés |
| **G4 — Interface web** | FastAPI/Starlette + HTML ; parité des parcours historiques sans réintroduire les bypass | T04–T06, T15 et inventaire fonctionnel comparé à l’existant |
| **G5 — Migration et exploitation** | Répétitions de migration, retour arrière sûr, restauration, incident, supervision, revue indépendante | T12–T14, écarts rapprochés, dossier opérationnel et décision humaine distincte |

Les six portes relèvent d’un **programme unique consolidé**, mais peuvent être organisées en lots d’implémentation contrôlés. Une preuve absente reste ouverte ; aucun PASS théorique. La permission de développement local sera une décision séparée. Les écritures réelles, Git et Render restent interdites sans autorisation particulière.

### 14.2. Conservation et transition sans perte

**À préserver :** `users.id` et ses relations, inscriptions historiques, commandes, preuves et historiques de paiement, abonnements FREE/PREMIUM/PREMIUM_PLUS, factures/exports légitimes, éléments visuels utiles et règles commerciales confirmées. Une valeur historique est conservée même si sa méthode de calcul doit évoluer pour les nouvelles opérations.

**À adapter :** couches UI Streamlit, sessions et administration historiques, services de commande et transactions, représentations `float`/`DOUBLE PRECISION`, traitements de migration au démarrage.

**À interdire dans les chemins remplacés :** jetons de session en URL, OTP UI comme autorité, permissions déduites des indicateurs visuels, SQL de secours après refus métier.

**Stratégie de migration à valider :**

1. Inventaire en lecture seule de la version réellement déployée, des fonctionnalités, du schéma et des données ; distinguer `afripay_app.py` et `afripay_app_REBUILD.py`.
2. Baseline fonctionnelle et financière de l’existant (identifiants, relations, abonnements, commandes, montants, états, justificatifs), avec comptes de contrôles et anomalies préexistantes.
3. Développement de la cible isolée sans toucher au service réel ; tests unitaires, PostgreSQL de qualification et essais de charge/concurrence.
4. Migrations **répétées à partir de copies autorisées**, sans inventer un téléphone ni transformer un contact e-mail non vérifié en identité ; conflits suspendus et historiques non écrasés.
5. Préparation d’une fenêtre de bascule maîtrisée ; événements prestataires durables, sessions anciennes invalidées et réauthentification contrôlée.
6. Comparaison après migration par compte/commande/abonnement/paiement et preuve d’absence d’écart inexpliqué.
7. Retour arrière uniquement vers une version **qualifiée et compatible avec les données** ; ne jamais réactiver une faiblesse connue. Si retour sûr impossible, prévoir maintenance contrôlée et correction.
8. Décision de mise en service séparée, signée par le responsable humain après revue du dossier de qualification.

**Note :** aucune modification des comptes, environnements ou données réelles n’est entreprise pendant la rédaction de ce document.


## 15. Point de reprise historique de la V0.3 (conservé pour traçabilité)

1. Soumettre la présente **V0.3 DRAFT** à une revue humaine et vérifier la matrice des 55 identifiants, la conservation de la V0.2 et la traçabilité des huit décisions.
2. Trancher les arbitrages qui commandent le modèle financier, les premiers pays/services, les preuves acceptées et l’exploitation réelle. Les valeurs proposées ne deviennent pas des décisions par insertion dans le texte.
3. Autoriser séparément, si souhaité, une **création documentaire uniquement** dans `afripay/docs/engineering/AFRIPAY/CAHIERS-DES-CHARGES/` ; ne remplacer aucun fichier historique.
4. Préparer la mission consolidée Codex-AFRIPAY d’**implémentation** uniquement après approbation des contrats nécessaires et définition d’un environnement de test isolé. L’autorisation de développement ne vaut jamais autorisation de migration des données réelles, de Git ou de production.

---

## 16. Objet, mission et ambition AfriPay — décisions consolidées

### 16.1. Identité du produit et périmètre initial

**AfriDIGID** est l’entreprise porteuse de la plateforme et des relations commerciales. **AfriPay Afrika** est son produit et son interface numérique historique — **le premier logiciel développé par AfriDIGID**. La mission initiale est de rendre possibles des **achats de produits et de services internationaux** pour des clients n’ayant pas nécessairement une carte de paiement internationale, en utilisant des moyens de règlement locaux appropriés. L’objectif n’est **pas** d’offrir d’emblée un compte de paiement rechargeable ou un transfert d’argent entre utilisateurs.

**Parcours fonctionnel de référence (fonctionnel, non encore qualification réglementaire) :**

1. Le client identifie un produit ou un service sur un site de commerce international et se connecte à AfriPay.
2. Il fournit les références exactes (marchand, URL, prix, caractéristiques/variantes, identité et modalités utiles) ; la plateforme distingue biens et services.
3. AfriPay prépare un devis vérifiable : prix marchand, éventuels frais de tiers, change applicable, **commission AfriPay explicitement annoncée**, montant total dû et responsabilités acceptées.
4. Le client effectue le paiement local selon les instructions du prestataire/compte marchand officiellement proposé, par exemple Mobile Money au Cameroun pour les marchés où ce canal est disponible.
5. AfriPay **n’exécute pas l’achat sur la base d’une simple capture d’écran** : le paiement effectif est vérifié avec une source fiable et rapproché à la commande.
6. AfriPay organise l’achat auprès du fournisseur international par un circuit contractuel et financier autorisé ; la preuve d’exécution est conservée, la commande suivie et le client informé.
7. Pour les biens physiques, les responsabilités de livraison, du transitaire, des frais d’importation et de douane sont exposées et acceptées contractuellement ; le README de mars indiquait que la logistique/douane n’étaient pas prises en charge par AfriPay. **AfriPost constitue un projet distinct, non assimilé au service AfriPay initial.**

**Distinction indispensable :** « AfriPay ne garde pas l’argent des clients » exprime l’absence de **portefeuille client ou de conservation volontaire de solde** dans le produit initial. Cela ne prouve pas l’absence de réception temporaire de fonds sur les comptes marchands. Les flux de règlement sont à caractériser et à faire qualifier juridiquement avant toute exploitation réelle. Le rôle exact d’AfriDIGID (agent/mandataire, commerçant-acheteur ou revendeur) et la partie juridiquement acheteuse chez le fournisseur demeurent un **arbitrage G0 ouvert** ; aucune fiction contractuelle ne doit le remplacer.

### 16.2. Ambition à moyen et long terme

- **Phase 1 :** AfriPay SAFE — faciliter les achats internationaux avec identité sûre, paiements locaux vérifiables, commandes et commissions traçables.
- **Phase 2 :** vendeurs sociaux et services aux marchands ; développer la visibilité de la plateforme auprès des entreprises et partenaires.
- **Phase 3 :** AfriMarketplace et services connexes de l’écosystème AfriDIGID, sans fusion implicite des autorités ni des comptes entre produits.
- **Phase PSP :** projet **ultérieur et indépendant**, soumis à une qualification réglementaire, financière et technique avant toute mise en œuvre. La vision ne vaut ni autorisation d'exercer ni calendrier approuvé.

Les anciennes références au **pilote Cameroun** dans README restent historiques ; la sélection des **premiers pays effectivement ouverts** dépend d’un arbitrage commercial, juridique, prestataires et risques distinct. Ne pas substituer un ordre de marché à une autorisation de lancement.

## 17. Politique économique — historique du taux et commissions

### 17.1. Registre temporel des sources et décisions

| Référence | Nature de la preuve | Constat / décision | Règle de gouvernance |
|---|---|---|---|
| README GitHub `main`, publié le 03/03/2026 | Documentation historique | Commission **10 %**, minimum **10 €**, facilitation d’achats internationaux et paiement Mobile Money | **Historique**, non barème courant par défaut |
| `services/settings_service.py`, GitHub `main` au 11/11/2026 | Code consulté, paramètres par défaut | `service_fee_percent = "20"` | Valeur de configuration ; **pas à elle seule la preuve d’application à tous les plans** |
| `services/order_service.py`, GitHub `main` au 11/11/2026 | Code consulté, formule métier | `FREE = 0 XAF`, `PREMIUM = 20 %`, `PREMIUM_PLUS actif = 0 XAF`, sinon traitement PREMIUM | **Comportement constaté**, soumis à rapprochement de la politique commerciale |
| Décision humaine du 11/11/2026 | Arbitrage commercial explicite | Le **20 % devient le taux de référence** après réévaluation des charges de personnel, téléphonie, transferts et exploitation | **Décision d’orientation actuelle** ; les exceptions par formule restent à réconcilier avant changement du code |

**AFR-BIZ-DEC-01 — Taux de référence :** l’évolution historique **10 % → 20 %** est reconnue. Le taux de **20 %** est approuvé comme **référence commerciale du service quand une commission proportionnelle est due**. Les plans `FREE`, `PREMIUM`, `PREMIUM_PLUS` conservent leurs états et historiques existants ; aucune suppression implicite des exonérations ou plafonds observés n’est autorisée. La grille contractuelle définitive par plan, les éventuels minimums, la période FREE et les exceptions requièrent une validation explicite ; **ne pas étendre automatiquement le 20 % à toutes les opérations**.

La commission rémunère notamment les charges de service mentionnées par le responsable humain : personnel, crédits téléphoniques, transfert/paiement, exploitation et accompagnement client. Ces postes expliquent la décision de taux, sans produire ici un calcul de rentabilité certifié.

### 17.2. Séparation des montants et preuves

Une commande doit distinguer de façon durable : `prix_fournisseur`, `devise_fournisseur`, `taux_change/heure/source`, `prix_converti`, `frais_tiers_justifiés`, `commission_AfriPay`, `total_client`, `montant_reçu`, `montant_payé_au_fournisseur`, `remboursements` et états associés. Ces libellés sont **conceptuels**, non un schéma de migration SQL approuvé. Aucun recalcul rétroactif de l’historique au taux du jour. Les règles de représentation monétaire exacte de la V0.3 restent obligatoires.

**La rémunération économique d’AfriDIGID n’est pas identique au montant encaissé pour une commande.** Les commandes historiques conservent leurs règles et preuves d’époque. Le circuit exact de règlement du prix fournisseur, la propriété des sommes encaissées, le mandat éventuel et les obligations de remboursement demeurent des sujets G0 ouverts, à documenter puis qualifier juridiquement.

**AC-BIZ-01 :** le devis et la confirmation montrent séparément le prix fournisseur, les frais de tiers, la commission et le total ; le montant dû est déterminé côté serveur.

**AC-BIZ-02 :** toutes les règles plan/taux sont versionnées et vérifiées ; le changement de barème n’altère jamais une commande confirmée antérieure.

**AC-BIZ-03 :** aucun versement, remboursement ou changement de plan n’est accepté sur une affirmation client ou un booléen d’interface ; rapprochement et autorisations indépendantes.

## 18. Module d’affichage publicitaire AfriPay — décision de périmètre

**AFR-UI-ADS-01 — Emplacements (VALIDÉ) :** la plateforme propose au minimum deux emplacements réutilisables : **`ADS-SIDEBAR`** (format vertical latéral) et **`ADS-FOOTER`** (bannière horizontale dans le bas du contenu, avant le pied de page). Les gabarits sont adaptatifs sur mobile ; aucun affichage ne doit obstruer une opération sensible, la connexion, l’OTP, le paiement ou la confirmation d’achat.

**AFR-UI-ADS-02 — Rotation (VALIDÉ) :** chaque emplacement diffuse **successivement des campagnes de plusieurs annonceurs**, selon un intervalle paramétrable et un mécanisme de sélection contrôlé. La rotation des deux emplacements est **indépendante** et fonctionne **sans rechargement complet de page**. L’exemple utilisateur de plus de dix annonces observées en deux minutes illustre l’objectif de fluidité ; il **ne constitue ni un intervalle obligatoire ni une garantie de nombre d’impressions**.

**AFR-UI-ADS-03 — Rôle de plateforme (VALIDÉ) :** les **annonceurs préparent et fournissent** leurs visuels/créations conformes aux spécifications remises par AfriDIGID. AfriPay est le **support de diffusion**, pas le studio créatif, pas la régie commerciale et pas un outil de facturation publicitaire. Les services commerciaux habilités d’**AfriDIGID** contrôlent les relations, contrats, validations, campagnes et diffusion ; la **comptabilité AfriDIGID** enregistre et suit les revenus publicitaires dans son propre système.

**AFR-UI-ADS-04 — Découverte (VALIDÉ) :** un lien public et visible **« Faire de la publicité sur AfriPay »** présente les emplacements et les modalités de contact avec les services compétents d’AfriDIGID. Il n’expose ni commandes individuelles, ni données clients, ni outils internes de diffusion. Exemple d’usage : une marque ou un vendeur intéressé par les visiteurs d’AfriPay découvre les emplacements et contacte AfriDIGID. **Une marque citée comme exemple (Nike, Amazon, Roomba) n’est pas un partenaire réel présumé.**

### 18.1. Frontières organisationnelles et fonctionnelles

| Acteur | Responsabilité autorisée | Hors périmètre AfriPay |
|---|---|---|
| Annonceur | Remet fichiers, texte, lien de destination et période envisagée aux services AfriDIGID | Aucun accès à la base clients/commandes ou aux paramètres d’administration |
| Service compétent AfriDIGID | Examine, approuve, programme, active, suspend et retire des campagnes avec droits individuels | Pas de vente/contrat/facturation réalisée automatiquement par le moteur de commandes AfriPay |
| Comptabilité AfriDIGID | Facturation, encaissement commercial et suivi des recettes publicitaires dans le système comptable de l’entreprise | Aucune écriture « revenu publicitaire » injectée dans les paiements de commandes AfriPay |
| Service d’affichage AfriPay | Applique les paramètres approuvés, choisit et affiche les créations dans les zones prévues | Pas de création graphique automatique, pas de régie CRM intégrée, pas de partage de données personnelles avec annonceurs |

**Ne pas inventer un module de marketplace publicitaire, un outil de facturation, des enchères publicitaires, ni un compte annonceur pouvant publier librement dans AfriPay** : ces fonctionnalités ne sont pas approuvées.

## 19. Contrat technique proposé — gestion et rotation des annonces

Les éléments suivants sont des **propositions d’implémentation à qualifier** et ne sont pas encore des API/SQL approuvés.

### 19.1. Configuration et données conceptuelles

- **Placement :** `placement_id`, `page_scope`, format/ratio autorisé, priorité d’affichage, `enabled`, politique mobile et emplacement de repli.
- **Campagne :** identifiant immuable, référence annonceur interne, création(s), date de début/fin en fuseau convenu, statut (`DRAFT`, `PENDING_REVIEW`, `APPROVED`, `ACTIVE`, `PAUSED`, `EXPIRED`, `REVOKED`), cible URL et version de validation.
- **Création :** image fournie, format/poids/dimensions vérifiés, variante desktop/mobile, texte alternatif, empreinte, stockage durable séparé et non exécutable.
- **Rotation :** intervalle **configurable** par emplacement, politique de sélection équitable/pondérée à définir, plafonds éventuels, absence de répétitions excessives, changement sans déploiement et repli si zéro campagne éligible.
- **Traçabilité :** auteur de la programmation, validateur, changements de statut et version, date d’effet, suspension, raisons et preuves. Chaque rôle suit le principe du moindre privilège.

**Formats indicatifs non décidés :** `300 × 600 px` pour un encart latéral et `970 × 250 px` pour une bannière horizontale ; les dimensions finales, tailles maximales, types autorisés et variants mobile font l’objet d’un **guide technique annonceurs** à approuver. PNG/JPEG/WebP sont des candidats ; fichiers HTML/JS tiers non approuvés.

### 19.2. Diffusion sûre et comportement UI

1. Le navigateur récupère uniquement les métadonnées des **campagnes actives approuvées**, limitées au placement et à l’horaire ; chaque entrée est contrôlée côté serveur. Ne jamais accorder l’autorité de publication à un état côté navigateur.
2. Le remplacement automatique utilise une zone stable, dimensionnée, non intrusive ; au changement, **pas de navigation forcée**, pas de perte de saisie, pas de rafraîchissement des routes sensibles.
3. Le visiteur doit pouvoir **mettre en pause/arrêter la rotation**, notamment pour respecter les exigences d’accessibilité concernant le contenu qui se met à jour automatiquement ; tenir compte des préférences de mouvement réduit. Les valeurs de durée, nombre d’annonces et algorithmes restent configurables à qualifier.
4. Les créations sont vérifiées avant approbation : type réel du fichier, dimensions, taille, métadonnées, sécurité du stockage ; pas d’injection HTML ou de JavaScript d’annonceur. Les liens de destination autorisent un schéma sûr (`https:`), avec validation et moyens de retrait immédiat. Une politique CSP et la protection du domaine hébergeur seront définies.
5. Toute annonce est identifiée visiblement **« Publicité »** ou **« Sponsorisé »** ; une annonce n’implique ni recommandation officielle ni relation contractuelle spéciale avec AfriPay.
6. Aucune donnée personnelle de client, commande, paiement ou identité ne doit être visible ou accessible aux annonceurs via l’interface, les API ou des statistiques individuelles. Les statistiques agrégées, si ajoutées ultérieurement, exigent un examen confidentialité et une décision distincte ; **pas de ciblage comportemental par défaut**.
7. Les modifications faites par le personnel habilité prennent effet sans changement du code ni redéploiement de l’application ; les mises en cache doivent respecter les révocations et expirations. En cas de panne, ne rien afficher plutôt qu’une campagne non autorisée.
8. Les médias sont servis de manière compatible avec la disponibilité attendue, la sauvegarde, la suppression contrôlée et une politique d’archivage ; les images fournies par des tiers ne constituent pas des fichiers de code applicatif.

**Limites UI :** la page de contact commercial est publique ; les étapes OTP, connexion, paiement, traitement d’erreur sensible et confirmation financière peuvent être configurées **sans annonces**, par défaut recommandé. Les emplacements concernés sont à valider page par page par l’équipe produit.

### 19.3. Administration limitée au paramétrage technique

Un espace **interne habilité** peut charger une création fournie par l’annonceur, saisir les paramètres, demander l’approbation, programmer, suspendre et vérifier l’état de diffusion. Le personnel concerné appartient à **AfriDIGID**, pas à un compte annonceur ayant des privilèges AfriPay. La matrice d’habilitation et la séparation validation/publication restent à qualifier. Les événements sensibles sont auditables. Le module ne contient **ni comptabilité, ni contrat publicitaire, ni prix de campagne, ni enchères**.

## 20. Critères d’acceptation nouveaux — publicité / modèle économique

| ID | Exigence et résultat attendu | Type de preuve futur |
|---|---|---|
| **AC-ADS-01** | Les deux emplacements `ADS-SIDEBAR` et `ADS-FOOTER` s’affichent sur les pages autorisées, avec rendu responsive | Tests desktop/mobile sur gabarits approuvés |
| **AC-ADS-02** | Deux campagnes ou davantage tournent automatiquement, séparément sur chaque emplacement, sans rechargement complet | Test UI automatisé avec horloge contrôlée |
| **AC-ADS-03** | Ajout, activation, suspension et remplacement sans changement du code Python ni redéploiement | Test configuration en environnement isolé |
| **AC-ADS-04** | Une campagne expirée, non approuvée, suspendue ou révoquée n’est plus diffusée dans un délai défini | Tests limites temporelles, cache et révocation |
| **AC-ADS-05** | Aucun tiers ne peut injecter script/HTML/code non approuvé, lien malveillant ou média non conforme | Tests formats, liens, CSP, stockage, charge |
| **AC-ADS-06** | Un visiteur peut interrompre le changement automatique ; l’interface reste accessible clavier, lecteur d’écran et mobile | Tests WCAG adaptés, non-régression UI |
| **AC-ADS-07** | Aucune publicité ne masque une action OTP, paiement, identification ou confirmation de commande | Scénarios d’accès et capture visuelle qualifiée |
| **AC-ADS-08** | Un annonceur n’accède ni aux commandes privées ni aux coordonnées personnelles des clients | Tests négatifs authentification/autorisation/API |
| **AC-ADS-09** | Seul le personnel AfriDIGID habilité change la configuration et l’audit constate les actions | Tests de permissions, traçabilité et révocation |
| **AC-ADS-10** | Sans campagne éligible ou si le service de publicité est indisponible, l’application métier continue sans échec et sans annonce illégitime | Tests de panne et repli contrôlé |
| **AC-ADS-11** | La page « Faire de la publicité sur AfriPay » renvoie vers un canal AfriDIGID autorisé, sans collecter de données de paiement | Tests de navigation et de confidentialité |
| **AC-ADS-12** | Aucun flux comptable publicitaire n’est injecté dans le traitement des commandes AfriPay | Inspection frontières du code et tests négatifs |

**Ces critères sont proposés, non testés**. Ils complètent — sans effacer — les **55 exigences et dix AC historiques**, les **12 objections E1–E12** et les **15 scénarios T01–T15** de la V0.3.

## 21. Décisions et arbitrages — table de gouvernance

| Identifiant | Statut actuel | Objet | Condition restante |
|---|---|---|---|
| `AFR-BIZ-DEC-01` | **Validé dans la conversation** | Historique 10 % → commission de référence 20 % | Barème et exceptions FREE/PREMIUM/PREMIUM_PLUS, éventuels minima et tarification territoriale |
| `AFR-BIZ-DEC-02` | **Validé dans la conversation** | AfriPay V1 facilite les achats internationaux ; PSP séparé et futur | Rôle contractuel et circuit exact des fonds, pays, prestataires, autorisations |
| `AFR-UI-ADS-01` | **Validé dans la conversation** | Deux emplacements vertical/horizontal, responsive | Guide format et pages autorisées |
| `AFR-UI-ADS-02` | **Validé dans la conversation** | Rotation indépendante et multi-annonceurs, sans redéploiement | Durée, algorithme, poids, cache, mesure et accessibilité |
| `AFR-UI-ADS-03` | **Validé dans la conversation** | AfriPay support de diffusion ; création/gestion commerciale/recettes hors application | Habilitations du service interne et interfaces limitées |
| `AFR-UI-ADS-04` | **Validé dans la conversation** | Point de contact annonceurs vers AfriDIGID, sans consultation des commandes privées | Adresse/canal de contact à confirmer |
| `AFR-ARCH-DIR-01` | **Validé en principe** | Monolithe Python modulaire, FastAPI/Starlette, HTML, PostgreSQL ; Streamlit retiré après qualification | Contrats HTTP, sécurité, migration avec parité et tests |
| `AFR-IDENT-DEC-01..06`, `AFR-SEC-DEC-07`, `AFR-MET-DEC-08` | **Décisions historiques approuvées** | Continuité identité, OTP/session, administration, permissions | Contrats et preuves techniques des gates G0–G5 |

**Les écarts de source ne sont pas des « dettes acceptées ».** Ils doivent être qualifiés, tranchés et testés avant d’implémenter un nouveau comportement. Aucun compromis sur les frontières d’autorisation et l’intégrité financière n’est autorisé.

## 22. Sources vérifiées et références utiles sans fouilles

- **Dépôt historique AfriPay GitHub :** <https://github.com/WillyPython/afripay> ; branche `main`, dernier `HEAD` consulté au 11/11/2026 : `a4a6c47e67474a5473a513e4d509143f6b4b4e40`. L’état GitHub et les fichiers Windows locaux peuvent diverger ; le présent dossier enregistre les sources consultées **à la date indiquée**, pas une synchronisation automatique.
- **README historique :** <https://github.com/WillyPython/afripay/blob/main/README.md> ; commit de documentation du 03/03/2026 `ccdd6f874579bc9a3a851c6b5531362aae4b882e`, fichier blob Git `ec5cfd4497929e7975043b165509da87ed70f106` ; décrit 10 % minimum 10 €, paiement Mobile Money, marchand international et logistique client.
- **Code frais par plan :** <https://github.com/WillyPython/afripay/blob/main/services/order_service.py> ; au 11/11/2026, `_compute_afripay_fee_xaf_for_plan` et `_build_locked_order_amounts` ; montant marchand + frais vendeur + frais AfriPay, et différenciation des plans.
- **Configuration commerciale historique :** <https://github.com/WillyPython/afripay/blob/main/services/settings_service.py> ; valeur par défaut `service_fee_percent = "20"` ; ne pas confondre avec la grille contractuelle applicable.
- **Référentiel AfriPay local :** `docs/engineering/AFRIPAY/REFERENTIEL.md` — SHA-256 `3E4F2B0E52D69D3ADDDC133E5D326A1ADD7FF6DDB5C8170CB80138D93112561E`.
- **CDC V0.1 local :** `docs/engineering/AFRIPAY/CAHIERS-DES-CHARGES/AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.1_DRAFT_2026-11-11.md` — SHA-256 `1C8D28CA85B40E4E58EAE2D26C4253E6FBFBF56917FB55BF7033C9130B0BAD85`.
- **RESUME-ANCHOR initial :** `docs/engineering/AFRIPAY/RESUME-ANCHORS/AFRIPAY_RESUME-ANCHOR_2026-11-11_AMSTERDAM.md` — SHA-256 `1B8D642D73D235E0589DB1CA3EC0997DB7F5EE00A116BAAAF2097633F1FC5AB5`.
- **CDC V0.2 téléchargé :** `AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.2_CONSOLIDATION_DRAFT_2026-11-11.md` — SHA-256 `C947982DF3D195F97DA2FDA2016930396DF6696E569BA81A7F952EA6937BC61C`.
- **CDC V0.3 vérifié dans Downloads :** `AFRIPAY_CDC_SECURITE_IDENTITE_UI_V0.3_ARCHITECTURE_MIGRATION_DRAFT_2026-11-11.md` — SHA-256 `7265ADBEF42E5D6B12B7473936D189A8C85043455A0867D47171F172A090EE4E` ; 43 910 octets.
- **CODEX-AFRIPAY-01 :** rapport final du 11/11/2026, expertise READ-ONLY avec V0.2 effectivement lue ; E1–E12 et T01–T15, **aucun test exécuté**. À conserver séparément ; sa matrice est déjà reprise dans les sections 12.1–12.2.
- **ADL-Foundation transversal ORYSK/AfriDIGID :** document de gouvernance conceptuelle mentionnant les produits ; **il ne suffit pas à définir le modèle économique précis d’AfriPay**. Les décisions métier ci-dessus viennent de leurs sources propres et de leurs validations humaines.
- **Marchés :** README de mars 2026 décrit un pilote Cameroun ; une stratégie commerciale ultérieure a examiné d’autres ordres de marché, dont Sénégal et Kenya. **Aucun territoire de production n’est ouvert par ce CDC**.

## 23. Point de reprise et livrables V0.4

1. **LIRE D’ABORD :** `docs/engineering/AFRIPAY/RESUME-ANCHORS/AFRIPAY_RESUME-ANCHOR_2026-11-11_AMSTERDAM_POST_CDC_V0.4.md` ; contient un résumé autonome et les points ouverts, pour éviter de reprendre les fouilles README/GitHub de zéro.
2. **PRENDRE CE CDC V0.4 comme base de revue documentaire :** toutes les 55 exigences historiques demeurent, complétées par `AFR-BIZ-DEC-01/02`, `AFR-UI-ADS-01..04` et `AC-ADS-01..12` ; la V0.3 reste inchangée, source de traçabilité.
3. **CONSOLIDER G0 (sans toucher au code) :** contrat d’achat/revente ou mandat, prix et flux marchand, fonds des comptes marchands, pays/prestataires, remboursements, règles commerciales détaillées par plan et conditions juridiques effectives ; puis guide annonceur et matrice de pages/emplacements.
4. **APRÈS approbation documentaire et autorisation bornée :** mission Codex-AFRIPAY consolidée sur architecture FastAPI, transactions, identité et diffusion publicitaire ; aucune implémentation ou certification supposée par la création de ce document.
5. **AUTORISATIONS :** la présente étape autorise l’**enregistrement local documentaire contrôlé** des deux **nouveaux** fichiers dans le dépôt AfriPay ; elle **n’autorise aucun Git add/commit/push, aucune écriture ou lecture de base réelle, aucun Render, DNS, secrets, achats, déploiement ni intervention dans ORYSK**.
6. **SUIVI DISTINCT :** documentation = préparée/rédigée, validée par le responsable humain pour les **orientations précises**, CDC complet DRAFT ; logiciel = code cible non implémenté/testé/certifié. Les tests `T01–T15` et `AC-ADS` sont des **scénarios futurs**.

**Fin du CDC V0.4 — DRAFT — non certifié.**
