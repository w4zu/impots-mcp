# Exemples d'utilisation

Exemples de questions à poser directement à Claude une fois le MCP installé.
Les outils sont appelés automatiquement selon le contexte de la conversation.

Tous les résultats ci-dessous sont produits par la version 3.0.0 du serveur.

---

## Impôt sur le revenu

**Question :**
> "Je suis célibataire, 58 000€ de revenus nets imposables. Quel est mon impôt 2026 ?"

**Outil appelé :** `calculer_impot_revenu`

**Résultat :**
```
Impôt net  : 10 504€
TMI        : 30%
Taux moyen : 18,1%
```

**Question :**
> "Je suis marié avec 2 enfants, 80 000€ de RNI. Quel est mon impôt ?"

**Résultat :**
```
Parts fiscales      : 3,0
Impôt net           : 6 594€
TMI                 : 11%
```

Le plafonnement de l'avantage lié aux enfants (1 807€ par demi-part) s'applique ici :
sans plafonnement, l'impôt ressortirait à 4 972€.

---

## CDHR, imposition minimale des hauts revenus

**Question :**
> "J'ai perçu 1 M€ de dividendes, célibataire, j'ai payé 128 000€ au PFU. Suis-je concerné
> par la contribution différentielle ?"

**Outil appelé :** `calculer_cdhr`

**Paramètres :**
```json
{
  "rfr_retraite": 1000000,
  "situation_famille": "celibataire",
  "impot_revenu_paye": 128000
}
```

**Résultat :**
```
Imposition minimale retenue (20% du RFR) : 200 000€
Impôt sur le revenu acquitté             : -128 000€
CEHR estimée                             : -27 500€
CDHR due                                 : 44 500€
Acompte de 95% du 1er au 15 décembre     : 42 275€
```

Entre 250 000€ et 330 000€ de RFR (500 000€ et 660 000€ en couple), une décote lisse
l'entrée dans le dispositif : à 280 000€, l'imposition minimale retenue tombe à 24 750€
au lieu de 56 000€.

---

## PER, plan d'épargne retraite

**Question :**
> "Si je verse 8 000€ sur mon PER, combien j'économise ? Je suis célibataire à 58 000€ de RNI."

**Outil appelé :** `calculer_economie_per`

**Résultat :**
```
Plafond déductible (versement 2026) : 5 800€  (10% des revenus professionnels)
Économie d'impôt                    : 1 740€
Taux de retour fiscal               : 30%
Coût réel du versement              : 4 060€
```

Le plafond maximum est de 37 680€ pour un versement 2026 (8 PASS 2025), contre 37 094€
pour un versement 2025.

---

## Optimisation fiscale

**Question :**
> "Je gagne 75 000€, marié avec 1 enfant. Quelles sont mes pistes d'optimisation ?"

**Outil appelé :** `optimiser_impots`

**Pistes identifiées, par priorité :**
```
1. PER (versement 3 000€)              gain ~900€
2. Emploi à domicile (5 000€)          gain ~2 500€ (crédit 50%)
3. Dons aux associations               réduction 66% à 75%
4. Frais réels professionnels          selon distance et frais engagés
5. Épargne défiscalisée (PEA, LEP...)
```

---

## Statuts professionnels, CDI contre freelance

**Question :**
> "Je suis en CDI à 60 000€ brut. Est-ce intéressant de passer freelance à 500€/jour
> (200 jours/an) en profession libérale ?"

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
CDI net en poche      : 41 060€   (coût employeur 85 200€, ratio net/coût 48,2%)

Auto-entrepreneur     : 61 496€   (61,5% du CA) seuil de 83 600€ dépassé, non applicable
SASU SMIC+dividendes  : 53 750€   (53,8% du CA) assimilé salarié
EURL à l'IS           : 47 368€   (47,4% du CA) TNS
Portage salarial      : 43 787€   (43,8% du CA) protection de salarié

TJM minimum pour égaler le CDI, sur 200 jours facturés :
  Auto-entrepreneur   313€/j     SASU              378€/j
  EURL à l'IS         422€/j     Portage salarial  463€/j
