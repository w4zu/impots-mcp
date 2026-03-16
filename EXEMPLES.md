# Exemples d'utilisation — MCP Impôts Français

Exemples de questions à poser directement à Claude une fois le MCP installé.
Les outils sont appelés automatiquement selon le contexte.

---

## Impôt sur le revenu

**Question :**
> "Je suis célibataire, 58 000€ de revenus nets imposables. Quel est mon impôt 2026 ?"

**Outil appelé :** `calculer_impot_revenu`

**Résultat :**
```
Impôt brut : 10 442€
Impôt net  : 10 442€
TMI        : 30%
Taux moyen : 18.0%
```

---

**Question :**
> "Je suis marié avec 2 enfants, 80 000€ de RNI. Quel est mon impôt ?"

**Outil appelé :** `calculer_impot_revenu`

**Résultat :**
```
Parts fiscales : 3.0
Impôt net      : 4 936€
TMI            : 11%
```

---

## PER — Plan d'Épargne Retraite

**Question :**
> "Si je verse 8 000€ sur mon PER, combien j'économise ? Je suis célibataire à 58 000€ de RNI."

**Outil appelé :** `calculer_economie_per`

**Résultat :**
```
Plafond déductible     : 5 800€ (10% de 58 000)
Économie d'impôt       : 1 740€
Taux de retour fiscal  : 30%
Coût réel du versement : 4 060€
```

---

## Optimisation fiscale

**Question :**
> "Je gagne 75 000€, marié avec 1 enfant. Quelles sont mes pistes d'optimisation ?"

**Outil appelé :** `optimiser_impots`

**Pistes identifiées :**
- PER (plafond 7 500€, économie ~2 250€ à TMI 30%)
- Emploi à domicile (crédit 50%)
- Dons aux associations (réduction 66–75%)

---

## Statuts professionnels — CDI vs Freelance

**Question :**
> "Je suis en CDI à 60 000€ brut. Est-ce qu'il serait intéressant de passer en freelance à 500€/jour (200 jours/an) en profession libérale ?"

**Outil appelé :** `comparer_statuts_professionnel`

**Paramètres :**
```json
{
  "salaire_brut_annuel_cdi": 60000,
  "tjm_freelance": 500,
  "jours_travailles_an": 200,
  "type_activite": "services_bnc",
  "situation_famille": "celibataire"
}
```

**Résultat (CA 100 000€) :**
```
CDI net en poche     : 41 122€  (coût employeur : 85 200€)

Auto-entrepreneur    : 64 058€  (64.1% du CA) — seuil AE dépassé
SASU SMIC+dividendes : 54 529€  (54.5% du CA) — assimilé salarié
EURL à l'IS          : 47 610€  (47.6% du CA) — TNS
Portage salarial     : 43 849€  (43.8% du CA) — protection salarié
```

**TJM minimum pour égaler le CDI (41 122€ net) :**
```
SASU           : 284€/j (CA 56 800€/an)
EURL IS        : 320€/j (CA 64 000€/an)
Portage salarial : 360€/j (CA 72 000€/an)
```

---

**Question (profil junior) :**
> "Je gagne 36 000€ brut. Quel TJM minimum pour m'y retrouver en freelance ?"

**Paramètres :**
```json
{
  "salaire_brut_annuel_cdi": 36000,
  "tjm_freelance": 300,
  "jours_travailles_an": 180,
  "type_activite": "services_bnc",
  "situation_famille": "celibataire"
}
```

**Résultat :**
```
CDI net en poche : 24 278€

TJM minimum :
  Auto-entrepreneur : 183€/j
  SASU             : 221€/j
  Portage salarial  : 253€/j
```

---

## Vérification actualité fiscale

**Question :**
> "Les données fiscales sont-elles à jour pour 2027 ?"

**Outil appelé :** `verifier_actualite_fiscale`

**Paramètres :**
```json
{ "annee_cible": 2027 }
```

