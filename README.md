# impots-mcp: Expert fiscal français pour Claude

## Vue d'ensemble

**impots-mcp** est un serveur MCP (Model Context Protocol) qui transforme Claude en assistant fiscal
spécialisé dans la fiscalité française. Il couvre l'impôt sur le revenu, l'IS, l'IFI, les
plus-values, la crypto, la retraite, la transmission de patrimoine et la comparaison de
statuts professionnels (CDI vs freelance).

Toutes les données fiscales sont intégrées localement. Aucune requête externe n'est effectuée
pendant les calculs.

---

## Fonctionnalités

Le serveur expose **62 outils** répartis en plusieurs domaines :

**Calcul et déclaration**
- Impôt sur le revenu 2026 (barème indexé, quotient familial, décote, garde alternée)
- Prélèvement à la source : taux, modulation, acomptes
- Analyse de déclaration 2042 case par case
- Correction de déclaration : délais, majorations, prescription

**Optimisation fiscale**
- PER : plafond déductible, économie selon TMI, simulation sortie
- Frais réels vs abattement 10%
- Dons, emploi à domicile, PEA, épargne salariale (PEE, PERCO, BSPCE)
- Diagnostic 360° avec recommandations priorisées

**Statuts professionnels**
- Comparaison CDI vs auto-entrepreneur, SASU, EURL IS, portage salarial
- Calcul du net en poche après toutes charges sociales et impôts
- TJM minimum pour égaler un salaire CDI donné
- Diagnostic personnalisé passage freelance : score de maturité, analyse secteur/épargne/réseau, verdict et TJM cible

**Revenus exceptionnels et capital**
- Système du quotient (art. 163-0 A) : indemnité de licenciement, prime exceptionnelle, rappels de salaires
- PFU 30% vs barème progressif pour dividendes, intérêts et plus-values mobilières
- Calcul du seuil TMI optimal et de la case 2OP

**Immobilier locatif avancé**
- LMNP : micro-BIC (50% longue durée, 50% tourisme classé, 30% tourisme non classé) vs réel
- Amortissement plafonné au bénéfice (art. 39 C II) et réintégré à la plus-value de revente (LF 2025)
- Micro-foncier vs réel : déficit foncier, imputation sur revenu global (10 700€), reports
- Loc'Avantages (art. 199 tricies) : réduction 15%/35%/65% via convention ANAH

**Rénovation énergétique**
- MaPrimeRénov' : forfaits du parcours par geste selon la catégorie de ressources
- Barèmes de ressources distincts Île-de-France / reste du territoire, indexés sur le nombre de personnes
- Rénovation d'ampleur : taux, plafonds de dépenses, écrêtement, Mon Accompagnateur Rénov'

**Retraite**
- Rachat de trimestres : coût net d'impôt, gain de pension, break-even en mois

**Expatriation**
- Exit tax (art. 167 bis) : PV latentes, sursis automatique UE/EEE, stratégies avant départ

**Société et dirigeant**
- Impôt sur les sociétés (15% / 25%, acomptes, déficit)
- Optimisation rémunération vs dividendes (SASU / EURL / SARL IS)
- SASU, SCI, holding, pacte Dutreil, cession d'entreprise

**Patrimoine et transmission**
- IFI : barème, abattements, plafonnement, stratégies
- Droits de donation et succession par lien de parenté
- Plus-values mobilières et immobilières (abattements durée, frais)
- Assurance-vie, démembrement, SCPI, PEA, réversion de pension

**Indépendants et entreprises**
- Auto-entrepreneur : seuils, cotisations, VFL, ACRE
- TNS : micro vs réel, Madelin, régimes BNC/BIC
- TVA : franchise, réel simplifié, taux, intracommunautaire
- CFE : cotisation par tranche de CA, exonérations

**Crypto-monnaies**
- Méthode PAMC officielle (formulaire 2086)
- Plus-values, moins-values reportables, staking, mining, NFT

**Fiscalité internationale**
- Résidence fiscale, formulaire 2047, conventions (13 pays)
- Frontaliers Suisse / Luxembourg / Belgique / Allemagne
- DOM-TOM : abattements, Girardin, Pinel outre-mer

**Actualité fiscale**
- Vérification que les barèmes sont à jour pour une année donnée
- Liste complète des paramètres à mettre à jour lors d'un changement d'année
- Procédure de mise à jour vers 2027, 2028...

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

- Linux / Mac : `~/.config/claude/claude_desktop_config.json`
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
"Calcule mon impôt, je suis marié avec 2 enfants et 65 000€ de revenus nets"
→ Impôt net : 2 530€ — TMI : 11% — Taux moyen : 4.2%