```

Les dividendes sont désormais taxés au PFU de 31,4% et non plus 30% : la SASU perd
environ 1 point de net par rapport à la version précédente du serveur.

---

## Diagnostic personnalisé de passage en freelance

**Question :**
> "Je suis dev senior à 65k brut, 8 ans d'expérience, 20k d'épargne, 1 800€ de charges
> mensuelles, pas encore de clients. Est-ce que je peux me lancer ?"

**Outil appelé :** `diagnostiquer_passage_freelance`

**Résultat :**
```
Score de maturité : 9 / 12

  Épargne de sécurité       2/3   11,1 mois de charges couvertes
  Expérience                2/2   profil senior, TJM élevé justifié
  Réseau et prospects       0/2   aucun prospect identifié
  Demande sectorielle       2/2   développement, demande très forte
  Gain financier            2/2   +66% de net potentiel
  Profil de risque          1/1   risque moyen, sans charge familiale lourde

CDI actuel            : 43 907€ net
SASU à 750€/jour      : 72 870€ net  (+28 963€)

TJM pour égaliser le CDI   : 444€/j
TJM recommandé             : 511€/j  (+15% pour les inter-contrats)
Médian du secteur          : 550€/j
```

Le diagnostic rappelle aussi que la durée d'indemnisation chômage après rupture
conventionnelle est passée à 15 mois au 1er septembre 2026, contre 18 auparavant.

---

## Facturation électronique

**Question :**
> "Je suis auto-entrepreneur en franchise de TVA, mes clients sont des entreprises
> françaises. Suis-je concerné par la facture électronique ?"

**Outil appelé :** `guide_facturation_electronique`

**Résultat :**
```
Recevoir des factures électroniques : 1er septembre 2026  (toutes les entreprises)
Émettre des factures électroniques  : 1er septembre 2027  (micro-entreprises)

La franchise en base de TVA ne dispense pas de l'obligation : le micro-entrepreneur
n'est pas redevable de la TVA mais reste assujetti.

B2B France      facture électronique obligatoire
B2C             e-reporting seulement
International   e-reporting seulement

Sanctions : 50€ par facture non conforme (plafond 15 000€/an),
            500€ par transmission d'e-reporting manquante,
            500€ en cas d'absence de plateforme agréée après mise en demeure.
```

---

## Prélèvement à la source

**Question :**
> "Marié avec 1 enfant, 45 000€ de RNI, 3 000€ net par mois. Quel est mon taux au
> 1er septembre ?"

**Outil appelé :** `calculer_prelevement_source`

**Résultat :**
```
Taux personnalisé du foyer   : 2,1%   soit 64€/mois
Taux par défaut (métropole)  : 7,5%   soit 225€/mois

Calendrier :
  1er septembre 2026  nouveau taux, issu de la déclaration des revenus 2025
  1er mai             actualisation de la grille des taux par défaut
  25 septembre        prélèvement du solde, étalé en 4 fois au-delà de 300€
```

Depuis le 1er septembre 2025, le taux individualisé s'applique par défaut aux couples
mariés ou pacsés : c'est le retour au taux du foyer qui demande désormais une démarche.

---

## Vérification de l'actualité fiscale

**Question :**
> "Les données fiscales sont-elles à jour pour 2027 ?"

**Outil appelé :** `verifier_actualite_fiscale`

**Résultat :**
```
Statut : mise à jour requise, 2027 est 1 an en avance sur les données du serveur.

Éléments à réviser :
  TRANCHES_IR_ACTIF                 indexation de la loi de finances
  PLAFOND_PER_MAX / _MIN            10% de 8 PASS N-1
  PS_CAPITAL / PS_IMMOBILIER        taux de prélèvements sociaux
  TAUX_NEUTRES_PAS                  grille BOFiP publiée chaque 1er mai
  Seuils micro-entreprise et TVA    URSSAF
  SMIC_BRUT_ANNUEL                  simulations SASU
```

---

## IFI

**Question :**
> "Mon patrimoine immobilier brut est de 2 000 000€, avec 200 000€ de dettes."

**Outil appelé :** `calculer_ifi`

**Résultat :**
```
Patrimoine net taxable : 1 800 000€
IFI à payer            : 6 000€   (0,5% de 800k à 1,3M, puis 0,7%)
```

La loi de finances 2026 a maintenu l'IFI dans son périmètre immobilier : le projet
d'impôt sur la fortune improductive n'a pas été retenu.

---

## Crypto-actifs

**Question :**
> "J'ai cédé des cryptos pour 15 000€. Mon portefeuille valait 50 000€ et mon PAMC
> est de 30 000€. Mon RNI est de 50 000€."

**Outil appelé :** `calculer_fiscalite_crypto`

**Résultat :**
```
Fraction cédée      : 30%
Plus-value brute    : 6 000€    (15 000 − 30% × 30 000)