**Résultat :**
```
Statut : Mise à jour requise — 2027 est 1 an en avance.

Éléments à mettre à jour :
- TRANCHES_IR_ACTIF (indexation ~1.8%/an)
- PLAFOND_PER_MAX (10% x 8 PASS N-1)
- PLAFOND_PER_MIN (10% x 1 PASS N-1)
- Seuils AE (reindexation biennale URSSAF)
- SMIC brut annuel (simulations SASU)
- annee_actuelle_mcp → 2027
```

**Question :**
> "Les données sont-elles à jour pour 2026 ?"

**Résultat :**
```
Statut : Le MCP est à jour pour cette année fiscale.
```

---

## IFI — Impôt sur la Fortune Immobilière

**Question :**
> "Mon patrimoine immobilier brut est de 2 000 000€, avec 200 000€ de dettes. Quel est mon IFI ?"

**Outil appelé :** `calculer_ifi`

**Résultat :**
```
Patrimoine net taxable : 1 800 000€  (abattement RP 30% non appliqué ici)
IFI à payer           : 6 000€
```

---

## Crypto-monnaies

**Question :**
> "J'ai cédé des cryptos pour 15 000€. Mon portefeuille valait 50 000€ et mon PAMC est de 30 000€."

**Outil appelé :** `calculer_fiscalite_crypto`

**Paramètres :**
```json
{
  "prix_total_cession": 15000,
  "valeur_portefeuille_avant_cession": 50000,
  "prix_acquisition_moyen_portefeuille": 30000,
  "tmi": 30
}
```

**Résultat :**
```
Fraction cédée      : 30%
Plus-value brute    : 6 000€  (15 000 − 30% × 30 000)
PFU 30%             : 1 800€  (IR 768€ + PS 1 032€)
Seuil d'exonération : 305€ — dépassé, déclaration obligatoire
```

---

## Droits de donation

**Question :**
> "Je veux donner 150 000€ à mon enfant. Quels sont les droits à payer ?"

**Outil appelé :** `simuler_droits_donation`

**Paramètres :**
```json
{
  "montant_donation": 150000,
  "lien_parente": "enfant_parent",
  "donations_anterieures": 0
}
```

**Résultat :**
```
Abattement disponible (15 ans) : 100 000€
Base taxable                   : 50 000€
Droits à payer                 : ~2 194€
Taux effectif                  : 1.5%
```

---

## Auto-entrepreneur

**Question :**
> "Je suis consultant en BNC à 55 000€ de CA. Micro ou réel ? VFL ?"

**Outil appelé :** `guide_auto_entrepreneur`

**Résultat :**
```
Activité         : BNC (professions libérales)
Seuil AE         : 77 700€ — eligible
Cotisations      : 12 705€  (23.1%)
Net cotisations  : 42 295€
Revenu imposable : 36 300€  (abattement 34%)
IR estimé        : ~8 000€ (selon foyer)
```

---

## Simulation retraite

**Question :**
> "J'ai 55 ans, 140 trimestres, 50 000€ de salaire brut. Quand puis-je partir à taux plein ?"

**Outil appelé :** `simuler_depart_retraite`

**Résultat :**
```
Trimestres requis    : 172  (née 1970 → réforme 2023)
Trimestres validés   : 140
Manquants            : 32  (8 ans à compléter)
Âge taux plein légal : 67 ans (quel que soit le nombre de trimestres)
Départ 64 ans        : décote  -18.75%
Départ 67 ans        : taux plein — pension ~2 200€/mois brut
```

---

## Comparaison de scénarios

**Question :**
> "Compare ma situation actuelle, avec PER 5 000€, et avec PER + dons 500€."

**Outil appelé :** `comparer_scenarios`

