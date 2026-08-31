# impots-mcp : expert fiscal français pour Claude

## Vue d'ensemble

**impots-mcp** est un serveur MCP (Model Context Protocol) qui transforme Claude en assistant
fiscal spécialisé dans la fiscalité française. Il couvre l'impôt sur le revenu, l'IS, l'IFI, les
plus-values, la crypto, la retraite, la transmission de patrimoine et la comparaison de statuts
professionnels (CDI contre freelance).

Toutes les données fiscales sont intégrées localement. Aucune requête externe n'est effectuée
pendant les calculs.

Version 3.0.0, à jour au 1er septembre 2026.

---

## Nouveautés de la version 3.0.0

Trois évolutions législatives entrées en vigueur en 2026 sont intégrées.

**Prélèvements sociaux sur le capital : 17,2% vers 18,6%**
La LFSS 2026 porte la CSG sur le capital de 9,2% à 10,6%. Le PFU passe donc de 30% à 31,4%.
Le taux de 17,2% reste applicable aux revenus limitativement énumérés par le nouvel article
L. 136-8, IV du code de la sécurité sociale : revenus fonciers, plus-values immobilières des
particuliers, assurance-vie, épargne logement et PEP. Les taux sont désormais centralisés dans
`PS_CAPITAL`, `PS_IMMOBILIER`, `PS_ASSURANCE_VIE` et `PS_PENSION`, appliqués régime par régime.

**CDHR, imposition minimale de 20% des hauts revenus**
Nouvel outil `calculer_cdhr` (article 224 CGI) : seuils de 250 000€ et 500 000€, décote
d'entrée, majorations forfaitaires, acompte de 95% du 1er au 15 décembre. La contribution est
aussi signalée automatiquement par `calculer_impot_revenu` quand le revenu dépasse le seuil.

**Facturation électronique obligatoire au 1er septembre 2026**
Nouvel outil `guide_facturation_electronique` : obligation de réception pour toutes les
entreprises assujetties à la TVA, émission pour les grandes entreprises et les ETI, échéance de
2027 pour les PME et micro-entreprises, plateformes agréées, formats, e-reporting et sanctions.

Autres mises à jour de cette version : grille officielle des taux par défaut du prélèvement à
la source (métropole et DOM, en vigueur au 1er mai 2026), nouveau taux personnalisé au
1er septembre, taux individualisé appliqué par défaut aux couples, suspension de la réforme des
retraites du 1er septembre 2026 au 1er janvier 2028, réduction de la durée d'indemnisation
chômage après rupture conventionnelle, actualisation de l'abattement de 10% sur les pensions,
de l'abattement des personnes âgées et du plafond de pension alimentaire.

---

## Fonctionnalités

Le serveur expose **64 outils** répartis en plusieurs domaines.

**Calcul et déclaration**
- Impôt sur le revenu 2026 (barème indexé, quotient familial plafonné, décote, garde alternée)
- CEHR et CDHR pour les hauts revenus
- Prélèvement à la source : taux personnalisé, grille des taux par défaut, modulation, acomptes
- Analyse de déclaration 2042 case par case
- Correction de déclaration : délais, majorations, prescription

**Optimisation fiscale**
- PER : plafond déductible, économie selon TMI, simulation de sortie
- Frais réels contre abattement de 10%
- Dons, emploi à domicile, PEA, épargne salariale (PEE, PERCO, BSPCE)
- Diagnostic complet avec recommandations priorisées

**Statuts professionnels**
- Comparaison CDI, auto-entrepreneur, SASU, EURL à l'IS, portage salarial
- Calcul du net en poche après toutes charges sociales et impôts
- TJM minimum pour égaler un salaire CDI donné
- Diagnostic de passage en freelance : score de maturité, secteur, épargne, réseau, TJM cible

**Entreprises et obligations**
- Facturation électronique : calendrier, plateformes agréées, formats, e-reporting, sanctions
- TVA : franchise en base, réel simplifié, taux, opérations intracommunautaires
- CFE : cotisation minimum par tranche de CA, exonérations