Option A, PFU 31,4% : 1 884€    (IR 768€ + PS 1 116€)
Option B, barème    : 2 916€    (IR 1 800€ + PS 1 116€)

Le PFU est plus favorable : économie de 1 032€.
Déclaration du formulaire 2086 obligatoire dès 305€ de cessions.
```

Les gains de crypto-actifs relèvent des prélèvements sociaux de 18,6% depuis les
revenus 2025.

---

## Droits de donation

**Question :**
> "Je veux donner 150 000€ à mon enfant. Quels sont les droits à payer ?"

**Outil appelé :** `simuler_droits_donation`

**Résultat :**
```
Abattement disponible (15 ans) : 100 000€
Base taxable                   : 50 000€
Droits à payer                 : 8 194€
Taux effectif global           : 5,5%
```

---

## Auto-entrepreneur

**Question :**
> "Je suis consultant en BNC à 55 000€ de CA. Micro ou réel ? Et la TVA ?"

**Outil appelé :** `guide_auto_entrepreneur`

**Résultat :**
```
Seuil de CA          : 83 600€    (exercices 2026 à 2028)
Cotisations 25,6%    : 14 080€
Net après cotisations: 40 920€
Franchise TVA        : 37 500€ dépassé, assujettissement obligatoire
```

Le taux de cotisations BNC est passé de 23,1% à 25,6% et la catégorie Cipav (23,2%)
est distinguée pour les professions libérales réglementées.

---

## Simulation de départ à la retraite

**Question :**
> "J'ai 55 ans, 140 trimestres, 50 000€ de salaire brut. Quand puis-je partir ?"

**Outil appelé :** `simuler_depart_retraite`

**Résultat :**
```
Trimestres requis : 172        Trimestres validés : 140

Âge     Trimestres  Décote/surcote  Brut/mois   Net/mois
62 ans     168         -5,0%         2 149€      2 069€   (carrière longue requise)
64 ans     176         +5,0%         2 431€      2 311€
67 ans     188        +20,0%         2 779€      2 603€
```

La réforme de 2023 est suspendue du 1er septembre 2026 au 1er janvier 2028 pour les
générations 1964 à 1968. Un assuré né en 1964 part à 62 ans et 9 mois avec 170
trimestres, au lieu de 63 ans et 171 trimestres.

---

## PFU contre barème progressif

**Question :**
> "J'ai 10 000€ de dividendes, mes autres revenus sont de 20 000€. Dois-je cocher 2OP ?"

**Outil appelé :** `comparer_pfu_bareme_capital`

**Résultat :**
```
PFU (flat tax 31,4%) : 3 140€   (IR 1 280€ + PS 1 860€)
Barème progressif    : 2 819€   (base 6 000€ après abattement de 40%)
Recommandation       : barème, économie de 321€
CSG déductible N+1   : 680€

Action : cochez la case 2OP de la déclaration 2042.
```

**Seuils de bascule, prélèvements sociaux inclus :**
```
TMI    Dividendes            Intérêts et PV mobilières
0 %    barème  18,6%         barème  18,6%
11 %   barème  25,2%         barème  29,6%
30 %   PFU     36,6%         PFU     48,6%
41 %   PFU     43,2%         PFU     59,6%
45 %   PFU     45,6%         PFU     63,6%
```

Pour les revenus 2026 et suivants, la loi de finances 2026 rend l'option révocable
dans le délai de réclamation. Elle reste irrévocable pour les revenus 2025.

---

## LMNP, location meublée non professionnelle

**Question :**
> "Je loue un meublé 12 000€/an. Le bien vaut 180 000€ hors terrain, mobilier 8 000€,
> charges 1 500€, intérêts 4 000€, taxe foncière 900€. Micro ou réel ?"

**Outil appelé :** `simuler_lmnp`

**Résultat :**
```
Micro-BIC (abattement 50%) : base 6 000€, taxes 2 916€, net 2 684€
Réel simplifié             : base 0€, taxes 0€, net 5 600€

  Charges déductibles      : 6 400€
  Amortissement bâtiment   : 4 500€/an  (180 000 / 40)
  Amortissement mobilier   : 1 143€/an  (8 000 / 7)

