# Changelog

Toutes les modifications notables de ce projet sont documentées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)

---

## [2.8.0] — 2026-04-12

### Mis à jour — Données fiscales avril 2026

**Barème IR 2026 corrigé** (Loi n° 2026-103 du 19 février 2026, art. 4 — indexation +0,9%)
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

**Calendrier fiscal 2026** — dates officielles confirmées (impots.gouv.fr)
- Ouverture déclaration en ligne : 9 avril 2026
- Date limite papier : 19 mai 2026
- Zone 1 (dép. 01-19 + non-résidents) : 21 mai 2026
- Zone 2 (dép. 20-54) : 28 mai 2026
- Zone 3 (dép. 55-974 et 976) : 4 juin 2026

---

## [2.5.0] — 2026-03-10

### Ajouté — 13 nouveaux outils (52 au total)
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

## [2.4.0] — 2026-03-10

### Ajouté — 3 nouveaux outils (39 au total)
- **Outil `simuler_depart_retraite`** : pension régime général + AGIRC-ARRCO estimée, comparatif départ 62/64/67 ans, décote/surcote (1.25%/trimestre), cumul emploi-retraite (libéralisé 2023), abattement 10% fiscal sur pensions, spécificités fonctionnaires et indépendants
- **Outil `guide_fiscalite_agricole`** : forfait collectif, RSA, réel normal — seuils 2025 (85 800€ / 391 000€), DEP (27% du bénéfice, max 41 620€), étalement revenus exceptionnels, exonérations jeune agriculteur (abattement 75% pendant 5 ans, DJA non imposable), TVA agricole, cotisations MSA
- **Outil `guide_fiscalite_outremer`** : abattements DOM IR (30% plafond 5 100€ pour Guadeloupe/Martinique/Réunion ; 40%/6 700€ pour Guyane/Mayotte), fiscalité propre Polynésie/Nouvelle-Calédonie/Saint-Barthélemy, Girardin industriel (>100% de réduction), Pinel OM (23%/29%/32%), LODEOM

---

## [2.3.0] — 2026-03-10

### Ajouté — 9 nouveaux outils (36 au total)
- **Outil `guide_evenements_vie`** : impact fiscal des événements majeurs (mariage, divorce, naissance, garde alternée, enfant majeur rattaché, décès du conjoint), déclarations à effectuer
- **Outil `calculer_revenus_remplacement`** : fiscalité chômage (ARE), retraite/pension (abattement 10%), rentes viagères à titre onéreux (RVTO — fractions par âge), indemnité de licenciement (seuils d'exonération), invalidité
- **Outil `simuler_sortie_per`** : simulation complète sortie PER — rente vs capital, déblocage anticipé résidence principale, déblocage exceptionnel (invalidité, décès conjoint…), versements déduits vs non déduits
- **Outil `optimiser_epargne_salariale`** : intéressement, participation, PEE, PERCO/PERCOL, AGA (abattement 50% plan conforme), BSPCE (PFU 30% / taux majoré 47.2%), abondement employeur plafonds PASS
- **Outil `calculer_impot_societes`** : IS 15% jusqu'à 42 500€ / 25% au-delà, éligibilité taux réduit PME (CA < 10M€, capital PP ≥ 75%), acomptes trimestriels, déficit reportable en avant/arrière
- **Outil `optimiser_remuneration_dirigeant`** : comparatif 3 scénarios (tout rémunération / mixte / tout dividendes) pour SASU, EURL IS, SARL IS — IS + charges sociales + IR + PFU 30%
- **Outil `calculer_fiscalite_crypto`** : refonte complète — méthode PAMC officielle (formulaire 2086), seuil 305€, moins-values reportables 10 ans, option barème vs PFU 30%, staking/mining/NFT (BNC/BIC), airdrops
- **Outil `simuler_pacte_dutreil`** : exonération 75% droits donation/succession entreprise (art. 787 B CGI), conditions ECC (2 ans) + EIC (4 ans) + direction, calcul comparatif avec/sans pacte
- **Outil `simuler_sci`** : comparatif SCI IR vs IS — revenus locatifs nets, amortissement IS, déficit foncier IR, fiscalité à la sortie (VNC, piège des amortissements IS), recommandation selon TMI et horizon

### Corrigé
- **Bug `calculer_parts()`** : garde alternée désormais correctement comptée à +0.25 part par enfant (au lieu de +0.5) — nouveau paramètre `nb_enfants_garde_alternee`
- **Micro-BIC meublés de tourisme** : taux mis à jour suite LF2024 — non classés 30% seuil 15 000€/an (au lieu de 50%), classés 71% seuil 188 700€ inchangé

### Modifié
- `calculer_impot_revenu` : nouveau paramètre `nb_enfants_garde_alternee` exposé dans le schéma

---

## [2.2.0] — 2026-03-10

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

## [2.1.0] — 2026-03-09

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

## [2.0.0] — 2026-03-09

### Ajouté
- **Outil `calculer_ifi`** : IFI avec barème officiel, abattement résidence principale 30%, décote, plafonnement 75%, stratégies
- **Outil `optimiser_tns`** : optimisation TNS/indépendants (micro vs réel, Madelin, ACRE, comparatif structures EI/EURL/SASU)
- **Outil `comparer_scenarios`** : tableau comparatif côte à côte de 2 ou 3 scénarios fiscaux
- **Outil `calculer_prelevement_source`** : taux PAS personnalisé, taux neutre, retenue mensuelle, acomptes, guide modulation
- Barème IFI 2026 avec décote et plafonnement
- Données TNS : cotisations micro BIC/BNC, plafonds Madelin

### Mis à jour
- Barème IR 2026 (revenus 2025) — indexé +1.8%
- Calendrier fiscal 2026 (dates déclaration revenus 2025)
- Plafond PER 2025 : 37 094€ max / 4 637€ plancher
- `PLAFOND_DEMI_PART` → 1 791€ (2026 estimé)
- Tous les libellés et titres mis à jour vers 2026

### Architecture
- Dispatch `if/elif` remplacé par dict `_TOOL_DISPATCH` (O(1), extensible)
- `calculer_ir()` : paramètre `tranches` optionnel pour choisir le barème
- `__version__` = "2.0.0"

---

## [1.0.0] — 2025 (version initiale)

### Ajouté
- 17 outils couvrant l'IR 2025, PER, MaPrimeRénov', plus-values, immobilier
- Barème IR 2025 (revenus 2024) officiel
- Seuils MaPrimeRénov' 2025 par catégorie (Bleu/Jaune/Violet/Rose)
- Plafonds PER 2024, barème kilométrique 2024
- Calendrier fiscal 2025
- Crédits et réductions d'impôt 2025