"Combien j'économise si je verse 8 000€ sur mon PER ? Je suis célibataire à 58 000€."
→ Économie : 1 740€ — Coût réel : 4 060€ — Plafond applicable : 5 800€

"Je suis en CDI à 60k brut. Est-ce intéressant de passer freelance à 500€/jour ?"
→ CDI net : 41 122€ — SASU net : 54 529€ — TJM min SASU : 284€/j

"J'ai vendu des cryptos pour 15 000€, portefeuille valait 50 000€, PAMC 30 000€"
→ PV : 6 000€ — PFU 30% : 1 800€ — Déclaration formulaire 2086 obligatoire

"Quand puis-je partir à la retraite taux plein ? 55 ans, 140 trimestres, 50k brut."
→ Taux plein légal : 67 ans — Départ 64 ans : décote 18.75%

"Les barèmes sont-ils à jour pour 2027 ?"
→ Mise à jour requise — liste des paramètres à modifier fournie

"J'ai reçu 40 000€ d'indemnité de licenciement supra-légale, je gagne 55 000€/an"
→ Sans quotient : 13 067€ | Avec quotient N=4 : 12 000€ | Economie : 1 067€ — cochez la case 2042C

"Dois-je opter pour le barème sur mes 10 000€ de dividendes ? TMI 11%"
→ Barème : 2 679€ | PFU : 3 000€ | Economie barème : 321€ — cochez la case 2OP

"Je loue un meublé 12 000€/an, bien à 180 000€, charges 6 400€ — micro ou réel ?"
→ Micro-BIC : 1 032€ de taxes | Réel : 0€ (amortissement absorbe le bénéfice) — Réel recommandé

"Racheter 4 trimestres à 50 ans pour ma retraite, salaire 55 000€ brut"
→ Coût brut : 57 496€ | Economie TMI 30% : 17 249€ | Coût net : 40 247€ | Break-even : à calculer

"Je pars m'installer en Allemagne avec 1,2M€ de PV latentes sur mes actions"
→ Exit tax : ~360 000€ | Départ UE → sursis automatique de paiement

