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

Le serveur expose **61 outils** répartis en plusieurs domaines :

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

**Revenus exceptionnels et capital**
- Système du quotient (art. 163-0 A) : indemnité de licenciement, prime exceptionnelle, rappels de salaires
- PFU 30% vs barème progressif pour dividendes, intérêts et plus-values mobilières
- Calcul du seuil TMI optimal et de la case 2OP

**Immobilier locatif avancé**
- LMNP : simulation micro-BIC (50%/71%) vs réel avec amortissement bâtiment et mobilier
- Micro-foncier vs réel : déficit foncier, imputation sur revenu global (10 700€), reports
- Loc'Avantages (art. 199 tricies) : réduction 15%/35%/65% via convention ANAH

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
→ Micro-BIC : 1 032€ de taxes | Réel : 0€ (déficit amortissements) — Réel recommandé

"Racheter 4 trimestres à 50 ans pour ma retraite, salaire 55 000€ brut"
→ Coût brut : 57 496€ | Economie TMI 30% : 17 249€ | Coût net : 40 247€ | Break-even : à calculer

"Je pars m'installer en Allemagne avec 1,2M€ de PV latentes sur mes actions"
→ Exit tax : ~360 000€ | Départ UE → sursis automatique de paiement
```

Des exemples détaillés avec les paramètres JSON exacts sont disponibles dans [EXEMPLES.md](EXEMPLES.md).

---

## Architecture

Le projet tient dans un seul fichier Python de ~11 400 lignes.

```
impots-mcp.py        Script principal — serveur MCP + 54 outils
requirements.txt     Dépendance unique : mcp >= 1.0.0
```

Structure interne :

```
Barèmes et données fiscales   lignes   1 – 800
Fonctions de calcul internes  lignes 800 – 950
Serveur MCP + définition des outils (TOOLS[])
Dispatch table (_TOOL_DISPATCH)
Implémentations des outils (tool_*)
Point d'entrée asyncio (main)
```

Le dispatch est géré par un dictionnaire `_TOOL_DISPATCH` associant chaque nom d'outil à sa
fonction. Ajouter un outil nécessite trois modifications : la définition `Tool()` dans `TOOLS`,
une entrée dans `_TOOL_DISPATCH`, et la fonction `tool_nom(args)`.

---

## Mise à jour annuelle

Chaque année fiscale, les éléments suivants doivent être vérifiés et mis à jour :

| Paramètre | Variable | Fréquence |
|-----------|----------|-----------|
| Barème IR | `TRANCHES_IR_ACTIF` | Annuelle (indexation ~1.8%) |
| Plafond PER | `PLAFOND_PER_MAX_*` | Annuelle (10% × 8 PASS) |
| Seuils AE | dans `tool_guide_auto_entrepreneur` | Biennale |
| SMIC brut | dans `tool_comparer_statuts_professionnel` | Annuelle |
| Taux cotisations TNS | dans les tools TNS/AE | Sur modification URSSAF |
| `ANNEE_FISCALE` | constante | Annuelle |
| `annee_actuelle_mcp` | dans `tool_verifier_actualite_fiscale` | Annuelle |

L'outil `verifier_actualite_fiscale` liste automatiquement tout ce qui doit être mis à jour
pour une année cible donnée.

---

## Données fiscales intégrées

| Domaine | Année de référence | Source |
|---------|-------------------|--------|
| Barème IR | 2026 (revenus 2025) | Loi de finances 2026 |
| IFI | 2026 | LFI 2026 |
| IS | 2025 (taux stables LF2023) | CGI art. 219 |
| Cotisations AE | 2025 | URSSAF |
| PASS | 2025 (46 368€) | Arrêté SS |
| Seuils TVA franchise | 2025 | LF 2025 |
| Barèmes donation/succession | 2024 (stables) | CGI art. 777 |
| MaPrimeRénov' | 2025 | Arrêté ADEME |
| Calendrier fiscal | 2026 | impots.gouv.fr |

---

## Avertissement

Les simulations fournies sont indicatives. Elles sont basées sur des approximations et des
règles fiscales générales. Pour toute décision financière ou fiscale, consultez un expert-comptable
ou un conseiller fiscal agréé.

---

## Licence

MIT — voir [LICENSE](LICENSE).