**Revenus exceptionnels et capital**
- Système du quotient (article 163-0 A) : indemnité de licenciement, prime, rappels de salaires
- PFU de 31,4% contre barème progressif pour dividendes, intérêts et plus-values mobilières
- Seuil de bascule selon le TMI, case 2OP et nouvelle révocabilité de l'option

**Immobilier locatif**
- LMNP : micro-BIC (50% longue durée, 50% tourisme classé, 30% non classé) contre réel
- Amortissement plafonné au bénéfice (article 39 C II) et réintégré à la plus-value (LF 2025)
- Micro-foncier contre réel : déficit foncier, imputation sur le revenu global, reports
- Loc'Avantages (article 199 tricies) : réduction de 15%, 35% ou 65% via convention ANAH

**Rénovation énergétique**
- MaPrimeRénov' : forfaits du parcours par geste selon la catégorie de ressources
- Barèmes distincts Île-de-France et reste du territoire, indexés sur le nombre de personnes
- Rénovation d'ampleur : taux, plafonds, écrêtement, Mon Accompagnateur Rénov'

**Retraite**
- Départ à la retraite : décote, surcote, comparatif 62, 64 et 67 ans, suspension de la réforme
- Rachat de trimestres : coût net d'impôt, gain de pension, retour sur investissement
- Réversion de pension, sortie de PER en rente ou en capital

**Expatriation et international**
- Exit tax (article 167 bis) : plus-values latentes, sursis automatique UE et EEE
- Résidence fiscale, formulaire 2047, conventions (13 pays)
- Frontaliers Suisse, Luxembourg, Belgique, Allemagne
- DOM-TOM : abattements, Girardin, Pinel outre-mer