**Paramètres :**
```json
{
  "scenarios": [
    {"label": "Actuel",     "revenu_net_imposable": 65000, "situation_famille": "celibataire"},
    {"label": "PER 5 000",  "revenu_net_imposable": 65000, "situation_famille": "celibataire", "versements_per": 5000},
    {"label": "PER + dons", "revenu_net_imposable": 65000, "situation_famille": "celibataire", "versements_per": 5000, "dons": 500}
  ]
}
```

---

## Revenus exceptionnels — Système du quotient

**Question :**
> "J'ai reçu 40 000€ d'indemnité de licenciement supra-légale en plus de mon salaire de 55 000€. Est-ce que le système du quotient m'aide ?"

**Outil appelé :** `simuler_revenus_exceptionnels`

**Paramètres :**
```json
{
  "rni_ordinaire": 55000,
  "revenu_exceptionnel": 40000,
  "nombre_annees_echelement": 4,
  "situation_famille": "celibataire",
  "type_revenu": "indemnite_licenciement"
}
```

**Résultat :**
```
RNI ordinaire seul       : 9 542€ d'IR
Sans quotient (55k+40k)  : 13 067€ sur l'indemnité
Avec quotient N=4        : 12 000€ sur l'indemnité
Economie                 : 1 067€
```

---

## PFU vs barème progressif

**Question :**
> "J'ai 10 000€ de dividendes, mes autres revenus sont 20 000€. Dois-je opter pour le barème ?"

**Outil appelé :** `comparer_pfu_bareme_capital`

**Paramètres :**
```json
{
  "type_revenu": "dividendes",
  "montant": 10000,
  "rni_autres_revenus": 20000,
  "situation_famille": "celibataire"
}
```

**Résultat :**
```
PFU (flat tax 30%)   : 3 000€  (IR 1 280€ + PS 1 720€)
Barème progressif    : 2 679€  (abattement 40%, IR 959€ + PS 1 720€)
Recommandation       : Barème progressif — economie 321€
CSG deductible N+1   : 680€ (gain ~75€ l'année suivante)

Action : cochez la case 2OP dans votre déclaration 2042
```

**Pour TMI 30% :**
```
PFU                  : 3 000€
Barème (60% × 30%)   : 3 520€
Recommandation       : PFU — économie 520€
```

---

## LMNP — Location Meublée Non Professionnelle

**Question :**
> "Je loue un appartement meublé 12 000€/an. Le bien vaut 180 000€ hors terrain, mobilier 8 000€, charges 1 500€, intérêts 4 000€, TF 900€. Micro ou réel ?"

**Outil appelé :** `simuler_lmnp`

**Paramètres :**
```json
{
  "loyers_annuels_bruts": 12000,
  "valeur_bien_hors_terrain": 180000,
  "valeur_mobilier": 8000,
  "charges_annuelles": 1500,
  "interets_emprunt_annuels": 4000,
  "taxe_fonciere": 900,
  "situation_famille": "celibataire",
  "rni_autres_revenus": 50000
}
```

**Résultat :**
```
Micro-BIC (abatt. 50%)     : base 6 000€ → taxes 1 032€ → net 10 968€
Réel simplifié             :
  Charges déductibles       : 6 400€
  Amortissement bâtiment    : 4 500€/an (180 000÷40)
  Amortissement mobilier    : 1 143€/an (8 000÷7)
  Résultat                  : Déficit 43€ → 0€ d'impôt

Recommandation : Régime réel — 0€ d'impôt vs 1 032€ en micro
```

---

## Rachat de trimestres retraite

**Question :**
> "J'ai 50 ans, 120 trimestres validés sur 172, salaire 55 000€ brut. Combien coûte le rachat de 4 trimestres ?"

**Outil appelé :** `simuler_rachat_trimestres`

**Paramètres :**
```json
{
  "nb_trimestres_racheter": 4,
  "salaire_annuel_brut": 55000,
  "age_actuel": 50,
  "annee_naissance": 1975,
  "trimestres_valides_actuels": 120,
  "option_rachat": "duree_seulement",
  "tmi": 30
}
```