Recommandation : régime réel.
```

Deux points d'attention : les prélèvements sociaux sur les revenus de location meublée
sont passés à 18,6% (contre 17,2% pour la location nue), et les amortissements déduits
sont réintégrés au calcul de la plus-value de revente depuis la loi de finances 2025.

---

## Micro-foncier contre réel

**Question :**
> "J'ai 9 600€ de loyers nus, intérêts 5 000€, charges 1 200€, taxe foncière 800€,
> travaux 6 000€, frais de gestion 480€."

**Outil appelé :** `simuler_micro_foncier`

**Résultat :**
```
Micro-foncier (abattement 30%) : base 6 720€, taxes 3 172€, net 6 428€
Régime réel                    : déficit de 3 880€, aucune imposition, net 9 600€

  Total des charges : 13 480€ pour 9 600€ de loyers

Recommandation : régime réel, avec report du déficit sur les revenus fonciers futurs.
```

Les revenus fonciers restent aux prélèvements sociaux de 17,2%.

---

## Rachat de trimestres

**Question :**
> "J'ai 50 ans, 120 trimestres validés, 55 000€ brut. Combien coûte le rachat de
> 4 trimestres ?"

**Outil appelé :** `simuler_rachat_trimestres`

**Résultat :**
```
Taux par trimestre (50 ans) : 31,0% du salaire de référence
Coût par trimestre          : 14 899€
Coût total                  : 59 596€
Économie fiscale à 30%      : -17 879€   (déductible, case 6DD)
Coût net d'impôt            : 41 717€

Gain de pension : 35€/mois
```

Avec 52 trimestres manquants, la décote reste plafonnée à 25% : le rachat de
4 trimestres n'agit que sur le prorata de pension, ce que le comparatif fait apparaître.

---

## Exit tax

**Question :**
> "Je pars en Allemagne avec 1,2 M€ de plus-values latentes sur mes actions."

**Outil appelé :** `calculer_exit_tax`

**Résultat :**
```
Plus-values latentes  : 1 200 000€   (seuil de déclenchement : 800 000€)

IR au PFU 12,8%       : 153 600€
Prélèvements sociaux  : 223 200€     (18,6%)
Exit tax totale       : 376 800€     (31,4%)

Départ vers l'Allemagne, donc UE : sursis de paiement automatique.
  Taxe déclarée mais non payée immédiatement
  Dégrèvement en cas de retour en France dans les 5 ans
  Le sursis prend fin lors de la cession effective des titres
  Déclaration annuelle 2074-ETD à maintenir
```

---

## Loc'Avantages

**Question :**
> "Je veux signer une convention ANAH sociale sur un 40 m² en zone B1. Loyers actuels
> de 7 200€/an."

**Outil appelé :** `guide_loc_avantages`

**Résultat :**
```
Réduction d'impôt (35%)      : 2 520€/an
Loyer plafond zone B1 social : 7,70€/m²/mois
Loyer annuel maximum, 40 m²  : 3 696€/an
Durée d'engagement           : 6 ans minimum
```

---

## Chômage après rupture conventionnelle

**Question :**
> "J'ai touché 25 000€ d'allocations chômage cette année. Comment sont-elles imposées ?"

**Outil appelé :** `calculer_revenus_remplacement`

**Résultat :**
```
Allocations ARE brutes     : 25 000€
Abattement de 10%          : -2 500€
Revenu imposable           : 22 500€
Impôt estimé (1 part)      : 845€

Durée maximale après rupture conventionnelle, depuis le 1er septembre 2026 :
  moins de 55 ans   15 mois     (18 mois auparavant)
  55 ans et plus    20,5 mois   (22,5 mois auparavant)
```

Aucun prélèvement social n'est dû sur les allocations chômage.

---

## Notes

- Les simulations reposent sur le barème 2026 (revenus 2025) et sur les taux en vigueur
  au 1er septembre 2026.
- Les taux de cotisations sociales sont des approximations. Consultez un expert-comptable
  avant toute décision.
- Les arguments JSON sont transmis automatiquement par Claude à partir de votre
  description en langage naturel : vous n'avez pas à les écrire.
