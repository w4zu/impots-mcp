# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)

---

## [3.0.0] (2026-08-31)

Version majeure : le taux des prélèvements sociaux sur le capital, utilisé par une trentaine
d'outils, a changé au 1er janvier 2026 et deux dispositifs entièrement absents du serveur sont
intégrés.

### Corrigé : prélèvements sociaux sur les revenus du capital

**CSG portée de 9,2% à 10,6% par la LFSS 2026** (loi n° 2025-1403 du 30 décembre 2025)

Le serveur appliquait 17,2% et un PFU de 30% partout. Le taux global des prélèvements sociaux
sur le capital est de **18,6%** et le PFU de **31,4%**. Les revenus limitativement énumérés au
nouvel article L. 136-8, IV du code de la sécurité sociale restent à 17,2%.

| Revenu | Taux | Entrée en vigueur |
|--------|------|-------------------|
| Dividendes, intérêts, livrets fiscalisés | 18,6% | produits versés depuis le 01/01/2026 |
| Plus-values mobilières, crypto-actifs | 18,6% | revenus perçus depuis 2025 |
| PEA, épargne salariale, gains de PER | 18,6% | 01/01/2026 |
| Location meublée non professionnelle | 18,6% | résultats à compter du 31/12/2025 |
| Revenus fonciers, plus-values immobilières | 17,2% | maintenu |
| Assurance-vie et capitalisation | 17,2% | maintenu |
| Épargne logement (PEL, CEL) et PEP | 17,2% | maintenu |

Impacts mesurés : PFU sur 10 000€ de dividendes 3 000€ vers **3 140€** ; exit tax sur 1,2 M€ de
plus-values latentes 360 000€ vers **376 800€** ; LMNP au micro-BIC sur 12 000€ de loyers
2 916€ de taxes au lieu de 2 832€ ; taux majoré BSPCE 47,2% vers **48,6%**.

Les taux sont désormais des constantes de module (`PS_CAPITAL`, `PS_IMMOBILIER`,
`PS_ASSURANCE_VIE`, `PS_EPARGNE_LOGEMENT`, `PS_PENSION`, `PFU_IR`, `PFU_CAPITAL`,
`CSG_DEDUCTIBLE`), appliquées régime par régime. Environ 155 emplacements écrivaient un taux en
dur, y compris dans les descriptions d'outils : plus aucun n'existe.

**Rentes viagères**

- Une rente issue de versements PER **déduits** est une rente à titre gratuit : barème de l'IR
  après abattement de 10% et prélèvements sociaux de **9,1%** (CSG 8,3%, CRDS 0,5%, Casa 0,3%).
  Le serveur appliquait 17,2% sur la rente entière
- Une rente issue de versements **non déduits** est une rente à titre onéreux : 18,6% sur la
  seule fraction imposable déterminée par l'âge

### Ajouté : CDHR, contribution différentielle sur les hauts revenus