**Société et dirigeant**
- Impôt sur les sociétés (15% et 25%, acomptes, déficit)
- Optimisation rémunération contre dividendes (SASU, EURL, SARL à l'IS)
- SASU, SCI, holding, pacte Dutreil, cession d'entreprise

**Patrimoine et transmission**
- IFI : barème, abattements, plafonnement, stratégies
- Droits de donation et de succession par lien de parenté
- Plus-values mobilières et immobilières (abattements de durée, frais)
- Assurance-vie, démembrement, SCPI, PEA

**Indépendants**
- Auto-entrepreneur : seuils, cotisations, versement libératoire, ACRE
- TNS : micro contre réel, Madelin, régimes BNC et BIC

**Crypto-actifs**
- Méthode PAMC officielle (formulaire 2086)
- Plus-values, moins-values reportables, staking, mining, NFT

**Actualité fiscale**
- Vérification que les barèmes sont à jour pour une année donnée
- Liste des paramètres à réviser lors d'un changement d'année
- Procédure de mise à jour vers 2027 et au-delà

---

## Prérequis

- Python 3.10 ou supérieur
- Claude Desktop ou Claude Code (CLI)
- pip

---

## Installation

### 1. Récupérer les sources

```bash
git clone https://github.com/VOTRE_USER/impots-mcp.git
cd impots-mcp
```

### 2. Créer l'environnement virtuel

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 3. Vérifier l'installation

```bash
venv/bin/python -c "import ast; ast.parse(open('impots-mcp.py').read()); print('OK')"
```

Résultat attendu : `OK`

---

## Configuration

### Claude Desktop

Éditez le fichier de configuration :

- Linux et macOS : `~/.config/claude/claude_desktop_config.json`
- Windows : `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "impots-fr": {
      "command": "/chemin/absolu/vers/impots-mcp/venv/bin/python",
      "args": ["/chemin/absolu/vers/impots-mcp/impots-mcp.py"]
    }
  }
}
```

Relancez Claude Desktop. Les outils apparaissent automatiquement dans l'interface.

### Claude Code (CLI)

```bash
claude mcp add impots-fr /chemin/absolu/vers/impots-mcp/venv/bin/python \
  -- /chemin/absolu/vers/impots-mcp/impots-mcp.py
```

Vérifier :

```bash
claude mcp list
```

---

## Utilisation

Les outils sont appelés automatiquement par Claude selon le contexte de la conversation.
Il suffit de poser vos questions en langage naturel.

### Exemples rapides

```
"Calcule mon impôt, je suis marié avec 2 enfants et 80 000€ de revenus nets imposables"
→ Impôt net 6 594€, TMI 11%, avantage enfants plafonné à 3 614€

"Combien j'économise si je verse 8 000€ sur mon PER ? Je suis célibataire à 58 000€."
→ Économie 1 740€, coût réel 4 060€, plafond applicable 5 800€

"Je suis en CDI à 60k brut. Est-ce intéressant de passer freelance à 500€/jour ?"
→ CDI net 41 060€, SASU net 53 750€, TJM minimum SASU 378€/j

"Je suis dev senior à 65k brut, 8 ans d'expérience, 20k d'épargne, pas encore de clients"
→ Score 9/12, TJM minimum 444€/j, TJM recommandé 511€/j, alerte réseau à construire

"J'ai 1 M€ de dividendes et j'ai payé 128 000€ au PFU. Suis-je redevable de la CDHR ?"
→ Imposition minimale 200 000€, CDHR 44 500€, acompte de 42 275€ en décembre

"Je suis auto-entrepreneur : la facture électronique me concerne quand ?"
→ Réception au 1er septembre 2026, émission au 1er septembre 2027, sanction 50€ par facture

"Dois-je opter pour le barème sur mes 10 000€ de dividendes ? Autres revenus 20 000€."
→ Barème 2 819€ contre PFU 3 140€, économie 321€, cochez la case 2OP

"J'ai vendu des cryptos pour 15 000€, portefeuille de 50 000€, PAMC de 30 000€"
→ Plus-value 6 000€, PFU 31,4% soit 1 884€, formulaire 2086 obligatoire

"Je loue un meublé 12 000€/an, bien à 180 000€, charges 6 400€. Micro ou réel ?"
→ Micro-BIC 2 916€ de taxes, réel 0€, prélèvements sociaux à 18,6% en meublé

"Quand puis-je partir à la retraite ? 55 ans, 140 trimestres, 50k brut."
→ 64 ans 2 311€ net/mois, 67 ans 2 603€ net/mois, réforme suspendue jusqu'en 2028

"Je pars m'installer en Allemagne avec 1,2 M€ de plus-values latentes"
→ Exit tax 376 800€ au taux de 31,4%, sursis de paiement automatique

"Les barèmes sont-ils à jour pour 2027 ?"
→ Mise à jour requise, liste des paramètres à modifier fournie
```

Des exemples détaillés avec les paramètres JSON exacts sont disponibles dans
[EXEMPLES.md](EXEMPLES.md).

---

## Architecture

Le projet tient dans un seul fichier Python d'environ 13 160 lignes.

```
impots-mcp.py        Serveur MCP et 64 outils
requirements.txt     Dépendance unique : mcp >= 1.0.0, < 2.0.0
```

Structure interne :

```
Barèmes et données fiscales (constantes de module)
Fonctions de calcul partagées
Serveur MCP et définition des outils (TOOLS)
Table de dispatch (_TOOL_DISPATCH)
Implémentations des outils (tool_*)
Point d'entrée asyncio (main)
```

Les données fiscales sont centralisées en constantes de module en tête de fichier. Les fonctions
de calcul partagées (`calculer_ir`, `calculer_parts`, `calculer_cehr`, `calculer_cdhr`,
`abattement_frais_pro`, `frais_kilometriques`, `plafond_lep`, `mpr_plafonds`) sont utilisées par
l'ensemble des outils, de manière à ce qu'une mise à jour de barème ne soit à faire qu'à un seul
endroit. Les taux sont affichés via `pct_fr`, qui lit la constante correspondante : aucun taux
n'est écrit en dur dans un texte de sortie.

Le dispatch est géré par un dictionnaire `_TOOL_DISPATCH` associant chaque nom d'outil à sa
fonction. Ajouter un outil nécessite trois modifications : la définition `Tool()` dans `TOOLS`,
une entrée dans `_TOOL_DISPATCH`, et la fonction `tool_nom(args)`.

---

## Mise à jour annuelle

Toutes les données à réviser sont des constantes de module, regroupées en tête de fichier.

| Paramètre | Constante | Fréquence |
|-----------|-----------|-----------|
| Année de référence | `ANNEE_DECLARATION` | Annuelle, pilote `ANNEE_FISCALE` et l'outil d'actualité |
| Barème IR | `TRANCHES_IR_ACTIF`, `TRANCHES_IR_2026` | Annuelle (indexation de la loi de finances) |
| Décote | `DECOTE_MAX_SEUL`, `DECOTE_MAX_COUPLE` | Annuelle (seuils dérivés) |
| Plafonds du quotient familial | `PLAFOND_DEMI_PART`, `PLAFOND_PARENT_ISOLE` | Annuelle |
| Abattement de 10% frais pro | `ABATTEMENT_FRAIS_PRO_MIN`, `_MAX` | Annuelle |
| Abattement de 10% pensions | `ABATTEMENT_PENSION_MIN`, `_MAX` | Annuelle |
| Abattement personnes âgées | `ABATT_PERSONNES_AGEES_PLEIN`, `_REDUIT` | Annuelle |
| Pension alimentaire enfant majeur | `PLAFOND_PENSION_ENFANT_MAJEUR` | Annuelle |
| Prélèvements sociaux sur le capital | `PS_CAPITAL`, `PS_IMMOBILIER`, `PS_ASSURANCE_VIE`, `PS_PENSION` | Sur modification législative |
| PFU | `PFU_IR`, `PFU_CAPITAL` | Dérivé des prélèvements sociaux |
| CDHR | `CDHR_TAUX`, `CDHR_SEUIL_SEUL`, `CDHR_SEUIL_COUPLE` | Tant que le déficit dépasse 3% du PIB |
| Grille des taux par défaut du PAS | `TAUX_NEUTRES_PAS`, `PAS_ABATTEMENT_CONTRAT_COURT` | Annuelle, publiée au BOFiP le 1er mai |
| PASS | `PASS_2026`, `PASS_ANNEE_COURANTE` | Annuelle |
| Plafonds PER | `PLAFOND_PER_MAX`, `PLAFOND_PER_MIN` | Annuelle (dérivés du PASS N-1) |
| SMIC brut annuel | `SMIC_BRUT_ANNUEL` | À chaque revalorisation |
| Taux des livrets réglementés | `TAUX_LIVRET_A`, `TAUX_LEP`, `DATE_TAUX_LIVRETS` | 1er février et 1er août |
| Plafonds LEP | `SEUIL_LEP_1_PART`, `LEP_INCREMENT_DEMI_PART` | Annuelle |
| Cotisations auto-entrepreneur | `COTISATIONS_AE_*` | Sur modification URSSAF ou Cipav |
| Seuils micro-entreprise | `SEUIL_MICRO_VENTE`, `SEUIL_MICRO_SERVICES` | Triennale (2026 à 2028) |
| Seuils de franchise TVA | `SEUIL_TVA_FRANCHISE_*` | Sur réforme |
| Facturation électronique | `FACTURATION_ELECTRONIQUE` | Sur report de calendrier |
| Barème kilométrique | `BAREME_KM_AUTO`, `BAREME_KM_MOTO`, `BAREME_KM_CYCLOMOTEUR` | Irrégulière |
| MaPrimeRénov' | `MAPRIMERENOV`, `MPR_PLAFONDS`, `MPR_INCREMENT_PAR_PERSONNE` | Annuelle |
| Retraite | `RETRAITE_SUSPENSION` | Fin de suspension au 1er janvier 2028 |
| Assurance chômage | `ARE_RUPTURE_CONVENTIONNELLE` | Sur nouvelle convention |
| Déficit foncier | `DEFICIT_FONCIER_PLAFOND` | Sur modification législative |

L'outil `verifier_actualite_fiscale` liste automatiquement tout ce qui doit être mis à jour pour
une année cible donnée, en lisant directement ces constantes.

---

## Données fiscales intégrées

| Domaine | Valeur de référence | Source |
|---------|--------------------|--------|
| Barème IR | 2026 (revenus 2025, indexation de 0,9%) | Loi n° 2026-103 du 19/02/2026, art. 4 |
| Décote | 897€ et 1 483€, seuils 1 982€ et 3 277€ | BOI-IR-LIQ-20-20-30 |
| Plafonnement du quotient familial | 1 807€ par demi-part, 4 262€ parent isolé | BOI-IR-LIQ-20-20-20 |
| Abattement de 10% frais pro | plancher 509€, plafond 14 555€ | CGI art. 83, 3° |
| Abattement de 10% pensions | plancher 454€, plafond 4 439€ par foyer | CGI art. 158-5 a |
| Abattement personnes âgées | 2 822€ jusqu'à 17 677€, 1 411€ jusqu'à 28 430€ | CGI art. 157 bis |
| Pension alimentaire enfant majeur | 6 855€ par enfant, 13 710€ si enfant marié | CGI art. 156 II-2° |
| Prélèvements sociaux du capital | 18,6% (CSG 10,6%), PFU total 31,4% | LFSS 2026, CSS art. L. 136-8 |
| Taux maintenu à 17,2% | fonciers, PV immobilières, assurance-vie, PEL, CEL, PEP | CSS art. L. 136-8, IV |
| CSG déductible | 6,8% en cas d'option pour le barème | CGI art. 154 quinquies II |
| CDHR | 20% minimum au-delà de 250 000€ ou 500 000€ | CGI art. 224, LF 2025 art. 10, LF 2026 |
| Prélèvement à la source | grille des taux par défaut au 01/05/2026, 3 zones | BOI-BAREME-000037 |
| Facturation électronique | réception au 01/09/2026, émission PME au 01/09/2027 | CGI art. 289 bis, LF 2024 art. 91 |
| Barème kilométrique | inchangé depuis 2023, majoration de 20% pour l'électrique | BOI-BAREME-000001 |
| IFI | 2026, maintenu dans son périmètre immobilier | LF 2026 |
| IS | taux stables depuis la LF 2023 | CGI art. 219 |
| PASS | 2026 : 48 060€ (2025 : 47 100€) | Arrêté du 22/12/2025 |
| SMIC | 12,31€/h depuis le 01/06/2026 | Arrêté du 22/05/2026 |
| Cotisations auto-entrepreneur | vente 12,3%, BIC 21,2%, BNC 25,6%, Cipav 23,2% | URSSAF, Cipav |
| Seuils micro-entreprise | 83 600€ et 203 100€ (exercices 2026 à 2028) | CGI art. 50-0 et 102 ter |
| Seuils de franchise TVA | 37 500€ et 85 000€ (réforme à 25 000€ abandonnée) | CGI art. 293 B |
| Barèmes donation et succession | stables | CGI art. 777 |
| LMNP | amortissements réintégrés à la plus-value, PS de 18,6% | LF 2025, CGI art. 150 VB II |
| Déficit foncier | 10 700€ (rehaussement à 21 400€ éteint au 31/12/2025) | CGI art. 156, I-3° |
| MaPrimeRénov' | barèmes et forfaits au 01/01/2026 | Guide des aides financières Anah 2026 |
| Retraite | réforme 2023 suspendue du 01/09/2026 au 01/01/2028 | LFSS 2026, circulaire Cnav |
| Assurance chômage | 15 mois après rupture conventionnelle depuis le 01/09/2026 | Avenant n° 2 du 10/04/2026, agréé le 19/06/2026 |
| Livret A et LDDS | 1,7% depuis le 01/08/2026 | Banque de France |
| LEP | 2,5% depuis le 01/08/2026, plafond de RFR 23 028€ pour 1 part | Banque de France, service-public.fr |
| Calendrier fiscal | 2026, dates officielles | impots.gouv.fr |

---

## Avertissement

Les simulations fournies sont indicatives. Elles reposent sur des approximations et des règles
fiscales générales. Pour toute décision financière ou fiscale, consultez un expert-comptable ou
un conseiller fiscal agréé.

---

## Licence

MIT, voir [LICENSE](LICENSE).
