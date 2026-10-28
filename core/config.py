"""
Configuration centrale d'InfraRent Africa.

Toutes les constantes métier (seuils, listes de choix, couleurs, chemins)
sont regroupées ici : pour adapter l'application à un autre chantier,
c'est le seul fichier à modifier dans 90 % des cas.
"""
from pathlib import Path

# --------------------------------------------------------------------------- #
# Chemins de stockage (CSV)
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
FLOTTE_CSV = DATA_DIR / "flotte.csv"
SAISIES_CSV = DATA_DIR / "saisies.csv"
MAINTENANCE_CSV = DATA_DIR / "maintenance.csv"

# --------------------------------------------------------------------------- #
# Identité de l'application
# --------------------------------------------------------------------------- #
APP_NAME = "InfraRent Africa"
APP_TAGLINE = "Gestion d'actifs de chantier · BTP Cameroun"
CURRENCY = "FCFA"
UTC_OFFSET_HOURS = 1  # Cameroun : UTC+1, pas d'heure d'été

# --------------------------------------------------------------------------- #
# Listes de choix métier
# --------------------------------------------------------------------------- #
TYPES_ENGINS = ["Pelle hydraulique", "Camion-benne", "Compacteur", "Chargeuse"]

ZONES_TACHES = {
    "Pelle hydraulique": ["Terrassement", "Fouilles / tranchées", "Chargement de camions", "Démolition"],
    "Camion-benne": ["Transport de matériaux", "Évacuation des déblais", "Approvisionnement en granulats"],
    "Compacteur": ["Compactage plateforme", "Compactage couche de base", "Compactage enrobé"],
    "Chargeuse": ["Chargement de matériaux", "Terrassement", "Approvisionnement centrale"],
}
ZONES_AUTRES = ["Autre (voir description)"]

STATUT_SERVICE = "En service"
STATUT_PANNE = "En panne"
STATUT_PIECE = "En attente de pièce"
STATUTS = [STATUT_SERVICE, STATUT_PANNE, STATUT_PIECE]

GRAVITE_AUCUN = "Aucun"
GRAVITE_MINEURE = "Mineure"
GRAVITE_MAJEURE = "Majeure"
GRAVITES = [GRAVITE_AUCUN, GRAVITE_MINEURE, GRAVITE_MAJEURE]

CATEGORIES_INCIDENT = [
    "Panne mécanique",
    "Panne hydraulique / électrique",
    "Accident matériel",
    "Presque-accident (sécurité)",
    "Fuite / pollution",
    "Autre",
]

TYPES_INTERVENTION = [
    "Vidange moteur",
    "Réparation",
    "Remplacement de pièce",
    "Inspection / contrôle",
]
INTERVENTION_VIDANGE = "Vidange moteur"

# --------------------------------------------------------------------------- #
# Règles métier et seuils
# --------------------------------------------------------------------------- #
PRIX_GASOIL_DEFAUT = 730          # FCFA / litre (prix à la pompe, à ajuster)
INTERVALLE_VIDANGE_DEFAUT = 250   # heures de marche entre deux vidanges
SEUIL_ORANGE_VIDANGE = 0.80       # orange dès 80 % de l'intervalle (200 h)
SEUIL_SURCONSO_ORANGE = 0.15      # +15 % vs consommation de référence
SEUIL_SURCONSO_ROUGE = 0.30       # +30 % vs consommation de référence
SEUIL_DISPO_ORANGE = 85.0         # % de disponibilité
SEUIL_DISPO_ROUGE = 70.0

# --------------------------------------------------------------------------- #
# Rôles
# --------------------------------------------------------------------------- #
ROLE_CHEF = "chef"
ROLE_ADMIN = "admin"
ROLE_LABELS = {
    ROLE_CHEF: "Chef de Chantier",
    ROLE_ADMIN: "Administrateur / Directeur de Projet",
}

# --------------------------------------------------------------------------- #
# Palette (gris technique, bleu foncé, accents orange / vert / rouge)
# --------------------------------------------------------------------------- #
COLORS = {
    "navy": "#12355B",
    "navy_light": "#2A5688",
    "steel": "#5B6770",
    "grey": "#8A949C",
    "grey_light": "#E3E7EB",
    "bg": "#F3F5F7",
    "ok": "#2E9E5B",
    "warn": "#F28C28",
    "danger": "#C8372D",
}
STATUT_COLORS = {
    STATUT_SERVICE: COLORS["ok"],
    STATUT_PANNE: COLORS["danger"],
    STATUT_PIECE: COLORS["warn"],
}
GRAVITE_COLORS = {
    GRAVITE_MINEURE: COLORS["warn"],
    GRAVITE_MAJEURE: COLORS["danger"],
}
NIVEAU_COLORS = {"vert": COLORS["ok"], "orange": COLORS["warn"], "rouge": COLORS["danger"]}

# --------------------------------------------------------------------------- #
# Comptes de démonstration
# (remplacés par st.secrets["users"] dès que ce bloc existe — voir README)
# --------------------------------------------------------------------------- #
DEMO_USERS = {
    "directeur": {"password": "Infra@2026", "role": ROLE_ADMIN, "nom": "Directeur de Projet"},
    "chef1": {"password": "Chantier@1", "role": ROLE_CHEF, "nom": "Chef de Chantier – Zone A"},
    "chef2": {"password": "Chantier@2", "role": ROLE_CHEF, "nom": "Chef de Chantier – Zone B"},
}