Nouvel outil `calculer_cdhr` (art. 224 CGI, créé par la LF 2025 et pérennisé par la LF 2026
jusqu'au retour du déficit public sous 3% du PIB). Le dispositif s'applique aux revenus 2025,
déclarés au printemps 2026, et était totalement absent du serveur.

- Imposition minimale de 20% du revenu fiscal de référence retraité au-delà de 250 000€
  (500 000€ en imposition commune)
- Décote d'entrée : l'imposition cible retenue est le minimum entre 20% du RFR et
  82,5% de la fraction excédant le seuil, ce qui lisse l'effet de seuil jusqu'à 330 000€
  (660 000€ en couple)
- Majorations forfaitaires de 12 500€ pour un couple et de 1 500€ par personne à charge
- Impôts pris en compte : IR au barème, PFU, prélèvements libératoires et CEHR. Les
  prélèvements sociaux n'entrent pas dans le calcul
- Acompte de 95% à verser du 1er au 15 décembre, ajouté au calendrier fiscal
- `calculer_impot_revenu` signale désormais la contribution dès que le revenu franchit le seuil

### Ajouté : facturation électronique obligatoire au 1er septembre 2026

Nouvel outil `guide_facturation_electronique` (art. 289 bis CGI, calendrier de la LF 2024
art. 91, sanctions relevées par la LF 2026).

- Réception obligatoire pour toutes les entreprises assujetties à la TVA au 1er septembre 2026,
  franchise en base comprise
- Émission obligatoire au 1er septembre 2026 pour les grandes entreprises et les ETI, au
  1er septembre 2027 pour les PME, TPE et micro-entreprises
- Le portail public de facturation ne joue plus le rôle de plateforme gratuite : il faut passer
  par une plateforme agréée immatriculée par la DGFiP
- Formats Factur-X, UBL et CII, quatre nouvelles mentions obligatoires, périmètre B2B contre
  e-reporting pour le B2C et l'international
- Sanctions : 50€ par facture non conforme et 500€ par transmission d'e-reporting manquante,
  dans la limite de 15 000€ par an, 500€ en cas d'absence de plateforme après mise en demeure
- Le sujet est également rappelé par `calculer_tva`, `guide_auto_entrepreneur` et
  `diagnostiquer_passage_freelance`

### Corrigé : grille des taux par défaut du prélèvement à la source

La grille intégrée datait d'environ quatre ans (première tranche à 1 456€, taux maximal de 38%).
Les trois grilles officielles en vigueur au 1er mai 2026 sont reprises intégralement depuis
BOI-BAREME-000037 : métropole, Guadeloupe / Martinique / Réunion, Guyane / Mayotte. Vingt
tranches chacune, de 0% sous 1 635€ à 43% au-delà de 55 558€ en métropole.

- Nouveau paramètre `zone` sur `calculer_prelevement_source`
- Abattement pour les contrats courts : 748€ par mois
- Le taux individualisé est appliqué **par défaut** aux couples mariés ou pacsés depuis le
  1er septembre 2025 : le serveur le présentait encore comme une option à demander
- Calendrier corrigé : nouveau taux au 1er septembre, actualisation de la grille au 1er mai

### Corrigé : données indexées restées à des millésimes antérieurs

| Paramètre | Avant | Revenus 2025 |
|-----------|-------|--------------|
| Abattement de 10% sur les pensions | 422€ / 4 321€ | **454€ / 4 439€** (plafond par foyer) |
| Abattement personnes âgées ou invalides | 2 620€ / 1 310€, seuils 16 750€ et 26 970€ | **2 822€ / 1 411€**, seuils 17 677€ et 28 430€ |
| Pension alimentaire à un enfant majeur | 6 368€ | **6 855€**, 13 710€ si l'enfant est marié |

Deux valeurs différentes de l'abattement des personnes âgées coexistaient dans deux outils.
Les trois paramètres sont désormais des constantes uniques.

### Corrigé : plafond du PER

`PLAFOND_PER_MAX` valait 37 094€, soit le plafond d'un versement effectué en 2025. Un versement
réalisé en 2026 relève du PASS 2025, donc de **37 680€** (plancher 4 710€). Les deux millésimes
sont désormais distingués (`PLAFOND_PER_MAX_VERSEMENTS_2025` et `_2026`) et l'outil affiche le
plafond du versement en cours ainsi que celui de l'année précédente.

### Corrigé : surcote de retraite jamais appliquée

Le calcul de la pension de base plafonnait le taux à 50% du salaire annuel moyen **après** avoir
appliqué la surcote, ce qui l'annulait systématiquement : un départ à 67 ans donnait la même
pension qu'à 64 ans. Le plafond de 50% ne s'applique plus qu'au taux avant surcote, et la
surcote exige désormais d'avoir atteint l'âge légal. Sur un cas à 50 000€ de brut, la pension
d'un départ à 67 ans passe de 2 316€ à **2 779€** bruts par mois.

### Corrigé : régime des échanges entre crypto-actifs

L'outil affirmait que l'échange crypto contre crypto est imposable depuis 2019 « sauf dans un
même wallet », suivi d'une ligne de brouillon restée dans le code. C'est l'inverse : l'échange
entre actifs numériques est une opération intercalaire non imposable (art. 150 VH bis CGI),
y compris entre deux plateformes. Seules la cession contre monnaie ayant cours légal, l'achat
d'un bien ou d'un service et l'échange avec soulte constituent un fait générateur.

### Ajouté : suspension de la réforme des retraites

La LFSS 2026 gèle le relèvement de l'âge légal et de la durée d'assurance pour les pensions
prenant effet du 1er septembre 2026 au 1er janvier 2028. `simuler_depart_retraite` affiche le
tableau des générations 1964 à 1968 et signale la ligne correspondant à l'utilisateur.

### Ajouté : durée d'indemnisation après rupture conventionnelle

Pour les fins de contrat intervenant à compter du 1er septembre 2026, la durée maximale
d'indemnisation passe de 18 à **15 mois** avant 55 ans et de 22,5 à **20,5 mois** à partir de
55 ans (avenant n° 2 à la convention du 15 novembre 2024, agréé le 19 juin 2026). Intégré à
`calculer_revenus_remplacement` et au diagnostic de passage en freelance, où trois mois de
matelas en moins changent le calibrage de l'épargne de précaution.

### Ajouté : révocabilité de l'option pour le barème

La LF 2026 supprime le caractère irrévocable de l'option de la case 2OP pour les revenus 2026
et suivants : le contribuable peut y renoncer a posteriori dans le délai de réclamation.
L'option reste irrévocable pour les revenus 2025. Précisé dans
`comparer_pfu_bareme_capital`, dont le tableau des seuils de bascule est maintenant calculé
plutôt que recopié (une valeur y était fausse de deux points).

### Modifié : calendrier fiscal 2026

- Ajout du 1er septembre (taux du prélèvement à la source, facturation électronique,
  suspension de la réforme des retraites)
- Ajout du 25 septembre : prélèvement automatique du solde, étalé en quatre échéances du
  25 septembre au 28 décembre au-delà de 300€
- Correction du 15 septembre, qui est la date limite d'un paiement non dématérialisé
  (20 septembre en ligne) et non une date de prélèvement
- Ajout de l'acompte de CDHR du 1er au 15 décembre et de l'échéance du 1er septembre 2027

### Modifié : rendu des sorties

Toutes les icônes UTF-8 des sorties sont supprimées (environ 190 occurrences), conformément au
parti pris du projet. Les catégories MaPrimeRénov' portent à nouveau leur nom (Bleu, Jaune,
Violet, Rose) au lieu d'une puce colorée, et les cellules de tableau où une coche portait le
sens sont explicitées. Les annotations de développement restées dans le code (« Bug B », « Bug
C », « Bug D ») sont remplacées par les références légales correspondantes.