**Résultat :**
```
Taux par trimestre (50 ans) : 31.0% du PASS
Coût par trimestre          : 14 374€
Coût total (4 trimestres)   : 57 496€
Economie fiscale (TMI 30%)  : -17 249€  (case 6DD)
Coût net d'impôt            : 40 247€

Types rachetables : années incomplètes, études supérieures (max 12), stages
Comparer avec : versement PER équivalent (même économie fiscale, plus flexible)
```

---

## Exit tax

**Question :**
> "Je pars m'installer en Allemagne. J'ai 1,2M€ de plus-values latentes sur mes actions. Qu'est-ce que je dois à l'état ?"

**Outil appelé :** `calculer_exit_tax`

**Paramètres :**
```json
{
  "plus_values_latentes_total": 1200000,
  "situation_famille": "celibataire",
  "pays_destination": "ue_eea",
  "annees_residence_france_10_dernieres": 10
}
```

**Résultat :**
```
Exit tax calculée           : ~360 000€  (PFU 30%)
  IR 12.8%                  : 153 600€
  Prélèvements sociaux 17.2%: 206 400€

Départ vers Allemagne (UE) → Sursis automatique de paiement
  - Taxe déclarée mais non payée immédiatement
  - Dégrevée si retour en France dans les 5 ans
  - Exigible lors de la cession effective des titres
  - Déclaration annuelle 2074-ETD obligatoire
```

**Si départ hors UE (ex. Suisse) :**
```
Paiement immédiat ou garantie (nantissement des titres) requise
```

---

## Loc'Avantages

**Question :**
> "Je veux signer une convention ANAH sociale sur un appartement de 40m² en zone B1. Loyers actuels : 7 200€/an."

**Outil appelé :** `guide_loc_avantages`

**Paramètres :**
```json
{
  "loyers_bruts_annuels": 7200,
  "niveau_convention": "social",
  "surface_m2": 40,
  "zone": "B1",
  "rni_autres_revenus": 45000,
  "situation_famille": "celibataire"
}
```

**Résultat :**
```
Réduction d'impôt (35%)     : 2 520€/an
Loyer plafond zone B1 social : 7.70€/m²/mois  (11€ × 70%)
Loyer annuel max 40m²       : 3 696€/an

Gain fiscal annuel          : ~2 520€ (plafond niches 10 000€)
Durée engagement            : 6 ans minimum (convention ANAH)
```

---

## Micro-foncier vs réel

**Question :**
> "J'ai 9 600€ de loyers, intérêts 5 000€, charges 1 200€, TF 800€, travaux 6 000€. Quel régime ?"

**Outil appelé :** `simuler_micro_foncier`

**Paramètres :**
```json
{
  "loyers_bruts_annuels": 9600,
  "interets_emprunt": 5000,
  "charges_copropriete": 1200,
  "taxe_fonciere": 800,
  "travaux_entretien_annuels": 6000,
  "frais_gestion_annuels": 480,
  "situation_famille": "celibataire",
  "rni_autres_revenus": 55000
}
```

**Résultat :**
```
Micro-foncier (30%)  : base 6 720€ → taxes ~2 197€
Régime réel          :
  Charges totales    : 13 480€  > loyers 9 600€
  Déficit foncier    : 3 880€
  Hors intérêts      : 0€ (tout imputable aux intérêts)
  Imputable global   : 0€ (intérêts = toute la perte)
  Report foncier     : 3 880€ sur revenus fonciers futurs (10 ans)

Recommandation : Régime réel — 0€ d'impôt + report déficit
```

---

## Notes

- Toutes les simulations sont basées sur le barème **2026 (revenus 2025)**.
- Les taux de cotisations sociales sont des approximations. Consultez un expert-comptable pour vos décisions.
- Les arguments JSON sont passés automatiquement par Claude selon votre description en langage naturel.
