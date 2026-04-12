#!/usr/bin/env python3
"""
MCP Impôts Français - Expert en optimisation fiscale pour particuliers et professionnels
Spécialiste de l'impôt sur le revenu, IS, IFI, PER, cryptomonnaies,
épargne salariale, transmission d'entreprise et SCI.

Version : 2.8.0
Données : Barème IR 2026 +0,9% (revenus 2025, LFI n°2026-103 du 19/02/2026),
          IFI 2026, PER 2026, IS 2025, Calendrier 2026 (dates officielles),
          Livret A/LDDS 1,5% / LEP 2,5% (depuis 01/02/2026),
          CEHR, Droits de donation/succession, SCPI, Crypto 2086,
          Retraite (réforme 2023), Fiscalité agricole, Outre-mer DOM-TOM
"""

__version__ = "2.8.0"

import json
import sys
import logging
from typing import Any, Dict, List, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Erreur: bibliothèque MCP non installée.")
    print("Installez avec: pip install mcp")
    sys.exit(1)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("impots-mcp")

# ─── Barèmes et données fiscales 2025 (revenus 2024) ─────────────────────────

TRANCHES_IR_2025 = [
    {"min": 0,       "max": 11_497,  "taux": 0.00},
    {"min": 11_497,  "max": 29_315,  "taux": 0.11},
    {"min": 29_315,  "max": 83_823,  "taux": 0.30},
    {"min": 83_823,  "max": 180_294, "taux": 0.41},
    {"min": 180_294, "max": None,    "taux": 0.45},
]

# Barème IR 2026 (revenus 2025, déclaration printemps 2026) — indexé +0,9%
# Source : Loi n° 2026-103 du 19 février 2026 de finances pour 2026, art. 4
# Confirmé BOFiP ACTU-2026-00022 du 07/04/2026
TRANCHES_IR_2026 = [
    {"min": 0,       "max": 11_600,  "taux": 0.00},
    {"min": 11_600,  "max": 29_579,  "taux": 0.11},
    {"min": 29_579,  "max": 84_577,  "taux": 0.30},
    {"min": 84_577,  "max": 181_917, "taux": 0.41},
    {"min": 181_917, "max": None,    "taux": 0.45},
]

# Barème actif (2026 = revenus 2025)
TRANCHES_IR_ACTIF = TRANCHES_IR_2026
ANNEE_FISCALE = "2026 (revenus 2025)"

# Plafond de la réduction du quotient familial par demi-part
PLAFOND_DEMI_PART = 1_807  # 2026, euros par demi-part supplémentaire (LFI 2026 +0,9%)

# Plafond PER déductible (10% des revenus professionnels nets)
PLAFOND_PER_POURCENTAGE = 0.10
PLAFOND_PER_MAX_2025 = 35_194  # 10% de 8 PASS 2024 (historique)
PLAFOND_PER_MAX_2025 = 37_094  # 10% de 8 PASS 2025 — utilisé pour déclaration 2026
PLAFOND_PER_MIN_2025 = 4_637   # 10% du PASS 2025 (plancher)

# Crédits d'impôt principaux 2025
CREDITS_IMPOT = {
    "garde_enfant_hors_domicile": {
        "nom": "Garde d'enfants hors domicile (crèche, assistante maternelle)",
        "taux": 0.50,
        "plafond_depenses": 3_500,
        "credit_max": 1_750,
        "conditions": "Enfant de moins de 6 ans au 1er janvier de l'année d'imposition",
        "article": "Art. 200 quater B CGI",
    },
    "emploi_domicile": {
        "nom": "Emploi à domicile (ménage, jardinage, soutien scolaire...)",
        "taux": 0.50,
        "plafond_depenses": 12_000,  # de base, +1500 par enfant/personne dép.
        "credit_max": 6_000,
        "conditions": "Dépenses pour services à domicile. Plafond augmenté selon situation.",
        "article": "Art. 199 sexdecies CGI",
    },
    "prime_activite": {
        "nom": "Prime d'activité (versée par CAF, non imposable)",
        "taux": None,
        "plafond_depenses": None,
        "credit_max": None,
        "conditions": "Revenus d'activité modestes - faire simulation sur caf.fr",
        "article": "Art. L842-1 CSS",
    },
    "transition_energetique": {
        "nom": "MaPrimeRénov' (ex-CITE) - Travaux d'isolation, chaudière...",
        "taux": "variable",
        "plafond_depenses": None,
        "credit_max": "variable selon revenus et travaux",
        "conditions": "Résidence principale, entreprise RGE. Remplacé par MaPrimeRénov' depuis 2021.",
        "article": "maprimerenov.gouv.fr",
    },
    "formation_dirigeant": {
        "nom": "Crédit formation du chef d'entreprise",
        "taux": 1.00,
        "plafond_depenses": None,
        "credit_max": "SMIC horaire x heures de formation",
        "conditions": "Chef d'entreprise en formation professionnelle",
        "article": "Art. 244 quater M CGI",
    },
}

# Réductions d'impôt principales 2025
REDUCTIONS_IMPOT = {
    "dons_organismes": {
        "nom": "Dons aux associations (Croix-Rouge, Restos du Cœur...)",
        "taux": 0.75,  # jusqu'à 1000€ de dons
        "taux2": 0.66,  # au-delà de 1000€
        "plafond_revenu": 0.20,  # 20% du revenu imposable
        "don_max_75pct": 1_000,
        "conditions": "Dons aux organismes d'aide aux personnes en difficulté (75%). Autres organismes : 66%.",
        "article": "Art. 200 CGI",
    },
    "dons_partis_politiques": {
        "nom": "Dons aux partis politiques",
        "taux": 0.66,
        "plafond_depenses": 7_500,
        "conditions": "66% du don dans la limite de 20% du revenu imposable",
        "article": "Art. 200 CGI",
    },
    "investissement_pme": {
        "nom": "Investissement au capital de PME (IR-PME / Madelin)",
        "taux": 0.18,
        "plafond_depenses_celibataire": 50_000,
        "plafond_depenses_couple": 100_000,
        "conditions": "Souscription au capital de PME non cotées. Report possible 5 ans.",
        "article": "Art. 199 terdecies-0 A CGI",
    },
    "sofica": {
        "nom": "SOFICA (financement cinéma français)",
        "taux": 0.30,  # ou 36% selon SOFICA
        "plafond": "25% du revenu net global, max 18 000€",
        "conditions": "Investissement dans des sociétés de financement du cinéma",
        "article": "Art. 199 unvicies CGI",
    },
    "pinel": {
        "nom": "Dispositif Pinel (investissement locatif neuf) - TERMINÉ 2024",
        "taux": "9% à 21% selon durée (6, 9 ou 12 ans)",
        "plafond_depenses": 300_000,
        "conditions": "ATTENTION: Le Pinel a pris fin le 31/12/2024. Plus de nouveaux investissements possibles.",
        "article": "Art. 199 novovicies CGI",
    },
    "monuments_historiques": {
        "nom": "Monuments Historiques (déficit foncier illimité)",
        "taux": "Déduction 100% des charges sur revenu global",
        "conditions": "Propriétaire d'un immeuble classé ou inscrit MH avec charges déductibles",
        "article": "Art. 156 CGI",
    },
}

# Dispositifs d'épargne défiscalisante
EPARGNE_FISCALE = {
    "PER": {
        "nom": "Plan d'Épargne Retraite (PER individuel)",
        "avantage": "Versements déductibles du revenu imposable",
        "plafond_2024": "10% des revenus professionnels nets (max 35 194€) ou 10% du PASS (4 637€)",
        "sortie": "Capital ou rente à la retraite (fiscalisé). Sortie en capital possible (cas exceptionnels).",
        "remarque": "Économie d'impôt = versement × taux marginal d'imposition",
        "article": "Art. L224-1 Code monétaire",
    },
    "PEA": {
        "nom": "Plan d'Épargne en Actions (PEA)",
        "avantage": "Exonération d'IR sur les plus-values et dividendes après 5 ans",
        "plafond": "150 000€ (PEA classique) + 75 000€ (PEA-PME)",
        "sortie": "Prélèvements sociaux 17,2% uniquement après 5 ans",
        "article": "Art. 163 quinquies D CGI",
    },
    "assurance_vie": {
        "nom": "Assurance-vie",
        "avantage": "Abattement annuel sur les gains après 8 ans (4 600€ célibataire / 9 200€ couple)",
        "plafond": "Pas de plafond de versement",
        "sortie": "Fiscalité avantageuse après 8 ans. Transmission hors succession (152 500€/bénéficiaire).",
        "article": "Art. 990 I CGI",
    },
    "LEP": {
        "nom": "Livret d'Épargne Populaire (LEP)",
        "avantage": "Intérêts exonérés d'impôt ET de prélèvements sociaux. Taux : 2,5% (depuis 01/02/2026)",
        "plafond": "10 000€",
        "conditions": "Sous conditions de revenus (RFR ≤ 23 028€ pour 1 part en 2026)",
        "article": "Art. L221-13 Code monétaire",
    },
    "livret_A": {
        "nom": "Livret A",
        "avantage": "Intérêts exonérés d'impôt ET de prélèvements sociaux. Taux : 1,5% (depuis 01/02/2026)",
        "plafond": "22 950€",
        "article": "Art. L221-1 Code monétaire",
    },
    "LDDS": {
        "nom": "Livret de Développement Durable et Solidaire (LDDS)",
        "avantage": "Intérêts exonérés. Taux : 1,5% (depuis 01/02/2026)",
        "plafond": "12 000€",
        "article": "Art. L221-27 Code monétaire",
    },
}

# Déductions du revenu imposable
DEDUCTIONS_REVENU = {
    "abattement_10pct": {
        "nom": "Abattement forfaitaire 10% frais professionnels",
        "description": "Appliqué automatiquement sur les salaires. Min 495€, max 14 426€ par personne.",
        "avantage": "Automatique - pas de justificatif requis",
    },
    "frais_reels": {
        "nom": "Déduction des frais réels professionnels",
        "description": "Alternative à l'abattement 10%. Déduire les frais réels (transport, repas, formation...).",
        "avantage": "Avantageux si frais > 10% du salaire brut",
        "exemples": [
            "Frais kilométriques (barème fiscal)",
            "Repas au bureau (si éloignement)",
            "Formation professionnelle",
            "Tenue de travail spécifique",
            "Double résidence (si justifiée)",
        ],
    },
    "pension_alimentaire": {
        "nom": "Pensions alimentaires versées",
        "description": "Déductibles si versées à ascendants/descendants dans le besoin ou ex-conjoint (fixée par jugement).",
        "plafond_enfant_majeur": 6_368,  # par enfant en 2024
        "article": "Art. 156 II CGI",
    },
    "per_versements": {
        "nom": "Versements PER déductibles",
        "description": "Voir dispositif PER - déductibles du revenu global",
    },
    "monuments_historiques_def": {
        "nom": "Déficit foncier Monuments Historiques",
        "description": "Imputation illimitée sur le revenu global",
    },
    "deficit_foncier": {
        "nom": "Déficit foncier (revenus fonciers)",
        "description": "Le déficit foncier hors intérêts d'emprunt est déductible du revenu global à hauteur de 10 700€/an.",
        "plafond_annuel": 10_700,
        "article": "Art. 156 I 3° CGI",
    },
    "csg_deductible": {
        "nom": "CSG déductible",
        "description": "6,8% de la CSG payée sur revenus du patrimoine est déductible du revenu imposable de l'année suivante.",
        "taux_deductible": 0.068,
    },
}

# Calendrier fiscal 2025
# Données MaPrimeRénov' 2025
MAPRIMERENOV = {
    "categories": {
        "bleu": {
            "label": "MaPrimeRénov' Bleu (très modestes)",
            "rfr_max_1part": 17_009,
            "taux_isolation": 0.70,
            "taux_chaudiere_bois": 0.50,
            "taux_pompe_chaleur": 0.70,
            "taux_fenetres": 0.40,
            "couleur": "Bleu",
        },
        "jaune": {
            "label": "MaPrimeRénov' Jaune (modestes)",
            "rfr_max_1part": 21_805,
            "taux_isolation": 0.60,
            "taux_chaudiere_bois": 0.40,
            "taux_pompe_chaleur": 0.50,
            "taux_fenetres": 0.30,
            "couleur": "Jaune",
        },
        "violet": {
            "label": "MaPrimeRénov' Violet (intermédiaires)",
            "rfr_max_1part": 30_549,
            "taux_isolation": 0.40,
            "taux_chaudiere_bois": 0.30,
            "taux_pompe_chaleur": 0.30,
            "taux_fenetres": 0.15,
            "couleur": "Violet",
        },
        "rose": {
            "label": "MaPrimeRénov' Rose (supérieurs)",
            "rfr_max_1part": None,  # Tous les autres
            "taux_isolation": 0.20,
            "taux_chaudiere_bois": 0.15,
            "taux_pompe_chaleur": 0.20,
            "taux_fenetres": 0.00,
            "couleur": "Rose",
        },
    },
    "travaux": {
        "isolation_combles": {
            "nom": "Isolation des combles perdus / toiture",
            "description": "Isolation thermique des combles ou de la toiture",
            "cout_moyen_m2": 30,
            "plafond_aide_m2": 25,
        },
        "isolation_murs": {
            "nom": "Isolation des murs (ITI ou ITE)",
            "description": "Isolation des murs par l'intérieur ou l'extérieur",
            "cout_moyen_m2": 80,
            "plafond_aide_m2": 75,
        },
        "isolation_plancher": {
            "nom": "Isolation du plancher bas",
            "description": "Isolation du sol / plancher bas",
            "cout_moyen_m2": 20,
            "plafond_aide_m2": 7,
        },
        "pompe_chaleur_air_eau": {
            "nom": "Pompe à chaleur air/eau",
            "description": "Remplacement chaudière fioul/gaz par PAC air/eau",
            "cout_moyen": 12_000,
            "plafond_aide": 10_000,
        },
        "pompe_chaleur_geothermique": {
            "nom": "Pompe à chaleur géothermique",
            "description": "PAC eau/eau ou sol/eau",
            "cout_moyen": 18_000,
            "plafond_aide": 12_000,
        },
        "chaudiere_bois": {
            "nom": "Chaudière à granulés ou à bûches",
            "description": "Chaudière biomasse haute performance",
            "cout_moyen": 15_000,
            "plafond_aide": 12_000,
        },
        "poele_granules": {
            "nom": "Poêle à granulés / insert bois",
            "description": "Appareil de chauffage au bois performant",
            "cout_moyen": 4_000,
            "plafond_aide": 2_500,
        },
        "vmc_double_flux": {
            "nom": "VMC double flux",
            "description": "Ventilation mécanique contrôlée double flux",
            "cout_moyen": 5_000,
            "plafond_aide": 2_500,
        },
        "fenetres": {
            "nom": "Fenêtres / double vitrage",
            "description": "Remplacement fenêtres simple vitrage par double vitrage",
            "cout_moyen_unite": 800,
            "plafond_aide_unite": 100,
            "note": "Aide uniquement pour ménages bleus/jaunes/violets",
        },
        "audit_energetique": {
            "nom": "Audit énergétique",
            "description": "Audit obligatoire pour MaPrimeRénov' Parcours accompagné",
            "cout_moyen": 700,
            "plafond_aide": 500,
        },
    },
    "bonus_sortie_passoire": 1_500,  # Bonus si on sort du statut F/G
    "note": "Les montants sont indicatifs. Simuler sur maprimerenov.gouv.fr",
}

# Seuils de revenus MaPrimeRénov' 2025 pour différentes tailles de foyer
MPR_SEUILS_2025 = {
    # (nb_parts) : (bleu_max, jaune_max, violet_max)
    1: (17_009, 21_805, 30_549),
    1.5: (19_255, 24_701, 34_595),
    2: (21_502, 27_596, 38_641),
    2.5: (23_734, 30_490, 42_687),
    3: (25_982, 33_399, 46_733),
    3.5: (28_214, 36_293, 50_779),
    4: (30_461, 39_188, 54_826),
    4.5: (32_693, 42_082, 58_872),
    5: (34_940, 44_977, 62_918),
}

CALENDRIER_FISCAL_2026 = [
    {
        "date": "9 avril 2026",
        "evenement": "Ouverture de la déclaration de revenus 2025 en ligne (impots.gouv.fr)",
        "important": True,
    },
    {
        "date": "19 mai 2026",
        "evenement": "Date limite déclaration papier (cachet La Poste faisant foi, 23h59)",
        "important": True,
    },
    {
        "date": "21 mai 2026",
        "evenement": "Date limite déclaration en ligne — Zone 1 (dép. 01 à 19 + non-résidents) — 23h59",
        "important": True,
    },
    {
        "date": "28 mai 2026",
        "evenement": "Date limite déclaration en ligne — Zone 2 (dép. 20 à 54) — 23h59",
        "important": True,
    },
    {
        "date": "4 juin 2026",
        "evenement": "Date limite déclaration en ligne — Zone 3 (dép. 55 à 974 et 976) — 23h59",
        "important": True,
    },
    {
        "date": "Juillet-Août 2026",
        "evenement": "Envoi des avis d'imposition (revenus 2025)",
        "important": False,
    },
    {
        "date": "15 septembre 2026",
        "evenement": "Date limite paiement solde IR si avis > 300€ (non-mensuel)",
        "important": True,
    },
    {
        "date": "15 octobre 2026",
        "evenement": "Acompte prélèvement à la source sur revenus fonciers/BNC/BIC (si applicable)",
        "important": False,
    },
    {
        "date": "31 décembre 2026",
        "evenement": "⚡ DEADLINE : versements PER, dons, souscriptions PME — économies d'impôt 2026",
        "important": True,
    },
    {
        "date": "1er janvier 2027",
        "evenement": "Vérifier éligibilité LEP, nouveaux plafonds Livret A / LDDS",
        "important": False,
    },
]
# Alias pour compatibilité
CALENDRIER_FISCAL_2025 = CALENDRIER_FISCAL_2026

# ─── Barème IFI 2026 ─────────────────────────────────────────────────────────

BAREME_IFI = [
    {"min": 0,          "max": 800_000,    "taux": 0.000},
    {"min": 800_000,    "max": 1_300_000,  "taux": 0.005},
    {"min": 1_300_000,  "max": 2_570_000,  "taux": 0.007},
    {"min": 2_570_000,  "max": 5_000_000,  "taux": 0.010},
    {"min": 5_000_000,  "max": 10_000_000, "taux": 0.0125},
    {"min": 10_000_000, "max": None,       "taux": 0.015},
]
IFI_SEUIL_ENTREE = 1_300_000
IFI_ABATTEMENT_RP = 0.30  # 30% sur résidence principale

# ─── CEHR — Contribution Exceptionnelle sur les Hauts Revenus ────────────────
CEHR_BAREME = {
    "seul": [   # célibataire, divorcé, veuf
        {"min": 250_000, "max": 500_000, "taux": 0.03},
        {"min": 500_000, "max": None,    "taux": 0.04},
    ],
    "couple": [ # marié, pacsé
        {"min": 500_000, "max": 1_000_000, "taux": 0.03},
        {"min": 1_000_000, "max": None,    "taux": 0.04},
    ],
}

# ─── Droits de donation et succession ────────────────────────────────────────

BAREME_DROITS = {
    "ligne_directe": [
        {"min": 0,          "max": 8_072,      "taux": 0.05},
        {"min": 8_072,      "max": 12_109,     "taux": 0.10},
        {"min": 12_109,     "max": 15_932,     "taux": 0.15},
        {"min": 15_932,     "max": 552_324,    "taux": 0.20},
        {"min": 552_324,    "max": 902_838,    "taux": 0.30},
        {"min": 902_838,    "max": 1_805_677,  "taux": 0.40},
        {"min": 1_805_677,  "max": None,       "taux": 0.45},
    ],
    "conjoint_donation": [
        {"min": 0,         "max": 8_072,     "taux": 0.05},
        {"min": 8_072,     "max": 15_932,    "taux": 0.10},
        {"min": 15_932,    "max": 31_865,    "taux": 0.15},
        {"min": 31_865,    "max": 552_324,   "taux": 0.20},
        {"min": 552_324,   "max": 902_838,   "taux": 0.30},
        {"min": 902_838,   "max": 1_805_677, "taux": 0.40},
        {"min": 1_805_677, "max": None,      "taux": 0.45},
    ],
    "frere_soeur": [
        {"min": 0,      "max": 24_430, "taux": 0.35},
        {"min": 24_430, "max": None,   "taux": 0.45},
    ],
    "neveu_niece":  [{"min": 0, "max": None, "taux": 0.55}],
    "autre":        [{"min": 0, "max": None, "taux": 0.60}],
}

ABATTEMENTS_DONATIONS = {
    "enfant_parent":  {"label": "Enfant ↔ Parent",         "montant": 100_000, "bareme": "ligne_directe",    "periodicite": 15},
    "petit_enfant":   {"label": "Petit-enfant",             "montant": 31_865,  "bareme": "ligne_directe",    "periodicite": 15},
    "arriere_petit_enfant": {"label": "Arrière-petit-enfant", "montant": 5_310, "bareme": "ligne_directe",    "periodicite": 15},
    "conjoint_pacs":  {"label": "Conjoint / PACS",          "montant": 80_724,  "bareme": "conjoint_donation","periodicite": 15},
    "frere_soeur":    {"label": "Frère / Sœur",             "montant": 15_932,  "bareme": "frere_soeur",      "periodicite": 15},
    "neveu_niece":    {"label": "Neveu / Nièce",            "montant": 7_967,   "bareme": "neveu_niece",      "periodicite": 15},
    "autre":          {"label": "Autre (non-parent)",        "montant": 1_594,   "bareme": "autre",            "periodicite": 15},
}

# Don exceptionnel de somme d'argent (Pacte Dutreil simplifié)
DON_ARGENT_EXONERE = {
    "montant": 31_865,
    "conditions": "Donateur < 80 ans, bénéficiaire majeur (enfant, petit-enfant, neveu/nièce). Tous les 15 ans.",
}

ABATTEMENTS_SUCCESSION = {
    "conjoint_pacs":  {"label": "Conjoint / PACS (survivant)", "montant": None,    "bareme": None,          "note": "EXONÉRÉ totalement"},
    "enfant":         {"label": "Enfant",                      "montant": 100_000, "bareme": "ligne_directe","periodicite": None},
    "petit_enfant":   {"label": "Petit-enfant (par représentation)", "montant": 1_594, "bareme": "ligne_directe", "periodicite": None},
    "frere_soeur":    {"label": "Frère / Sœur",                "montant": 15_932,  "bareme": "frere_soeur",  "periodicite": None, "exo_conditions": "Exonéré si célibataire/veuf/divorcé, vivant avec le défunt depuis 5 ans"},
    "neveu_niece":    {"label": "Neveu / Nièce",               "montant": 7_967,   "bareme": "neveu_niece",  "periodicite": None},
    "autre":          {"label": "Autre",                       "montant": 1_594,   "bareme": "autre",        "periodicite": None},
    "handicape":      {"label": "Personne handicapée (supplément)", "montant": 159_325, "bareme": None,      "periodicite": None, "note": "Abattement supplémentaire cumulable"},
}

# ─── SCPI ─────────────────────────────────────────────────────────────────────
SCPI_INFO = {
    "regime_revenus": "Revenus fonciers (location nue) — ajoutés au revenu imposable",
    "ps_taux": 0.172,
    "abattement_micro_foncier": 0.30,
    "seuil_micro_foncier": 15_000,
    "plus_value": "Régime immobilier : 19% IR + 17,2% PS avec abattements durée détention",
    "note_demembrement": "SCPI en nue-propriété : aucun revenu taxable, récupération pleine propriété à terme",
}

# ─── Données TNS / Indépendants ───────────────────────────────────────────────

TNS_COTISATIONS = {
    "micro_be": {
        "label": "Micro-BIC (vente/hébergement)",
        "abattement": 0.71,
        "seuil_ca": 188_700,
        "taux_cotisations_sociales": 0.121,
    },
    "micro_bic_services": {
        "label": "Micro-BIC (prestations de services)",
        "abattement": 0.50,
        "seuil_ca": 77_700,
        "taux_cotisations_sociales": 0.214,
    },
    "micro_bnc": {
        "label": "Micro-BNC (professions libérales)",
        "abattement": 0.34,
        "seuil_ca": 77_700,
        "taux_cotisations_sociales": 0.214,
    },
    "reel_independant": {
        "label": "Régime réel (EI / EURL / SASU IS)",
        "abattement": None,
        "cotisations_tns_sur_benefice": 0.45,  # approximation TNS
    },
}

PLAFOND_MADELIN_2025 = {
    "prevoyance": {"taux": 0.07, "max_pass": 3.75, "description": "Prévoyance (maladie, invalidité, décès)"},
    "retraite":   {"taux": 0.10, "max_pass": 8.0,  "description": "Retraite complémentaire (art. 154 bis)"},
    "perte_emploi": {"taux": 0.01875, "max_pass": 8.0, "description": "Perte d'emploi involontaire"},
}

# ─── Fiscalité internationale ────────────────────────────────────────────────

CONVENTIONS_FISCALES = {
    "ireland": {
        "pays": "Irlande",
        "convention": "Convention France-Irlande (21 mars 1968, modifiée)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.00,
        "retenue_redevances_max": 0.00,
        "impot_etranger": {
            "taux_standard": 0.20,
            "taux_superieur": 0.40,
            "seuil_superieur_celibataire": 42_000,
            "usc_taux": [0.005, 0.02, 0.04, 0.08],
            "usc_seuils": [12_012, 26_360, 70_044],
            "prsi": 0.04,
        },
        "note": "Crédit d'impôt égal à l'impôt français correspondant aux revenus irlandais. Déclarer formulaire 2047.",
        "particularites": [
            "Les dividendes irlandais subissent 25% de retenue à la source (réduit à 15% par convention)",
            "Les intérêts sont exonérés de retenue à la source par convention",
            "Les pensions irlandaises : imposables en France si résident fiscal français",
            "Double imposition possible sur les revenus d'emploi travaillés en Irlande",
        ],
    },
    "suisse": {
        "pays": "Suisse",
        "convention": "Convention Franco-Suisse (9 sept. 1966, modifiée + Accord frontaliers 11 avril 1983)",
        "methode_salaires": "exemption_progressivite",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.10,
        "note_frontaliers": "Frontaliers : voir guide_frontaliers — régime spécial selon canton",
        "particularites": [
            "Accord frontaliers 1983 : résidents français travaillant dans cantons hors Genève → imposés en France seulement",
            "Genève : imposition partagée France + Genève (compensation annuelle)",
            "Nouvel accord bilatéral 2023 en cours de ratification (télétravail 40% max sans changement fiscal)",
            "Impôt à la source suisse (IS) : retenu par l'employeur suisse, crédit d'impôt en France",
            "Salaires suisses convertis en EUR au taux de change moyen annuel BNF",
        ],
    },
    "luxembourg": {
        "pays": "Luxembourg",
        "convention": "Convention France-Luxembourg (1er avril 1958, modifiée 2022)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.00,
        "note_frontaliers": "Frontaliers : salaire imposé au Luxembourg. Déclaration en France avec crédit d'impôt.",
        "particularites": [
            "Frontaliers : imposés au Luxembourg (pas en France sur ce salaire)",
            "Déclaration 2042 + 2047 obligatoire en France (revenu déclaré mais crédit d'impôt annule l'IR français)",
            "Impact sur le TAUX global français (revenu luxembourgeois pris en compte pour le taux)",
            "Dividendes luxembourgeois : retenue 15% maximum par convention",
            "Attention : certaines primes et avantages en nature restent imposables en France",
        ],
    },
    "belgique": {
        "pays": "Belgique",
        "convention": "Convention France-Belgique (10 mars 1964, modifiée)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.15,
        "note_frontaliers": "Frontaliers : régime complexe selon secteur public/privé",
        "particularites": [
            "Secteur privé : imposés en Belgique, déclaration France avec crédit d'impôt",
            "Secteur public belge : peut être imposé en France selon la convention",
            "Zone frontalière spéciale (art. 11 convention) : certains départements bénéficient d'un régime particulier",
            "Dividendes belges : précompte mobilier 30% (réduit à 15% par convention)",
        ],
    },
    "allemagne": {
        "pays": "Allemagne",
        "convention": "Convention France-Allemagne (21 juillet 1959, modifiée)",
        "methode_salaires": "exemption_progressivite",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.00,
        "particularites": [
            "Frontaliers franco-allemands : régime spécial zones frontalières (Bas-Rhin, Moselle, Rhin-Supérieur)",
            "Salaires allemands : exemptés en France avec progressivité (inclus pour calcul du taux)",
            "Dividendes allemands : retenue Kapitalertragsteuer 26,375% (réduite à 15% par convention)",
            "Revenus de retraite : complexe selon la nature (régimes de base vs complémentaire)",
        ],
    },
    "royaume_uni": {
        "pays": "Royaume-Uni",
        "convention": "Convention France-Royaume-Uni (22 mai 1968, modifiée post-Brexit)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.00,
        "note": "Post-Brexit (jan. 2021) : la convention fiscale bilatérale reste en vigueur. Pas de changement pour l'IR.",
        "particularites": [
            "Convention maintenue après Brexit (traité bilatéral indépendant de l'UE)",
            "Dividendes UK : retenue à la source 0% généralement (crédit d'impôt en France)",
            "ISA britannique : non reconnu en France, gains imposables en France",
            "Pension UK (State Pension + private) : déclarable en France sur 2047",
        ],
    },
    "etats_unis": {
        "pays": "États-Unis",
        "convention": "Convention France-USA (31 août 1994, modifiée 2009)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.00,
        "particularites": [
            "FATCA : obligation de déclaration des comptes américains pour résidents US en France",
            "Citoyens US en France : imposables aux USA sur revenus mondiaux (filing obligation)",
            "FBAR : déclaration obligatoire des comptes étrangers > 10 000$ aux USA",
            "401k/IRA : traitement fiscal spécifique en France (DGFiP accepte report d'imposition sous conditions)",
            "Stock-options et RSU américaines : fiscalité complexe, souvent double imposition résiduelle",
        ],
    },
    "espagne": {
        "pays": "Espagne",
        "convention": "Convention France-Espagne (10 oct. 1995)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.10,
        "particularites": [
            "Dividendes espagnols : retenue 19% (réduite à 15% par convention)",
            "Revenus immobiliers en Espagne : imposables en Espagne ET pris en compte pour le taux français",
            "Pas de régime frontalier spécifique France-Espagne",
        ],
    },
    "italie": {
        "pays": "Italie",
        "convention": "Convention France-Italie (5 oct. 1989)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.10,
        "particularites": [
            "Dividendes italiens : ritenuta d'acconto 26% réduite à 15% par convention",
            "Revenus immobiliers italiens : imposables en Italie, crédit d'impôt en France",
        ],
    },
    "portugal": {
        "pays": "Portugal",
        "convention": "Convention France-Portugal (14 jan. 1971, modifiée)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.12,
        "particularites": [
            "NHR portugais (Non-Habitual Resident) : régime très avantageux pour certains revenus (mais pertes de droits en France si on change de résidence)",
            "Dividendes portugais : retenue 28% (réduite à 15% par convention)",
        ],
    },
    "canada": {
        "pays": "Canada",
        "convention": "Convention France-Canada (2 mai 1975, modifiée)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.10,
        "particularites": [
            "RRSP canadien : similaire au PER, traitement fiscal reconnu en France sous conditions",
            "Dividendes canadiens : retenue 25% (réduite à 15% par convention)",
        ],
    },
    "maroc": {
        "pays": "Maroc",
        "convention": "Convention France-Maroc (29 mai 1970, modifiée)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.15,
        "particularites": [
            "Transferts de revenus Maroc → France : déclaration obligatoire",
            "Revenus immobiliers au Maroc : imposables au Maroc, crédit d'impôt en France",
            "Pensions de retraite : imposables en France si résident fiscal français",
        ],
    },
    "tunisie": {
        "pays": "Tunisie",
        "convention": "Convention France-Tunisie (28 mai 1973, modifiée)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.12,
    },
    "algerie": {
        "pays": "Algérie",
        "convention": "Convention France-Algérie (17 mai 1982, modifiée)",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "retenue_dividendes_max": 0.15,
        "retenue_interets_max": 0.12,
    },
    "sans_convention": {
        "pays": "Sans convention (défaut)",
        "convention": "Pas de convention — risque double imposition",
        "methode_salaires": "credit_impot",
        "methode_dividendes": "credit_impot",
        "methode_interets": "credit_impot",
        "note": "Sans convention, l'impôt étranger peut quand même être déduit sous conditions (art. 57 CGI)",
    },
}

# Particularités Alsace-Moselle
ALSACE_MOSELLE = {
    "departements": [57, 67, 68],
    "nom": "Alsace-Moselle (Bas-Rhin, Haut-Rhin, Moselle)",
    "ir_impact": "AUCUN — le barème IR est identique au reste de la France",
    "cotisation_maladie_supplementaire": 0.015,
    "remboursement_sante": "90% au lieu de 70% (meilleure couverture santé)",
    "impact_salaire_net": "Salaire net légèrement inférieur (-1,5% brut) mais meilleures prestations maladie",
    "autres_particularites": [
        "Droit local des associations (loi 1908 au lieu de loi 1901)",
        "Régime concordataire : rémunération des ministres du culte prise en charge par l'État",
        "Droit local du travail : quelques spécificités (congés supplémentaires dans certains secteurs)",
        "Assurance maladie complémentaire : les mutuelles tiennent compte du régime local",
    ],
    "impact_fiscal_direct": False,
    "note": "Pour le calcul de l'IR, utilisez normalement les outils — aucune correction nécessaire. L'impact est sur les charges sociales salariales (+1,5% maladie), pas sur l'IR.",
}

# ─── Fonctions de calcul ──────────────────────────────────────────────────────

def _valider_revenu(valeur: float, nom: str = "revenu") -> float:
    """Valide et corrige un montant monétaire."""
    if not isinstance(valeur, (int, float)) or valeur != valeur:  # NaN check
        raise ValueError(f"{nom} invalide : {valeur}")
    if valeur < 0:
        raise ValueError(f"{nom} ne peut pas être négatif ({valeur:,.0f}€)")
    if valeur > 100_000_000:
        raise ValueError(f"{nom} semble incorrect ({valeur:,.0f}€ > 100M€)")
    return float(valeur)


def calculer_ir(revenu_net_imposable: float, nb_parts: float, tranches: Optional[List] = None) -> Dict:
    """Calcule l'impôt sur le revenu selon le quotient familial."""
    if tranches is None:
        tranches = TRANCHES_IR_ACTIF
    revenu_net_imposable = _valider_revenu(revenu_net_imposable, "revenu_net_imposable")
    nb_parts = max(0.5, float(nb_parts))
    revenu_par_part = revenu_net_imposable / nb_parts
    impot_par_part = 0.0
    detail_tranches = []

    for tranche in tranches:
        if revenu_par_part <= tranche["min"]:
            break
        max_tranche = tranche["max"] if tranche["max"] else float('inf')
        montant_dans_tranche = min(revenu_par_part, max_tranche) - tranche["min"]
        impot_tranche = montant_dans_tranche * tranche["taux"]
        if tranche["taux"] > 0:
            detail_tranches.append({
                "tranche": f"{tranche['min']:,}€ - {tranche['max']:,}€" if tranche["max"] else f"+ {tranche['min']:,}€",
                "taux": f"{tranche['taux']*100:.0f}%",
                "base": f"{montant_dans_tranche:,.0f}€",
                "impot": f"{impot_tranche:,.0f}€",
            })
        impot_par_part += impot_tranche

    impot_brut = impot_par_part * nb_parts

    # Décote 2026 (estimée +1.8% vs 2025) — vérifier sur impots.gouv.fr
    seuil_decote_seul = 1_964
    seuil_decote_couple = 3_249

    decote = 0.0
    if nb_parts < 2:
        if impot_brut < seuil_decote_seul:
            decote = max(0, 889 - (0.4525 * impot_brut))
    else:
        if impot_brut < seuil_decote_couple:
            decote = max(0, 1_470 - (0.4525 * impot_brut))

    impot_apres_decote = max(0, impot_brut - decote)

    # Taux moyen et taux marginal
    taux_moyen = (impot_apres_decote / revenu_net_imposable * 100) if revenu_net_imposable > 0 else 0
    taux_marginal = 0.0
    for tranche in tranches:
        if revenu_par_part > tranche["min"]:
            taux_marginal = tranche["taux"] * 100

    return {
        "impot_brut": round(impot_brut, 2),
        "decote": round(decote, 2),
        "impot_net": round(impot_apres_decote, 2),
        "taux_moyen": round(taux_moyen, 2),
        "taux_marginal": round(taux_marginal, 1),
        "detail_tranches": detail_tranches,
    }


def calculer_parts(situation_famille: str, nb_enfants: int, enfants_handicap: int = 0,
                   nb_enfants_garde_alternee: int = 0) -> float:
    """Calcule le nombre de parts fiscales.

    nb_enfants_garde_alternee : enfants en garde alternée (comptés 0.5 part au lieu de 1 part).
    Ces enfants ne doivent PAS être inclus dans nb_enfants.
    """
    parts = {
        "celibataire": 1.0,
        "marie": 2.0,
        "pacse": 2.0,
        "divorce": 1.0,
        "veuf": 1.0,
    }.get(situation_famille.lower(), 1.0)

    # Enfants à charge exclusive
    nb_total = nb_enfants  # enfants en garde exclusive pour calcul des tranches
    for i in range(1, nb_enfants + 1):
        if i <= 2:
            parts += 0.5
        else:
            parts += 1.0  # À partir du 3ème enfant

    # Enfants en garde alternée : +0.25 part par enfant (moitié du droit normal)
    # Les 2 premiers enfants valent 0.5 chacun en exclusif → 0.25 en alternée
    # À partir du 3ème : 1.0 en exclusif → 0.5 en alternée
    for i in range(1, nb_enfants_garde_alternee + 1):
        rang = nb_total + i
        if rang <= 2:
            parts += 0.25
        else:
            parts += 0.5

    # Enfants handicapés : +0.5 part supplémentaire par enfant
    parts += enfants_handicap * 0.5

    # Parent isolé avec enfants : +0.5 part
    nb_enfants_total = nb_enfants + nb_enfants_garde_alternee
    if situation_famille.lower() in ["celibataire", "divorce"] and nb_enfants_total > 0:
        parts += 0.5

    return parts


def calculer_ifi_montant(patrimoine_net: float) -> Dict:
    """Calcule l'IFI selon le barème officiel."""
    if patrimoine_net < IFI_SEUIL_ENTREE:
        return {"ifi": 0.0, "detail": [], "decote": 0.0}

    ifi = 0.0
    detail = []
    for tranche in BAREME_IFI:
        if patrimoine_net <= tranche["min"]:
            break
        max_t = tranche["max"] if tranche["max"] else float("inf")
        base = min(patrimoine_net, max_t) - tranche["min"]
        montant = base * tranche["taux"]
        if tranche["taux"] > 0:
            detail.append({
                "tranche": f"{tranche['min']:,}€ → {tranche['max']:,}€" if tranche["max"] else f"+ {tranche['min']:,}€",
                "taux": f"{tranche['taux']*100:.3f}%",
                "base": f"{base:,.0f}€",
                "ifi": f"{montant:,.0f}€",
            })
        ifi += montant

    # Décote si patrimoine entre 1.3M et 1.4M
    decote = 0.0
    if IFI_SEUIL_ENTREE <= patrimoine_net <= 1_400_000:
        decote = max(0, 17_500 - 0.0125 * patrimoine_net)
        ifi = max(0, ifi - decote)

    return {"ifi": round(ifi, 2), "detail": detail, "decote": round(decote, 2)}


def calculer_cehr(revenu_net_global: float, situation_famille: str) -> float:
    """Calcule la CEHR (3% ou 4% sur très hauts revenus)."""
    mode = "couple" if situation_famille in ("marie", "pacse") else "seul"
    cehr = 0.0
    for tranche in CEHR_BAREME[mode]:
        if revenu_net_global <= tranche["min"]:
            break
        max_t = tranche["max"] if tranche["max"] else float("inf")
        base = min(revenu_net_global, max_t) - tranche["min"]
        cehr += base * tranche["taux"]
    return round(cehr, 2)


# ─── Serveur MCP ─────────────────────────────────────────────────────────────

server = Server("impots-mcp")

TOOLS = [
    Tool(
        name="calculer_impot_revenu",
        description=(
            "Calcule l'impôt sur le revenu 2025 (revenus 2024). "
            "Prend en compte le quotient familial, la décote et les tranches officielles. "
            "Fournit l'impôt brut, net, le taux moyen et le taux marginal."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_net_imposable": {
                    "type": "number",
                    "description": "Revenu net imposable annuel en euros (après abattement 10% si salarié)",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "description": "Situation de famille",
                },
                "nb_enfants": {
                    "type": "integer",
                    "description": "Nombre d'enfants à charge exclusive (défaut: 0)",
                    "default": 0,
                },
                "nb_enfants_garde_alternee": {
                    "type": "integer",
                    "description": "Nombre d'enfants en garde alternée (compte pour 0.25 part au lieu de 0.5). Ne pas les inclure dans nb_enfants.",
                    "default": 0,
                },
                "enfants_handicap": {
                    "type": "integer",
                    "description": "Nombre d'enfants à charge en situation de handicap (défaut: 0)",
                    "default": 0,
                },
                "nb_parts_custom": {
                    "type": "number",
                    "description": "Nombre de parts personnalisé (optionnel, remplace le calcul automatique)",
                },
                "annee": {
                    "type": "integer",
                    "enum": [2025, 2026],
                    "description": "Année fiscale : 2025 (revenus 2024) ou 2026 (revenus 2025, défaut)",
                    "default": 2026,
                },
                "age_contribuable": {
                    "type": "integer",
                    "description": "Âge du contribuable principal (pour abattement +65 ans)",
                },
            },
            "required": ["revenu_net_imposable", "situation_famille"],
        },
    ),
    Tool(
        name="simuler_tranches_imposition",
        description=(
            "Affiche le détail des tranches d'imposition 2025 et montre "
            "dans quelle tranche se situe un revenu donné."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_annuel_brut": {
                    "type": "number",
                    "description": "Revenu annuel brut ou net imposable en euros",
                },
                "type_revenu": {
                    "type": "string",
                    "enum": ["salaire_brut", "salaire_net", "net_imposable"],
                    "description": "Type de revenu fourni (défaut: net_imposable)",
                    "default": "net_imposable",
                },
            },
            "required": ["revenu_annuel_brut"],
        },
    ),
    Tool(
        name="optimiser_impots",
        description=(
            "Analyse la situation fiscale et propose des stratégies d'optimisation légales "
            "personnalisées : PER, dons, emploi domicile, PEA, frais réels, etc. "
            "C'est l'outil principal pour économiser des impôts."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_net_imposable": {
                    "type": "number",
                    "description": "Revenu net imposable annuel",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                },
                "nb_enfants": {
                    "type": "integer",
                    "default": 0,
                },
                "a_employe_domicile": {
                    "type": "boolean",
                    "description": "A-t-on un employé à domicile (ménage, garde enfant, jardinage) ?",
                    "default": False,
                },
                "a_enfant_moins_6ans": {
                    "type": "boolean",
                    "description": "A-t-on un enfant de moins de 6 ans en crèche ou chez assistante maternelle ?",
                    "default": False,
                },
                "versements_per": {
                    "type": "number",
                    "description": "Versements PER déjà effectués cette année (optionnel)",
                    "default": 0,
                },
                "a_investissement_locatif": {
                    "type": "boolean",
                    "description": "Possède-t-on un investissement locatif ?",
                    "default": False,
                },
                "fait_des_dons": {
                    "type": "boolean",
                    "description": "Fait-on des dons à des associations ?",
                    "default": False,
                },
                "type_contribuable": {
                    "type": "string",
                    "enum": ["salarie", "independant", "retraite", "mixte"],
                    "description": "Statut professionnel",
                    "default": "salarie",
                },
            },
            "required": ["revenu_net_imposable", "situation_famille"],
        },
    ),
    Tool(
        name="calculer_economie_per",
        description=(
            "Calcule l'économie d'impôt réalisée en versant sur un Plan d'Épargne Retraite (PER). "
            "Le PER est souvent la meilleure stratégie pour réduire son impôt légalement."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_net_imposable": {
                    "type": "number",
                    "description": "Revenu net imposable avant versement PER",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                },
                "nb_enfants": {
                    "type": "integer",
                    "default": 0,
                },
                "montant_versement": {
                    "type": "number",
                    "description": "Montant envisagé pour le versement PER",
                },
                "revenu_pro_net": {
                    "type": "number",
                    "description": "Revenus professionnels nets de l'année (pour calculer le plafond)",
                },
            },
            "required": ["revenu_net_imposable", "situation_famille", "montant_versement"],
        },
    ),
    Tool(
        name="lister_credits_impot",
        description=(
            "Liste tous les crédits d'impôt disponibles pour les particuliers français en 2025 "
            "avec les conditions d'éligibilité et les montants. "
            "Un crédit d'impôt est remboursé même si vous ne payez pas d'impôt."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filtre": {
                    "type": "string",
                    "description": "Filtre optionnel (ex: 'garde', 'domicile', 'energie')",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="lister_reductions_impot",
        description=(
            "Liste toutes les réductions d'impôt disponibles pour les particuliers en 2025 "
            "(dons, investissement PME, Pinel, etc.). "
            "Une réduction d'impôt diminue l'impôt mais n'est pas remboursable si elle dépasse l'impôt dû."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filtre": {
                    "type": "string",
                    "description": "Filtre optionnel (ex: 'don', 'immobilier', 'investissement')",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="lister_deductions_revenu",
        description=(
            "Liste toutes les déductions possibles du revenu imposable : "
            "frais réels, PER, pensions alimentaires, déficit foncier, CSG déductible... "
            "Les déductions réduisent directement la base imposable."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="lister_epargne_defiscalisante",
        description=(
            "Liste les dispositifs d'épargne avec avantages fiscaux : "
            "PER, PEA, assurance-vie, Livret A, LEP, LDDS. "
            "Explique les plafonds, les avantages et les conditions."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="calculer_quotient_familial",
        description=(
            "Calcule le nombre de parts fiscales (quotient familial) selon la situation de famille "
            "et le nombre d'enfants à charge."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                },
                "nb_enfants": {
                    "type": "integer",
                    "description": "Nombre d'enfants à charge",
                    "default": 0,
                },
                "enfants_handicap": {
                    "type": "integer",
                    "description": "Dont enfants en situation de handicap",
                    "default": 0,
                },
                "invalide_contribuable": {
                    "type": "boolean",
                    "description": "Le contribuable est-il invalide (carte d'invalidité) ?",
                    "default": False,
                },
                "ancien_combattant": {
                    "type": "boolean",
                    "description": "Est-ce un ancien combattant ou une personne de + de 74 ans avec carte combattant ?",
                    "default": False,
                },
            },
            "required": ["situation_famille"],
        },
    ),
    Tool(
        name="guide_frais_reels",
        description=(
            "Guide complet sur la déduction des frais réels professionnels : "
            "quand est-ce avantageux, quels frais déduire, comment calculer les frais kilométriques. "
            "Alternative à l'abattement forfaitaire de 10%."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "salaire_net_annuel": {
                    "type": "number",
                    "description": "Salaire net annuel (pour comparer avec l'abattement 10%)",
                },
                "distance_domicile_travail_km": {
                    "type": "number",
                    "description": "Distance domicile-travail en km (aller simple)",
                },
                "nb_jours_travail": {
                    "type": "integer",
                    "description": "Nombre de jours travaillés par an (défaut: 220)",
                    "default": 220,
                },
                "type_vehicule": {
                    "type": "string",
                    "enum": ["voiture", "moto", "velo_electrique"],
                    "description": "Type de véhicule utilisé",
                    "default": "voiture",
                },
                "puissance_fiscale": {
                    "type": "integer",
                    "description": "Puissance fiscale du véhicule en CV (pour voiture/moto)",
                    "default": 5,
                },
            },
            "required": ["salaire_net_annuel"],
        },
    ),
    Tool(
        name="calendrier_fiscal",
        description=(
            "Affiche le calendrier fiscal 2025 avec toutes les dates importantes : "
            "déclaration de revenus, paiements, versements PER, etc."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filtre_urgent": {
                    "type": "boolean",
                    "description": "Afficher uniquement les dates importantes (défaut: false)",
                    "default": False,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="calculer_plus_values",
        description=(
            "Calcule la fiscalité sur les plus-values mobilières (actions, PEA, etc.) "
            "et immobilières. Explique les abattements pour durée de détention."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type_actif": {
                    "type": "string",
                    "enum": ["actions_hors_pea", "immobilier_residence_principale", "immobilier_locatif", "cryptomonnaie"],
                    "description": "Type d'actif cédé",
                },
                "montant_plus_value": {
                    "type": "number",
                    "description": "Montant de la plus-value brute en euros",
                },
                "duree_detention_ans": {
                    "type": "number",
                    "description": "Durée de détention en années",
                    "default": 0,
                },
                "revenu_net_imposable": {
                    "type": "number",
                    "description": "Revenu net imposable (hors plus-value) pour calcul du taux",
                },
            },
            "required": ["type_actif", "montant_plus_value"],
        },
    ),
    Tool(
        name="info_fiscalite_immobilier",
        description=(
            "Informations sur la fiscalité immobilière pour les particuliers : "
            "revenus fonciers, LMNP, LMP, déficit foncier, taxe foncière, IFI."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type_location": {
                    "type": "string",
                    "enum": ["nue", "meublee_lmnp", "meublee_lmp", "saisonniere"],
                    "description": "Type de location",
                },
                "loyers_annuels": {
                    "type": "number",
                    "description": "Montant annuel des loyers perçus",
                },
                "charges_annuelles": {
                    "type": "number",
                    "description": "Montant annuel des charges (travaux, intérêts, gestion...)",
                    "default": 0,
                },
            },
            "required": ["type_location"],
        },
    ),
    Tool(
        name="analyser_declaration_revenus",
        description=(
            "Analyse une déclaration d'impôts (données saisies manuellement ou copiées) "
            "et identifie les cases non optimisées, les oublis fréquents et les économies possibles. "
            "Fournir les montants des cases clés de votre déclaration 2042."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_1AJ": {"type": "number", "description": "Case 1AJ : Salaires du déclarant 1 (net imposable)"},
                "case_1BJ": {"type": "number", "description": "Case 1BJ : Salaires du déclarant 2 (net imposable)"},
                "case_1AK": {"type": "number", "description": "Case 1AK : Frais réels déclarant 1 (si option frais réels)"},
                "case_1BK": {"type": "number", "description": "Case 1BK : Frais réels déclarant 2"},
                "case_2DC": {"type": "number", "description": "Case 2DC : Revenus de capitaux mobiliers (dividendes)"},
                "case_2TR": {"type": "number", "description": "Case 2TR : Intérêts et produits de placement"},
                "case_3VG": {"type": "number", "description": "Case 3VG : Plus-values mobilières imposables"},
                "case_4BA": {"type": "number", "description": "Case 4BA : Revenus fonciers nets (régime réel)"},
                "case_4BE": {"type": "number", "description": "Case 4BE : Revenus fonciers micro-foncier (brut)"},
                "case_6NS": {"type": "number", "description": "Case 6NS : Versements PER déductibles déclarant 1"},
                "case_6NT": {"type": "number", "description": "Case 6NT : Versements PER déductibles déclarant 2"},
                "case_7DB": {"type": "number", "description": "Case 7DB : Garde enfants hors domicile (dépenses)"},
                "case_7DF": {"type": "number", "description": "Case 7DF : Emploi à domicile (dépenses)"},
                "case_7UD": {"type": "number", "description": "Case 7UD : Dons organismes aide personnes en difficulté"},
                "case_7UF": {"type": "number", "description": "Case 7UF : Dons autres organismes"},
                "case_7WF": {"type": "number", "description": "Case 7WF : Dépenses éligibles MaPrimeRénov' / transition énergie"},
                "revenu_fiscal_reference": {"type": "number", "description": "Revenu fiscal de référence (RFR) de l'avis précédent"},
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                },
                "nb_enfants": {"type": "integer", "default": 0},
                "nb_parts": {"type": "number", "description": "Nombre de parts de l'avis d'imposition"},
            },
            "required": ["situation_famille"],
        },
    ),
    Tool(
        name="diagnostic_fiscal_complet",
        description=(
            "Diagnostic fiscal complet par questionnaire. "
            "Posez vos informations et obtenez une analyse 360° : "
            "propriétaire ou locataire, travaux de rénovation, enfants, emploi, épargne, "
            "investissements, dons, situation familiale. "
            "Génère un rapport personnalisé avec toutes les pistes d'économies fiscales."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                # Situation personnelle
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "description": "Situation familiale",
                },
                "age": {"type": "integer", "description": "Âge du contribuable principal"},
                "nb_enfants_charge": {"type": "integer", "default": 0, "description": "Nombre d'enfants à charge"},
                "nb_enfants_moins_6ans": {"type": "integer", "default": 0, "description": "Dont enfants de moins de 6 ans"},
                "parents_a_charge": {"type": "boolean", "default": False, "description": "A-t-on des parents ou ascendants à charge ?"},
                # Revenus
                "salaire_net_annuel": {"type": "number", "description": "Salaire(s) net(s) annuel(s) total du foyer"},
                "revenus_fonciers": {"type": "number", "default": 0, "description": "Revenus locatifs bruts annuels"},
                "revenus_capitaux": {"type": "number", "default": 0, "description": "Dividendes et intérêts taxables"},
                "revenu_independant": {"type": "number", "default": 0, "description": "BNC/BIC (indépendant/freelance)"},
                # Logement
                "statut_logement": {
                    "type": "string",
                    "enum": ["proprietaire_residence_principale", "proprietaire_locatif", "locataire", "loge_gratuit"],
                    "description": "Statut vis-à-vis du logement",
                },
                "annee_construction_bien": {"type": "integer", "description": "Année de construction du bien (si propriétaire)"},
                "dpe_actuel": {
                    "type": "string",
                    "enum": ["A", "B", "C", "D", "E", "F", "G", "inconnu"],
                    "description": "DPE actuel du logement (si propriétaire)",
                },
                "surface_m2": {"type": "number", "description": "Surface du logement en m²"},
                "a_fait_travaux_recents": {"type": "boolean", "default": False, "description": "A-t-on fait des travaux de rénovation récemment ?"},
                "travaux_envisages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Travaux envisagés (ex: ['isolation_combles', 'pompe_chaleur_air_eau', 'fenetres'])",
                },
                "budget_travaux": {"type": "number", "description": "Budget total envisagé pour les travaux"},
                # Épargne et investissements
                "a_pea": {"type": "boolean", "default": False, "description": "Possède un PEA ?"},
                "a_assurance_vie": {"type": "boolean", "default": False, "description": "Possède une assurance-vie ?"},
                "a_per": {"type": "boolean", "default": False, "description": "Possède un PER ?"},
                "versements_per_annuels": {"type": "number", "default": 0, "description": "Versements PER effectués cette année"},
                "a_livret_a_plein": {"type": "boolean", "default": False, "description": "Livret A au plafond ?"},
                # Charges et dépenses déductibles
                "a_employe_domicile": {"type": "boolean", "default": False, "description": "Emploie une personne à domicile ?"},
                "depenses_domicile_annuelles": {"type": "number", "default": 0, "description": "Dépenses emploi domicile annuelles"},
                "depenses_garde_enfants": {"type": "number", "default": 0, "description": "Frais garde enfants hors domicile"},
                "fait_des_dons": {"type": "boolean", "default": False, "description": "Fait des dons à des associations ?"},
                "montant_dons_annuels": {"type": "number", "default": 0, "description": "Montant total des dons annuels"},
                "a_pension_alimentaire": {"type": "boolean", "default": False, "description": "Verse une pension alimentaire ?"},
                # Situation pro
                "type_emploi": {
                    "type": "string",
                    "enum": ["salarie", "fonctionnaire", "independant", "retraite", "sans_emploi", "mixte"],
                    "description": "Type d'emploi",
                },
                "teletravail_jours_semaine": {"type": "number", "default": 0, "description": "Jours de télétravail par semaine"},
                "distance_travail_km": {"type": "number", "default": 0, "description": "Distance domicile-travail en km"},
                # Questions complémentaires
                "a_credit_immobilier": {"type": "boolean", "default": False, "description": "A un crédit immobilier en cours ?"},
                "investissement_pme_envisage": {"type": "boolean", "default": False, "description": "Envisage d'investir dans des PME ?"},
                "patrimoine_total_estime": {"type": "number", "description": "Patrimoine immobilier total estimé (pour IFI)"},
            },
            "required": ["situation_famille", "salaire_net_annuel"],
        },
    ),
    Tool(
        name="guide_maprimerenov",
        description=(
            "Guide complet MaPrimeRénov' 2025 : catégories de revenus, travaux éligibles, "
            "montants des aides, conditions, démarches. "
            "Calcule l'aide estimée selon les revenus et les travaux envisagés."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_fiscal_reference": {
                    "type": "number",
                    "description": "Revenu fiscal de référence (RFR) du foyer",
                },
                "nb_parts": {
                    "type": "number",
                    "description": "Nombre de parts fiscales",
                    "default": 1,
                },
                "travaux_envisages": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "isolation_combles", "isolation_murs", "isolation_plancher",
                            "pompe_chaleur_air_eau", "pompe_chaleur_geothermique",
                            "chaudiere_bois", "poele_granules", "vmc_double_flux",
                            "fenetres", "audit_energetique"
                        ]
                    },
                    "description": "Liste des travaux envisagés",
                },
                "budget_total": {
                    "type": "number",
                    "description": "Budget total envisagé pour les travaux",
                },
                "dpe_actuel": {
                    "type": "string",
                    "enum": ["A", "B", "C", "D", "E", "F", "G", "inconnu"],
                    "description": "Classe énergie DPE actuelle du logement",
                    "default": "inconnu",
                },
                "dpe_cible": {
                    "type": "string",
                    "enum": ["A", "B", "C", "D", "E", "F", "G", "inconnu"],
                    "description": "Classe énergie DPE visée après travaux",
                    "default": "inconnu",
                },
            },
            "required": ["revenu_fiscal_reference"],
        },
    ),
    Tool(
        name="checker_eligibilite_aides",
        description=(
            "Vérifie les aides et dispositifs auxquels vous pourriez être éligible "
            "selon votre situation : LEP, prime activité, APL, bourses, exonérations."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_fiscal_reference": {
                    "type": "number",
                    "description": "Revenu fiscal de référence (RFR, visible sur l'avis d'imposition)",
                },
                "nb_parts": {
                    "type": "number",
                    "description": "Nombre de parts fiscales",
                    "default": 1,
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                },
                "nb_enfants": {
                    "type": "integer",
                    "default": 0,
                },
                "age": {
                    "type": "integer",
                    "description": "Âge du contribuable",
                },
            },
            "required": ["revenu_fiscal_reference", "situation_famille"],
        },
    ),
    Tool(
        name="calculer_ifi",
        description=(
            "Calcule l'Impôt sur la Fortune Immobilière (IFI) 2026. "
            "S'applique si le patrimoine immobilier net dépasse 1 300 000€. "
            "Prend en compte l'abattement de 30% sur la résidence principale, "
            "les dettes déductibles et les biens professionnels exonérés."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "patrimoine_immobilier_brut": {
                    "type": "number",
                    "description": "Valeur totale brute de vos biens immobiliers (marché)",
                },
                "valeur_residence_principale": {
                    "type": "number",
                    "description": "Valeur de la résidence principale (abattement 30% appliqué)",
                    "default": 0,
                },
                "dettes_deductibles": {
                    "type": "number",
                    "description": "Dettes déductibles : emprunts immobiliers restants, taxes foncières dues...",
                    "default": 0,
                },
                "biens_professionnels": {
                    "type": "number",
                    "description": "Valeur des biens professionnels exonérés (LMP sous conditions, SCI professionnelle...)",
                    "default": 0,
                },
                "revenu_net_imposable": {
                    "type": "number",
                    "description": "Revenu net imposable (pour vérifier le plafonnement IFI)",
                    "default": 0,
                },
            },
            "required": ["patrimoine_immobilier_brut"],
        },
    ),
    Tool(
        name="optimiser_tns",
        description=(
            "Optimisation fiscale spécifique aux travailleurs non-salariés (TNS) : "
            "auto-entrepreneurs, indépendants, freelances, gérants. "
            "Analyse le régime fiscal optimal (micro vs réel), les déductions Madelin, "
            "l'article 154 bis, PER Madelin, et compare EI / EURL / SASU."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "statut_juridique": {
                    "type": "string",
                    "enum": ["micro_entrepreneur", "ei_reel", "eurl_ir", "eurl_is", "sasu", "sarl"],
                    "description": "Statut juridique actuel",
                },
                "type_activite": {
                    "type": "string",
                    "enum": ["vente_marchandises", "prestations_services_bic", "prestations_liberales_bnc"],
                    "description": "Type d'activité",
                },
                "chiffre_affaires": {
                    "type": "number",
                    "description": "Chiffre d'affaires annuel HT",
                },
                "charges_reelles": {
                    "type": "number",
                    "description": "Charges professionnelles réelles annuelles (hors cotisations sociales)",
                    "default": 0,
                },
                "cotisations_sociales": {
                    "type": "number",
                    "description": "Cotisations sociales payées (TNS / URSSAF)",
                    "default": 0,
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
                "a_madelin": {
                    "type": "boolean",
                    "description": "Avez-vous des contrats Madelin (prévoyance/retraite) ?",
                    "default": False,
                },
                "cotisations_madelin": {
                    "type": "number",
                    "description": "Montant annuel cotisations Madelin si existantes",
                    "default": 0,
                },
                "premiere_annee": {
                    "type": "boolean",
                    "description": "Première année d'activité ? (ACRE possible)",
                    "default": False,
                },
            },
            "required": ["statut_juridique", "type_activite", "chiffre_affaires"],
        },
    ),
    Tool(
        name="comparer_scenarios",
        description=(
            "Compare jusqu'à 3 scénarios fiscaux côte à côte. "
            "Utile pour : comparer avec/sans PER, avec/sans dons, avant/après changement de situation, "
            "ou comparer deux stratégies d'optimisation différentes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "scenarios": {
                    "type": "array",
                    "description": "Liste de 2 ou 3 scénarios à comparer",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string", "description": "Nom du scénario (ex: 'Situation actuelle')"},
                            "revenu_net_imposable": {"type": "number"},
                            "situation_famille": {
                                "type": "string",
                                "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                            },
                            "nb_enfants": {"type": "integer", "default": 0},
                            "versement_per": {"type": "number", "default": 0},
                            "dons_75": {"type": "number", "default": 0},
                            "dons_66": {"type": "number", "default": 0},
                            "emploi_domicile": {"type": "number", "default": 0},
                            "garde_enfants": {"type": "number", "default": 0},
                        },
                        "required": ["label", "revenu_net_imposable", "situation_famille"],
                    },
                    "minItems": 2,
                    "maxItems": 3,
                },
            },
            "required": ["scenarios"],
        },
    ),
    Tool(
        name="calculer_prelevement_source",
        description=(
            "Calcule et explique le taux de prélèvement à la source (PAS). "
            "Indique le taux personnalisé estimé, le taux neutre, les mensualités prélevées, "
            "et comment moduler (à la hausse ou à la baisse) via impots.gouv.fr."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_net_imposable": {
                    "type": "number",
                    "description": "Revenu net imposable annuel estimé",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                },
                "nb_enfants": {"type": "integer", "default": 0},
                "salaire_mensuel_net": {
                    "type": "number",
                    "description": "Salaire mensuel net (pour calculer la retenue mensuelle)",
                },
                "revenus_complementaires": {
                    "type": "number",
                    "description": "Autres revenus annuels (fonciers, BIC, BNC...) soumis à acompte",
                    "default": 0,
                },
            },
            "required": ["revenu_net_imposable", "situation_famille"],
        },
    ),
    Tool(
        name="simuler_droits_donation",
        description=(
            "Calcule les droits de donation selon le lien de parenté. "
            "Prend en compte les abattements (100 000€ enfant/parent tous les 15 ans, "
            "80 724€ conjoint...), le barème progressif, et les dons d'argent exonérés. "
            "Utile pour planifier une transmission de patrimoine."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "montant_donation": {
                    "type": "number",
                    "description": "Montant de la donation en euros",
                },
                "lien_parente": {
                    "type": "string",
                    "enum": ["enfant_parent", "petit_enfant", "arriere_petit_enfant", "conjoint_pacs", "frere_soeur", "neveu_niece", "autre"],
                    "description": "Lien de parenté entre donateur et bénéficiaire",
                },
                "donations_anterieures": {
                    "type": "number",
                    "description": "Montant des donations déjà réalisées dans les 15 dernières années (réduit l'abattement disponible)",
                    "default": 0,
                },
                "don_argent_exonere": {
                    "type": "boolean",
                    "description": "S'agit-il d'un don de somme d'argent ? (exonération supplémentaire possible de 31 865€)",
                    "default": False,
                },
                "age_donateur": {
                    "type": "integer",
                    "description": "Âge du donateur (le don d'argent exonéré requiert donateur < 80 ans)",
                },
            },
            "required": ["montant_donation", "lien_parente"],
        },
    ),
    Tool(
        name="calculer_succession",
        description=(
            "Calcule les droits de succession selon les héritiers et le patrimoine transmis. "
            "Conjoint/PACS totalement exonéré. Enfants : abattement 100 000€ chacun. "
            "Simule la répartition optimale et les stratégies d'anticipation."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "actif_net_succession": {
                    "type": "number",
                    "description": "Actif net successoral (tous biens - dettes - frais funéraires)",
                },
                "heritiers": {
                    "type": "array",
                    "description": "Liste des héritiers",
                    "items": {
                        "type": "object",
                        "properties": {
                            "lien": {
                                "type": "string",
                                "enum": ["conjoint_pacs", "enfant", "petit_enfant", "frere_soeur", "neveu_niece", "autre"],
                            },
                            "nb": {"type": "integer", "description": "Nombre d'héritiers de ce type", "default": 1},
                            "donations_anterieures": {"type": "number", "description": "Donations reçues dans les 15 ans (réduit l'abattement)", "default": 0},
                            "handicape": {"type": "boolean", "description": "Héritier en situation de handicap (+159 325€ d'abattement)", "default": False},
                        },
                        "required": ["lien"],
                    },
                },
                "assurance_vie_hors_succession": {
                    "type": "number",
                    "description": "Capitaux assurance-vie transmis hors succession (exonérés jusqu'à 152 500€/bénéf.)",
                    "default": 0,
                },
            },
            "required": ["actif_net_succession", "heritiers"],
        },
    ),
    Tool(
        name="simuler_scpi",
        description=(
            "Simule la fiscalité d'un investissement SCPI (Société Civile de Placement Immobilier). "
            "Calcule l'impôt sur les revenus fonciers SCPI, les prélèvements sociaux, "
            "le rendement net de fiscalité, et explique les options (pleine propriété, "
            "démembrement, assurance-vie)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "montant_investi": {
                    "type": "number",
                    "description": "Capital investi dans la SCPI en euros",
                },
                "rendement_brut_pct": {
                    "type": "number",
                    "description": "Taux de distribution brut annuel (ex: 5.0 pour 5%)",
                },
                "revenu_net_imposable_hors_scpi": {
                    "type": "number",
                    "description": "Revenu net imposable du foyer hors revenus SCPI",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
                "type_detention": {
                    "type": "string",
                    "enum": ["pleine_propriete", "assurance_vie", "nue_propriete"],
                    "description": "Mode de détention des parts SCPI",
                    "default": "pleine_propriete",
                },
                "duree_detention_nue_propriete": {
                    "type": "integer",
                    "description": "Durée du démembrement en années (si nue_propriete)",
                    "default": 10,
                },
                "autres_revenus_fonciers": {
                    "type": "number",
                    "description": "Autres revenus fonciers existants (pour vérifier seuil micro-foncier)",
                    "default": 0,
                },
            },
            "required": ["montant_investi", "rendement_brut_pct", "revenu_net_imposable_hors_scpi", "situation_famille"],
        },
    ),
    Tool(
        name="guide_fiscalite_internationale",
        description=(
            "Guide de la fiscalité internationale pour les résidents français : "
            "résidence fiscale, formulaire 2047, méthodes pour éviter la double imposition "
            "(crédit d'impôt ou exemption avec progressivité). "
            "Couvre : Irlande, Suisse, Luxembourg, Belgique, Allemagne, UK, USA, Espagne, "
            "Italie, Portugal, Canada, Maroc, Tunisie, Algérie. "
            "Mentionne les particularités Alsace-Moselle."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "pays": {
                    "type": "string",
                    "description": "Pays concerné (ex: 'ireland', 'suisse', 'luxembourg', 'belgique', 'allemagne', 'royaume_uni', 'etats_unis', 'espagne', 'italie', 'portugal', 'canada', 'maroc', 'tunisie', 'algerie'). Laisser vide pour guide général.",
                },
                "situation": {
                    "type": "string",
                    "enum": ["resident_francais_revenus_etrangers", "non_resident_revenus_france", "frontalier", "expatrie_retour", "general"],
                    "description": "Situation du contribuable",
                    "default": "general",
                },
                "departement_alsace_moselle": {
                    "type": "boolean",
                    "description": "Résidez-vous en Alsace-Moselle (dép. 57, 67, 68) ?",
                    "default": False,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="calculer_revenu_etranger",
        description=(
            "Intègre un revenu étranger dans le calcul IR français. "
            "Applique automatiquement la bonne méthode selon la convention fiscale "
            "(crédit d'impôt ou exemption avec progressivité). "
            "Calcule l'IR total, le crédit d'impôt, et l'IR net à payer en France. "
            "Supporte : Irlande, Suisse, Luxembourg, Belgique, Allemagne, et autres."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_france": {
                    "type": "number",
                    "description": "Revenu net imposable de source française (salaires, fonciers...) en euros",
                    "default": 0,
                },
                "revenu_etranger_eur": {
                    "type": "number",
                    "description": "Revenu étranger converti en euros (au taux de change moyen annuel)",
                },
                "pays": {
                    "type": "string",
                    "description": "Code pays (ireland, suisse, luxembourg, belgique, allemagne, royaume_uni, etats_unis, espagne, italie, portugal, canada, maroc, sans_convention...)",
                },
                "type_revenu": {
                    "type": "string",
                    "enum": ["salaire", "dividendes", "interets", "pension", "immobilier", "autre"],
                    "description": "Nature du revenu étranger",
                    "default": "salaire",
                },
                "impot_paye_etranger": {
                    "type": "number",
                    "description": "Impôt déjà payé à l'étranger sur ce revenu (en euros)",
                    "default": 0,
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": ["revenu_etranger_eur", "pays", "situation_famille"],
        },
    ),
    Tool(
        name="guide_frontaliers",
        description=(
            "Guide fiscal spécialisé pour les travailleurs frontaliers français : "
            "Suisse (régime canton par canton, accord 1983 + nouvel accord 2023), "
            "Luxembourg (imposition au Luxembourg, déclaration en France), "
            "Belgique et Allemagne. "
            "Calcule l'impact sur la déclaration française et les obligations."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "pays_emploi": {
                    "type": "string",
                    "enum": ["suisse", "luxembourg", "belgique", "allemagne"],
                    "description": "Pays où vous travaillez",
                },
                "canton_suisse": {
                    "type": "string",
                    "description": "Canton suisse (si pays = suisse) : geneve, vaud, bale, zurich, neuchatel, etc.",
                },
                "salaire_brut_etranger": {
                    "type": "number",
                    "description": "Salaire brut annuel dans le pays d'emploi (en devise locale)",
                },
                "devise": {
                    "type": "string",
                    "enum": ["EUR", "CHF", "GBP"],
                    "description": "Devise du salaire étranger (CHF pour Suisse)",
                    "default": "EUR",
                },
                "taux_change": {
                    "type": "number",
                    "description": "Taux de change moyen annuel (ex: 1.05 pour 1 CHF = 1.05 EUR). Défaut : taux indicatifs.",
                },
                "revenu_france": {
                    "type": "number",
                    "description": "Autres revenus de source française (si vous avez des revenus en France aussi)",
                    "default": 0,
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
                "teletravail_jours_par_semaine": {
                    "type": "number",
                    "description": "Jours de télétravail depuis la France par semaine (impact fiscal depuis 2023)",
                    "default": 0,
                },
            },
            "required": ["pays_emploi", "salaire_brut_etranger", "situation_famille"],
        },
    ),
    Tool(
        name="calculer_fiscalite_crypto",
        description=(
            "Calcule la fiscalité des cryptomonnaies selon la méthode officielle 2086 (FIFO/PAMC). "
            "Gère PFU 30%, option barème IR, moins-values reportables sur 10 ans, "
            "revenus staking/mining/DeFi/NFT/airdrops. Remplace le calcul simplifié."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prix_total_cession": {
                    "type": "number",
                    "description": "Total des prix de cession de l'année (toutes cessions crypto→fiat ou crypto→bien)",
                },
                "valeur_portefeuille_avant_cession": {
                    "type": "number",
                    "description": "Valeur totale du portefeuille crypto juste avant la cession (en euros)",
                },
                "prix_acquisition_moyen_portefeuille": {
                    "type": "number",
                    "description": "Prix total d'acquisition moyen du portefeuille (PAMC — somme des coûts d'acquisition)",
                },
                "moins_values_anterieures": {
                    "type": "number",
                    "description": "Moins-values crypto reportables des années antérieures (max 10 ans)",
                    "default": 0,
                },
                "revenus_staking": {
                    "type": "number",
                    "description": "Revenus de staking/yield farming perçus dans l'année (BNC, imposables à réception)",
                    "default": 0,
                },
                "revenus_mining": {
                    "type": "number",
                    "description": "Revenus de minage (BIC si activité répétée, BNC si occasionnel)",
                    "default": 0,
                },
                "revenus_nft": {
                    "type": "number",
                    "description": "Revenus NFT (BNC si créateur ; si acheteur-revendeur, traité comme PV crypto)",
                    "default": 0,
                },
                "tmi": {
                    "type": "number",
                    "description": "Tranche marginale d'imposition en % (pour comparer PFU vs barème IR)",
                    "default": 30,
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": ["prix_total_cession", "valeur_portefeuille_avant_cession", "prix_acquisition_moyen_portefeuille"],
        },
    ),
    Tool(
        name="simuler_pacte_dutreil",
        description=(
            "Simule l'optimisation fiscale d'un Pacte Dutreil (art. 787 B CGI) pour la transmission "
            "d'entreprise familiale. Calcule l'exonération de 75% de la valeur des parts, "
            "les droits de donation ou succession avec et sans Dutreil, et les conditions à respecter."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "valeur_entreprise": {
                    "type": "number",
                    "description": "Valeur totale de l'entreprise (parts/actions) à transmettre en euros",
                },
                "lien_parente": {
                    "type": "string",
                    "enum": ["enfant", "frere_soeur", "neveu_niece", "tiers"],
                    "description": "Lien de parenté entre le donateur/défunt et le bénéficiaire",
                },
                "nb_donataires": {
                    "type": "integer",
                    "description": "Nombre de bénéficiaires (enfants, héritiers…)",
                    "default": 1,
                },
                "age_donateur": {
                    "type": "integer",
                    "description": "Age du donateur au moment de la transmission",
                },
                "donateur_dirigeant": {
                    "type": "boolean",
                    "description": "Le donateur/défunt exerce-t-il une fonction de direction dans l'entreprise ?",
                    "default": True,
                },
                "transmission_type": {
                    "type": "string",
                    "enum": ["donation", "succession"],
                    "description": "Type de transmission : donation du vivant ou succession",
                },
            },
            "required": ["valeur_entreprise", "lien_parente", "age_donateur", "transmission_type"],
        },
    ),
    Tool(
        name="simuler_sci",
        description=(
            "Compare les deux régimes fiscaux d'une SCI (Société Civile Immobilière) : "
            "SCI à l'IR (translucide, revenus fonciers) vs SCI à l'IS (amortissements, IS 15%/25%). "
            "Calcule les revenus nets après impôt, avantages transmission et fiscalité à la revente."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "valeur_bien": {
                    "type": "number",
                    "description": "Valeur vénale du bien immobilier apporté à la SCI (en euros)",
                },
                "loyers_annuels": {
                    "type": "number",
                    "description": "Total des loyers bruts annuels perçus par la SCI",
                },
                "charges_annuelles": {
                    "type": "number",
                    "description": "Charges annuelles hors intérêts d'emprunt (entretien, gestion, assurance, taxe foncière…)",
                },
                "interet_emprunt": {
                    "type": "number",
                    "description": "Intérêts d'emprunt annuels (déductibles dans les deux régimes)",
                    "default": 0,
                },
                "tmi": {
                    "type": "number",
                    "description": "Tranche marginale d'imposition de l'associé principal (%)",
                    "default": 30,
                },
                "nb_parts": {
                    "type": "integer",
                    "description": "Nombre total de parts de la SCI",
                    "default": 100,
                },
                "parts_contribuable": {
                    "type": "integer",
                    "description": "Nombre de parts détenues par le contribuable (pour quote-part)",
                    "default": 100,
                },
                "horizon_revente_ans": {
                    "type": "integer",
                    "description": "Horizon de revente du bien (en années) — impact majeur sur la fiscalité IS à la sortie",
                    "default": 20,
                },
            },
            "required": ["valeur_bien", "loyers_annuels", "charges_annuelles"],
        },
    ),
    Tool(
        name="optimiser_epargne_salariale",
        description=(
            "Optimise l'épargne salariale : intéressement, participation, PEE, PERCO/PERCOL, "
            "abondement employeur, AGA (actions gratuites d'attribution), BSPCE. "
            "Compare la fiscalité de chaque dispositif et recommande la stratégie optimale."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type_dispositif": {
                    "type": "string",
                    "enum": ["interessement", "participation", "pee", "perco", "aga", "bspce", "synthese"],
                    "description": "Type de dispositif d'épargne salariale à analyser",
                },
                "montant": {"type": "number", "default": 0, "description": "Montant du versement ou du gain"},
                "abondement_employeur": {"type": "number", "default": 0, "description": "Abondement de l'employeur"},
                "tmi": {"type": "number", "default": 30, "description": "Taux marginal d'imposition (%)"},
                "annees_blocage_restantes": {"type": "integer", "default": 0, "description": "Années de blocage restantes"},
                "moins_3ans_societe": {
                    "type": "boolean",
                    "default": False,
                    "description": "Présent dans la société depuis moins de 3 ans (BSPCE : taux majoré à 47.2%)",
                },
            },
            "required": ["type_dispositif"],
        },
    ),
    Tool(
        name="calculer_impot_societes",
        description=(
            "Calcule l'impôt sur les sociétés (IS) : taux réduit PME 15% jusqu'à 42 500€ de bénéfice, "
            "taux normal 25%. Vérifie l'éligibilité, calcule les acomptes trimestriels, "
            "analyse le déficit reportable et la contribution sociale sur hauts bénéfices."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "benefice": {"type": "number", "description": "Bénéfice imposable de l'exercice (avant IS)"},
                "ca": {
                    "type": "number",
                    "description": "Chiffre d'affaires HT (condition éligibilité taux réduit : CA < 10M€)",
                },
                "capital_personnes_physiques_pct": {
                    "type": "number",
                    "default": 100,
                    "description": "% du capital détenu par des personnes physiques (condition taux réduit PME ≥ 75%)",
                },
                "deficit_reporte": {
                    "type": "number",
                    "default": 0,
                    "description": "Déficits antérieurs reportables en avant (réduisent le bénéfice imposable)",
                },
            },
            "required": ["benefice"],
        },
    ),
    Tool(
        name="optimiser_remuneration_dirigeant",
        description=(
            "Optimise la rémunération du dirigeant entre salaire et dividendes (SASU, EURL IS, SARL IS). "
            "Compare IS + charges sociales + IR pour différentes répartitions. "
            "Calcule le net perçu, le coût pour la société et le taux de prélèvement effectif."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "benefice_brut_societe": {
                    "type": "number",
                    "description": "Résultat de la société AVANT rémunération du dirigeant et IS",
                },
                "remuneration_souhaitee": {
                    "type": "number",
                    "description": "Rémunération brute annuelle souhaitée pour le dirigeant",
                },
                "structure": {
                    "type": "string",
                    "enum": ["sasu", "eurl_is", "sarl_is"],
                    "description": "Forme juridique : SASU (assimilé salarié), EURL IS ou SARL IS (gérant TNS)",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": ["benefice_brut_societe", "remuneration_souhaitee", "structure", "situation_famille"],
        },
    ),
    # ── Nouveaux outils 2.3.0 ──────────────────────────────────────────────────
    Tool(
        name="guide_evenements_vie",
        description=(
            "Guide fiscal sur les grands événements de vie et leur impact sur la déclaration de revenus : "
            "mariage, PACS, divorce/séparation, naissance, garde alternée, enfant majeur rattaché, décès du conjoint. "
            "Explique les règles de quotient familial, les choix déclaratifs disponibles et simule l'impact fiscal."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "evenement": {
                    "type": "string",
                    "enum": ["mariage", "divorce", "naissance", "garde_alternee", "enfant_majeur", "deces_conjoint"],
                    "description": "Type d'événement de vie survenu au cours de l'année",
                },
                "situation_actuelle": {
                    "type": "string",
                    "description": "Situation familiale actuelle (ex: 'célibataire avant mariage', 'marié avec 2 enfants')",
                },
                "nb_enfants": {
                    "type": "integer",
                    "description": "Nombre d'enfants à charge (hors garde alternée)",
                    "default": 0,
                },
                "nb_enfants_garde_alternee": {
                    "type": "integer",
                    "description": "Nombre d'enfants en garde alternée",
                    "default": 0,
                },
                "revenu_annuel": {
                    "type": "number",
                    "description": "Revenu net imposable annuel (pour simulation d'impact fiscal)",
                    "default": 0,
                },
                "age_enfant": {
                    "type": "integer",
                    "description": "Age de l'enfant (pour le cas 'enfant_majeur', rattachement possible jusqu'à 25 ans)",
                },
            },
            "required": ["evenement", "situation_actuelle"],
        },
    ),
    Tool(
        name="calculer_revenus_remplacement",
        description=(
            "Calcule le traitement fiscal des revenus de remplacement : allocations chômage (ARE), "
            "pensions de retraite, rentes viagères à titre onéreux (RVTO), indemnités de licenciement, "
            "pensions d'invalidité. Applique les abattements spécifiques et compare avec les revenus d'activité."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type_revenu": {
                    "type": "string",
                    "enum": ["chomage", "retraite", "rente_viagere", "indemnite_licenciement", "invalidite"],
                    "description": "Type de revenu de remplacement",
                },
                "montant": {
                    "type": "number",
                    "description": "Montant brut annuel du revenu de remplacement (en euros)",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "description": "Situation de famille",
                },
                "nb_enfants": {
                    "type": "integer",
                    "description": "Nombre d'enfants à charge",
                    "default": 0,
                },
                "rni_autres_revenus": {
                    "type": "number",
                    "description": "Revenu net imposable des autres sources (salaires, foncier...) déjà dans le foyer",
                    "default": 0,
                },
                "age_premier_versement_rente": {
                    "type": "integer",
                    "description": "Age lors du premier versement de la rente (uniquement pour type 'rente_viagere')",
                },
                "remuneration_annuelle_brute": {
                    "type": "number",
                    "description": "Rémunération brute annuelle de référence (pour indemnité licenciement)",
                },
                "indemnite_conventionnelle": {
                    "type": "number",
                    "description": "Montant de l'indemnité conventionnelle de licenciement (référence exonération)",
                },
            },
            "required": ["type_revenu", "montant", "situation_famille"],
        },
    ),
    Tool(
        name="simuler_sortie_per",
        description=(
            "Simule les différents modes de sortie d'un PER (Plan Épargne Retraite) : "
            "sortie en rente ou en capital à la retraite, déblocage anticipé pour résidence principale "
            "ou cas exceptionnels (invalidité, décès conjoint, surendettement, fin droits chômage, liquidation). "
            "Compare la fiscalité nette pour chaque scénario selon que les versements ont été déduits ou non."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "capital_total": {
                    "type": "number",
                    "description": "Valeur totale du PER au moment de la sortie (versements + gains)",
                },
                "versements_cumules": {
                    "type": "number",
                    "description": "Total des versements effectués (hors gains)",
                },
                "versements_deduits": {
                    "type": "number",
                    "description": "Part des versements qui ont été fiscalement déduits du revenu imposable",
                },
                "tmi": {
                    "type": "number",
                    "description": "Taux marginal d'imposition actuel du foyer en % (ex: 30 pour TMI 30%)",
                },
                "situation": {
                    "type": "string",
                    "enum": ["retraite_rente", "retraite_capital", "anticipation_rp", "anticipation_exceptionnelle"],
                    "description": (
                        "Mode de sortie : 'retraite_rente' (rente à la retraite), "
                        "'retraite_capital' (capital à la retraite), "
                        "'anticipation_rp' (déblocage anticipé résidence principale), "
                        "'anticipation_exceptionnelle' (invalidité/décès conjoint/surendettement/fin droits/liquidation)"
                    ),
                },
                "age": {
                    "type": "integer",
                    "description": "Age lors de la sortie (fraction RVTO pour rente selon l'âge)",
                },
                "rente_annuelle": {
                    "type": "number",
                    "description": "Rente annuelle versée (uniquement pour situation 'retraite_rente')",
                },
            },
            "required": ["capital_total", "versements_cumules", "versements_deduits", "tmi", "situation"],
        },
    ),
    # ── Nouveaux outils v2.4.0 ─────────────────────────────────────────────────
    Tool(
        name="simuler_depart_retraite",
        description=(
            "Simule le départ à la retraite : estimation de la pension (régimes général, complémentaire AGIRC-ARRCO), "
            "impact de l'âge de départ (décote/surcote), cumul emploi-retraite, abattement fiscal 10% sur pensions. "
            "Compare les scénarios de départ à 62, 64, 67 ans."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "salaire_annuel_brut": {
                    "type": "number",
                    "description": "Dernier salaire annuel brut (base de calcul de la pension)",
                },
                "trimestres_valides": {
                    "type": "integer",
                    "description": "Nombre de trimestres cotisés à ce jour (tous régimes confondus)",
                },
                "age_actuel": {
                    "type": "integer",
                    "description": "Âge actuel (pour calculer les trimestres restants et la date de départ)",
                },
                "regime": {
                    "type": "string",
                    "enum": ["prive", "fonctionnaire", "independant"],
                    "default": "prive",
                    "description": "Régime de retraite principal",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
                "cumul_emploi_retraite": {
                    "type": "boolean",
                    "default": False,
                    "description": "Envisagez-vous de cumuler emploi et retraite ?",
                },
                "salaire_cumul": {
                    "type": "number",
                    "default": 0,
                    "description": "Revenu d'activité envisagé en cas de cumul emploi-retraite",
                },
            },
            "required": ["salaire_annuel_brut", "trimestres_valides", "age_actuel"],
        },
    ),
    Tool(
        name="guide_fiscalite_agricole",
        description=(
            "Guide de la fiscalité agricole : régime du forfait collectif, régime simplifié (RSA), "
            "régime réel normal (RN). DPA (Déduction pour Aléas), DEP (Déduction pour Épargne de Précaution), "
            "exonération jeune agriculteur, TVA agricole, cotisations MSA."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "recettes_annuelles": {
                    "type": "number",
                    "description": "Recettes annuelles de l'exploitation agricole (HT)",
                },
                "regime": {
                    "type": "string",
                    "enum": ["forfait", "simplifie", "reel_normal", "auto"],
                    "default": "auto",
                    "description": "Régime fiscal souhaité (auto = déterminé selon les seuils)",
                },
                "benefice_agricole": {
                    "type": "number",
                    "default": 0,
                    "description": "Bénéfice agricole estimé (pour régimes réels)",
                },
                "dep_souhaitee": {
                    "type": "number",
                    "default": 0,
                    "description": "Montant de DEP (Déduction pour Épargne de Précaution) envisagé",
                },
                "jeune_agriculteur": {
                    "type": "boolean",
                    "default": False,
                    "description": "Jeune agriculteur (< 5 ans d'installation) — exonérations spécifiques",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": ["recettes_annuelles"],
        },
    ),
    Tool(
        name="guide_fiscalite_outremer",
        description=(
            "Guide des dispositifs fiscaux spécifiques aux DOM-TOM (Guadeloupe, Martinique, Réunion, Guyane, "
            "Mayotte, Saint-Martin, Polynésie, Nouvelle-Calédonie…) : abattement spécifique IR 30%/40%, "
            "défiscalisation Girardin, loi Pinel outre-mer, exonérations entreprises, TVA NPR."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "territoire": {
                    "type": "string",
                    "enum": [
                        "guadeloupe", "martinique", "reunion", "guyane", "mayotte",
                        "saint_martin", "saint_barthelemy", "polynesie", "nouvelle_caledonie",
                        "saint_pierre_miquelon", "wallis_futuna"
                    ],
                    "description": "Territoire d'outre-mer de résidence ou d'investissement",
                },
                "situation": {
                    "type": "string",
                    "enum": ["resident", "investisseur_metropole"],
                    "default": "resident",
                    "description": "Résident du territoire ou investisseur depuis la métropole",
                },
                "revenu_net_imposable": {
                    "type": "number",
                    "default": 0,
                    "description": "Revenu net imposable annuel (pour calculer l'abattement spécifique DOM)",
                },
                "type_investissement": {
                    "type": "string",
                    "enum": ["immobilier_locatif", "girardin_industriel", "pinel_om", "creation_entreprise", "aucun"],
                    "default": "aucun",
                    "description": "Type d'investissement outre-mer envisagé",
                },
                "montant_investissement": {
                    "type": "number",
                    "default": 0,
                    "description": "Montant de l'investissement (pour Girardin ou Pinel OM)",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": ["territoire"],
        },
    ),
    # ── Nouveaux outils v2.5.0 ─────────────────────────────────────────────────
    Tool(
        name="simuler_assurance_vie",
        description=(
            "Simule la fiscalité de l'assurance-vie : rachats partiels/totaux (taux 7.5% après 8 ans, "
            "abattement 4 600€/9 200€), transmission au décès hors succession (152 500€/bénéficiaire), "
            "primes après 70 ans (abattement 30 500€). Compare PFU vs barème IR."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "capital_total": {"type": "number", "description": "Valeur actuelle du contrat"},
                "versements_cumules": {"type": "number", "description": "Total des primes versées"},
                "anciennete_ans": {"type": "integer", "default": 0, "description": "Ancienneté du contrat en années"},
                "situation_famille": {"type": "string", "enum": ["celibataire","marie","pacse","divorce","veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "type_operation": {"type": "string", "enum": ["rachat_partiel","rachat_total","transmission"], "default": "rachat_partiel"},
                "montant_rachat": {"type": "number", "default": 0, "description": "Montant du rachat partiel envisagé"},
                "primes_versees_apres_70_ans": {"type": "number", "default": 0},
                "nb_beneficiaires": {"type": "integer", "default": 1},
            },
            "required": ["capital_total", "versements_cumules"],
        },
    ),
    Tool(
        name="simuler_demembrement",
        description=(
            "Simule le démembrement de propriété (usufruit/nue-propriété) : barème fiscal art. 669 CGI, "
            "calcul de la valeur de la nue-propriété selon l'âge, économies sur droits de donation, "
            "usufruit temporaire, donation-partage."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "valeur_pleine_propriete": {"type": "number", "description": "Valeur du bien en pleine propriété"},
                "age_usufruitier": {"type": "integer", "description": "Âge de l'usufruitier (barème art. 669 CGI)"},
                "type_operation": {"type": "string", "enum": ["donation_nue_propriete","achat_demembre","usufruit_temporaire"], "default": "donation_nue_propriete"},
                "lien_parente": {"type": "string", "enum": ["enfant","frere_soeur","neveu_niece","conjoint","tiers"], "default": "enfant"},
                "nb_donataires": {"type": "integer", "default": 1},
                "usufruit_temporaire": {"type": "boolean", "default": False},
                "duree_usufruit_temporaire": {"type": "integer", "default": 10, "description": "Durée en années de l'usufruit temporaire"},
            },
            "required": ["valeur_pleine_propriete", "age_usufruitier"],
        },
    ),
    Tool(
        name="simuler_cession_entreprise",
        description=(
            "Simule la fiscalité de cession d'entreprise : PFU 30%, abattement renforcé PME (50%/65%/85%), "
            "abattement départ retraite dirigeant (500 000€), apport-cession avec report d'imposition "
            "(art. 150-0 B ter). Compare tous les régimes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prix_cession": {"type": "number", "description": "Prix de cession des titres ou du fonds"},
                "prix_acquisition": {"type": "number", "default": 0, "description": "Prix d'acquisition initial"},
                "duree_detention_ans": {"type": "integer", "default": 0},
                "type_cession": {"type": "string", "enum": ["titres_pme","fonds_commerce","titres_holding"], "default": "titres_pme"},
                "depart_retraite_dirigeant": {"type": "boolean", "default": False, "description": "Le cédant part à la retraite dans les 24 mois"},
                "situation_famille": {"type": "string", "enum": ["celibataire","marie","pacse","divorce","veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "apport_avant_cession": {"type": "boolean", "default": False, "description": "Apport des titres à une holding avant cession (report d'imposition)"},
            },
            "required": ["prix_cession"],
        },
    ),
    Tool(
        name="simuler_holding",
        description=(
            "Simule l'intérêt d'une holding : régime mère-fille (IS sur 5% des dividendes), "
            "comparatif détention directe vs holding, intégration fiscale, réinvestissement optimisé."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "benefice_filiale": {"type": "number", "description": "Bénéfice net de la filiale après IS"},
                "taux_detention_holding": {"type": "number", "default": 100, "description": "% détenu par la holding"},
                "dividendes_vers_personne_physique": {"type": "number", "default": 0, "description": "Dividendes à redistribuer à l'actionnaire PP"},
                "montant_reinvestissement": {"type": "number", "default": 0},
                "situation_famille": {"type": "string", "enum": ["celibataire","marie","pacse","divorce","veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "nb_filiales": {"type": "integer", "default": 1},
            },
            "required": ["benefice_filiale"],
        },
    ),
    Tool(
        name="calculer_tva",
        description=(
            "Guide TVA complet : seuils de franchise en base 2025 (37 500€ services / 85 000€ marchandises), "
            "régime réel simplifié vs normal, taux 20%/10%/5.5%/2.1%, calcul TVA nette, "
            "TVA intracommunautaire (OSS, autoliquidation)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "chiffre_affaires_ht": {"type": "number", "default": 0},
                "type_activite": {"type": "string", "enum": ["marchandises","services","liberal","mixte","agricole"], "default": "services"},
                "regime": {"type": "string", "enum": ["auto","franchise","reel_simplifie","reel_normal"], "default": "auto"},
                "tva_collectee": {"type": "number", "default": 0},
                "tva_deductible": {"type": "number", "default": 0},
                "ventes_intracommunautaires": {"type": "number", "default": 0},
                "achats_intracommunautaires": {"type": "number", "default": 0},
            },
            "required": [],
        },
    ),
    Tool(
        name="guide_auto_entrepreneur",
        description=(
            "Guide complet auto-entrepreneur / micro-entrepreneur : seuils CA 2025, taux de cotisations, "
            "versement libératoire forfaitaire (VFL), ACRE, abattements IR, TVA franchise, "
            "CFE, obligations déclaratives, radiation."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "chiffre_affaires_annuel": {"type": "number", "default": 0},
                "type_activite": {"type": "string", "enum": ["vente_marchandises","services_bic","services_bnc"], "default": "services_bic"},
                "option_versement_liberatoire": {"type": "boolean", "default": False},
                "rni_foyer_n_moins_2": {"type": "number", "default": 0, "description": "RFR du foyer de l'année N-2 (condition VFL)"},
                "nb_parts_foyer": {"type": "number", "default": 1.0},
                "premiere_annee": {"type": "boolean", "default": False},
                "beneficie_acre": {"type": "boolean", "default": False},
            },
            "required": [],
        },
    ),
    Tool(
        name="calculer_cfe",
        description=(
            "Calcule la Cotisation Foncière des Entreprises (CFE) : cotisation minimum selon CA, "
            "exonérations (1ère année, JEI, ZFU, ZRR, CA < 5 000€, artisans), base sur valeur locative, "
            "déductibilité fiscale."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "chiffre_affaires": {"type": "number", "default": 0},
                "commune_type": {"type": "string", "enum": ["petite","moyenne","grande","paris"], "default": "moyenne"},
                "type_entreprise": {"type": "string", "enum": ["auto_entrepreneur","pme","liberal","sci"], "default": "auto_entrepreneur"},
                "premiere_annee_activite": {"type": "boolean", "default": False},
                "superficie_locaux_m2": {"type": "number", "default": 0},
                "valeur_locative_brute": {"type": "number", "default": 0, "description": "Valeur locative cadastrale brute des locaux (si connu)"},
            },
            "required": [],
        },
    ),
    Tool(
        name="simuler_investissement_pea",
        description=(
            "Simule la fiscalité du PEA (Plan Épargne en Actions) : exonération IR après 5 ans, "
            "PS 17.2% sur les gains, plafond 150 000€ (PEA) + 75 000€ (PEA-PME), "
            "rente viagère exonérée, comparatif PEA vs CTO."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "versements_cumules": {"type": "number", "default": 0},
                "valeur_actuelle": {"type": "number", "default": 0},
                "anciennete_ans": {"type": "integer", "default": 0},
                "type_pea": {"type": "string", "enum": ["pea_classique","pea_pme"], "default": "pea_classique"},
                "montant_retrait": {"type": "number", "default": 0},
                "situation_famille": {"type": "string", "enum": ["celibataire","marie","pacse","divorce","veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    ),
    Tool(
        name="guide_defiscalisation_solidaire",
        description=(
            "Guide des dispositifs de défiscalisation solidaire et éthique : dons associations (75%/66%), "
            "réduction IFI, investissement PME/ESUS (25%), FIP/FCPI (18%/25%), SOFICA (30%/36%), "
            "plafond niches fiscales 10 000€."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "revenu_net_imposable": {"type": "number", "default": 0},
                "impot_actuel": {"type": "number", "default": 0},
                "situation_famille": {"type": "string", "enum": ["celibataire","marie","pacse","divorce","veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "patrimoine_ifi": {"type": "number", "default": 0, "description": "Patrimoine immobilier net (si assujetti IFI)"},
                "tmi_41_ou_plus": {"type": "boolean", "default": False},
            },
            "required": [],
        },
    ),
    Tool(
        name="calculer_pv_immobiliere",
        description=(
            "Calcule la plus-value immobilière avec tous les mécanismes officiels : "
            "frais d'acquisition 7.5% forfaitaires, travaux 15% forfaitaires après 5 ans, "
            "abattements IR (19%) et PS (17.2%) par durée de détention, "
            "exonération résidence principale, taxe sur hautes plus-values (2% à 6%)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prix_vente": {"type": "number", "description": "Prix de vente du bien"},
                "prix_achat": {"type": "number", "default": 0, "description": "Prix d'acquisition initial"},
                "frais_achat": {"type": "number", "default": 0, "description": "Frais d'acquisition réels (notaire, agence)"},
                "travaux_justifies": {"type": "number", "default": 0, "description": "Montant des travaux justifiés par factures"},
                "duree_detention_ans": {"type": "integer", "default": 0},
                "type_bien": {"type": "string", "enum": ["residence_principale","secondaire","locatif","terrain"], "default": "secondaire"},
                "primo_accedant_acheteur": {"type": "boolean", "default": False},
            },
            "required": ["prix_vente"],
        },
    ),
    Tool(
        name="guide_taxe_fonciere",
        description=(
            "Guide de la taxe foncière : calcul (valeur locative cadastrale × 50% × taux communes), "
            "exonérations (construction neuve 2 ans, personnes âgées modestes, ZRR, JEI), "
            "plafonnement à 50% du RNI, taxe sur logements vacants, THRS résidences secondaires."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "valeur_locative_brute": {"type": "number", "default": 0, "description": "Valeur locative cadastrale brute (sur l'avis de TF)"},
                "taux_commune_pct": {"type": "number", "default": 25, "description": "Taux communal (%)"},
                "taux_departement_pct": {"type": "number", "default": 10, "description": "Taux départemental (%)"},
                "revenu_net_imposable": {"type": "number", "default": 0, "description": "RNI pour vérifier le plafonnement"},
                "nb_parts": {"type": "number", "default": 1.0},
                "type_bien": {"type": "string", "enum": ["bati","non_bati"], "default": "bati"},
                "logement_neuf": {"type": "boolean", "default": False},
                "personne_agee_modeste": {"type": "boolean", "default": False},
            },
            "required": [],
        },
    ),
    Tool(
        name="simuler_reversion_pension",
        description=(
            "Simule la pension de réversion : taux (54% régime général, 60% AGIRC-ARRCO), "
            "conditions d'accès (âge, ressources), écrêtement selon revenus, "
            "cumul avec pension personnelle, fiscalité (abattement 10%)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "pension_annuelle_defunt": {"type": "number", "description": "Pension annuelle du défunt"},
                "pension_personnelle_beneficiaire": {"type": "number", "default": 0},
                "age_beneficiaire": {"type": "integer", "default": 55},
                "revenus_annuels_beneficiaire": {"type": "number", "default": 0, "description": "Revenus annuels (hors réversion) pour calcul écrêtement"},
                "situation_beneficiaire": {"type": "string", "enum": ["veuf","remarie","concubinage"], "default": "veuf"},
                "nb_enfants": {"type": "integer", "default": 0},
                "regime_defunt": {"type": "string", "enum": ["general","agirc_arrco","fonctionnaire","independant","liberal"], "default": "general"},
            },
            "required": ["pension_annuelle_defunt"],
        },
    ),
    Tool(
        name="guide_revision_declaration",
        description=(
            "Guide pour corriger une déclaration fiscale : déclaration rectificative (avant 15 déc.), "
            "réclamation contentieuse (délai 2 ans après avis d'imposition), "
            "majorations et intérêts de retard (2.4%/an), prescription (3 ans), recours possibles."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "annee_declaration": {"type": "integer", "default": 2025, "description": "Année de la déclaration à corriger (ex. 2025 pour revenus 2024)"},
                "type_erreur": {"type": "string", "enum": ["omission_deduction","revenu_omis","erreur_situation_famille","autre"], "default": "omission_deduction"},
                "montant_impact_estime": {"type": "number", "default": 0, "description": "Montant estimé de l'erreur en euros"},
                "declaration_deja_soumise": {"type": "boolean", "default": True},
            },
            "required": [],
        },
    ),
    Tool(
        name="simuler_revenus_exceptionnels",
        description=(
            "Calcule l'economie d'impot grace au systeme du quotient (art. 163-0 A CGI) "
            "pour les revenus exceptionnels ou differés : indemnite de licenciement supra-legale, "
            "rappels de salaires, prime exceptionnelle, gains pluriannuels. "
            "Compare l'imposition normale vs le quotient sur N annees."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "rni_ordinaire": {"type": "number", "description": "Revenu net imposable ordinaire (hors revenu exceptionnel)", "default": 0},
                "revenu_exceptionnel": {"type": "number", "description": "Montant du revenu exceptionnel ou differe a declarer"},
                "nombre_annees_echelement": {"type": "integer", "description": "Coefficient N (nombre d'annees sur lesquelles le droit a ete acquis, defaut 4)", "default": 4},
                "situation_famille": {"type": "string", "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "type_revenu": {"type": "string", "enum": ["indemnite_licenciement", "prime_exceptionnelle", "revenus_differés", "gain_stock_options", "autre"], "default": "autre"},
            },
            "required": ["revenu_exceptionnel"],
        },
    ),
    Tool(
        name="comparer_pfu_bareme_capital",
        description=(
            "Compare la flat tax PFU 30% et le bareme progressif pour les revenus du capital : "
            "dividendes (abattement 40%, CSG ded.), interets, plus-values mobilieres. "
            "Identifie l'option optimale selon votre TMI et calcule l'economie realisee."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type_revenu": {"type": "string", "enum": ["dividendes", "interets", "plus_values_mobilieres"], "description": "Nature du revenu de capital", "default": "dividendes"},
                "montant": {"type": "number", "description": "Montant du revenu de capital en euros"},
                "rni_autres_revenus": {"type": "number", "description": "Revenus nets imposables autres (salaires, BIC...) du foyer", "default": 0},
                "situation_famille": {"type": "string", "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": ["montant"],
        },
    ),
    Tool(
        name="simuler_lmnp",
        description=(
            "Simulation LMNP (Location Meublee Non Professionnelle) : "
            "compare micro-BIC (abattement 50% ou 71%) vs regime reel avec amortissement. "
            "Calcule l'amortissement du batiment et du mobilier, le deficit reportable, "
            "et recommande le regime optimal."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "loyers_annuels_bruts": {"type": "number", "description": "Total des loyers encaisses par an (hors charges refacturees)"},
                "valeur_bien_hors_terrain": {"type": "number", "description": "Valeur d'acquisition du batiment HORS terrain (base amortissable)", "default": 0},
                "valeur_terrain": {"type": "number", "description": "Valeur du terrain (non amortissable)", "default": 0},
                "valeur_mobilier": {"type": "number", "description": "Valeur du mobilier et equipements (amortissables sur 7 ans)", "default": 5000},
                "charges_annuelles": {"type": "number", "description": "Charges courantes : copropriete, assurance, frais de gestion", "default": 0},
                "interets_emprunt_annuels": {"type": "number", "description": "Interets d'emprunt annuels", "default": 0},
                "taxe_fonciere": {"type": "number", "description": "Taxe fonciere annuelle", "default": 0},
                "type_location": {"type": "string", "enum": ["classique", "tourisme_classe"], "description": "classique (abatt. 50%) ou tourisme_classe/VFT (abatt. 71%)", "default": "classique"},
                "situation_famille": {"type": "string", "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "rni_autres_revenus": {"type": "number", "description": "Autres revenus nets imposables du foyer", "default": 0},
            },
            "required": ["loyers_annuels_bruts"],
        },
    ),
    Tool(
        name="simuler_rachat_trimestres",
        description=(
            "Simule le rachat de trimestres manquants pour la retraite : "
            "cout brut selon l'age et le salaire, economie fiscale (deductible IR), "
            "gain de pension mensuel, et break-even en mois. "
            "Compare avec un versement PER equivalent."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "nb_trimestres_racheter": {"type": "integer", "description": "Nombre de trimestres a racheter (1 a 12)", "default": 4},
                "salaire_annuel_brut": {"type": "number", "description": "Salaire annuel brut (reference pour le calcul, plafonne au PASS)"},
                "age_actuel": {"type": "integer", "description": "Age actuel du cotisant"},
                "annee_naissance": {"type": "integer", "description": "Annee de naissance (pour determiner le nombre de trimestres requis)", "default": 1975},
                "trimestres_valides_actuels": {"type": "integer", "description": "Nombre de trimestres deja valides", "default": 100},
                "option_rachat": {"type": "string", "enum": ["duree_seulement", "duree_et_taux"], "description": "duree_seulement : moins cher. duree_et_taux : augmente aussi le salaire de reference.", "default": "duree_seulement"},
                "tmi": {"type": "number", "description": "Taux marginal d'imposition actuel (pour calcul economie fiscale)", "default": 30},
                "statut_professionnel": {"type": "string", "enum": ["salarie", "independant", "fonctionnaire"], "default": "salarie"},
            },
            "required": ["salaire_annuel_brut", "age_actuel"],
        },
    ),
    Tool(
        name="calculer_exit_tax",
        description=(
            "Calcule l'exit tax (art. 167 bis CGI) due lors du transfert du domicile fiscal "
            "hors de France : imposition des plus-values latentes sur titres et droits sociaux. "
            "Indique si un sursis automatique s'applique (depart vers UE/EEE) et les strategies "
            "pour minimiser l'imposition avant le depart."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "plus_values_latentes_total": {"type": "number", "description": "Total des plus-values latentes nettes sur titres et droits sociaux (valeur actuelle - prix de revient)"},
                "rni_autres_revenus": {"type": "number", "description": "Autres revenus nets imposables (pour option bareme)", "default": 0},
                "situation_famille": {"type": "string", "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "pays_destination": {"type": "string", "enum": ["ue_eea", "hors_ue"], "description": "ue_eea : sursis automatique. hors_ue : paiement immediat ou garantie.", "default": "hors_ue"},
                "annees_residence_france_10_dernieres": {"type": "integer", "description": "Nombre d'annees de residence fiscale en France sur les 10 dernieres annees", "default": 10},
                "option_bareme_progressif": {"type": "boolean", "description": "Opter pour le bareme progressif plutot que le PFU (utile si TMI < 30%)", "default": False},
            },
            "required": ["plus_values_latentes_total"],
        },
    ),
    Tool(
        name="guide_loc_avantages",
        description=(
            "Guide et simulation Loc'Avantages (art. 199 tricies CGI, ex-Cosse Ancien) : "
            "reduction d'impot 15% a 65% en echange d'un loyer modere sur logement loue nu, "
            "via convention ANAH. Alternative au Pinel pour l'immobilier ancien."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "loyers_bruts_annuels": {"type": "number", "description": "Loyers bruts annuels du logement concerne", "default": 0},
                "niveau_convention": {"type": "string", "enum": ["intermediaire", "social", "tres_social", "solidaire"], "description": "Niveau de la convention ANAH : intermediaire (15%), social (35%), tres_social (65%), solidaire (65%)", "default": "intermediaire"},
                "surface_m2": {"type": "number", "description": "Surface habitable du logement en m2 (pour calcul du loyer plafond)", "default": 0},
                "zone": {"type": "string", "enum": ["A_bis", "A", "B1", "B2_C"], "description": "Zone geographique : A_bis (Paris), A (IDF...), B1, B2_C", "default": "B1"},
                "rni_autres_revenus": {"type": "number", "description": "Autres revenus nets imposables du foyer", "default": 0},
                "situation_famille": {"type": "string", "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    ),
    Tool(
        name="simuler_micro_foncier",
        description=(
            "Compare le regime micro-foncier (abattement forfaitaire 30%) et le regime reel "
            "pour les revenus locatifs nus (< 15 000 EUR/an). "
            "Calcule le deficit foncier imputable sur le revenu global (jusqu'a 10 700 EUR/an), "
            "les reports de deficit et l'impact sur l'IR."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "loyers_bruts_annuels": {"type": "number", "description": "Total des loyers bruts percus dans l'annee"},
                "interets_emprunt": {"type": "number", "description": "Interets d'emprunt immobilier deductibles", "default": 0},
                "charges_copropriete": {"type": "number", "description": "Charges de copropriete (part non recuperable sur locataire)", "default": 0},
                "taxe_fonciere": {"type": "number", "description": "Taxe fonciere (hors ordures menageres si remboursee)", "default": 0},
                "travaux_entretien_annuels": {"type": "number", "description": "Travaux de reparation, entretien et amelioration", "default": 0},
                "frais_gestion_annuels": {"type": "number", "description": "Frais d'agence, de gestion locative", "default": 0},
                "assurance_pno": {"type": "number", "description": "Primes d'assurance proprietaire non-occupant", "default": 0},
                "deficits_fonciers_anterieurs": {"type": "number", "description": "Deficits fonciers des annees anterieures non encore imputes", "default": 0},
                "situation_famille": {"type": "string", "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"], "default": "celibataire"},
                "nb_enfants": {"type": "integer", "default": 0},
                "rni_autres_revenus": {"type": "number", "description": "Autres revenus nets imposables du foyer (salaires, BIC...)", "default": 0},
            },
            "required": ["loyers_bruts_annuels"],
        },
    ),
    Tool(
        name="verifier_actualite_fiscale",
        description=(
            "Verifie si les baremes et donnees fiscales du MCP sont a jour pour une annee donnee. "
            "Liste les parametres cles (tranches IR, PASS, plafonds PER, IS, seuils AE...) "
            "et signale ce qui doit etre mis a jour lors d'un changement d'annee fiscale."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "annee_cible": {
                    "type": "integer",
                    "description": "Annee fiscale a verifier (ex. 2027 pour revenus 2026). Defaut : annee courante du MCP.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="comparer_statuts_professionnel",
        description=(
            "Compare la situation financiere nette entre CDI/CDD et les statuts independants "
            "(auto-entrepreneur, SASU, EURL IS, portage salarial). "
            "Calcule le net en poche apres toutes charges sociales et impots, "
            "identifie le TJM minimum pour egaler un salaire CDI donne, "
            "et formule une recommandation selon le CA et le profil."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "salaire_brut_annuel_cdi": {
                    "type": "number",
                    "description": "Salaire brut annuel actuel ou cible en CDI/CDD (pour comparaison, optionnel)",
                },
                "tjm_freelance": {
                    "type": "number",
                    "description": "Taux journalier moyen envisage en freelance (euros/jour HT)",
                },
                "jours_travailles_an": {
                    "type": "integer",
                    "description": "Nombre de jours factures par an (defaut 200)",
                    "default": 200,
                },
                "ca_annuel": {
                    "type": "number",
                    "description": "CA annuel HT si connu directement (alternatif a TJM x jours)",
                },
                "type_activite": {
                    "type": "string",
                    "enum": ["services_bnc", "services_bic", "vente_marchandises"],
                    "description": "Type d'activite : services_bnc (liberal/conseil/IT), services_bic (artisan/commerce), vente_marchandises",
                    "default": "services_bnc",
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {
                    "type": "integer",
                    "default": 0,
                },
                "charges_pro_annuelles": {
                    "type": "number",
                    "description": "Charges professionnelles deductibles SASU/EURL (loyer bureau, materiel, deplacements...) en euros",
                    "default": 0,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="diagnostiquer_passage_freelance",
        description=(
            "Diagnostic personnalise : est-il interessant de passer freelance (independant) "
            "plutot que de rester en CDI/CDD ? "
            "Analyse la situation financiere, le secteur, l'experience, l'epargne de securite, "
            "le reseau clients et la tolerance au risque. "
            "Produit un score de maturite et une recommandation claire : passer maintenant, "
            "preparer le passage, ou rester salarie. "
            "Calcule le gain net potentiel et le TJM cible selon le profil."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "salaire_brut_annuel_cdi": {
                    "type": "number",
                    "description": "Salaire brut annuel actuel en CDI/CDD (euros)",
                },
                "secteur": {
                    "type": "string",
                    "enum": [
                        "it_dev", "it_conseil_data", "conseil_management",
                        "marketing_communication", "juridique_rh",
                        "btp_artisanat", "sante_paramedical",
                        "formation_coaching", "commerce_vente", "autre",
                    ],
                    "description": (
                        "Secteur d'activite : it_dev (dev/devops/securite), "
                        "it_conseil_data (conseil IT/data/cloud), "
                        "conseil_management (strategie/organisation), "
                        "marketing_communication, juridique_rh, "
                        "btp_artisanat, sante_paramedical, "
                        "formation_coaching, commerce_vente, autre"
                    ),
                    "default": "it_dev",
                },
                "anciennete_ans": {
                    "type": "integer",
                    "description": "Annees d'experience professionnelle dans le secteur",
                    "default": 5,
                },
                "epargne_disponible": {
                    "type": "number",
                    "description": "Epargne de precaution disponible (euros)",
                    "default": 0,
                },
                "clients_potentiels": {
                    "type": "boolean",
                    "description": "Avez-vous deja des prospects, un reseau ou une mission en vue ?",
                    "default": False,
                },
                "situation_famille": {
                    "type": "string",
                    "enum": ["celibataire", "marie", "pacse", "divorce", "veuf"],
                    "default": "celibataire",
                },
                "nb_enfants": {
                    "type": "integer",
                    "default": 0,
                },
                "acceptation_risque": {
                    "type": "string",
                    "enum": ["faible", "moyen", "eleve"],
                    "description": "Tolerance au risque financier et professionnel",
                    "default": "moyen",
                },
                "tjm_vise": {
                    "type": "number",
                    "description": "TJM envisage (euros/jour HT). Si omis, calcule le TJM minimum pour egaliser le CDI.",
                    "default": 0,
                },
                "jours_facturation_an": {
                    "type": "integer",
                    "description": "Jours facturable par an (defaut 180 pour etre conservateur)",
                    "default": 180,
                },
                "charges_mensuelles": {
                    "type": "number",
                    "description": "Charges mensuelles personnelles (loyer, credits, alimentation...) en euros. Aide a calculer le buffer de securite.",
                    "default": 0,
                },
                "type_activite": {
                    "type": "string",
                    "enum": ["services_bnc", "services_bic", "vente_marchandises"],
                    "description": "Type fiscal : services_bnc (liberal/conseil/IT), services_bic (artisan/commerce), vente_marchandises",
                    "default": "services_bnc",
                },
            },
            "required": ["salaire_brut_annuel_cdi"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> List[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        result = await dispatch_tool(name, arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Erreur outil {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Erreur lors de l'exécution de '{name}': {str(e)}")]


_TOOL_DISPATCH = {
    "calculer_impot_revenu":       lambda a: tool_calculer_impot_revenu(a),
    "simuler_tranches_imposition": lambda a: tool_simuler_tranches(a),
    "optimiser_impots":            lambda a: tool_optimiser_impots(a),
    "calculer_economie_per":       lambda a: tool_calculer_economie_per(a),
    "lister_credits_impot":        lambda a: tool_lister_credits(a),
    "lister_reductions_impot":     lambda a: tool_lister_reductions(a),
    "lister_deductions_revenu":    lambda a: tool_lister_deductions(a),
    "lister_epargne_defiscalisante": lambda a: tool_lister_epargne(a),
    "calculer_quotient_familial":  lambda a: tool_calculer_quotient_familial(a),
    "guide_frais_reels":           lambda a: tool_guide_frais_reels(a),
    "calendrier_fiscal":           lambda a: tool_calendrier_fiscal(a),
    "calculer_plus_values":        lambda a: tool_calculer_plus_values(a),
    "info_fiscalite_immobilier":   lambda a: tool_info_immobilier(a),
    "analyser_declaration_revenus": lambda a: tool_analyser_declaration(a),
    "diagnostic_fiscal_complet":   lambda a: tool_diagnostic_complet(a),
    "guide_maprimerenov":          lambda a: tool_guide_maprimerenov(a),
    "checker_eligibilite_aides":   lambda a: tool_checker_eligibilite(a),
    # Nouveaux outils 2026
    "calculer_ifi":                lambda a: tool_calculer_ifi(a),
    "optimiser_tns":               lambda a: tool_optimiser_tns(a),
    "comparer_scenarios":          lambda a: tool_comparer_scenarios(a),
    "calculer_prelevement_source": lambda a: tool_calculer_prelevement_source(a),
    # Nouveaux outils 2.1.0
    "simuler_droits_donation":     lambda a: tool_simuler_droits_donation(a),
    "calculer_succession":         lambda a: tool_calculer_succession(a),
    "simuler_scpi":                lambda a: tool_simuler_scpi(a),
    # Nouveaux outils 2.2.0 — Fiscalité internationale
    "guide_fiscalite_internationale": lambda a: tool_guide_fiscalite_internationale(a),
    "calculer_revenu_etranger":       lambda a: tool_calculer_revenu_etranger(a),
    "guide_frontaliers":              lambda a: tool_guide_frontaliers(a),
    # Nouveaux outils 2.3.0 — Événements de vie, revenus de remplacement, PER sortie
    "guide_evenements_vie":           lambda a: tool_guide_evenements_vie(a),
    "calculer_revenus_remplacement":  lambda a: tool_calculer_revenus_remplacement(a),
    "simuler_sortie_per":             lambda a: tool_simuler_sortie_per(a),
    # Nouveaux outils 2.4.0 — Crypto, Dutreil, SCI
    "calculer_fiscalite_crypto":      lambda a: tool_calculer_fiscalite_crypto(a),
    "simuler_pacte_dutreil":          lambda a: tool_simuler_pacte_dutreil(a),
    "simuler_sci":                    lambda a: tool_simuler_sci(a),
    # Nouveaux outils 2.3.0b — Épargne salariale, IS, Rémunération dirigeant
    "optimiser_epargne_salariale":    lambda a: tool_optimiser_epargne_salariale(a),
    "calculer_impot_societes":        lambda a: tool_calculer_impot_societes(a),
    "optimiser_remuneration_dirigeant": lambda a: tool_optimiser_remuneration_dirigeant(a),
    # Nouveaux outils 2.4.0 — Retraite, Agriculture, Outre-mer
    "simuler_depart_retraite":        lambda a: tool_simuler_depart_retraite(a),
    "guide_fiscalite_agricole":       lambda a: tool_guide_fiscalite_agricole(a),
    "guide_fiscalite_outremer":       lambda a: tool_guide_fiscalite_outremer(a),
    # Nouveaux outils 2.5.0 — Patrimoine, Entreprise, Placements, Indépendants
    "simuler_assurance_vie":          lambda a: tool_simuler_assurance_vie(a),
    "simuler_demembrement":           lambda a: tool_simuler_demembrement(a),
    "simuler_cession_entreprise":     lambda a: tool_simuler_cession_entreprise(a),
    "simuler_holding":                lambda a: tool_simuler_holding(a),
    "calculer_tva":                   lambda a: tool_calculer_tva(a),
    "guide_auto_entrepreneur":        lambda a: tool_guide_auto_entrepreneur(a),
    "calculer_cfe":                   lambda a: tool_calculer_cfe(a),
    "simuler_investissement_pea":     lambda a: tool_simuler_investissement_pea(a),
    "guide_defiscalisation_solidaire": lambda a: tool_guide_defiscalisation_solidaire(a),
    "calculer_pv_immobiliere":        lambda a: tool_calculer_pv_immobiliere(a),
    "guide_taxe_fonciere":            lambda a: tool_guide_taxe_fonciere(a),
    "simuler_reversion_pension":      lambda a: tool_simuler_reversion_pension(a),
    "guide_revision_declaration":     lambda a: tool_guide_revision_declaration(a),
    # Nouveaux outils 2.6.0 — Statuts professionnels, Actualite fiscale
    "comparer_statuts_professionnel": lambda a: tool_comparer_statuts_professionnel(a),
    "verifier_actualite_fiscale":     lambda a: tool_verifier_actualite_fiscale(a),
    # Nouveaux outils 2.7.0 — Revenus exceptionnels, Capital, LMNP, Rachat trimestres, Exit tax, Loc'Avantages, Micro-foncier
    "simuler_revenus_exceptionnels":  lambda a: tool_simuler_revenus_exceptionnels(a),
    "comparer_pfu_bareme_capital":    lambda a: tool_comparer_pfu_bareme_capital(a),
    "simuler_lmnp":                   lambda a: tool_simuler_lmnp(a),
    "simuler_rachat_trimestres":      lambda a: tool_simuler_rachat_trimestres(a),
    "calculer_exit_tax":              lambda a: tool_calculer_exit_tax(a),
    "guide_loc_avantages":            lambda a: tool_guide_loc_avantages(a),
    "simuler_micro_foncier":          lambda a: tool_simuler_micro_foncier(a),
    # Nouveaux outils 2.8.0 — Diagnostic passage freelance
    "diagnostiquer_passage_freelance": lambda a: tool_diagnostiquer_passage_freelance(a),
}


async def dispatch_tool(name: str, args: Dict[str, Any]) -> str:
    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        return f"Outil inconnu: {name}"
    return fn(args)


# ─── Implémentation des outils ────────────────────────────────────────────────

def tool_calculer_impot_revenu(args: Dict) -> str:
    rni = _valider_revenu(float(args["revenu_net_imposable"]), "revenu_net_imposable")
    situation = args["situation_famille"]
    nb_enfants = int(args.get("nb_enfants", 0))
    nb_enfants_ga = int(args.get("nb_enfants_garde_alternee", 0))
    enfants_handicap = int(args.get("enfants_handicap", 0))
    nb_parts_custom = args.get("nb_parts_custom")
    annee = int(args.get("annee", 2026))

    if nb_parts_custom:
        nb_parts = float(nb_parts_custom)
    else:
        nb_parts = calculer_parts(situation, nb_enfants, enfants_handicap, nb_enfants_ga)

    # Bug B — Abattement personnes âgées/invalides
    age = args.get("age_contribuable")
    invalide = args.get("invalide_contribuable", False)
    abattement_special = 0.0
    nb_personnes_abattement = 0
    if age and age >= 65:
        nb_personnes_abattement += 1
    if invalide:
        nb_personnes_abattement += 1
    if nb_personnes_abattement > 0:
        if rni <= 16_750:
            abattement_special = nb_personnes_abattement * 2_620
        elif rni <= 26_970:
            abattement_special = nb_personnes_abattement * 1_310
    rni_apres_abattement = max(0, rni - abattement_special)

    # Bug D — choix du barème selon l'année
    tranches = TRANCHES_IR_2025 if annee == 2025 else TRANCHES_IR_2026
    annee_label = "2025 (revenus 2024)" if annee == 2025 else ANNEE_FISCALE

    res = calculer_ir(rni_apres_abattement, nb_parts, tranches)

    # Bug C — CEHR
    cehr = calculer_cehr(rni, situation)

    lines = [
        f"## Calcul Impôt sur le Revenu {annee_label}",
        "",
        f"**Situation** : {situation.capitalize()} — {nb_parts} parts fiscales",
        f"**Revenu net imposable** : {rni:,.0f}€",
    ]
    if abattement_special > 0:
        lines += [
            f"**Abattement spécial (+65 ans / invalide)** : -{abattement_special:,.0f}€",
            f"**Revenu après abattement spécial** : {rni_apres_abattement:,.0f}€",
        ]
    lines += [
        "",
        "### Résultat",
        f"- Impôt brut (avant décote) : **{res['impot_brut']:,.0f}€**",
    ]
    if res["decote"] > 0:
        lines.append(f"- Décote appliquée : -{res['decote']:,.0f}€")
    lines += [
        f"- **Impôt net à payer : {res['impot_net']:,.0f}€**",
        f"- Taux moyen d'imposition : {res['taux_moyen']:.1f}%",
        f"- Taux marginal d'imposition (TMI) : **{res['taux_marginal']:.0f}%**",
    ]
    if cehr > 0:
        lines += [
            f"- **CEHR (Contribution Exceptionnelle Hauts Revenus) : {cehr:,.0f}€**",
            f"- **Total IR + CEHR : {res['impot_net'] + cehr:,.0f}€**",
        ]
    lines += [
        "",
        "### Détail par tranche",
    ]
    if res["detail_tranches"]:
        for t in res["detail_tranches"]:
            lines.append(f"- Tranche {t['taux']} sur {t['base']} = {t['impot']}")
    else:
        lines.append("- Non imposable (revenu inférieur au seuil)")

    lines += [
        "",
        "### À savoir",
        "- Le revenu net imposable = revenus bruts - abattement 10% (pour salariés)",
        "- Vérifiez votre avis d'imposition ou simulez sur impots.gouv.fr",
        f"- Avec un TMI de {res['taux_marginal']:.0f}%, chaque euro épargné sur un PER vous économise {res['taux_marginal']:.0f} centimes d'impôt",
    ]
    return "\n".join(lines)


def tool_simuler_tranches(args: Dict) -> str:
    revenu = float(args["revenu_annuel_brut"])
    type_rev = args.get("type_revenu", "net_imposable")

    # Conversions approximatives
    if type_rev == "salaire_brut":
        note = f"Conversion approximative : brut {revenu:,.0f}€ → net {revenu*0.77:,.0f}€ → net imposable {revenu*0.77*0.90:,.0f}€"
        revenu = revenu * 0.77 * 0.90
    elif type_rev == "salaire_net":
        note = f"Net {revenu:,.0f}€ → net imposable après abattement 10% : {revenu*0.90:,.0f}€"
        revenu = revenu * 0.90
    else:
        note = None

    lines = [
        f"## Tranches d'imposition {ANNEE_FISCALE} (barème officiel)",
        "",
        "| Tranche | Taux | Votre revenu dans cette tranche |",
        "|---------|------|----------------------------------|",
    ]

    revenu_restant = revenu
    for tranche in TRANCHES_IR_ACTIF:
        max_t = tranche["max"] if tranche["max"] else float('inf')
        label_max = f"{tranche['max']:,}€" if tranche["max"] else "∞"
        label = f"{tranche['min']:,}€ → {label_max}"
        taux = f"{tranche['taux']*100:.0f}%"
        montant = min(max(revenu - tranche["min"], 0), (max_t - tranche["min"]) if tranche["max"] else float('inf'))
        montant = max(0, montant)
        if montant > 0:
            position = f"**{montant:,.0f}€** ← votre revenu ici"
        elif revenu < tranche["min"]:
            position = "— (hors tranche)"
        else:
            position = "0€"
        lines.append(f"| {label} | {taux} | {position} |")

    if note:
        lines += ["", f"ℹ️ {note}"]

    lines += [
        "",
        "### Important",
        "- Le barème est **progressif** : chaque tranche s'applique uniquement à la partie du revenu qui y tombe",
        "- Le revenu est divisé par le nombre de **parts fiscales** avant application du barème",
        "- La **décote** peut réduire l'impôt pour les revenus modestes",
    ]
    return "\n".join(lines)


def tool_optimiser_impots(args: Dict) -> str:
    rni = float(args["revenu_net_imposable"])
    situation = args["situation_famille"]
    nb_enfants = int(args.get("nb_enfants", 0))
    a_employe = args.get("a_employe_domicile", False)
    a_enfant_bas_age = args.get("a_enfant_moins_6ans", False)
    versements_per = float(args.get("versements_per", 0))
    a_locatif = args.get("a_investissement_locatif", False)
    fait_dons = args.get("fait_des_dons", False)
    type_contrib = args.get("type_contribuable", "salarie")

    nb_parts = calculer_parts(situation, nb_enfants)
    res = calculer_ir(rni, nb_parts)
    tmi = res["taux_marginal"]
    impot = res["impot_net"]

    # Calcul plafond PER
    plafond_per = min(rni * PLAFOND_PER_POURCENTAGE, PLAFOND_PER_MAX_2025)
    plafond_per_restant = max(0, plafond_per - versements_per)

    lines = [
        "## Stratégies d'optimisation fiscale — Analyse personnalisée",
        "",
        f"**Votre situation** : {situation.capitalize()}, {nb_parts} parts, TMI {tmi:.0f}%",
        f"**Impôt estimé** : {impot:,.0f}€ sur {rni:,.0f}€ de revenu net imposable",
        "",
        "---",
        "",
        "### Recommandations par priorité",
        "",
    ]

    prio = 1

    # PER — toujours pertinent si TMI >= 11%
    if tmi >= 11 and plafond_per_restant > 0:
        economie_per_exemple = min(plafond_per_restant, 3000) * tmi / 100
        lines += [
            f"#### {prio}. Plan d'Épargne Retraite (PER) ⭐ PRIORITAIRE",
            f"- Plafond déductible restant : **{plafond_per_restant:,.0f}€**",
            f"- Économie si vous versez 3 000€ : **~{economie_per_exemple:,.0f}€** d'impôt en moins",
            f"- Principe : chaque euro versé économise {tmi:.0f}€ de centimes d'impôt (votre TMI)",
            "- Argent disponible à la retraite (capital ou rente)",
            "- ✅ À faire avant le **31 décembre** de l'année fiscale",
            "",
        ]
        prio += 1

    # Emploi à domicile
    if not a_employe:
        lines += [
            f"#### {prio}. Emploi à domicile — Crédit d'impôt 50%",
            "- Ménage, jardinage, garde d'enfants, soutien scolaire...",
            "- **50% des dépenses** remboursées en crédit d'impôt",
            "- Plafond : 12 000€ de dépenses (soit 6 000€ de crédit max)",
            "- ✅ Même si vous ne payez pas d'impôt, le crédit est remboursé",
            "",
        ]
        prio += 1
    else:
        lines += [
            f"#### {prio}. Emploi à domicile — Vérifiez votre déclaration",
            "- Vous utilisez déjà ce crédit. Vérifiez que toutes les dépenses sont déclarées.",
            "- Pensez à augmenter le plafond si vous avez des enfants ou des parents à charge.",
            "",
        ]
        prio += 1

    # Garde enfant bas âge
    if a_enfant_bas_age:
        lines += [
            f"#### {prio}. Crédit garde d'enfants hors domicile (crèche/assistante maternelle)",
            "- **50% des frais** de garde en crédit d'impôt",
            "- Plafond : 3 500€ par enfant (soit 1 750€ de crédit max)",
            "- ✅ Cumulable avec le crédit emploi à domicile",
            "",
        ]
        prio += 1

    # Dons
    if not fait_dons:
        lines += [
            f"#### {prio}. Dons aux associations — Réduction jusqu'à 75%",
            "- Dons aux Restos du Cœur, Croix-Rouge... : **75%** de réduction (jusqu'à 1 000€ de dons)",
            "- Autres associations reconnues d'utilité publique : **66%**",
            "- Exemple : 100€ de don → 75€ de réduction d'impôt (vous ne débourser que 25€ net)",
            "- ✅ À déclarer case 7UD/7UF",
            "",
        ]
        prio += 1
    else:
        lines += [
            f"#### {prio}. Dons — Optimisez vos dons",
            "- Vous faites des dons. Pensez aux organismes éligibles au taux de 75%.",
            "- Le plafond est de 1 000€ à 75% puis 66% au-delà.",
            "",
        ]
        prio += 1

    # Frais réels (salariés)
    if type_contrib in ["salarie", "mixte"]:
        lines += [
            f"#### {prio}. Frais réels professionnels",
            "- Si vos frais > 10% de votre salaire net, les frais réels sont plus avantageux",
            "- Incluez : frais kilométriques, repas, formation, matériel...",
            f"- Abattement forfaitaire actuel : 10% du salaire (max 14 426€)",
            "- Utilisez l'outil **guide_frais_reels** pour simuler",
            "",
        ]
        prio += 1

    # Épargne défiscalisée
    lines += [
        f"#### {prio}. Maximisez votre épargne défiscalisée",
        "- **Livret A** : 1,5% sans impôt ni prélèvements sociaux (plafond 22 950€)",
    ]
    if rni / nb_parts < 23_028:
        lines.append("- **LEP** : vous semblez éligible ! 2,5% défiscalisé (plafond 10 000€) — vérifiez sur impots.gouv.fr")
    lines += [
        "- **PEA** : plus-values exonérées après 5 ans (plafond 150 000€)",
        "- **Assurance-vie** : exonération après 8 ans (abattement 4 600€/9 200€ par an)",
        "",
    ]
    prio += 1

    # Investissement locatif
    if a_locatif:
        lines += [
            f"#### {prio}. Optimisez votre investissement locatif",
            "- **Location nue** : régime micro-foncier (30% abattement) si < 15 000€ de loyers",
            "- Ou régime réel : déduisez charges, travaux, intérêts d'emprunt",
            "- **LMNP** : location meublée avec amortissement du bien (régime réel)",
            "- Déficit foncier : jusqu'à 10 700€ déductible du revenu global",
            "- Utilisez l'outil **info_fiscalite_immobilier** pour plus de détails",
            "",
        ]
        prio += 1

    lines += [
        "---",
        "",
        "### Récapitulatif des gains potentiels estimés",
        "",
        f"| Stratégie | Économie estimée |",
        f"|-----------|-----------------|",
    ]
    if tmi >= 11 and plafond_per_restant > 0:
        lines.append(f"| PER (versement 3 000€) | ~{3000*tmi/100:,.0f}€ |")
    lines += [
        "| Emploi domicile (5 000€ dépenses) | ~2 500€ (crédit 50%) |",
        "| Dons (200€) | ~150€ (réduction 75%) |",
        "",
        "> ⚠️ Ces chiffres sont des estimations. Consultez un conseiller fiscal pour votre situation exacte.",
        "> 📋 Toutes ces stratégies sont **légales** et prévues par le Code Général des Impôts.",
    ]
    return "\n".join(lines)


def tool_calculer_economie_per(args: Dict) -> str:
    rni = float(args["revenu_net_imposable"])
    situation = args["situation_famille"]
    nb_enfants = int(args.get("nb_enfants", 0))
    versement = float(args["montant_versement"])
    revenu_pro = float(args.get("revenu_pro_net", rni))

    nb_parts = calculer_parts(situation, nb_enfants)

    # Plafond PER
    plafond_per = min(revenu_pro * PLAFOND_PER_POURCENTAGE, PLAFOND_PER_MAX_2025)
    plafond_effectif = max(plafond_per, PLAFOND_PER_MIN_2025)

    versement_deductible = min(versement, plafond_effectif)

    # Impôt avant et après
    res_avant = calculer_ir(rni, nb_parts)
    rni_apres = max(0, rni - versement_deductible)
    res_apres = calculer_ir(rni_apres, nb_parts)

    economie = res_avant["impot_net"] - res_apres["impot_net"]
    taux_retour = (economie / versement_deductible * 100) if versement_deductible > 0 else 0

    lines = [
        "## Simulation PER — Plan d'Épargne Retraite",
        "",
        f"**Versement envisagé** : {versement:,.0f}€",
        f"**Plafond déductible 2025** : {plafond_effectif:,.0f}€",
    ]

    if versement > plafond_effectif:
        lines.append(f"⚠️ Versement réduit au plafond : {versement_deductible:,.0f}€")

    lines += [
        "",
        "### Comparaison avant/après versement PER",
        "",
        f"| | Avant PER | Après PER |",
        f"|--|-----------|-----------|",
        f"| Revenu imposable | {rni:,.0f}€ | {rni_apres:,.0f}€ |",
        f"| Impôt dû | {res_avant['impot_net']:,.0f}€ | {res_apres['impot_net']:,.0f}€ |",
        f"| TMI | {res_avant['taux_marginal']:.0f}% | {res_apres['taux_marginal']:.0f}% |",
        "",
        f"### Économie réalisée : **{economie:,.0f}€** d'impôt en moins",
        f"- Taux de retour fiscal : **{taux_retour:.1f}%** (pour {versement_deductible:,.0f}€ versés)",
        f"- Coût réel du versement : **{versement_deductible - economie:,.0f}€**",
        "",
        "### Comment ça marche",
        "- Vous versez sur votre PER → votre revenu imposable baisse → vous payez moins d'impôts",
        "- L'argent est bloqué jusqu'à la retraite (sauf cas exceptionnels : achat résidence principale, invalidité...)",
        "- À la retraite : imposition sur les retraits (souvent à un TMI plus faible)",
        "",
        "### Astuce : Plafonds non utilisés",
        "- Vous pouvez utiliser les plafonds PER des 3 dernières années non utilisés",
        "- Consultez votre avis d'imposition (rubrique « Plafonds épargne retraite »)",
        "",
        "⚠️ Vérifiez votre plafond exact sur votre avis d'imposition avant de verser.",
    ]
    return "\n".join(lines)


def tool_lister_credits(args: Dict) -> str:
    filtre = args.get("filtre", "").lower()

    lines = [
        "## Crédits d'impôt 2026 pour les particuliers",
        "",
        "> Un crédit d'impôt est remboursé même si vous ne payez pas d'impôt (contrairement à une réduction).",
        "",
    ]
    for key, credit in CREDITS_IMPOT.items():
        if filtre and filtre not in key.lower() and filtre not in credit["nom"].lower():
            continue
        lines += [
            f"### {credit['nom']}",
            f"- **Taux** : {credit['taux']*100:.0f}%" if isinstance(credit.get("taux"), float) else f"- **Taux** : {credit.get('taux', 'variable')}",
        ]
        if credit.get("plafond_depenses"):
            lines.append(f"- **Plafond dépenses** : {credit['plafond_depenses']:,}€")
        if credit.get("credit_max") and isinstance(credit["credit_max"], (int, float)):
            lines.append(f"- **Crédit max** : {credit['credit_max']:,}€")
        elif credit.get("credit_max"):
            lines.append(f"- **Crédit max** : {credit['credit_max']}")
        lines += [
            f"- **Conditions** : {credit['conditions']}",
            f"- *Référence* : {credit.get('article', '')}",
            "",
        ]
    return "\n".join(lines)


def tool_lister_reductions(args: Dict) -> str:
    filtre = args.get("filtre", "").lower()

    lines = [
        "## Réductions d'impôt 2026 pour les particuliers",
        "",
        "> Une réduction d'impôt diminue l'impôt mais n'est pas remboursable (contrairement au crédit).",
        "> Si la réduction dépasse l'impôt dû, le surplus est perdu (sauf exceptions).",
        "",
    ]
    for key, red in REDUCTIONS_IMPOT.items():
        if filtre and filtre not in key.lower() and filtre not in red["nom"].lower():
            continue
        taux_display = f"{red['taux']*100:.0f}%" if isinstance(red.get("taux"), float) else red.get("taux", "variable")
        lines += [
            f"### {red['nom']}",
            f"- **Taux** : {taux_display}",
        ]
        if red.get("plafond_depenses"):
            lines.append(f"- **Plafond dépenses** : {red['plafond_depenses']:,}€")
        lines += [
            f"- **Conditions** : {red['conditions']}",
            f"- *Référence* : {red.get('article', '')}",
            "",
        ]
    return "\n".join(lines)


def tool_lister_deductions(args: Dict) -> str:
    lines = [
        "## Déductions du revenu imposable 2026",
        "",
        "> Les déductions réduisent votre revenu imposable AVANT le calcul de l'impôt.",
        "> Plus votre TMI est élevé, plus l'effet est important.",
        "",
    ]
    for key, ded in DEDUCTIONS_REVENU.items():
        lines += [f"### {ded['nom']}", f"- {ded['description']}"]
        if "plafond_annuel" in ded:
            lines.append(f"- Plafond : {ded['plafond_annuel']:,}€/an")
        if "plafond_enfant_majeur" in ded:
            lines.append(f"- Plafond par enfant majeur : {ded['plafond_enfant_majeur']:,}€")
        if "exemples" in ded:
            lines.append("- Exemples : " + ", ".join(ded["exemples"]))
        if "article" in ded:
            lines.append(f"- *{ded['article']}*")
        lines.append("")
    return "\n".join(lines)


def tool_lister_epargne(args: Dict) -> str:
    lines = [
        "## Épargne défiscalisante 2026",
        "",
        "> Classés du plus avantageux fiscalement au moins.",
        "",
    ]
    for key, ep in EPARGNE_FISCALE.items():
        lines += [
            f"### {ep['nom']} ({key})",
            f"- **Avantage** : {ep['avantage']}",
        ]
        if ep.get("plafond"):
            lines.append(f"- **Plafond** : {ep['plafond']}")
        if ep.get("plafond_2024"):
            lines.append(f"- **Plafond 2024** : {ep['plafond_2024']}")
        if ep.get("conditions"):
            lines.append(f"- **Conditions** : {ep['conditions']}")
        lines += [
            f"- **Sortie** : {ep.get('sortie', 'Libre')}",
            f"- *{ep.get('article', '')}*",
            "",
        ]
    return "\n".join(lines)


def tool_calculer_quotient_familial(args: Dict) -> str:
    situation = args["situation_famille"]
    nb_enfants = int(args.get("nb_enfants", 0))
    enfants_handicap = int(args.get("enfants_handicap", 0))
    invalide = args.get("invalide_contribuable", False)
    ancien_combattant = args.get("ancien_combattant", False)

    parts = calculer_parts(situation, nb_enfants, enfants_handicap)
    if invalide:
        parts += 0.5
    if ancien_combattant:
        parts += 0.5

    lines = [
        "## Calcul du Quotient Familial",
        "",
        f"**Situation** : {situation.capitalize()}",
        f"**Enfants à charge** : {nb_enfants} (dont {enfants_handicap} en situation de handicap)",
        "",
        "### Décomposition des parts",
        f"- Part(s) de base ({situation}) : {2.0 if situation in ['marie','pacse'] else 1.0}",
    ]

    parts_enfants = 0.0
    for i in range(1, nb_enfants + 1):
        if i <= 2:
            parts_enfants += 0.5
        else:
            parts_enfants += 1.0
    if parts_enfants > 0:
        lines.append(f"- Parts pour {nb_enfants} enfant(s) : +{parts_enfants}")

    if situation in ["celibataire", "divorce"] and nb_enfants > 0:
        lines.append("- Parent isolé avec enfant(s) : +0,5 part")

    if enfants_handicap > 0:
        lines.append(f"- Enfant(s) handicapé(s) ({enfants_handicap}) : +{enfants_handicap * 0.5}")

    if invalide:
        lines.append("- Invalidité contribuable : +0,5 part")
    if ancien_combattant:
        lines.append("- Ancien combattant : +0,5 part")

    lines += [
        "",
        f"### **Total : {parts} parts fiscales**",
        "",
        "### Impact fiscal",
        f"- Le revenu imposable est divisé par {parts} avant application du barème",
        f"- Puis l'impôt calculé est multiplié par {parts}",
        "- Plus le nombre de parts est élevé, moins vous payez d'impôt",
        "",
        "> Plafond du quotient familial : la réduction liée aux enfants ne peut pas dépasser",
        f"> {PLAFOND_DEMI_PART:,}€ par demi-part supplémentaire.",
    ]
    return "\n".join(lines)


def tool_guide_frais_reels(args: Dict) -> str:
    salaire_net = float(args["salaire_net_annuel"])
    distance_km = float(args.get("distance_domicile_travail_km", 0))
    nb_jours = int(args.get("nb_jours_travail", 220))
    type_vehicule = args.get("type_vehicule", "voiture")
    cv = int(args.get("puissance_fiscale", 5))

    abattement_auto = min(salaire_net * 0.10, 14_426)
    abattement_auto = max(abattement_auto, 495)

    lines = [
        "## Guide Frais Réels Professionnels",
        "",
        f"**Abattement forfaitaire automatique** : {abattement_auto:,.0f}€",
        "(10% du salaire net, min 495€, max 14 426€)",
        "",
        "### Quand opter pour les frais réels ?",
        f"Si vos frais réels dépassent {abattement_auto:,.0f}€",
        "",
    ]

    # Calcul frais kilométriques si renseigné
    if distance_km > 0:
        # Barème kilométrique 2024 (voiture 5CV à titre d'exemple)
        bareme = {
            "voiture": {
                3: (0.456, 0.272, 0.318),
                4: (0.523, 0.311, 0.364),
                5: (0.548, 0.326, 0.381),
                6: (0.574, 0.342, 0.400),
                7: (0.601, 0.358, 0.418),
            },
            "moto": {
                1: (0.395, 0.099, 0.209),
                2: (0.468, 0.117, 0.247),
                3: (0.606, 0.151, 0.320),
                5: (0.606, 0.151, 0.320),
            },
        }

        km_annuels = distance_km * 2 * nb_jours  # aller-retour

        if type_vehicule == "voiture":
            cv_key = min(cv, 7) if cv <= 7 else 7
            cv_key = max(cv_key, 3)
            taux_km = bareme["voiture"].get(cv_key, bareme["voiture"][5])
            if km_annuels <= 5_000:
                indemnite = km_annuels * taux_km[0]
            elif km_annuels <= 20_000:
                indemnite = km_annuels * taux_km[1] + 5_000 * (taux_km[0] - taux_km[1])
            else:
                indemnite = km_annuels * taux_km[2]
        elif type_vehicule == "moto":
            cv_key = min(cv, 5) if cv >= 3 else (2 if cv == 2 else 1)
            taux_km = bareme["moto"].get(cv_key, (0.395, 0.099, 0.209))
            if km_annuels <= 3_000:
                indemnite = km_annuels * taux_km[0]
            elif km_annuels <= 6_000:
                indemnite = km_annuels * taux_km[1] + 3_000 * (taux_km[0] - taux_km[1])
            else:
                indemnite = km_annuels * taux_km[2]
        else:  # velo_electrique
            indemnite = km_annuels * 0.25  # forfait

        lines += [
            f"### Frais kilométriques estimés ({type_vehicule} {cv}CV)",
            f"- Distance : {distance_km} km × 2 × {nb_jours} jours = {km_annuels:,.0f} km/an",
            f"- **Indemnité kilométrique : {indemnite:,.0f}€**",
            "",
        ]

        if indemnite > abattement_auto:
            lines.append(f"✅ Les frais kilométriques seuls ({indemnite:,.0f}€) dépassent l'abattement automatique ({abattement_auto:,.0f}€).")
            lines.append("**Les frais réels sont avantageux pour vous !**")
        else:
            lines.append(f"ℹ️ Les frais kilométriques ({indemnite:,.0f}€) ne dépassent pas l'abattement automatique.")
            lines.append("Ajoutez les autres frais réels pour comparer.")

    lines += [
        "",
        "### Quels frais peut-on déduire ?",
        "- **Transport** : frais kilométriques (barème officiel), transports en commun, parking",
        "- **Repas** : si vous ne pouvez pas rentrer déjeuner (forfait ~5€/repas)",
        "- **Formation** : frais de formation professionnelle",
        "- **Matériel** : outillage, vêtements professionnels spécifiques",
        "- **Double résidence** : si mutation ou emploi éloigné du domicile",
        "- **Télétravail** : internet, bureau à domicile (au prorata)",
        "",
        "### Comment déclarer",
        "1. Cochez la case 1AK (ou 1BK) dans votre déclaration",
        "2. Listez tous vos frais avec justificatifs",
        "3. Déclarez le montant total case 1AK à la place de l'abattement",
        "4. Conservez tous les justificatifs 3 ans",
        "",
        "> ⚠️ Les frais réels annulent l'abattement forfaitaire 10% — à vous de choisir le plus avantageux.",
    ]
    return "\n".join(lines)


def tool_calendrier_fiscal(args: Dict) -> str:
    filtre_urgent = args.get("filtre_urgent", False)

    lines = [
        "## Calendrier Fiscal 2026 (déclaration des revenus 2025)",
        "",
        "> ⚠️ Dates estimées — vérifiez les dates exactes sur impots.gouv.fr",
        "",
    ]
    for evt in CALENDRIER_FISCAL_2026:
        if filtre_urgent and not evt["important"]:
            continue
        flag = "🔴" if evt["important"] else "📅"
        lines.append(f"{flag} **{evt['date']}** — {evt['evenement']}")

    lines += [
        "",
        "### Liens utiles",
        "- Déclaration en ligne : impots.gouv.fr",
        "- Simulation impôt : impots.gouv.fr/simulateur",
        "- MaPrimeRénov' : maprimerenov.gouv.fr",
    ]
    return "\n".join(lines)


def tool_calculer_plus_values(args: Dict) -> str:
    type_actif = args["type_actif"]
    pv = float(args["montant_plus_value"])
    duree = float(args.get("duree_detention_ans", 0))
    rni = float(args.get("revenu_net_imposable", 30_000))

    lines = [
        f"## Fiscalité des Plus-Values — {type_actif.replace('_', ' ').title()}",
        "",
        f"**Plus-value brute** : {pv:,.0f}€",
        f"**Durée de détention** : {duree:.1f} ans",
        "",
    ]

    if type_actif == "actions_hors_pea":
        ir = pv * 0.128  # 12,8% PFU
        ps = pv * 0.172  # 17,2% PS
        total = ir + ps
        lines += [
            "### Fiscalité des actions (hors PEA)",
            "**Prélèvement Forfaitaire Unique (PFU) = 30%** (flat tax)",
            f"- IR 12,8% : {ir:,.0f}€",
            f"- Prélèvements sociaux 17,2% : {ps:,.0f}€",
            f"- **Total : {total:,.0f}€**",
            "",
            "### Alternative : barème progressif",
            "Vous pouvez opter pour le barème progressif si votre TMI est inférieur à 12,8%",
            "(Option globale — s'applique à tous vos revenus du capital)",
            "",
            "### Conseil : Utilisez le PEA !",
            "- Après 5 ans, les plus-values sont exonérées d'IR (seulement 17,2% de PS)",
            f"- Économie si PEA : {ir:,.0f}€ d'IR économisé",
        ]

    elif type_actif == "immobilier_residence_principale":
        lines += [
            "### Plus-value résidence principale",
            "✅ **EXONÉRÉE** d'impôt et de prélèvements sociaux",
            "Conditions : logement constituait votre résidence principale au jour de la cession",
            "",
            "Cette exonération est totale, quel que soit le montant de la plus-value.",
        ]

    elif type_actif == "immobilier_locatif":
        # Abattements pour durée de détention
        if duree < 6:
            abatt_ir = 0.0
            abatt_ps = 0.0
        elif duree < 22:
            abatt_ir = min((duree - 5) * 6, 100) / 100  # 6% par an de 6 à 21 ans
            abatt_ps = min((duree - 5) * 1.65, 100) / 100
        else:
            abatt_ir = 1.0  # exonéré IR après 22 ans
            abatt_ps = min(1.65 * 17 + 9 * (min(duree, 30) - 22), 100) / 100  # simplif.

        pv_imposable_ir = pv * (1 - abatt_ir)
        pv_imposable_ps = pv * (1 - abatt_ps)
        ir = pv_imposable_ir * 0.19
        ps = pv_imposable_ps * 0.172
        total = ir + ps

        lines += [
            "### Plus-value immobilière (bien locatif)",
            f"- Abattement IR après {duree:.0f} ans : {abatt_ir*100:.0f}%",
            f"- Base imposable IR : {pv_imposable_ir:,.0f}€ → IR à 19% : {ir:,.0f}€",
            f"- Abattement PS après {duree:.0f} ans : {abatt_ps*100:.0f}%",
            f"- Base imposable PS : {pv_imposable_ps:,.0f}€ → PS à 17,2% : {ps:,.0f}€",
            f"- **Total impôts : {total:,.0f}€**",
            "",
            "### Exonérations selon durée de détention",
            "- IR : totalement exonéré après **22 ans**",
            "- PS : totalement exonéré après **30 ans**",
            "- Abattements progressifs à partir de la **6ème année**",
        ]

    elif type_actif == "cryptomonnaie":
        taux = 0.30  # PFU 30%
        total = pv * taux
        lines += [
            "### Fiscalité des cryptomonnaies",
            "**PFU 30%** sur les cessions (flat tax depuis 2023)",
            f"- Impôt : {pv:,.0f}€ × 30% = **{total:,.0f}€**",
            "",
            "### Important pour les crypto",
            "- Imposable uniquement lors de la **conversion en euros** (ou autre monnaie fiat)",
            "- Échange crypto/crypto : non imposable",
            "- Seuil de cession total < 305€ dans l'année : exonéré",
            "- Déclaration obligatoire même si pas de gains : comptes à l'étranger",
            "",
            "### Déclaration",
            "- Formulaire 2086 pour le détail des cessions",
            "- Case 3AN (gains) ou 3BN (moins-values) de la déclaration 2042C",
        ]

    return "\n".join(lines)


def tool_info_immobilier(args: Dict) -> str:
    type_loc = args["type_location"]
    loyers = float(args.get("loyers_annuels", 0))
    charges = float(args.get("charges_annuelles", 0))

    lines = [
        "## Fiscalité Immobilière — Particuliers",
        "",
    ]

    if type_loc == "nue":
        lines += [
            "### Location Nue (revenus fonciers)",
            "",
            "**Régime micro-foncier** (si loyers < 15 000€/an)",
            "- Abattement forfaitaire de **30%**",
            f"- Si loyers = {loyers:,.0f}€ → imposable : {loyers*0.70:,.0f}€",
            "",
            "**Régime réel** (obligatoire si loyers > 15 000€ ou sur option)",
            "- Déduisez toutes les charges réelles : intérêts d'emprunt, travaux, assurances, frais gestion",
        ]
        if charges > 0:
            resultat = loyers - charges
            if resultat < 0:
                lines += [
                    f"- Loyers {loyers:,.0f}€ - Charges {charges:,.0f}€ = **Déficit {abs(resultat):,.0f}€**",
                    f"- Déficit imputable sur revenu global : jusqu'à **10 700€/an**",
                    f"- Excédent reportable 10 ans sur revenus fonciers",
                ]
            else:
                lines += [
                    f"- Loyers {loyers:,.0f}€ - Charges {charges:,.0f}€ = Bénéfice {resultat:,.0f}€",
                    "- Ce bénéfice s'ajoute à votre revenu imposable",
                ]

    elif type_loc == "meublee_lmnp":
        lines += [
            "### Location Meublée Non Professionnelle (LMNP)",
            "",
            "**Régime micro-BIC — depuis LF 2024**",
            "- LMNP classique (non touristique) : abattement **50%** si recettes < 77 700€/an",
            f"  → Si loyers = {loyers:,.0f}€ → imposable : {loyers*0.50:,.0f}€",
            "- Meublé de tourisme **non classé** : abattement **30%**, seuil ramené à 15 000€/an (depuis 2024)",
            "- Meublé de tourisme **classé** : abattement **71%**, seuil 188 700€/an",
            "",
            "**Régime réel** (recommandé si charges importantes)",
            "- Déduisez : charges courantes + **amortissement du bien et du mobilier**",
            "- L'amortissement génère souvent un résultat nul → **pas d'impôt sur les loyers**",
            "- Résultat déficitaire : non imputable sur revenu global (report sur BIC LMNP)",
            "",
            "### Avantages LMNP réel",
            "- Amortissement du bien sur 25-40 ans (2-4%/an)",
            "- Amortissement du mobilier sur 5-10 ans (10-20%/an)",
            "- Résultat fiscal souvent nul ou déficitaire = 0 impôt sur les loyers",
        ]

    elif type_loc == "meublee_lmp":
        lines += [
            "### Location Meublée Professionnelle (LMP)",
            "(recettes > 23 000€/an ET > 50% des revenus professionnels du foyer)",
            "",
            "**Avantages LMP**",
            "- Déficit imputable sur revenu global (sans limite !)",
            "- Plus-value de cession exonérée après 5 ans d'activité et si recettes < 90 000€",
            "- Exonération IFI sous conditions",
            "",
            "**Inconvénients LMP**",
            "- Soumis aux cotisations sociales (SSI) sur les bénéfices",
            "- Statut professionnel : déclaration BIC obligatoire",
        ]

    elif type_loc == "saisonniere":
        lines += [
            "### Location Saisonnière / Airbnb",
            "",
            "**Meublé de tourisme non classé** — depuis LF 2024",
            "- Abattement **30%** (au lieu de 50% avant 2024), seuil 15 000€/an de recettes",
            "- Au-delà de 15 000€ : régime réel obligatoire",
            "",
            "**Meublé de tourisme classé**",
            f"- Abattement **71%** si recettes < 188 700€/an (régime micro-BIC)",
            "",
            "### Attention",
            "- Déclaration obligatoire en mairie",
            "- Limite 120 nuits/an pour résidence principale",
            "- TVA possible si location para-hôtelière",
        ]

    lines += [
        "",
        "### IFI (Impôt sur la Fortune Immobilière)",
        "- Applicable si patrimoine immobilier net > **1 300 000€**",
        "- Taux de 0,5% à 1,5% sur la valeur nette",
        "- Résidence principale : abattement de 30%",
        "- Biens professionnels (LMP) : exonérés sous conditions",
    ]
    return "\n".join(lines)


def tool_checker_eligibilite(args: Dict) -> str:
    rfr = float(args["revenu_fiscal_reference"])
    nb_parts = float(args.get("nb_parts", 1))
    situation = args["situation_famille"]
    nb_enfants = int(args.get("nb_enfants", 0))
    age = args.get("age")

    rfr_par_part = rfr / nb_parts

    lines = [
        "## Vérification d'éligibilité aux aides et dispositifs",
        "",
        f"**RFR** : {rfr:,.0f}€ — **Nb parts** : {nb_parts} — **RFR/part** : {rfr_par_part:,.0f}€",
        "",
        "### Dispositifs vérifiés",
        "",
    ]

    # LEP — seuils 2026 (source : service-public.fr)
    seuil_lep = {1: 23_028, 2: 35_326, 3: 47_624, 4: 59_922}.get(int(nb_parts), 23_028 + (int(nb_parts)-1)*12_298)
    if rfr <= seuil_lep:
        lines.append(f"✅ **LEP** : Vous êtes éligible ! Ouvrez un Livret d'Épargne Populaire (2,5%, plafond 10 000€)")
    else:
        lines.append(f"❌ **LEP** : Non éligible (RFR {rfr:,.0f}€ > seuil {seuil_lep:,.0f}€)")

    # Non-imposition
    if rfr_par_part < 11_497:
        lines.append(f"✅ **Non-imposition** : Vous n'êtes probablement pas imposable (RFR/part < 11 497€)")
    else:
        lines.append(f"ℹ️ **Imposition** : Vous êtes probablement imposable")

    # Décote
    impot_estime = calculer_ir(rfr, nb_parts)
    if impot_estime["decote"] > 0:
        lines.append(f"✅ **Décote** : Vous bénéficiez d'une décote ({impot_estime['decote']:,.0f}€)")

    # Personnes âgées
    if age and age >= 65:
        lines += [
            f"✅ **Abattement personnes âgées** : +2 620€ d'abattement si RFR ≤ 16 410€",
            "   ou +1 310€ si RFR entre 16 410€ et 26 330€ (par personne de 65 ans et +)",
        ]

    # Prime d'activité (estimation grossière)
    if rfr < 25_000 and situation in ["celibataire", "divorce"]:
        lines.append("ℹ️ **Prime d'activité** : Simulez sur caf.fr — potentiellement éligible selon vos revenus d'activité")
    elif rfr < 40_000:
        lines.append("ℹ️ **Prime d'activité** : Simulez sur caf.fr pour votre situation exacte")

    # Chèque énergie
    seuil_cheque_energie = {1: 11_000, 2: 15_500, 3: 19_000, 4: 22_500}
    seuil_ce = seuil_cheque_energie.get(int(nb_parts), 11_000 + int(nb_parts)*3_500)
    if rfr <= seuil_ce:
        lines.append(f"✅ **Chèque énergie** : Vous devriez recevoir un chèque énergie automatiquement (envoyé par l'État)")
    else:
        lines.append(f"❌ **Chèque énergie** : Probablement non éligible (RFR {rfr:,.0f}€ > seuil estimé)")

    # Aide juridictionnelle
    if rfr < 12_271:
        lines.append("✅ **Aide juridictionnelle** : Probablement éligible (accès gratuit à la justice)")

    lines += [
        "",
        "### Ressources",
        "- **mes-aides.gouv.fr** : simulateur officiel de toutes vos aides",
        "- **caf.fr** : droits CAF (APL, prime activité, allocations familiales)",
        "- **impots.gouv.fr** : votre espace personnel et votre RFR exact",
        "",
        "> ⚠️ Ces vérifications sont indicatives. Consultez impots.gouv.fr et caf.fr pour confirmation.",
    ]
    return "\n".join(lines)


def _get_mpr_categorie(rfr: float, nb_parts: float) -> str:
    """Détermine la catégorie MaPrimeRénov' selon le RFR et les parts."""
    # Interpolation pour les parts non entières
    np_int = min(5, max(1, round(nb_parts * 2) / 2))
    seuils = MPR_SEUILS_2025.get(np_int, MPR_SEUILS_2025[1])
    if rfr <= seuils[0]:
        return "bleu"
    elif rfr <= seuils[1]:
        return "jaune"
    elif rfr <= seuils[2]:
        return "violet"
    else:
        return "rose"


def tool_analyser_declaration(args: Dict) -> str:
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    nb_parts = float(args.get("nb_parts", calculer_parts(situation, nb_enfants)))

    # Revenus déclarés
    sal1 = float(args.get("case_1AJ", 0))
    sal2 = float(args.get("case_1BJ", 0))
    frais1 = float(args.get("case_1AK", 0))
    frais2 = float(args.get("case_1BK", 0))
    rev_foncier = float(args.get("case_4BA", 0) or args.get("case_4BE", 0) * 0.70)
    rev_cap = float(args.get("case_2DC", 0)) + float(args.get("case_2TR", 0))
    pv = float(args.get("case_3VG", 0))
    per1 = float(args.get("case_6NS", 0))
    per2 = float(args.get("case_6NT", 0))
    garde = float(args.get("case_7DB", 0))
    domicile = float(args.get("case_7DF", 0))
    dons_75 = float(args.get("case_7UD", 0))
    dons_66 = float(args.get("case_7UF", 0))
    rfr = float(args.get("revenu_fiscal_reference", (sal1 + sal2) * 0.9))

    total_salaires = sal1 + sal2
    total_per = per1 + per2

    lines = [
        "## Analyse de votre Déclaration de Revenus",
        "",
        "### Récapitulatif des données saisies",
        f"- Salaires déclarés : {total_salaires:,.0f}€",
    ]
    if frais1 or frais2:
        lines.append(f"- Frais réels : {frais1 + frais2:,.0f}€ (option activée)")
    else:
        abatt = min(total_salaires * 0.10, 14_426)
        lines.append(f"- Abattement 10% automatique : {abatt:,.0f}€")
    if rev_foncier:
        lines.append(f"- Revenus fonciers nets : {rev_foncier:,.0f}€")
    if rev_cap:
        lines.append(f"- Revenus de capitaux : {rev_cap:,.0f}€")
    if total_per:
        lines.append(f"- Versements PER déduits : {total_per:,.0f}€")
    if garde:
        lines.append(f"- Garde d'enfants (7DB) : {garde:,.0f}€ → crédit {garde*0.5:,.0f}€")
    if domicile:
        lines.append(f"- Emploi domicile (7DF) : {domicile:,.0f}€ → crédit {domicile*0.5:,.0f}€")
    if dons_75 or dons_66:
        red = dons_75 * 0.75 + dons_66 * 0.66
        lines.append(f"- Dons : {dons_75+dons_66:,.0f}€ → réduction {red:,.0f}€")

    lines += ["", "---", "", "### Alertes et optimisations identifiées", ""]

    alertes = []
    conseils = []

    # Vérification frais réels
    if not frais1 and sal1 > 0:
        seuil_fr = sal1 * 0.10
        alertes.append(
            f"❓ **Frais réels non déclarés** (déclarant 1) : si vos frais réels dépassent "
            f"{seuil_fr:,.0f}€ (10% de {sal1:,.0f}€), l'option frais réels est avantageuse. "
            "Vérifiez vos frais de transport, repas, formation."
        )

    if not frais2 and sal2 > 0:
        seuil_fr2 = sal2 * 0.10
        alertes.append(
            f"❓ **Frais réels non déclarés** (déclarant 2) : vérifiez si vos frais dépassent {seuil_fr2:,.0f}€."
        )

    # PER
    plafond_per_est = min(total_salaires * 0.10, PLAFOND_PER_MAX_2025)
    if total_per < plafond_per_est * 0.5:
        pot = plafond_per_est - total_per
        conseils.append(
            f"💡 **PER sous-utilisé** : votre plafond estimé est {plafond_per_est:,.0f}€, "
            f"vous n'avez versé que {total_per:,.0f}€. "
            f"Il reste {pot:,.0f}€ de plafond pour réduire votre impôt. "
            "(Consultez votre avis d'imposition pour le plafond exact)"
        )
    elif total_per == 0:
        conseils.append(
            f"💡 **Aucun versement PER** : pensez au PER pour réduire votre revenu imposable. "
            f"Plafond estimé : {plafond_per_est:,.0f}€."
        )

    # Garde d'enfants
    if garde == 0 and nb_enfants > 0:
        alertes.append(
            "❓ **Garde d'enfants non déclarée** (case 7DB) : si vous avez des enfants < 6 ans "
            "en crèche ou chez assistante maternelle, déclarez les frais pour obtenir 50% en crédit d'impôt."
        )

    # Emploi domicile
    if domicile == 0:
        conseils.append(
            "💡 **Emploi à domicile** (case 7DF) : ménage, jardinage, garde d'enfants, soutien scolaire... "
            "50% de crédit d'impôt. Si vous utilisez ces services, déclarez-les !"
        )

    # Dons
    if dons_75 == 0 and dons_66 == 0:
        conseils.append(
            "💡 **Dons non déclarés** (cases 7UD/7UF) : si vous avez fait des dons à des associations, "
            "ils donnent droit à 75% ou 66% de réduction. Vérifiez vos reçus fiscaux."
        )

    # Revenus fonciers
    if args.get("case_4BE") and not args.get("case_4BA"):
        loyers_bruts = float(args.get("case_4BE", 0))
        if loyers_bruts > 15_000:
            alertes.append(
                f"⚠️ **Micro-foncier impossible** : vos loyers ({loyers_bruts:,.0f}€) dépassent "
                "15 000€. Vous devez obligatoirement déclarer au régime réel (case 4BA). "
                "Au réel vous pouvez déduire toutes vos charges réelles."
            )

    # RFR et LEP — seuil 2026
    if rfr > 0:
        seuil_lep = 23_028
        if rfr <= seuil_lep:
            conseils.append(
                f"✅ **LEP éligible** : votre RFR ({rfr:,.0f}€) vous permet d'ouvrir un "
                "Livret d'Épargne Populaire (2,5%, exonéré, plafond 10 000€)."
            )

    for a in alertes:
        lines.append(a)
        lines.append("")
    for c in conseils:
        lines.append(c)
        lines.append("")

    if not alertes and not conseils:
        lines.append("✅ Votre déclaration semble bien optimisée avec les données fournies.")

    lines += [
        "---",
        "",
        "### Prochaines étapes",
        "1. Utilisez `diagnostic_fiscal_complet` pour une analyse plus poussée",
        "2. Utilisez `calculer_economie_per` pour simuler un versement PER",
        "3. Utilisez `guide_maprimerenov` si vous êtes propriétaire avec travaux à envisager",
        "",
        "> ⚠️ Cette analyse est basée sur les données fournies. Consultez impots.gouv.fr ou un conseiller fiscal.",
    ]
    return "\n".join(lines)


def tool_diagnostic_complet(args: Dict) -> str:
    situation = args["situation_famille"]
    salaire = float(args["salaire_net_annuel"])
    age = args.get("age")
    nb_enfants = int(args.get("nb_enfants_charge", 0))
    nb_enfants_bas_age = int(args.get("nb_enfants_moins_6ans", 0))
    parents_charge = args.get("parents_a_charge", False)
    rev_fonciers = float(args.get("revenus_fonciers", 0))
    rev_cap = float(args.get("revenus_capitaux", 0))
    rev_indep = float(args.get("revenu_independant", 0))
    statut_logement = args.get("statut_logement", "locataire")
    dpe = args.get("dpe_actuel", "inconnu")
    surface = args.get("surface_m2")
    travaux_envisages = args.get("travaux_envisages", [])
    budget_travaux = float(args.get("budget_travaux", 0))
    annee_construction = args.get("annee_construction_bien")
    a_pea = args.get("a_pea", False)
    a_av = args.get("a_assurance_vie", False)
    a_per = args.get("a_per", False)
    versements_per = float(args.get("versements_per_annuels", 0))
    a_livret_plein = args.get("a_livret_a_plein", False)
    a_employe = args.get("a_employe_domicile", False)
    dep_domicile = float(args.get("depenses_domicile_annuelles", 0))
    dep_garde = float(args.get("depenses_garde_enfants", 0))
    fait_dons = args.get("fait_des_dons", False)
    montant_dons = float(args.get("montant_dons_annuels", 0))
    a_pension = args.get("a_pension_alimentaire", False)
    type_emploi = args.get("type_emploi", "salarie")
    teletravail = float(args.get("teletravail_jours_semaine", 0))
    dist_travail = float(args.get("distance_travail_km", 0))
    a_credit_immo = args.get("a_credit_immobilier", False)
    patrimoine = args.get("patrimoine_total_estime")

    # Calculs de base
    nb_parts = calculer_parts(situation, nb_enfants)
    revenu_total = salaire + rev_fonciers + rev_cap + rev_indep
    abattement = min(salaire * 0.10, 14_426) if type_emploi != "independant" else 0
    rni_estime = max(0, revenu_total - abattement - versements_per)
    res_ir = calculer_ir(rni_estime, nb_parts)
    tmi = res_ir["taux_marginal"]
    impot = res_ir["impot_net"]

    # RFR approx
    rfr_estime = max(0, revenu_total - versements_per)

    # Catégorie MPR si propriétaire
    mpr_cat = None
    if "proprietaire" in statut_logement:
        mpr_cat = _get_mpr_categorie(rfr_estime, nb_parts)

    lines = [
        "# Diagnostic Fiscal Complet — Rapport Personnalisé",
        "",
        "## Votre situation",
        f"- **Famille** : {situation.capitalize()}, {nb_parts} parts, {nb_enfants} enfant(s)",
        f"- **Revenus estimés** : {revenu_total:,.0f}€/an",
        f"- **Logement** : {statut_logement.replace('_', ' ').capitalize()}",
        f"- **Emploi** : {type_emploi.capitalize()}",
        "",
        "## Estimation fiscale",
        f"- Revenu net imposable estimé : {rni_estime:,.0f}€",
        f"- **Impôt estimé : {impot:,.0f}€**",
        f"- TMI (taux marginal) : **{tmi:.0f}%**",
        f"- Taux moyen : {res_ir['taux_moyen']:.1f}%",
        "",
        "---",
        "",
        "## Recommandations prioritaires",
        "",
    ]

    prio = 1
    economies_totales = 0

    # ── 1. PER ──────────────────────────────────────────────────────────────
    if tmi >= 11:
        plafond_per = min(salaire * 0.10, PLAFOND_PER_MAX_2025)
        restant_per = max(0, plafond_per - versements_per)
        if restant_per > 500:
            economie_per = min(restant_per, 5000) * tmi / 100
            economies_totales += economie_per
            lines += [
                f"### {prio}. Plan d'Épargne Retraite (PER) — PRIORITAIRE ⭐",
                f"- Plafond disponible : **{restant_per:,.0f}€**",
                f"- Économie si versement de 5 000€ : **~{economie_per:,.0f}€**",
                f"- Chaque euro versé économise **{tmi:.0f} centimes** d'impôt (votre TMI)",
                "- Action : verser sur un PER avant le **31 décembre**",
                "",
            ]
            prio += 1

    # ── 2. MaPrimeRénov' ────────────────────────────────────────────────────
    if "proprietaire" in statut_logement and mpr_cat:
        cat_info = MAPRIMERENOV["categories"][mpr_cat]
        aide_estimee = 0
        travaux_str = []

        if travaux_envisages:
            for trav in travaux_envisages:
                t_info = MAPRIMERENOV["travaux"].get(trav, {})
                if t_info:
                    plafond = t_info.get("plafond_aide", t_info.get("plafond_aide_m2", 0))
                    taux_mpr = cat_info.get(f"taux_{trav.split('_')[0]}", cat_info.get("taux_isolation", 0.20))
                    if isinstance(plafond, (int, float)) and plafond > 0:
                        aide_t = plafond * taux_mpr
                        aide_estimee += aide_t
                        travaux_str.append(f"  - {t_info['nom']} : aide ~{aide_t:,.0f}€")
        elif budget_travaux > 0:
            aide_estimee = budget_travaux * cat_info["taux_isolation"] * 0.5  # estimation grossière

        if dpe in ["F", "G"]:
            aide_estimee += MAPRIMERENOV["bonus_sortie_passoire"]
            travaux_str.append(f"  - Bonus sortie passoire thermique (F/G) : +{MAPRIMERENOV['bonus_sortie_passoire']:,}€")

        if aide_estimee > 0 or "proprietaire" in statut_logement:
            lines += [
                f"### {prio}. MaPrimeRénov' — Travaux de rénovation énergétique 🏠",
                f"- **Votre catégorie** : {cat_info['label']}",
                f"- Taux pour isolation : {cat_info['taux_isolation']*100:.0f}%",
                f"- Taux pour pompe à chaleur : {cat_info['taux_pompe_chaleur']*100:.0f}%",
            ]
            if travaux_str:
                lines.append("- **Aides estimées pour vos travaux** :")
                lines += travaux_str
                lines.append(f"- **Total aide estimée : ~{aide_estimee:,.0f}€**")
            else:
                lines += [
                    "- Vous n'avez pas renseigné de travaux. Travaux éligibles : isolation, PAC, chaudière bois...",
                    "- Utilisez `guide_maprimerenov` pour simuler vos travaux précis",
                ]
            if dpe in ["E", "F", "G", "inconnu"] or annee_construction and annee_construction < 1990:
                lines.append("- ⚡ Votre logement semble potentiellement éligible à des travaux prioritaires")
            lines += [
                "- **Action** : Simuler sur maprimerenov.gouv.fr + faire un audit énergétique",
                "- Conditions : résidence principale > 15 ans, entreprise RGE",
                "",
            ]
            prio += 1

    # ── 3. Emploi domicile ──────────────────────────────────────────────────
    if not a_employe or dep_domicile == 0:
        economie_dom = min(12_000, 5_000) * 0.50
        economies_totales += 1_000  # estimatif
        lines += [
            f"### {prio}. Emploi à domicile — Crédit d'impôt 50%",
            "- Ménage, jardinage, soutien scolaire, garde d'enfants à domicile...",
            "- **50% des dépenses** = crédit d'impôt (remboursé même sans impôt)",
            "- Plafond : 12 000€/an + 1 500€ par enfant (max 15 000€)",
            "- Exemple : 200€/mois ménage → crédit 1 200€/an",
            "- Action : déclarez en case **7DF** de votre déclaration",
            "",
        ]
        prio += 1
    elif dep_domicile > 0:
        economie_dom = dep_domicile * 0.50
        economies_totales += economie_dom
        lines += [
            f"### {prio}. Emploi à domicile — Vous êtes sur la bonne voie ✅",
            f"- Dépenses déclarées : {dep_domicile:,.0f}€ → crédit d'impôt {economie_dom:,.0f}€",
            "- Vérifiez que toutes vos dépenses sont bien déclarées",
            "",
        ]
        prio += 1

    # ── 4. Garde enfants ────────────────────────────────────────────────────
    if nb_enfants_bas_age > 0 and dep_garde == 0:
        lines += [
            f"### {prio}. Garde d'enfants — Crédit d'impôt 50%",
            f"- Vous avez {nb_enfants_bas_age} enfant(s) < 6 ans",
            "- Crèche, assistante maternelle : **50% en crédit d'impôt** (case 7DB)",
            f"- Plafond : 3 500€/enfant → crédit max 1 750€/enfant",
            "- Action : déclarez les frais de garde case **7DB**",
            "",
        ]
        prio += 1

    # ── 5. Frais réels ──────────────────────────────────────────────────────
    if type_emploi in ["salarie", "fonctionnaire", "mixte"] and (dist_travail > 30 or teletravail >= 3):
        abatt_auto = min(salaire * 0.10, 14_426)
        km_annuels = dist_travail * 2 * 220 if dist_travail > 0 else 0
        frais_km = km_annuels * 0.381  # 5CV approximatif
        if frais_km > abatt_auto or teletravail >= 3:
            lines += [
                f"### {prio}. Frais Réels Professionnels",
            ]
            if frais_km > abatt_auto:
                lines.append(f"- Frais kilométriques estimés ({km_annuels:,.0f} km) : **{frais_km:,.0f}€ > abattement auto {abatt_auto:,.0f}€**")
                lines.append("- ✅ L'option frais réels semble avantageuse pour vous !")
            if teletravail >= 3:
                lines.append(f"- Télétravail {teletravail:.0f}j/sem : déduisez internet, bureau à domicile, matériel")
            lines += [
                "- Utilisez `guide_frais_reels` pour calculer précisément",
                "",
            ]
            prio += 1

    # ── 6. Dons ─────────────────────────────────────────────────────────────
    if not fait_dons or montant_dons == 0:
        lines += [
            f"### {prio}. Dons aux associations",
            "- Restos du Cœur, Croix-Rouge, Fondation Abbé Pierre : **75% de réduction**",
            "- Jusqu'à 1 000€ de dons → 750€ de réduction d'impôt",
            "- Vous ne débourser que 25€ pour faire 100€ de don !",
            "- Action : déclarer en case **7UD** (organismes aide personnes) ou **7UF** (autres)",
            "",
        ]
        prio += 1

    # ── 7. Épargne défiscalisée ─────────────────────────────────────────────
    epargne_conseils = []
    if not a_per:
        epargne_conseils.append("- Ouvrir un **PER** pour déduire les versements du revenu imposable")
    if not a_pea:
        epargne_conseils.append("- Ouvrir un **PEA** pour vos actions (exonération IR après 5 ans)")
    if not a_av:
        epargne_conseils.append("- Ouvrir une **assurance-vie** pour préparer transmission et épargne longue")
    if not a_livret_plein and rfr_estime < 23_028:
        epargne_conseils.append("- **LEP** : 2,5% défiscalisé — à maximiser en priorité !")

    if epargne_conseils:
        lines += [
            f"### {prio}. Optimisation de l'épargne",
        ] + epargne_conseils + [""]
        prio += 1

    # ── 8. Revenus fonciers ─────────────────────────────────────────────────
    if rev_fonciers > 0:
        lines += [
            f"### {prio}. Revenus locatifs — Optimisation du régime",
        ]
        if rev_fonciers < 15_000:
            lines += [
                f"- Loyers : {rev_fonciers:,.0f}€ (< 15 000€ : micro-foncier possible à 30% d'abattement)",
                "- Comparez avec le régime réel si vous avez des charges importantes (travaux, intérêts...)",
            ]
        else:
            lines += [
                f"- Loyers : {rev_fonciers:,.0f}€ (> 15 000€ : régime réel obligatoire)",
                "- Déduisez toutes vos charges : travaux, intérêts, assurances, frais de gestion",
            ]
        if a_credit_immo:
            lines.append("- Vous avez un crédit : les intérêts d'emprunt sont déductibles des revenus fonciers")
        lines.append("")
        prio += 1

    # ── 9. IFI ──────────────────────────────────────────────────────────────
    if patrimoine and patrimoine > 1_300_000:
        lines += [
            f"### {prio}. IFI (Impôt sur la Fortune Immobilière)",
            f"- Patrimoine immobilier estimé : {patrimoine:,.0f}€ → **IFI applicable**",
            "- Stratégies : démembrement de propriété, SCI, donation, dons IFI (75% réduction)",
            "- Consultez un notaire ou conseiller en gestion de patrimoine",
            "",
        ]
        prio += 1

    # ── Récapitulatif ────────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## Synthèse — Économies potentielles",
        "",
        f"| Action | Économie estimée |",
        f"|--------|-----------------|",
    ]
    if tmi >= 11:
        plafond_per2 = min(salaire * 0.10, PLAFOND_PER_MAX_2025)
        lines.append(f"| PER (5 000€ versés) | ~{5000*tmi/100:,.0f}€ d'impôt |")
    if "proprietaire" in statut_logement and travaux_envisages:
        lines.append(f"| MaPrimeRénov' | Subvention non fiscale (aide directe) |")
    lines += [
        "| Emploi à domicile (200€/mois) | ~1 200€ crédit d'impôt |",
        "| Dons 200€ (75%) | ~150€ réduction d'impôt |",
        "",
        "> 💡 **Total potentiel** : plusieurs milliers d'euros selon votre situation",
        "",
        "---",
        "",
        "## Questions pour affiner l'analyse",
        "",
        "Pour aller plus loin, renseignez (si non fait) :",
        "- Vos travaux de rénovation envisagés → `guide_maprimerenov`",
        "- Votre déclaration détaillée → `analyser_declaration_revenus`",
        "- Simulation PER précise → `calculer_economie_per`",
        "- Vos frais professionnels → `guide_frais_reels`",
        "- Comparer deux stratégies → `comparer_scenarios`",
        "- Calcul prélèvement à la source → `calculer_prelevement_source`",
        "- Si patrimoine immobilier > 1,3M€ → `calculer_ifi`",
        "- Si indépendant / TNS → `optimiser_tns`",
        "",
        "> ⚠️ Ce rapport est indicatif. Les montants réels dépendent de votre situation exacte.",
        "> Consultez impots.gouv.fr pour votre déclaration officielle.",
    ]
    return "\n".join(lines)


def tool_calculer_ifi(args: Dict) -> str:
    patrimoine_brut = float(args["patrimoine_immobilier_brut"])
    valeur_rp = float(args.get("valeur_residence_principale", 0))
    dettes = float(args.get("dettes_deductibles", 0))
    biens_pro = float(args.get("biens_professionnels", 0))
    rni = float(args.get("revenu_net_imposable", 0))

    # Calcul patrimoine net IFI
    abatt_rp = valeur_rp * IFI_ABATTEMENT_RP
    patrimoine_net = max(0, patrimoine_brut - abatt_rp - dettes - biens_pro)

    res = calculer_ifi_montant(patrimoine_net)
    ifi = res["ifi"]

    lines = [
        "## Calcul IFI — Impôt sur la Fortune Immobilière 2026",
        "",
        "### Calcul de l'assiette taxable",
        f"| Élément | Montant |",
        f"|---------|---------|",
        f"| Patrimoine immobilier brut | {patrimoine_brut:,.0f}€ |",
    ]
    if valeur_rp > 0:
        lines.append(f"| Abattement résidence principale (30%) | -{abatt_rp:,.0f}€ |")
    if dettes > 0:
        lines.append(f"| Dettes déductibles | -{dettes:,.0f}€ |")
    if biens_pro > 0:
        lines.append(f"| Biens professionnels exonérés | -{biens_pro:,.0f}€ |")
    lines += [
        f"| **Patrimoine net taxable** | **{patrimoine_net:,.0f}€** |",
        "",
    ]

    if patrimoine_net < IFI_SEUIL_ENTREE:
        lines += [
            f"✅ **Pas d'IFI** : votre patrimoine net ({patrimoine_net:,.0f}€) est inférieur au seuil de {IFI_SEUIL_ENTREE:,}€.",
            "",
            f"Il faudrait {IFI_SEUIL_ENTREE - patrimoine_net:,.0f}€ de patrimoine net supplémentaire pour être assujetti.",
        ]
    else:
        lines += [
            "### Calcul de l'IFI",
            "",
            f"| Tranche | Taux | Base | IFI |",
            f"|---------|------|------|-----|",
        ]
        for d in res["detail"]:
            lines.append(f"| {d['tranche']} | {d['taux']} | {d['base']} | {d['ifi']} |")

        if res["decote"] > 0:
            lines.append(f"| Décote appliquée | — | — | -{res['decote']:,.0f}€ |")

        lines += [
            "",
            f"### **IFI à payer : {ifi:,.0f}€**",
            "",
        ]

        # Plafonnement IFI (IR + IFI ne peut dépasser 75% des revenus)
        if rni > 0:
            plafond_75 = rni * 0.75
            ir_estime = calculer_ir(rni, 1)["impot_net"]
            total_ir_ifi = ir_estime + ifi
            if total_ir_ifi > plafond_75:
                reduction_plafond = total_ir_ifi - plafond_75
                lines += [
                    f"### Plafonnement (bouclier fiscal)",
                    f"- IR estimé + IFI = {total_ir_ifi:,.0f}€ > 75% des revenus ({plafond_75:,.0f}€)",
                    f"- Réduction IFI possible : **{reduction_plafond:,.0f}€**",
                    f"- IFI après plafonnement : **{max(0, ifi - reduction_plafond):,.0f}€**",
                    "",
                ]

        lines += [
            "### Stratégies pour réduire l'IFI",
            "- **Dons IFI** : dons aux organismes d'intérêt général → 75% de réduction IFI (max 50 000€)",
            "- **Démembrement de propriété** : donner la nue-propriété réduit la valeur taxable",
            "- **SCI avec emprunt** : les dettes sont déductibles si affectées aux biens taxables",
            "- **SCPI de rendement** : certaines structures permettent une optimisation",
            "- **LMP** : si statuts LMP remplis, les biens professionnels sont exonérés",
            "",
            "> ⚠️ L'IFI est déclaré avec votre déclaration de revenus (formulaire 2042-IFI).",
            "> Consultez un notaire ou conseiller en gestion de patrimoine pour votre situation exacte.",
        ]
    return "\n".join(lines)


def tool_optimiser_tns(args: Dict) -> str:
    statut = args["statut_juridique"]
    type_act = args["type_activite"]
    ca = float(args["chiffre_affaires"])
    charges = float(args.get("charges_reelles", 0))
    cotis_actuelles = float(args.get("cotisations_sociales", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    a_madelin = args.get("a_madelin", False)
    cotis_madelin = float(args.get("cotisations_madelin", 0))
    premiere_annee = args.get("premiere_annee", False)
    nb_parts = calculer_parts(situation, nb_enfants)

    # Régime micro applicable ?
    regime_micro = TNS_COTISATIONS.get({
        "vente_marchandises": "micro_be",
        "prestations_services_bic": "micro_bic_services",
        "prestations_liberales_bnc": "micro_bnc",
    }.get(type_act, "micro_bnc"), {})

    micro_eligible = regime_micro and ca <= regime_micro.get("seuil_ca", 0)

    lines = [
        "## Optimisation Fiscale TNS / Indépendant",
        "",
        f"**Statut actuel** : {statut.replace('_', ' ').upper()}",
        f"**Activité** : {type_act.replace('_', ' ')}",
        f"**CA annuel HT** : {ca:,.0f}€",
        "",
    ]

    # ── Analyse régime micro vs réel ────────────────────────────────────────
    lines += ["### 1. Régime fiscal : Micro vs Réel", ""]

    if micro_eligible:
        abatt = regime_micro["abattement"]
        benefice_micro = ca * (1 - abatt)
        cotis_micro = ca * regime_micro.get("taux_cotisations_sociales", 0.214)
        rni_micro = max(0, benefice_micro - cotis_micro)
        ir_micro = calculer_ir(rni_micro, nb_parts)["impot_net"]

        benefice_reel = max(0, ca - charges - (cotis_actuelles or cotis_micro))
        rni_reel = benefice_reel
        ir_reel = calculer_ir(rni_reel, nb_parts)["impot_net"]

        lines += [
            f"| Régime | Bénéfice imposable | IR estimé | Avantage |",
            f"|--------|-------------------|-----------|----------|",
            f"| **Micro** (abattement {abatt*100:.0f}%) | {benefice_micro:,.0f}€ | {ir_micro:,.0f}€ | Simple, pas de compta |",
            f"| **Réel** (charges réelles) | {benefice_reel:,.0f}€ | {ir_reel:,.0f}€ | Plus précis si charges élevées |",
            "",
        ]
        if charges > ca * abatt:
            lines.append(f"✅ **Le régime réel est plus avantageux** : vos charges réelles ({charges:,.0f}€) dépassent l'abattement micro ({ca*abatt:,.0f}€).")
        elif charges > 0:
            lines.append(f"ℹ️ Le régime micro est avantageux : abattement ({ca*abatt:,.0f}€) > charges réelles ({charges:,.0f}€).")
        else:
            lines.append("ℹ️ Sans données de charges, le micro est souvent avantageux si charges < abattement.")
        lines.append("")
    else:
        if regime_micro:
            lines.append(f"⚠️ **Micro non éligible** : CA {ca:,.0f}€ > seuil {regime_micro.get('seuil_ca', 0):,}€. Régime réel obligatoire.")
        benefice_reel = max(0, ca - charges - cotis_actuelles)
        ir_reel = calculer_ir(benefice_reel, nb_parts)["impot_net"]
        lines += [
            f"- Bénéfice imposable (réel) : {benefice_reel:,.0f}€",
            f"- IR estimé : {ir_reel:,.0f}€",
            "",
        ]

    # ── PER TNS ─────────────────────────────────────────────────────────────
    benefice_ref = max(0, ca - charges - cotis_actuelles) if not micro_eligible else ca * (1 - regime_micro.get("abattement", 0.34))
    plafond_per = min(benefice_ref * 0.10, PLAFOND_PER_MAX_2025)
    plafond_per = max(plafond_per, PLAFOND_PER_MIN_2025)
    tmi = calculer_ir(benefice_ref, nb_parts)["taux_marginal"]

    lines += [
        "### 2. PER Indépendant (ex-PERP / Madelin retraite)",
        f"- Plafond déductible estimé : **{plafond_per:,.0f}€**",
        f"- Économie si versement plafond max : **~{plafond_per * tmi / 100:,.0f}€** (TMI {tmi:.0f}%)",
        "- Le PER est déductible du bénéfice imposable (article 154 bis du CGI)",
        "- Versez avant le **31 décembre** pour réduire l'impôt de l'année",
        "",
    ]

    # ── Madelin ─────────────────────────────────────────────────────────────
    lines += ["### 3. Contrats Madelin (prévoyance & retraite)", ""]
    pass_2025 = 47_100
    for key, mad in PLAFOND_MADELIN_2025.items():
        plafond_mad = min(benefice_ref * mad["taux"], mad["max_pass"] * pass_2025 * mad["taux"])
        lines.append(f"- **{mad['description']}** : plafond ~{plafond_mad:,.0f}€/an (déductible du bénéfice)")
    if not a_madelin:
        lines.append("\n💡 Vous n'avez pas de contrats Madelin — à envisager pour optimiser prévoyance + déduction fiscale.")
    else:
        lines.append(f"\n✅ Madelin existant : {cotis_madelin:,.0f}€/an — vérifiez que vous utilisez bien votre plafond.")
    lines.append("")

    # ── ACRE ────────────────────────────────────────────────────────────────
    if premiere_annee:
        lines += [
            "### 4. ACRE — Aide à la Création/Reprise d'Entreprise",
            "- Exonération partielle de cotisations sociales la 1ère année (env. 50%)",
            f"- Économie estimée sur cotisations : ~{cotis_actuelles * 0.50:,.0f}€ si éligible",
            "- Demande à faire lors de la création auprès de l'URSSAF",
            "",
        ]

    # ── Choix de structure ───────────────────────────────────────────────────
    lines += [
        "### 5. Choix de structure — Comparatif rapide",
        "",
        "| Structure | Charges sociales | IR/IS | Avantage |",
        "|-----------|-----------------|-------|----------|",
        "| **EI / Micro** | 21-25% du CA | IR barème | Simplicité |",
        "| **EURL à l'IR** | ~45% du bénéfice | IR barème | Déduction charges complète |",
        "| **EURL à l'IS** | ~45% rémunération | IS 15%/25% + IR dividendes | Optimisation rémunération |",
        "| **SASU** | ~75% rémunération (salarié) | IS 15%/25% | Protection sociale salarié |",
        "",
        "> 💡 EURL/SASU à l'IS : vous pouvez optimiser la répartition rémunération/dividendes.",
        "> Dividendes : PFU 30% (flat tax) — souvent plus avantageux si TMI > 30%.",
        "",
        "> ⚠️ Consultez un expert-comptable pour le choix de structure adapté à votre situation.",
    ]
    return "\n".join(lines)


def tool_comparer_scenarios(args: Dict) -> str:
    scenarios = args["scenarios"]

    lines = [
        "## Comparaison de Scénarios Fiscaux",
        "",
    ]

    results = []
    for sc in scenarios:
        label = sc["label"]
        rni = float(sc["revenu_net_imposable"])
        situation = sc["situation_famille"]
        nb_enfants = int(sc.get("nb_enfants", 0))
        versement_per = float(sc.get("versement_per", 0))
        dons_75 = float(sc.get("dons_75", 0))
        dons_66 = float(sc.get("dons_66", 0))
        emploi_dom = float(sc.get("emploi_domicile", 0))
        garde = float(sc.get("garde_enfants", 0))

        nb_parts = calculer_parts(situation, nb_enfants)
        rni_apres_per = max(0, rni - versement_per)
        ir = calculer_ir(rni_apres_per, nb_parts)

        # Réductions / crédits
        reduction_dons = min(dons_75, 1_000) * 0.75 + max(0, dons_75 - 1_000) * 0.66 + dons_66 * 0.66
        credit_dom = min(emploi_dom, 12_000) * 0.50
        credit_garde = min(garde, 3_500) * 0.50

        impot_avant_credits = ir["impot_net"]
        impot_final = max(0, impot_avant_credits - reduction_dons)
        remboursement = credit_dom + credit_garde  # crédits remboursables
        impot_net_final = max(0, impot_final - remboursement)
        # Si crédit > impôt, remboursé
        solde_credits = max(0, remboursement - impot_final)

        results.append({
            "label": label,
            "rni": rni,
            "nb_parts": nb_parts,
            "tmi": ir["taux_marginal"],
            "taux_moyen": ir["taux_moyen"],
            "impot_brut": impot_avant_credits,
            "reduction_dons": reduction_dons,
            "credit_dom": credit_dom,
            "credit_garde": credit_garde,
            "remboursement": solde_credits,
            "impot_net_final": impot_net_final,
            "versement_per": versement_per,
        })

    # En-tête tableau
    headers = ["Indicateur"] + [r["label"] for r in results]
    sep = ["-" * 30] + ["-" * 20] * len(results)
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(sep) + " |")

    def row(label, values):
        return "| " + label + " | " + " | ".join(values) + " |"

    lines.append(row("Revenu net imposable", [f"{r['rni']:,.0f}€" for r in results]))
    lines.append(row("Parts fiscales", [f"{r['nb_parts']}" for r in results]))
    if any(r["versement_per"] > 0 for r in results):
        lines.append(row("Versement PER déduit", [f"{r['versement_per']:,.0f}€" for r in results]))
    lines.append(row("Impôt brut (avant crédits)", [f"{r['impot_brut']:,.0f}€" for r in results]))
    if any(r["reduction_dons"] > 0 for r in results):
        lines.append(row("Réduction dons", [f"-{r['reduction_dons']:,.0f}€" for r in results]))
    if any(r["credit_dom"] > 0 for r in results):
        lines.append(row("Crédit emploi domicile", [f"-{r['credit_dom']:,.0f}€" for r in results]))
    if any(r["credit_garde"] > 0 for r in results):
        lines.append(row("Crédit garde enfants", [f"-{r['credit_garde']:,.0f}€" for r in results]))
    lines.append(row("**Impôt net à payer**", [f"**{r['impot_net_final']:,.0f}€**" for r in results]))
    lines.append(row("TMI", [f"{r['tmi']:.0f}%" for r in results]))
    lines.append(row("Taux moyen", [f"{r['taux_moyen']:.1f}%" for r in results]))

    # Analyse comparative
    lines += ["", "### Analyse"]
    if len(results) >= 2:
        best = min(results, key=lambda x: x["impot_net_final"])
        worst = max(results, key=lambda x: x["impot_net_final"])
        diff = worst["impot_net_final"] - best["impot_net_final"]
        lines += [
            f"- **Scénario le plus avantageux** : {best['label']} → {best['impot_net_final']:,.0f}€ d'impôt",
            f"- **Économie vs le moins avantageux** : **{diff:,.0f}€** par an",
        ]
        for r in results:
            if r is not best:
                d = r["impot_net_final"] - best["impot_net_final"]
                if d > 0:
                    lines.append(f"- {r['label']} : {d:,.0f}€ de plus que {best['label']}")

    lines += [
        "",
        "> ⚠️ Simulation indicative — consultez impots.gouv.fr ou un conseiller fiscal pour validation.",
    ]
    return "\n".join(lines)


def tool_calculer_prelevement_source(args: Dict) -> str:
    rni = float(args["revenu_net_imposable"])
    situation = args["situation_famille"]
    nb_enfants = int(args.get("nb_enfants", 0))
    salaire_mensuel = float(args.get("salaire_mensuel_net", rni / 12))
    rev_complementaires = float(args.get("revenus_complementaires", 0))

    nb_parts = calculer_parts(situation, nb_enfants)
    ir = calculer_ir(rni, nb_parts)
    impot_annuel = ir["impot_net"]

    # Taux personnalisé PAS = impôt / revenu net avant abattement (approximation)
    revenu_base_pas = rni / 0.90 if rni > 0 else 1  # retransformer en net déclaré approx
    taux_perso = (impot_annuel / revenu_base_pas * 100) if revenu_base_pas > 0 else 0

    # Retenue mensuelle sur salaire
    retenue_mensuelle = salaire_mensuel * taux_perso / 100

    # Taux neutre (grille officielle simplifiée — célibataire)
    TAUX_NEUTRES = [
        (1_456, 0.0), (1_518, 0.5), (1_580, 1.5), (1_650, 2.5), (1_722, 3.5),
        (1_803, 4.5), (1_988, 6.0), (2_243, 7.5), (2_568, 9.0), (2_920, 10.5),
        (3_317, 12.0), (3_734, 13.5), (4_506, 15.0), (5_708, 17.5), (7_111, 20.0),
        (9_218, 22.5), (11_877, 25.0), (18_234, 30.0), (float("inf"), 38.0),
    ]
    taux_neutre = 0.0
    for seuil, taux in TAUX_NEUTRES:
        if salaire_mensuel <= seuil:
            taux_neutre = taux
            break

    lines = [
        "## Prélèvement à la Source (PAS) — Simulation",
        "",
        f"**Situation** : {situation.capitalize()}, {nb_parts} parts, {nb_enfants} enfant(s)",
        f"**Revenu net imposable** : {rni:,.0f}€/an",
        f"**Impôt estimé** : {impot_annuel:,.0f}€",
        "",
        "### Vos taux PAS",
        "",
        f"| Type de taux | Valeur | Retenue mensuelle |",
        f"|--------------|--------|-------------------|",
        f"| **Taux personnalisé** (foyer fiscal) | **{taux_perso:.1f}%** | **{retenue_mensuelle:,.0f}€/mois** |",
        f"| Taux neutre (célibataire, sans info) | {taux_neutre:.1f}% | {salaire_mensuel * taux_neutre / 100:,.0f}€/mois |",
        "",
        "### Acomptes sur revenus complémentaires",
    ]

    if rev_complementaires > 0:
        ir_compl = calculer_ir(rev_complementaires, 1)
        taux_compl = ir["taux_marginal"]
        acompte_mensuel = rev_complementaires * taux_compl / 100 / 12
        lines += [
            f"- Revenus fonciers / BIC / BNC : {rev_complementaires:,.0f}€/an",
            f"- Acompte mensuel estimé (TMI {taux_compl:.0f}%) : **{acompte_mensuel:,.0f}€/mois**",
            "- Prélevé le 15 de chaque mois directement sur votre compte",
        ]
    else:
        lines.append("- Aucun revenu complémentaire renseigné (pas d'acompte supplémentaire)")

    lines += [
        "",
        "### Comment agir sur votre taux",
        "",
        "**Moduler à la baisse** (si revenus diminuent) :",
        "- Connectez-vous sur **impots.gouv.fr → Gérer mon prélèvement à la source**",
        "- Possible si la modulation entraîne une baisse d'au moins 10% et 200€",
        "- Délai : pris en compte le mois suivant",
        "",
        "**Moduler à la hausse** :",
        "- Si vous anticipez un revenu exceptionnel (prime, cession, revenus locatifs...)",
        "- Evite une régularisation importante en septembre N+1",
        "",
        "**Opter pour le taux individualisé** (couples) :",
        "- Chaque conjoint paie en fonction de son propre revenu",
        "- Avantageux si forte disparité de revenus dans le couple",
        "",
        "**Opter pour le taux neutre** :",
        "- Utile pour ne pas communiquer votre taux à votre employeur",
        "- Vous devrez alors payer la différence directement à l'administration",
        "",
        "### Calendrier du PAS",
        "- **Janvier** : nouveau taux personnalisé calculé par l'administration (sur revenus N-2)",
        "- **Septembre** : mise à jour du taux avec la déclaration de revenus N-1",
        "- **Régularisation** : si trop ou trop peu prélevé, ajustement en septembre",
        "",
        "> ℹ️ Votre taux personnalisé exact figure sur votre avis d'imposition ou sur impots.gouv.fr.",
    ]
    return "\n".join(lines)


def _appliquer_bareme_droits(base_taxable: float, cle_bareme: str) -> Dict:
    """Applique un barème de droits (donation/succession) sur une base taxable."""
    droits = 0.0
    detail = []
    for tranche in BAREME_DROITS.get(cle_bareme, []):
        if base_taxable <= tranche["min"]:
            break
        max_t = tranche["max"] if tranche["max"] else float("inf")
        base = min(base_taxable, max_t) - tranche["min"]
        montant = base * tranche["taux"]
        if montant > 0:
            detail.append({
                "tranche": f"{tranche['min']:,}€ → {tranche['max']:,}€" if tranche["max"] else f"> {tranche['min']:,}€",
                "taux": f"{tranche['taux']*100:.0f}%",
                "base": f"{base:,.0f}€",
                "droits": f"{montant:,.0f}€",
            })
        droits += montant
    return {"droits": round(droits, 2), "detail": detail}


def tool_simuler_droits_donation(args: Dict) -> str:
    montant = _valider_revenu(float(args["montant_donation"]), "montant_donation")
    lien = args["lien_parente"]
    dons_anterieurs = float(args.get("donations_anterieures", 0))
    don_argent = args.get("don_argent_exonere", False)
    age_donateur = args.get("age_donateur")

    config = ABATTEMENTS_DONATIONS.get(lien)
    if not config:
        return f"Lien de parenté inconnu : {lien}"

    abattement_dispo = max(0, config["montant"] - dons_anterieurs)

    # Don d'argent exonéré supplémentaire
    exo_argent = 0.0
    if don_argent and (age_donateur is None or age_donateur < 80):
        exo_argent = min(montant, DON_ARGENT_EXONERE["montant"])

    base_taxable = max(0, montant - abattement_dispo - exo_argent)
    res = _appliquer_bareme_droits(base_taxable, config["bareme"])
    droits = res["droits"]
    taux_effectif = (droits / montant * 100) if montant > 0 else 0

    lines = [
        "## Simulation Droits de Donation",
        "",
        f"**Lien de parenté** : {config['label']}",
        f"**Montant de la donation** : {montant:,.0f}€",
        "",
        "### Calcul de la base taxable",
        f"| Élément | Montant |",
        f"|---------|---------|",
        f"| Donation brute | {montant:,.0f}€ |",
        f"| Abattement disponible ({config['periodicite']} ans) | -{abattement_dispo:,.0f}€ |",
    ]
    if dons_anterieurs > 0:
        lines.append(f"| *(Abattement déjà consommé : {dons_anterieurs:,.0f}€)* | — |")
    if exo_argent > 0:
        lines.append(f"| Don d'argent exonéré | -{exo_argent:,.0f}€ |")
    lines += [
        f"| **Base taxable** | **{base_taxable:,.0f}€** |",
        "",
    ]

    if base_taxable <= 0:
        lines += [
            f"✅ **Aucun droit à payer** — la donation est entièrement couverte par les abattements.",
            f"Reste d'abattement non utilisé : {abattement_dispo - montant:,.0f}€",
        ]
    else:
        lines += [
            "### Détail du calcul des droits",
            f"| Tranche | Taux | Base | Droits |",
            f"|---------|------|------|--------|",
        ]
        for d in res["detail"]:
            lines.append(f"| {d['tranche']} | {d['taux']} | {d['base']} | {d['droits']} |")
        lines += [
            "",
            f"### **Droits à payer : {droits:,.0f}€**",
            f"- Taux effectif global : **{taux_effectif:.1f}%**",
            f"- Montant net reçu par le bénéficiaire : **{montant - droits:,.0f}€**",
        ]

    lines += [
        "",
        "### Stratégies d'optimisation",
        f"- **Donner par tranches** : l'abattement de {config['montant']:,}€ se renouvelle tous les {config['periodicite']} ans",
        f"- **Donations multiples** : chaque parent peut donner {config['montant']:,}€ → {config['montant']*2:,}€ par couple",
    ]
    if lien in ["enfant_parent", "petit_enfant"]:
        lines += [
            f"- **Don d'argent exonéré** (+31 865€ si donateur < 80 ans et bénéficiaire majeur)",
            "- **Démembrement** : donner la nue-propriété, conserver l'usufruit → valeur réduite taxable",
            "- **Assurance-vie** : hors succession jusqu'à 152 500€ par bénéficiaire (primes versées avant 70 ans)",
        ]
    lines += [
        "",
        "> ⚠️ La donation doit être déclarée (formulaire 2735) dans le mois suivant.",
        "> Consultez un notaire pour les donations importantes.",
    ]
    return "\n".join(lines)


def tool_calculer_succession(args: Dict) -> str:
    actif = _valider_revenu(float(args["actif_net_succession"]), "actif_net_succession")
    heritiers = args["heritiers"]
    av_hors_succ = float(args.get("assurance_vie_hors_succession", 0))

    lines = [
        "## Calcul des Droits de Succession",
        "",
        f"**Actif net successoral** : {actif:,.0f}€",
    ]
    if av_hors_succ > 0:
        lines.append(f"**Assurance-vie hors succession** : {av_hors_succ:,.0f}€ (mentionné séparément)")
    lines += ["", "### Droits par héritier", ""]

    total_droits = 0.0
    recap_rows = []

    for h in heritiers:
        lien = h["lien"]
        nb = int(h.get("nb", 1))
        dons_ant = float(h.get("donations_anterieures", 0))
        handicape = h.get("handicape", False)

        config_succ = ABATTEMENTS_SUCCESSION.get(lien)
        if not config_succ:
            continue

        # Exonération totale conjoint/PACS
        if config_succ.get("note") == "EXONÉRÉ totalement":
            recap_rows.append(f"| {config_succ['label']} (×{nb}) | — | 0€ | ✅ EXONÉRÉ |")
            continue

        # Part reçue (division égale entre héritiers du même rang — simplifiée)
        part = actif / sum(int(hh.get("nb", 1)) for hh in heritiers if ABATTEMENTS_SUCCESSION.get(hh["lien"], {}).get("note") != "EXONÉRÉ totalement")
        part_par_personne = part  # simplification

        abatt = config_succ.get("montant", 0) or 0
        if handicape:
            abatt += 159_325
        abatt_dispo = max(0, abatt - dons_ant)
        base_taxable = max(0, part_par_personne - abatt_dispo)
        res = _appliquer_bareme_droits(base_taxable, config_succ.get("bareme", "autre"))
        droits_par_personne = res["droits"]
        droits_total_lien = droits_par_personne * nb
        total_droits += droits_total_lien

        recap_rows.append(
            f"| {config_succ['label']} (×{nb}) | {part_par_personne:,.0f}€ | {abatt_dispo:,}€ | "
            f"{base_taxable:,.0f}€ | **{droits_par_personne:,.0f}€** |"
        )

    lines += [
        "| Héritier | Part brute | Abattement | Base taxable | Droits |",
        "|----------|-----------|------------|--------------|--------|",
    ]
    lines += recap_rows
    lines += [
        "",
        f"### **Total droits de succession : {total_droits:,.0f}€**",
        f"- Actif net transmis (après droits) : **{actif - total_droits:,.0f}€**",
        "",
        "### Stratégies pour réduire les droits de succession",
        "- **Donations du vivant** : 100 000€/enfant tous les 15 ans sans droits (commence tôt !)",
        "- **Assurance-vie** : hors succession, 152 500€ exonérés par bénéficiaire (primes avant 70 ans)",
        "- **Démembrement de propriété** : transmettre la nue-propriété, conserver l'usufruit",
        "- **SCI familiale** : abattement pour défaut de liquidité (~15-20%)",
        "- **Pacte Dutreil** : exonération 75% sur transmission d'entreprise",
        "",
        "> ⚠️ La succession doit être déclarée dans les 6 mois (délai porté à 12 mois si décès à l'étranger).",
        "> Consultez un notaire — les règles varient selon la composition de la famille et les régimes matrimoniaux.",
    ]
    if av_hors_succ > 0:
        lines += [
            "",
            "### Assurance-vie transmise hors succession",
            f"- Capital décès : {av_hors_succ:,.0f}€",
            "- Exonération par bénéficiaire : 152 500€ (primes versées avant 70 ans)",
            "- Au-delà : prélèvement de 20% jusqu'à 700 000€, puis 31,25%",
            "- Primes versées après 70 ans : abattement global 30 500€ puis droits de succession normaux",
        ]
    return "\n".join(lines)


def tool_simuler_scpi(args: Dict) -> str:
    montant = _valider_revenu(float(args["montant_investi"]), "montant_investi")
    rendement_pct = float(args["rendement_brut_pct"])
    rni_hors_scpi = _valider_revenu(float(args["revenu_net_imposable_hors_scpi"]), "revenu_net_imposable_hors_scpi")
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    type_det = args.get("type_detention", "pleine_propriete")
    duree_nue = int(args.get("duree_detention_nue_propriete", 10))
    autres_fonciers = float(args.get("autres_revenus_fonciers", 0))

    revenus_bruts_scpi = montant * rendement_pct / 100
    nb_parts = calculer_parts(situation, nb_enfants)
    tmi_base = calculer_ir(rni_hors_scpi, nb_parts)["taux_marginal"]

    lines = [
        "## Simulation Fiscale SCPI",
        "",
        f"**Capital investi** : {montant:,.0f}€",
        f"**Rendement brut** : {rendement_pct:.2f}%",
        f"**Revenus bruts annuels** : {revenus_bruts_scpi:,.0f}€",
        f"**Votre TMI actuel** : {tmi_base:.0f}%",
        "",
    ]

    if type_det == "nue_propriete":
        # Tables de valeur économique de la nue-propriété (approximation)
        taux_np = {5: 0.60, 7: 0.55, 10: 0.49, 12: 0.46, 15: 0.41, 20: 0.33}
        taux = min(taux_np.items(), key=lambda x: abs(x[0] - duree_nue))[1]
        valeur_np = montant * taux
        gain_terme = montant - valeur_np  # gain à terme (pleine propriété récupérée)

        lines += [
            f"### Mode : Nue-Propriété ({duree_nue} ans)",
            "",
            f"- Vous achetez la nue-propriété : **{valeur_np:,.0f}€** ({taux*100:.0f}% de la valeur)",
            f"- L'usufruitier perçoit les loyers pendant {duree_nue} ans",
            f"- À terme, vous récupérez la pleine propriété : **{montant:,.0f}€**",
            f"- Gain de valeur à terme : **{gain_terme:,.0f}€** (non imposable si résidence principale non applicable)",
            "",
            "### Avantages fiscaux nue-propriété",
            "✅ **Aucun revenu taxable** pendant la durée du démembrement",
            "✅ **Non soumis à l'IFI** (valeur nue-propriété non retenue pour l'usufruitier)",
            "✅ **Plus-value à terme** calculée sur la valeur pleine propriété (durée détention depuis achat NP)",
            f"✅ **Rendement implicite** : {gain_terme/valeur_np/duree_nue*100:.2f}%/an (gain capitalistique)",
            "",
            "> Idéal si vous êtes fortement imposé et n'avez pas besoin de revenus complémentaires immédiats.",
        ]
        return "\n".join(lines)

    if type_det == "assurance_vie":
        # En AV : revenus réinvestis, taxation seulement au rachat après 8 ans
        rendement_net_av = revenus_bruts_scpi * 0.85  # frais UC ~0.5-1%/an approx
        abatt_annuel = 4_600 if situation == "celibataire" else 9_200
        lines += [
            "### Mode : Assurance-Vie",
            "",
            "**Pendant la phase d'épargne** : aucune fiscalité sur les revenus (capitalisation)",
            f"- Revenus réinvestis estimés : ~{rendement_net_av:,.0f}€/an (net de frais UC)",
            "",
            "**Au rachat (après 8 ans)** :",
            f"- Abattement annuel : {abatt_annuel:,}€ sur les gains",
            "- Taux IR sur gains : 7,5% (PFU réduit) jusqu'à 150 000€ de versements",
            "- Prélèvements sociaux : 17,2% (sur la part gains du rachat)",
            "",
            "**Avantages**",
            "✅ Pas de fiscalité annuelle → effet de capitalisation",
            "✅ Transmission hors succession (152 500€/bénéficiaire exonéré)",
            "✅ Souplesse : rachats partiels possibles",
            "",
            "**Inconvénient** : frais de gestion UC (0.5 à 1%/an) réduisent le rendement",
        ]
        return "\n".join(lines)

    # Pleine propriété — calcul fiscal complet
    total_foncier = revenus_bruts_scpi + autres_fonciers

    # Régime micro-foncier ou réel
    if total_foncier <= SCPI_INFO["seuil_micro_foncier"]:
        base_micro = revenus_bruts_scpi * (1 - SCPI_INFO["abattement_micro_foncier"])
        ir_micro = base_micro * tmi_base / 100
        ps_micro = base_micro * SCPI_INFO["ps_taux"]
        total_fisc_micro = ir_micro + ps_micro

        rni_avec_scpi = rni_hors_scpi + base_micro
        ir_total = calculer_ir(rni_avec_scpi, nb_parts)["impot_net"]
        ir_base = calculer_ir(rni_hors_scpi, nb_parts)["impot_net"]
        ir_reel_scpi = ir_total - ir_base
        ps_reel = revenus_bruts_scpi * SCPI_INFO["ps_taux"]  # PS sur revenus bruts (pas d'abattement micro pour PS... en réalité si)
        total_fisc_reel = ir_reel_scpi + ps_reel

        rendement_net_micro = (revenus_bruts_scpi - total_fisc_micro) / montant * 100
        rendement_net_reel = (revenus_bruts_scpi - total_fisc_reel) / montant * 100

        lines += [
            "### Fiscalité en Pleine Propriété",
            "",
            f"| | Micro-foncier (30% abatt.) | Réel (IR progressif) |",
            f"|--|--------------------------|---------------------|",
            f"| Revenus bruts SCPI | {revenus_bruts_scpi:,.0f}€ | {revenus_bruts_scpi:,.0f}€ |",
            f"| Abattement / charges | -{revenus_bruts_scpi*0.30:,.0f}€ | variable |",
            f"| Base imposable | {base_micro:,.0f}€ | {revenus_bruts_scpi:,.0f}€ |",
            f"| IR ({tmi_base:.0f}% TMI) | {ir_micro:,.0f}€ | {ir_reel_scpi:,.0f}€ |",
            f"| Prélèvements sociaux 17,2% | {ps_micro:,.0f}€ | {ps_reel:,.0f}€ |",
            f"| **Total fiscalité** | **{total_fisc_micro:,.0f}€** | **{total_fisc_reel:,.0f}€** |",
            f"| **Revenus nets** | **{revenus_bruts_scpi - total_fisc_micro:,.0f}€** | **{revenus_bruts_scpi - total_fisc_reel:,.0f}€** |",
            f"| **Rendement net fiscal** | **{rendement_net_micro:.2f}%** | **{rendement_net_reel:.2f}%** |",
            "",
        ]
    else:
        rni_avec_scpi = rni_hors_scpi + revenus_bruts_scpi
        ir_total = calculer_ir(rni_avec_scpi, nb_parts)["impot_net"]
        ir_base = calculer_ir(rni_hors_scpi, nb_parts)["impot_net"]
        ir_scpi = ir_total - ir_base
        ps_scpi = revenus_bruts_scpi * SCPI_INFO["ps_taux"]
        total_fisc = ir_scpi + ps_scpi
        rendement_net = (revenus_bruts_scpi - total_fisc) / montant * 100

        lines += [
            "### Fiscalité en Pleine Propriété (régime réel obligatoire > 15 000€)",
            f"- IR sur revenus SCPI : {ir_scpi:,.0f}€",
            f"- Prélèvements sociaux 17,2% : {ps_scpi:,.0f}€",
            f"- **Total fiscalité : {total_fisc:,.0f}€**",
            f"- Revenus nets après impôt : **{revenus_bruts_scpi - total_fisc:,.0f}€**",
            f"- **Rendement net fiscal : {rendement_net:.2f}%**",
            "",
        ]

    lines += [
        "### Comparaison des modes de détention",
        "",
        f"| Mode | Avantage principal | Idéal pour |",
        f"|------|--------------------|------------|",
        f"| Pleine propriété | Revenus immédiats | TMI ≤ 30% |",
        f"| Assurance-vie | Capitalisation, transmission | Long terme, TMI élevé |",
        f"| Nue-propriété | Zéro fiscalité immédiate, décote achat | TMI ≥ 41%, pas besoin revenus |",
        "",
        "### Rappel : Plus-values SCPI",
        "- Régime des plus-values immobilières (19% IR + 17,2% PS)",
        "- Exonération IR totale après **22 ans** de détention",
        "- Exonération PS totale après **30 ans**",
        "",
        "> ⚠️ Rendement non garanti. Investissement à risque de perte en capital.",
        "> Ce calcul est indicatif — vérifiez le prospectus de la SCPI.",
    ]
    return "\n".join(lines)


def tool_guide_fiscalite_internationale(args: Dict) -> str:
    pays_key = args.get("pays", "").lower().replace("-", "_").replace(" ", "_")
    situation = args.get("situation", "general")
    alsace = args.get("departement_alsace_moselle", False)

    lines = [
        "## Guide Fiscalité Internationale — Résidents Français",
        "",
    ]

    # Particularités Alsace-Moselle si demandé
    if alsace:
        am = ALSACE_MOSELLE
        lines += [
            f"### Alsace-Moselle ({am['nom']})",
            "",
            f"**Impact sur l'IR : {am['ir_impact']}**",
            "",
            "| Aspect | Alsace-Moselle | Reste de la France |",
            "|--------|---------------|-------------------|",
            "| Barème IR | Identique | Identique |",
            f"| Cotisation maladie | +{am['cotisation_maladie_supplementaire']*100:.1f}% sur salaire brut | Non |",
            f"| Remboursements santé | {am['remboursement_sante']} | 70% base sécu |",
            "| Droit des associations | Loi 1908 locale | Loi 1901 |",
            "",
            "> **Pour tous vos calculs d'IR, utilisez normalement les outils — aucune correction nécessaire.**",
            f"> Votre salaire net est légèrement inférieur au reste de la France ({am['cotisation_maladie_supplementaire']*100:.1f}% de cotisation maladie supplémentaire), mais vous bénéficiez d'une meilleure couverture santé.",
            "",
            "---",
            "",
        ]

    # Principes généraux
    lines += [
        "### Principes fondamentaux",
        "",
        "#### 1. Résidence fiscale française (art. 4B CGI)",
        "Vous êtes résident fiscal français si **au moins un** des critères est rempli :",
        "- **Foyer** ou lieu de séjour principal en France",
        "- **Activité professionnelle principale** exercée en France",
        "- **Centre des intérêts économiques** en France (investissements, revenus principaux)",
        "",
        "→ Si résident fiscal français : **imposé sur vos revenus mondiaux** en France",
        "",
        "#### 2. Formulaire 2047 — Revenus étrangers",
        "Obligatoire si vous percevez des revenus de source étrangère :",
        "- Déclarez les revenus étrangers sur le **formulaire 2047**",
        "- Report automatique sur la **déclaration 2042**",
        "- La convention fiscale détermine si vous payez l'IR en France",
        "",
        "#### 3. Deux méthodes pour éviter la double imposition",
        "",
        "| Méthode | Principe | Pays concernés (exemples) |",
        "|---------|----------|--------------------------|",
        "| **Exemption avec progressivité** | Revenu étranger exonéré d'IR français MAIS inclus pour calculer le taux sur vos autres revenus français | Allemagne (salaires), Suisse (frontaliers hors Genève) |",
        "| **Crédit d'impôt** | Revenu étranger inclus dans la base IR → IR calculé sur le total → crédit = impôt français correspondant | Irlande, Luxembourg, Belgique, UK, USA... |",
        "",
        "> Dans les deux cas, les **prélèvements sociaux (17,2%)** peuvent s'appliquer en France sur les revenus du patrimoine étranger, sauf si vous cotisez à un régime de sécurité sociale étranger de l'UE/EEE.",
        "",
    ]

    # Détail pays si spécifié
    if pays_key and pays_key in CONVENTIONS_FISCALES:
        conv = CONVENTIONS_FISCALES[pays_key]
        lines += [
            "---",
            "",
            f"### {conv['pays']} — {conv.get('convention', '')}",
            "",
            "| Type de revenu | Méthode | Retenue max à la source |",
            "|----------------|---------|------------------------|",
            f"| Salaires | {conv['methode_salaires'].replace('_', ' ')} | — |",
            f"| Dividendes | {conv['methode_dividendes'].replace('_', ' ')} | {conv.get('retenue_dividendes_max', 0)*100:.0f}% |",
            f"| Intérêts | {conv['methode_interets'].replace('_', ' ')} | {conv.get('retenue_interets_max', 0)*100:.0f}% |",
            "",
        ]
        if conv.get("note"):
            lines.append(f"ℹ️ {conv['note']}")
        if conv.get("note_frontaliers"):
            lines.append(f"**Frontaliers** : {conv['note_frontaliers']}")
        if conv.get("particularites"):
            lines += ["", "**Particularités importantes :**"]
            for p in conv["particularites"]:
                lines.append(f"- {p}")

        # Détail Irlande
        if pays_key == "ireland":
            imp = conv.get("impot_etranger", {})
            lines += [
                "",
                "#### Impôts irlandais (pour information)",
                "| Impôt | Taux | Remarque |",
                "|-------|------|----------|",
                f"| Income Tax standard | {imp.get('taux_standard', 0)*100:.0f}% | Sur revenus jusqu'à ~42 000€ |",
                f"| Income Tax supérieur | {imp.get('taux_superieur', 0)*100:.0f}% | Au-delà |",
                "| USC (Universal Social Charge) | 0,5% → 8% | Sur tranches de revenus |",
                f"| PRSI (cotisation sociale) | {imp.get('prsi', 0)*100:.0f}% | Salarié |",
                "",
                "**Pour un résident fiscal français avec revenus irlandais** :",
                "1. Déclarer les revenus irlandais sur le formulaire **2047**",
                "2. L'IR français est calculé sur l'ensemble (France + Irlande)",
                "3. Un **crédit d'impôt** égal à l'IR français correspondant aux revenus irlandais est accordé",
                "4. En pratique : vous payez l'impôt irlandais en Irlande + l'éventuel différentiel en France",
                "5. Utilisez `calculer_revenu_etranger` pour simuler votre IR total",
            ]

    elif pays_key and pays_key not in CONVENTIONS_FISCALES:
        lines += [
            "---",
            f"⚠️ Pays '{pays_key}' non référencé dans la base de données.",
            "Vérifiez l'existence d'une convention fiscale sur **impots.gouv.fr → Conventions fiscales**.",
            "Sans convention : risque de double imposition. Un crédit d'impôt partiel peut s'appliquer (art. 57 CGI).",
        ]

    # Non-résidents
    if situation == "non_resident_revenus_france":
        lines += [
            "---",
            "",
            "### Non-résidents avec revenus de source française",
            "",
            "| Tranche | Taux minimum |",
            "|---------|-------------|",
            "| Jusqu'à 27 794€ | **20%** |",
            "| Au-delà de 27 794€ | **30%** |",
            "",
            "- Option possible : appliquer le **barème progressif** si plus favorable",
            "- Déclaration : **formulaire 2042** + **2042-NR** (non-résidents)",
            "- Retenue à la source sur salaires : appliquée par l'employeur français",
            "- Centre des impôts compétent : **Service des impôts des particuliers non-résidents (SIPNR)** - Noisy-le-Grand",
        ]

    lines += [
        "",
        "---",
        "",
        "### Obligations déclaratives",
        "- **Formulaire 2047** : revenus encaissés à l'étranger (dividendes, intérêts, salaires, pensions...)",
        "- **Formulaire 3916** : déclaration des comptes bancaires étrangers (même inactifs) — amende 1 500€/compte",
        "- **Formulaire 3916-bis** : contrats d'assurance-vie et de capitalisation étrangers",
        "- **Formulaire 2042** : report des revenus étrangers (cases 1AF, 1BF pour salaires ; 2TR, 2DC pour capitaux...)",
        "",
        "### Ressources officielles",
        "- Conventions fiscales : **bofip.impots.gouv.fr** (BOFiP)",
        "- Liste des conventions : **impots.gouv.fr → International → Conventions fiscales**",
        "- Service non-résidents : **sipnr.dgfip.finances.gouv.fr**",
        "",
        "> ⚠️ La fiscalité internationale est complexe. Pour votre situation exacte, consultez un conseiller fiscal spécialisé.",
    ]
    return "\n".join(lines)


def tool_calculer_revenu_etranger(args: Dict) -> str:
    revenu_fr = _valider_revenu(float(args.get("revenu_france", 0)), "revenu_france")
    revenu_etr = _valider_revenu(float(args["revenu_etranger_eur"]), "revenu_etranger_eur")
    pays_key = args["pays"].lower().replace("-", "_").replace(" ", "_")
    type_rev = args.get("type_revenu", "salaire")
    impot_etranger = _valider_revenu(float(args.get("impot_paye_etranger", 0)), "impot_paye_etranger")
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    nb_parts = calculer_parts(situation, nb_enfants)

    conv = CONVENTIONS_FISCALES.get(pays_key, CONVENTIONS_FISCALES["sans_convention"])
    methode = conv.get(f"methode_{type_rev}", conv.get("methode_salaires", "credit_impot"))

    revenu_total = revenu_fr + revenu_etr

    # IR sans revenu étranger
    ir_france_seul = calculer_ir(revenu_fr, nb_parts) if revenu_fr > 0 else {"impot_net": 0.0, "taux_marginal": 0.0, "taux_moyen": 0.0}
    # IR sur revenu total
    ir_total = calculer_ir(revenu_total, nb_parts)

    lines = [
        "## Calcul IR avec Revenu Étranger",
        "",
        f"**Pays** : {conv['pays']} — *{conv.get('convention', '')}*",
        f"**Méthode** : {'Exemption avec progressivité' if methode == 'exemption_progressivite' else 'Crédit d\u2019impôt'}",
        f"**Type de revenu** : {type_rev}",
        "",
        "### Revenus",
        "| Source | Montant |",
        "|--------|---------|",
        f"| Revenus de source française | {revenu_fr:,.0f}€ |",
        f"| Revenus de source étrangère ({conv['pays']}) | {revenu_etr:,.0f}€ |",
        f"| **Total** | **{revenu_total:,.0f}€** |",
        "",
    ]

    ir_final = 0.0

    if methode == "exemption_progressivite":
        # IR calculé sur le total pour obtenir le taux, appliqué uniquement sur revenus FR
        taux_avec_etranger = ir_total["taux_moyen"] / 100
        ir_effectif = revenu_fr * taux_avec_etranger
        ir_effectif = max(0.0, ir_effectif)
        ir_final = ir_effectif

        lines += [
            "### Calcul par exemption avec progressivité",
            "",
            "| Étape | Valeur |",
            "|-------|--------|",
            f"| IR calculé sur revenus totaux ({revenu_total:,.0f}€) | {ir_total['impot_net']:,.0f}€ |",
            f"| Taux moyen résultant | {ir_total['taux_moyen']:.2f}% |",
            f"| IR appliqué aux seuls revenus français ({revenu_fr:,.0f}€) | **{ir_effectif:,.0f}€** |",
            "",
            f"### **IR à payer en France : {ir_effectif:,.0f}€**",
            "",
            f"ℹ️ Le revenu étranger ({revenu_etr:,.0f}€) est **exonéré d'IR français** mais augmente le taux appliqué à vos revenus français.",
            f"ℹ️ TMI effectif : {ir_total['taux_marginal']:.0f}%",
        ]
        if impot_etranger > 0:
            lines.append(f"\nImpôt payé à l'étranger : {impot_etranger:,.0f}€ (non déduit dans ce régime — normal)")

    else:  # credit_impot
        # Crédit d'impôt = part de l'IR français proportionnelle au revenu étranger
        if revenu_total > 0:
            credit = ir_total["impot_net"] * (revenu_etr / revenu_total)
        else:
            credit = 0.0
        credit = min(credit, impot_etranger) if impot_etranger > 0 else credit
        ir_net_france = max(0.0, ir_total["impot_net"] - credit)
        ir_final = ir_net_france

        lines += [
            "### Calcul par crédit d'impôt",
            "",
            "| Étape | Valeur |",
            "|-------|--------|",
            f"| IR calculé sur revenus totaux ({revenu_total:,.0f}€) | {ir_total['impot_net']:,.0f}€ |",
            f"| Crédit d'impôt (part revenus étrangers) | -{credit:,.0f}€ |",
            f"| **IR net à payer en France** | **{ir_net_france:,.0f}€** |",
            "",
        ]
        if impot_etranger > 0:
            lines += [
                f"**Impôt payé à l'étranger** : {impot_etranger:,.0f}€",
                f"**Coût fiscal total** (étranger + France) : {impot_etranger + ir_net_france:,.0f}€",
            ]
            if impot_etranger > credit:
                lines.append(f"⚠️ Impôt étranger ({impot_etranger:,.0f}€) > crédit accordé ({credit:,.0f}€) : double imposition résiduelle de {impot_etranger - credit:,.0f}€")

    lines += [
        "",
        "### Comparaison",
        "| Scénario | IR France |",
        "|----------|----------|",
        f"| Sans revenu étranger | {ir_france_seul['impot_net']:,.0f}€ |",
        f"| Avec revenu étranger ({conv['pays']}) | {ir_total['impot_net']:,.0f}€ (brut) |",
        f"| Après mécanisme convention | **{ir_final:,.0f}€** |",
        "",
        "### Obligations déclaratives",
        "- **Formulaire 2047** : déclarer les revenus étrangers",
        "- **Formulaire 2042** : reporter les montants (cases spécifiques selon le type de revenu)",
        "- **Formulaire 3916** : déclarer les comptes bancaires à l'étranger (même si inactifs)",
        "",
        "> ⚠️ Simulation indicative. La règle exacte dépend de la nature précise du revenu et de l'article de la convention applicable.",
        "> Consultez un conseiller fiscal spécialisé en fiscalité internationale.",
    ]
    return "\n".join(lines)


def tool_guide_frontaliers(args: Dict) -> str:
    pays = args["pays_emploi"].lower()
    canton = args.get("canton_suisse", "").lower()
    salaire_brut_etr = float(args["salaire_brut_etranger"])
    devise = args.get("devise", "EUR")
    taux_change = float(args.get("taux_change", 1.0))
    revenu_fr = float(args.get("revenu_france", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    teletravail = float(args.get("teletravail_jours_par_semaine", 0))
    nb_parts = calculer_parts(situation, nb_enfants)

    # Taux de change indicatifs si non fournis
    if taux_change == 1.0 and devise == "CHF":
        taux_change = 1.04  # CHF/EUR indicatif 2025

    salaire_eur = salaire_brut_etr * taux_change if devise != "EUR" else salaire_brut_etr

    lines = [
        f"## Guide Frontalier — France → {pays.upper()}",
        "",
        f"**Salaire brut** : {salaire_brut_etr:,.0f} {devise}",
        f"**Équivalent en euros** : {salaire_eur:,.0f}€ (taux {taux_change:.4f})",
    ]
    if revenu_fr > 0:
        lines.append(f"**Autres revenus français** : {revenu_fr:,.0f}€")
    lines.append("")

    if pays == "suisse":
        lines += [
            "### Régime fiscal Suisse — Frontaliers",
            "",
            "#### Accord frontaliers du 11 avril 1983 (toujours en vigueur)",
            "",
        ]
        is_geneve = "genev" in canton or canton == "ge"
        if is_geneve:
            lines += [
                "⚠️ **Canton de Genève : régime particulier**",
                "- Imposition **partagée** : impôt à la source suisse retenu par l'employeur genevois",
                "- France perçoit une **compensation annuelle** de Genève",
                "- Vous êtes également imposable en France (crédit d'impôt accordé)",
                "- Taux source genevois : ~35-40% selon revenu",
                "",
                "**Déclaration en France :**",
                "1. Déclarez le salaire genevois sur le formulaire **2047** (cases revenus étrangers)",
                "2. Indiquez l'impôt retenu à la source suisse",
                "3. Un crédit d'impôt est accordé → réduction de l'IR français",
            ]
        else:
            lines += [
                "✅ **Autres cantons (hors Genève) : imposition en France uniquement**",
                "- Votre employeur suisse retient un **impôt à la source (IS)** de ~8-10%",
                "- Cet IS est **remboursé/crédité** car vous êtes imposable uniquement en France",
                "- **Aucun impôt sur le revenu suisse** à payer en Suisse (hors IS remboursable)",
                "",
                "**Démarche pour récupérer l'impôt à la source suisse :**",
                "1. Demander le remboursement auprès de l'autorité fiscale du canton",
                "2. Délai : avant le 31 mars de l'année suivante en général",
                "",
                "**Déclaration en France :**",
                "1. Déclarez le **salaire brut suisse** converti en euros (taux BNS moyen annuel)",
                "2. Formulaire **2047**, puis report en **1AF/1BF** sur la 2042",
                "3. Méthode : **exemption avec progressivité** (salaire suisse non taxé mais inclus pour le taux)",
            ]
            if canton:
                lines.append(f"\nCanton renseigné : **{canton}** — hors Genève → régime d'exemption avec progressivité.")

        # Télétravail
        if teletravail > 0:
            pct_teletravail = teletravail / 5 * 100
            lines += [
                "",
                f"#### Télétravail — {teletravail:.0f} jour(s)/semaine ({pct_teletravail:.0f}%)",
                "",
                "**Accord franco-suisse télétravail (entré en vigueur progressivement depuis 2023) :**",
                "- Tolérance télétravail depuis la France : **jusqu'à 40%** du temps de travail sans changer la règle fiscale",
                f"- Votre situation : {pct_teletravail:.0f}% de télétravail → " + ("dans la tolérance 40%" if pct_teletravail <= 40 else "DÉPASSEMENT : impact fiscal possible, consultez l'administration"),
                "- Au-delà de 40% : les jours télétravaillés peuvent devenir imposables en France séparément",
            ]

        # Calcul IR estimé
        ir_total = calculer_ir(revenu_fr + salaire_eur, nb_parts)
        if revenu_fr > 0 and is_geneve:
            credit = ir_total["impot_net"] * (salaire_eur / (revenu_fr + salaire_eur))
            ir_net = max(0.0, ir_total["impot_net"] - credit)
        else:
            taux_global = ir_total["taux_moyen"] / 100
            ir_net = revenu_fr * taux_global if revenu_fr > 0 else 0.0

        lines += [
            "",
            "### Estimation IR français",
            "| | Montant |",
            "|--|---------|",
            f"| Salaire suisse (€) | {salaire_eur:,.0f}€ |",
            f"| Revenus français | {revenu_fr:,.0f}€ |",
            f"| Taux moyen global | {ir_total['taux_moyen']:.1f}% |",
            f"| **IR estimé en France** | **{ir_net:,.0f}€** |",
            "",
        ]

        lines += [
            "### Points d'attention Suisse",
            "- **Pilier 2 (LPP)** : cotisations retraite suisses non déductibles en France (à déclarer)",
            "- **Pilier 3a** : épargne retraite suisse, traitement fiscal complexe en France",
            "- **Attestation de résidence fiscale** : à fournir à l'employeur suisse (formulaire R-EXP ou équivalent canton)",
            "- **Taux de change** : utilisez le taux moyen BNS (Banque Nationale Suisse) de l'année fiscale",
            "- **Prime de fidélité / 13ème mois** : entièrement imposable en France",
        ]

    elif pays == "luxembourg":
        ir_total = calculer_ir(revenu_fr + salaire_eur, nb_parts)
        total = revenu_fr + salaire_eur
        credit = ir_total["impot_net"] * (salaire_eur / total) if total > 0 else 0.0
        ir_net = max(0.0, ir_total["impot_net"] - credit)

        lines += [
            "### Régime fiscal Luxembourg — Frontaliers",
            "",
            "**Principe** : Salaire imposé **au Luxembourg** (PAS en France sur ce salaire)",
            "",
            "#### Mécanisme : Crédit d'impôt",
            "1. Votre employeur luxembourgeois retient l'**impôt luxembourgeois** à la source",
            "2. En France : vous déclarez le salaire luxembourgeois sur le formulaire **2047**",
            "3. L'IR français est calculé sur l'ensemble (France + Luxembourg)",
            "4. Un **crédit d'impôt** = impôt français correspondant au salaire luxembourgeois → annule la double imposition",
            "5. Impact pratique : le salaire luxembourgeois fait **monter votre taux** sur vos revenus français",
            "",
            "#### Taux d'imposition luxembourgeois (barème 2025 indicatif)",
            "| Tranche | Taux |",
            "|---------|------|",
            "| 0 — 11 265€ | 0% |",
            "| 11 265 — 13 173€ | 8% |",
            "| 13 173 — 15 021€ | 10% |",
            "| 15 021 — 100 000€ | 14% — 38% (progressif) |",
            "| > 200 000€ | 42% |",
            "",
            "#### Estimation IR français",
            "| | Montant |",
            "|--|---------|",
            f"| Salaire luxembourgeois (€) | {salaire_eur:,.0f}€ |",
            f"| Autres revenus français | {revenu_fr:,.0f}€ |",
            f"| IR calculé sur total | {ir_total['impot_net']:,.0f}€ |",
            f"| Crédit d'impôt (part Luxembourg) | -{credit:,.0f}€ |",
            f"| **IR net à payer en France** | **{ir_net:,.0f}€** |",
            f"| Taux moyen global | {ir_total['taux_moyen']:.1f}% |",
            "",
            "#### Points d'attention Luxembourg",
            "- **Fiche de salaire** : conservez toutes vos fiches et le certificat fiscal annuel luxembourgeois",
            "- **Assurance maladie** : vous cotisez à la CNS (Caisse Nationale de Santé) luxembourgeoise",
            "- **Retraite** : droits CNAP (Caisse Nationale d'Assurance Pension) + droits français CNAV",
            "- **Télétravail** : accord franco-luxembourgeois depuis 2022 — tolérance 34 jours/an sans impact fiscal",
        ]
        if teletravail > 0:
            jours_annuel = round(teletravail * 46)
            if teletravail > 0.7:
                lines.append(f"⚠️ Vous dépassez probablement la tolérance de 34j/an avec {jours_annuel} jours estimés")
            else:
                lines.append(f"ℹ️ Télétravail {jours_annuel} j/an estimé — dans la tolérance 34j")

    elif pays == "belgique":
        lines += [
            "### Régime fiscal Belgique — Frontaliers",
            "",
            "⚠️ **Régime complexe selon le secteur d'activité**",
            "",
            "#### Secteur privé",
            "- Salaire généralement imposé **en Belgique** (retenue précompte professionnel)",
            "- Déclaration en France : formulaire 2047 + crédit d'impôt",
            "- Impact sur le taux français si revenus mixtes France + Belgique",
            "",
            "#### Zone frontalière spéciale (art. 11 de la convention)",
            "- Certains travailleurs des zones frontalières peuvent bénéficier d'un régime particulier",
            "- Vérifiez si votre commune de résidence et d'emploi sont dans les zones éligibles",
            "",
            "#### Secteur public belge",
            "- Fonctionnaires et assimilés : conventions spécifiques, souvent imposés en France",
            "- Consultez la convention art. 18 et le BOFiP",
            "",
            "#### Prélèvement belge",
            "- Précompte professionnel : de 25% à 50% selon revenus",
            "- Cotisations ONSS (sécurité sociale belge) : ~13,07% du brut",
            "",
            "> Consultez un conseiller fiscal spécialisé franco-belge pour votre situation exacte.",
        ]

    elif pays == "allemagne":
        lines += [
            "### Régime fiscal Allemagne — Frontaliers",
            "",
            "**Principe général** : Salaire imposé **en Allemagne** (sauf exception frontalière)",
            "",
            "#### Frontaliers franco-allemands",
            "- Zone frontalière : départements 57 (Moselle), 67 (Bas-Rhin), 68 (Haut-Rhin) côté français",
            "- **Régime d'exemption avec progressivité** : salaire allemand exonéré d'IR français",
            "  mais inclus pour le calcul du taux sur revenus français",
            "",
            "#### Impôt allemand (Lohnsteuer)",
            "- Retenu à la source par l'employeur allemand",
            "- Classes fiscales (Steuerklasse 1 à 6) selon situation familiale",
            "- Solidaritätszuschlag (Soli) : 0% pour la plupart depuis 2021",
            "- Kirchensteuer (impôt d'église) : 8-9% de l'impôt si vous êtes membre d'une église enregistrée",
            "",
            "#### Points d'attention",
            "- **Attestation de résidence** : formulaire à fournir à l'employeur et à l'administration allemande",
            "- **Déclaration France** : formulaire 2047 obligatoire",
            "- **Cotisations sociales allemandes** : Krankenversicherung (~7,3%), Pflegeversicherung (1,7%), Rentenversicherung (9,3%), Arbeitslosenversicherung (1,3%)",
            "- **Pension allemande** : droits Deutsche Rentenversicherung + retraite française CNAV si vous avez cotisé en France",
        ]

    lines += [
        "",
        "---",
        "",
        "### Obligations communes à tous les frontaliers",
        "- **Formulaire 2047** : déclaration revenus étrangers (obligatoire)",
        "- **Formulaire 3916** : déclaration compte bancaire étranger (obligatoire, même compte salaire)",
        "- **Attestation de résidence fiscale** : à fournir à l'employeur étranger chaque année",
        "- **Sécurité sociale** : règlement UE 883/2004 — en principe couvert par le pays d'emploi",
        "- **Retraite** : droits acquis dans les deux pays (totalisation possible)",
        "",
        "> Utilisez `calculer_revenu_etranger` pour simuler précisément votre IR français.",
        "> Pour votre situation exacte, consultez un expert-comptable spécialisé en fiscalité transfrontalière.",
    ]
    return "\n".join(lines)


def tool_guide_maprimerenov(args: Dict) -> str:
    rfr = float(args["revenu_fiscal_reference"])
    nb_parts = float(args.get("nb_parts", 1))
    travaux = args.get("travaux_envisages", [])
    budget = float(args.get("budget_total", 0))
    dpe = args.get("dpe_actuel", "inconnu")
    dpe_cible = args.get("dpe_cible", "inconnu")

    categorie = _get_mpr_categorie(rfr, nb_parts)
    cat_info = MAPRIMERENOV["categories"][categorie]

    # Seuils pour info
    np_int = min(5, max(1, round(nb_parts * 2) / 2))
    seuils = MPR_SEUILS_2025.get(np_int, MPR_SEUILS_2025[1])

    lines = [
        "## Guide MaPrimeRénov' 2025",
        "",
        f"### Votre profil",
        f"- RFR : {rfr:,.0f}€ pour {nb_parts} parts fiscales",
        f"- **Catégorie : {cat_info['label']} ({categorie.upper()})**",
        "",
        "#### Taux d'aide applicables à votre catégorie :",
        f"| Type de travaux | Taux |",
        f"|-----------------|------|",
        f"| Isolation (combles, murs, plancher) | {cat_info['taux_isolation']*100:.0f}% |",
        f"| Pompe à chaleur | {cat_info['taux_pompe_chaleur']*100:.0f}% |",
        f"| Chaudière à granulés/bois | {cat_info['taux_chaudiere_bois']*100:.0f}% |",
        f"| Fenêtres / double vitrage | {cat_info['taux_fenetres']*100:.0f}%" + (" (non éligible)" if cat_info['taux_fenetres'] == 0 else "") + " |",
        "",
    ]

    # Tableau des seuils
    lines += [
        "### Seuils de revenus MaPrimeRénov' 2025",
        f"(Pour {nb_parts} parts fiscales)",
        f"| Catégorie | Plafond RFR | Votre situation |",
        f"|-----------|-------------|-----------------|",
        f"| 🔵 Bleu (très modestes) | ≤ {seuils[0]:,}€ | {'✅ VOTRE CATÉGORIE' if categorie=='bleu' else ''} |",
        f"| 🟡 Jaune (modestes) | ≤ {seuils[1]:,}€ | {'✅ VOTRE CATÉGORIE' if categorie=='jaune' else ''} |",
        f"| 🟣 Violet (intermédiaires) | ≤ {seuils[2]:,}€ | {'✅ VOTRE CATÉGORIE' if categorie=='violet' else ''} |",
        f"| 🌸 Rose (supérieurs) | > {seuils[2]:,}€ | {'✅ VOTRE CATÉGORIE' if categorie=='rose' else ''} |",
        "",
    ]

    # Simulation travaux
    if travaux:
        lines += [
            "### Simulation de vos travaux",
            "",
            f"| Travaux | Coût moyen | Plafond aide | Aide estimée ({categorie}) |",
            f"|---------|------------|--------------|--------------------------|",
        ]
        total_cout = 0
        total_aide = 0
        for trav_key in travaux:
            t = MAPRIMERENOV["travaux"].get(trav_key)
            if not t:
                continue
            cout = t.get("cout_moyen", t.get("cout_moyen_m2", 0))
            plafond = t.get("plafond_aide", t.get("plafond_aide_m2", 0))
            taux = cat_info.get(f"taux_{trav_key.split('_')[0]}", cat_info["taux_isolation"])
            if trav_key == "fenetres" and categorie == "rose":
                aide = 0
                note = "(non éligible catégorie Rose)"
            else:
                aide = plafond * taux
                note = ""
            total_cout += cout
            total_aide += aide
            cout_str = f"~{cout:,}€" if isinstance(cout, int) else f"~{cout}€/m²"
            plafond_str = f"{plafond:,}€" if isinstance(plafond, int) else f"{plafond}€/m²"
            lines.append(f"| {t['nom']} | {cout_str} | {plafond_str} | **{aide:,.0f}€** {note} |")

        # Bonus passoire thermique
        if dpe in ["F", "G"]:
            lines.append(f"| Bonus sortie passoire (F→E ou mieux) | — | — | **+{MAPRIMERENOV['bonus_sortie_passoire']:,}€** |")
            total_aide += MAPRIMERENOV["bonus_sortie_passoire"]

        lines += [
            "",
            f"**Total aide estimée : {total_aide:,.0f}€**",
            f"*(sur un investissement d'environ {total_cout:,.0f}€)*",
            "",
        ]

    elif budget > 0:
        aide_estim = budget * cat_info["taux_isolation"]
        lines += [
            f"### Estimation globale",
            f"- Budget travaux : {budget:,.0f}€",
            f"- Aide estimée (taux isolation {cat_info['taux_isolation']*100:.0f}%) : ~{aide_estim:,.0f}€",
            "",
        ]

    # Conditions générales
    lines += [
        "### Conditions générales d'éligibilité",
        "1. **Logement** : résidence principale construite il y a > 15 ans",
        "2. **Entreprise RGE** : obligatoirement réalisé par artisan certifié RGE (Reconnu Garant Environnement)",
        "3. **Demande avant travaux** : la demande doit être faite sur maprimerenov.gouv.fr AVANT de signer le devis",
        "4. **Propriétaire** : occupant ou bailleur (conditions différentes pour les bailleurs)",
        "",
        "### Parcours recommandés",
        "- **Mono-geste** : un seul type de travaux (isolation OU PAC OU chaudière)",
        "- **Parcours accompagné** : plusieurs travaux permettant un gain de 2 classes DPE minimum",
        "  - Obligatoire si aide > 5 000€ sur 5 ans",
        "  - Audit énergétique obligatoire (aide pour l'audit disponible)",
        "  - Suivi par Mon Accompagnateur Rénov' (MAR)",
        "",
        "### Cumuler avec d'autres aides",
        "- **Éco-PTZ** : prêt à taux zéro pour financer le reste à charge",
        "- **Aides ANAH** : complémentaires pour ménages modestes",
        "- **TVA réduite 5,5%** : sur travaux d'amélioration énergétique (au lieu de 10%)",
        "- **Aides locales** : départements et régions ont souvent des aides supplémentaires",
        "- **Certificats d'Économies d'Énergie (CEE)** : primes énergie des fournisseurs",
        "",
        "### Liens essentiels",
        "- Simulateur officiel : **maprimerenov.gouv.fr**",
        "- Annuaire RGE : **france-renov.gouv.fr**",
        "- Accompagnateur Rénov' : **france-renov.gouv.fr/mon-accompagnateur-renov**",
        "",
        "> ⚠️ Les montants sont indicatifs. Les aides réelles dépendent du plafond de ressources exact",
        "> et des devis obtenus. Simulez toujours sur maprimerenov.gouv.fr avant d'engager des travaux.",
    ]
    return "\n".join(lines)


# ─── Outils 2.3.0 ────────────────────────────────────────────────────────────

def tool_guide_evenements_vie(args: Dict) -> str:
    evenement = args["evenement"]
    situation_actuelle = args.get("situation_actuelle", "")
    nb_enfants = int(args.get("nb_enfants", 0))
    nb_enfants_ga = int(args.get("nb_enfants_garde_alternee", 0))
    revenu = float(args.get("revenu_annuel", 0))
    age_enfant = args.get("age_enfant")

    lines = [f"## Impact fiscal — Événement de vie : {evenement.replace('_', ' ').title()}", ""]

    # ── MARIAGE / PACS ────────────────────────────────────────────────────────
    if evenement == "mariage":
        lines += [
            "### Règles applicables (Loi de finances 2020 — art. 6-1 CGI)",
            "",
            "Depuis l'imposition des revenus 2019, **une seule déclaration commune** est établie l'année du mariage ou du PACS, quelle que soit la date de l'événement dans l'année.",
            "",
            "**Option disponible : imposition distincte**",
            "- Chaque partenaire peut opter pour une **imposition séparée** pour l'année du mariage/PACS.",
            "- Chacun déclare ses revenus personnels perçus **sur toute l'année** (pas de prorata).",
            "- L'option est irrévocable pour l'année considérée.",
            "- Avantageuse si les revenus sont très déséquilibrés (ex : l'un travaille, l'autre non).",
            "",
            "**Déclaration commune (par défaut)**",
            "- Les revenus des deux conjoints sont cumulés sur l'année entière.",
            "- Le foyer dispose de **2 parts** (+ parts pour enfants).",
            "- Avantageuse en général quand les revenus sont proches.",
            "",
        ]
        if revenu > 0:
            # Simulation comparative
            parts_seul = calculer_parts("celibataire", nb_enfants)
            parts_couple = calculer_parts("marie", nb_enfants)
            res_seul = calculer_ir(revenu, parts_seul)
            res_couple = calculer_ir(revenu, parts_couple)
            # Estimation imposition commune (revenu doublé, 2 parts de base)
            res_couple_cumul = calculer_ir(revenu * 2, parts_couple)
            lines += [
                "### Simulation indicative",
                "",
                f"| Scénario | Revenu imposable | Parts | Impôt estimé |",
                f"|----------|-----------------|-------|--------------|",
                f"| Imposition séparée (vous seul) | {revenu:,.0f}€ | {parts_seul} | {res_seul['impot_net']:,.0f}€ |",
                f"| Déclaration commune (× 2 revenus) | {revenu*2:,.0f}€ | {parts_couple} | {res_couple_cumul['impot_net']:,.0f}€ |",
                "",
                "> Ces calculs supposent que les deux conjoints ont le même revenu. Adaptez avec vos revenus réels.",
            ]
        lines += [
            "",
            "### Démarches",
            "- Signaler le mariage/PACS sur votre espace impots.gouv.fr dans les 60 jours.",
            "- L'administration crée automatiquement un foyer fiscal commun.",
            "- En cas de PACS, joindre la copie du contrat si demandé.",
            "",
            "### Abattements et crédits d'impôt",
            "- Les crédits d'impôt (emploi à domicile, garde d'enfant) se cumulent pour le foyer commun.",
            "- Le plafond PER passe à deux plafonds individuels (non cumulables sur une même personne).",
        ]

    # ── DIVORCE / SÉPARATION ──────────────────────────────────────────────────
    elif evenement == "divorce":
        lines += [
            "### Règles applicables (art. 6-1 CGI)",
            "",
            "**L'année du divorce ou de la séparation de corps** : chaque ex-conjoint établit **sa propre déclaration** pour l'ensemble de l'année.",
            "",
            "- Chacun déclare ses revenus **personnels** perçus sur toute l'année.",
            "- Les revenus communs (fonciers, valeurs mobilières) sont déclarés à hauteur de **sa quote-part**.",
            "- La date exacte du divorce ne crée pas de prorata sur les revenus d'activité.",
            "",
            "### Attribution des enfants",
        ]
        if nb_enfants > 0:
            parts_excl = calculer_parts("celibataire", nb_enfants)
            parts_ga = calculer_parts("celibataire", 0, 0, nb_enfants)
            lines += [
                f"- **Garde exclusive** : le parent gardien bénéficie de {parts_excl} parts fiscales ({nb_enfants} enfant(s)).",
                f"- **Garde alternée** : chaque parent bénéficie de {parts_ga} parts fiscales ({nb_enfants} enfant(s) en alternée).",
                "- En garde alternée, les avantages fiscaux (abattement PER, crédits) sont partagés par moitié.",
            ]
        else:
            lines += [
                "- Sans enfant : chaque ex-conjoint a **1 part** (célibataire / divorcé).",
            ]
        lines += [
            "",
            "### Pension alimentaire versée",
            "- Déductible du revenu imposable du payeur (art. 156 II CGI).",
            "- Imposable chez le bénéficiaire comme pension alimentaire reçue.",
            "- Plafond si enfant majeur non rattaché : **6 368 €** par enfant (2025).",
            "",
            "### Démarches",
            "- Mettre à jour la situation sur impots.gouv.fr dès la séparation.",
            "- Deux avis d'imposition distincts seront émis.",
        ]
        if revenu > 0:
            parts_div = calculer_parts("divorce", nb_enfants, 0, nb_enfants_ga)
            res = calculer_ir(revenu, parts_div)
            lines += [
                "",
                "### Simulation post-divorce",
                f"- Revenu annuel : {revenu:,.0f}€",
                f"- Parts fiscales : {parts_div}",
                f"- **Impôt estimé : {res['impot_net']:,.0f}€** (TMI {res['taux_marginal']:.0f}%)",
            ]

    # ── NAISSANCE ─────────────────────────────────────────────────────────────
    elif evenement == "naissance":
        rang = nb_enfants  # L'enfant qui naît est de rang nb_enfants (déjà incrémenté par l'utilisateur)
        # Calculer les parts avant (nb_enfants - 1) et après (nb_enfants)
        sit = "marie" if "mari" in situation_actuelle.lower() or "pacs" in situation_actuelle.lower() else "celibataire"
        parts_avant = calculer_parts(sit, max(0, nb_enfants - 1))
        parts_apres = calculer_parts(sit, nb_enfants)
        gain_parts = parts_apres - parts_avant

        lines += [
            "### Règles applicables",
            "",
            "**L'enfant né en cours d'année compte pour l'année entière** — aucun prorata selon la date de naissance (art. 196 CGI).",
            "",
            f"### Impact sur le quotient familial",
            f"- Parts avant naissance : **{parts_avant}**",
            f"- Parts après naissance : **{parts_apres}** (+{gain_parts} part{'s' if gain_parts > 1 else ''})",
            "",
            "**Règle des demi-parts par rang :**",
            "- 1er enfant : +0,5 part",
            "- 2ème enfant : +0,5 part",
            "- 3ème enfant et suivants : +1 part chacun",
            "- Parent isolé (célibataire/divorcé) avec enfant(s) : +0,5 part supplémentaire",
            "",
            f"**Plafond de l'avantage lié au quotient familial** : {PLAFOND_DEMI_PART:,}€ par demi-part supplémentaire.",
        ]
        if revenu > 0:
            res_avant = calculer_ir(revenu, parts_avant)
            res_apres = calculer_ir(revenu, parts_apres)
            gain_impot = res_avant["impot_net"] - res_apres["impot_net"]
            lines += [
                "",
                "### Simulation d'impact fiscal",
                f"| | Avant naissance | Après naissance |",
                f"|--|----------------|-----------------|",
                f"| Parts fiscales | {parts_avant} | {parts_apres} |",
                f"| Impôt estimé | {res_avant['impot_net']:,.0f}€ | {res_apres['impot_net']:,.0f}€ |",
                f"| **Économie d'impôt** | | **{gain_impot:,.0f}€** |",
            ]
        lines += [
            "",
            "### Démarches",
            "- Déclarer l'enfant sur impots.gouv.fr (rubrique « Ma situation »).",
            "- Déclarer la naissance à la mairie dans les 5 jours — transmission automatique aux impôts.",
            "- Vérifier les droits à la Prime d'activité (CAF) et aux allocations familiales.",
        ]

    # ── GARDE ALTERNÉE ────────────────────────────────────────────────────────
    elif evenement == "garde_alternee":
        sit = "celibataire"
        parts_excl = calculer_parts(sit, nb_enfants_ga)
        parts_ga = calculer_parts(sit, 0, 0, nb_enfants_ga)
        lines += [
            "### Règles de la garde alternée (art. 194 CGI)",
            "",
            "En garde alternée, **chaque parent bénéficie de la moitié des parts** liées aux enfants :",
            "- Garde exclusive : +0,5 part par enfant (rang 1 et 2), +1 part à partir du 3ème",
            "- Garde alternée : **+0,25 part** par enfant (rang 1 et 2), **+0,5 part** à partir du 3ème",
            "",
            f"### Votre situation ({nb_enfants_ga} enfant(s) en garde alternée)",
            f"- Parts en garde **exclusive** : {parts_excl} parts",
            f"- Parts en garde **alternée** : {parts_ga} parts",
            "",
            "### Partage des avantages fiscaux",
            "- La **majoration de parts** est partagée par moitié entre les deux parents.",
            "- Le **crédit d'impôt garde d'enfants** (50% des frais de garde) : chaque parent déduit sa part des frais qu'il supporte.",
            "- La **pension alimentaire** ne peut pas être déduite pour un enfant en garde alternée (avantage en parts déjà partagé).",
            "- Le **rattachement** d'un enfant majeur en alternée n'est pas possible (chaque parent conserve ses 0,25 parts).",
        ]
        if nb_enfants > 0:
            parts_mixte = calculer_parts("celibataire", nb_enfants, 0, nb_enfants_ga)
            lines += [
                "",
                f"### Situation mixte : {nb_enfants} enfant(s) en garde exclusive + {nb_enfants_ga} en alternée",
                f"- Parts totales : **{parts_mixte}**",
            ]
            if revenu > 0:
                res = calculer_ir(revenu, parts_mixte)
                lines += [
                    f"- Impôt estimé : **{res['impot_net']:,.0f}€** (TMI {res['taux_marginal']:.0f}%)",
                ]
        elif revenu > 0:
            res = calculer_ir(revenu, parts_ga)
            lines += [
                "",
                "### Simulation fiscale",
                f"- Parts : {parts_ga} | Impôt estimé : **{res['impot_net']:,.0f}€** (TMI {res['taux_marginal']:.0f}%)",
            ]
        lines += [
            "",
            "### Démarches",
            "- Joindre le jugement de divorce ou l'accord parental homologué à la première déclaration.",
            "- Cocher la case appropriée dans la rubrique « Enfants en garde alternée ».",
        ]

    # ── ENFANT MAJEUR RATTACHÉ ────────────────────────────────────────────────
    elif evenement == "enfant_majeur":
        age = age_enfant if age_enfant else 20
        eligible_rattachement = age <= 25
        eligible_etudes = age <= 25  # jusqu'à 25 ans si études ou service militaire

        lines += [
            "### Conditions de rattachement d'un enfant majeur (art. 196 B CGI)",
            "",
            f"- **Âge de l'enfant** : {age} ans",
            f"- **Rattachement possible** : {'Oui' if eligible_rattachement else 'Non — limite : 25 ans révolus'}",
            "",
            "**Conditions** :",
            "- Enfant de moins de **21 ans** (sans condition) ou moins de **25 ans** s'il est étudiant.",
            "- Ou en apprentissage (sans condition d'âge si contrat d'apprentissage).",
            "- L'enfant rattaché **renonce à son propre abattement de 10%** (il est imposé dans le foyer des parents).",
            "",
            "### Comparaison : rattachement vs pension alimentaire",
            "",
        ]
        # Plafond pension alimentaire enfant majeur non rattaché
        plafond_pension = 6_368  # 2025
        lines += [
            "| Critère | Rattachement | Pension alimentaire |",
            "|---------|-------------|---------------------|",
            f"| Avantage fiscal parent | +0,5 part (ou +1 à partir du 3ème) | Déduction jusqu'à {plafond_pension:,}€/enfant |",
            "| Impact sur l'enfant | Imposé dans le foyer parental | Déclare la pension comme revenu |",
            "| Condition | Enfant < 21 ans ou < 25 ans si étudiant | Enfant > 18 ans non rattaché |",
            "| Cumul avec APL | Non (revenus parents pris en compte) | Oui possible |",
            "",
        ]
        if revenu > 0 and eligible_rattachement:
            sit = "marie" if "mari" in situation_actuelle.lower() or "pacs" in situation_actuelle.lower() else "celibataire"
            parts_sans = calculer_parts(sit, nb_enfants)
            parts_avec = calculer_parts(sit, nb_enfants + 1)
            res_sans = calculer_ir(revenu, parts_sans)
            res_avec = calculer_ir(revenu, parts_avec)
            gain_rattachement = res_sans["impot_net"] - res_avec["impot_net"]
            # Avantage pension alimentaire
            avantage_pension = min(plafond_pension, plafond_pension) * (res_sans["taux_marginal"] / 100)
            lines += [
                "### Simulation comparative",
                f"| | Sans rattachement | Avec rattachement | Pension alim. déduite |",
                f"|--|---|----|---|",
                f"| Revenu imposable | {revenu:,.0f}€ | {revenu:,.0f}€ | {max(0, revenu - plafond_pension):,.0f}€ |",
                f"| Parts | {parts_sans} | {parts_avec} | {parts_sans} |",
                f"| Impôt estimé | {res_sans['impot_net']:,.0f}€ | {res_avec['impot_net']:,.0f}€ | ~{max(0, res_sans['impot_net'] - avantage_pension):,.0f}€ |",
                f"| **Économie** | — | **{gain_rattachement:,.0f}€** | **~{avantage_pension:,.0f}€** |",
                "",
                "> Comparez les deux options avec vos revenus réels. Le rattachement est souvent plus avantageux si le TMI est élevé.",
            ]
        lines += [
            "",
            "### Démarches",
            "- L'enfant signe le formulaire de demande de rattachement (disponible sur impots.gouv.fr).",
            "- Reporter l'enfant rattaché dans la rubrique appropriée de la déclaration 2042.",
            "- L'enfant ne peut pas bénéficier de la prime d'activité ou d'aides CAF calculées sur ses propres revenus.",
        ]

    # ── DÉCÈS DU CONJOINT ─────────────────────────────────────────────────────
    elif evenement == "deces_conjoint":
        lines += [
            "### Règles applicables en cas de décès du conjoint (art. 204 CGI)",
            "",
            "L'année du décès donne lieu à **deux déclarations distinctes** pour le foyer :",
            "",
            "**Déclaration 1 — Du 1er janvier au jour du décès**",
            "- Établie au nom du couple (déclaration conjointe pour la période commune).",
            "- Inclut les revenus des deux conjoints jusqu'à la date du décès.",
            "- Parts : celles du couple (2 + parts enfants).",
            "",
            "**Déclaration 2 — Du lendemain du décès au 31 décembre**",
            "- Établie au nom du conjoint survivant seul.",
            "- N'inclut que les revenus du survivant pour la période restante.",
            "- Parts du veuf : **maintien du quotient familial du couple** l'année du décès et l'année suivante (art. 195 CGI).",
            "",
            "### Parts du veuf",
            "- L'année du décès et l'année suivante : le conjoint survivant conserve **les mêmes parts qu'un couple avec enfants** + 0,5 part supplémentaire pour le 1er enfant.",
            "- Sans enfant : 2 parts (comme un couple) pour l'année du décès uniquement.",
            "- À partir de la 2ème année : situation de célibataire/veuf sans enfant = 1 part.",
        ]
        if nb_enfants > 0:
            parts_veuf_annee1 = calculer_parts("veuf", nb_enfants)
            parts_veuf_apres = calculer_parts("veuf", nb_enfants)
            # Note : la fonction calculer_parts traite "veuf" comme 1 part de base
            # Le vrai régime veuf avec enfants = 2.5 parts pour 1 enfant, 3 pour 2, etc.
            # On simule manuellement le régime favorable
            parts_regime_veuf = 2.0 + (0.5 if nb_enfants >= 1 else 0) + sum(
                0.5 if i <= 2 else 1.0 for i in range(2, nb_enfants + 1)
            )
            lines += [
                "",
                f"### Simulation — Conjoint survivant avec {nb_enfants} enfant(s)",
                f"- Parts régime veuf (année du décès et suivante) : **{parts_regime_veuf}**",
            ]
            if revenu > 0:
                res_veuf = calculer_ir(revenu, parts_regime_veuf)
                res_seul = calculer_ir(revenu, calculer_parts("celibataire", nb_enfants))
                lines += [
                    f"- Impôt avec régime veuf : **{res_veuf['impot_net']:,.0f}€**",
                    f"- Impôt en situation de parent seul (à partir de la 3ème année) : {res_seul['impot_net']:,.0f}€",
                ]
        lines += [
            "",
            "### Délais déclaratifs",
            "- La déclaration au nom du couple (1ère période) doit être déposée dans les **délais habituels**.",
            "- La déclaration du survivant (2ème période) également dans les délais normaux.",
            "- Prévenir l'administration fiscale du décès pour mettre à jour le dossier.",
            "",
            "### Succession",
            "- Le conjoint survivant est **totalement exonéré de droits de succession** (art. 796-0 bis CGI).",
            "- Les donations passées entre époux restent soumises aux règles habituelles.",
        ]

    else:
        lines += [f"Événement '{evenement}' non reconnu. Événements supportés : mariage, divorce, naissance, garde_alternee, enfant_majeur, deces_conjoint."]

    lines += [
        "",
        "---",
        "*Source : CGI art. 6, 194, 195, 196, 196 B, 204 — Barème 2026 (revenus 2025)*",
        "*Simulation indicative. Consultez impots.gouv.fr ou un conseiller fiscal pour votre situation exacte.*",
    ]
    return "\n".join(lines)


def tool_calculer_revenus_remplacement(args: Dict) -> str:
    type_revenu = args["type_revenu"]
    montant = _valider_revenu(float(args["montant"]), "montant")
    situation = args["situation_famille"]
    nb_enfants = int(args.get("nb_enfants", 0))
    rni_autres = _valider_revenu(float(args.get("rni_autres_revenus", 0)), "rni_autres_revenus")
    age_rente = args.get("age_premier_versement_rente")
    remuneration_brute = args.get("remuneration_annuelle_brute")
    indemnite_conv = args.get("indemnite_conventionnelle")

    nb_parts = calculer_parts(situation, nb_enfants)

    # Constantes fiscales 2025/2026
    PASS_2025 = 46_368  # Plafond Annuel de la Sécurité Sociale 2025
    ABATTEMENT_RETRAITE_MIN = 422      # Abattement 10% retraite — plancher par pensionné
    ABATTEMENT_RETRAITE_MAX = 4_321    # Abattement 10% retraite — plafond par pensionné
    ABATTEMENT_SALAIRE_MIN = 495       # Abattement 10% salaires — plancher
    ABATTEMENT_SALAIRE_MAX = 14_426    # Abattement 10% salaires — plafond
    ABATT_PERSONNES_AGEES_1 = 2_312    # RFR < 17 510 €
    ABATT_PERSONNES_AGEES_2 = 1_156    # RFR < 28 058 €
    SEUIL_RFR_PA_1 = 17_510
    SEUIL_RFR_PA_2 = 28_058
    PLAFOND_PENSION_ENFANT_MAJEUR = 6_368

    lines = [f"## Fiscalité des revenus de remplacement — {type_revenu.replace('_', ' ').title()}", ""]

    revenu_imposable = 0.0
    note_abattement = ""
    detail_calcul = []

    # ── CHÔMAGE (ARE) ─────────────────────────────────────────────────────────
    if type_revenu == "chomage":
        abattement = min(montant * 0.10, ABATTEMENT_SALAIRE_MAX)
        abattement = max(abattement, ABATTEMENT_SALAIRE_MIN)
        revenu_imposable = max(0, montant - abattement)
        lines += [
            "### Traitement fiscal des allocations chômage (ARE)",
            "",
            "Les allocations ARE sont **imposables comme des salaires** (art. 79 CGI).",
            "L'abattement forfaitaire de 10% pour frais professionnels s'applique.",
            "**Aucun prélèvement social** sur les allocations chômage.",
            "",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Allocations ARE brutes | {montant:,.0f}€ |",
            f"| Abattement 10% (min {ABATTEMENT_SALAIRE_MIN:,}€ / max {ABATTEMENT_SALAIRE_MAX:,}€) | -{abattement:,.0f}€ |",
            f"| **Revenu imposable ARE** | **{revenu_imposable:,.0f}€** |",
            "",
            "**À déclarer** : case 1AP/1BP de la déclaration 2042 (traitements, salaires, ARE).",
            "Le prélèvement à la source s'applique sur les ARE (taux neutre ou personnalisé).",
        ]

    # ── RETRAITE / PENSION D'INVALIDITÉ ──────────────────────────────────────
    elif type_revenu in ("retraite", "invalidite"):
        abattement_brut = montant * 0.10
        abattement = min(max(abattement_brut, ABATTEMENT_RETRAITE_MIN), ABATTEMENT_RETRAITE_MAX)
        revenu_imposable = max(0, montant - abattement)

        label = "pension de retraite" if type_revenu == "retraite" else "pension d'invalidité"
        lines += [
            f"### Traitement fiscal de la {label}",
            "",
            f"Les pensions de retraite et d'invalidité sont **imposables** (art. 79 et 158 CGI).",
            "Elles bénéficient d'un **abattement de 10% spécifique** (différent de l'abattement salaires).",
            "",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Pension brute | {montant:,.0f}€ |",
            f"| Abattement 10% (min {ABATTEMENT_RETRAITE_MIN:,}€ / max {ABATTEMENT_RETRAITE_MAX:,}€ par pensionné) | -{abattement:,.0f}€ |",
            f"| **Pension imposable** | **{revenu_imposable:,.0f}€** |",
        ]
        # Abattement spécifique personnes âgées (revenus modestes)
        rfr_estime = revenu_imposable + rni_autres
        if rfr_estime < SEUIL_RFR_PA_1:
            abatt_pa = ABATT_PERSONNES_AGEES_1
            lines += [
                "",
                f"#### Abattement spécifique personnes âgées (art. 157 bis CGI)",
                f"- RFR estimé ({rfr_estime:,.0f}€) < {SEUIL_RFR_PA_1:,}€ → abattement supplémentaire : **{abatt_pa:,}€**",
                f"- Revenu imposable après abattement PA : {max(0, revenu_imposable - abatt_pa):,.0f}€",
            ]
            revenu_imposable = max(0, revenu_imposable - abatt_pa)
        elif rfr_estime < SEUIL_RFR_PA_2:
            abatt_pa = ABATT_PERSONNES_AGEES_2
            lines += [
                "",
                f"#### Abattement spécifique personnes âgées (art. 157 bis CGI)",
                f"- RFR estimé ({rfr_estime:,.0f}€) < {SEUIL_RFR_PA_2:,}€ → abattement supplémentaire : **{abatt_pa:,}€**",
                f"- Revenu imposable après abattement PA : {max(0, revenu_imposable - abatt_pa):,.0f}€",
            ]
            revenu_imposable = max(0, revenu_imposable - abatt_pa)

        lines += [
            "",
            f"**À déclarer** : case 1AS/1BS (pensions, retraites, rentes).",
            "Les pensions d'invalidité de catégorie 1 sont imposables. Catégories 2 et 3 : imposables sauf exonération spécifique.",
        ]

    # ── RENTE VIAGÈRE À TITRE ONÉREUX (RVTO) ─────────────────────────────────
    elif type_revenu == "rente_viagere":
        age = age_rente if age_rente else 60
        if age < 50:
            fraction = 0.70
            label_age = "moins de 50 ans"
        elif age < 60:
            fraction = 0.50
            label_age = "50 à 59 ans"
        elif age < 70:
            fraction = 0.40
            label_age = "60 à 69 ans"
        else:
            fraction = 0.30
            label_age = "70 ans et plus"

        revenu_imposable = montant * fraction
        lines += [
            "### Rentes viagères à titre onéreux (RVTO)",
            "",
            "Les RVTO proviennent d'un capital aliéné (ex : vente immobilière avec rente, PER sorti en rente si versements non déduits, etc.).",
            "Seule **une fraction** est imposable, déterminée par l'âge au **premier versement** (art. 158-6 CGI).",
            "",
            "| Âge au 1er versement | Fraction imposable |",
            "|---------------------|--------------------|",
            "| Moins de 50 ans     | 70%                |",
            "| 50 à 59 ans         | 50%                |",
            "| 60 à 69 ans         | 40%                |",
            "| 70 ans et plus      | 30%                |",
            "",
            f"**Votre situation** : premier versement à **{age} ans** ({label_age})",
            "",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Rente brute annuelle | {montant:,.0f}€ |",
            f"| Fraction imposable ({fraction*100:.0f}%) | {revenu_imposable:,.0f}€ |",
            f"| Fraction exonérée ({(1-fraction)*100:.0f}%) | {montant - revenu_imposable:,.0f}€ |",
            "",
            "**À déclarer** : case 1AW/1BW (rentes viagères à titre onéreux).",
            "L'abattement de 10% retraites **ne s'applique pas** aux RVTO — la fraction imposable est directement la base.",
            "**Prélèvements sociaux** : 17,2% sur la fraction imposable si la rente provient de versements déduits (PER).",
        ]

    # ── INDEMNITÉ DE LICENCIEMENT ─────────────────────────────────────────────
    elif type_revenu == "indemnite_licenciement":
        PASS_X6 = PASS_2025 * 6  # 278 208 €
        indemnite = montant

        # Calcul du plafond d'exonération
        exo_options = []
        if remuneration_brute:
            exo_2x = remuneration_brute * 2
            exo_50pct = indemnite * 0.5
            exo_options.append(exo_2x)
            exo_options.append(exo_50pct)
        exo_options.append(PASS_X6)  # plafond absolu

        if remuneration_brute:
            # Plafond = max(2× rémunération brute, 50% indemnité), plafonné à 6 PASS
            plafond_exo = min(max(remuneration_brute * 2, indemnite * 0.5), PASS_X6)
        else:
            # Sans rémunération brute connue, on utilise uniquement le plafond 6 PASS
            plafond_exo = PASS_X6

        # Si indemnité conventionnelle connue, l'exonération est au moins égale à l'indemnité conventionnelle
        if indemnite_conv:
            plafond_exo = max(plafond_exo, indemnite_conv)
            plafond_exo = min(plafond_exo, PASS_X6)

        exo = min(indemnite, plafond_exo)
        revenu_imposable = max(0, indemnite - exo)

        lines += [
            "### Indemnité de licenciement — Régime d'exonération (art. 80 duodecies CGI)",
            "",
            "L'indemnité de licenciement est **exonérée dans la limite du plus élevé** des trois montants suivants :",
            f"1. **Deux fois la rémunération brute annuelle** de référence",
            f"2. **50% de l'indemnité** totale versée",
            f"3. Plafonnée au maximum à **6 × PASS = {PASS_X6:,}€** (PASS 2025 = {PASS_2025:,}€)",
            "",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Indemnité de licenciement totale | {indemnite:,.0f}€ |",
        ]
        if remuneration_brute:
            lines += [
                f"| 2× rémunération brute ({remuneration_brute:,.0f}€ × 2) | {remuneration_brute*2:,.0f}€ |",
                f"| 50% de l'indemnité | {indemnite*0.5:,.0f}€ |",
            ]
        if indemnite_conv:
            lines += [f"| Indemnité conventionnelle de référence | {indemnite_conv:,.0f}€ |"]
        lines += [
            f"| Plafond absolu (6 PASS) | {PASS_X6:,}€ |",
            f"| **Montant exonéré** | **{exo:,.0f}€** |",
            f"| **Montant imposable** | **{revenu_imposable:,.0f}€** |",
            "",
        ]
        if revenu_imposable == 0:
            lines.append("**Bonne nouvelle : l'intégralité de votre indemnité est exonérée d'IR.**")
        else:
            lines += [
                f"La fraction imposable ({revenu_imposable:,.0f}€) s'ajoute à vos autres revenus et est soumise au barème progressif.",
                "Elle est également soumise aux prélèvements sociaux (CSG/CRDS) selon les règles applicables.",
            ]
        lines += [
            "",
            "**Cas particulier : licenciement économique**",
            "- L'indemnité versée dans le cadre d'un licenciement économique bénéficie du même régime.",
            "- Rupture conventionnelle : exonération identique si la rupture ne permet pas de bénéficier d'une retraite à taux plein.",
        ]

    else:
        revenu_imposable = montant
        lines += [f"Type '{type_revenu}' non reconnu."]

    # ── SIMULATION IR GLOBALE ─────────────────────────────────────────────────
    if revenu_imposable > 0 or rni_autres > 0:
        rni_total = revenu_imposable + rni_autres
        res = calculer_ir(rni_total, nb_parts)
        res_sans = calculer_ir(rni_autres, nb_parts) if rni_autres > 0 else None

        lines += [
            "",
            "### Impact fiscal global",
            "",
            f"| | Montant |",
            f"|--|---------|",
            f"| Revenu imposable ({type_revenu.replace('_',' ')}) | {revenu_imposable:,.0f}€ |",
        ]
        if rni_autres > 0:
            lines.append(f"| Autres revenus du foyer | {rni_autres:,.0f}€ |")
        lines += [
            f"| **RNI total** | **{rni_total:,.0f}€** |",
            f"| Parts fiscales | {nb_parts} |",
            f"| **Impôt sur le revenu estimé** | **{res['impot_net']:,.0f}€** |",
            f"| TMI | {res['taux_marginal']:.0f}% |",
            f"| Taux moyen | {res['taux_moyen']:.1f}% |",
        ]
        if res_sans:
            impot_du_a_revenu_remp = res["impot_net"] - res_sans["impot_net"]
            lines += [
                "",
                f"> Dont **{impot_du_a_revenu_remp:,.0f}€** d'impôt attribuable au revenu de remplacement.",
            ]

    lines += [
        "",
        "---",
        "*Source : CGI art. 79, 80 duodecies, 157 bis, 158-6 — Barème 2026 (revenus 2025)*",
        "*Simulation indicative. Vérifiez votre situation sur impots.gouv.fr.*",
    ]
    return "\n".join(lines)


def tool_simuler_sortie_per(args: Dict) -> str:
    capital_total = _valider_revenu(float(args["capital_total"]), "capital_total")
    versements_cumules = _valider_revenu(float(args["versements_cumules"]), "versements_cumules")
    versements_deduits = _valider_revenu(float(args["versements_deduits"]), "versements_deduits")
    tmi_pct = float(args["tmi"])  # en %, ex: 30
    situation = args["situation"]
    age = int(args.get("age", 65))
    rente_annuelle = float(args.get("rente_annuelle", 0))

    # Validation
    versements_deduits = min(versements_deduits, versements_cumules)
    versements_non_deduits = versements_cumules - versements_deduits
    gains = max(0, capital_total - versements_cumules)
    tmi = tmi_pct / 100.0

    # Prélèvements sociaux
    TAUX_PS = 0.172
    PFU = 0.30  # Prélèvement Forfaitaire Unique (12,8% IR + 17,2% PS)
    TAUX_PFU_IR = 0.128
    TAUX_PFU_PS = 0.172

    # Abattement 10% retraite pour la rente
    ABATT_RENTE_MIN = 422
    ABATT_RENTE_MAX = 4_321

    lines = [
        "## Simulation sortie PER — Plan Épargne Retraite",
        "",
        "### Caractéristiques du PER",
        "",
        f"| Élément | Montant |",
        f"|---------|---------|",
        f"| Capital total | {capital_total:,.0f}€ |",
        f"| Versements cumulés (total) | {versements_cumules:,.0f}€ |",
        f"| dont versements déduits | {versements_deduits:,.0f}€ |",
        f"| dont versements non déduits | {versements_non_deduits:,.0f}€ |",
        f"| Plus-values / gains | {gains:,.0f}€ |",
        f"| TMI du foyer | {tmi_pct:.0f}% |",
        "",
    ]

    # ── RETRAITE EN RENTE ─────────────────────────────────────────────────────
    if situation == "retraite_rente":
        rente = rente_annuelle if rente_annuelle > 0 else capital_total * 0.04  # estimation 4%/an si non fournie
        abatt_rente = min(max(rente * 0.10, ABATT_RENTE_MIN), ABATT_RENTE_MAX)
        rente_imposable = max(0, rente - abatt_rente)
        ir_rente = rente_imposable * tmi
        # PS sur la fraction imposable des versements déduits
        # La rente issue de versements déduits : PS 17,2% sur la part issue des gains uniquement
        # Note : techniquement, la rente PER déduit est soumise au barème IR en totalité
        # Les PS (CSG 6,8% déductible + CRDS + solidarité) s'appliquent à 17,2%
        ps_rente = rente * TAUX_PS  # PS sur rente totale (régime général)
        rente_nette = rente - ir_rente - ps_rente

        lines += [
            "### Scénario : Sortie en RENTE à la retraite",
            "",
            "La rente PER est assimilée à une **pension de retraite** (art. L224-2 Code monétaire).",
            "Elle bénéficie de l'abattement de 10% spécifique retraites.",
            "",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Rente annuelle brute | {rente:,.0f}€ |",
            f"| Abattement 10% retraites (min {ABATT_RENTE_MIN:,}€ / max {ABATT_RENTE_MAX:,}€) | -{abatt_rente:,.0f}€ |",
            f"| Rente imposable (barème IR, TMI {tmi_pct:.0f}%) | {rente_imposable:,.0f}€ → **{ir_rente:,.0f}€ d'IR** |",
            f"| Prélèvements sociaux 17,2% | -{ps_rente:,.0f}€ |",
            f"| **Rente nette annuelle** | **{rente_nette:,.0f}€** |",
            "",
            "> Les prélèvements sociaux incluent la CSG (dont 6,8% déductible l'année suivante), CRDS et prélèvement de solidarité.",
        ]

    # ── RETRAITE EN CAPITAL ────────────────────────────────────────────────────
    elif situation == "retraite_capital":
        lines += [
            "### Scénario : Sortie en CAPITAL à la retraite",
            "",
            "Le capital PER se décompose selon l'origine des versements (déduits / non déduits).",
            "",
        ]

        # Fraction du capital correspondant aux versements déduits
        if versements_cumules > 0:
            ratio_deduit = versements_deduits / versements_cumules
            ratio_non_deduit = versements_non_deduits / versements_cumules
        else:
            ratio_deduit = 1.0
            ratio_non_deduit = 0.0

        cap_deduit = capital_total * ratio_deduit
        cap_non_deduit = capital_total * ratio_non_deduit
        gains_deduits = gains * ratio_deduit
        gains_non_deduits = gains * ratio_non_deduit
        versements_deduits_sortie = versements_deduits  # fraction des versements déduits
        versements_non_deduits_sortie = versements_non_deduits

        # Partie déduites : capital = imposable barème IR ; gains = PFU 30%
        ir_cap_deduit = versements_deduits_sortie * tmi
        pfu_gains_deduits = gains_deduits * PFU

        # Partie non déduite : capital = exonéré ; gains = PFU 30%
        pfu_gains_non_deduits = gains_non_deduits * PFU

        total_fiscalite = ir_cap_deduit + pfu_gains_deduits + pfu_gains_non_deduits
        capital_net = capital_total - total_fiscalite

        lines += [
            "#### Versements DÉDUITS (imposables à l'IR)",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Fraction du capital (versements déduits) | {versements_deduits_sortie:,.0f}€ |",
            f"| Imposition au barème IR (TMI {tmi_pct:.0f}%) | **{ir_cap_deduit:,.0f}€** |",
            f"| Plus-values rattachées (gains sur versements déduits) | {gains_deduits:,.0f}€ |",
            f"| PFU 30% sur ces gains | **{pfu_gains_deduits:,.0f}€** |",
            "",
            "#### Versements NON DÉDUITS (capital exonéré, gains au PFU)",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Fraction du capital (versements non déduits) | {versements_non_deduits_sortie:,.0f}€ | **EXONÉRÉ** |",
            f"| Plus-values rattachées (gains sur versements non déduits) | {gains_non_deduits:,.0f}€ |",
            f"| PFU 30% sur ces gains | **{pfu_gains_non_deduits:,.0f}€** |",
            "",
            "#### Bilan global",
            f"| | Montant |",
            f"|--|---------|",
            f"| Capital total PER | {capital_total:,.0f}€ |",
            f"| Total fiscalité (IR + PFU) | -{total_fiscalite:,.0f}€ |",
            f"| **Capital net perçu** | **{capital_net:,.0f}€** |",
            f"| Taux de prélèvement effectif | {total_fiscalite/capital_total*100:.1f}% |" if capital_total > 0 else "",
        ]

    # ── DÉBLOCAGE ANTICIPÉ — RÉSIDENCE PRINCIPALE ─────────────────────────────
    elif situation == "anticipation_rp":
        lines += [
            "### Scénario : Déblocage anticipé — Acquisition résidence principale",
            "",
            "> **Attention** : le déblocage pour résidence principale est soumis à l'IR (contrairement aux autres déblocages anticipés exceptionnels).",
            "",
            "**Règle applicable** (art. L224-4 Code monétaire) :",
            "- La fraction correspondant aux **versements déduits** : imposable au barème IR (TMI).",
            "- La fraction correspondant aux **versements non déduits** : exonérée d'IR.",
            "- Les **plus-values** (gains) : soumises au **PFU 30%** dans tous les cas.",
            "",
        ]
        ir_versements_deduits = versements_deduits * tmi
        pfu_gains = gains * PFU
        total_fiscalite = ir_versements_deduits + pfu_gains
        capital_net = capital_total - total_fiscalite

        lines += [
            f"| Élément | Montant | Fiscalité |",
            f"|---------|---------|-----------|",
            f"| Versements déduits | {versements_deduits:,.0f}€ | IR au barème ({tmi_pct:.0f}%) → **{ir_versements_deduits:,.0f}€** |",
            f"| Versements non déduits | {versements_non_deduits:,.0f}€ | **Exonéré** |",
            f"| Plus-values / gains | {gains:,.0f}€ | PFU 30% → **{pfu_gains:,.0f}€** |",
            "",
            f"| | |",
            f"|--|--|",
            f"| Capital total | {capital_total:,.0f}€ |",
            f"| Total impôts | -{total_fiscalite:,.0f}€ |",
            f"| **Capital net** | **{capital_net:,.0f}€** |",
            "",
            "**Documents requis** : contrat de réservation ou compromis de vente pour le déblocage anticipé.",
            "Le déblocage peut être partiel ou total.",
        ]

    # ── DÉBLOCAGE ANTICIPÉ EXCEPTIONNEL ──────────────────────────────────────
    elif situation == "anticipation_exceptionnelle":
        lines += [
            "### Scénario : Déblocage anticipé exceptionnel",
            "",
            "**Cas éligibles** (art. L224-4 Code monétaire) :",
            "- Invalidité de 2ème ou 3ème catégorie (assuré, conjoint ou enfant)",
            "- Décès du conjoint ou partenaire PACS",
            "- Surendettement (commission de surendettement)",
            "- Expiration des droits à l'assurance chômage",
            "- Liquidation judiciaire (travailleur indépendant)",
            "",
            "> **Ces déblocages sont EXONÉRÉS d'IR**, même si les versements avaient été déduits.",
            "",
            "**Régime fiscal** :",
            "- Fraction correspondant aux versements (déduits ou non) : **exonérée d'IR**.",
            "- **Plus-values / gains** : soumises aux prélèvements sociaux 17,2%.",
            "- Les gains restent soumis aux **PS uniquement** (pas d'IR, pas de PFU).",
            "",
        ]
        ps_gains = gains * TAUX_PS
        total_fiscalite = ps_gains
        capital_net = capital_total - total_fiscalite

        lines += [
            f"| Élément | Montant | Fiscalité |",
            f"|---------|---------|-----------|",
            f"| Versements déduits | {versements_deduits:,.0f}€ | **EXONÉRÉ d'IR** |",
            f"| Versements non déduits | {versements_non_deduits:,.0f}€ | **EXONÉRÉ d'IR** |",
            f"| Plus-values / gains | {gains:,.0f}€ | PS 17,2% → **{ps_gains:,.0f}€** |",
            "",
            f"| | |",
            f"|--|--|",
            f"| Capital total | {capital_total:,.0f}€ |",
            f"| Total prélèvements (PS uniquement) | -{total_fiscalite:,.0f}€ |",
            f"| **Capital net** | **{capital_net:,.0f}€** |",
            "",
            "**Documents requis** : justificatif du cas de déblocage (notification CPAM, jugement, attestation Pôle Emploi, etc.).",
        ]

    else:
        lines.append(f"Situation '{situation}' non reconnue.")

    # ── TABLEAU COMPARATIF FINAL ───────────────────────────────────────────────
    if situation in ("retraite_capital", "anticipation_rp", "anticipation_exceptionnelle"):
        lines += [
            "",
            "---",
            "### Aide à la décision — Comparaison des modes de sortie",
            "",
            "| Mode de sortie | Versements déduits | Versements non déduits | Gains |",
            "|----------------|-------------------|----------------------|-------|",
            f"| **Retraite — Capital** | Barème IR (TMI {tmi_pct:.0f}%) | Exonéré | PFU 30% |",
            f"| **Retraite — Rente** | Barème IR après abatt. 10% | Fraction RVTO imposable | PS 17,2% inclus |",
            f"| **Anticipation RP** | Barème IR (TMI {tmi_pct:.0f}%) | Exonéré | PFU 30% |",
            f"| **Anticipation exceptionnelle** | Exonéré | Exonéré | PS 17,2% uniquement |",
        ]

    lines += [
        "",
        "### Points clés à retenir",
        "- Les versements **déduits** à l'entrée sont **imposables à la sortie** (principe de symétrie fiscale).",
        "- Les versements **non déduits** sont exonérés à la sortie (pas de double imposition).",
        f"- Les **plus-values** sont toujours soumises au PFU 30% (sauf déblocage exceptionnel : PS 17,2% seulement).",
        "- À la retraite, le TMI est souvent plus faible → c'est tout l'intérêt de la déduction à l'entrée.",
        f"- Avec un TMI de {tmi_pct:.0f}% aujourd'hui, chaque euro déduit du PER économise {tmi_pct:.0f} centimes d'impôt.",
        "",
        "---",
        "*Source : Art. L224-1 à L224-40 Code monétaire et financier — CGI art. 163 quatervicies, 158*",
        "*Simulation indicative. Les montants exacts dépendent de votre situation fiscale globale.*",
    ]
    return "\n".join(lines)


def tool_optimiser_epargne_salariale(args: Dict) -> str:
    """Optimise l'épargne salariale : PEE, PERCO, intéressement, participation, AGA, BSPCE."""
    dispositif = args.get("type_dispositif", "synthese")
    montant = float(args.get("montant", 0))
    abondement = float(args.get("abondement_employeur", 0))
    tmi = float(args.get("tmi", 30))
    moins_3ans = bool(args.get("moins_3ans_societe", False))

    # Constantes
    PASS_2025 = 46_368
    ABOND_MAX_PEE = PASS_2025 * 0.08        # 3,709.44€
    ABOND_MAX_PERCO = PASS_2025 * 0.16      # 7,418.88€
    CSG_CRDS = 9.7  # %

    lines = ["# Optimisation de l'épargne salariale", ""]

    if dispositif == "interessement":
        exo_ir = montant if montant > 0 else 0
        csg = montant * CSG_CRDS / 100
        lines += [
            "## Intéressement",
            "",
            "### Régime fiscal",
            f"- Montant brut : {montant:,.0f}€",
            "- **Si placé sur PEE/PERCOL :** exonéré d'IR (bloqué 5 ans minimum)",
            f"- CSG/CRDS : {CSG_CRDS}% = {csg:,.0f}€ (non déductible)",
            f"- Économie d'IR estimée vs salaire : ~{montant * tmi/100:,.0f}€ (à TMI {tmi}%)",
            "",
            "- **Si perçu en cash :** imposable à l'IR comme salaire",
            f"  → Impôt à TMI {tmi}% : ~{montant * tmi/100:,.0f}€",
            "",
            "### Recommandation",
            "- ✅ Toujours placer sur PEE ou PERCOL pour l'exonération d'IR",
            f"- Abondement employeur possible : jusqu'à 300% de votre versement, plafonné à {ABOND_MAX_PEE:,.0f}€/an",
        ]
        if abondement > 0:
            ab_net = min(abondement, ABOND_MAX_PEE)
            lines += [
                "",
                f"### Avec abondement employeur ({abondement:,.0f}€)",
                f"- Abondement retenu (plafond {ABOND_MAX_PEE:,.0f}€) : {ab_net:,.0f}€",
                f"- Total épargné : {montant + ab_net:,.0f}€",
                f"- Gain fiscal immédiat (exo IR) : ~{(montant + ab_net) * tmi/100:,.0f}€",
            ]

    elif dispositif == "participation":
        lines += [
            "## Participation aux résultats",
            "",
            "### Régime fiscal",
            "- Même régime que l'intéressement si bloquée sur PEE/PERCOL : **exonérée d'IR**",
            f"- CSG/CRDS : {CSG_CRDS}% prélevée à la source",
            "- Déblocage anticipé possible dans 9 cas légaux (mariage, naissance, achat RP, licenciement…)",
            "",
            "### Différence avec l'intéressement",
            "- La participation est **obligatoire** dans les entreprises de + de 50 salariés",
            "- L'intéressement est optionnel (accord d'entreprise)",
            "- Les deux sont **cumulables** et ont les mêmes plafonds d'abondement",
        ]

    elif dispositif == "pee":
        gains = montant * 0.05 * 5  # estimation 5%/an sur 5 ans
        ps = gains * 0.172
        lines += [
            "## Plan Épargne Entreprise (PEE)",
            "",
            "### Caractéristiques",
            "- Blocage : **5 ans minimum** (sauf déblocage anticipé légal)",
            "- Versements volontaires du salarié + abondement employeur",
            f"- Abondement employeur max : **{ABOND_MAX_PEE:,.0f}€/an** (8% du PASS)",
            "- L'abondement est exonéré d'IR et de charges patronales (hors forfait social)",
            "",
            "### Fiscalité à la sortie",
            "- **Gains/intérêts** : exonérés d'IR (mais prélèvements sociaux 17.2%)",
            f"- Estimation sur {montant:,.0f}€ à 5%/an pendant 5 ans :",
            f"  - Gains estimés : ~{gains:,.0f}€",
            f"  - PS (17.2%) : ~{ps:,.0f}€",
            f"  - **Net perçu : ~{montant + gains - ps:,.0f}€**",
            "",
            "### Cas de déblocage anticipé",
            "Mariage/PACS, naissance 3ème enfant, divorce, achat résidence principale,",
            "création d'entreprise, chômage, invalidité, décès, surendettement.",
        ]

    elif dispositif == "perco":
        lines += [
            "## PERCO / PERCOL (Plan Épargne Retraite Collectif)",
            "",
            "### Caractéristiques",
            "- Blocage jusqu'à la **retraite** (sauf cas exceptionnels)",
            f"- Abondement employeur max : **{ABOND_MAX_PERCO:,.0f}€/an** (16% du PASS)",
            "- Versements volontaires **déductibles du revenu imposable** (comme PER individuel)",
            "",
            "### Fiscalité",
            "- Versements exonérés d'IR + abondement exonéré de charges patronales",
            "- **Sortie en capital** : versements imposables (si déduits) + PS 17.2% sur gains",
            "- **Sortie en rente** : abattement 10% puis barème IR",
            "",
            f"### Économie d'IR estimée",
            f"- Si vous versez {montant:,.0f}€ à TMI {tmi}% : économie ~{montant * tmi/100:,.0f}€",
            f"- Avec abondement {abondement:,.0f}€ : économie totale sur {montant + min(abondement, ABOND_MAX_PERCO):,.0f}€",
        ]

    elif dispositif == "aga":
        gain_acquisition = montant  # valeur des actions à la date d'attribution
        # Plan conforme : abattement 50% si détention > 2 ans
        base_csg = gain_acquisition
        csg_amount = base_csg * CSG_CRDS / 100
        if montant > 0:
            # Gain d'acquisition imposé comme salaire avec abattement 50% si plan conforme
            base_imposable_conforme = montant * 0.50
            ir_conforme = base_imposable_conforme * tmi / 100
            ir_non_conforme = montant * tmi / 100
            lines += [
                "## Actions Gratuites d'Attribution (AGA)",
                "",
                "### Fiscalité du gain d'acquisition",
                f"Valeur des actions à la date d'acquisition : {montant:,.0f}€",
                "",
                "**Plan conforme (conservation > 2 ans après acquisition)**",
                f"- Abattement : **50%**",
                f"- Base imposable : {base_imposable_conforme:,.0f}€",
                f"- IR estimé à TMI {tmi}% : ~{ir_conforme:,.0f}€",
                f"- CSG/CRDS (9.7%) : ~{csg_amount:,.0f}€",
                f"- **Net estimé : ~{montant - ir_conforme - csg_amount:,.0f}€**",
                "",
                "**Plan non conforme ou conservation < 2 ans**",
                f"- Imposé comme salaire sans abattement",
                f"- IR à TMI {tmi}% : ~{ir_non_conforme:,.0f}€",
                "",
                "### Gain de cession (plus-value)",
                "- PFU 30% sur la différence prix de vente - valeur à l'acquisition",
            ]

    elif dispositif == "bspce":
        # BSPCE: PFU 12.8% IR + 17.2% PS = 30% si plan normal
        # Si < 3 ans dans la société: IR 30% + PS 17.2% = 47.2%
        taux_ir_bspce = 30.0 if moins_3ans else 12.8
        taux_total = taux_ir_bspce + 17.2
        ir = montant * taux_ir_bspce / 100
        ps = montant * 17.2 / 100
        net = montant - ir - ps
        lines += [
            "## BSPCE (Bons de Souscription de Parts de Créateur d'Entreprise)",
            "",
            "### Conditions d'émission",
            "- Société par actions, < 15 ans, non cotée (ou petite capitalisation)",
            "- Réservés aux salariés et dirigeants",
            "",
            "### Fiscalité du gain (prix de vente - prix d'exercice)",
            f"Gain estimé : {montant:,.0f}€",
            "",
        ]
        if moins_3ans:
            lines += [
                "⚠️ **Taux majoré** : ancienneté < 3 ans dans la société",
                f"- IR : **30%** = {ir:,.0f}€",
                f"- Prélèvements sociaux : 17.2% = {ps:,.0f}€",
                f"- **Taux global : {taux_total}%** → Net : {net:,.0f}€",
            ]
        else:
            lines += [
                "✅ **Taux standard** : ancienneté ≥ 3 ans",
                f"- IR (PFU) : 12.8% = {ir:,.0f}€",
                f"- Prélèvements sociaux : 17.2% = {ps:,.0f}€",
                f"- **Taux global : {taux_total}%** → Net : {net:,.0f}€",
            ]
        lines += [
            "",
            "### Comparaison avec un salaire équivalent",
            f"- Salaire imposé à TMI {tmi}% + charges : taux effectif ~{tmi + 22:.0f}%",
            f"- BSPCE : {taux_total}% → **avantage fiscal ~{max(0, tmi + 22 - taux_total):.0f}pts**",
        ]

    else:  # synthese
        lines += [
            "## Synthèse de l'épargne salariale",
            "",
            "| Dispositif | Exonération IR | Blocage | Abondement max employeur | Atout principal |",
            "|-----------|--------------|---------|--------------------------|-----------------|",
            f"| **Intéressement** | ✅ Si PEE | 5 ans | {ABOND_MAX_PEE:,.0f}€/an | Flexible, exo immédiate |",
            f"| **Participation** | ✅ Si PEE | 5 ans | {ABOND_MAX_PEE:,.0f}€/an | Obligatoire >50 sal. |",
            f"| **PEE** | ✅ Gains exonérés | 5 ans | {ABOND_MAX_PEE:,.0f}€/an | Court/moyen terme |",
            f"| **PERCOL** | ✅ Versements déductibles | Retraite | {ABOND_MAX_PERCO:,.0f}€/an | Retraite + déduction |",
            "| **AGA** | Partiel (abatt. 50%) | 2 ans | — | Fidélisation dirigeants |",
            "| **BSPCE** | PFU 30% (ou 47.2%) | — | — | Startups, création valeur |",
            "",
            "### Stratégie recommandée",
            "1. **Maximisez l'abondement** : placez au moins autant que l'abondement max employeur",
            f"   → Abondement max PEE : {ABOND_MAX_PEE:,.0f}€/an | PERCOL : {ABOND_MAX_PERCO:,.0f}€/an",
            "2. **Intéressement/participation** : toujours placer sur PEE ou PERCOL (jamais en cash)",
            "3. **Arbitrage PEE vs PERCOL** : si vous approchez la retraite, PERCOL + déduction IR",
            "4. **BSPCE** : lever le plus tôt possible pour maximiser la plus-value future",
            "",
            "### Plafonds 2025 (PASS = 46 368€)",
            f"- Abondement PEE : 8% PASS = **{ABOND_MAX_PEE:,.0f}€/an**",
            f"- Abondement PERCOL : 16% PASS = **{ABOND_MAX_PERCO:,.0f}€/an**",
            "- Intéressement : plafonné à 75% du PASS par bénéficiaire",
        ]

    lines += [
        "",
        "---",
        "*Source : Art. L3312-1 à L3315-5 Code du travail — CGI art. 81 (18° et 18° bis), 150-0 A*",
    ]
    return "\n".join(lines)


def tool_calculer_impot_societes(args: Dict) -> str:
    """Calcule l'IS français : taux réduit PME 15% / taux normal 25%."""
    benefice = _valider_revenu(float(args["benefice"]), "benefice")
    ca = float(args.get("ca", 0))
    capital_pp_pct = float(args.get("capital_personnes_physiques_pct", 100))
    deficit_reporte = float(args.get("deficit_reporte", 0))

    # Éligibilité taux réduit PME
    eligible_taux_reduit = (
        (ca == 0 or ca < 10_000_000) and
        capital_pp_pct >= 75
    )

    SEUIL_TAUX_REDUIT = 42_500
    TAUX_REDUIT = 0.15
    TAUX_NORMAL = 0.25
    SEUIL_CONTRIBUTION_SOCIALE = 763_000

    # Bénéfice après déficits reportés
    benefice_apres_deficit = max(0, benefice - deficit_reporte)
    deficit_utilise = min(deficit_reporte, benefice)
    deficit_restant = max(0, deficit_reporte - deficit_utilise)

    # Calcul IS
    if eligible_taux_reduit:
        if benefice_apres_deficit <= SEUIL_TAUX_REDUIT:
            is_reduit = benefice_apres_deficit * TAUX_REDUIT
            is_normal = 0.0
        else:
            is_reduit = SEUIL_TAUX_REDUIT * TAUX_REDUIT
            is_normal = (benefice_apres_deficit - SEUIL_TAUX_REDUIT) * TAUX_NORMAL
    else:
        is_reduit = 0.0
        is_normal = benefice_apres_deficit * TAUX_NORMAL

    is_total = is_reduit + is_normal

    # Contribution sociale (3.3% si IS > 763 000€ pour grandes entreprises)
    contribution_sociale = 0.0
    if is_total > SEUIL_CONTRIBUTION_SOCIALE:
        contribution_sociale = (is_total - SEUIL_CONTRIBUTION_SOCIALE) * 0.033

    is_final = is_total + contribution_sociale

    # Taux effectif
    taux_effectif = is_final / benefice * 100 if benefice > 0 else 0

    # Résultat net
    resultat_net = benefice_apres_deficit - is_final

    # Acomptes trimestriels
    acompte = is_total / 4  # simplification

    lines = [
        "# Impôt sur les Sociétés (IS) 2025",
        "",
        "## Paramètres",
        f"- Bénéfice imposable : {benefice:,.0f}€",
    ]

    if deficit_reporte > 0:
        lines += [
            f"- Déficit reporté antérieur : {deficit_reporte:,.0f}€",
            f"- Déficit imputé : {deficit_utilise:,.0f}€",
            f"- Bénéfice après imputation : {benefice_apres_deficit:,.0f}€",
        ]
        if deficit_restant > 0:
            lines.append(f"- Déficit restant à reporter : {deficit_restant:,.0f}€")

    lines += [""]

    # Éligibilité
    if eligible_taux_reduit:
        lines += [
            "## ✅ Éligible au taux réduit PME",
            "Conditions remplies :",
            f"- CA {'non renseigné (supposé < 10M€)' if ca == 0 else f'{ca:,.0f}€ < 10 000 000€'}",
            f"- Capital détenu par personnes physiques : {capital_pp_pct:.0f}% ≥ 75%",
            "",
        ]
    else:
        lines += [
            "## ⚠️ Non éligible au taux réduit PME",
        ]
        if ca >= 10_000_000:
            lines.append(f"- CA {ca:,.0f}€ ≥ 10 000 000€")
        if capital_pp_pct < 75:
            lines.append(f"- Capital PP : {capital_pp_pct:.0f}% < 75%")
        lines.append("")

    lines += [
        "## Calcul de l'IS",
        "",
        "| Tranche | Taux | Base | IS |",
        "|---------|------|------|-----|",
    ]

    if eligible_taux_reduit:
        base_reduit = min(benefice_apres_deficit, SEUIL_TAUX_REDUIT)
        lines.append(f"| Jusqu'à {SEUIL_TAUX_REDUIT:,}€ | 15% | {base_reduit:,.0f}€ | {is_reduit:,.0f}€ |")
        if benefice_apres_deficit > SEUIL_TAUX_REDUIT:
            base_norm = benefice_apres_deficit - SEUIL_TAUX_REDUIT
            lines.append(f"| Au-delà de {SEUIL_TAUX_REDUIT:,}€ | 25% | {base_norm:,.0f}€ | {is_normal:,.0f}€ |")
    else:
        lines.append(f"| Totalité | 25% | {benefice_apres_deficit:,.0f}€ | {is_normal:,.0f}€ |")

    lines += [
        f"| **Total IS** | | | **{is_total:,.0f}€** |",
        "",
    ]

    if contribution_sociale > 0:
        lines += [
            f"### Contribution sociale des sociétés (3.3%)",
            f"- IS {is_total:,.0f}€ > seuil {SEUIL_CONTRIBUTION_SOCIALE:,}€",
            f"- Contribution : {contribution_sociale:,.0f}€",
            "",
        ]

    lines += [
        "## Résultat",
        f"| Indicateur | Montant |",
        f"|-----------|---------|",
        f"| IS total | {is_final:,.0f}€ |",
        f"| Taux effectif | {taux_effectif:.1f}% |",
        f"| Résultat net après IS | {resultat_net:,.0f}€ |",
        "",
        "## Acomptes provisionnels",
        f"- 4 acomptes égaux : **{acompte:,.0f}€ / trimestre**",
        "- Dates : 15 mars · 15 juin · 15 septembre · 15 décembre",
        "- Exonération si IS N-1 < 3 000€",
        "",
        "## Déficit reportable",
        "- **Report en avant** : illimité dans le temps",
        "- Déduction plafonnée à : 1 000 000€ + 50% du bénéfice excédant ce montant",
        "- **Report en arrière (carry-back)** : sur le seul exercice précédent, max 1 000 000€",
        "",
        "## Distribution des dividendes",
        f"Sur le résultat net {resultat_net:,.0f}€ :",
        "- **PFU 30%** sur dividendes (12.8% IR + 17.2% PS)",
        "- Ou option barème + abattement 40% (si plus favorable)",
        f"- Ex. : dividende de {resultat_net:,.0f}€ → PFU {resultat_net * 0.30:,.0f}€ → net {resultat_net * 0.70:,.0f}€",
        "",
        "---",
        "*Source : CGI art. 219, 235 ter ZC — Taux IS fixé par LFR 2022*",
    ]
    return "\n".join(lines)


def tool_optimiser_remuneration_dirigeant(args: Dict) -> str:
    """Optimise rémunération vs dividendes pour dirigeant de société IS."""
    benefice_brut = _valider_revenu(float(args["benefice_brut_societe"]), "benefice_brut_societe")
    remuneration = float(args["remuneration_souhaitee"])
    structure = args.get("structure", "sasu").lower()
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))

    nb_parts_ir = calculer_parts(situation, nb_enfants)

    # Taux de charges sociales simplifiés
    if structure == "sasu":
        # Assimilé salarié : charges pat ~42% + sal ~22% → coût total ~1.42× brut, net ~0.78× brut
        coeff_cout_societe = 1.42   # charges patronales incluses
        coeff_net_salarie = 0.78    # après charges salariales (approximation)
        label_regime = "Assimilé salarié (SASU)"
    else:
        # TNS (gérant majoritaire EURL/SARL IS) : cotisations ~45% du net = ~31% du brut
        coeff_cout_societe = 1.31
        coeff_net_salarie = 0.69
        label_regime = "TNS gérant majoritaire (EURL/SARL IS)"

    SEUIL_IS_REDUIT = 42_500
    TAUX_IS_REDUIT = 0.15
    TAUX_IS_NORMAL = 0.25

    def calc_is(base: float) -> float:
        if base <= 0:
            return 0.0
        if base <= SEUIL_IS_REDUIT:
            return base * TAUX_IS_REDUIT
        return SEUIL_IS_REDUIT * TAUX_IS_REDUIT + (base - SEUIL_IS_REDUIT) * TAUX_IS_NORMAL

    def calc_ir(rni: float) -> float:
        res = calculer_ir(rni, nb_parts_ir)
        return res["impot_net"]

    lines = [
        "# Optimisation Rémunération Dirigeant",
        f"**Structure** : {structure.upper()} — {label_regime}",
        f"**Bénéfice brut avant rémunération** : {benefice_brut:,.0f}€",
        "",
    ]

    # ── Scénario A : rémunération souhaitée + zéro dividende ─────────────────
    cout_remun_a = remuneration * coeff_cout_societe
    net_remun_a = remuneration * coeff_net_salarie
    benefice_apres_remun_a = max(0, benefice_brut - cout_remun_a)
    is_a = calc_is(benefice_apres_remun_a)
    resultat_net_a = benefice_apres_remun_a - is_a
    # IR sur le revenu net du dirigeant
    rni_a = net_remun_a * 0.90  # abattement 10% salarié (approximation)
    ir_a = calc_ir(rni_a)
    net_total_a = net_remun_a - ir_a + resultat_net_a  # + bénéfices non distribués

    # ── Scénario B : rémunération réduite de moitié + dividendes ─────────────
    remun_b = remuneration * 0.5
    cout_remun_b = remun_b * coeff_cout_societe
    net_remun_b = remun_b * coeff_net_salarie
    benefice_apres_remun_b = max(0, benefice_brut - cout_remun_b)
    is_b = calc_is(benefice_apres_remun_b)
    resultat_net_b = benefice_apres_remun_b - is_b
    # L'actionnaire décide de distribuer tout le résultat net en dividendes
    dividendes_bruts_b = resultat_net_b
    pfu_b = dividendes_bruts_b * 0.30  # PFU 30%
    net_dividendes_b = dividendes_bruts_b - pfu_b
    rni_b = net_remun_b * 0.90
    ir_b = calc_ir(rni_b)
    net_total_b = net_remun_b - ir_b + net_dividendes_b

    # ── Scénario C : zéro rémunération + dividendes ───────────────────────────
    is_c = calc_is(benefice_brut)
    resultat_net_c = benefice_brut - is_c
    dividendes_bruts_c = resultat_net_c
    pfu_c = dividendes_bruts_c * 0.30
    net_dividendes_c = dividendes_bruts_c - pfu_c
    net_total_c = net_dividendes_c

    lines += [
        "## Comparatif des scénarios",
        "",
        f"| | **A — Tout en rémunération** | **B — Mixte (50/50)** | **C — Tout en dividendes** |",
        f"|--|--|--|--|",
        f"| Rémunération brute | {remuneration:,.0f}€ | {remun_b:,.0f}€ | 0€ |",
        f"| Coût charges sociales | {remuneration*(coeff_cout_societe-1):,.0f}€ | {remun_b*(coeff_cout_societe-1):,.0f}€ | 0€ |",
        f"| Bénéfice IS après remun | {benefice_apres_remun_a:,.0f}€ | {benefice_apres_remun_b:,.0f}€ | {benefice_brut:,.0f}€ |",
        f"| IS payé | {is_a:,.0f}€ | {is_b:,.0f}€ | {is_c:,.0f}€ |",
        f"| Net salarié (après charges) | {net_remun_a:,.0f}€ | {net_remun_b:,.0f}€ | — |",
        f"| IR sur rémunération | {ir_a:,.0f}€ | {ir_b:,.0f}€ | — |",
        f"| Dividendes nets (PFU 30%) | — | {net_dividendes_b:,.0f}€ | {net_dividendes_c:,.0f}€ |",
        f"| **Net total perçu** | **{net_remun_a - ir_a:,.0f}€** | **{net_remun_b - ir_b + net_dividendes_b:,.0f}€** | **{net_dividendes_c:,.0f}€** |",
        "",
        "*(Scénarios A et B : résultat non distribué mis en réserve)*",
        "",
    ]

    # Recommandation
    best = max(
        ("A", net_remun_a - ir_a),
        ("B", net_remun_b - ir_b + net_dividendes_b),
        ("C", net_dividendes_c),
        key=lambda x: x[1]
    )
    lines += [
        f"## ✅ Recommandation : Scénario **{best[0]}** — net immédiat le plus élevé ({best[1]:,.0f}€)",
        "",
        "### Points d'attention",
    ]

    if structure == "sasu":
        lines += [
            "- **SASU** : dividendes soumis au PFU 30% uniquement (pas de cotisations sociales)",
            "- Une rémunération élevée génère des droits à la retraite et une meilleure protection sociale",
        ]
    else:
        lines += [
            "- **EURL/SARL IS** : dividendes > 10% du capital soumis aux cotisations TNS (~17%)",
            "  → L'avantage réel des dividendes pour un gérant TNS est moins net qu'en SASU",
        ]

    lines += [
        "- L'optimisation dépend aussi de votre besoin de trésorerie, retraite et protection sociale",
        "- ⚠️ Simulation simplifiée. Consultez un expert-comptable pour votre situation précise.",
        "",
        "---",
        "*Source : CGI art. 13, 62, 158 — CSS art. L131-6 — Taux IS art. 219*",
    ]
    return "\n".join(lines)


def tool_calculer_fiscalite_crypto(args: Dict) -> str:
    """Fiscalité des cryptomonnaies — méthode PAMC officielle (formulaire 2086)."""
    prix_cession = _valider_revenu(float(args["prix_total_cession"]), "prix_total_cession")
    valeur_portefeuille = float(args.get("valeur_portefeuille_avant_cession", 0))
    pamc = float(args.get("prix_acquisition_moyen_portefeuille", 0))
    mv_anterieures = float(args.get("moins_values_anterieures", 0))
    rev_staking = float(args.get("revenus_staking", 0))
    rev_mining = float(args.get("revenus_mining", 0))
    rev_nft = float(args.get("revenus_nft", 0))
    tmi = float(args.get("tmi", 30))

    SEUIL_IMPOSITION = 305.0
    PFU_IR = 12.8
    PFU_PS = 17.2
    PFU_TOTAL = 30.0

    lines = [
        "# Fiscalité des Cryptomonnaies 2025",
        "*(Art. 150 VH bis CGI — Formulaire 2086)*",
        "",
    ]

    # ── Calcul de la plus-value selon formule officielle ─────────────────────
    if valeur_portefeuille > 0 and pamc > 0:
        # PV = Prix cession - (PAMC × Prix cession / Valeur totale portefeuille)
        fraction = prix_cession / valeur_portefeuille if valeur_portefeuille > 0 else 1.0
        prix_revient = pamc * fraction
        pv_brute = prix_cession - prix_revient
        pv_apres_mv = pv_brute - mv_anterieures

        lines += [
            "## Calcul de la plus-value (méthode PAMC officielle)",
            "",
            "**Formule** : PV = Prix de cession − (PAMC × Prix de cession / Valeur totale du portefeuille)",
            "",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Prix de cession | {prix_cession:,.2f}€ |",
            f"| Valeur totale du portefeuille avant cession | {valeur_portefeuille:,.2f}€ |",
            f"| PAMC (Prix d'Acquisition Moyen Cumulé) | {pamc:,.2f}€ |",
            f"| Fraction cédée ({fraction*100:.2f}%) | {prix_revient:,.2f}€ |",
            f"| **Plus-value brute** | **{pv_brute:,.2f}€** |",
        ]

        if mv_anterieures > 0:
            lines += [
                f"| Moins-values antérieures imputées | -{mv_anterieures:,.2f}€ |",
                f"| **Plus-value nette** | **{pv_apres_mv:,.2f}€** |",
            ]
        lines.append("")

        # Seuil d'imposition
        if prix_cession <= SEUIL_IMPOSITION:
            lines += [
                f"## ✅ Exonération — Cessions ≤ {SEUIL_IMPOSITION}€/an",
                f"Total de cessions : {prix_cession:.2f}€ ≤ 305€ → **aucune imposition**",
                "*(Le seuil de 305€ s'applique au total des cessions, pas à la plus-value)*",
            ]
        elif pv_apres_mv <= 0:
            lines += [
                "## Moins-value — Aucun impôt dû",
                f"Plus-value nette après imputation : {pv_apres_mv:,.2f}€ ≤ 0€",
                f"**Moins-value reportable sur les 10 prochaines années : {abs(pv_apres_mv):,.2f}€**",
            ]
        else:
            pfu_ir_amount = pv_apres_mv * PFU_IR / 100
            pfu_ps_amount = pv_apres_mv * PFU_PS / 100
            pfu_total_amount = pv_apres_mv * PFU_TOTAL / 100

            # Option barème
            ir_bareme = pv_apres_mv * tmi / 100
            ps_bareme = pv_apres_mv * PFU_PS / 100
            total_bareme = ir_bareme + ps_bareme

            lines += [
                "## Imposition de la plus-value",
                "",
                "### Option A — PFU 30% (régime par défaut)",
                f"| IR 12.8% | PS 17.2% | **Total PFU** |",
                f"|----------|----------|--------------|",
                f"| {pfu_ir_amount:,.2f}€ | {pfu_ps_amount:,.2f}€ | **{pfu_total_amount:,.2f}€** |",
                "",
                f"### Option B — Barème IR progressif + PS (TMI {tmi}%)",
                f"| IR barème ({tmi}%) | PS 17.2% | **Total barème** |",
                f"|-------------------|----------|-----------------|",
                f"| {ir_bareme:,.2f}€ | {ps_bareme:,.2f}€ | **{total_bareme:,.2f}€** |",
                "",
            ]

            if total_bareme < pfu_total_amount:
                lines += [
                    f"✅ **Option barème plus favorable** : économie de {pfu_total_amount - total_bareme:,.2f}€",
                    "(Cochez la case 3CN de la 2042 C pour opter pour le barème)",
                ]
            else:
                lines += [
                    f"✅ **PFU 30% plus favorable** : économie de {total_bareme - pfu_total_amount:,.2f}€",
                ]

            if mv_anterieures > 0 and pv_brute > 0:
                lines += [
                    "",
                    f"### Moins-values imputées",
                    f"- MV antérieures utilisées : {min(mv_anterieures, pv_brute):,.2f}€",
                    f"- MV restantes reportables : {max(0, mv_anterieures - pv_brute):,.2f}€",
                ]
    else:
        lines += [
            "## ⚠️ Paramètres insuffisants",
            "Pour calculer la PV selon la méthode officielle, fournissez :",
            "- `valeur_portefeuille_avant_cession` : valeur totale du portefeuille AVANT la cession",
            "- `prix_acquisition_moyen_portefeuille` : PAMC (total des prix d'acquisition cumulés)",
            "",
            "**Méthode simplifiée** (si PAMC non disponible) :",
            f"PV estimée = Prix de cession − coût d'acquisition de ce lot",
        ]

    # ── Revenus annexes ───────────────────────────────────────────────────────
    revenus_annexes = rev_staking + rev_mining + rev_nft
    if revenus_annexes > 0:
        lines += [
            "",
            "## Revenus annexes crypto",
            "",
            "| Type | Montant | Régime | Imposition |",
            "|------|---------|--------|------------|",
        ]
        if rev_staking > 0:
            ir_staking = rev_staking * tmi / 100
            lines.append(
                f"| Staking / DeFi / Yield farming | {rev_staking:,.0f}€ | **BNC** (art. 92 CGI) | "
                f"Barème IR → ~{ir_staking:,.0f}€ + PS 17.2% |"
            )
        if rev_mining > 0:
            ir_mining = rev_mining * tmi / 100
            lines.append(
                f"| Minage (mining) | {rev_mining:,.0f}€ | **BIC** si répété / BNC si occasion. | "
                f"~{ir_mining:,.0f}€ + PS |"
            )
        if rev_nft > 0:
            ir_nft = rev_nft * tmi / 100
            lines.append(
                f"| NFT (créateur/vente) | {rev_nft:,.0f}€ | **BNC** | "
                f"~{ir_nft:,.0f}€ + PS 17.2% |"
            )
        lines += [
            "",
            "⚠️ Ces revenus s'ajoutent au RNI et sont imposés au barème progressif (+ prélèvements sociaux).",
            "À déclarer case **5HQ** (BNC non professionnel) ou **5KU** (BIC).",
        ]

    lines += [
        "",
        "## Obligations déclaratives",
        "- **Formulaire 2086** : obligatoire si cessions > 305€ (détail de chaque cession)",
        "- **Comptes étrangers** : déclarer sur formulaire 3916-bis si plateforme étrangère",
        "- **Airdrops** : imposables comme BNC à la réception (valeur du jour)",
        "- Conservation des justificatifs : historique des transactions, prix d'achat",
        "",
        "## Points de vigilance",
        "- L'échange crypto→crypto est **imposable** depuis 2019 (sauf si dans un même wallet)",
        "  Wait — depuis 2022 : crypto→crypto dans le même wallet = non imposable ; crypto→euros ou biens = imposable",
        "- Les échanges crypto/crypto sur des exchanges différents sont imposables",
        "- Stablecoins : une conversion USDC→EUR est un événement imposable",
        "",
        "---",
        "*Source : CGI art. 150 VH bis — BOFiP BIC-CHAMP-60-50 — LFR 2022*",
    ]
    return "\n".join(lines)


def tool_simuler_pacte_dutreil(args: Dict) -> str:
    """Simule le pacte Dutreil : exonération 75% pour transmission d'entreprise."""
    valeur = _valider_revenu(float(args["valeur_entreprise"]), "valeur_entreprise")
    lien = args.get("lien_parente", "enfant").lower()
    nb_donataires = max(1, int(args.get("nb_donataires", 1)))
    age_donateur = int(args.get("age_donateur", 60))
    donateur_dirigeant = bool(args.get("donateur_dirigeant", True))
    transmission_type = args.get("transmission_type", "donation").lower()

    # Barèmes droits de mutation en ligne directe et autres
    BAREME_DIRECTE = [
        {"min": 0,       "max": 8_072,    "taux": 0.05},
        {"min": 8_072,   "max": 12_109,   "taux": 0.10},
        {"min": 12_109,  "max": 15_932,   "taux": 0.15},
        {"min": 15_932,  "max": 552_324,  "taux": 0.20},
        {"min": 552_324, "max": 902_838,  "taux": 0.30},
        {"min": 902_838, "max": 1_805_677,"taux": 0.40},
        {"min": 1_805_677,"max": None,    "taux": 0.45},
    ]
    BAREME_FRERES = [
        {"min": 0,       "max": 24_430,   "taux": 0.35},
        {"min": 24_430,  "max": None,     "taux": 0.45},
    ]
    BAREME_NEVEUX = [
        {"min": 0,       "max": None,     "taux": 0.55},
    ]
    BAREME_TIERS = [
        {"min": 0,       "max": None,     "taux": 0.60},
    ]

    ABATTEMENTS = {
        "enfant": 100_000,       # par parent, par enfant (renouvelable 15 ans)
        "frere_soeur": 15_932,
        "neveu_niece": 7_967,
        "tiers": 1_594,
    }

    BAREMES = {
        "enfant": BAREME_DIRECTE,
        "frere_soeur": BAREME_FRERES,
        "neveu_niece": BAREME_NEVEUX,
        "tiers": BAREME_TIERS,
    }

    def calc_droits(base: float, bareme: list) -> float:
        droits = 0.0
        for tranche in bareme:
            if base <= tranche["min"]:
                break
            max_t = tranche["max"] if tranche["max"] else float("inf")
            imposable = min(base, max_t) - tranche["min"]
            droits += imposable * tranche["taux"]
        return droits

    # Part par donataire
    valeur_par_donataire = valeur / nb_donataires
    abattement = ABATTEMENTS.get(lien, 1_594)
    bareme = BAREMES.get(lien, BAREME_TIERS)

    # ── Sans pacte Dutreil ───────────────────────────────────────────────────
    base_sans_dutreil = max(0, valeur_par_donataire - abattement)
    droits_sans = calc_droits(base_sans_dutreil, bareme)
    total_sans = droits_sans * nb_donataires

    # ── Avec pacte Dutreil (exonération 75%) ─────────────────────────────────
    valeur_apres_dutreil = valeur_par_donataire * 0.25  # 25% restant
    base_avec_dutreil = max(0, valeur_apres_dutreil - abattement)
    droits_avec = calc_droits(base_avec_dutreil, bareme)
    total_avec = droits_avec * nb_donataires

    economie = total_sans - total_avec
    taux_reduction = (economie / total_sans * 100) if total_sans > 0 else 0

    lines = [
        "# Pacte Dutreil — Transmission d'Entreprise",
        f"*(Art. 787 B CGI — {'Donation' if transmission_type == 'donation' else 'Succession'})*",
        "",
        "## Paramètres",
        f"- Valeur de l'entreprise : {valeur:,.0f}€",
        f"- Nombre de {'donataires' if transmission_type == 'donation' else 'héritiers'} : {nb_donataires}",
        f"- Lien de parenté : {lien.replace('_', ' ')}",
        f"- Abattement légal : {abattement:,}€ par bénéficiaire",
        "",
        "## Comparatif droits avec / sans pacte Dutreil",
        "",
        f"| | **Sans Dutreil** | **Avec Dutreil** |",
        f"|--|--|--|",
        f"| Valeur transmise (par bénéficiaire) | {valeur_par_donataire:,.0f}€ | {valeur_par_donataire:,.0f}€ |",
        f"| Exonération Dutreil (75%) | — | -{valeur_par_donataire * 0.75:,.0f}€ |",
        f"| Base après exonération | {valeur_par_donataire:,.0f}€ | {valeur_apres_dutreil:,.0f}€ |",
        f"| Abattement légal ({abattement:,}€) | -{min(abattement, valeur_par_donataire):,.0f}€ | -{min(abattement, valeur_apres_dutreil):,.0f}€ |",
        f"| Base taxable | {base_sans_dutreil:,.0f}€ | {base_avec_dutreil:,.0f}€ |",
        f"| Droits par bénéficiaire | {droits_sans:,.0f}€ | {droits_avec:,.0f}€ |",
        f"| **Droits totaux ({nb_donataires} bénéficiaire(s))** | **{total_sans:,.0f}€** | **{total_avec:,.0f}€** |",
        "",
        f"### ✅ Économie grâce au pacte Dutreil : **{economie:,.0f}€** ({taux_reduction:.0f}% de réduction)",
        "",
        "## Conditions du pacte Dutreil",
        "",
        "### 1. Engagement collectif de conservation (ECC)",
        "- Durée : **2 ans minimum** avant la transmission",
        "- Portant sur : ≥ 17% des droits financiers et 34% des droits de vote (sociétés cotées)",
        "  OU ≥ 34% des droits financiers et de vote (sociétés non cotées)",
        "- Signé entre actionnaires/associés (y compris le futur donataire)",
        "",
        "### 2. Engagement individuel de conservation (EIC)",
        "- Le donataire/héritier s'engage à conserver les titres pendant **4 ans supplémentaires**",
        "- Soit une durée totale minimale : 6 ans",
        "",
        "### 3. Obligation de direction",
        "- L'un des signataires (ou le donataire/héritier) doit exercer une **fonction de direction**",
        "  pendant toute la durée de l'ECC + 3 ans après la transmission",
    ]

    if not donateur_dirigeant:
        lines += [
            "",
            "⚠️ **Attention** : le donateur n'est pas déclaré comme dirigeant.",
            "Le donataire ou un autre signataire de l'ECC devra assurer la direction.",
        ]

    lines += [
        "",
        "## Avantages supplémentaires",
        "- Paiement différé et fractionné des droits restants (sur 5 ans, prorogeable 10 ans)",
        "- Cumulable avec l'abattement légal de droit commun",
        "- Le pacte peut être conclu jusqu'à 6 mois après le décès (transmission par succession)",
        "",
        "## Risques de remise en cause",
        "- Non-respect de l'engagement de conservation (cession prématurée)",
        "- Cessation de l'activité opérationnelle",
        "- Dissolution de la société",
        "",
        "---",
        "*Source : CGI art. 787 B — BOFiP ENR-DMTG-10-20-40*",
        "*Consultez un notaire ou avocat fiscaliste pour la rédaction du pacte.*",
    ]
    return "\n".join(lines)


def tool_simuler_sci(args: Dict) -> str:
    """Compare les régimes IR et IS pour une SCI."""
    valeur_bien = _valider_revenu(float(args["valeur_bien"]), "valeur_bien")
    loyers = float(args["loyers_annuels"])
    charges = float(args["charges_annuelles"])
    interets = float(args.get("interet_emprunt", 0))
    tmi = float(args.get("tmi", 30))
    nb_parts_total = int(args.get("nb_parts", 100))
    parts_contrib = int(args.get("parts_contribuable", 100))
    horizon = int(args.get("horizon_revente_ans", 20))

    quote_part = parts_contrib / nb_parts_total if nb_parts_total > 0 else 1.0

    # ── SCI à l'IR ────────────────────────────────────────────────────────────
    # Revenus fonciers = loyers - charges - intérêts (régime réel)
    resultat_foncier = loyers - charges - interets
    # Quote-part de l'associé
    qp_loyers = loyers * quote_part
    qp_charges_ir = (charges + interets) * quote_part
    qp_resultat_ir = qp_loyers - qp_charges_ir

    if qp_resultat_ir < 0:
        # Déficit foncier
        deficit_imputable_rg = min(abs(qp_resultat_ir), 10_700)
        deficit_report = max(0, abs(qp_resultat_ir) - 10_700)
        ir_sur_loyers = 0.0
        ps_sur_loyers = 0.0
        economie_deficit = deficit_imputable_rg * tmi / 100
    else:
        deficit_imputable_rg = 0.0
        deficit_report = 0.0
        ir_sur_loyers = qp_resultat_ir * tmi / 100
        ps_sur_loyers = qp_resultat_ir * 0.172
        economie_deficit = 0.0

    net_apres_impot_ir = qp_loyers - qp_charges_ir - ir_sur_loyers - ps_sur_loyers + economie_deficit
    rendement_net_ir = net_apres_impot_ir / (valeur_bien * quote_part) * 100 if valeur_bien > 0 else 0

    # ── SCI à l'IS ────────────────────────────────────────────────────────────
    # Amortissement linéaire du bien sur 30 ans (taux 3.33%/an)
    amort_annuel = valeur_bien * 0.0333
    # Résultat IS = loyers - charges - intérêts - amortissement
    resultat_is = loyers - charges - interets - amort_annuel

    if resultat_is <= 0:
        is_annuel = 0.0
    elif resultat_is <= 42_500:
        is_annuel = resultat_is * 0.15
    else:
        is_annuel = 42_500 * 0.15 + (resultat_is - 42_500) * 0.25

    resultat_apres_is = resultat_is - is_annuel
    # Si distribution de tout le résultat en dividendes :
    qp_dividendes = resultat_apres_is * quote_part
    pfu_dividendes = qp_dividendes * 0.30
    net_dividendes = qp_dividendes - pfu_dividendes
    net_apres_impot_is = (loyers - charges - interets) * quote_part * (1 - 0.30) - amort_annuel * quote_part * 0.30
    # Simplifié : rendement locatif net après IS + PFU sur dividendes
    cash_flow_is = (loyers - charges - interets) * quote_part - is_annuel * quote_part - pfu_dividendes
    rendement_net_is = cash_flow_is / (valeur_bien * quote_part) * 100 if valeur_bien > 0 else 0

    # ── Fiscalité à la sortie (revente dans N ans) ────────────────────────────
    # SCI IR : plus-value immobilière des particuliers avec abattements pour durée
    if horizon >= 30:
        abatt_ir_pct = 100.0
        pv_imposable_ir_pct = 0.0
    elif horizon >= 22:
        abatt_ir_pct = 96.0  # exonération IR à 22 ans
        pv_imposable_ir_pct = 0.0
    elif horizon >= 6:
        abatt_ir_pct = (horizon - 5) * 6.0
        pv_imposable_ir_pct = max(0, 100 - abatt_ir_pct)
    else:
        abatt_ir_pct = 0.0
        pv_imposable_ir_pct = 100.0

    # PS : exonération totale à 30 ans, abattement 1.65%/an de 6 à 21 ans, 9%/an à partir de 22 ans
    if horizon >= 30:
        abatt_ps_pct = 100.0
    elif horizon >= 22:
        abatt_ps_pct = (22 - 5) * 1.65 + (horizon - 21) * 9.0
        abatt_ps_pct = min(abatt_ps_pct, 100)
    elif horizon >= 6:
        abatt_ps_pct = (horizon - 5) * 1.65
    else:
        abatt_ps_pct = 0.0

    plus_value_estimee = valeur_bien * 0.02 * horizon  # hypothèse +2%/an

    pv_taxable_ir = plus_value_estimee * (pv_imposable_ir_pct / 100)
    pv_taxable_ps = plus_value_estimee * (1 - abatt_ps_pct / 100)
    impot_sortie_ir = pv_taxable_ir * 0.19 + pv_taxable_ps * 0.172

    # SCI IS : la base de plus-value est valeur de cession - valeur nette comptable (après amortissements)
    vnc = max(0, valeur_bien - amort_annuel * horizon)  # valeur nette comptable
    pv_is = plus_value_estimee + (valeur_bien - vnc)  # PV = prix vente - VNC
    pv_is_imposable = max(0, pv_is)
    is_pv = (42_500 * 0.15 + max(0, pv_is_imposable - 42_500) * 0.25) if pv_is_imposable > 0 else 0
    net_apres_is_pv = pv_is_imposable - is_pv
    pfu_sur_net = net_apres_is_pv * 0.30  # distribution en dividendes
    impot_sortie_is = is_pv + pfu_sur_net

    lines = [
        "# Comparatif SCI à l'IR vs SCI à l'IS",
        "",
        "## Paramètres",
        f"- Valeur du bien : {valeur_bien:,.0f}€",
        f"- Loyers annuels bruts : {loyers:,.0f}€",
        f"- Charges annuelles : {charges:,.0f}€",
        f"- Intérêts d'emprunt : {interets:,.0f}€",
        f"- TMI de l'associé : {tmi}%",
        f"- Quote-part : {quote_part*100:.0f}% ({parts_contrib}/{nb_parts_total} parts)",
        f"- Horizon de détention : {horizon} ans",
        "",
        "## 1. Revenus locatifs annuels",
        "",
        f"| | **SCI à l'IR** | **SCI à l'IS** |",
        f"|--|--|--|",
        f"| Loyers bruts (quote-part) | {qp_loyers:,.0f}€ | {qp_loyers:,.0f}€ |",
        f"| Charges déductibles | -{qp_charges_ir:,.0f}€ | -{(charges + interets) * quote_part:,.0f}€ |",
        f"| Amortissement du bien (3.33%/an) | — | -{amort_annuel * quote_part:,.0f}€ |",
        f"| Résultat avant impôt | {qp_resultat_ir:,.0f}€ | {resultat_is * quote_part:,.0f}€ |",
        f"| IS (15%/25%) | — | -{is_annuel * quote_part:,.0f}€ |",
        f"| IR + PS 17.2% (TMI {tmi}%) | -{ir_sur_loyers + ps_sur_loyers:,.0f}€ | — |",
        f"| PFU 30% si distribution dividendes | — | -{pfu_dividendes:,.0f}€ |",
        f"| **Cash-flow net annuel** | **{net_apres_impot_ir:,.0f}€** | **{cash_flow_is:,.0f}€** |",
        f"| **Rendement net** | **{rendement_net_ir:.2f}%** | **{rendement_net_is:.2f}%** |",
        "",
    ]

    if qp_resultat_ir < 0:
        lines += [
            "### ℹ️ Déficit foncier (SCI IR)",
            f"- Déficit total quote-part : {abs(qp_resultat_ir):,.0f}€",
            f"- Imputable sur revenu global : {deficit_imputable_rg:,.0f}€ → économie IR : ~{economie_deficit:,.0f}€",
            f"- Report sur revenus fonciers futurs : {deficit_report:,.0f}€",
            "",
        ]

    lines += [
        "## 2. Fiscalité à la sortie (revente dans {horizon} ans)".format(horizon=horizon),
        f"*(Hypothèse : bien valorisé +2%/an, plus-value estimée {plus_value_estimee:,.0f}€)*",
        "",
        f"| | **SCI à l'IR** | **SCI à l'IS** |",
        f"|--|--|--|",
        f"| Base de calcul PV | PV nette abattements durée | Valeur vente - VNC ({vnc:,.0f}€) |",
        f"| Plus-value imposable | {pv_taxable_ir:,.0f}€ IR + {pv_taxable_ps:,.0f}€ PS | {pv_is_imposable:,.0f}€ |",
        f"| Abattement durée détention | IR : {100-pv_imposable_ir_pct:.0f}% / PS : {abatt_ps_pct:.0f}% | Aucun |",
        f"| Impôt sur la PV | {impot_sortie_ir:,.0f}€ | {impot_sortie_is:,.0f}€ (IS + PFU div.) |",
        "",
        "## 3. Analyse et recommandation",
        "",
        "### ✅ SCI à l'IR recommandée si :",
        "- TMI ≤ 30% (fiscalité des revenus fonciers supportable)",
        "- Vous avez des charges/travaux importants générant un déficit foncier",
        "- Objectif de détention > 22 ans (exonération IR totale à 22 ans, PS à 30 ans)",
        "- Objectif de transmission facilitée (cessions de parts sans frais notariaux)",
        "",
        "### ✅ SCI à l'IS recommandée si :",
        "- TMI ≥ 41% (IS 15%/25% < TMI + PS)",
        "- Nombreux travaux permettant de gros amortissements",
        "- Horizon de détention ≤ 15 ans (avant que l'effet des amortissements se retourne)",
        "- Réinvestissement des bénéfices dans la société (pas de distribution)",
        "",
        "### ⚠️ Piège de la SCI IS à la revente",
        f"- Amortissements cumulés sur {horizon} ans : {amort_annuel * horizon:,.0f}€",
        f"- VNC du bien : {vnc:,.0f}€ (au lieu de {valeur_bien:,.0f}€ à l'achat)",
        "- La PV imposable est calculée sur le prix de vente MOINS la VNC → base très élevée",
        "- Double imposition : IS sur la PV + PFU 30% sur la distribution",
        "",
        "---",
        "*Source : CGI art. 8, 219, 238 bis K — BOFiP BIC-BASE-20*",
        "*Simulation indicative — Consultez un expert-comptable avant toute décision.*",
    ]
    return "\n".join(lines)


def tool_simuler_depart_retraite(args: Dict) -> str:
    """Simule le départ à la retraite : pension, décote/surcote, cumul emploi-retraite."""
    salaire_brut = _valider_revenu(float(args["salaire_annuel_brut"]), "salaire_annuel_brut")
    trimestres = int(args["trimestres_valides"])
    age_actuel = int(args["age_actuel"])
    regime = args.get("regime", "prive")
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    cumul = bool(args.get("cumul_emploi_retraite", False))
    salaire_cumul = float(args.get("salaire_cumul", 0))

    # Paramètres légaux 2024-2025 (réforme 2023)
    AGE_LEGAL = 64          # âge légal (réforme 2023, passage de 62 à 64 ans)
    AGE_TAUX_PLEIN_AUTO = 67  # taux plein automatique sans décote
    TRIMESTRES_TAUX_PLEIN = 172  # génération née à partir de 1965
    TAUX_DECOTE = 1.25      # % par trimestre manquant (max 20 trimestres = 25%)
    TAUX_SURCOTE = 1.25     # % par trimestre supplémentaire après taux plein
    SAM_COEFF = 0.50        # 50% du salaire annuel moyen (25 meilleures années)

    # Salaire annuel moyen estimé (net imposable ≈ brut × 0.78)
    sam = salaire_brut * 0.78 * 0.95  # 25 meilleures années ≈ légèrement < dernier salaire

    # Pension de base (régime général)
    def calc_pension_base(trimestres_au_depart: int, age_depart: int) -> Dict:
        manquants = max(0, TRIMESTRES_TAUX_PLEIN - trimestres_au_depart)
        # Décote : 1.25%/trimestre manquant, limitée à 20 trimestres
        decote_trimestres = min(manquants, 20) if age_depart < AGE_TAUX_PLEIN_AUTO else 0
        decote_pct = decote_trimestres * TAUX_DECOTE / 100

        # Surcote : 1.25%/trimestre au-delà du taux plein après l'âge légal
        surcote_trimestres = max(0, trimestres_au_depart - TRIMESTRES_TAUX_PLEIN) if trimestres_au_depart >= TRIMESTRES_TAUX_PLEIN else 0
        surcote_pct = surcote_trimestres * TAUX_SURCOTE / 100

        taux_effectif = SAM_COEFF * (1 - decote_pct) * (1 + surcote_pct)
        taux_effectif = min(taux_effectif, SAM_COEFF)  # plafond à 50%

        prorata = min(trimestres_au_depart / TRIMESTRES_TAUX_PLEIN, 1.0)
        pension_brute = sam * taux_effectif * prorata
        return {
            "pension_brute": pension_brute,
            "taux_effectif": taux_effectif * 100,
            "decote_pct": decote_pct * 100,
            "surcote_pct": surcote_pct * 100,
            "decote_trim": decote_trimestres,
            "surcote_trim": surcote_trimestres,
        }

    # Complément AGIRC-ARRCO estimé (≈ 60% de la pension de base pour un cadre, 40% non-cadre)
    def calc_agirc(pension_base: float) -> float:
        return pension_base * 0.50  # estimation moyenne

    # Fiscalité de la pension
    def calc_ir_pension(pension_annuelle: float, parts: float) -> float:
        abatt = max(422, min(4_321, pension_annuelle * 0.10))
        rni = max(0, pension_annuelle - abatt)
        return calculer_ir(rni, parts)["impot_net"]

    nb_parts = calculer_parts(situation, nb_enfants)
    trimestres_annee = 4

    lines = [
        "# Simulation Départ à la Retraite",
        f"*(Réforme retraites 2023 — âge légal : {AGE_LEGAL} ans)*",
        "",
        "## Paramètres",
        f"- Salaire annuel brut : {salaire_brut:,.0f}€",
        f"- Trimestres validés : {trimestres} / {TRIMESTRES_TAUX_PLEIN} requis pour taux plein",
        f"- Âge actuel : {age_actuel} ans",
        f"- Régime : {regime}",
        "",
        "## Comparatif des scénarios de départ",
        "",
        f"| Âge de départ | Trimestres | Décote | Pension base/mois | AGIRC-ARRCO/mois | **Total brut/mois** | IR annuel | **Net/mois** |",
        f"|---------------|-----------|--------|-------------------|-----------------|---------------------|-----------|--------------|",
    ]

    scenarios = [62, 64, 67]
    for age_dep in scenarios:
        if age_dep < AGE_LEGAL:
            # Avant l'âge légal : carrière longue ou inaccessible
            trim_dep = trimestres + (age_dep - age_actuel) * trimestres_annee
            note = " ⚠️ (carrière longue requis)"
        else:
            trim_dep = trimestres + (age_dep - age_actuel) * trimestres_annee
            note = ""

        r = calc_pension_base(trim_dep, age_dep)
        agirc = calc_agirc(r["pension_brute"])
        total_brut_annuel = r["pension_brute"] + agirc
        total_brut_mois = total_brut_annuel / 12
        ir = calc_ir_pension(total_brut_annuel, nb_parts)
        net_mois = (total_brut_annuel - ir) / 12

        decote_str = f"-{r['decote_pct']:.1f}%" if r['decote_pct'] > 0 else (f"+{r['surcote_pct']:.1f}%" if r['surcote_pct'] > 0 else "0%")
        lines.append(
            f"| {age_dep} ans{note} | {trim_dep} | {decote_str} | "
            f"{r['pension_brute']/12:,.0f}€ | {agirc/12:,.0f}€ | **{total_brut_mois:,.0f}€** | "
            f"{ir:,.0f}€/an | **{net_mois:,.0f}€** |"
        )

    # Détail pour l'âge légal
    trim_64 = trimestres + (AGE_LEGAL - age_actuel) * trimestres_annee
    r64 = calc_pension_base(trim_64, AGE_LEGAL)

    lines += [
        "",
        f"## Détail — Départ à {AGE_LEGAL} ans (âge légal)",
        "",
        f"- Trimestres à {AGE_LEGAL} ans : {trim_64}",
    ]

    if r64["decote_pct"] > 0:
        lines += [
            f"- **Décote** : {r64['decote_trim']} trimestres manquants × 1.25% = **-{r64['decote_pct']:.1f}%**",
            f"  → Pour éviter la décote : attendre {AGE_TAUX_PLEIN_AUTO} ans (taux plein automatique)",
        ]
    elif r64["surcote_pct"] > 0:
        lines += [
            f"- **Surcote** : {r64['surcote_trim']} trimestres supplémentaires × 1.25% = **+{r64['surcote_pct']:.1f}%**",
        ]
    else:
        lines.append("- Taux plein atteint ✅")

    lines += [
        "",
        "## Abattement fiscal sur les pensions",
        "- Abattement 10% sur les pensions (min 422€ / max 4 321€ par pensionné)",
        "- Prélèvements sociaux : CSG 8.3% + CRDS 0.5% + Casa 0.3% = **9.1%** (si pension > 1 362€/mois)",
        "- Réduction si pension modeste (CSG 3.8% ou 6.6% selon le RFR)",
    ]

    if regime == "fonctionnaire":
        lines += [
            "",
            "## Spécificités fonctionnaires",
            "- Pension calculée sur les 6 derniers mois de traitement indiciaire (hors primes)",
            "- Taux : 75% maximum après 167 trimestres (né avant 1958) à 172 trimestres (né après 1965)",
            "- Décote : 1.25%/trimestre manquant (même règle que le régime général)",
            "- RAFP (retraite additionnelle) sur les primes et indemnités",
        ]

    if regime == "independant":
        lines += [
            "",
            "## Spécificités indépendants (SSI)",
            "- Retraite de base : calcul similaire au régime général",
            "- Retraite complémentaire : points RCI/RCO selon cotisations versées",
            "- PER individuel fortement recommandé pour compenser la pension souvent plus faible",
        ]

    if cumul and salaire_cumul > 0:
        lines += [
            "",
            "## Cumul emploi-retraite",
            "- **Cumul libéralisé** (depuis 2023) : retraite liquidée + nouveau contrat = acquisition de nouveaux droits",
            f"- Revenus d'activité envisagés : {salaire_cumul:,.0f}€/an",
            "- Les cotisations versées en cumul ouvrent désormais de nouveaux droits à retraite",
            "- Plafond pour cumul intégral : revenus d'activité < 1 SMIC (ou pension liquidée au taux plein)",
        ]
        # Estimation fiscale cumul
        trim_dep = trimestres + (AGE_LEGAL - age_actuel) * trimestres_annee
        r = calc_pension_base(trim_dep, AGE_LEGAL)
        agirc = calc_agirc(r["pension_brute"])
        total_revenus = r["pension_brute"] + agirc + salaire_cumul * 0.9  # abatt. 10% salaire
        ir_cumul = calc_ir_pension(total_revenus, nb_parts)
        lines += [
            f"- IR estimé en cumul : {ir_cumul:,.0f}€/an (pension + salaire)",
        ]

    lines += [
        "",
        "## Points de vigilance",
        f"- Trimestres requis (génération ≥ 1965) : **{TRIMESTRES_TAUX_PLEIN}** (43 ans de cotisation)",
        "- Les trimestres de chômage, maladie, maternité, invalidité comptent",
        "- Majoration : +10% de pension à partir du 3ème enfant",
        "- Réversion au conjoint : 54% de la pension du défunt (sous conditions de ressources)",
        "",
        "> ℹ️ Simulation indicative. Pour une estimation précise, consultez votre relevé de carrière",
        "> sur **info-retraite.fr** et les organismes de retraite complémentaire (AGIRC-ARRCO).",
        "",
        "---",
        "*Source : CSS art. L351-1 — Décret n°2023-436 (réforme 2023) — Circulaire CNAV*",
    ]
    return "\n".join(lines)


def tool_guide_fiscalite_agricole(args: Dict) -> str:
    """Guide de la fiscalité agricole : forfait, RSA, réel normal, DEP, jeune agriculteur."""
    recettes = _valider_revenu(float(args["recettes_annuelles"]), "recettes_annuelles")
    regime_souhaite = args.get("regime", "auto")
    benefice = float(args.get("benefice_agricole", 0))
    dep = float(args.get("dep_souhaitee", 0))
    jeune_agri = bool(args.get("jeune_agriculteur", False))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))

    # Seuils régimes agricoles 2025
    SEUIL_FORFAIT_MAX = 85_800     # moyenne triennale des recettes
    SEUIL_RSA_MAX = 391_000        # réel simplifié si recettes ≤ 391 000€
    DEP_MAX_TAUX = 0.27            # DEP : 27% du bénéfice imposable
    DEP_MAX_ABSOLU = 41_620        # plafond absolu DEP
    DEP_PLANCHER = 1_000

    # Détermination du régime applicable
    if regime_souhaite == "auto":
        if recettes <= SEUIL_FORFAIT_MAX:
            regime_applicable = "forfait"
        elif recettes <= SEUIL_RSA_MAX:
            regime_applicable = "simplifie"
        else:
            regime_applicable = "reel_normal"
    else:
        regime_applicable = regime_souhaite

    nb_parts = calculer_parts(situation, nb_enfants)

    lines = [
        "# Fiscalité Agricole 2025",
        "",
        "## Régimes d'imposition agricole",
        "",
        f"| Régime | Condition (recettes moyennes sur 3 ans) | Obligations |",
        f"|--------|----------------------------------------|-------------|",
        f"| **Forfait collectif** | ≤ {SEUIL_FORFAIT_MAX:,}€ | Minimal — bénéfice forfaitaire fixé par barème |",
        f"| **Réel simplifié** (RSA) | {SEUIL_FORFAIT_MAX:,}€ → {SEUIL_RSA_MAX:,}€ | Comptabilité simplifiée |",
        f"| **Réel normal** | > {SEUIL_RSA_MAX:,}€ | Comptabilité complète |",
        "",
        f"**Vos recettes : {recettes:,.0f}€ → Régime applicable : {regime_applicable.replace('_', ' ').upper()}**",
        "",
    ]

    if regime_applicable == "forfait":
        lines += [
            "## Régime du Forfait Collectif",
            "",
            "- Le bénéfice imposable est **fixé chaque année par arrêté préfectoral** par nature de culture/élevage",
            "- Vous n'avez pas à tenir de comptabilité détaillée",
            "- Le bénéfice forfaitaire est calculé par hectare ou par tête de bétail",
            "",
            "### Avantages",
            "- Simplicité maximale",
            "- Possibilité d'opter pour le régime réel si plus favorable (option irrévocable 2 ans)",
            "",
            "### Inconvénients",
            "- Impossible de déduire les charges réelles (même si elles sont élevées)",
            "- Pas d'accès à la DEP ou aux amortissements",
            "",
            "### Cotisations MSA",
            "- Calculées sur le bénéfice forfaitaire",
            "- Taux : environ 33% du bénéfice agricole",
        ]

    elif regime_applicable in ["simplifie", "reel_normal"]:
        # Calcul DEP
        dep_max = min(benefice * DEP_MAX_TAUX, DEP_MAX_ABSOLU) if benefice > 0 else 0
        dep_retenu = min(dep, dep_max) if dep > 0 else 0
        benefice_apres_dep = max(0, benefice - dep_retenu)

        label = "Réel Simplifié (RSA)" if regime_applicable == "simplifie" else "Réel Normal"
        lines += [
            f"## Régime {label}",
            "",
            "### Déductibilité des charges",
            "Sont déductibles du bénéfice agricole :",
            "- Charges d'exploitation : semences, engrais, produits phytosanitaires, alimentation animale",
            "- Cotisations MSA et assurances",
            "- Amortissements des bâtiments (4-5%/an), matériel (10-25%/an), vignes (5%/an)",
            "- Intérêts d'emprunt",
            "- Fermages",
            "- Carburant (100% si usage agricole)",
            "",
        ]

        if benefice > 0:
            ir_sans_dep = calculer_ir(benefice, nb_parts)["impot_net"]
            ir_avec_dep = calculer_ir(benefice_apres_dep, nb_parts)["impot_net"] if dep_retenu > 0 else ir_sans_dep
            economie_dep = ir_sans_dep - ir_avec_dep

            lines += [
                "### DEP — Déduction pour Épargne de Précaution",
                f"*(Art. 73 CGI — remplace la DPA depuis 2019)*",
                "",
                f"- Bénéfice imposable : {benefice:,.0f}€",
                f"- DEP maximum déductible : {dep_max:,.0f}€ (27% du bénéfice, max {DEP_MAX_ABSOLU:,}€)",
            ]
            if dep_retenu > 0:
                lines += [
                    f"- DEP retenue : {dep_retenu:,.0f}€",
                    f"- Bénéfice après DEP : {benefice_apres_dep:,.0f}€",
                    f"- **Économie d'IR estimée : {economie_dep:,.0f}€**",
                    "",
                    "⚠️ Les sommes déposées en DEP doivent être utilisées dans les 10 ans",
                    "pour des dépenses professionnelles (aléas économiques/climatiques, investissements).",
                ]
            else:
                lines += [
                    f"- DEP disponible à utiliser : {dep_max:,.0f}€",
                    f"- Économie potentielle si DEP max : {ir_sans_dep - calculer_ir(max(0, benefice - dep_max), nb_parts)['impot_net']:,.0f}€",
                ]
            lines.append("")

        lines += [
            "### Étalement des revenus exceptionnels",
            "- Revenus exceptionnels (indemnités PAC, plus-values…) peuvent être étalés sur 7 ans",
            "- Système du quotient : divise le revenu exceptionnel par 7, calcule l'IR sur 7× ce quotient",
        ]

        if regime_applicable == "simplifie":
            lines += [
                "",
                "### Spécificités RSA",
                "- Comptabilité de trésorerie (recettes/dépenses encaissées)",
                "- Déclaration sur formulaire 2342",
                "- Bilan simplifié (tableau des immobilisations et amortissements)",
            ]
        else:
            lines += [
                "",
                "### Spécificités Réel Normal",
                "- Comptabilité d'engagement (créances/dettes)",
                "- Expert-comptable fortement recommandé",
                "- Déclaration sur formulaire 2143 (liasse fiscale agricole)",
            ]

    if jeune_agri:
        lines += [
            "",
            "## Jeune Agriculteur — Exonérations spécifiques",
            "",
            "### Abattement JA (Art. 73 B CGI)",
            "- **75% du bénéfice** pendant les 5 premières années d'installation",
            "  (si installation aidée avec DJA — Dotation Jeune Agriculteur)",
            "- Limité à 100 000€ de bénéfice réduit sur 5 ans",
            "",
            "### Exonération de taxe foncière",
            "- Exonération partielle ou totale pendant 5 ans selon les communes",
            "",
            "### DJA (Dotation Jeune Agriculteur)",
            "- Aide à l'installation non imposable (exonérée d'IR et de cotisations MSA)",
            "- Montant variable : 8 000€ à 40 000€ selon la zone et le projet",
            "",
            "### Crédit d'impôt pour remplacement pour congés",
            "- 50% des dépenses de remplacement (congés, maladie) — plafonné à 14 jours/an",
        ]

    lines += [
        "",
        "## TVA Agricole",
        "- **Régime du remboursement forfaitaire** (si CA < 46 000€) : TVA récupérée via un taux forfaitaire",
        "  sur les ventes (4.65% céréales/betteraves, 3.05% bovins/ovins, 3.95% autres)",
        "- **Régime réel simplifié** : TVA collectée - TVA déductible (sur option ou obligation)",
        "- TVA sur aliments pour animaux, semences certifiées : **taux 2.1%**",
        "- TVA sur produits agricoles non transformés : **taux 10%**",
        "",
        "## Cotisations MSA",
        "- Taux global : environ **33 à 45%** du revenu professionnel selon la situation",
        "- Assiette minimale : 800 SMIC horaire",
        "- Cotisations retraite, maladie, accidents du travail, allocations familiales",
        "- Possibilité de cotiser sur une assiette optionnelle (meilleure protection)",
        "",
        "---",
        "*Source : CGI art. 63 à 78 — Art. 73 (DEP) — BOFiP BA-BASE-30*",
        "*Consultez un conseiller en gestion d'entreprise agricole (CGA) pour votre situation.*",
    ]
    return "\n".join(lines)


def tool_guide_fiscalite_outremer(args: Dict) -> str:
    """Guide des dispositifs fiscaux spécifiques aux DOM-TOM."""
    territoire = args.get("territoire", "reunion")
    situation_type = args.get("situation", "resident")
    rni = float(args.get("revenu_net_imposable", 0))
    type_invest = args.get("type_investissement", "aucun")
    montant_invest = float(args.get("montant_investissement", 0))
    situation_famille = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))

    # Abattements DOM (Art. 197 CGI)
    ABATTEMENTS_DOM = {
        "guadeloupe":   {"taux": 0.30, "max": 5_100, "label": "Guadeloupe"},
        "martinique":   {"taux": 0.30, "max": 5_100, "label": "Martinique"},
        "reunion":      {"taux": 0.30, "max": 5_100, "label": "La Réunion"},
        "guyane":       {"taux": 0.40, "max": 6_700, "label": "Guyane"},
        "mayotte":      {"taux": 0.40, "max": 6_700, "label": "Mayotte"},
        "saint_martin": {"taux": 0.30, "max": 5_100, "label": "Saint-Martin"},
        "saint_barthelemy": {"taux": None, "max": None, "label": "Saint-Barthélemy"},
        "polynesie":    {"taux": None, "max": None, "label": "Polynésie française"},
        "nouvelle_caledonie": {"taux": None, "max": None, "label": "Nouvelle-Calédonie"},
        "saint_pierre_miquelon": {"taux": 0.30, "max": 5_100, "label": "Saint-Pierre-et-Miquelon"},
        "wallis_futuna": {"taux": None, "max": None, "label": "Wallis-et-Futuna"},
    }

    info = ABATTEMENTS_DOM.get(territoire, ABATTEMENTS_DOM["reunion"])
    label = info["label"]
    taux_abatt = info["taux"]
    max_abatt = info["max"]

    nb_parts = calculer_parts(situation_famille, nb_enfants)

    lines = [
        f"# Fiscalité Outre-mer — {label}",
        "",
    ]

    # Collectivités à fiscalité propre (non soumises à l'IR métropolitain)
    fiscalite_propre = territoire in ["polynesie", "nouvelle_caledonie", "saint_barthelemy", "wallis_futuna"]

    if fiscalite_propre:
        regimes_propres = {
            "polynesie": "Impôt sur les transactions (IT) — pas d'IR au sens français",
            "nouvelle_caledonie": "Impôt sur le revenu calédonien (IRCAL) — fiscalité propre",
            "saint_barthelemy": "Fiscalité locale propre — pas d'IR français ni de cotisations sociales françaises",
            "wallis_futuna": "Pas d'impôt direct — régime fiscal très spécifique",
        }
        lines += [
            f"## ⚠️ Collectivité à fiscalité propre",
            f"**{label}** n'est pas soumis au Code Général des Impôts français.",
            f"- Régime : {regimes_propres.get(territoire, 'Fiscalité locale spécifique')}",
            "",
            "Les résidents de ces territoires ne sont PAS soumis à l'IR français.",
            "En cas d'installation depuis la métropole, consultez les conventions fiscales locales.",
        ]
        return "\n".join(lines)

    # DOM / Collectivités soumises à l'IR français avec abattements
    if situation_type == "resident" and taux_abatt:
        abatt_montant = min(rni * taux_abatt, max_abatt) if rni > 0 else 0
        rni_apres_abatt = max(0, rni - abatt_montant) if rni > 0 else 0

        lines += [
            "## Abattement spécifique sur l'IR (Art. 197 CGI)",
            "",
            f"Les résidents de **{label}** bénéficient d'un abattement sur l'IR calculé :",
            f"- Taux : **{taux_abatt*100:.0f}%** de l'impôt dû",
            f"- Plafond : **{max_abatt:,}€**",
            "",
        ]

        if rni > 0:
            ir_sans_abatt = calculer_ir(rni, nb_parts)["impot_net"]
            reduction = min(ir_sans_abatt * taux_abatt, max_abatt)
            ir_avec_abatt = max(0, ir_sans_abatt - reduction)
            lines += [
                f"### Calcul pour {rni:,.0f}€ de RNI",
                f"| | Métropole | {label} |",
                f"|--|-----------|---------|",
                f"| IR calculé (barème) | {ir_sans_abatt:,.0f}€ | {ir_sans_abatt:,.0f}€ |",
                f"| Abattement DOM ({taux_abatt*100:.0f}%) | — | -{reduction:,.0f}€ |",
                f"| **IR final** | **{ir_sans_abatt:,.0f}€** | **{ir_avec_abatt:,.0f}€** |",
                f"| Économie | — | {ir_sans_abatt - ir_avec_abatt:,.0f}€ |",
                "",
            ]

        if territoire == "mayotte":
            lines += [
                "### Spécificités Mayotte",
                "- Abattement renforcé 40% (plafonné à 6 700€)",
                "- Déductions spécifiques pour frais de scolarité et de transport",
                "- TVA : taux réduit sur de nombreux produits",
                "",
            ]

    # Prélèvements sociaux DOM
    lines += [
        "## Prélèvements sociaux",
        "- **DOM (Guadeloupe, Martinique, Réunion, Guyane, Mayotte)** : prélèvements sociaux identiques à la métropole",
        "- CRDS : 0.5% — CSG : selon les revenus — Prélèvement de solidarité : 7.5%",
        "",
    ]

    # Dispositifs d'investissement outre-mer
    if situation_type == "investisseur_metropole" or type_invest != "aucun":
        lines += [
            "## Dispositifs de défiscalisation outre-mer (investisseurs métropole)",
            "",
        ]

        if type_invest in ["girardin_industriel", "aucun"]:
            lines += [
                "### Girardin Industriel (Art. 199 undecies B CGI)",
                "- Réduction d'impôt > 100% du montant investi (ex. 110% à 120% la même année)",
                "- Investissement dans des équipements productifs en outre-mer via une société de portage",
                "- **One shot** : la réduction est accordée l'année de l'investissement",
                "- Risque : si l'exploitation cesse avant 5 ans → reprise de l'avantage fiscal",
            ]
            if montant_invest > 0 and type_invest == "girardin_industriel":
                reduction_estim = montant_invest * 1.10  # estimation 110%
                lines += [
                    f"- Investissement envisagé : {montant_invest:,.0f}€",
                    f"- Réduction IR estimée (×110%) : **{reduction_estim:,.0f}€**",
                ]
            lines.append("")

        if type_invest in ["pinel_om", "aucun"]:
            lines += [
                "### Pinel Outre-mer (Art. 199 novovicies CGI)",
                "- Taux de réduction supérieurs au Pinel métropole :",
                "  | Durée engagement | Taux réduction |",
                "  |-----------------|----------------|",
                "  | 6 ans | **23%** |",
                "  | 9 ans | **29%** |",
                "  | 12 ans | **32%** |",
                "- Plafond investissement : 300 000€/an (2 logements max)",
                "- Zones éligibles : toutes les DOM + certaines collectivités",
            ]
            if montant_invest > 0 and type_invest == "pinel_om":
                red_6 = montant_invest * 0.23
                red_9 = montant_invest * 0.29
                red_12 = montant_invest * 0.32
                lines += [
                    f"- Investissement : {montant_invest:,.0f}€",
                    f"  → 6 ans : {red_6:,.0f}€ de réduction ({red_6/6:,.0f}€/an)",
                    f"  → 9 ans : {red_9:,.0f}€ de réduction ({red_9/9:,.0f}€/an)",
                    f"  → 12 ans : {red_12:,.0f}€ de réduction ({red_12/12:,.0f}€/an)",
                ]
            lines.append("")

        lines += [
            "### Autres dispositifs",
            "- **Girardin social** : financement logement social — réduction 50% à 60%",
            "- **Girardin IS** : pour les sociétés qui investissent en outre-mer (art. 217 undecies)",
            "- **LODEOM** : exonérations de charges sociales patronales pour entreprises implantées en DOM",
        ]

    # Spécificités par territoire
    lines += ["", "## Points spécifiques par territoire", ""]
    specifiques = {
        "guadeloupe":  "TVA applicable (taux 8.5% réduit, 2.1% super-réduit). Octroi de mer sur importations.",
        "martinique":  "TVA applicable (taux 8.5%/2.1%). Octroi de mer. Zone franche urbaine Fort-de-France.",
        "reunion":     "TVA applicable (8.5%/2.1%). Octroi de mer. Nombreuses ZFU et zones d'aide à finalité régionale.",
        "guyane":      "Pas de TVA (régime de l'octroi de mer uniquement). Exonérations renforcées entreprises.",
        "mayotte":     "TVA applicable depuis 2014. Fiscalité en convergence progressive avec la métropole.",
        "saint_martin": "Collectivité d'outre-mer. Fiscalité propre partielle. Pas d'octroi de mer.",
    }
    if territoire in specifiques:
        lines.append(f"**{label}** : {specifiques[territoire]}")
    else:
        lines.append(f"**{label}** : Consultez la direction des impôts territoriale.")

    lines += [
        "",
        "---",
        "*Source : CGI art. 197 I 3, 199 undecies B, 199 novovicies — BOFiP IR-LIQ-20-20-40*",
        "*Les dispositifs Girardin sont complexes — consultez un conseiller fiscal spécialisé outre-mer.*",
    ]
    return "\n".join(lines)




# ═══════════════════════════════════════════════════════════════════════════
# GROUP 1 : Assurance-vie, Démembrement, Cession entreprise, Holding
# ═══════════════════════════════════════════════════════════════════════════

def tool_simuler_assurance_vie(args: Dict) -> str:
    """Simule la fiscalité de l'assurance-vie : rachats, transmission, rentes."""
    capital = _valider_revenu(float(args["capital_total"]), "capital_total")
    versements = _valider_revenu(float(args["versements_cumules"]), "versements_cumules")
    anciennete = int(args.get("anciennete_ans", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    type_operation = args.get("type_operation", "rachat_partiel")
    montant_rachat = float(args.get("montant_rachat", 0))
    primes_apres_70 = float(args.get("primes_versees_apres_70_ans", 0))
    nb_beneficiaires = int(args.get("nb_beneficiaires", 1))

    # Calculs de base
    plus_value_totale = max(0, capital - versements)
    rendement_pct = (plus_value_totale / versements * 100) if versements > 0 else 0

    # Fraction des intérêts dans un rachat partiel
    def fraction_interets(rachat: float) -> float:
        if capital <= 0:
            return 0
        return rachat * (plus_value_totale / capital)

    lines = [
        "# Assurance-Vie — Simulation Fiscale",
        "",
        "## Contrat",
        f"- Capital total : {capital:,.0f}€",
        f"- Versements cumulés (primes) : {versements:,.0f}€",
        f"- Plus-value latente : {plus_value_totale:,.0f}€ ({rendement_pct:.1f}%)",
        f"- Ancienneté du contrat : {anciennete} ans",
        "",
    ]

    # ── Fiscalité des rachats ─────────────────────────────────────────────
    ABATT_SEUL = 4_600
    ABATT_COUPLE = 9_200
    abattement = ABATT_COUPLE if situation in ["marie", "pacse"] else ABATT_SEUL

    lines += [
        "## Fiscalité des rachats",
        "",
        f"| Ancienneté | Taux IR sur intérêts | Abattement annuel |",
        f"|-----------|---------------------|-------------------|",
        f"| < 4 ans | PFU 12.8% + PS 17.2% = **30%** | Aucun |",
        f"| 4 à 8 ans | PFU 12.8% + PS 17.2% = **30%** | Aucun |",
        f"| ≥ 8 ans | **7.5%** + PS 17.2% = **24.7%** | **{abattement:,}€/an** |",
        "",
    ]

    if type_operation == "rachat_partiel" and montant_rachat > 0:
        interets_rachat = fraction_interets(montant_rachat)
        capital_rachat = montant_rachat - interets_rachat

        lines += [
            f"### Rachat partiel de {montant_rachat:,.0f}€",
            f"- Dont capital : {capital_rachat:,.0f}€ (non imposable)",
            f"- Dont intérêts : {interets_rachat:,.0f}€ (imposables)",
            "",
        ]

        if anciennete >= 8:
            interets_imposables = max(0, interets_rachat - abattement)
            ir_7_5 = interets_imposables * 0.075
            ps = interets_rachat * 0.172
            total_fiscal = ir_7_5 + ps
            net_rachat = montant_rachat - total_fiscal
            lines += [
                f"**Contrat ≥ 8 ans :**",
                f"- Intérêts imposables après abattement {abattement:,}€ : {interets_imposables:,.0f}€",
                f"- IR 7.5% : {ir_7_5:,.0f}€",
                f"- PS 17.2% sur {interets_rachat:,.0f}€ : {ps:,.0f}€",
                f"- **Net reçu : {net_rachat:,.0f}€** (fiscalité : {total_fiscal:,.0f}€)",
            ]
            # Comparaison option barème
            nb_parts = calculer_parts(situation, nb_enfants)
            ir_bareme = calculer_ir(interets_imposables, nb_parts)["impot_net"]
            if ir_bareme < ir_7_5:
                lines.append(f"- ✅ Option barème IR plus favorable : {ir_bareme:,.0f}€ < {ir_7_5:,.0f}€")
        else:
            ir_pfu = interets_rachat * 0.128
            ps = interets_rachat * 0.172
            total_fiscal = ir_pfu + ps
            net_rachat = montant_rachat - total_fiscal
            lines += [
                f"**Contrat < 8 ans — PFU 30% :**",
                f"- IR 12.8% : {ir_pfu:,.0f}€",
                f"- PS 17.2% : {ps:,.0f}€",
                f"- **Net reçu : {net_rachat:,.0f}€** (fiscalité : {total_fiscal:,.0f}€)",
                "",
                f"💡 **Conseil : attendez 8 ans** pour bénéficier du taux 7.5% + abattement {abattement:,}€",
            ]

    elif type_operation == "rachat_total":
        if anciennete >= 8:
            interets_imposables = max(0, plus_value_totale - abattement)
            ir_7_5 = interets_imposables * 0.075
            ps = plus_value_totale * 0.172
            total_fiscal = ir_7_5 + ps
            net = capital - total_fiscal
            lines += [
                f"### Rachat total",
                f"- Plus-value imposable après abattement {abattement:,}€ : {interets_imposables:,.0f}€",
                f"- IR 7.5% : {ir_7_5:,.0f}€",
                f"- PS 17.2% sur {plus_value_totale:,.0f}€ : {ps:,.0f}€",
                f"- **Net perçu : {net:,.0f}€**",
            ]
        else:
            pfu = plus_value_totale * 0.30
            net = capital - pfu
            lines += [
                f"### Rachat total — PFU 30%",
                f"- Fiscalité sur {plus_value_totale:,.0f}€ : {pfu:,.0f}€",
                f"- **Net perçu : {net:,.0f}€**",
            ]

    # ── Transmission / Décès ──────────────────────────────────────────────
    ABATT_BENEF = 152_500  # par bénéficiaire, primes versées avant 70 ans
    SEUIL_PRELEVEMENT_1 = 700_000
    TAUX_PRELEVEMENT_1 = 0.20
    TAUX_PRELEVEMENT_2 = 0.3125

    capital_avant_70 = capital - primes_apres_70
    capital_apres_70_gains = primes_apres_70 * (1 + rendement_pct / 100) if rendement_pct > 0 else primes_apres_70

    lines += [
        "",
        "## Transmission au décès (hors succession)",
        "",
        "### Primes versées AVANT 70 ans (art. 990 I CGI)",
        f"- Abattement par bénéficiaire : **{ABATT_BENEF:,}€**",
        f"- Prélèvement : 20% jusqu'à {SEUIL_PRELEVEMENT_1:,}€ par bénéficiaire, puis 31.25%",
    ]

    base_par_benef = capital_avant_70 / nb_beneficiaires if nb_beneficiaires > 0 else capital_avant_70
    base_imposable = max(0, base_par_benef - ABATT_BENEF)
    if base_imposable <= SEUIL_PRELEVEMENT_1:
        prelevement = base_imposable * TAUX_PRELEVEMENT_1
    else:
        prelevement = SEUIL_PRELEVEMENT_1 * TAUX_PRELEVEMENT_1 + (base_imposable - SEUIL_PRELEVEMENT_1) * TAUX_PRELEVEMENT_2
    prelevement_total = prelevement * nb_beneficiaires

    lines += [
        f"- Capital hors succession : {capital_avant_70:,.0f}€ / {nb_beneficiaires} bénéficiaire(s)",
        f"- Par bénéficiaire : {base_par_benef:,.0f}€ − abattement {ABATT_BENEF:,}€ = {base_imposable:,.0f}€",
        f"- Prélèvement par bénéficiaire : {prelevement:,.0f}€",
        f"- **Net transmis au total : {capital_avant_70 - prelevement_total:,.0f}€**",
    ]

    if primes_apres_70 > 0:
        abatt_70 = 30_500
        base_succession = max(0, primes_apres_70 - abatt_70)
        lines += [
            "",
            "### Primes versées APRÈS 70 ans (art. 757 B CGI)",
            f"- Abattement global : {abatt_70:,}€ (tous bénéficiaires confondus)",
            f"- Primes après 70 ans : {primes_apres_70:,.0f}€",
            f"- Base soumise aux droits de succession : {base_succession:,.0f}€",
            "- ⚠️ Les gains sont exonérés — seules les primes nettes sont taxées",
        ]

    lines += [
        "",
        "## Avantages clés de l'assurance-vie",
        "- **Hors succession** : capital transmis sans droits jusqu'à 152 500€/bénéficiaire (avant 70 ans)",
        "- **Conjoint ou partenaire PACS** : totalement exonéré quel que soit le montant",
        f"- **Abattement annuel** sur les rachats après 8 ans : {abattement:,}€",
        "- **Taux préférentiel** 7.5% (au lieu de 12.8% PFU) après 8 ans",
        "- **Clause bénéficiaire** : désignez nominativement chaque bénéficiaire",
        "",
        "---",
        "*Source : CGI art. 990 I, 757 B, 125-0 A — Instruction fiscale BOFiP*",
    ]
    return "\n".join(lines)


def tool_simuler_demembrement(args: Dict) -> str:
    """Simule le démembrement de propriété : usufruit/nue-propriété, barème fiscal, stratégies."""
    valeur_pleine_propriete = _valider_revenu(float(args["valeur_pleine_propriete"]), "valeur_pleine_propriete")
    age_usufruitier = int(args["age_usufruitier"])
    type_operation = args.get("type_operation", "donation_nue_propriete")
    lien_parente = args.get("lien_parente", "enfant")
    nb_donataires = max(1, int(args.get("nb_donataires", 1)))
    usufruit_temporaire = bool(args.get("usufruit_temporaire", False))
    duree_usufruit_temporaire = int(args.get("duree_usufruit_temporaire", 10))

    # Barème fiscal de l'usufruit viager (art. 669 CGI)
    # Valeur de l'usufruit selon l'âge de l'usufruitier
    BAREME_USUFRUIT = [
        (20,  0.90),
        (30,  0.80),
        (40,  0.70),
        (50,  0.60),
        (60,  0.50),
        (70,  0.40),
        (80,  0.30),
        (90,  0.20),
        (999, 0.10),
    ]
    # Valeur de l'usufruit temporaire : 23% par tranche de 10 ans
    def valeur_usufruit_viager(age: int) -> float:
        for seuil, taux in BAREME_USUFRUIT:
            if age < seuil:
                return taux
        return 0.10

    def valeur_usufruit_temporaire(duree: int) -> float:
        # 23% pour chaque période de 10 ans, plafond 1
        return min(1.0, (duree / 10) * 0.23)

    if usufruit_temporaire:
        taux_usufruit = valeur_usufruit_temporaire(duree_usufruit_temporaire)
    else:
        taux_usufruit = valeur_usufruit_viager(age_usufruitier)

    taux_nue_propriete = 1 - taux_usufruit
    valeur_usufruit = valeur_pleine_propriete * taux_usufruit
    valeur_nue_propriete = valeur_pleine_propriete * taux_nue_propriete

    # Barèmes droits de donation ligne directe
    BAREME_DIRECTE = [
        (8_072,     0.05),
        (12_109,    0.10),
        (15_932,    0.15),
        (552_324,   0.20),
        (902_838,   0.30),
        (1_805_677, 0.40),
        (float("inf"), 0.45),
    ]
    ABATTEMENTS = {
        "enfant": 100_000,
        "frere_soeur": 15_932,
        "neveu_niece": 7_967,
        "conjoint": 80_724,
        "tiers": 1_594,
    }

    def calc_droits_donation(base: float, lien: str) -> float:
        abatt = ABATTEMENTS.get(lien, 1_594)
        taxable = max(0, base / nb_donataires - abatt)
        droits = 0.0
        prev = 0.0
        for seuil, taux in BAREME_DIRECTE:
            if taxable <= prev:
                break
            tranche = min(taxable, seuil) - prev
            droits += tranche * taux
            prev = seuil
        return droits * nb_donataires

    droits_pp = calc_droits_donation(valeur_pleine_propriete, lien_parente)
    droits_nue = calc_droits_donation(valeur_nue_propriete, lien_parente)
    economie = droits_pp - droits_nue

    lines = [
        "# Démembrement de Propriété",
        "*(Art. 669 CGI — Stratégie de transmission)*",
        "",
        "## Barème fiscal de l'usufruit (Art. 669 CGI)",
        "",
        "| Âge de l'usufruitier | Valeur usufruit | Valeur nue-propriété |",
        "|---------------------|----------------|---------------------|",
        "| Moins de 21 ans | 90% | 10% |",
        "| 21 à 30 ans | 80% | 20% |",
        "| 31 à 40 ans | 70% | 30% |",
        "| 41 à 50 ans | 60% | 40% |",
        "| 51 à 60 ans | 50% | 50% |",
        "| 61 à 70 ans | 40% | 60% |",
        "| 71 à 80 ans | 30% | 70% |",
        "| 81 à 90 ans | 20% | 80% |",
        "| Plus de 90 ans | 10% | 90% |",
        "",
    ]

    if usufruit_temporaire:
        lines += [
            f"## Usufruit temporaire ({duree_usufruit_temporaire} ans)",
            f"- Valeur fiscale de l'usufruit temporaire : **{taux_usufruit*100:.0f}%** (23% par tranche de 10 ans)",
            f"- Valeur de l'usufruit : {valeur_usufruit:,.0f}€",
            f"- Valeur de la nue-propriété : {valeur_nue_propriete:,.0f}€",
            "",
            "### Usage : donation temporaire d'usufruit",
            "- Transmettre l'usufruit à un enfant étudiant ou à une association",
            "- Les revenus lui reviennent directement (baisse de RNI pour le donateur)",
            "- Pas de droits de donation si le donataire est un enfant (abattement 100 000€)",
            "- **Impact IFI** : l'usufruitier déclare le bien en pleine propriété à l'IFI",
        ]
    else:
        lines += [
            f"## Votre situation — Usufruitier : {age_usufruitier} ans",
            f"- Taux usufruit : **{taux_usufruit*100:.0f}%** → Valeur : {valeur_usufruit:,.0f}€",
            f"- Taux nue-propriété : **{taux_nue_propriete*100:.0f}%** → Valeur : {valeur_nue_propriete:,.0f}€",
            "",
        ]

    lines += [
        "## Calcul — Donation de la nue-propriété",
        f"*(Bien en pleine propriété : {valeur_pleine_propriete:,.0f}€ — {nb_donataires} donataire(s), lien : {lien_parente})*",
        "",
        f"| | Donation PP | Donation nue-propriété |",
        f"|--|-------------|----------------------|",
        f"| Base taxable par donataire | {valeur_pleine_propriete/nb_donataires:,.0f}€ | {valeur_nue_propriete/nb_donataires:,.0f}€ |",
        f"| Abattement ({ABATTEMENTS.get(lien_parente, 1594):,}€) | oui | oui |",
        f"| Droits totaux | {droits_pp:,.0f}€ | {droits_nue:,.0f}€ |",
        f"| **Économie grâce au démembrement** | | **{economie:,.0f}€** |",
        "",
        "## Mécanisme et avantages",
        "",
        "### 1. Donation de la nue-propriété (stratégie classique)",
        "- Le parent conserve l'**usufruit** : il continue à habiter le bien ou percevoir les loyers",
        "- Les enfants reçoivent la **nue-propriété** : ils deviendront plein propriétaires au décès",
        "- Au décès de l'usufruitier : **extinction de l'usufruit sans droits supplémentaires**",
        f"- Plus le parent est jeune, plus la nue-propriété est faible → moins de droits",
        "",
        "### 2. Achat en démembrement",
        "- L'enfant achète la nue-propriété (décote) ; le parent finance l'usufruit",
        "- Stratégie utile si l'enfant a des liquidités mais pas de revenus immédiats",
        "",
        "### 3. Démembrement et IFI",
        "- L'**usufruitier** déclare la valeur en pleine propriété à l'IFI",
        "- Le nu-propriétaire n'est pas assujetti pour ce bien",
        "",
        "### 4. Donation-partage avec réserve d'usufruit",
        "- Partage anticipé et figé des valeurs (évite les conflits à la succession)",
        "- Les enfants sont assurés de recevoir leur part à la valeur actuelle",
        "- Rapport à la succession gelé à la date de la donation",
        "",
        "## Points de vigilance",
        f"- Abattement de {ABATTEMENTS.get(lien_parente, 1594):,}€ renouvelable tous les **15 ans**",
        "- Acte notarié obligatoire pour les immeubles",
        "- Quasi-usufruit sur somme d'argent : attention à la créance de restitution",
        "",
        "---",
        "*Source : CGI art. 669, 762 — BOFiP ENR-DMTG-10-10-20*",
    ]
    return "\n".join(lines)


def tool_simuler_cession_entreprise(args: Dict) -> str:
    """Simule la fiscalité de cession d'entreprise : abattements, apport-cession, départ retraite."""
    prix_cession = _valider_revenu(float(args["prix_cession"]), "prix_cession")
    prix_acquisition = float(args.get("prix_acquisition", 0))
    duree_detention_ans = int(args.get("duree_detention_ans", 0))
    type_cession = args.get("type_cession", "titres_pme")
    depart_retraite = bool(args.get("depart_retraite_dirigeant", False))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    apport_cession = bool(args.get("apport_avant_cession", False))

    pv_brute = max(0, prix_cession - prix_acquisition)
    nb_parts = calculer_parts(situation, nb_enfants)

    # Abattements pour durée de détention (régime PME — art. 150-0 D)
    ABATTEMENTS_DUREE = [
        (2, 0.50),   # 2 à 8 ans : 50%
        (8, 0.65),   # 8 à 12 ans (ou plus) : mais le régime de droit commun c'est 50% > 2 ans, 65% > 8 ans
    ]
    # Régime de droit commun (applicable depuis 2018 sous PFU — mais option barème possible)
    # Sous PFU : PAS d'abattement pour durée de détention
    # Sous barème : abattements applicables si titres acquis avant 01/01/2018
    # Régime PME créée depuis moins de 10 ans (art. 150-0 D ter) : abattements renforcés
    # 50% si 1-4 ans, 65% si 4-8 ans, 85% si > 8 ans

    def abatt_renforce(duree: int) -> float:
        if duree < 1:
            return 0.0
        elif duree < 4:
            return 0.50
        elif duree < 8:
            return 0.65
        else:
            return 0.85

    def abatt_droit_commun(duree: int) -> float:
        if duree < 2:
            return 0.0
        elif duree < 8:
            return 0.50
        else:
            return 0.65

    lines = [
        "# Cession d'Entreprise — Fiscalité de la Plus-Value",
        "",
        "## Paramètres",
        f"- Prix de cession : {prix_cession:,.0f}€",
        f"- Prix d'acquisition : {prix_acquisition:,.0f}€",
        f"- Plus-value brute : {pv_brute:,.0f}€",
        f"- Durée de détention : {duree_detention_ans} ans",
        f"- Type : {type_cession.replace('_', ' ')}",
        "",
    ]

    # ── Option A : PFU 30% (sans abattement) ─────────────────────────────
    pfu = pv_brute * 0.30
    net_pfu = pv_brute - pfu

    lines += [
        "## Option A — PFU 30% (Prélèvement Forfaitaire Unique)",
        "*(Régime par défaut depuis 2018)*",
        f"- PV brute × 30% = **{pfu:,.0f}€**",
        f"- Net après fiscalité : {net_pfu:,.0f}€",
        "",
    ]

    # ── Option B : Barème IR + abattements ───────────────────────────────
    ab_renf = abatt_renforce(duree_detention_ans)
    ab_comm = abatt_droit_commun(duree_detention_ans)
    pv_abatt_renf = pv_brute * (1 - ab_renf)
    pv_abatt_comm = pv_brute * (1 - ab_comm)

    ir_renf = calculer_ir(pv_abatt_renf, nb_parts)["impot_net"] if pv_abatt_renf > 0 else 0
    ps_renf = pv_brute * 0.172  # PS sur PV brute (les abattements ne s'appliquent pas aux PS)
    total_renf = ir_renf + ps_renf

    ir_comm = calculer_ir(pv_abatt_comm, nb_parts)["impot_net"] if pv_abatt_comm > 0 else 0
    total_comm = ir_comm + ps_renf

    lines += [
        "## Option B — Barème IR + abattements",
        "*(Option globale — s'applique à l'ensemble des revenus du capital)*",
        "",
        f"| | Abatt. renforcé PME | Abatt. droit commun |",
        f"|--|---------------------|---------------------|",
        f"| Condition | PME < 10 ans, détention ≥ 1 an | Titres acquis avant 2018 |",
        f"| Abattement | **{ab_renf*100:.0f}%** ({duree_detention_ans} ans de détention) | **{ab_comm*100:.0f}%** |",
        f"| PV après abattement | {pv_abatt_renf:,.0f}€ | {pv_abatt_comm:,.0f}€ |",
        f"| IR (barème) | {ir_renf:,.0f}€ | {ir_comm:,.0f}€ |",
        f"| PS 17.2% (sur PV brute) | {ps_renf:,.0f}€ | {ps_renf:,.0f}€ |",
        f"| **Total fiscal** | **{total_renf:,.0f}€** | **{total_comm:,.0f}€** |",
        f"| Net perçu | {pv_brute - total_renf:,.0f}€ | {pv_brute - total_comm:,.0f}€ |",
        "",
    ]

    meilleure = min(pfu, total_renf, total_comm)
    if meilleure == pfu:
        lines.append("✅ **PFU 30% est le plus favorable dans votre cas**")
    elif meilleure == total_renf:
        lines.append("✅ **Barème + abattement renforcé PME est le plus favorable**")
    else:
        lines.append("✅ **Barème + abattement droit commun est le plus favorable**")

    # ── Abattement départ retraite dirigeant ─────────────────────────────
    if depart_retraite:
        ABATT_RETRAITE = 500_000
        pv_apres_abatt_retraite = max(0, pv_brute - ABATT_RETRAITE)
        pfu_retraite = pv_apres_abatt_retraite * 0.30
        ps_retraite = pv_brute * 0.172  # PS sur PV brute avant abattement retraite
        total_retraite = pfu_retraite + ps_retraite
        economie_retraite = pfu - total_retraite

        lines += [
            "",
            "## Abattement départ à la retraite (Art. 150-0 D ter CGI)",
            "",
            f"- Abattement fixe : **{ABATT_RETRAITE:,}€**",
            f"- PV imposable après abattement : {pv_apres_abatt_retraite:,.0f}€",
            f"- IR PFU 12.8% : {pv_apres_abatt_retraite * 0.128:,.0f}€",
            f"- PS 17.2% (sur PV brute {pv_brute:,.0f}€) : {ps_retraite:,.0f}€",
            f"- **Total fiscal avec abattement retraite : {total_retraite:,.0f}€**",
            f"- Économie vs PFU sans abattement : **{economie_retraite:,.0f}€**",
            "",
            "### Conditions de l'abattement départ retraite",
            "1. Cession de titres d'une **PME** (CA < 10M€, bilan < 10M€, < 250 salariés)",
            "2. Le cédant a exercé une **fonction de direction** pendant ≥ 5 ans",
            "3. Le cédant doit partir à la retraite dans les **24 mois** avant ou après la cession",
            "4. Le cédant ne doit pas détenir > 50% des droits dans la société cessionnaire",
            "5. Abattement cumulable avec l'abattement renforcé PME (option barème)",
        ]

    # ── Apport-cession ────────────────────────────────────────────────────
    if apport_cession:
        lines += [
            "",
            "## Apport-Cession — Report d'imposition (Art. 150-0 B ter CGI)",
            "",
            "### Principe",
            "- Apportez vos titres à une **holding que vous contrôlez** avant la cession",
            "- La PV est mise en **report d'imposition** (pas d'impôt immédiat)",
            "- La holding reçoit le prix de cession et peut le réinvestir librement",
            "",
            "### Obligation de réinvestissement",
            "- Dans les **2 ans** suivant la cession : réinvestir ≥ **60%** du produit",
            "- Dans des activités économiques (PME, fonds professionnels…)",
            "- Sinon : la PV en report devient imposable immédiatement",
            "",
            "### Avantage",
            f"- Report de {pfu:,.0f}€ d'impôts → capital disponible pour réinvestissement : {prix_cession:,.0f}€",
            "- La PV en report n'est imposée qu'à la cession des titres de la holding",
            "  (ou au décès de l'apporteur → exonération définitive !)",
            "",
            "⚠️ Dispositif anti-abus : contrôle rigoureux par l'administration — consultez un avocat fiscaliste.",
        ]

    lines += [
        "",
        "## Synthèse — Mécanismes disponibles",
        "| Mécanisme | Avantage | Condition clé |",
        "|-----------|---------|---------------|",
        "| PFU 30% | Simplicité | Aucune |",
        "| Abatt. renforcé PME | Jusqu'à 85% d'abattement | PME < 10 ans, détention ≥ 1 an |",
        f"| Abatt. départ retraite | {500_000:,}€ d'abattement fixe | Direction ≥ 5 ans, retraite sous 24 mois |",
        "| Apport-cession | Report total de la PV | Holding contrôlée, réinvestissement 60% |",
        "| Pacte Dutreil | Exo 75% droits mutation | Transmission familiale uniquement |",
        "",
        "---",
        "*Source : CGI art. 150-0 A, 150-0 D, 150-0 D ter, 150-0 B ter*",
        "*Consultez impérativement un avocat fiscaliste ou expert-comptable avant toute cession.*",
    ]
    return "\n".join(lines)


def tool_simuler_holding(args: Dict) -> str:
    """Simule l'intérêt d'une holding : régime mère-fille, intégration fiscale, optimisation IS."""
    benefice_filiale = _valider_revenu(float(args["benefice_filiale"]), "benefice_filiale")
    taux_detention = float(args.get("taux_detention_holding", 100))
    dividendes_souhaites = float(args.get("dividendes_vers_personne_physique", 0))
    reinvestissement = float(args.get("montant_reinvestissement", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    nb_filiales = int(args.get("nb_filiales", 1))

    SEUIL_IS_REDUIT = 42_500
    TAUX_IS_15 = 0.15
    TAUX_IS_25 = 0.25

    def calc_is(base: float) -> float:
        if base <= 0:
            return 0.0
        if base <= SEUIL_IS_REDUIT:
            return base * TAUX_IS_15
        return SEUIL_IS_REDUIT * TAUX_IS_15 + (base - SEUIL_IS_REDUIT) * TAUX_IS_25

    nb_parts = calculer_parts(situation, nb_enfants)

    # IS filiale
    is_filiale = calc_is(benefice_filiale)
    resultat_net_filiale = benefice_filiale - is_filiale

    # ── Détention directe (sans holding) ─────────────────────────────────
    dividendes_directs = resultat_net_filiale * (taux_detention / 100)
    pfu_directs = dividendes_directs * 0.30
    net_direct = dividendes_directs - pfu_directs

    # ── Via holding — Régime mère-fille ──────────────────────────────────
    # Dividendes remontés à la holding : exonération 95% (quote-part de frais et charges 5%)
    dividendes_holding = resultat_net_filiale * (taux_detention / 100)
    quote_part_fec = dividendes_holding * 0.05  # réintégration 5%
    is_holding_sur_qpfec = calc_is(quote_part_fec)
    # Fiscalité effective : IS sur 5% seulement
    taux_effectif_regime_mere_fille = is_holding_sur_qpfec / dividendes_holding * 100 if dividendes_holding > 0 else 0

    # Si la holding redistribue à son tour (dividendes PP)
    net_holding_avant_redistrib = dividendes_holding - is_holding_sur_qpfec
    if dividendes_souhaites > 0:
        div_redistrib = min(dividendes_souhaites, net_holding_avant_redistrib)
        pfu_redistrib = div_redistrib * 0.30
        net_redistrib = div_redistrib - pfu_redistrib
    else:
        div_redistrib = 0
        pfu_redistrib = 0
        net_redistrib = 0

    economie_vs_direct = net_holding_avant_redistrib - net_direct

    lines = [
        "# Holding — Optimisation Fiscale",
        "",
        "## Paramètres",
        f"- Bénéfice de la filiale : {benefice_filiale:,.0f}€",
        f"- Taux de détention de la holding : {taux_detention:.0f}%",
        f"- Filiales concernées : {nb_filiales}",
        "",
        "## IS de la filiale",
        f"| Tranche | Taux | IS |",
        f"|---------|------|-----|",
    ]
    if benefice_filiale <= SEUIL_IS_REDUIT:
        lines.append(f"| Totalité | 15% | {is_filiale:,.0f}€ |")
    else:
        lines += [
            f"| 0 → {SEUIL_IS_REDUIT:,}€ | 15% | {SEUIL_IS_REDUIT * TAUX_IS_15:,.0f}€ |",
            f"| Au-delà | 25% | {(benefice_filiale - SEUIL_IS_REDUIT) * TAUX_IS_25:,.0f}€ |",
        ]
    lines += [
        f"| **Total IS filiale** | | **{is_filiale:,.0f}€** |",
        f"- Résultat net filiale : {resultat_net_filiale:,.0f}€",
        "",
        "## Comparatif : Détention directe vs Holding",
        "",
        f"| | Détention directe | Via holding (régime mère-fille) |",
        f"|--|-------------------|--------------------------------|",
        f"| Dividendes reçus | {dividendes_directs:,.0f}€ | {dividendes_holding:,.0f}€ |",
        f"| Quote-part frais et charges (5%) | — | {quote_part_fec:,.0f}€ réintégrée |",
        f"| IS sur les dividendes | PFU 30% = {pfu_directs:,.0f}€ | IS sur 5% = {is_holding_sur_qpfec:,.0f}€ |",
        f"| Taux effectif sur dividendes | 30% | **{taux_effectif_regime_mere_fille:.1f}%** |",
        f"| **Net disponible** | **{net_direct:,.0f}€** | **{net_holding_avant_redistrib:,.0f}€** |",
        f"| **Avantage holding** | | **+{economie_vs_direct:,.0f}€** |",
        "",
    ]

    if reinvestissement > 0:
        is_eco = calc_is(reinvestissement)
        net_reinvest = reinvestissement - is_eco
        lines += [
            f"## Réinvestissement via la holding",
            f"- Montant à réinvestir : {reinvestissement:,.0f}€",
            f"- IS de la holding sur ce bénéfice : {is_eco:,.0f}€",
            f"- Capital net à investir : {net_reinvest:,.0f}€",
            f"- Avantage : la holding peut réinvestir {net_holding_avant_redistrib:,.0f}€",
            f"  vs {net_direct:,.0f}€ en détention directe (après PFU 30%)",
            "",
        ]

    if dividendes_souhaites > 0:
        lines += [
            f"## Redistribution à l'actionnaire ({dividendes_souhaites:,.0f}€ souhaités)",
            f"- Dividendes redistribués depuis la holding : {div_redistrib:,.0f}€",
            f"- PFU 30% au niveau de l'actionnaire : {pfu_redistrib:,.0f}€",
            f"- **Net perçu par l'actionnaire : {net_redistrib:,.0f}€**",
            "",
            "*(La holding a déjà payé IS sur 5% → pas de double imposition sur 95%)*",
            "",
        ]

    lines += [
        "## Conditions du régime mère-fille (Art. 145 CGI)",
        "1. La holding doit détenir **≥ 5%** du capital de la filiale",
        "2. Les titres doivent être détenus depuis **≥ 2 ans**",
        "3. La holding doit être soumise à l'**IS**",
        "4. La filiale doit être une société passible de l'IS (France ou UE avec convention)",
        "",
        "## Autres avantages de la holding",
        "- **Intégration fiscale** : si détention ≥ 95%, compensation des déficits entre filiales",
        "  → La holding paie l'IS sur le résultat consolidé du groupe",
        "- **Rachat de ses propres titres** : mécanisme alternatif aux dividendes",
        "- **Transmission** : donations de parts de holding + abattements + Dutreil possible",
        "- **Levier d'acquisition** (LBO) : la holding s'endette pour racheter, les intérêts sont déductibles",
        "",
        "## Précautions",
        "- Holding **animatrice** (vs passive) : conditions d'éligibilité IFI, Dutreil, abattements PME",
        "- Frais de création et gestion de la holding (comptable, juridique) à prendre en compte",
        "- Administration peut requalifier si la holding n'a pas de substance économique réelle",
        "",
        "---",
        "*Source : CGI art. 145, 216, 223 A — Régime d'intégration fiscale : art. 223 A à U*",
    ]
    return "\n".join(lines)
# ═══════════════════════════════════════════════════════════════════════════
# GROUP 2 : TVA, Auto-entrepreneur, CFE, PEA, Défiscalisation solidaire
# ═══════════════════════════════════════════════════════════════════════════

def tool_calculer_tva(args: Dict) -> str:
    """Guide et calcul TVA : franchise, régimes réels, taux, intracommunautaire."""
    ca_ht = float(args.get("chiffre_affaires_ht", 0))
    type_activite = args.get("type_activite", "services")
    regime_souhaite = args.get("regime", "auto")
    tva_collectee = float(args.get("tva_collectee", 0))
    tva_deductible = float(args.get("tva_deductible", 0))
    ventes_ue = float(args.get("ventes_intracommunautaires", 0))
    achats_ue = float(args.get("achats_intracommunautaires", 0))

    # Seuils franchise en base 2025
    SEUILS = {
        "marchandises":  {"principal": 85_000, "majore": 93_500},
        "services":      {"principal": 37_500, "majore": 41_250},  # LF2025: abaissé de 36 800 à 37 500
        "liberal":       {"principal": 37_500, "majore": 41_250},
        "mixte":         {"principal": 37_500, "majore": 41_250},
        "agricole":      {"principal": 46_000, "majore": 56_000},
    }
    seuils = SEUILS.get(type_activite, SEUILS["services"])

    # Détermination du régime
    if regime_souhaite == "auto":
        if ca_ht == 0:
            regime_applicable = "franchise"
        elif ca_ht <= seuils["principal"]:
            regime_applicable = "franchise"
        elif ca_ht <= 840_000 if type_activite == "marchandises" else ca_ht <= 254_000:
            regime_applicable = "reel_simplifie"
        else:
            regime_applicable = "reel_normal"
    else:
        regime_applicable = regime_souhaite

    taux_principaux = {
        "normal": 20.0,
        "intermediaire": 10.0,
        "reduit": 5.5,
        "super_reduit": 2.1,
    }

    lines = [
        "# TVA — Taxe sur la Valeur Ajoutée",
        "",
        "## Taux de TVA en France",
        "",
        "| Taux | % | Applications principales |",
        "|------|---|--------------------------|",
        "| **Normal** | 20% | Majorité des biens et services |",
        "| **Intermédiaire** | 10% | Restauration, travaux rénovation, transports, hôtellerie |",
        "| **Réduit** | 5.5% | Alimentation, livres, travaux économies d'énergie, billetterie |",
        "| **Super-réduit** | 2.1% | Médicaments remboursables, presse, spectacles vivants |",
        "",
        "## Seuils de franchise en base 2025",
        "",
        f"| Activité | Seuil principal | Seuil majoré |",
        f"|---------|----------------|--------------|",
        f"| Marchandises/vente | {SEUILS['marchandises']['principal']:,}€ | {SEUILS['marchandises']['majore']:,}€ |",
        f"| Services / libéral | {SEUILS['services']['principal']:,}€ | {SEUILS['services']['majore']:,}€ |",
        f"| Agricole | {SEUILS['agricole']['principal']:,}€ | {SEUILS['agricole']['majore']:,}€ |",
        "",
        "*(Si CA dépasse le seuil majoré en cours d'année → assujettissement immédiat)*",
        "",
    ]

    if ca_ht > 0:
        lines += [
            f"## Votre situation — CA HT : {ca_ht:,.0f}€ ({type_activite})",
            f"Seuil franchise principal : {seuils['principal']:,}€ | majoré : {seuils['majore']:,}€",
            "",
        ]

        if regime_applicable == "franchise":
            lines += [
                "### ✅ Franchise en base — Aucune TVA à collecter",
                f"- CA {ca_ht:,.0f}€ ≤ seuil {seuils['principal']:,}€",
                "- Mentions obligatoires sur factures : **« TVA non applicable — art. 293 B CGI »**",
                "- Avantage : simplicité, prix compétitifs B2C",
                "- Inconvénient : **TVA sur achats non déductible** (coût réel pour les achats)",
                "",
                "### Passage au régime réel",
                "- Option possible à tout moment (irrévocable 2 ans)",
                "- Obligatoire si CA > seuil majoré en cours d'année (effet immédiat)",
            ]
        else:
            tva_nette = tva_collectee - tva_deductible
            lines += [
                f"### Régime {regime_applicable.replace('_', ' ').title()}",
                "",
            ]
            if regime_applicable == "reel_simplifie":
                lines += [
                    "- Déclaration **annuelle** (CA3 annuelle déposée avant le 2ème jour ouvré de mai)",
                    "- 2 acomptes semestriels : 55% en juillet, 40% en décembre (sur TVA N-1)",
                    "- Dispense d'acompte si TVA annuelle < 1 000€",
                ]
            else:
                lines += [
                    "- Déclaration **mensuelle** (CA3 mensuelle, ou trimestrielle si TVA < 4 000€/an)",
                    "- Paiement mensuel de la TVA nette due",
                ]

            if tva_collectee > 0 or tva_deductible > 0:
                lines += [
                    "",
                    "### Calcul TVA nette",
                    f"- TVA collectée (sur ventes) : {tva_collectee:,.0f}€",
                    f"- TVA déductible (sur achats) : {tva_deductible:,.0f}€",
                    f"- **TVA nette {'due' if tva_nette >= 0 else 'à rembourser'} : {abs(tva_nette):,.0f}€**",
                ]
                if tva_nette < 0:
                    lines.append("- Crédit de TVA : remboursable sur demande (formulaire 3519)")

    # TVA intracommunautaire
    if ventes_ue > 0 or achats_ue > 0:
        lines += [
            "",
            "## TVA Intracommunautaire (UE)",
            "",
            "### Numéro de TVA intracommunautaire",
            "- Obligatoire pour tout assujetti effectuant des échanges intra-UE",
            "- Format France : **FR + 2 clés + SIREN** (ex. FR12 123456789)",
            "",
        ]
        if ventes_ue > 0:
            lines += [
                f"### Ventes vers l'UE : {ventes_ue:,.0f}€",
                "- **B2B (professionnel) :** autoliquidation — le client déclare la TVA dans son pays",
                "  → Facturez HT, mention « Autoliquidation par le preneur »",
                "- **B2C (particulier) :** seuil OSS 10 000€ — si > 10 000€ : TVA du pays du client",
                "  → Déclarez via le guichet OSS (One Stop Shop) sur impots.gouv.fr",
            ]
        if achats_ue > 0:
            lines += [
                f"### Achats depuis l'UE : {achats_ue:,.0f}€",
                "- **Autoliquidation** : vous déclarez et déduisez simultanément la TVA",
                "- Net fiscal = 0 si pleinement assujetti (sauf pro-rata)",
            ]

    lines += [
        "",
        "## Règles clés",
        "- **Fait générateur** : livraison du bien (vente) ou encaissement (services par défaut)",
        "- **Exigibilité** : sur les débits (option) ou les encaissements (défaut pour services)",
        "- **Délai de déduction** : TVA déductible à la date de la facture fournisseur",
        "- **Prescription** : 2 ans pour réclamer un remboursement de crédit de TVA",
        "",
        "---",
        "*Source : CGI art. 256 à 293 B — Directive TVA 2006/112/CE*",
    ]
    return "\n".join(lines)


def tool_guide_auto_entrepreneur(args: Dict) -> str:
    """Guide complet auto-entrepreneur / micro-entrepreneur : seuils, cotisations, TVA, fiscalité."""
    ca = float(args.get("chiffre_affaires_annuel", 0))
    type_activite = args.get("type_activite", "services_bic")
    option_vfl = bool(args.get("option_versement_liberatoire", False))
    rni_foyer = float(args.get("rni_foyer_n_moins_2", 0))
    nb_parts_foyer = float(args.get("nb_parts_foyer", 1.0))
    premiere_annee = bool(args.get("premiere_annee", False))
    acre = bool(args.get("beneficie_acre", False))

    # Seuils et taux 2025
    ACTIVITES = {
        "vente_marchandises": {
            "label": "Vente de marchandises / hébergement / restauration",
            "seuil_ca": 188_700,
            "seuil_tva_franchise": 85_000,
            "taux_cotisations": 0.128,
            "taux_vfl": 0.01,
            "abattement_ir": 0.71,
        },
        "services_bic": {
            "label": "Prestations de services BIC (artisans, commerçants)",
            "seuil_ca": 77_700,
            "seuil_tva_franchise": 37_500,
            "taux_cotisations": 0.214,
            "taux_vfl": 0.017,
            "abattement_ir": 0.50,
        },
        "services_bnc": {
            "label": "Professions libérales / BNC",
            "seuil_ca": 77_700,
            "seuil_tva_franchise": 37_500,
            "taux_cotisations": 0.231,
            "taux_vfl": 0.022,
            "abattement_ir": 0.34,
        },
    }

    act = ACTIVITES.get(type_activite, ACTIVITES["services_bic"])
    taux_cotis = act["taux_cotisations"]
    if acre:
        taux_cotis = taux_cotis * 0.50  # ACRE : 50% de réduction la 1ère année
    cotisations = ca * taux_cotis
    net_avant_ir = ca - cotisations

    # IR micro (abattement forfaitaire)
    revenu_imposable = max(0, ca * (1 - act["abattement_ir"]))

    # VFL : Versement Libératoire Forfaitaire
    seuil_vfl = {1: 27_478, 1.5: 34_348, 2: 41_217, 2.5: 48_087, 3: 54_956}.get(
        nb_parts_foyer, nb_parts_foyer * 13_739
    )
    eligible_vfl = rni_foyer <= seuil_vfl if rni_foyer > 0 else True

    vfl_taux = act["taux_vfl"]
    vfl_montant = ca * vfl_taux

    lines = [
        "# Guide Auto-Entrepreneur (Micro-Entrepreneur) 2025",
        "",
        "## Activité",
        f"**{act['label']}**",
        "",
        "## Seuils de CA à ne pas dépasser",
        f"| Seuil | Montant | Conséquence si dépassé |",
        f"|-------|---------|------------------------|",
        f"| **CA annuel max** | {act['seuil_ca']:,}€ | Basculement régime réel (au 1er jan. suivant) |",
        f"| **Franchise TVA** | {act['seuil_tva_franchise']:,}€ | Assujettissement TVA si seuil majoré dépassé en cours d'année |",
        "",
    ]

    if ca > 0:
        lines += [
            f"## Simulation pour un CA de {ca:,.0f}€",
            "",
            "### Cotisations sociales",
            f"- Taux : **{act['taux_cotisations']*100:.1f}%**" + (" (réduit 50% ACRE)" if acre else ""),
            f"- Cotisations : {cotisations:,.0f}€",
            f"- Net après cotisations : {net_avant_ir:,.0f}€",
            "",
            "### Fiscalité",
            f"**Option A — Abattement forfaitaire IR ({act['abattement_ir']*100:.0f}%)**",
            f"- Revenu imposable (case 5HQ/5KO) : {revenu_imposable:,.0f}€",
            "- Imposé au barème progressif avec les autres revenus du foyer",
            "",
        ]
        if eligible_vfl:
            lines += [
                f"**Option B — Versement Libératoire Forfaitaire (VFL)** ✅ Éligible",
                f"- Taux : {vfl_taux*100:.1f}% du CA",
                f"- Montant VFL : {vfl_montant:,.0f}€ (prélevé avec les cotisations mensuelles/trimestrielles)",
                "- L'IR est soldé : pas de régularisation en fin d'année",
            ]
            if rni_foyer > 0:
                lines.append(
                    f"- RFR N-2 : {rni_foyer:,.0f}€ ≤ seuil {seuil_vfl:,.0f}€ → éligible ✅"
                )
            # Comparaison
            if revenu_imposable > 0:
                ir_bareme_estime = revenu_imposable * 0.11  # TMI 11% par défaut, approximatif
                if vfl_montant < ir_bareme_estime:
                    lines.append(f"- 💡 VFL souvent avantageux si TMI ≥ {vfl_taux/(1-act['abattement_ir'])*100:.0f}%")
        else:
            lines += [
                f"**Option B — VFL** ⛔ Non éligible",
                f"- RFR N-2 : {rni_foyer:,.0f}€ > seuil {seuil_vfl:,.0f}€",
            ]

        if ca > act["seuil_tva_franchise"]:
            lines += [
                "",
                f"### ⚠️ TVA",
                f"CA {ca:,.0f}€ > seuil franchise {act['seuil_tva_franchise']:,}€",
                "→ **Assujettissement à la TVA obligatoire** (ou déjà en cours d'année si seuil majoré dépassé)",
                "→ Facturez TTC et déposez des CA3",
            ]

    if premiere_annee:
        lines += [
            "",
            "## Première année — Points clés",
            "- **Inscription** : sur autoentrepreneur.urssaf.fr (gratuit)",
            "- **Début d'activité** : la déclaration de CA est obligatoire dès le 1er mois (même si CA = 0)",
            "- **ACRE** : demandez l'exonération ACRE à l'URSSAF lors de la création",
            f"  → Cotisations réduites à {act['taux_cotisations']*50:.1f}% pendant 12 mois",
            "- **Prorata CA** : le seuil de CA est proratisé à la date de création la 1ère année",
            f"  → Ex. création en juillet : seuil = {act['seuil_ca']:,}€ × 6/12 = {act['seuil_ca']//2:,}€",
        ]

    lines += [
        "",
        "## Obligations déclaratives",
        "- **Déclaration du CA** : mensuellement ou trimestriellement sur autoentrepreneur.urssaf.fr",
        "- **Déclaration IR** : case 5KO (BNC) ou 5KP (BIC services) ou 5KY (BIC ventes)",
        "- **Cotisation CFE** : due dès la 2ème année (exonération la 1ère année d'activité)",
        "- **Registre des achats** : obligatoire pour les activités de vente",
        "- **Livre des recettes** : obligatoire (date, montant, nature, mode de paiement)",
        "",
        "## Radiation automatique",
        "- Si CA = 0 pendant **24 mois consécutifs** → radiation automatique par l'URSSAF",
        "",
        "---",
        "*Source : Art. L133-6-8 CSS — CGI art. 50-0, 102 ter — Décret n°2008-1348*",
    ]
    return "\n".join(lines)


def tool_calculer_cfe(args: Dict) -> str:
    """Calcule la Cotisation Foncière des Entreprises (CFE) : base, taux, exonérations."""
    ca = float(args.get("chiffre_affaires", 0))
    commune = args.get("commune_type", "moyenne")
    type_entreprise = args.get("type_entreprise", "auto_entrepreneur")
    premiere_annee = bool(args.get("premiere_annee_activite", False))
    superficie_locaux = float(args.get("superficie_locaux_m2", 0))
    valeur_locative_brute = float(args.get("valeur_locative_brute", 0))

    # Cotisation minimum selon le CA (barème national 2024)
    # La CFE minimum est fixée par la commune dans ces fourchettes
    COTISATION_MINIMUM = [
        (10_000,   238, 565),
        (32_600,   238, 1_130),
        (100_000,  238, 2_383),
        (250_000,  238, 3_981),
        (500_000,  238, 5_677),
        (3_000_000,238, 7_370),
        (float("inf"), 238, 9_064),
    ]

    def cotisation_min(ca_val: float) -> tuple:
        for seuil, mini, maxi in COTISATION_MINIMUM:
            if ca_val <= seuil:
                return (mini, maxi)
        return (238, 9_064)

    cot_min, cot_max = cotisation_min(ca)
    # Estimation : milieu de la fourchette ajusté selon le type de commune
    coeff_commune = {"petite": 0.6, "moyenne": 0.8, "grande": 1.0, "paris": 1.2}.get(commune, 0.8)
    cfe_estimee = cot_min + (cot_max - cot_min) * coeff_commune

    lines = [
        "# Cotisation Foncière des Entreprises (CFE)",
        "",
        "## Qu'est-ce que la CFE ?",
        "- Taxe locale annuelle due par **toute personne physique ou morale** exerçant une activité professionnelle non salariée",
        "- S'applique aux : auto-entrepreneurs, libéraux, sociétés, SCI louant des locaux...",
        "- Calculée sur la **valeur locative des biens immobiliers** utilisés pour l'activité",
        "",
        "## Cotisation minimum (barème 2024)",
        "Si pas de locaux propres (domicile = siège social), une cotisation minimum s'applique :",
        "",
        "| CA réalisé N-2 | Fourchette cotisation minimum |",
        "|---------------|-------------------------------|",
    ]
    for seuil, mini, maxi in COTISATION_MINIMUM:
        seuil_label = f"≤ {seuil:,}€" if seuil != float("inf") else "> 3 000 000€"
        lines.append(f"| {seuil_label} | {mini}€ → {maxi}€ |")

    if premiere_annee:
        lines += [
            "",
            "## ✅ Exonération 1ère année",
            "**Exonération totale de CFE l'année de création de l'entreprise**",
            "- Pas de CFE due pour l'année de début d'activité",
            "- La CFE sera due à compter de l'année suivante",
        ]
    elif ca > 0:
        lines += [
            "",
            f"## Estimation pour un CA de {ca:,.0f}€",
            f"- Fourchette applicable : {cot_min}€ → {cot_max}€",
            f"- Estimation selon localisation ({commune}) : **~{cfe_estimee:,.0f}€/an**",
            "",
            "*(Le montant exact est fixé par la commune — consultez votre avis de CFE)*",
        ]

    if valeur_locative_brute > 0:
        lines += [
            "",
            f"## Si vous avez des locaux (valeur locative brute : {valeur_locative_brute:,.0f}€)",
            "- CFE = Base nette × Taux communal",
            f"- Base nette (après abattement 50% locaux industriels ou usage) ≈ {valeur_locative_brute * 0.80:,.0f}€",
            "- Taux communal : variable, généralement entre 15% et 35%",
            f"- CFE estimée : {valeur_locative_brute * 0.80 * 0.25:,.0f}€ (hypothèse taux 25%)",
        ]

    lines += [
        "",
        "## Exonérations principales",
        "| Cas | Durée | Condition |",
        "|-----|-------|-----------|",
        "| Création d'entreprise | 1 an | Automatique |",
        "| Jeune Entreprise Innovante (JEI) | 7 ans | R&D ≥ 15% des charges |",
        "| Zone Franche Urbaine (ZFU) | 5 ans | Implantation en ZFU |",
        "| Zone de Revitalisation Rurale (ZRR) | 5 ans | Implantation en ZRR |",
        "| Auto-entrepreneur CA < 5 000€ | Permanente | CA annuel ≤ 5 000€ |",
        "| Artisans sans salariés | Permanente | Travail manuel principal |",
        "| Agriculteurs | Permanente | Activité agricole |",
        "",
        "## Paiement",
        "- **Date limite** : 15 décembre de chaque année",
        "- Avis disponible sur impots.gouv.fr (espace professionnel)",
        "- Mensualisation possible",
        "",
        "## Déductibilité",
        "- **Déductible** des résultats imposables (BIC, BNC, IS)",
        "- Non déductible en micro-entreprise (abattement forfaitaire couvre tout)",
        "",
        "---",
        "*Source : CGI art. 1447 à 1478 — Instruction fiscale BOFiP IF-CFE*",
    ]
    return "\n".join(lines)


def tool_simuler_investissement_pea(args: Dict) -> str:
    """Simule la fiscalité et les règles du PEA (Plan Épargne en Actions)."""
    versements = float(args.get("versements_cumules", 0))
    valeur_actuelle = float(args.get("valeur_actuelle", 0))
    anciennete_ans = int(args.get("anciennete_ans", 0))
    type_pea = args.get("type_pea", "pea_classique")
    montant_retrait = float(args.get("montant_retrait", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))

    PLAFOND_PEA = 150_000
    PLAFOND_PEA_PME = 75_000
    plafond = PLAFOND_PEA if type_pea == "pea_classique" else PLAFOND_PEA_PME

    plus_value = max(0, valeur_actuelle - versements)
    taux_pv = (plus_value / versements * 100) if versements > 0 else 0

    lines = [
        "# Plan Épargne en Actions (PEA)",
        "",
        "## Les deux types de PEA",
        f"| | PEA classique | PEA-PME |",
        f"|--|--------------|---------|",
        f"| Plafond versements | {PLAFOND_PEA:,}€ | {PLAFOND_PEA_PME:,}€ |",
        f"| Titres éligibles | Actions UE, OPCVM ≥ 75% actions UE | PME/ETI, crowdfunding equity |",
        f"| Cumulable | Oui (1 PEA + 1 PEA-PME max) | Oui |",
        "",
        "## Votre PEA",
        f"- Type : {type_pea.replace('_', ' ').upper()}",
        f"- Plafond : {plafond:,}€",
        f"- Versements cumulés : {versements:,.0f}€ ({plafond - versements:,.0f}€ de capacité restante)" if versements <= plafond else f"- Versements : {versements:,.0f}€ ⚠️ Plafond atteint",
        f"- Valeur actuelle : {valeur_actuelle:,.0f}€",
        f"- Plus-value latente : {plus_value:,.0f}€ ({taux_pv:.1f}%)",
        f"- Ancienneté : {anciennete_ans} ans",
        "",
        "## Fiscalité selon l'ancienneté",
        "",
        "| Ancienneté | IR sur PV | PS 17.2% | Total | Clôture |",
        "|-----------|-----------|----------|-------|---------|",
        "| < 2 ans | 22.5% | 17.2% | **39.7%** | Clôture obligatoire |",
        "| 2 à 5 ans | 19% | 17.2% | **36.2%** | Clôture obligatoire |",
        "| ≥ 5 ans | **0%** | 17.2% | **17.2%** | Retrait partiel autorisé (si > 5 ans) |",
        "| ≥ 5 ans (rente) | 0% | 0% | **0%** | Sortie en rente viagère exonérée |",
        "",
    ]

    if anciennete_ans >= 5 and valeur_actuelle > 0:
        ps_due = plus_value * 0.172
        net_apres_ps = valeur_actuelle - ps_due
        lines += [
            "## ✅ Votre PEA a plus de 5 ans — Avantage fiscal maximum",
            "",
            f"| | Montant |",
            f"|--|---------|",
            f"| Valeur totale | {valeur_actuelle:,.0f}€ |",
            f"| PS 17.2% sur PV {plus_value:,.0f}€ | {ps_due:,.0f}€ |",
            f"| **Net après fiscalité** | **{net_apres_ps:,.0f}€** |",
            "",
        ]
        if montant_retrait > 0:
            pv_fraction = montant_retrait * (plus_value / valeur_actuelle) if valeur_actuelle > 0 else 0
            ps_retrait = pv_fraction * 0.172
            lines += [
                f"### Retrait partiel de {montant_retrait:,.0f}€",
                f"- Fraction de PV dans le retrait : {pv_fraction:,.0f}€",
                f"- PS dues : {ps_retrait:,.0f}€",
                f"- Net retrait : {montant_retrait - ps_retrait:,.0f}€",
                "- ✅ Le PEA reste ouvert après un retrait partiel (si > 5 ans)",
            ]
    elif anciennete_ans < 5 and plus_value > 0:
        taux_ir = 0.225 if anciennete_ans < 2 else 0.19
        ir_pv = plus_value * taux_ir
        ps_pv = plus_value * 0.172
        total = ir_pv + ps_pv
        net = valeur_actuelle - total
        lines += [
            f"## Fiscalité si clôture maintenant ({anciennete_ans} ans)",
            f"- IR {taux_ir*100:.1f}% : {ir_pv:,.0f}€",
            f"- PS 17.2% : {ps_pv:,.0f}€",
            f"- Total fiscal : {total:,.0f}€",
            f"- Net perçu : {net:,.0f}€",
            "",
            f"💡 **Attendez {5 - anciennete_ans} an(s)** de plus pour économiser ~{ir_pv:,.0f}€ d'IR",
        ]

    lines += [
        "",
        "## Règles essentielles",
        "- **1 PEA par personne** (2 par foyer fiscal) + 1 PEA-PME",
        "- Les dividendes et PV restent dans le PEA sans imposition immédiate",
        "- Après 5 ans : retraits partiels possibles sans clôture",
        "- Avant 5 ans : tout retrait entraîne la **clôture du PEA**",
        "- Rente viagère après 5 ans : **totalement exonérée** (IR + PS)",
        "",
        "## Titres éligibles PEA",
        "- Actions de sociétés de l'Union Européenne (siège dans l'UE)",
        "- OPCVM (SICAV, FCP) investis à ≥ 75% en actions UE",
        "- ETF répliquant des indices UE",
        "- ⛔ Actions américaines, obligations, fonds monétaires : non éligibles",
        "",
        "## Comparaison PEA vs CTO (Compte-Titres Ordinaire)",
        "| | PEA | CTO |",
        "|--|-----|-----|",
        "| Fiscalité après 5 ans | 17.2% (PS seulement) | 30% (PFU) |",
        "| Flexibilité des retraits | Limitée avant 5 ans | Totale |",
        "| Titres éligibles | Actions UE principalement | Monde entier |",
        "| Plafond | 150 000€ | Aucun |",
        "",
        "---",
        "*Source : CGI art. 157 (22°) — Art. 150-0 A — Loi n°92-666 du 16/07/1992*",
    ]
    return "\n".join(lines)


def tool_guide_defiscalisation_solidaire(args: Dict) -> str:
    """Guide des dispositifs de défiscalisation solidaire : dons, PME, FIP, FCPI, SOFICA."""
    revenu_net_imposable = float(args.get("revenu_net_imposable", 0))
    impot_actuel = float(args.get("impot_actuel", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    patrimoine_ifi = float(args.get("patrimoine_ifi", 0))
    a_tmi_41_plus = bool(args.get("tmi_41_ou_plus", False))

    nb_parts = calculer_parts(situation, nb_enfants)
    if impot_actuel == 0 and revenu_net_imposable > 0:
        impot_actuel = calculer_ir(revenu_net_imposable, nb_parts)["impot_net"]

    lines = [
        "# Défiscalisation Solidaire & Éthique 2025",
        "",
        "## 1. Dons aux associations et organismes",
        "",
        "| Type de bénéficiaire | Réduction d'impôt | Plafond dons |",
        "|---------------------|-------------------|--------------|",
        "| Aide aux personnes en difficulté (restos du cœur, Secours Populaire…) | **75%** | 1 000€/an |",
        "| Autres associations d'intérêt général | **66%** | 20% du RNI |",
        "| Associations cultuelles | **66%** | 20% du RNI |",
        "| Organismes d'enseignement supérieur | **66%** | 20% du RNI |",
        "| Dons aux partis politiques | 66% | 15 000€/an |",
        "",
    ]

    if impot_actuel > 0:
        don_75_max = 1_000
        reduction_75 = don_75_max * 0.75
        don_66_max = revenu_net_imposable * 0.20 if revenu_net_imposable > 0 else 0
        reduction_66_exemple = 200 * 0.66

        lines += [
            f"### Simulation pour votre situation (impôt actuel : {impot_actuel:,.0f}€)",
            f"- Don 200€ à une asso 75% → réduction : **150€**",
            f"- Don 200€ à une asso 66% → réduction : **132€**",
            f"- Don max eligible 66% : {don_66_max:,.0f}€ (20% de votre RNI)",
            f"  → Réduction max 66% : {don_66_max * 0.66:,.0f}€",
            "",
        ]

    # IFI
    if patrimoine_ifi >= 1_300_000:
        lines += [
            "## 2. Réduction IFI par les dons",
            "",
            "- Dons à certains organismes → réduction **75% de l'IFI** (plafond 50 000€/an)",
            "- Organismes éligibles : fondations reconnues d'utilité publique, ESUS, établissements enseignement supérieur…",
            f"- Votre patrimoine {patrimoine_ifi:,.0f}€ > seuil IFI 1 300 000€ → dispositif applicable",
            "",
        ]

    lines += [
        "## 3. Investissement dans les PME (Réduction IR)",
        "",
        "| Dispositif | Réduction IR | Plafond investissement | Durée blocage |",
        "|-----------|-------------|------------------------|---------------|",
        "| **IR-PME classique** | 18% | 50 000€ (célibataire) / 100 000€ (couple) | 5 ans |",
        "| **IR-PME majoré** (2025) | **25%** | idem | 5 ans |",
        "| **ESUS** (entreprise solidaire) | 25% | idem | 5 ans |",
        "",
        "### Conditions IR-PME",
        "- PME de moins de 7 ans ou secteur innovation",
        "- Souscription au capital lors d'une augmentation de capital",
        "- Pas de garantie ni remboursement pendant 5 ans",
        "- Risque de perte en capital",
        "",
    ]

    if impot_actuel > 0:
        invest_pme = 10_000
        reduction_pme = invest_pme * 0.25
        lines += [
            f"### Exemple : investissement de 10 000€ dans une PME",
            f"- Réduction IR 25% : **{reduction_pme:,.0f}€**",
            f"- Investissement net réel : {invest_pme - reduction_pme:,.0f}€",
            f"- Limite par le montant d'impôt : réduction plafonnée à {impot_actuel:,.0f}€",
            "",
        ]

    lines += [
        "## 4. FIP et FCPI",
        "",
        "| Fonds | Réduction | Investissement max | Éligibilité |",
        "|-------|-----------|-------------------|-------------|",
        "| **FIP** (Fonds d'Investissement de Proximité) | **18%** (25% si FIP Corse/Outre-mer) | 12 000€ / 24 000€ | PME régionales |",
        "| **FCPI** (Fonds Commun de Placement dans l'Innovation) | **18%** (25% temporaire) | 12 000€ / 24 000€ | PME innovantes |",
        "",
        "- Durée de blocage : 5 à 10 ans (généralement 8 ans)",
        "- Liquidité faible — fonds bloqués jusqu'à la dissolution",
        "- Gains à la sortie : exonérés d'IR (mais PS 17.2%)",
        "",
        "## 5. SOFICA (Financement Cinéma)",
        "",
        "- Réduction d'impôt : **30%** des sommes investies (36% si investissement dans la production)",
        "- Plafond : 25% du RNI, maximum 18 000€ d'investissement",
        f"- Réduction max : 18 000€ × 36% = **{18_000 * 0.36:,.0f}€**",
        "- Durée de blocage : 5 à 10 ans",
        "- Disponibles chez certains établissements financiers en fin d'année (oct./nov.)",
        "",
        "## 6. Épargne solidaire (FINANSOL)",
        "- Livrets d'épargne solidaire : une partie de vos intérêts va à des projets solidaires",
        "- CEL/PEL abondé pour logement social — pas de réduction d'IR directe",
        "",
    ]

    if impot_actuel > 0:
        lines += [
            "## Récapitulatif — Réductions maximales pour votre situation",
            "",
            f"| Dispositif | Investissement | Réduction max | Net investissement |",
            f"|-----------|----------------|---------------|-------------------|",
            f"| Don restos du cœur | 1 000€ | {750:,}€ (75%) | 250€ |",
            f"| Don asso 66% | {min(2000, revenu_net_imposable*0.20 if revenu_net_imposable > 0 else 2000):,.0f}€ | {min(2000, revenu_net_imposable*0.20 if revenu_net_imposable > 0 else 2000)*0.66:,.0f}€ | — |",
            f"| PME 25% | 10 000€ | {2_500:,}€ | 7 500€ |",
            f"| SOFICA 36% | 18 000€ | {6_480:,}€ | 11 520€ |",
            f"| FIP/FCPI 25% | 24 000€ | {6_000:,}€ | 18 000€ |",
        ]

    lines += [
        "",
        "## Points de vigilance",
        "- Les réductions d'impôt ne peuvent pas dépasser votre **impôt réellement dû**",
        "- Plafonnement global des niches fiscales : **10 000€/an** (hors outre-mer et SOFICA)",
        "- Risque de perte en capital pour PME, FIP, FCPI",
        "- Vérifiez l'agrément fiscal avant tout investissement",
        "",
        "---",
        "*Source : CGI art. 200, 199 terdecies-0 A, 199 unvicies — BOFiP IR-RICI*",
    ]
    return "\n".join(lines)
# ═══════════════════════════════════════════════════════════════════════════
# GROUP 3 : PV immobilière, Taxe foncière, Réversion pension, Révision déclaration
# ═══════════════════════════════════════════════════════════════════════════

def tool_calculer_pv_immobiliere(args: Dict) -> str:
    """Calcule la plus-value immobilière avec tous les abattements officiels."""
    prix_vente = _valider_revenu(float(args["prix_vente"]), "prix_vente")
    prix_achat = float(args.get("prix_achat", 0))
    frais_achat = float(args.get("frais_achat", 0))         # frais notaire, agence
    travaux_justifies = float(args.get("travaux_justifies", 0))
    duree_detention_ans = int(args.get("duree_detention_ans", 0))
    type_bien = args.get("type_bien", "secondaire")
    primo_accedant_acheteur = bool(args.get("primo_accedant_acheteur", False))

    # Prix de revient
    # Option forfaitaire : +7.5% sur le prix d'achat pour les frais d'acquisition
    # + travaux : réel si justifiés, ou forfait 15% si détention > 5 ans
    frais_achat_retenus = max(frais_achat, prix_achat * 0.075)
    if duree_detention_ans >= 5:
        travaux_retenus = max(travaux_justifies, prix_achat * 0.15)
    else:
        travaux_retenus = travaux_justifies
    prix_revient = prix_achat + frais_achat_retenus + travaux_retenus
    pv_brute = max(0, prix_vente - prix_revient)

    # Abattements pour durée de détention
    # IR : 0% de 0 à 5 ans, 6%/an de 6 à 21 ans, 4% à la 22ème année → exo à 22 ans
    # PS : 0% de 0 à 5 ans, 1.65%/an de 6 à 21 ans, 1.60% à 22 ans, 9%/an de 23 à 30 ans → exo à 30 ans

    def abattement_ir(duree: int) -> float:
        if duree <= 5:
            return 0.0
        elif duree <= 21:
            return min(1.0, (duree - 5) * 0.06)
        elif duree == 22:
            return 0.96 + 0.04  # 96% + 4% = 100%
        else:
            return 1.0

    def abattement_ps(duree: int) -> float:
        if duree <= 5:
            return 0.0
        elif duree <= 21:
            return (duree - 5) * 0.0165
        elif duree == 22:
            return (21 - 5) * 0.0165 + 0.0160
        elif duree <= 29:
            return (21 - 5) * 0.0165 + 0.0160 + (duree - 22) * 0.09
        else:
            return 1.0

    ab_ir = abattement_ir(duree_detention_ans)
    ab_ps = abattement_ps(duree_detention_ans)
    pv_imposable_ir = pv_brute * (1 - ab_ir)
    pv_imposable_ps = pv_brute * (1 - ab_ps)

    ir_pv = pv_imposable_ir * 0.19   # taux fixe 19%
    ps_pv = pv_imposable_ps * 0.172  # PS 17.2%
    total_fiscal = ir_pv + ps_pv
    net = pv_brute - total_fiscal

    # Taxe sur les hautes plus-values (si PV nette > 50 000€)
    def taxe_haute_pv(pv_nette: float) -> float:
        if pv_nette <= 50_000:
            return 0.0
        BAREME_HAUTE_PV = [
            (100_000, 0.02),
            (150_000, 0.03),
            (200_000, 0.04),
            (250_000, 0.05),
            (float("inf"), 0.06),
        ]
        taxe = 0.0
        prev = 50_000
        for seuil, taux in BAREME_HAUTE_PV:
            if pv_nette <= prev:
                break
            tranche = min(pv_nette, seuil) - prev
            taxe += tranche * taux
            prev = seuil
        return taxe

    taxe_hpv = taxe_haute_pv(pv_imposable_ir) if pv_imposable_ir > 50_000 else 0

    lines = [
        "# Plus-Value Immobilière — Calcul Officiel",
        "*(Art. 150 U à 150 VH CGI)*",
        "",
        "## Prix de revient",
        f"| Élément | Montant |",
        f"|---------|---------|",
        f"| Prix d'acquisition | {prix_achat:,.0f}€ |",
        f"| Frais d'acquisition (réel : {frais_achat:,.0f}€ / forfait 7.5% : {prix_achat*0.075:,.0f}€) | **{frais_achat_retenus:,.0f}€** |",
    ]
    if duree_detention_ans >= 5:
        lines.append(f"| Travaux (réel : {travaux_justifies:,.0f}€ / forfait 15% : {prix_achat*0.15:,.0f}€) | **{travaux_retenus:,.0f}€** |")
    else:
        lines.append(f"| Travaux justifiés (< 5 ans : forfait non disponible) | {travaux_retenus:,.0f}€ |")
    lines += [
        f"| **Prix de revient total** | **{prix_revient:,.0f}€** |",
        "",
        f"**Plus-value brute : {prix_vente:,.0f}€ − {prix_revient:,.0f}€ = {pv_brute:,.0f}€**",
        "",
    ]

    # Exonérations
    if type_bien == "residence_principale":
        lines += [
            "## ✅ Exonération — Résidence Principale",
            "La plus-value sur la **résidence principale** est **totalement exonérée**",
            "d'IR et de prélèvements sociaux.",
            "",
            "Conditions :",
            "- Le bien doit être votre résidence principale à la date de la cession",
            "- Ou avoir été votre RP et vendu dans un délai dit 'normal' (1 an) après déménagement",
        ]
        return "\n".join(lines)

    if duree_detention_ans >= 30:
        lines += [
            f"## ✅ Exonération totale — {duree_detention_ans} ans de détention",
            "Exonération d'IR (≥ 22 ans) ET de PS (≥ 30 ans) → **Aucun impôt dû**",
        ]
        return "\n".join(lines)

    lines += [
        "## Abattements pour durée de détention",
        "",
        f"| | IR (19%) | PS (17.2%) |",
        f"|--|----------|-----------|",
        f"| Durée de détention | {duree_detention_ans} ans | {duree_detention_ans} ans |",
        f"| Abattement | **{ab_ir*100:.1f}%** | **{ab_ps*100:.1f}%** |",
        f"| PV imposable | {pv_imposable_ir:,.0f}€ | {pv_imposable_ps:,.0f}€ |",
        f"| Impôt | {ir_pv:,.0f}€ | {ps_pv:,.0f}€ |",
        "",
        "*(Exonération IR totale à 22 ans — Exonération PS totale à 30 ans)*",
        "",
    ]

    if taxe_hpv > 0:
        lines += [
            f"## Taxe sur les hautes plus-values",
            f"PV nette après abattement {pv_imposable_ir:,.0f}€ > 50 000€ → taxe supplémentaire",
            f"- Taxe : **{taxe_hpv:,.0f}€**",
            "",
        ]
        total_fiscal += taxe_hpv

    lines += [
        "## Résultat",
        f"| | Montant |",
        f"|--|---------|",
        f"| Plus-value brute | {pv_brute:,.0f}€ |",
        f"| IR 19% | {ir_pv:,.0f}€ |",
        f"| PS 17.2% | {ps_pv:,.0f}€ |",
    ]
    if taxe_hpv > 0:
        lines.append(f"| Taxe haute PV | {taxe_hpv:,.0f}€ |")
    lines += [
        f"| **Total fiscal** | **{total_fiscal:,.0f}€** ({total_fiscal/pv_brute*100:.1f}% de la PV) |",
        f"| **Net perçu** | **{net:,.0f}€** |",
        "",
    ]

    if primo_accedant_acheteur:
        lines += [
            "## Exonération primo-accédant",
            "Si l'acheteur est un primo-accédant (ou un organisme HLM), une exonération partielle",
            "ou totale peut s'appliquer sous conditions — à vérifier avec le notaire.",
            "",
        ]

    # Tableau d'abattements complet
    lines += [
        "## Tableau des abattements par durée",
        "",
        "| Année | Abatt. IR cumulé | Abatt. PS cumulé |",
        "|-------|-----------------|-----------------|",
    ]
    for yr in [5, 6, 10, 15, 20, 21, 22, 25, 28, 30]:
        ab_i = abattement_ir(yr)
        ab_p = abattement_ps(yr)
        exo_i = "✅ Exo" if ab_i >= 1.0 else f"{ab_i*100:.0f}%"
        exo_p = "✅ Exo" if ab_p >= 1.0 else f"{ab_p*100:.1f}%"
        lines.append(f"| {yr} ans | {exo_i} | {exo_p} |")

    lines += [
        "",
        "---",
        "*Source : CGI art. 150 U, 150 VC, 150 VD, 1609 nonies G — BOFiP RFPI-PVI*",
    ]
    return "\n".join(lines)


def tool_guide_taxe_fonciere(args: Dict) -> str:
    """Guide de la taxe foncière : calcul, exonérations, plafonnement, recours."""
    valeur_locative_brute = float(args.get("valeur_locative_brute", 0))
    taux_commune = float(args.get("taux_commune_pct", 25))
    taux_departement = float(args.get("taux_departement_pct", 10))
    rni = float(args.get("revenu_net_imposable", 0))
    nb_parts = float(args.get("nb_parts", 1.0))
    type_bien = args.get("type_bien", "bati")
    annee_construction = int(args.get("annee_construction", 0))
    logement_neuf = bool(args.get("logement_neuf", False))
    personne_agee_modeste = bool(args.get("personne_agee_modeste", False))

    lines = [
        "# Taxe Foncière — Guide Complet 2025",
        "",
        "## Principes",
        "- **Taxe foncière sur propriétés bâties (TFPB)** : immeubles, maisons, appartements, dépendances",
        "- **Taxe foncière sur propriétés non bâties (TFPNB)** : terrains, terres agricoles",
        "- Due par le **propriétaire** au 1er janvier de l'année d'imposition",
        "- Payée même si le bien est loué (le bailleur peut refacturer une partie au locataire)",
        "",
        "## Calcul de la taxe foncière",
        "",
        "```",
        "Base = Valeur locative cadastrale brute × 50% (abattement légal)",
        "TF = Base × (Taux commune + Taux intercommunalité + Taux département)",
        "```",
        "",
    ]

    if valeur_locative_brute > 0:
        base = valeur_locative_brute * 0.50
        tf_commune = base * taux_commune / 100
        tf_dpt = base * taux_departement / 100
        tf_total = tf_commune + tf_dpt
        lines += [
            f"## Simulation",
            f"| Élément | Montant |",
            f"|---------|---------|",
            f"| Valeur locative cadastrale brute | {valeur_locative_brute:,.0f}€ |",
            f"| Abattement légal 50% | -{valeur_locative_brute*0.50:,.0f}€ |",
            f"| Base nette d'imposition | {base:,.0f}€ |",
            f"| Taux commune ({taux_commune}%) | {tf_commune:,.0f}€ |",
            f"| Taux département ({taux_departement}%) | {tf_dpt:,.0f}€ |",
            f"| **Taxe foncière estimée** | **{tf_total:,.0f}€** |",
            "",
        ]
        # Plafonnement
        if rni > 0:
            plafond_tf = rni * 0.50  # TF ne peut dépasser 50% du RNI (art. 1391 B ter)
            if tf_total > plafond_tf:
                degrevement = tf_total - plafond_tf
                lines += [
                    f"### ⚠️ Plafonnement possible (Art. 1391 B ter)",
                    f"TF {tf_total:,.0f}€ > 50% du RNI {rni:,.0f}€ = {plafond_tf:,.0f}€",
                    f"→ Dégrèvement potentiel : **{degrevement:,.0f}€**",
                    "(À demander auprès du centre des impôts — conditions de ressources à vérifier)",
                    "",
                ]

    lines += [
        "## Exonérations et dégrèvements",
        "",
        "### Exonérations permanentes",
        "| Cas | Condition |",
        "|-----|-----------|",
        "| Bâtiments ruraux affectés à usage agricole | Usage exclusif agricole |",
        "| Propriétés publiques | Affectation à un service public |",
        "| Édifices religieux | Culte reconnu |",
        "",
        "### Exonérations temporaires",
        "| Cas | Durée | Condition |",
        "|-----|-------|-----------|",
        "| Construction neuve (résidence principale) | **2 ans** | Déclaration H1 dans les 90 jours |",
        "| Construction neuve (locatif) | **2 ans** | Déclaration H2 |",
        "| Logement social, HLM | Longue durée | Sous convention |",
        "| Logement rénové économies d'énergie | 3 à 5 ans | Sur délibération commune |",
        "| Zone de Revitalisation Rurale (ZRR) | Variable | Sur délibération |",
        "",
    ]

    if logement_neuf:
        lines += [
            "### ✅ Votre logement neuf",
            "- Exonération de taxe foncière pendant **2 ans** à compter de la fin des travaux",
            "- Déposez la **déclaration H1** (résidence principale) ou **H2** (autre) dans les 90 jours",
            "  suivant l'achèvement de la construction auprès du centre des impôts",
            "",
        ]

    if personne_agee_modeste:
        lines += [
            "### Exonérations personnes âgées/modestes",
            "**Exonération totale** si vous remplissez TOUTES ces conditions :",
            "- Âge ≥ 75 ans au 1er janvier de l'année d'imposition",
            "- Occupez le bien à titre de résidence principale",
            "- RFR ≤ 12 455€ (1ère part) + 3 328€ par demi-part supplémentaire (2024)",
            "",
            "**Dégrèvement de 100€** (art. 1391 B ter) si :",
            "- Âge ≥ 65 ans et < 75 ans",
            "- Mêmes conditions de ressources",
            "",
        ]

    lines += [
        "## Taxe sur les logements vacants (TLV)",
        "- Applicable dans les communes de > 50 000 habitants en zone tendue",
        "- Logement vacant depuis > 1 an : **17% la 1ère année**, **34% les années suivantes**",
        "- Calculée sur la valeur locative du bien",
        "",
        "## Taxe d'habitation sur résidences secondaires (THRS)",
        "- La TH principale a été supprimée pour toutes les RP en 2023",
        "- La **THRS sur résidences secondaires** reste due à 100%",
        "- Certaines communes peuvent majorer la THRS de 5% à 60%",
        "",
        "## Comment contester sa taxe foncière ?",
        "1. **Réclamation contentieuse** : avant le 31 déc. de l'année suivant la mise en recouvrement",
        "2. **Motifs** : erreur sur la surface, valeur locative excessive, bien démoli, exonération oubliée",
        "3. **Demande gracieuse** : difficultés financières exceptionnelles",
        "4. **En ligne** : espace particulier sur impots.gouv.fr → « Gérer mes biens immobiliers »",
        "",
        "---",
        "*Source : CGI art. 1380 à 1391 D — Instruction fiscale BOFiP IF-TFB*",
    ]
    return "\n".join(lines)


def tool_simuler_reversion_pension(args: Dict) -> str:
    """Simule la pension de réversion : calcul, conditions, cumul, fiscalité."""
    pension_defunt = float(args.get("pension_annuelle_defunt", 0))
    pension_propre = float(args.get("pension_personnelle_beneficiaire", 0))
    age_beneficiaire = int(args.get("age_beneficiaire", 55))
    revenu_brut_annuel = float(args.get("revenus_annuels_beneficiaire", 0))
    situation_beneficiaire = args.get("situation_beneficiaire", "veuf")
    nb_enfants = int(args.get("nb_enfants", 0))
    regime = args.get("regime_defunt", "general")

    # Taux de réversion par régime
    TAUX_REVERSION = {
        "general": 0.54,        # CNAV (régime général)
        "agirc_arrco": 0.60,    # AGIRC-ARRCO (retraite complémentaire)
        "fonctionnaire": 0.50,  # CNRACL / FPE
        "independant": 0.54,    # SSI (ex-RSI)
        "liberal": 0.60,        # CIPAV
    }

    taux = TAUX_REVERSION.get(regime, 0.54)
    reversion_brute = pension_defunt * taux

    # Plafond de ressources pour régime général
    # RFR plafond 2025 : 24 232€ (célibataire veuf) = 1.6 SMIC mensuel × 12
    PLAFOND_RFR_SEUL = 24_232
    PLAFOND_RFR_COUPLE = 38_771

    # Ressources prises en compte (régime général)
    rfr_prise_en_compte = revenu_brut_annuel + reversion_brute
    if situation_beneficiaire in ["remarie", "concubinage"]:
        plafond = PLAFOND_RFR_COUPLE
    else:
        plafond = PLAFOND_RFR_SEUL

    # Calcul écrêtement
    if rfr_prise_en_compte > plafond and regime == "general":
        depassement = rfr_prise_en_compte - plafond
        reversion_servie = max(0, reversion_brute - depassement)
        ecrêtement = True
    else:
        reversion_servie = reversion_brute
        ecrêtement = False

    # Fiscalité
    pension_totale = pension_propre + reversion_servie
    abatt_retraite_min = 422
    abatt_retraite_max = 4_321
    abatt = max(abatt_retraite_min, min(abatt_retraite_max, pension_totale * 0.10))
    rni_retraite = max(0, pension_totale - abatt)
    nb_parts_ir = calculer_parts("veuf" if situation_beneficiaire == "veuf" else "celibataire", nb_enfants)
    ir_estime = calculer_ir(rni_retraite, nb_parts_ir)["impot_net"]

    lines = [
        "# Pension de Réversion",
        f"*(Régime : {regime.replace('_', ' ').title()})*",
        "",
        "## Qu'est-ce que la pension de réversion ?",
        "- Part de la retraite du défunt versée au conjoint survivant",
        "- **Pas automatique** : demande à effectuer auprès des caisses de retraite",
        "",
        "## Conditions d'accès",
        "",
        "| Régime | Âge minimum | Condition ressources | Remariage |",
        "|--------|-------------|---------------------|-----------|",
        "| **Régime général (CNAV)** | 55 ans | Oui (plafond RFR) | Autorisé (ressources prises en compte) |",
        "| **AGIRC-ARRCO** | Pas d'âge minimum | **Non** | Autorisé sans impact |",
        "| **Fonctionnaire (CNRACL/FPE)** | Pas d'âge min. | Non | Suppression si remariage |",
        "| **SSI (indépendants)** | 55 ans | Oui | Autorisé |",
        "",
    ]

    if age_beneficiaire < 55 and regime in ["general", "independant"]:
        lines += [
            f"⚠️ Vous avez {age_beneficiaire} ans — La réversion au régime général nécessite **55 ans minimum**",
            f"   → Vous pourrez en bénéficier dans {55 - age_beneficiaire} an(s)",
            "",
        ]

    lines += [
        "## Calcul de votre réversion",
        "",
        f"| Élément | Montant |",
        f"|---------|---------|",
        f"| Pension annuelle du défunt | {pension_defunt:,.0f}€ |",
        f"| Taux de réversion ({regime}) | **{taux*100:.0f}%** |",
        f"| Réversion brute | {reversion_brute:,.0f}€/an ({reversion_brute/12:,.0f}€/mois) |",
    ]

    if regime == "general" and ecrêtement:
        lines += [
            f"| Plafond ressources | {plafond:,}€/an |",
            f"| Vos ressources + réversion | {rfr_prise_en_compte:,.0f}€ |",
            f"| Dépassement → écrêtement | -{reversion_brute - reversion_servie:,.0f}€ |",
            f"| **Réversion servie réellement** | **{reversion_servie:,.0f}€/an ({reversion_servie/12:,.0f}€/mois)** |",
        ]
    elif regime == "general":
        lines += [
            f"| Plafond ressources | {plafond:,}€/an |",
            f"| Vos ressources + réversion | {rfr_prise_en_compte:,.0f}€ ✅ Dans les limites |",
            f"| **Réversion servie** | **{reversion_servie:,.0f}€/an ({reversion_servie/12:,.0f}€/mois)** |",
        ]
    else:
        lines.append(f"| **Réversion servie** | **{reversion_servie:,.0f}€/an ({reversion_servie/12:,.0f}€/mois)** |")

    if pension_propre > 0:
        lines += [
            "",
            "## Cumul avec votre propre pension",
            f"| | Annuel | Mensuel |",
            f"|--|-------|---------|",
            f"| Votre pension | {pension_propre:,.0f}€ | {pension_propre/12:,.0f}€ |",
            f"| Réversion | {reversion_servie:,.0f}€ | {reversion_servie/12:,.0f}€ |",
            f"| **Total brut** | **{pension_totale:,.0f}€** | **{pension_totale/12:,.0f}€** |",
            "",
            f"**Fiscalité :** abattement 10% ({abatt:,.0f}€) → RNI {rni_retraite:,.0f}€ → IR ~{ir_estime:,.0f}€",
        ]

    lines += [
        "",
        "## Comment faire la demande ?",
        "1. **Régime général** : sur retraite.fr ou à la CARSAT",
        "   - Documents : acte de mariage, acte de décès, justificatifs de ressources",
        "2. **AGIRC-ARRCO** : sur agirc-arrco.fr ou auprès de la caisse complémentaire",
        "3. **Fonctionnaires** : auprès du service des retraites de l'État ou CNRACL",
        "",
        "## Majoration pour enfants",
        "- Si vous avez élevé ≥ 3 enfants : majoration de **10%** de la pension de réversion",
        "",
        "## Délai de versement",
        "- Régime général : rétroactive à compter du 1er jour du mois suivant le décès",
        "  si demande dans les 12 mois, sinon à compter du dépôt de la demande",
        "",
        "---",
        "*Source : Art. L353-1 à L353-6 CSS — Décret n°2004-1384*",
    ]
    return "\n".join(lines)


def tool_guide_revision_declaration(args: Dict) -> str:
    """Guide pour corriger une déclaration fiscale : délais, procédures, pénalités."""
    annee_concernee = int(args.get("annee_declaration", 2025))
    type_erreur = args.get("type_erreur", "omission_deduction")
    montant_erreur = float(args.get("montant_impact_estime", 0))
    declaration_deja_soumise = bool(args.get("declaration_deja_soumise", True))

    annee_revenus = annee_concernee - 1
    annee_actuelle = 2026

    # Délais de réclamation
    # Réclamation contentieuse : 31 décembre de la 2ème année suivant la mise en recouvrement
    # Mise en recouvrement ≈ septembre de l'année de déclaration
    annee_fin_reclamation = annee_concernee + 2

    lines = [
        "# Révision de Déclaration Fiscale",
        f"*(Déclaration {annee_concernee} — Revenus {annee_revenus})*",
        "",
        "## Délais de réclamation et correction",
        "",
        "| Procédure | Délai limite | Objectif |",
        "|-----------|-------------|----------|",
        f"| **Déclaration rectificative** (en ligne) | Jusqu'au **15 décembre {annee_concernee}** | Corriger avant avis d'imposition |",
        f"| **Réclamation contentieuse** | Jusqu'au **31 décembre {annee_fin_reclamation}** | Obtenir un dégrèvement après AI |",
        f"| **Demande gracieuse** | Pas de délai strict | Difficultés financières |",
        f"| **Remise en cause par l'administration** | Jusqu'au **31 décembre {annee_concernee + 3}** | Prescription du contrôle fiscal |",
        "",
    ]

    if annee_fin_reclamation < annee_actuelle:
        lines += [
            f"⚠️ **Délai de réclamation expiré** : la période de réclamation pour {annee_concernee} s'est terminée le 31/12/{annee_fin_reclamation}",
            "",
        ]
    elif annee_concernee < annee_actuelle:
        lines += [
            f"✅ **Réclamation encore possible** jusqu'au 31 décembre {annee_fin_reclamation}",
            "",
        ]

    lines += [
        "## Comment corriger selon le cas",
        "",
    ]

    procedures = {
        "omission_deduction": {
            "titre": "Oubli d'une déduction ou d'un crédit d'impôt",
            "demarche": [
                "→ **En ligne** (si déclaration < 15 déc.) : impots.gouv.fr → « Corriger ma déclaration »",
                "→ **Après l'avis d'imposition** : réclamation contentieuse par messagerie sécurisée",
                "  ou courrier au Service des Impôts des Particuliers (SIP)",
                "Pièces justificatives : reçus de dons, factures travaux, attestation PER…",
                "Résultat attendu : remboursement de trop-perçu + intérêts moratoires 2.4%/an",
            ]
        },
        "revenu_omis": {
            "titre": "Revenu non déclaré (oubli involontaire)",
            "demarche": [
                "→ **Correction spontanée** fortement recommandée (réduit les pénalités)",
                "→ En ligne avant le 15 décembre ou déclaration rectificative papier",
                "⚠️ Si l'administration détecte l'omission : majoration 10% (bonne foi) à 40% (manquement délibéré)",
                "Intérêts de retard : 0.20%/mois (soit 2.4%/an)",
                "Divulgation spontanée : majoration généralement limitée à 10%",
            ]
        },
        "erreur_situation_famille": {
            "titre": "Erreur sur la situation de famille ou le nombre d'enfants",
            "demarche": [
                "→ Corriger en ligne ou par réclamation contentieuse",
                "→ Joindre : acte de naissance, jugement de divorce, acte de PACS, attestation garde alternée",
                "Impact : modification du nombre de parts → recalcul complet de l'impôt",
            ]
        },
        "autre": {
            "titre": "Autre type d'erreur",
            "demarche": [
                "→ Identifier la case erronée dans votre déclaration",
                "→ Corriger en ligne ou par réclamation avec pièces justificatives",
            ]
        }
    }

    proc = procedures.get(type_erreur, procedures["autre"])
    lines += [
        f"### {proc['titre']}",
    ]
    for etape in proc["demarche"]:
        lines.append(etape)

    if montant_erreur > 0:
        interets_retard_annuel = montant_erreur * 0.024
        lines += [
            "",
            f"### Impact estimé",
            f"- Montant en jeu : {montant_erreur:,.0f}€",
            f"- Intérêts de retard si redressement : {interets_retard_annuel:,.0f}€/an (2.4%/an)",
        ]

    lines += [
        "",
        "## Prescription fiscale",
        "",
        "| Situation | Délai de reprise de l'administration |",
        "|-----------|--------------------------------------|",
        "| Cas général | **3 ans** (jusqu'au 31 déc. N+3) |",
        "| Activités occultes / fraude | **6 ans** |",
        "| Avoirs non déclarés à l'étranger | **10 ans** |",
        "| Infractions pénales | Imprescriptible |",
        "",
        "## Intérêts de retard et majorations",
        "",
        "| Situation | Majoration |",
        "|-----------|-----------|",
        "| Erreur involontaire (bonne foi) | 10% + intérêts 2.4%/an |",
        "| Retard de paiement (sans majoration) | Intérêts 2.4%/an seulement |",
        "| Manquement délibéré | **40%** + intérêts |",
        "| Manœuvres frauduleuses | **80%** + intérêts |",
        "| Activités occultes | **80%** + intérêts |",
        "",
        "## Recours en cas de désaccord",
        "1. **Réclamation** auprès du SIP (premier niveau)",
        "2. **Interlocuteur départemental** si désaccord avec le SIP",
        "3. **Tribunal administratif** si désaccord persistant (délai 2 ans après décision de rejet)",
        "4. **Médiateur des ministères économiques et financiers** : médiation amiable",
        "",
        "## Contact",
        "- En ligne : impots.gouv.fr → Espace particulier → Messagerie sécurisée",
        "- Par téléphone : 0809 401 401 (numéro non surtaxé)",
        "- En rendez-vous : SIP de votre département",
        "",
        "---",
        "*Source : LPF art. L190, L196 A — CGI art. 1727, 1728, 1729*",
    ]
    return "\n".join(lines)


# ─── Outils 2.6.0 ────────────────────────────────────────────────────────────

def tool_comparer_statuts_professionnel(args: Dict) -> str:
    """Compare CDI vs statuts independants : AE, SASU, EURL IS, portage salarial."""
    salaire_brut_cdi = float(args.get("salaire_brut_annuel_cdi", 0))
    tjm = float(args.get("tjm_freelance", 0))
    jours = int(args.get("jours_travailles_an", 200))
    ca_direct = float(args.get("ca_annuel", 0))
    type_activite = args.get("type_activite", "services_bnc")
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    charges_pro = float(args.get("charges_pro_annuelles", 0))

    nb_parts = calculer_parts(situation, nb_enfants)

    ACTIVITES_PARAMS = {
        "services_bnc": {"label": "Professions liberales / BNC (conseil, IT, sante...)", "taux_ae_cotis": 0.231, "abatt_ae_ir": 0.34, "seuil_ae": 77_700},
        "services_bic": {"label": "Prestations de services BIC (artisan, commerce)", "taux_ae_cotis": 0.214, "abatt_ae_ir": 0.50, "seuil_ae": 77_700},
        "vente_marchandises": {"label": "Vente de marchandises / hebergement", "taux_ae_cotis": 0.128, "abatt_ae_ir": 0.71, "seuil_ae": 188_700},
    }
    act = ACTIVITES_PARAMS.get(type_activite, ACTIVITES_PARAMS["services_bnc"])

    ca = ca_direct if ca_direct > 0 else (tjm * jours if tjm > 0 else 0)

    # ── Simulation CDI ────────────────────────────────────────────────────────
    def simuler_cdi(brut: float) -> Dict:
        if brut <= 0:
            return {}
        net_salarie = brut * 0.78        # charges salariales ~22%
        cout_employeur = brut * 1.42     # charges patronales ~42%
        abatt = min(14_426, max(495, net_salarie * 0.10))
        rni = max(0, net_salarie - abatt)
        res_ir = calculer_ir(rni, nb_parts)
        ir = res_ir["impot_net"]
        return {
            "brut": round(brut),
            "cout_employeur": round(cout_employeur),
            "net_salarie": round(net_salarie),
            "rni": round(rni),
            "ir": round(ir),
            "net_final": round(net_salarie - ir),
            "tmi": res_ir["taux_marginal"],
            "ratio_net_cout": round((net_salarie - ir) / cout_employeur * 100, 1),
        }

    # ── Simulation Auto-Entrepreneur ──────────────────────────────────────────
    def simuler_ae(ca_val: float) -> Dict:
        if ca_val <= 0:
            return {}
        cotisations = ca_val * act["taux_ae_cotis"]
        net_cotis = ca_val - cotisations
        rni = max(0, ca_val * (1 - act["abatt_ae_ir"]))
        res_ir = calculer_ir(rni, nb_parts)
        ir = res_ir["impot_net"]
        net_final = net_cotis - ir
        return {
            "ca": round(ca_val),
            "cotisations": round(cotisations),
            "rni": round(rni),
            "ir": round(ir),
            "net_final": round(net_final),
            "ratio_net_ca": round(net_final / ca_val * 100, 1) if ca_val > 0 else 0,
            "hors_seuil": ca_val > act["seuil_ae"],
        }

    # ── Simulation SASU (remuneration SMIC + dividendes PFU) ─────────────────
    def simuler_sasu(ca_val: float) -> Dict:
        if ca_val <= 0:
            return {}
        SMIC_BRUT = 21_622  # 2025
        # President assimile salarie : patronales ~55%, salariales ~23%
        cout_salarial = round(SMIC_BRUT * 1.55)
        net_smic = round(SMIC_BRUT * 0.77)
        is_base = max(0, ca_val - charges_pro - cout_salarial)
        is_total = round(min(is_base, 42_500) * 0.15 + max(0, is_base - 42_500) * 0.25)
        dividendes_bruts = max(0, is_base - is_total)
        net_dividendes = round(dividendes_bruts * 0.70)
        abatt = min(14_426, max(495, net_smic * 0.10))
        ir_smic = calculer_ir(max(0, net_smic - abatt), nb_parts)["impot_net"]
        net_final = net_smic - round(ir_smic) + net_dividendes
        return {
            "ca": round(ca_val),
            "cout_salarial": cout_salarial,
            "is_base": round(is_base),
            "is_total": is_total,
            "dividendes_bruts": round(dividendes_bruts),
            "net_dividendes": net_dividendes,
            "net_smic": net_smic,
            "ir_smic": round(ir_smic),
            "net_final": net_final,
            "ratio_net_ca": round(net_final / ca_val * 100, 1) if ca_val > 0 else 0,
        }

    # ── Simulation EURL IS (gerant majoritaire TNS) ───────────────────────────
    def simuler_eurl(ca_val: float) -> Dict:
        if ca_val <= 0:
            return {}
        benefice = max(0, ca_val - charges_pro)
        # Optimisation : gerant verse ~65% du benefice en remuneration
        remun_brute = round(benefice * 0.65)
        # Cotisations TNS ≈ 30.5% de la remuneration brute (assiette IS)
        cotis_tns = round(remun_brute * 0.305)
        net_remun = remun_brute - cotis_tns
        is_base = max(0, benefice - remun_brute - cotis_tns)
        is_total = round(min(is_base, 42_500) * 0.15 + max(0, is_base - 42_500) * 0.25)
        dividendes_bruts = max(0, is_base - is_total)
        net_dividendes = round(dividendes_bruts * 0.70)
        ir_remun = round(calculer_ir(net_remun, nb_parts)["impot_net"])
        net_final = net_remun - ir_remun + net_dividendes
        return {
            "ca": round(ca_val),
            "remun_brute": remun_brute,
            "cotis_tns": cotis_tns,
            "net_remun": net_remun,
            "is_base": round(is_base),
            "is_total": is_total,
            "net_dividendes": net_dividendes,
            "ir_remun": ir_remun,
            "net_final": net_final,
            "ratio_net_ca": round(net_final / ca_val * 100, 1) if ca_val > 0 else 0,
        }

    # ── Simulation Portage salarial ───────────────────────────────────────────
    def simuler_portage(ca_val: float) -> Dict:
        if ca_val <= 0:
            return {}
        frais_gestion = round(ca_val * 0.08)
        base = ca_val - frais_gestion
        salaire_brut = round(base / 1.42)
        net_salarie = round(salaire_brut * 0.78)
        abatt = min(14_426, max(495, net_salarie * 0.10))
        rni = max(0, net_salarie - abatt)
        ir = round(calculer_ir(rni, nb_parts)["impot_net"])
        net_final = net_salarie - ir
        return {
            "ca": round(ca_val),
            "frais_gestion": frais_gestion,
            "salaire_brut": salaire_brut,
            "net_salarie": net_salarie,
            "ir": ir,
            "net_final": net_final,
            "ratio_net_ca": round(net_final / ca_val * 100, 1) if ca_val > 0 else 0,
        }

    # ── TJM d'equivalence (recherche dichotomique) ────────────────────────────
    def tjm_equivalence(net_cdi: float, statut: str) -> int:
        if net_cdi <= 0 or jours <= 0:
            return 0
        lo, hi = 0.0, 10_000.0
        for _ in range(60):
            mid = (lo + hi) / 2
            ca_t = mid * jours
            if statut == "ae":
                cotis = ca_t * act["taux_ae_cotis"]
                rni = max(0, ca_t * (1 - act["abatt_ae_ir"]))
                net = ca_t - cotis - calculer_ir(rni, nb_parts)["impot_net"]
            elif statut == "sasu":
                net = simuler_sasu(ca_t).get("net_final", 0)
            elif statut == "eurl":
                net = simuler_eurl(ca_t).get("net_final", 0)
            else:  # portage
                net = simuler_portage(ca_t).get("net_final", 0)
            if net < net_cdi:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2)

    # ── Assemblage ────────────────────────────────────────────────────────────
    lines = [
        "# Comparaison Statuts Professionnels : CDI vs Independant",
        "",
        f"*Simulation indicative — Bareme {ANNEE_FISCALE}*",
        "",
        "## Parametres",
        "",
    ]
    if salaire_brut_cdi > 0:
        lines.append(f"- Salaire brut CDI : {salaire_brut_cdi:,.0f} EUR/an")
    if ca > 0:
        desc_ca = f"{tjm:.0f} EUR/j x {jours} j" if tjm > 0 and ca_direct == 0 else "CA direct"
        lines.append(f"- CA freelance : {ca:,.0f} EUR/an ({desc_ca})")
    lines += [
        f"- Activite : {act['label']}",
        f"- Situation : {situation}, {nb_enfants} enfant(s) — {nb_parts:.1f} part(s) fiscale(s)",
        "",
    ]

    cdi_res = simuler_cdi(salaire_brut_cdi)
    if cdi_res:
        lines += [
            "## CDI / Salarie",
            "",
            "| Indicateur | Montant |",
            "|-----------|---------|",
            f"| Salaire brut | {cdi_res['brut']:,} EUR |",
            f"| Cout employeur total | {cdi_res['cout_employeur']:,} EUR |",
            f"| Net salarie (apres charges) | {cdi_res['net_salarie']:,} EUR |",
            f"| Revenu net imposable | {cdi_res['rni']:,} EUR |",
            f"| Impot sur le revenu | {cdi_res['ir']:,} EUR |",
            f"| **Net en poche** | **{cdi_res['net_final']:,} EUR** |",
            f"| Ratio net / cout employeur | {cdi_res['ratio_net_cout']} % |",
            f"| Taux marginal (TMI) | {cdi_res['tmi']:.0f} % |",
            "",
            "Protection sociale : chomage, maladie, retraite, prevoyance — couverture complete.",
            "",
        ]

    if ca > 0:
        ae_r = simuler_ae(ca)
        sasu_r = simuler_sasu(ca)
        eurl_r = simuler_eurl(ca)
        port_r = simuler_portage(ca)

        lines += [
            "## Comparatif des statuts independants",
            f"*(CA annuel HT : {ca:,.0f} EUR)*",
            "",
            "| Statut | Net en poche | Net / CA | Protection sociale |",
            "|--------|-------------|----------|--------------------|",
            f"| Auto-entrepreneur | {ae_r['net_final']:,} EUR | {ae_r['ratio_net_ca']} % | Minimale (SSI) |",
            f"| SASU — SMIC + dividendes | {sasu_r['net_final']:,} EUR | {sasu_r['ratio_net_ca']} % | Assimile salarie |",
            f"| EURL a l'IS | {eurl_r['net_final']:,} EUR | {eurl_r['ratio_net_ca']} % | TNS (SSI) |",
            f"| Portage salarial | {port_r['net_final']:,} EUR | {port_r['ratio_net_ca']} % | Salarie complete |",
        ]
        if cdi_res:
            lines.append(f"| CDI (reference) | {cdi_res['net_final']:,} EUR | — | Complete |")
        lines.append("")

        if ae_r.get("hors_seuil"):
            lines.append(f"Note : CA {ca:,.0f} EUR depasse le seuil AE ({act['seuil_ae']:,} EUR). Le statut AE n'est pas applicable.")
            lines.append("")

        lines += [
            "### Detail Auto-Entrepreneur",
            "",
            "| Poste | Montant |",
            "|-------|---------|",
            f"| CA annuel HT | {ae_r['ca']:,} EUR |",
            f"| Cotisations sociales ({act['taux_ae_cotis']*100:.1f} %) | {ae_r['cotisations']:,} EUR |",
            f"| Revenu imposable (abatt. {int((1-act['abatt_ae_ir'])*100)} %) | {ae_r['rni']:,} EUR |",
            f"| Impot sur le revenu | {ae_r['ir']:,} EUR |",
            f"| Net en poche | {ae_r['net_final']:,} EUR |",
            "",
            "### Detail SASU",
            "*(Remuneration SMIC + dividendes soumis PFU 30 %)*",
            "",
            "| Poste | Montant |",
            "|-------|---------|",
            f"| CA | {sasu_r['ca']:,} EUR |",
            f"| Cout salarial SMIC (pres. assimile) | {sasu_r['cout_salarial']:,} EUR |",
            f"| Base IS | {sasu_r['is_base']:,} EUR |",
            f"| IS (15 % / 25 %) | {sasu_r['is_total']:,} EUR |",
            f"| Dividendes nets (PFU 30 %) | {sasu_r['net_dividendes']:,} EUR |",
            f"| Net salaire SMIC | {sasu_r['net_smic']:,} EUR |",
            f"| Net en poche | {sasu_r['net_final']:,} EUR |",
            "",
            "### Detail EURL a l'IS",
            "*(Remuneration 65 % du benefice + dividendes PFU 30 %)*",
            "",
            "| Poste | Montant |",
            "|-------|---------|",
            f"| CA | {eurl_r['ca']:,} EUR |",
            f"| Remuneration brute gerant | {eurl_r['remun_brute']:,} EUR |",
            f"| Cotisations TNS (~30.5 %) | {eurl_r['cotis_tns']:,} EUR |",
            f"| Net remuneration | {eurl_r['net_remun']:,} EUR |",
            f"| IR sur remuneration | {eurl_r['ir_remun']:,} EUR |",
            f"| IS (15 % / 25 %) | {eurl_r['is_total']:,} EUR |",
            f"| Net dividendes (PFU 30 %) | {eurl_r['net_dividendes']:,} EUR |",
            f"| Net en poche | {eurl_r['net_final']:,} EUR |",
            "",
            "### Detail Portage salarial",
            "*(Frais de gestion 8 % + charges salariales classiques)*",
            "",
            "| Poste | Montant |",
            "|-------|---------|",
            f"| CA | {port_r['ca']:,} EUR |",
            f"| Frais de gestion (8 %) | {port_r['frais_gestion']:,} EUR |",
            f"| Salaire brut | {port_r['salaire_brut']:,} EUR |",
            f"| Net salarie | {port_r['net_salarie']:,} EUR |",
            f"| Impot sur le revenu | {port_r['ir']:,} EUR |",
            f"| Net en poche | {port_r['net_final']:,} EUR |",
            "",
        ]

    if cdi_res and jours > 0:
        net_cdi = cdi_res["net_final"]
        lines += [
            "## TJM minimum pour egaler le net CDI",
            f"*(Base : {jours} jours factures/an — CDI net de reference : {net_cdi:,} EUR)*",
            "",
            "| Statut | TJM minimum | CA annuel equivalent |",
            "|--------|------------|---------------------|",
        ]
        for key, label in [("ae", "Auto-entrepreneur"), ("sasu", "SASU"), ("eurl", "EURL IS"), ("portage", "Portage salarial")]:
            tjm_eq = tjm_equivalence(net_cdi, key)
            lines.append(f"| {label} | {tjm_eq:,} EUR/j | {tjm_eq * jours:,} EUR/an |")
        lines.append("")

    lines += [
        "## Synthese et recommandations",
        "",
        "### Avantages du passage en independant",
        "- Net potentiellement superieur car le cout employeur devient du CA facturable",
        "- Deductions professionnelles etendues (materiel, bureau, formation, vehicule...)",
        "- Optimisation IS + dividendes possible en SASU/EURL des que le CA depasse ~60 000 EUR",
        "- Flexibilite sur les missions, les clients, le rythme de travail",
        "",
        "### Risques et contraintes",
        "- Pas d'assurance chomage en AE / EURL (sauf portage ou option SASU specifique)",
        "- Retraite : droits plus faibles en TNS — compenser via PER ou assurance-vie",
        "- Irrégularite des revenus : constituer 3 a 6 mois de tresorerie de securite",
        "- Frais de structure : expert-comptable (~1 500 a 2 500 EUR/an pour SASU/EURL)",
        "- Delai de carence IJSS maladie : 3 jours en TNS vs 0 en salarie",
        "",
        "### Quel statut selon le CA ?",
        "",
        "| Fourchette CA | Statut recommande | Raison |",
        "|---------------|-------------------|--------|",
        f"| < {act['seuil_ae']:,} EUR | Auto-entrepreneur | Simplicite, zero comptabilite |",
        f"| {act['seuil_ae']:,} – 100 000 EUR | EURL IS ou SASU | Optimisation IS + protection |",
        "| > 100 000 EUR | SASU | IS reduit, protection assimile salarie, image professionnelle |",
        "| Transition / missions courtes | Portage salarial | Securite, pas de creation de societe |",
        "",
        "---",
        "*Simulation basee sur les taux 2025. Les taux de cotisations sont approximatifs.*",
        "*Consultez un expert-comptable avant toute decision de changement de statut.*",
    ]
    return "\n".join(lines)


def tool_verifier_actualite_fiscale(args: Dict) -> str:
    """Liste les baremes et donnees fiscales integres au MCP et signale ce qui necessite une mise a jour."""
    annee_cible = int(args.get("annee_cible", 2026))
    annee_actuelle_mcp = 2026   # annee de reference du MCP (mettre a jour a chaque release)
    annee_revenus_mcp = annee_actuelle_mcp - 1

    lines = [
        "# Verification Actualite Fiscale du MCP",
        "",
        f"**Annee fiscale couverte par ce MCP** : {ANNEE_FISCALE}",
        f"**Annee cible demandee** : {annee_cible} (revenus {annee_cible - 1})",
        "",
    ]

    if annee_cible == annee_actuelle_mcp:
        lines += [
            "Statut : **Le MCP est a jour** pour cette annee fiscale.",
            "",
        ]
    elif annee_cible < annee_actuelle_mcp:
        lines += [
            f"Statut : L'annee {annee_cible} est anterieure a la version actuelle du MCP ({annee_actuelle_mcp}).",
            "Les donnees historiques peuvent etre consultees mais les baremes actuels s'appliquent.",
            "",
        ]
    else:
        delta = annee_cible - annee_actuelle_mcp
        lines += [
            f"Statut : **Mise a jour requise** — {annee_cible} est {delta} an(s) en avance sur les donnees du MCP.",
            "",
            "Les elements ci-dessous sont a verifier et mettre a jour dans le code source :",
            "",
        ]

    lines += [
        "## Donnees integrees dans le MCP (version actuelle)",
        "",
        "### Impot sur le revenu",
        "",
        "| Parametre | Valeur MCP | A verifier pour annee cible |",
        "|-----------|-----------|------------------------------|",
        f"| Annee bareme actif | {ANNEE_FISCALE} | Indexation annuelle (~1.8 %/an) |",
    ]
    # Afficher les tranches
    for t in TRANCHES_IR_ACTIF:
        max_str = f"{t['max']:,}" if t["max"] else "+"
        lines.append(f"| Tranche {t['taux']*100:.0f} % | {t['min']:,} – {max_str} EUR | Reindexer |")

    lines += [
        f"| Decote celibataire (seuil) | 1 964 EUR | Reindexer |",
        f"| Decote couple (seuil) | 3 249 EUR | Reindexer |",
        f"| Plafond abattement 10 % | 14 426 EUR | Reindexer |",
        f"| Plafond demi-part QF | {PLAFOND_DEMI_PART:,} EUR | Reindexer |",
        "",
        "### PER et epargne retraite",
        "",
        "| Parametre | Valeur MCP | Source |",
        "|-----------|-----------|--------|",
        f"| Plafond PER max | {PLAFOND_PER_MAX_2025:,} EUR | 10 % x 8 PASS — reindexer avec PASS {annee_revenus_mcp} |",
        f"| Plafond PER min | {PLAFOND_PER_MIN_2025:,} EUR | 10 % x 1 PASS — reindexer avec PASS {annee_revenus_mcp} |",
        "",
        "### Impot sur les societes",
        "",
        "| Parametre | Valeur MCP | Stabilite |",
        "|-----------|-----------|-----------|",
        "| Taux reduit IS | 15 % jusqu'a 42 500 EUR | Stable (LF 2023) |",
        "| Taux normal IS | 25 % | Stable |",
        "",
        "### Auto-entrepreneur / Micro",
        "",
        "| Parametre | Valeur MCP | A verifier |",
        "|-----------|-----------|------------|",
        "| Seuil CA services BIC/BNC | 77 700 EUR | Reindexation biennale possible |",
        "| Seuil CA vente marchandises | 188 700 EUR | Reindexation biennale possible |",
        "| Taux cotisations BNC | 23.1 % | Peut evoluer (URSSAF) |",
        "| Taux cotisations BIC services | 21.4 % | Peut evoluer (URSSAF) |",
        "| Seuil TVA franchise BIC | 37 500 EUR | Reindexation possible |",
        "| Seuil TVA franchise vente | 85 000 EUR | Reindexation possible |",
        "",
        "### IFI",
        "",
        "| Parametre | Valeur MCP | A verifier |",
        "|-----------|-----------|------------|",
        "| Seuil d'entree IFI | 1 300 000 EUR | Stable depuis 2018 |",
        "| Bareme IFI | 5 tranches (0 a 1.5 %) | Stable |",
        "| Decote IFI (1.3M – 1.4M) | 17 500 – 0.0125 x patrimoine | Stable |",
        "",
        "### Droits de donation / succession",
        "",
        "| Parametre | A verifier |",
        "|-----------|------------|",
        "| Abattements (parent/enfant, grands-parents...) | Stables sauf legislation |",
        "| Don d'argent exonere | 31 865 EUR — stable |",
        "| Baremes progressifs par lien de parente | Stables |",
        "",
        "### CEHR (contribution exceptionnelle hauts revenus)",
        "",
        "| Parametre | Valeur MCP | A verifier |",
        "|-----------|-----------|------------|",
        "| Seuil 3 % (celibataire) | 250 000 EUR | Stable |",
        "| Seuil 4 % (celibataire) | 500 000 EUR | Stable |",
        "",
    ]

    if annee_cible > annee_actuelle_mcp:
        lines += [
            "## Procedure de mise a jour",
            "",
            "Pour mettre le MCP a jour vers une nouvelle annee fiscale :",
            "",
            "1. Mettre a jour `TRANCHES_IR_ACTIF` avec le nouveau bareme (publie en loi de finances).",
            "2. Ajouter `TRANCHES_IR_XXXX` avec les nouvelles tranches indexees.",
            "3. Mettre a jour `ANNEE_FISCALE` (ex. '2027 (revenus 2026)').",
            "4. Recalculer `PLAFOND_PER_MAX` et `PLAFOND_PER_MIN` avec le nouveau PASS.",
            "5. Verifier les seuils AE et TVA aupres de l'URSSAF.",
            "6. Verifier le SMIC brut annuel pour les simulations SASU.",
            "7. Mettre a jour `__version__` et le CHANGELOG.",
            "",
            "Sources officielles :",
            "- impots.gouv.fr (baremes IR, IS, IFI)",
            "- urssaf.fr (taux cotisations, PASS, seuils AE)",
            "- legifrance.gouv.fr (loi de finances)",
            "- service-public.fr (droits donation, succession)",
        ]

    lines += [
        "",
        "---",
        f"*MCP version {__version__} — Donnees {ANNEE_FISCALE}*",
    ]
    return "\n".join(lines)


# ─── Outils 2.7.0 ────────────────────────────────────────────────────────────

def tool_simuler_revenus_exceptionnels(args: Dict) -> str:
    """Systeme du quotient (art. 163-0 A CGI) pour revenus exceptionnels ou differes."""
    rni_ordinaire = float(args.get("rni_ordinaire", 0))
    revenu_exceptionnel = float(args["revenu_exceptionnel"])
    n = max(1, int(args.get("nombre_annees_echelement", 4)))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    type_revenu = args.get("type_revenu", "autre")

    nb_parts = calculer_parts(situation, nb_enfants)

    ir_ordinaire = calculer_ir(rni_ordinaire, nb_parts)["impot_net"]
    # Sans quotient : IR sur RNI + RE en totalite
    ir_sans_quotient_total = calculer_ir(rni_ordinaire + revenu_exceptionnel, nb_parts)["impot_net"]
    surcout_sans_quotient = ir_sans_quotient_total - ir_ordinaire
    # Avec quotient : [IR(RNI + RE/N) - IR(RNI)] * N
    ir_avec_quotient_1part = calculer_ir(rni_ordinaire + revenu_exceptionnel / n, nb_parts)["impot_net"]
    surcout_avec_quotient = (ir_avec_quotient_1part - ir_ordinaire) * n
    ir_avec_quotient_total = ir_ordinaire + surcout_avec_quotient
    economie = surcout_sans_quotient - surcout_avec_quotient

    TYPES_INFOS = {
        "indemnite_licenciement": ("Indemnite de licenciement supra-legale", "La fraction legale est exoneree (min 2 PASS). Le surplus est un revenu exceptionnel eligible au quotient."),
        "prime_exceptionnelle":   ("Prime ou bonus exceptionnel", "N = nombre d'annees sur lesquelles le droit a ete acquis. Utiliser N=4 par defaut si non justifiable autrement."),
        "revenus_differés":       ("Revenus differes (rappels de salaires, arrieres)", "N = nombre d'annees ecoulees entre la naissance du droit et la perception. Eligibilite automatique."),
        "gain_stock_options":     ("Gain de levee de stock-options / RSU / AGA", "Regime specifique : taux 30% + PS 10% pour options post-mars 2012. Le quotient ne s'applique pas."),
        "autre":                  ("Autre revenu exceptionnel ou pluriannuel", "Eligibilite a confirmer selon le caractere non recurrent et pluriannuel du revenu."),
    }
    label, info_type = TYPES_INFOS.get(type_revenu, TYPES_INFOS["autre"])

    lines = [
        "# Systeme du Quotient — Revenus Exceptionnels",
        "*(Art. 163-0 A CGI)*",
        "",
        "## Principe",
        f"Le quotient divise le revenu exceptionnel par N={n} pour calculer l'impot,",
        f"puis multiplie par {n}. Il limite l'effet de la progressivite de l'IR.",
        "",
        "## Simulation",
        "",
        "| Scenario | RNI total | IR total | Impot sur le revenu exceptionnel |",
        "|----------|-----------|---------|----------------------------------|",
        f"| RNI ordinaire seul | {rni_ordinaire:,.0f} EUR | {ir_ordinaire:,.0f} EUR | — |",
        f"| Declaration normale (sans quotient) | {rni_ordinaire + revenu_exceptionnel:,.0f} EUR | {ir_sans_quotient_total:,.0f} EUR | {surcout_sans_quotient:,.0f} EUR |",
        f"| Avec quotient (N={n}, art. 163-0 A) | — | {ir_avec_quotient_total:,.0f} EUR | {surcout_avec_quotient:,.0f} EUR |",
        "",
    ]

    if economie <= 0:
        lines += [
            "Le systeme du quotient n'apporte pas d'avantage ici.",
            "Votre revenu exceptionnel ne vous fait pas changer de tranche marginale.",
            "",
        ]
    else:
        taux_eff_sans = surcout_sans_quotient / revenu_exceptionnel * 100
        taux_eff_avec = surcout_avec_quotient / revenu_exceptionnel * 100
        lines += [
            f"### Economie grace au quotient : **{economie:,.0f} EUR**",
            "",
            f"| | Sans quotient | Avec quotient (N={n}) |",
            f"|--|--------------|----------------------|",
            f"| Impot sur le revenu exceptionnel | {surcout_sans_quotient:,.0f} EUR | {surcout_avec_quotient:,.0f} EUR |",
            f"| Taux effectif | {taux_eff_sans:.1f}% | {taux_eff_avec:.1f}% |",
            "",
        ]

    lines += [
        f"## Type de revenu : {label}",
        "",
        info_type,
        "",
        "## Revenus eligibles au quotient",
        "",
        "| Type | Coefficient N | Remarque |",
        "|------|---------------|----------|",
        "| Rappels de salaires / arrieres | Annees concernees | Eligibilite automatique |",
        "| Indemnite de licenciement supra-legale | 4 (usage standard) | Fraction legale exoneree |",
        "| Revenus d'activite pluriannuels (gerant, liberal) | Annees d'activite | Art. 163-0 A al. 2 |",
        "| Prime ou bonus exceptionnel non recurrent | 4 | Sur acceptation administration |",
        "| Gain levee d'options / AGA ante-mars 2012 | Variable | Regime fiscal specifique |",
        "",
        "## Procedure de declaration",
        "",
        "1. Incluez le revenu exceptionnel dans votre declaration 2042 (case correspondante)",
        "2. Remplissez le formulaire **2042 C** — rubrique 'Revenus exceptionnels ou differes'",
        "3. Indiquez le montant du revenu exceptionnel et le coefficient N retenu",
        "4. L'administration recalcule l'IR avec le quotient automatiquement",
        "",
        "---",
        "*Sources : Art. 163-0 A CGI — BOFIP BOI-IR-LIQ-20-30-20*",
    ]
    return "\n".join(lines)


def tool_comparer_pfu_bareme_capital(args: Dict) -> str:
    """Compare PFU 30% et bareme progressif pour revenus du capital."""
    type_revenu = args.get("type_revenu", "dividendes")
    montant = float(args["montant"])
    rni_autres = float(args.get("rni_autres_revenus", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))

    nb_parts = calculer_parts(situation, nb_enfants)
    PS = 0.172

    # PFU 30%
    tax_pfu = round(montant * 0.30)
    ir_pfu = round(montant * 0.128)
    ps_pfu = round(montant * PS)

    # Option bareme
    if type_revenu == "dividendes":
        base_ir_bareme = montant * 0.60  # abattement 40%
        csg_ded = round(montant * 0.068)  # deductible N+1
    else:
        base_ir_bareme = montant
        csg_ded = 0

    ir_bareme_avec = calculer_ir(rni_autres + base_ir_bareme, nb_parts)["impot_net"]
    ir_bareme_sans = calculer_ir(rni_autres, nb_parts)["impot_net"]
    ir_supplementaire = round(ir_bareme_avec - ir_bareme_sans)
    ps_bareme = round(montant * PS)
    tax_bareme = ir_supplementaire + ps_bareme

    tmi = calculer_ir(rni_autres + base_ir_bareme, nb_parts)["taux_marginal"]
    difference = tax_pfu - tax_bareme
    meilleure = "PFU (flat tax 30%)" if difference < 0 else "Bareme progressif"
    economie = abs(difference)

    LABELS = {
        "dividendes": "Dividendes",
        "interets": "Interets et revenus assimiles",
        "plus_values_mobilieres": "Plus-values mobilieres (compte-titres)",
    }

    lines = [
        "# PFU vs Bareme Progressif — Revenus du Capital",
        "",
        f"**Type de revenu** : {LABELS.get(type_revenu, type_revenu)}",
        f"**Montant** : {montant:,.0f} EUR",
        f"**Autres revenus du foyer (RNI)** : {rni_autres:,.0f} EUR",
        f"**TMI sur revenus ordinaires** : {tmi:.0f}%",
        "",
        "## Comparaison",
        "",
        "| Option | Base IR | IR | Prel. sociaux | Total | Taux effectif |",
        "|--------|---------|-----|--------------|-------|---------------|",
        f"| PFU (flat tax) | {montant:,.0f} EUR | {ir_pfu:,} EUR | {ps_pfu:,} EUR | {tax_pfu:,} EUR | 30.0% |",
        f"| Bareme progressif | {base_ir_bareme:,.0f} EUR | {ir_supplementaire:,} EUR | {ps_bareme:,} EUR | {tax_bareme:,} EUR | {tax_bareme/montant*100:.1f}% |",
        "",
        f"## Recommandation : **{meilleure}**",
        f"Economie : **{economie:,} EUR** en faveur du {meilleure}",
        "",
    ]

    if type_revenu == "dividendes":
        lines += [
            "Note dividendes (bareme) : abattement 40% applique. CSG deductible N+1 : "
            f"{csg_ded:,} EUR (gain supplementaire ~{round(csg_ded * tmi / 100):,} EUR l'annee suivante).",
            "",
        ]

    lines += [
        "## Seuils de bascule selon le TMI",
        "",
        "| TMI | Dividendes | Interets / PV mobilieres |",
        "|-----|-----------|--------------------------|",
        "| 0 % | Bareme (17.2% seulement) | Bareme (17.2% seulement) |",
        "| 11 % | Bareme (~23.8% effectif) | Bareme (~28.2% effectif) |",
        "| 30 % | PFU (30% vs ~35.2%) | PFU (30% vs ~47.2%) |",
        "| 41 % | PFU (30% vs ~43.8%) | PFU (30% vs ~58.2%) |",
        "",
        "- **Dividendes** : bareme avantageux si TMI <= 11% (break-even theorique ~21% avec abatt. 40%)",
        "- **Interets / PV** : bareme avantageux si TMI <= 11% (break-even a 12.8%)",
        "",
        "## Comment opter pour le bareme",
        "",
        "- Cochez la case **2OP** dans votre declaration 2042",
        "- L'option est globale : s'applique a tous vos revenus de capitaux mobiliers de l'annee",
        "- Elle est irrevocable pour l'annee concernee",
        "- A refaire chaque annee si pertinent",
        "",
        "---",
        "*Sources : Art. 200 A, 158-3 CGI — BOFIP BOI-RPPM-RCM-20-20*",
    ]
    return "\n".join(lines)


def tool_simuler_lmnp(args: Dict) -> str:
    """Simulation LMNP : micro-BIC vs reel avec amortissement batiment et mobilier."""
    loyers = float(args["loyers_annuels_bruts"])
    val_bien = float(args.get("valeur_bien_hors_terrain", 0))
    val_mobilier = float(args.get("valeur_mobilier", 5000))
    charges = float(args.get("charges_annuelles", 0))
    interets = float(args.get("interets_emprunt_annuels", 0))
    tf = float(args.get("taxe_fonciere", 0))
    type_loc = args.get("type_location", "classique")
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    rni_autres = float(args.get("rni_autres_revenus", 0))

    nb_parts = calculer_parts(situation, nb_enfants)
    PS = 0.172

    abatt_micro = 0.71 if type_loc == "tourisme_classe" else 0.50
    seuil_micro = 188_700 if type_loc == "tourisme_classe" else 77_700
    micro_eligible = loyers <= seuil_micro

    # Micro-BIC
    base_micro = loyers * (1 - abatt_micro)
    ir_micro = round(calculer_ir(rni_autres + base_micro, nb_parts)["impot_net"] - calculer_ir(rni_autres, nb_parts)["impot_net"])
    ps_micro = round(base_micro * PS)
    tax_micro = ir_micro + ps_micro
    net_micro = round(loyers - tax_micro)

    # Reel simplifie
    amort_bien = round(val_bien / 40) if val_bien > 0 else 0
    amort_mobilier = round(val_mobilier / 7) if val_mobilier > 0 else 0
    amort_total = amort_bien + amort_mobilier
    charges_totales = charges + interets + tf
    benefice_avant_amort = loyers - charges_totales
    benefice_reel = benefice_avant_amort - amort_total

    if benefice_reel > 0:
        ir_reel = round(calculer_ir(rni_autres + benefice_reel, nb_parts)["impot_net"] - calculer_ir(rni_autres, nb_parts)["impot_net"])
        ps_reel = round(benefice_reel * PS)
        tax_reel = ir_reel + ps_reel
        net_reel = round(loyers - tax_reel)
        deficit_genere = 0
    else:
        ir_reel = 0
        ps_reel = 0
        tax_reel = 0
        net_reel = round(loyers)
        deficit_genere = abs(benefice_reel)

    tmi = calculer_ir(rni_autres + base_micro, nb_parts)["taux_marginal"]

    lines = [
        "# Simulation LMNP — Location Meublee Non Professionnelle",
        "",
        f"**Loyers annuels bruts** : {loyers:,.0f} EUR",
        f"**Type** : {'Meuble tourisme classe / VFT (abatt. 71%)' if type_loc == 'tourisme_classe' else 'Location meublee classique (abatt. 50%)'}",
        f"**TMI** : {tmi:.0f}%",
        "",
        "## Statut LMNP — Verification",
        "",
        "| Condition LMNP | Seuil | Statut |",
        "|---------------|-------|--------|",
        f"| Recettes annuelles | < 23 000 EUR | {'A verifier — vous etes peut-etre LMP' if loyers >= 23000 else 'OK'} |",
        f"| Recettes < 50% du RFR global | Depend du foyer | A verifier |",
        "",
        "Si recettes > 23 000 EUR ET > 50% du RFR : basculement en LMP (regime different, IS sur PV revente).",
        "",
        "## Comparatif Micro-BIC vs Reel",
        "",
        "| Regime | Base imposable | IR | PS (17.2%) | Total taxes | Net encaisse |",
        "|--------|---------------|-----|-----------|-------------|--------------|",
    ]

    if micro_eligible:
        lines.append(f"| Micro-BIC (abatt. {int(abatt_micro*100)}%) | {base_micro:,.0f} EUR | {ir_micro:,} EUR | {ps_micro:,} EUR | {tax_micro:,} EUR | {net_micro:,} EUR |")
    else:
        lines.append(f"| Micro-BIC | Non applicable (CA {loyers:,.0f} > {seuil_micro:,} EUR) | — | — | — | — |")

    if benefice_reel > 0:
        lines.append(f"| Reel simplifie | {benefice_reel:,.0f} EUR | {ir_reel:,} EUR | {ps_reel:,} EUR | {tax_reel:,} EUR | {net_reel:,} EUR |")
    else:
        lines.append(f"| Reel simplifie | **Deficit {deficit_genere:,.0f} EUR** | 0 EUR | 0 EUR | 0 EUR | {net_reel:,} EUR + report deficit |")

    lines += ["", "## Detail du regime reel", ""]

    if charges_totales > 0 or amort_total > 0:
        lines += [
            "### Charges deductibles",
            "| Poste | Montant |",
            "|-------|---------|",
            f"| Charges courantes (copro, assurance, gestion) | {charges:,.0f} EUR |",
            f"| Interets d'emprunt | {interets:,.0f} EUR |",
            f"| Taxe fonciere | {tf:,.0f} EUR |",
            f"| **Total charges** | **{charges_totales:,.0f} EUR** |",
            "",
            "### Amortissements",
            "| Actif | Valeur | Duree | Dotation annuelle |",
            "|-------|--------|-------|-------------------|",
        ]
        if val_bien > 0:
            lines.append(f"| Batiment (hors terrain) | {val_bien:,.0f} EUR | 40 ans | {amort_bien:,} EUR/an |")
        if val_mobilier > 0:
            lines.append(f"| Mobilier / equipements | {val_mobilier:,.0f} EUR | 7 ans | {amort_mobilier:,} EUR/an |")
        lines += [
            f"| **Total amortissements** | | | **{amort_total:,} EUR/an** |",
            "",
            f"Loyers                         : {loyers:,.0f} EUR",
            f"- Charges                      : -{charges_totales:,.0f} EUR",
            f"- Amortissements               : -{amort_total:,.0f} EUR",
            f"= Resultat imposable           : {benefice_reel:,.0f} EUR" + (" (DEFICIT — report 10 ans sur BIC meublés)" if benefice_reel < 0 else ""),
            "",
        ]

    lines += [
        "## Particularites du deficit LMNP",
        "- Le deficit LMNP ne s'impute PAS sur le revenu global (contrairement a la location nue)",
        "- Il est reportable 10 ans sur les benefices de location meublee non professionnelle du meme foyer",
        "- Les amortissements non utilises (benefice = 0) sont mis en reserve pour annees futures",
        "",
        "## LMNP a la revente",
        "- Plus-value calculee sur regime immo (exonerations selon duree de detention)",
        "- Les amortissements deduits ne sont PAS reintegres dans la PV (avantage majeur vs LMP)",
        "- Seule la difference prix vente - prix achat initial est taxee",
        "",
        "---",
        "*Sources : Art. 35, 50-0, 151 septies A CGI — BOI-BIC-CHAMP-40-20 (LMNP)*",
    ]

    if micro_eligible and benefice_reel < 0:
        lines.insert(-3, "## Recommandation : Regime reel")
        lines.insert(-3, "Le reel genere un deficit grace aux amortissements — aucun impot cette annee. Le micro impose {:.0f} EUR.".format(tax_micro))
    elif micro_eligible and tax_micro > tax_reel:
        eco = tax_micro - tax_reel
        lines.insert(-3, f"## Recommandation : Regime reel (economie {eco:,} EUR/an)")
        lines.insert(-3, f"Charges + amortissements ({charges_totales + amort_total:,.0f} EUR) > abattement micro ({loyers * abatt_micro:,.0f} EUR).")
    elif micro_eligible:
        eco = tax_reel - tax_micro
        lines.insert(-3, f"## Recommandation : Micro-BIC (economie {eco:,} EUR/an)")
        lines.insert(-3, f"Abattement micro ({loyers * abatt_micro:,.0f} EUR) > charges + amortissements ({charges_totales + amort_total:,.0f} EUR). Plus simple, pas de comptabilite.")

    return "\n".join(lines)


def tool_simuler_rachat_trimestres(args: Dict) -> str:
    """Simulation rachat de trimestres retraite : cout, gain de pension, break-even."""
    nb_trim = max(1, int(args.get("nb_trimestres_racheter", 4)))
    salaire_brut = float(args["salaire_annuel_brut"])
    age = int(args["age_actuel"])
    annee_nais = int(args.get("annee_naissance", 1975))
    trim_actuels = int(args.get("trimestres_valides_actuels", 100))
    option = args.get("option_rachat", "duree_seulement")
    tmi = float(args.get("tmi", 30))
    statut = args.get("statut_professionnel", "salarie")

    PASS_2025 = 46_368

    # Trimestres requis selon annee naissance (reforme 2023)
    if annee_nais >= 1965:
        n_requis = 172
    elif annee_nais >= 1961:
        n_requis = 165 + min(annee_nais - 1961, 3)
    else:
        n_requis = 160

    # Tarifs approximatifs CNAV 2025 par tranche d'age (% du salaire plafonne au PASS)
    TARIFS = [
        (20, 29, 0.110), (30, 34, 0.135), (35, 39, 0.165),
        (40, 44, 0.205), (45, 49, 0.255), (50, 54, 0.310),
        (55, 59, 0.370), (60, 99, 0.415),
    ]
    taux_trim = 0.30
    for age_min, age_max, t in TARIFS:
        if age_min <= age <= age_max:
            taux_trim = t
            break
    if option == "duree_et_taux":
        taux_trim *= 1.33

    salaire_ref = min(salaire_brut, PASS_2025)
    cout_par_trim = round(salaire_ref * taux_trim)
    cout_total = cout_par_trim * nb_trim
    economie_fiscale = round(cout_total * tmi / 100)
    cout_net = cout_total - economie_fiscale

    # Gain de pension estime (base regime general simplifie)
    salaire_ref_mensuel = min(salaire_brut, PASS_2025) / 12
    trim_apres = trim_actuels + nb_trim
    manquants_avant = max(0, n_requis - trim_actuels)
    manquants_apres = max(0, n_requis - trim_apres)
    decote_avant = min(manquants_avant, 20) * 0.0125
    decote_apres = min(manquants_apres, 20) * 0.0125

    pension_avant = salaire_ref_mensuel * 0.50 * (trim_actuels / n_requis) * (1 - decote_avant)
    pension_apres = salaire_ref_mensuel * 0.50 * (trim_apres / n_requis) * (1 - decote_apres)
    gain_mensuel = max(0, round(pension_apres - pension_avant))

    mois_be = round(cout_net / gain_mensuel) if gain_mensuel > 0 else None

    lines = [
        "# Simulation Rachat de Trimestres Retraite",
        "*(Art. L161-17-3 Code de la Securite Sociale)*",
        "",
        "## Parametres",
        "",
        f"| Element | Valeur |",
        f"|---------|--------|",
        f"| Age actuel | {age} ans |",
        f"| Trimestres valides | {trim_actuels} / {n_requis} requis |",
        f"| Trimestres a racheter | {nb_trim} |",
        f"| Option | {'Duree + taux de liquidation (plus cher)' if option == 'duree_et_taux' else 'Duree d assurance seulement'} |",
        f"| Salaire brut annuel | {salaire_brut:,.0f} EUR (ref PASS : {salaire_ref:,.0f} EUR) |",
        "",
        "## Cout du rachat",
        "",
        f"| Poste | Montant |",
        f"|-------|---------|",
        f"| Taux par trimestre (age {age} ans) | {taux_trim*100:.1f}% du salaire reference |",
        f"| Cout par trimestre | {cout_par_trim:,} EUR |",
        f"| Cout total ({nb_trim} trimestre(s)) | {cout_total:,} EUR |",
        f"| Economie fiscale ({tmi:.0f}% TMI — deductible {'IR case 6DD' if statut == 'salarie' else 'cotisations TNS'}) | -{economie_fiscale:,} EUR |",
        f"| **Cout net d'impot** | **{cout_net:,} EUR** |",
        "",
        "## Gain de pension estime (regime general)",
        "",
        "| Scenario | Trimestres | Decote | Pension base /mois |",
        "|----------|-----------|--------|-------------------|",
        f"| Avant rachat | {trim_actuels} | {decote_avant*100:.2f}% | {pension_avant:,.0f} EUR |",
        f"| Apres rachat | {trim_apres} | {decote_apres*100:.2f}% | {pension_apres:,.0f} EUR |",
        f"| **Gain mensuel** | | | **{gain_mensuel:,} EUR/mois** |",
        "",
    ]

    if gain_mensuel > 0 and mois_be is not None:
        ans_be = mois_be / 12
        lines += [
            "## Rentabilite",
            "",
            f"- Point de break-even : **{mois_be} mois ({ans_be:.1f} ans) apres la retraite**",
            f"- Gain annuel brut : {gain_mensuel * 12:,} EUR/an",
        ]
        if ans_be <= 10:
            lines.append("Rentabilite tres bonne : break-even < 10 ans.")
        elif ans_be <= 15:
            lines.append("Rentabilite correcte : break-even entre 10 et 15 ans.")
        else:
            lines.append("Rentabilite faible : break-even > 15 ans. A peser selon l'esperance de vie.")
        lines.append("")
    else:
        lines += ["Le rachat n'ameliore pas la pension (trimestres deja au maximum ou taux plein atteint).", ""]

    lines += [
        "## Types de trimestres rachetables",
        "",
        "| Type | Maximum | Condition principale |",
        "|------|---------|---------------------|",
        "| Annees a faible cotisation (< 4 trim.) | Sans limite | Annees anterieures incompletes |",
        "| Etudes superieures (diplome bac+2 ou plus) | 12 trimestres | Dans les 10 ans apres fin etudes |",
        "| Stages conventionnes | 4 trimestres | Pendant les etudes |",
        "",
        "## Deductibilite fiscale",
        "",
        "| Statut | Mode de deduction | Plafond |",
        "|--------|------------------|---------|",
        "| Salarie | Case 6DD — revenu imposable | Dans l'enveloppe PER |",
        "| TNS / independant | Cotisations sociales deductibles | Plafond Madelin/PER |",
        "| Fonctionnaire | Non deductible | — |",
        "",
        f"Note : le rachat est irreversible. Verifier le releve de carriere sur info-retraite.fr avant tout versement.",
        f"Comparer avec un versement PER equivalent : meme economie fiscale, plus de flexibilite a la sortie.",
        "",
        "---",
        f"*Tarifs indicatifs — CNAV 2025 — PASS 2025 : {PASS_2025:,} EUR*",
        "*Sources : Art. L161-17-3 CSS — Circ. CNAV — info-retraite.fr*",
    ]
    return "\n".join(lines)


def tool_calculer_exit_tax(args: Dict) -> str:
    """Exit tax (art. 167 bis CGI) : imposition des PV latentes lors du depart de France."""
    pv_latentes = float(args.get("plus_values_latentes_total", 0))
    rni_autres = float(args.get("rni_autres_revenus", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    pays = args.get("pays_destination", "hors_ue")
    annees_res = int(args.get("annees_residence_france_10_dernieres", 10))
    option_bareme = bool(args.get("option_bareme_progressif", False))

    nb_parts = calculer_parts(situation, nb_enfants)
    SEUIL = 800_000
    PS = 0.172

    applicable = pv_latentes >= SEUIL and annees_res >= 6

    lines = [
        "# Exit Tax — Depart de France",
        "*(Art. 167 bis CGI)*",
        "",
        "## Conditions de declenchement",
        "",
        "| Condition | Requis | Situation |",
        "|-----------|--------|-----------|",
        f"| Residence fiscale en France (10 dernieres annees) | >= 6 ans | {annees_res} an(s) — {'OK' if annees_res >= 6 else 'Non applicable'} |",
        f"| Plus-values latentes nettes | > 800 000 EUR | {pv_latentes:,.0f} EUR — {'Declenche' if pv_latentes >= SEUIL else 'Sous le seuil'} |",
        "",
    ]

    if not applicable:
        lines += [
            "**Exit tax non applicable** dans votre situation.",
            "",
            "- Si vos PV latentes progressent : surveiller le seuil de 800 000 EUR",
            "- Autre declencheur possible : titres representant > 50% du benefice d'une societe",
            "",
            "---",
            "*Art. 167 bis CGI — BOI-RPPM-PVBMI-50-10*",
        ]
        return "\n".join(lines)

    # Calcul de l'exit tax
    if option_bareme:
        ir_avec = calculer_ir(rni_autres + pv_latentes, nb_parts)["impot_net"]
        ir_sans = calculer_ir(rni_autres, nb_parts)["impot_net"]
        ir_exit = round(ir_avec - ir_sans)
    else:
        ir_exit = round(pv_latentes * 0.128)
    ps_exit = round(pv_latentes * PS)
    exit_tax = ir_exit + ps_exit

    lines += [
        f"**Exit tax applicable** — PV latentes : {pv_latentes:,.0f} EUR",
        "",
        "## Calcul",
        "",
        f"| Composante | Taux | Montant |",
        f"|-----------|------|---------|",
        f"| IR ({'bareme progressif' if option_bareme else 'PFU 12.8%'}) | {'variable' if option_bareme else '12.8%'} | {ir_exit:,} EUR |",
        f"| Prelevement sociaux | 17.2% | {ps_exit:,} EUR |",
        f"| **Exit tax totale** | {exit_tax/pv_latentes*100:.1f}% | **{exit_tax:,} EUR** |",
        "",
        "## Regime de paiement",
        "",
    ]

    if pays == "ue_eea":
        lines += [
            "### Depart vers l'UE / EEE — Sursis automatique",
            "",
            "- Exit tax calculee et declaree, mais **paiement automatiquement differe**",
            "- Degreve si retour en France dans les 5 ans",
            "- Degreve si perte ou cession a perte apres le depart",
            "- Degreve si les titres ont ete transmis a titre gratuit",
            "- Obligation : declaration annuelle 2074-ETD de suivi des titres",
            "- Le sursis prend fin lors de la cession effective des titres (impot du au taux de depart)",
            "",
        ]
    else:
        lines += [
            "### Depart hors UE / EEE — Paiement immediat",
            "",
            "- L'exit tax est exigible immediatement au depart",
            "- Sursis sur demande possible : necessite une garantie (nantissement des titres)",
            "- Si garantie accordee : paiement fractionne possible jusqu'a la cession (max 5 ans)",
            "- Degreve si retour en France dans les 5 ans",
            "",
        ]

    lines += [
        "## Actifs concernes et exoneres",
        "",
        "| Actif | Concerne par l'exit tax |",
        "|-------|------------------------|",
        "| Actions, obligations, titres de societes | Oui |",
        "| Parts de fonds (FCP, SICAV, FCT) | Oui |",
        "| PEA (plus-values latentes) | Oui |",
        "| Contrats d'assurance-vie (unites de compte) | Oui |",
        "| Residence principale | Non |",
        "| Livret A, LDD, LEP, livrets reglementes | Non |",
        "| Immobilier locatif | Non (regime PV immo applique lors de la cession) |",
        "",
        "## Strategies pour minimiser avant le depart",
        "",
        "- **Realiser des moins-values** avant le depart pour reduire les PV latentes nettes",
        "- **Donner les titres** avant le depart : la PV latente n'est pas taxee a la donation",
        "  (attention : le donataire reprend la valeur d'origine, pas le prix de marche)",
        "- **Evaluer precisement** les PV latente par actif avec un avocat fiscaliste",
        "- **Anticiper la declaration 2074-ETD** si depart vers UE/EEE",
        "- **Passer sous le seuil** de 800 000 EUR si possible avant le changement de domicile",
        "",
        "---",
        "*Sources : Art. 167 bis CGI — Loi de finances 2019 (reforme) — BOI-RPPM-PVBMI-50-10*",
    ]
    return "\n".join(lines)


def tool_guide_loc_avantages(args: Dict) -> str:
    """Guide Loc'Avantages (art. 199 tricies CGI) : reduction d'impot 15% a 65% sur location abordable."""
    loyers = float(args.get("loyers_bruts_annuels", 0))
    niveau = args.get("niveau_convention", "intermediaire")
    surface = float(args.get("surface_m2", 0))
    zone = args.get("zone", "B1")
    rni_autres = float(args.get("rni_autres_revenus", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))

    nb_parts = calculer_parts(situation, nb_enfants)

    NIVEAUX = {
        "intermediaire": {"label": "Intermediaire", "taux": 0.15, "minoration": 0.15, "desc": "Loyer <= marche - 15%"},
        "social":        {"label": "Social",        "taux": 0.35, "minoration": 0.30, "desc": "Loyer <= marche - 30%"},
        "tres_social":   {"label": "Tres social",   "taux": 0.65, "minoration": 0.45, "desc": "Loyer <= marche - 45%"},
        "solidaire":     {"label": "Solidaire (via association agreee)", "taux": 0.65, "minoration": 0.45, "desc": "Sous-location solidaire"},
    }
    ZONES = {
        "A_bis": ("Zone A bis — Paris et 76 communes", 18.0),
        "A":     ("Zone A — IDF hors A bis, Cote d'Azur, Genevois", 13.5),
        "B1":    ("Zone B1 — agglomerations > 250 000 hab.", 11.0),
        "B2_C":  ("Zone B2 / C — autres communes", 8.5),
    }

    niv = NIVEAUX.get(niveau, NIVEAUX["intermediaire"])
    zone_label, loyer_marche_m2 = ZONES.get(zone, ZONES["B1"])
    loyer_plafond_m2 = loyer_marche_m2 * (1 - niv["minoration"])
    loyer_plafond_an = loyer_plafond_m2 * surface * 12 if surface > 0 else 0

    reduction = round(loyers * niv["taux"]) if loyers > 0 else 0
    reduction_effective = min(reduction, 10_000)  # plafond niches fiscales

    # Gain fiscal : la reduction s'impute directement sur l'IR
    rni_total = rni_autres + loyers * 0.70  # estimation revenus fonciers nets
    ir_sans = round(calculer_ir(rni_total, nb_parts)["impot_net"])
    ir_avec = max(0, ir_sans - reduction_effective)
    gain = ir_sans - ir_avec

    lines = [
        "# Loc'Avantages — Location a Loyer Abordable",
        "*(Art. 199 tricies CGI — Convention ANAH)*",
        "",
        "Loc'Avantages remplace le dispositif Pinel pour l'immobilier ancien.",
        "Il offre une reduction d'IR de 15% a 65% en echange d'un loyer modere, via convention ANAH.",
        "",
        "## Convention choisie",
        "",
        f"| Parametre | Valeur |",
        f"|-----------|--------|",
        f"| Niveau | {niv['label']} |",
        f"| Reduction d'impot | {int(niv['taux']*100)}% des loyers bruts |",
        f"| Engagement de loyer | {niv['desc']} |",
        f"| Zone | {zone_label} |",
        "",
    ]

    if surface > 0:
        lines += [
            "## Loyer plafond applicable",
            "",
            f"| Zone | Loyer marche (m2/mois) | Reduction | Plafond Loc'Avantages (m2/mois) | Loyer annuel max ({surface:.0f} m2) |",
            f"|------|-----------------------|-----------|--------------------------------|------------------------------------|",
            f"| {zone} | {loyer_marche_m2:.2f} EUR | -{int(niv['minoration']*100)}% | {loyer_plafond_m2:.2f} EUR | {loyer_plafond_an:,.0f} EUR/an |",
            "",
        ]

    if loyers > 0:
        lines += [
            "## Simulation fiscale",
            "",
            f"| Poste | Montant |",
            f"|-------|---------|",
            f"| Loyers bruts annuels | {loyers:,.0f} EUR |",
            f"| Reduction d'impot calculee ({int(niv['taux']*100)}%) | {reduction:,.0f} EUR |",
        ]
        if reduction > 10_000:
            lines.append(f"| Reduction apres plafond niches fiscales (10 000 EUR) | {reduction_effective:,.0f} EUR |")
        lines += [
            f"| IR avant Loc'Avantages (estime) | {ir_sans:,.0f} EUR |",
            f"| IR apres Loc'Avantages | {ir_avec:,.0f} EUR |",
            f"| **Gain fiscal annuel** | **{gain:,.0f} EUR** |",
            "",
        ]

    lines += [
        "## Tableau comparatif des niveaux",
        "",
        "| Niveau | Reduction IR | Minoration loyer | Plafonds locataire (celibataire zone B1) |",
        "|--------|-------------|-----------------|----------------------------------------|",
        "| Intermediaire | 15% | -15% | ~43 000 EUR de revenus annuels |",
        "| Social | 35% | -30% | ~37 000 EUR de revenus annuels |",
        "| Tres social | 65% | -45% | ~24 000 EUR de revenus annuels |",
        "| Solidaire | 65% | -45% | Locataires en grande precarite |",
        "",
        "## Conditions",
        "",
        "1. Logement loue **nu** (pas meuble), usage de residence principale du locataire",
        "2. **Convention signee avec l'ANAH** (anah.fr) — delai environ 2 a 3 mois",
        "3. **Duree minimum** : 6 ans (renouvelable — eligible 9 ans via ANAH Habiter Mieux)",
        "4. **Loyer plafonne** selon la zone et le niveau de convention",
        "5. **Locataire sous plafond de ressources** (revenus N-2 verifies par l'ANAH)",
        "6. Logement conforme aux criteres de decence",
        "",
        "## Avantages par rapport au Pinel (clos fin 2024)",
        "",
        "- Applicable a **l'immobilier ancien** (pas seulement le neuf)",
        "- Taux de reduction jusqu'a **65%** vs 9-21% pour le Pinel",
        "- **Pas de plafond d'investissement specifique** (hors plafond global niches 10 000 EUR/an)",
        "- Pas de contrainte geographique stricte comme le Pinel",
        "- **Non soumis au bouclier fiscal specifique** des niches (mais soumis au plafond 10 000 EUR)",
        "",
        "## Demarches",
        "",
        "1. Contacter l'ANAH (anah.fr) pour evaluer l'eligibilite du logement",
        "2. Faire etablir un diagnostic energetique (DPE) si necessaire",
        "3. Signer la convention ANAH",
        "4. Declarer les loyers en revenus fonciers (formulaire 2044)",
        "5. Reporter la reduction d'impot en 2042 (case dedicee Loc'Avantages)",
        "",
        "---",
        "*Sources : Art. 199 tricies CGI — Decret 2022-1626 — anah.fr*",
        "*Loc'Avantages est soumis au plafond global des niches fiscales de 10 000 EUR/an.*",
    ]
    return "\n".join(lines)


def tool_simuler_micro_foncier(args: Dict) -> str:
    """Compare micro-foncier (abattement 30%) et regime reel pour revenus locatifs nus."""
    loyers = float(args["loyers_bruts_annuels"])
    interets = float(args.get("interets_emprunt", 0))
    charges_copro = float(args.get("charges_copropriete", 0))
    tf = float(args.get("taxe_fonciere", 0))
    travaux = float(args.get("travaux_entretien_annuels", 0))
    gestion = float(args.get("frais_gestion_annuels", 0))
    assurance = float(args.get("assurance_pno", 0))
    deficits_ante = float(args.get("deficits_fonciers_anterieurs", 0))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    rni_autres = float(args.get("rni_autres_revenus", 0))

    nb_parts = calculer_parts(situation, nb_enfants)
    PS = 0.172
    SEUIL_MICRO = 15_000
    ABATT_MICRO = 0.30
    PLAFOND_DEFICIT = 10_700   # doublé a 21 400 pour travaux énergétiques

    eligible_micro = loyers <= SEUIL_MICRO

    # ── Micro-foncier ─────────────────────────────────────────────────────────
    base_micro = loyers * (1 - ABATT_MICRO)
    ir_micro = round(calculer_ir(rni_autres + base_micro, nb_parts)["impot_net"] - calculer_ir(rni_autres, nb_parts)["impot_net"])
    ps_micro = round(base_micro * PS)
    tax_micro = ir_micro + ps_micro
    net_micro = round(loyers - tax_micro)

    # ── Regime reel ───────────────────────────────────────────────────────────
    charges_totales = interets + charges_copro + tf + travaux + gestion + assurance
    benefice_brut = loyers - charges_totales

    # Imputation des déficits antérieurs (sur revenus fonciers)
    if benefice_brut > 0 and deficits_ante > 0:
        imputation_ante = min(benefice_brut, deficits_ante)
        benefice_net = benefice_brut - imputation_ante
        deficit_reste = max(0, deficits_ante - imputation_ante)
    else:
        benefice_net = benefice_brut
        deficit_reste = deficits_ante

    if benefice_net > 0:
        ir_reel = round(calculer_ir(rni_autres + benefice_net, nb_parts)["impot_net"] - calculer_ir(rni_autres, nb_parts)["impot_net"])
        ps_reel = round(benefice_net * PS)
        tax_reel = ir_reel + ps_reel
        net_reel = round(loyers - tax_reel)
        deficit_imputable = 0
        nouveau_deficit = 0
    elif benefice_brut < 0:
        # Deficit foncier
        deficit = abs(benefice_brut)
        deficit_hors_interets = max(0, deficit - interets)
        deficit_imputable = min(deficit_hors_interets, PLAFOND_DEFICIT)
        rni_apres = max(0, rni_autres - deficit_imputable)
        economie_ir = round(calculer_ir(rni_autres, nb_parts)["impot_net"] - calculer_ir(rni_apres, nb_parts)["impot_net"])
        ir_reel = -economie_ir
        ps_reel = 0
        tax_reel = -economie_ir
        net_reel = round(loyers + economie_ir)
        nouveau_deficit = deficit - deficit_imputable
    else:
        ir_reel = 0
        ps_reel = 0
        tax_reel = 0
        net_reel = round(loyers)
        deficit_imputable = 0
        nouveau_deficit = 0

    tmi = calculer_ir(rni_autres + base_micro, nb_parts)["taux_marginal"]

    lines = [
        "# Micro-Foncier vs Regime Reel — Revenus Locatifs Nus",
        "",
        f"**Loyers bruts annuels** : {loyers:,.0f} EUR",
        f"**TMI** : {tmi:.0f}%",
        "",
        "## Eligibilite au micro-foncier",
        "",
        f"| Condition | Seuil | Statut |",
        f"|-----------|-------|--------|",
        f"| Loyers bruts annuels | <= 15 000 EUR | {'Eligible' if eligible_micro else 'Non eligible — reel obligatoire'} |",
        "| Pas de regime special actif (Pinel, Malraux, MH...) | — | A verifier |",
        "| Pas de parts de SCPI ou societes immobilieres | — | A verifier |",
        "",
    ]

    if not eligible_micro:
        lines += [
            f"Loyers ({loyers:,.0f} EUR) > seuil 15 000 EUR. Le regime reel est obligatoire.",
            "",
        ]

    lines += [
        "## Comparatif",
        "",
        "| Regime | Base imposable | IR | PS (17.2%) | Total taxes | Net annuel |",
        "|--------|---------------|-----|-----------|-------------|------------|",
    ]
    if eligible_micro:
        lines.append(f"| Micro-foncier (abatt. 30%) | {base_micro:,.0f} EUR | {ir_micro:,} EUR | {ps_micro:,} EUR | {tax_micro:,} EUR | {net_micro:,} EUR |")

    if benefice_net > 0:
        lines.append(f"| Reel (charges {charges_totales:,.0f} EUR) | {benefice_net:,.0f} EUR | {ir_reel:,} EUR | {ps_reel:,} EUR | {tax_reel:,} EUR | {net_reel:,} EUR |")
    elif benefice_brut < 0:
        lines.append(f"| Reel — Deficit {abs(benefice_brut):,.0f} EUR | — | gain {abs(ir_reel):,} EUR | 0 EUR | — | {net_reel:,} EUR |")
    else:
        lines.append(f"| Reel (benefice nul) | 0 EUR | 0 EUR | 0 EUR | 0 EUR | {loyers:,.0f} EUR |")

    lines += [""]

    if charges_totales > 0:
        lines += [
            "## Detail des charges reelles",
            "",
            "| Poste | Montant |",
            "|-------|---------|",
            f"| Interets d'emprunt | {interets:,.0f} EUR |",
            f"| Charges de copropriete | {charges_copro:,.0f} EUR |",
            f"| Taxe fonciere | {tf:,.0f} EUR |",
            f"| Travaux entretien / reparation | {travaux:,.0f} EUR |",
            f"| Frais de gestion | {gestion:,.0f} EUR |",
            f"| Assurance PNO | {assurance:,.0f} EUR |",
            f"| **Total charges** | **{charges_totales:,.0f} EUR** |",
            f"| Abattement micro equivalent | {loyers * ABATT_MICRO:,.0f} EUR (30%) |",
            "",
        ]
        if charges_totales > loyers * ABATT_MICRO or benefice_brut < 0:
            lines.append(f"Charges reelles ({charges_totales:,.0f} EUR) > abattement micro ({loyers * ABATT_MICRO:,.0f} EUR) : le regime reel est plus avantageux.")
        else:
            lines.append(f"Abattement micro ({loyers * ABATT_MICRO:,.0f} EUR) > charges ({charges_totales:,.0f} EUR) : le micro-foncier est plus avantageux.")
        lines.append("")

    if benefice_brut < 0:
        lines += [
            "## Deficit foncier",
            "",
            "| Poste | Montant |",
            "|-------|---------|",
            f"| Deficit total | {abs(benefice_brut):,.0f} EUR |",
            f"| Dont interets d'emprunt (non imputable sur global) | {interets:,.0f} EUR |",
            f"| Deficit hors interets | {max(0, abs(benefice_brut) - interets):,.0f} EUR |",
            f"| Plafond imputable sur revenu global | {PLAFOND_DEFICIT:,} EUR |",
            f"| Impute sur revenu global cette annee | {deficit_imputable:,.0f} EUR |",
            f"| Economie IR generee | {abs(ir_reel):,.0f} EUR |",
            f"| Deficit reporte (BF futurs sur 10 ans) | {nouveau_deficit:,.0f} EUR |",
            "",
            "Note : le plafond passe a 21 400 EUR/an pour travaux de renovation energetique (DPE F/G, 2023-2025).",
            "",
        ]

    if deficits_ante > 0:
        lines += [
            f"Deficits anterieurs : {deficits_ante:,.0f} EUR. Restant apres imputation : {deficit_reste:,.0f} EUR.",
            "",
        ]

    lines += [
        "## Regles essentielles",
        "",
        "- Option reel irrevocable 3 ans : si vous choisissez le reel, pas de retour micro pendant 3 ans",
        "- Le deficit foncier hors interets s'impute sur le revenu global (plafond 10 700 EUR/an)",
        "- Les interets d'emprunt en deficit restent reportables 10 ans sur les revenus fonciers uniquement",
        "- En micro-foncier : impossible de creer un deficit, impossible de deduire les travaux importants",
        "",
        "## Charges deductibles au reel",
        "",
        "- Interets et frais d'emprunt (acquisition, travaux, assurance emprunteur)",
        "- Charges de copropriete non recuperees sur le locataire",
        "- Taxe fonciere (hors TEOM si remboursee par le locataire)",
        "- Travaux de reparation, d'entretien et d'amelioration (pas construction ni agrandissement)",
        "- Frais de gestion locative (agence, syndic, administrateur)",
        "- Primes assurance PNO, loyers impayes",
        "- Frais de procedure (contentieux locatif)",
        "- Diagnostics obligatoires (DPE, amiante, plomb...)",
        "",
        "---",
        "*Sources : Art. 14, 28, 32, 156 I 3° CGI — BOFIP BOI-RFPI-BASE-20 et 30*",
    ]
    return "\n".join(lines)


# ─── Diagnostic passage freelance ────────────────────────────────────────────

def tool_diagnostiquer_passage_freelance(args: Dict) -> str:
    """Diagnostic personnalise : est-il pertinent de passer freelance plutot que de rester en CDI/CDD ?"""
    salaire_brut_cdi = float(args.get("salaire_brut_annuel_cdi", 0))
    secteur = args.get("secteur", "it_dev")
    anciennete_ans = int(args.get("anciennete_ans", 5))
    epargne_disponible = float(args.get("epargne_disponible", 0))
    clients_potentiels = bool(args.get("clients_potentiels", False))
    situation = args.get("situation_famille", "celibataire")
    nb_enfants = int(args.get("nb_enfants", 0))
    acceptation_risque = args.get("acceptation_risque", "moyen")
    tjm_vise = float(args.get("tjm_vise", 0))
    jours = int(args.get("jours_facturation_an", 180))
    charges_mensuelles = float(args.get("charges_mensuelles", 0))
    type_activite = args.get("type_activite", "services_bnc")

    nb_parts = calculer_parts(situation, nb_enfants)

    # ── Donnees sectorielles ──────────────────────────────────────────────────
    SECTEURS = {
        "it_dev": {
            "label": "Developpement / DevOps / Securite informatique",
            "demande": 5,
            "tjm_median": 550,
            "tjm_senior": 750,
            "risque_metier": "faible",
            "note": "Marche en tension structurelle. Tres forte demande de profils autonomes.",
        },
        "it_conseil_data": {
            "label": "Conseil IT / Data / Cloud / Architecture",
            "demande": 5,
            "tjm_median": 600,
            "tjm_senior": 850,
            "risque_metier": "faible",
            "note": "Cloud, IA, data : demande soutenue. TJM eleves des 5 ans d'experience.",
        },
        "conseil_management": {
            "label": "Conseil en management / strategie / organisation",
            "demande": 4,
            "tjm_median": 800,
            "tjm_senior": 1_200,
            "risque_metier": "moyen",
            "note": "Marche porteur pour les profils experimentes (> 8 ans). Reseau indispensable.",
        },
        "marketing_communication": {
            "label": "Marketing / Communication / Design",
            "demande": 3,
            "tjm_median": 350,
            "tjm_senior": 550,
            "risque_metier": "moyen",
            "note": "Concurrence elevee. Specialisation (SEO, performance, UX) augmente le TJM.",
        },
        "juridique_rh": {
            "label": "Juridique / RH / Paie / Compliance",
            "demande": 3,
            "tjm_median": 450,
            "tjm_senior": 700,
            "risque_metier": "moyen",
            "note": "Demande stable. Niche en compliance RGPD/ESG valorisee.",
        },
        "btp_artisanat": {
            "label": "BTP / Artisanat / Metiers du batiment",
            "demande": 4,
            "tjm_median": 300,
            "tjm_senior": 500,
            "risque_metier": "moyen",
            "note": "Penurie de mains-d'oeuvre qualifiees. Sous-traitance directe frequente.",
        },
        "sante_paramedical": {
            "label": "Sante / Paramedical / Bien-etre",
            "demande": 4,
            "tjm_median": 400,
            "tjm_senior": 600,
            "risque_metier": "faible",
            "note": "Liberaux de sante : modele independant historique. Revenus stables.",
        },
        "formation_coaching": {
            "label": "Formation / Coaching / Conseil RH",
            "demande": 3,
            "tjm_median": 500,
            "tjm_senior": 800,
            "risque_metier": "eleve",
            "note": "Marche sature en generalist. Expertise sectorielle ou technique differenciante requise.",
        },
        "commerce_vente": {
            "label": "Commerce / Vente / Business Development",
            "demande": 2,
            "tjm_median": 300,
            "tjm_senior": 450,
            "risque_metier": "eleve",
            "note": "Variable incontournable. Revenus irreguliers. Reseau determinant.",
        },
        "autre": {
            "label": "Autre secteur",
            "demande": 3,
            "tjm_median": 350,
            "tjm_senior": 550,
            "risque_metier": "moyen",
            "note": "Evaluer la demande locale et sectorielle avant de se lancer.",
        },
    }
    sect = SECTEURS.get(secteur, SECTEURS["autre"])

    ACTIVITES_PARAMS = {
        "services_bnc": {"taux_ae_cotis": 0.231, "abatt_ae_ir": 0.34, "seuil_ae": 77_700},
        "services_bic": {"taux_ae_cotis": 0.214, "abatt_ae_ir": 0.50, "seuil_ae": 77_700},
        "vente_marchandises": {"taux_ae_cotis": 0.128, "abatt_ae_ir": 0.71, "seuil_ae": 188_700},
    }
    act = ACTIVITES_PARAMS.get(type_activite, ACTIVITES_PARAMS["services_bnc"])

    # ── Net CDI de reference ──────────────────────────────────────────────────
    net_salarie_cdi = salaire_brut_cdi * 0.78
    abatt_cdi = min(14_426, max(495, net_salarie_cdi * 0.10))
    rni_cdi = max(0, net_salarie_cdi - abatt_cdi)
    ir_cdi = calculer_ir(rni_cdi, nb_parts)["impot_net"]
    net_cdi = round(net_salarie_cdi - ir_cdi)
    net_cdi_mensuel = round(net_cdi / 12)

    # ── TJM minimum pour egaliser le CDI (SASU comme reference principale) ────
    def tjm_equiv_sasu(net_ref: float) -> int:
        SMIC_BRUT = 21_622
        lo, hi = 0.0, 10_000.0
        for _ in range(60):
            mid = (lo + hi) / 2
            ca = mid * jours
            cout_sal = SMIC_BRUT * 1.55
            is_base = max(0, ca - cout_sal)
            is_tot = min(is_base, 42_500) * 0.15 + max(0, is_base - 42_500) * 0.25
            div_net = max(0, is_base - is_tot) * 0.70
            net_smic = SMIC_BRUT * 0.77
            ir_s = calculer_ir(max(0, net_smic - min(14_426, max(495, net_smic * 0.10))), nb_parts)["impot_net"]
            net = net_smic - ir_s + div_net
            if net < net_ref:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2)

    tjm_min_sasu = tjm_equiv_sasu(net_cdi)

    # ── Net freelance avec le TJM vise ───────────────────────────────────────
    tjm_calcul = tjm_vise if tjm_vise > 0 else (
        sect["tjm_senior"] if anciennete_ans >= 8 else sect["tjm_median"]
    )
    ca_vise = tjm_calcul * jours

    # Simulation SASU
    SMIC_BRUT = 21_622
    cout_sal_sasu = round(SMIC_BRUT * 1.55)
    net_smic_sasu = round(SMIC_BRUT * 0.77)
    is_base_sasu = max(0, ca_vise - cout_sal_sasu)
    is_tot_sasu = round(min(is_base_sasu, 42_500) * 0.15 + max(0, is_base_sasu - 42_500) * 0.25)
    div_nets_sasu = round(max(0, is_base_sasu - is_tot_sasu) * 0.70)
    ir_smic_sasu = round(calculer_ir(max(0, net_smic_sasu - min(14_426, max(495, net_smic_sasu * 0.10))), nb_parts)["impot_net"])
    net_freelance_sasu = net_smic_sasu - ir_smic_sasu + div_nets_sasu

    # Simulation AE (si dans les seuils)
    ca_ae_ok = ca_vise <= act["seuil_ae"]
    cotis_ae = round(ca_vise * act["taux_ae_cotis"])
    rni_ae = max(0, ca_vise * (1 - act["abatt_ae_ir"]))
    ir_ae = round(calculer_ir(rni_ae, nb_parts)["impot_net"])
    net_freelance_ae = round(ca_vise - cotis_ae - ir_ae)

    gain_sasu = net_freelance_sasu - net_cdi
    gain_pct_sasu = round(gain_sasu / net_cdi * 100, 1) if net_cdi > 0 else 0

    # ── Buffer de securite ────────────────────────────────────────────────────
    charges_ref = charges_mensuelles if charges_mensuelles > 0 else net_cdi_mensuel
    mois_buffer = round(epargne_disponible / charges_ref, 1) if charges_ref > 0 else 0

    # ── Scoring (0-12) ────────────────────────────────────────────────────────
    score = 0
    details_score = []

    # 1. Epargne (0-3)
    if mois_buffer >= 12:
        pts = 3; detail = f"Epargne >= 12 mois ({mois_buffer:.1f} mois) — tres solide"
    elif mois_buffer >= 6:
        pts = 2; detail = f"Epargne 6-12 mois ({mois_buffer:.1f} mois) — suffisante"
    elif mois_buffer >= 3:
        pts = 1; detail = f"Epargne 3-6 mois ({mois_buffer:.1f} mois) — limite, a renforcer"
    else:
        pts = 0; detail = f"Epargne < 3 mois ({mois_buffer:.1f} mois) — insuffisante"
    score += pts
    details_score.append((f"Epargne de securite", pts, 3, detail))

    # 2. Experience (0-2)
    if anciennete_ans >= 8:
        pts = 2; detail = f"{anciennete_ans} ans d'experience — profil senior, TJM eleve justifie"
    elif anciennete_ans >= 3:
        pts = 1; detail = f"{anciennete_ans} ans d'experience — suffisant pour se lancer"
    else:
        pts = 0; detail = f"{anciennete_ans} an(s) — experience limitee, risque de sous-facturation"
    score += pts
    details_score.append(("Experience professionnelle", pts, 2, detail))

    # 3. Reseau / clients potentiels (0-2)
    if clients_potentiels:
        pts = 2; detail = "Reseau / mission en vue — demarrage sans periode blanche probable"
    else:
        pts = 0; detail = "Pas de prospect identifie — periode de demarrage a anticiper (2-6 mois)"
    score += pts
    details_score.append(("Reseau et prospects", pts, 2, detail))

    # 4. Demande sectorielle (0-2)
    d = sect["demande"]
    if d >= 5:
        pts = 2; detail = f"Demande tres forte ({sect['label']})"
    elif d >= 4:
        pts = 2; detail = f"Demande forte ({sect['label']})"
    elif d >= 3:
        pts = 1; detail = f"Demande moderee ({sect['label']})"
    else:
        pts = 0; detail = f"Demande faible ({sect['label']}) — niche ou reinvention necessaire"
    score += pts
    details_score.append(("Demande sectorielle", pts, 2, detail))

    # 5. Gain financier potentiel (0-2)
    if gain_pct_sasu >= 20:
        pts = 2; detail = f"Gain net potentiel : +{gain_pct_sasu:.1f} % par rapport au CDI"
    elif gain_pct_sasu >= 5:
        pts = 1; detail = f"Gain net modere : +{gain_pct_sasu:.1f} % par rapport au CDI"
    elif gain_pct_sasu >= 0:
        pts = 1; detail = f"Gain marginal : +{gain_pct_sasu:.1f} % — interet surtout non financier"
    else:
        pts = 0; detail = f"Gain negatif au TJM cible ({tjm_calcul:.0f} EUR/j) : {gain_pct_sasu:.1f} % vs CDI"
    score += pts
    details_score.append(("Gain financier potentiel", pts, 2, detail))

    # 6. Coherence risque / situation (0-1)
    charge_familiale = nb_enfants > 0 or situation in ("marie", "pacse")
    if acceptation_risque == "eleve":
        pts = 1; detail = "Forte tolerance au risque — compatible avec le saut freelance"
    elif acceptation_risque == "moyen" and not charge_familiale:
        pts = 1; detail = "Risque moyen, sans charge familiale lourde — acceptable"
    elif acceptation_risque == "moyen" and charge_familiale:
        pts = 0; detail = "Risque moyen avec charge familiale — renforcer l'epargne avant"
    else:  # faible
        pts = 0; detail = "Faible tolerance au risque — portage salarial ou transition progressive conseillee"
    score += pts
    details_score.append(("Profil risque / situation", pts, 1, detail))

    # ── Verdict ────────────────────────────────────────────────────────────────
    if score >= 10:
        verdict = "FAVORABLE — Passer freelance est pertinent maintenant"
        verdict_court = "Passer maintenant"
        couleur = "+++"
    elif score >= 7:
        verdict = "FAVORABLE SOUS CONDITIONS — Le passage est envisageable avec quelques ajustements"
        verdict_court = "Envisageable"
        couleur = "++"
    elif score >= 4:
        verdict = "A PREPARER — Des conditions cles ne sont pas reunies. Planifier sur 6-18 mois."
        verdict_court = "Preparer le passage"
        couleur = "+"
    else:
        verdict = "DECONSEILLE A CE STADE — Consolider d'abord experience, epargne et reseau"
        verdict_court = "Trop tot"
        couleur = "---"

    # ── TJM cible recommande ──────────────────────────────────────────────────
    tjm_cible_conservateur = round(tjm_min_sasu * 1.15)  # +15% pour inter-contrats

    # ── Mise en garde specifique situations a risque ─────────────────────────
    alertes = []
    if mois_buffer < 3:
        alertes.append("Epargne critique : constituer au minimum 3 mois de charges avant de quitter le CDI.")
    if not clients_potentiels and score >= 7:
        alertes.append("Aucun prospect identifie : demarrer la prospection 3 a 6 mois avant la demission.")
    if anciennete_ans < 3:
        alertes.append("Moins de 3 ans d'experience : risque de difficultes a justifier un TJM de marche.")
    if charge_familiale and mois_buffer < 6:
        alertes.append("Charge familiale avec epargne < 6 mois : considerez le portage salarial comme etape intermediaire.")
    if ca_vise > act["seuil_ae"]:
        alertes.append(f"CA vise ({ca_vise:,.0f} EUR) depasse le seuil AE ({act['seuil_ae']:,} EUR) : SASU ou EURL requis.")
    if gain_pct_sasu < 0 and tjm_vise > 0:
        alertes.append(f"Le TJM vise ({tjm_vise:.0f} EUR/j) ne permet pas d'egaliser le CDI. TJM minimum SASU : {tjm_min_sasu:,} EUR/j.")

    # ── Assemblage ─────────────────────────────────────────────────────────────
    lines = [
        "# Diagnostic Passage Freelance",
        "",
        f"*Simulation indicative — Bareme {ANNEE_FISCALE}*",
        "",
        "## Profil analyse",
        "",
        f"- Salaire CDI brut : {salaire_brut_cdi:,.0f} EUR/an — net en poche : {net_cdi:,} EUR/an ({net_cdi_mensuel:,} EUR/mois)",
        f"- Secteur : {sect['label']}",
        f"- Experience : {anciennete_ans} an(s)",
        f"- Epargne disponible : {epargne_disponible:,.0f} EUR ({mois_buffer:.1f} mois de charges)",
        f"- Reseau / prospects : {'Oui' if clients_potentiels else 'Non'}",
        f"- Situation familiale : {situation}, {nb_enfants} enfant(s)",
        f"- Tolerance au risque : {acceptation_risque}",
        f"- Regime fiscal vise : {type_activite}",
        "",
    ]

    lines += [
        "## Score de maturite freelance",
        "",
        f"**Score global : {score} / 12**",
        "",
        "| Critere | Points | Max | Detail |",
        "|---------|--------|-----|--------|",
    ]
    for nom, pts, maxi, det in details_score:
        lines.append(f"| {nom} | {pts} | {maxi} | {det} |")
    lines.append("")

    lines += [
        "## Verdict",
        "",
        f"**{couleur} {verdict}**",
        "",
    ]

    if alertes:
        lines += [
            "### Points de vigilance",
            "",
        ]
        for a in alertes:
            lines.append(f"- {a}")
        lines.append("")

    lines += [
        "## Projection financiere",
        "",
        f"*TJM analyse : {tjm_calcul:.0f} EUR/j HT — {jours} jours factures/an — CA : {ca_vise:,.0f} EUR*",
        "",
        "| Scenario | Net annuel | vs CDI |",
        "|----------|-----------|--------|",
        f"| CDI actuel | {net_cdi:,} EUR | reference |",
    ]
    if ca_ae_ok:
        lines.append(f"| Auto-entrepreneur | {net_freelance_ae:,} EUR | {'+' if net_freelance_ae > net_cdi else ''}{net_freelance_ae - net_cdi:,} EUR |")
    lines += [
        f"| SASU (SMIC + dividendes) | {net_freelance_sasu:,} EUR | {'+' if net_freelance_sasu > net_cdi else ''}{net_freelance_sasu - net_cdi:,} EUR |",
        "",
    ]

    lines += [
        "## TJM cible",
        "",
        f"| Objectif | TJM | CA annuel ({jours} j) |",
        "|----------|-----|----------------------|",
        f"| Egaliser le CDI net (SASU) | {tjm_min_sasu:,} EUR/j | {tjm_min_sasu * jours:,} EUR |",
        f"| TJM recommande (+15% inter-contrats) | {tjm_cible_conservateur:,} EUR/j | {tjm_cible_conservateur * jours:,} EUR |",
        f"| Median du secteur | {sect['tjm_median']:,} EUR/j | {sect['tjm_median'] * jours:,} EUR |",
        f"| Senior du secteur (>= 8 ans) | {sect['tjm_senior']:,} EUR/j | {sect['tjm_senior'] * jours:,} EUR |",
        "",
    ]

    lines += [
        "## Analyse du secteur",
        "",
        f"- Demande marche : {'*' * sect['demande']} ({sect['demande']}/5)",
        f"- Risque metier : {sect['risque_metier']}",
        f"- Note : {sect['note']}",
        "",
    ]

    lines += [
        "## Preparation recommandee avant le saut",
        "",
        "1. Epargne : constituer 6 a 12 mois de charges mensuelles avant de quitter le CDI",
        "2. Reseau : identifier 2 a 3 clients potentiels ou une mission de demarrage",
        "3. Statut : immatriculer SASU ou AE avant la demission (delai d'immatriculation : 1-5 jours)",
        "4. Couverture : souscrire une RC Pro et mutuelle independant avant le depart",
        "5. Transition : negocier une rupture conventionnelle pour conserver les droits au chomage (ARE)",
        "   (ARE en independant : possible si CA < seuil ou en portage, a verifier Pole Emploi)",
        "6. Expert-comptable : prevoir 1 500 a 2 500 EUR/an (SASU/EURL) ou 500 EUR (AE)",
        "",
        "## Alternatives au saut direct",
        "",
        "- **Portage salarial** : tester sans creation de structure, conserver le chomage, charges ~8%",
        "- **Cumuler CDI + activite annexe** : AE en micro pendant le CDI (accord employeur requis)",
        "- **Negocier un temps partiel** : 4 jours/5 pour tester le marche en parallele",
        "",
        "---",
        f"*Simulation basee sur les taux {ANNEE_FISCALE}. Consultez un expert-comptable avant toute decision.*",
    ]
    return "\n".join(lines)


# ─── Point d'entrée ──────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