### Vérifié

Les données 2026 du serveur ont été contrôlées auprès des sources officielles et sont exactes :
barème indexé de 0,9% (loi n° 2026-103, BOFiP ACTU-2026-00022), décote, plafonds du quotient
familial, abattement de 10% pour frais professionnels, PASS 2026 à 48 060€, SMIC à 12,31€ depuis
le 1er juin 2026, Livret A et LDDS à 1,7% et LEP à 2,5% depuis le 1er août 2026, seuils
micro-entreprise 2026-2028, seuils de franchise de TVA. L'IFI est maintenu dans son périmètre
immobilier : le projet d'impôt sur la fortune improductive n'a pas été retenu par la LF 2026.

Les 64 outils ont été exercés sur 533 combinaisons de paramètres (chaque valeur d'énumération
de chaque outil) sans erreur ni sortie vide.

---

## [2.9.0] (2026-08-31)

### Corrigé : Calcul de l'impôt sur le revenu

**Plafonnement du quotient familial** (art. 197-2 CGI), jamais appliqué jusqu'ici
- La constante `PLAFOND_DEMI_PART` n'était utilisée que dans du texte affiché : `calculer_ir()`
  ne plafonnait pas l'avantage tiré des personnes à charge
- Impact mesuré : couple avec 2 enfants à 100 000€ de RNI, impôt de 9 312€ → **12 594€** ;
  à 300 000€, 74 402€ → **86 987€**