"Je suis dev senior à 65k brut, 8 ans d'expérience, 20k d'épargne, pas encore de clients"
→ Score : 7/12 — Envisageable | TJM min SASU : 298€/j | TJM recommandé : 343€/j | Alerte : constituer 6 mois d'épargne, identifier 1-2 prospects avant de démissionner
```

Des exemples détaillés avec les paramètres JSON exacts sont disponibles dans [EXEMPLES.md](EXEMPLES.md).

---

## Architecture

Le projet tient dans un seul fichier Python de ~12 300 lignes.

```
impots-mcp.py        Script principal — serveur MCP + 62 outils
requirements.txt     Dépendance unique : mcp >= 1.0.0, < 2.0.0
```

Structure interne :

```
Barèmes et données fiscales           lignes    1 –  910
Fonctions de calcul internes          lignes  910 – 1165
Serveur MCP + définition des outils (TOOLS[])
Dispatch table (_TOOL_DISPATCH)
Implémentations des outils (tool_*)
Point d'entrée asyncio (main)
```

Les données fiscales sont centralisées en constantes de module en tête de fichier. Les fonctions
de calcul partagées (`calculer_ir`, `calculer_parts`, `abattement_frais_pro`,
`frais_kilometriques`, `plafond_lep`, `mpr_plafonds`) sont utilisées par l'ensemble des outils,
de manière à ce qu'une mise à jour de barème ne soit à faire qu'à un seul endroit.

Le dispatch est géré par un dictionnaire `_TOOL_DISPATCH` associant chaque nom d'outil à sa
fonction. Ajouter un outil nécessite trois modifications : la définition `Tool()` dans `TOOLS`,
une entrée dans `_TOOL_DISPATCH`, et la fonction `tool_nom(args)`.

---

## Mise à jour annuelle

Toutes les données à réviser sont des constantes de module, regroupées en tête de fichier.
Aucune valeur fiscale n'est écrite en dur dans le corps des outils.

| Paramètre | Constante | Fréquence |
|-----------|-----------|-----------|
| Année de référence | `ANNEE_DECLARATION` | Annuelle — pilote `ANNEE_FISCALE` et l'outil d'actualité |
| Barème IR | `TRANCHES_IR_ACTIF`, `TRANCHES_IR_2026` | Annuelle (indexation LFI) |
| Décote | `DECOTE_MAX_SEUL`, `DECOTE_MAX_COUPLE` | Annuelle (seuils dérivés) |
| Plafonds du quotient familial | `PLAFOND_DEMI_PART`, `PLAFOND_PARENT_ISOLE` | Annuelle |
| Abattement 10% frais pro | `ABATTEMENT_FRAIS_PRO_MIN`, `_MAX` | Annuelle |
| PASS | `PASS_2026`, `PASS_ANNEE_COURANTE` | Annuelle |
| Plafonds PER | `PLAFOND_PER_MAX_2025`, `_MIN` | Annuelle (dérivés du PASS N-1) |
| SMIC brut annuel | `SMIC_BRUT_ANNUEL` | À chaque revalorisation |
| Taux des livrets réglementés | `TAUX_LIVRET_A`, `TAUX_LEP`, `DATE_TAUX_LIVRETS` | 1er février et 1er août |
| Plafonds LEP | `SEUIL_LEP_1_PART`, `LEP_INCREMENT_DEMI_PART` | Annuelle |
| Cotisations auto-entrepreneur | `COTISATIONS_AE_*` | Sur modification URSSAF / Cipav |
| Seuils micro-entreprise | `SEUIL_MICRO_VENTE`, `SEUIL_MICRO_SERVICES` | Triennale (2026-2028) |
| Seuils de franchise TVA | `SEUIL_TVA_FRANCHISE_*` | Sur réforme |
| Barème kilométrique | `BAREME_KM_AUTO`, `BAREME_KM_MOTO`, `BAREME_KM_CYCLOMOTEUR` | Irrégulière |
| MaPrimeRénov' | `MAPRIMERENOV`, `MPR_PLAFONDS`, `MPR_INCREMENT_PAR_PERSONNE` | Annuelle |
| Déficit foncier | `DEFICIT_FONCIER_PLAFOND` | Sur modification législative |

L'outil `verifier_actualite_fiscale` liste automatiquement tout ce qui doit être mis à jour
pour une année cible donnée, en lisant directement ces constantes.

---

## Données fiscales intégrées

| Domaine | Valeur de référence | Source |
|---------|--------------------|--------|
| Barème IR | 2026 (revenus 2025, indexation +0,9%) | Loi n° 2026-103 du 19/02/2026, art. 4 |
| Décote | 897€ / 1 483€ — seuils 1 982€ / 3 277€ | BOI-IR-LIQ-20-20-30 |
| Plafonnement du quotient familial | 1 807€ par demi-part — 4 262€ parent isolé | BOI-IR-LIQ-20-20-20 |
| Abattement 10% frais pro | plancher 509€, plafond 14 555€ | CGI art. 83, 3° |
| Barème kilométrique | inchangé depuis 2023, majoration 20% électrique | BOI-BAREME-000001 |
| IFI | 2026 | LFI 2026 |
| IS | Taux stables depuis LF 2023 | CGI art. 219 |
| PASS | 2026 : 48 060€ (2025 : 47 100€) | Arrêté du 22/12/2025 |
| SMIC | 12,31€/h depuis le 01/06/2026 | Arrêté du 22/05/2026 |
| Cotisations auto-entrepreneur | vente 12,3% / BIC 21,2% / BNC 25,6% / Cipav 23,2% | URSSAF, Cipav |
| Seuils micro-entreprise | 83 600€ / 203 100€ (exercices 2026-2028) | CGI art. 50-0 et 102 ter |
| Seuils de franchise TVA | 37 500€ / 85 000€ (réforme à 25 000€ abandonnée) | CGI art. 293 B |
| Barèmes donation/succession | Stables | CGI art. 777 |
| LMNP | Amortissements réintégrés à la plus-value | LF 2025, CGI art. 150 VB II |
| Déficit foncier | 10 700€ (rehaussement à 21 400€ éteint au 31/12/2025) | CGI art. 156, I-3° |
| MaPrimeRénov' | Barèmes et forfaits au 01/01/2026 | Guide des aides financières Anah 2026 |
| Livret A / LDDS | 1,7% depuis le 01/08/2026 | Banque de France |
| LEP | 2,5% depuis le 01/08/2026 — plafond 23 028€ pour 1 part | Banque de France / service-public.fr |
| Calendrier fiscal | 2026 (dates officielles) | impots.gouv.fr |

---

## Avertissement

Les simulations fournies sont indicatives. Elles sont basées sur des approximations et des
règles fiscales générales. Pour toute décision financière ou fiscale, consultez un expert-comptable
ou un conseiller fiscal agréé.

---

## Licence

MIT — voir [LICENSE](LICENSE).