- Ajout du plafond spécifique parent isolé « case T » : **4 262€**
- Le plafond est désormais calculé par composition du foyer (`_plafond_quotient_familial`),
  et non par simple comptage de demi-parts

**Décote**, critère corrigé
- Le choix entre décote « personne seule » et « couple » se faisait sur le nombre de parts :
  un parent isolé avec un enfant (2 parts) recevait la décote couple
- Le critère est désormais la situation du foyer (`seul` / `couple` / `parent_isole`)

**Nombre de parts** (`calculer_parts`)
- Un veuf avec enfant à charge conserve le quotient conjugal (2 parts de base, art. 194 CGI)
- La majoration « case T » en garde alternée est due **par enfant** pour les deux premiers,
  et non une seule fois

**Erreurs d'exécution**
- Quatre `ZeroDivisionError` corrigées : `calculer_pv_immobiliere` sur moins-value,
  `simuler_scpi` et `comparer_pfu_bareme_capital` sur montant nul,
  `checker_eligibilite_aides` sur zéro part
- `calculer_pv_immobiliere` : le net perçu était calculé avant l'ajout de la taxe sur les
  hautes plus-values, rendant le tableau incohérent avec son propre total
- Le plancher du plafond PER n'était appliqué que sur deux des six sites de calcul
- `_valider_revenu` rejette désormais les booléens

**Modélisation**
- LMNP : l'amortissement est plafonné au bénéfice avant amortissement (art. 39 C II CGI),
  l'excédent est reporté sans limite de durée. Il ne peut plus créer de déficit
- SCPI : les prélèvements sociaux sont calculés sur la base après abattement micro-foncier ;
  la colonne « réel » recalculait en réalité la base micro et a été retirée

### Mis à jour : Données fiscales août 2026

**Impôt sur le revenu** (revenus 2025)
- Décote : 889€ / 1 470€ → **897€ / 1 483€**, seuils 1 982€ / 3 277€
- Abattement 10% frais professionnels : 495€ / 14 426€ → **509€ / 14 555€**
  (le plancher accusait deux ans de retard)
- Plafond quotient familial parent isolé : **4 262€** (absent du code)

**Épargne réglementée** (Banque de France, depuis le 1er août 2026)
- Livret A : 1,5% → **1,7%**
- LDDS : 1,5% → **1,7%**
- LEP : maintenu à 2,5%
- Plafonds LEP calculés par quart de part, conformes aux 19 valeurs officielles

**Cotisations et seuils sociaux**
- PASS 2026 : **48 060€** (2025 : 47 100€, 2024 : 46 368€)
- SMIC : **12,31€/h** soit 22 404€/an depuis le 1er juin 2026 (auparavant 21 622€)
- Auto-entrepreneur : vente 12,8% → **12,3%**, services BIC 21,4% → **21,2%**,
  BNC 23,1% → **25,6%**
- Ajout de la catégorie **Cipav 23,2%** pour les professions libérales réglementées
- Seuils micro-entreprise 2026-2028 : **83 600€ / 203 100€**, les seuils revenus 2025
  (77 700€ / 188 700€) restant disponibles pour la déclaration
- Seuils de franchise TVA maintenus à 37 500€ / 85 000€ (réforme à 25 000€ abandonnée)

**Barème kilométrique**, périmé d'environ cinq ans
- Valeurs officielles rétablies (5 CV : 0,548 → **0,636** sur la première tranche)
- La part forfaitaire des tranches médianes est reprise du texte au lieu d'être reconstruite
  (5 CV : 1 395€ au lieu de 1 110€)
- Ajout de la **majoration de 20% pour véhicules électriques**
- Les motos de plus de 5 CV étaient inatteignables, elles sont désormais distinguées
- Ajout du barème **cyclomoteurs** (< 50 cm³), auparavant traités comme des motos

**MaPrimeRénov'**, dispositif refondu au 1er janvier 2026
- Les plafonds de ressources sont indexés sur le **nombre de personnes du ménage**,
  et non sur le nombre de parts fiscales
- Ajout des barèmes **Île-de-France**, absents jusqu'ici (1 personne : 24 031€ contre
  17 363€ hors Île-de-France pour les très modestes)
- Les aides sont des **forfaits en euros** et non des pourcentages : PAC air/eau
  5 000 / 4 000 / 3 000€, PAC géothermique 11 000 / 9 000 / 6 000€, isolation de toiture
  25 / 20 / 15€/m², parois vitrées 100 / 80 / 40€/équipement
- Les ménages aux **revenus supérieurs ne sont plus éligibles** au parcours par geste
- Chaudière bois, isolation des murs et isolation du plancher bas sont sorties du parcours
  par geste ; le bonus sortie de passoire de 1 500€ n'existe plus
- Ajout de la **rénovation d'ampleur** : taux 80 / 60 / 45 / 10%, plafonds 30 000€ et
  40 000€ HT, écrêtement, prise en charge de Mon Accompagnateur Rénov'
- Depuis le 1er septembre 2026, l'aide est refusée si un chauffage au gaz est conservé

**Immobilier locatif**
- LMNP : les amortissements déduits sont **réintégrés au calcul de la plus-value** de revente
  (LF 2025, art. 150 VB II CGI). Le code affirmait exactement l'inverse
- `calculer_pv_immobiliere` accepte `type_bien = lmnp`, `amortissements_deduits` et
  `residence_services` (exclusion pour les résidences étudiantes, seniors et EHPAD)
- Meublés de tourisme : classés 71% / 188 700€ → **50% / 77 700€**, ajout des
  **non classés 30% / 15 000€**
- Déficit foncier : le rehaussement à 21 400€ pour travaux énergétiques est éteint depuis
  le 31 décembre 2025, la note le présentait encore comme une option

### Modifié : Structure du code

- Toutes les valeurs fiscales sont centralisées en constantes de module. Aucune n'est plus
  écrite en dur dans le corps des outils : l'abattement de 10% était recopié dans dix endroits,
  le SMIC dans trois, et deux valeurs différentes du PASS coexistaient sous le même nom
- `PLAFOND_PER_MAX_2025` était affecté deux fois de suite, la première valeur étant morte
- Nouvelles fonctions partagées : `abattement_frais_pro`, `frais_kilometriques`, `plafond_lep`,
  `mpr_plafonds`, `mpr_aide_geste`, `pct_fr`
- `calculer_parts` renvoie un objet `Parts` porteur des parts de base, du type de foyer et du
  plafond de quotient familial, ce qui propage le plafonnement à tous les points d'appel
- Sept schémas d'outils étaient désynchronisés du code : paramètres déclarés jamais lus
  (`case_7WF`, `a_fait_travaux_recents`, `investissement_pme_envisage`, `valeur_terrain`,
  `annees_blocage_restantes`, `situation_famille` et `nb_enfants` pour la crypto) ou lus sans
  être déclarés (`annee_construction`, `invalide_contribuable`)
- `calculer_fiscalite_crypto` accepte un revenu net imposable et calcule le TMI réel
- `verifier_actualite_fiscale` lit les constantes au lieu de les recopier en littéraux
- Les libellés d'année sont dérivés de `ANNEE_DECLARATION`
- Accents rétablis dans les outils 2.6.0 à 2.8.0

---

## [2.8.0] (2026-04-12)

### Mis à jour : Données fiscales avril 2026

**Barème IR 2026 corrigé** (Loi n° 2026-103 du 19 février 2026, art. 4, indexation +0,9%)
- Tranches IR 2026 : 0% → 11 600€ / 11% → 29 579€ / 30% → 84 577€ / 41% → 181 917€ / 45% au-delà
  (correction : l'ancien code utilisait +1,8% par erreur)
- Plafond demi-part quotient familial : 1 791€ → **1 807€**

**Taux livrets réglementés** (Banque de France, en vigueur depuis le 1er février 2026)
- Livret A : 2,4% → **1,5%**
- LDDS : 2,4% → **1,5%**
- LEP : 3,5% → **2,5%**

**Seuils LEP 2026** (source : service-public.fr)
- Plafond RFR 1 part : 22 419€ → **23 028€**
- Plafond RFR 2 parts : 34 393€ → **35 326€**
- Plafond RFR 3 parts : 41 289€ → **47 624€**
- Plafond RFR 4 parts : 48 189€ → **59 922€** (extrapolé)

**Calendrier fiscal 2026**, dates officielles confirmées (impots.gouv.fr)
- Ouverture déclaration en ligne : 9 avril 2026
- Date limite papier : 19 mai 2026
- Zone 1 (dép. 01-19 + non-résidents) : 21 mai 2026
- Zone 2 (dép. 20-54) : 28 mai 2026
- Zone 3 (dép. 55-974 et 976) : 4 juin 2026

---

## [2.5.0] (2026-03-10)

### Ajouté : 13 nouveaux outils (52 au total)
- **Outil `simuler_assurance_vie`** : fiscalité rachats partiels/totaux (PFU 12.8% ou 7.5% après 8 ans, abattements 4 600€/9 200€), transmission au décès (abattement 152 500€/bénéficiaire, primes après 70 ans régime spécial), option barème IR
- **Outil `simuler_demembrement`** : barème officiel art. 669 CGI (usufruitier 21% à 23% selon âge), calcul valeur nue-propriété et usufruit, usufruit temporaire, donation démembrée, stratégies d'optimisation
- **Outil `simuler_cession_entreprise`** : plus-value sur titres (PFU 30%), abattement renforcé PME créées avant 2018 (85% si >8 ans), abattement départ retraite 500 000€, régime apport-cession (art. 150-0 B ter CGI), comparatif scénarios
- **Outil `simuler_holding`** : régime mère-fille (IS sur 5% des dividendes), intégration fiscale (à partir de 95% détention), comparatif détention directe vs via holding, optimisation reinvestissement
- **Outil `calculer_tva`** : franchise en base (37 500€ services / 85 000€ ventes), régimes réel simplifié et normal, taux TVA par catégorie (20%/10%/5.5%/2.1%), TVA intracommunautaire
- **Outil `guide_auto_entrepreneur`** : seuils 2025 (77 700€ services BIC / 188 700€ ventes / 77 700€ BNC), cotisations par activité, versement libératoire de l'impôt (VFL), ACRE (1ère année), prorata 1ère année d'activité
- **Outil `calculer_cfe`** : cotisation minimum par tranche de CA (depuis 227€ à 2 336€), bases et taux indicatifs, exonérations (1ère année, JEI, ZFU, ZRR, activité de moins de 5 000€ de recettes)
- **Outil `simuler_investissement_pea`** : fiscalité PEA après 5 ans (PS 17.2% seulement, IR 0%), plafond 150 000€, PEA-PME 225 000€, retrait avant 5 ans (PFU 30%), clôture, transmission
- **Outil `guide_defiscalisation_solidaire`** : dons associations loi 1901 (66% dans limite 20% RNI, cumulable), dons urgence 75% (plafond 1 000€), investissement PME 25%, FIP/FCPI 18%, SOFICA 30%/36%, calcul gain fiscal personnalisé
- **Outil `calculer_pv_immobiliere`** : frais acquisition 7.5% forfait, travaux 15% forfait après 5 ans, abattements IR (22%→100% entre 6 et 22 ans) et PS (8.25%→100% entre 6 et 30 ans), taxe haute plus-value (2% à 6%), exonération résidence principale
- **Outil `guide_taxe_fonciere`** : calcul valeur locative × 50% × taux, plafonnement à 50% du RNI, exonérations (>75 ans sous conditions, logement neuf 2 ans, travaux économies d'énergie), réclamation
- **Outil `simuler_reversion_pension`** : pension de réversion régime général (54%) et AGIRC-ARRCO (60%), condition d'âge (55 ans), écrêtement selon ressources propres (plafond 24 232€/an), cumul emploi-reversion
- **Outil `guide_revision_declaration`** : délais de réclamation (31 déc. N+2), correction en ligne jusqu'au 30 nov., majorations 10%/40%/80% selon faute, prescription 3 ans, cas des rectifications spontanées et amendements amiables

---

## [2.4.0] (2026-03-10)

### Ajouté : 3 nouveaux outils (39 au total)
- **Outil `simuler_depart_retraite`** : pension régime général + AGIRC-ARRCO estimée, comparatif départ 62/64/67 ans, décote/surcote (1.25%/trimestre), cumul emploi-retraite (libéralisé 2023), abattement 10% fiscal sur pensions, spécificités fonctionnaires et indépendants
- **Outil `guide_fiscalite_agricole`** : forfait collectif, RSA, réel normal, seuils 2025 (85 800€ / 391 000€), DEP (27% du bénéfice, max 41 620€), étalement revenus exceptionnels, exonérations jeune agriculteur (abattement 75% pendant 5 ans, DJA non imposable), TVA agricole, cotisations MSA
- **Outil `guide_fiscalite_outremer`** : abattements DOM IR (30% plafond 5 100€ pour Guadeloupe/Martinique/Réunion ; 40%/6 700€ pour Guyane/Mayotte), fiscalité propre Polynésie/Nouvelle-Calédonie/Saint-Barthélemy, Girardin industriel (>100% de réduction), Pinel OM (23%/29%/32%), LODEOM

---

## [2.3.0] (2026-03-10)

### Ajouté : 9 nouveaux outils (36 au total)
- **Outil `guide_evenements_vie`** : impact fiscal des événements majeurs (mariage, divorce, naissance, garde alternée, enfant majeur rattaché, décès du conjoint), déclarations à effectuer
- **Outil `calculer_revenus_remplacement`** : fiscalité chômage (ARE), retraite/pension (abattement 10%), rentes viagères à titre onéreux (RVTO, fractions par âge), indemnité de licenciement (seuils d'exonération), invalidité
- **Outil `simuler_sortie_per`** : simulation complète sortie PER, rente vs capital, déblocage anticipé résidence principale, déblocage exceptionnel (invalidité, décès conjoint…), versements déduits vs non déduits
- **Outil `optimiser_epargne_salariale`** : intéressement, participation, PEE, PERCO/PERCOL, AGA (abattement 50% plan conforme), BSPCE (PFU 30% / taux majoré 47.2%), abondement employeur plafonds PASS
- **Outil `calculer_impot_societes`** : IS 15% jusqu'à 42 500€ / 25% au-delà, éligibilité taux réduit PME (CA < 10M€, capital PP ≥ 75%), acomptes trimestriels, déficit reportable en avant/arrière
- **Outil `optimiser_remuneration_dirigeant`** : comparatif 3 scénarios (tout rémunération / mixte / tout dividendes) pour SASU, EURL IS, SARL IS, IS + charges sociales + IR + PFU 30%
- **Outil `calculer_fiscalite_crypto`** : refonte complète, méthode PAMC officielle (formulaire 2086), seuil 305€, moins-values reportables 10 ans, option barème vs PFU 30%, staking/mining/NFT (BNC/BIC), airdrops
- **Outil `simuler_pacte_dutreil`** : exonération 75% droits donation/succession entreprise (art. 787 B CGI), conditions ECC (2 ans) + EIC (4 ans) + direction, calcul comparatif avec/sans pacte
- **Outil `simuler_sci`** : comparatif SCI IR vs IS, revenus locatifs nets, amortissement IS, déficit foncier IR, fiscalité à la sortie (VNC, piège des amortissements IS), recommandation selon TMI et horizon

### Corrigé
- **Bug `calculer_parts()`** : garde alternée désormais correctement comptée à +0.25 part par enfant (au lieu de +0.5), nouveau paramètre `nb_enfants_garde_alternee`
- **Micro-BIC meublés de tourisme** : taux mis à jour suite LF2024, non classés 30% seuil 15 000€/an (au lieu de 50%), classés 71% seuil 188 700€ inchangé

### Modifié
- `calculer_impot_revenu` : nouveau paramètre `nb_enfants_garde_alternee` exposé dans le schéma

---

## [2.2.0] (2026-03-10)

### Ajouté
- **Outil `guide_fiscalite_internationale`** : guide complet résidence fiscale, formulaire 2047, conventions par pays (13 pays), Alsace-Moselle, non-résidents
- **Outil `calculer_revenu_etranger`** : intégration d'un revenu étranger dans le calcul IR (crédit d'impôt ou exemption avec progressivité)
- **Outil `guide_frontaliers`** : guide détaillé Suisse (cantons, accord 1983, télétravail 2023), Luxembourg (crédit d'impôt, télétravail 34j), Belgique, Allemagne
- **Irlande** : convention France-Irlande détaillée (crédit d'impôt, Income Tax, USC, PRSI)
- **Alsace-Moselle** : documentation complète (IR identique, cotisation maladie +1,5%, remboursements 90%)

### Données ajoutées
- `CONVENTIONS_FISCALES` : 13 pays (Irlande, Suisse, Luxembourg, Belgique, Allemagne, UK, USA, Espagne, Italie, Portugal, Canada, Maroc, Tunisie, Algérie + sans convention)
- `ALSACE_MOSELLE` : particularités régionales documentées

---

## [2.1.0] (2026-03-09)

### Ajouté
- **Outil `simuler_droits_donation`** : calcul des droits de donation par lien de parenté, abattements, don d'argent exonéré, stratégies d'optimisation
- **Outil `calculer_succession`** : droits de succession, exonération conjoint/PACS, abattement handicap, stratégies d'anticipation
- **Outil `simuler_scpi`** : fiscalité SCPI en pleine propriété, assurance-vie et nue-propriété, rendement net de fiscalité
- **Paramètre `annee`** sur `calculer_impot_revenu` : choix barème 2025 ou 2026
- **Paramètre `age_contribuable`** : abattement spécial personnes âgées (+65 ans) / invalides
- **CEHR** (Contribution Exceptionnelle sur les Hauts Revenus) calculée et affichée si applicable

### Corrigé
- Décote 2026 mise à jour (seuils estimés +1.8% : 1 964€/3 249€)
- Dispatch refactorisé (if/elif → dict `_TOOL_DISPATCH`)
- Validation des inputs : montants négatifs, NaN, valeurs aberrantes détectés et rejetés proprement

### Données
- Barème CEHR 2026 (3%/4%)
- Barème droits de donation et succession (ligne directe, conjoint, frères/sœurs, tiers)
- Abattements donation/succession par lien de parenté
- Données SCPI (fiscalité, démembrement, assurance-vie)

---

## [2.0.0] (2026-03-09)

### Ajouté
- **Outil `calculer_ifi`** : IFI avec barème officiel, abattement résidence principale 30%, décote, plafonnement 75%, stratégies
- **Outil `optimiser_tns`** : optimisation TNS/indépendants (micro vs réel, Madelin, ACRE, comparatif structures EI/EURL/SASU)
- **Outil `comparer_scenarios`** : tableau comparatif côte à côte de 2 ou 3 scénarios fiscaux
- **Outil `calculer_prelevement_source`** : taux PAS personnalisé, taux neutre, retenue mensuelle, acomptes, guide modulation
- Barème IFI 2026 avec décote et plafonnement
- Données TNS : cotisations micro BIC/BNC, plafonds Madelin

### Mis à jour
- Barème IR 2026 (revenus 2025), indexé +1.8%
- Calendrier fiscal 2026 (dates déclaration revenus 2025)
- Plafond PER 2025 : 37 094€ max / 4 637€ plancher
- `PLAFOND_DEMI_PART` → 1 791€ (2026 estimé)
- Tous les libellés et titres mis à jour vers 2026

### Architecture
- Dispatch `if/elif` remplacé par dict `_TOOL_DISPATCH` (O(1), extensible)
- `calculer_ir()` : paramètre `tranches` optionnel pour choisir le barème
- `__version__` = "2.0.0"

---

## [1.0.0] (2025 (version initiale))

### Ajouté
- 17 outils couvrant l'IR 2025, PER, MaPrimeRénov', plus-values, immobilier
- Barème IR 2025 (revenus 2024) officiel
- Seuils MaPrimeRénov' 2025 par catégorie (Bleu/Jaune/Violet/Rose)
- Plafonds PER 2024, barème kilométrique 2024
- Calendrier fiscal 2025
- Crédits et réductions d'impôt 2025
