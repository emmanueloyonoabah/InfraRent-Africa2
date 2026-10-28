"""
Couche d'accès aux données (stockage CSV local).

Trois fichiers dans /data :
  - flotte.csv       : référentiel des engins (1 ligne = 1 engin)
  - saisies.csv      : relevés quotidiens du terrain (1 ligne = 1 engin x 1 jour)
  - maintenance.csv  : interventions (vidanges, réparations, inspections)

Au premier lancement, un jeu de données de démonstration est généré pour que
les tableaux de bord ne soient pas vides.
"""
import os
import threading
import uuid
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from core import config

FLOTTE_COLS = [
    "engin_id", "type_engin", "designation", "immatriculation",
    "conso_ref_lh", "cout_entretien_h", "intervalle_vidange_h", "horametre_initial",
]
SAISIES_COLS = [
    "id", "date", "engin_id", "type_engin", "heures", "carburant_l", "zone_tache",
    "statut", "categorie_incident", "gravite_hse", "description_incident",
    "saisi_par", "horodatage",
]
MAINTENANCE_COLS = [
    "id", "date", "engin_id", "type_intervention", "horametre", "cout_fcfa",
    "description", "saisi_par", "horodatage",
]

_NUM_FLOTTE = ["conso_ref_lh", "cout_entretien_h", "intervalle_vidange_h", "horametre_initial"]
_lock = threading.Lock()  # protège les réécritures complètes de fichiers


# --------------------------------------------------------------------------- #
# Temps (Cameroun, UTC+1)
# --------------------------------------------------------------------------- #
def now_local() -> datetime:
    return datetime.now(timezone(timedelta(hours=config.UTC_OFFSET_HOURS)))


def today_local() -> date:
    return now_local().date()


def new_id() -> str:
    return uuid.uuid4().hex[:10]


# --------------------------------------------------------------------------- #
# Lecture / écriture bas niveau
# --------------------------------------------------------------------------- #
def _read(path, columns: list[str]) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for col in columns:  # tolère un fichier ancien auquel il manque des colonnes
        if col not in df.columns:
            df[col] = ""
    return df[columns]


def _write(path, df: pd.DataFrame) -> None:
    """Écriture atomique : fichier temporaire puis remplacement."""
    with _lock:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)


def _append(path, row: dict, columns: list[str]) -> None:
    with _lock:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        new_file = not path.exists() or path.stat().st_size == 0
        pd.DataFrame([row], columns=columns).to_csv(path, mode="a", header=new_file, index=False)


# --------------------------------------------------------------------------- #
# Flotte
# --------------------------------------------------------------------------- #
def load_flotte() -> pd.DataFrame:
    df = _read(config.FLOTTE_CSV, FLOTTE_COLS)
    for col in _NUM_FLOTTE:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["intervalle_vidange_h"] = df["intervalle_vidange_h"].fillna(config.INTERVALLE_VIDANGE_DEFAUT)
    df["horametre_initial"] = df["horametre_initial"].fillna(0)
    return df


def validate_flotte(df: pd.DataFrame) -> list[str]:
    """Retourne la liste des erreurs de validation (vide si tout est correct)."""
    erreurs = []
    if df.empty:
        return ["Le parc doit contenir au moins un engin."]
    ids = df["engin_id"].astype(str).str.strip()
    if (ids == "").any() or df["engin_id"].isna().any():
        erreurs.append("Chaque engin doit avoir un identifiant.")
    if ids.duplicated().any():
        erreurs.append("Les identifiants d'engins doivent être uniques.")
    if not df["type_engin"].isin(config.TYPES_ENGINS).all():
        erreurs.append(f"Type d'engin invalide (valeurs permises : {', '.join(config.TYPES_ENGINS)}).")
    for col in ("conso_ref_lh", "cout_entretien_h", "intervalle_vidange_h"):
        if df[col].isna().any() or (pd.to_numeric(df[col], errors="coerce") <= 0).any():
            erreurs.append(f"La colonne « {col} » doit contenir des nombres strictement positifs.")
    return erreurs


def save_flotte(df: pd.DataFrame) -> None:
    out = df[FLOTTE_COLS].copy()
    out["engin_id"] = out["engin_id"].astype(str).str.strip().str.upper()
    _write(config.FLOTTE_CSV, out)


# --------------------------------------------------------------------------- #
# Saisies terrain
# --------------------------------------------------------------------------- #
def load_saisies() -> pd.DataFrame:
    df = _read(config.SAISIES_CSV, SAISIES_COLS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["heures"] = pd.to_numeric(df["heures"], errors="coerce").fillna(0.0)
    df["carburant_l"] = pd.to_numeric(df["carburant_l"], errors="coerce").fillna(0.0)
    return df.dropna(subset=["date"]).sort_values(["date", "engin_id"]).reset_index(drop=True)


def saisie_existe(jour: date, engin_id: str) -> bool:
    df = load_saisies()
    return bool(((df["date"].dt.date == jour) & (df["engin_id"] == engin_id)).any())


def save_saisie(row: dict, remplacer: bool = False) -> None:
    """
    Enregistre une saisie. Si `remplacer` est vrai, la saisie existante du même
    engin pour la même date est supprimée (correction d'une erreur de saisie).
    """
    row = {**row, "id": new_id(), "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d")}
    if remplacer:
        df = _read(config.SAISIES_CSV, SAISIES_COLS)
        garde = ~((df["date"] == row["date"]) & (df["engin_id"] == row["engin_id"]))
        df = pd.concat([df[garde], pd.DataFrame([row], columns=SAISIES_COLS)], ignore_index=True)
        _write(config.SAISIES_CSV, df)
    else:
        _append(config.SAISIES_CSV, row, SAISIES_COLS)


def replace_saisies(df: pd.DataFrame) -> None:
    out = df[SAISIES_COLS].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    _write(config.SAISIES_CSV, out)


# --------------------------------------------------------------------------- #
# Maintenance
# --------------------------------------------------------------------------- #
def load_maintenance() -> pd.DataFrame:
    df = _read(config.MAINTENANCE_CSV, MAINTENANCE_COLS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["horametre"] = pd.to_numeric(df["horametre"], errors="coerce")
    df["cout_fcfa"] = pd.to_numeric(df["cout_fcfa"], errors="coerce").fillna(0.0)
    return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def replace_maintenance(df: pd.DataFrame) -> None:
    out = df[MAINTENANCE_COLS].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    _write(config.MAINTENANCE_CSV, out)


def save_maintenance(row: dict) -> None:
    row = {**row, "id": new_id(), "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d")}
    _append(config.MAINTENANCE_CSV, row, MAINTENANCE_COLS)


# --------------------------------------------------------------------------- #
# Initialisation et réinitialisation
# --------------------------------------------------------------------------- #
def init_storage() -> None:
    """Crée les fichiers manquants (jeu de démo au tout premier lancement)."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    paths = (config.FLOTTE_CSV, config.SAISIES_CSV, config.MAINTENANCE_CSV)
    if not any(p.exists() for p in paths):
        seed_demo()
        return
    for path, cols in zip(paths, (FLOTTE_COLS, SAISIES_COLS, MAINTENANCE_COLS)):
        if not path.exists():
            _write(path, pd.DataFrame(columns=cols))


def seed_demo() -> None:
    flotte, saisies, maintenance = _generate_demo()
    _write(config.FLOTTE_CSV, flotte)
    _write(config.SAISIES_CSV, saisies)
    _write(config.MAINTENANCE_CSV, maintenance)


def clear_operational_data() -> None:
    """Vide saisies et maintenance, conserve le parc d'engins."""
    _write(config.SAISIES_CSV, pd.DataFrame(columns=SAISIES_COLS))
    _write(config.MAINTENANCE_CSV, pd.DataFrame(columns=MAINTENANCE_COLS))


# --------------------------------------------------------------------------- #
# Jeu de données de démonstration (reproductible : graine fixe)
# --------------------------------------------------------------------------- #
# id, type, désignation, immatriculation / n° série, L/h réf., entretien FCFA/h,
# intervalle vidange, horamètre initial,
# heures déjà faites au début de la période depuis la dernière vidange,
# vidange réalisée pendant la période (« il y a N jours », None = aucune)
# -> avec ~205 h de marche sur la période, donne 2 engins rouges, 3 orange, 5 verts.
_DEMO_PARC = [
    ("PH-01", "Pelle hydraulique", "Caterpillar 320D", "SN-CAT320-0412", 18.0, 9500, 250, 6420, 60, None),
    ("PH-02", "Pelle hydraulique", "Komatsu PC210-8", "SN-KOM210-1187", 16.5, 8800, 250, 4875, 6, None),
    ("PH-03", "Pelle hydraulique", "Hyundai R220LC-9S", "SN-HYU220-0733", 16.0, 8200, 250, 3310, 140, 20),
    ("CB-01", "Camion-benne", "Howo 6x4 - 25 t", "LT 4521 AB", 14.0, 6200, 250, 7240, 4, None),
    ("CB-02", "Camion-benne", "Sinotruk 8x4 - 30 t", "LT 7788 CD", 15.0, 6800, 250, 5120, 10, None),
    ("CB-03", "Camion-benne", "Mercedes Actros 3341", "CE 2290 EF", 13.5, 7200, 250, 8950, 120, 30),
    ("CP-01", "Compacteur", "Bomag BW 213 D-4", "SN-BOM213-5521", 10.5, 5500, 250, 3980, 90, 12),
    ("CP-02", "Compacteur", "Dynapac CA2500", "SN-DYN250-2204", 9.5, 5200, 250, 2650, 100, 18),
    ("CH-01", "Chargeuse", "Caterpillar 950H", "SN-CAT950-0876", 15.0, 8000, 250, 9110, 110, None),
    ("CH-02", "Chargeuse", "Volvo L90H", "SN-VOL090-3340", 13.0, 7400, 250, 4470, 130, 25),
]

# Pannes de démonstration : (engin, début en "jours avant aujourd'hui", durée en jours,
#                            catégorie, gravité, description, coût de réparation FCFA)
_DEMO_PANNES = [
    ("PH-01", 24, 3, "Panne hydraulique / électrique", "Majeure", "Rupture flexible hydraulique du bras, fuite d'huile importante", 480000),
    ("CP-01", 15, 2, "Panne mécanique", "Mineure", "Courroie d'alternateur détendue, surchauffe", 85000),
    ("CB-03", 11, 2, "Accident matériel", "Majeure", "Choc contre un poteau en marche arrière, feu arrière et aile endommagés", 320000),
    ("CH-02", 8, 1, "Panne hydraulique / électrique", "Mineure", "Capteur de pression défectueux, voyant allumé", 60000),
    ("PH-03", 5, 6, "Panne mécanique", "Majeure", "Turbo hors service, pièce commandée à Douala", 0),   # en cours
    ("CB-02", 2, 3, "Panne mécanique", "Majeure", "Boîte de vitesses : passage du 3e rapport impossible", 0),  # en cours
]

_DEMO_INCIDENTS_MINEURS = [
    ("Fuite / pollution", "Petite fuite de gasoil au bouchon de réservoir, sol absorbé et nettoyé"),
    ("Presque-accident (sécurité)", "Personnel à pied dans la zone de manœuvre, arrêt immédiat de l'engin"),
    ("Presque-accident (sécurité)", "Recul sans signaleur, rappel des consignes au conducteur"),
    ("Fuite / pollution", "Suintement d'huile moteur constaté au démarrage"),
]


def _generate_demo(n_jours: int = 35):
    rng = np.random.default_rng(42)
    fin = today_local()
    debut = fin - timedelta(days=n_jours - 1)
    jours = [debut + timedelta(days=i) for i in range(n_jours) if (debut + timedelta(days=i)).weekday() != 6]

    flotte = pd.DataFrame([p[:8] for p in _DEMO_PARC], columns=FLOTTE_COLS)
    chefs = ["Chef de Chantier – Zone A (chef1)", "Chef de Chantier – Zone B (chef2)"]
    # Surconsommations de démo : CH-01 chroniquement élevée (+22 %), PH-02 pics ponctuels
    facteur_conso = {"CH-01": 1.22}

    pannes_par_engin: dict[str, list] = {}
    for p in _DEMO_PANNES:
        pannes_par_engin.setdefault(p[0], []).append(p)

    def jours_ouvres_panne(depart: int, duree: int) -> list:
        """Jours (hors dimanche) couverts par une panne démarrée il y a `depart` jours."""
        jours_panne = [fin - timedelta(days=depart - k) for k in range(duree)]
        return [j for j in jours_panne if j.weekday() != 6]

    lignes, maint = [], []
    for idx, (eid, typ, _des, _imm, ref, _ent, inter, h0, depuis, vidange_il_y_a) in enumerate(_DEMO_PARC):
        # Vidange de référence, datée avant le début de la période
        maint.append(dict(
            id=new_id(), date=(debut - timedelta(days=12)).isoformat(), engin_id=eid,
            type_intervention=config.INTERVENTION_VIDANGE, horametre=h0 - depuis, cout_fcfa=65000,
            description="Vidange moteur + filtres à huile et gasoil",
            saisi_par="Directeur de Projet (directeur)", horodatage=f"{debut - timedelta(days=12)} 16:00:00",
        ))
        for jour in jours:
            ecart_jours = (fin - jour).days
            panne = next(
                (p for p in pannes_par_engin.get(eid, []) if jour in jours_ouvres_panne(p[1], p[2])), None
            )
            statut, heures, carb = config.STATUT_SERVICE, 0.0, 0.0
            cat, grav, desc = "", config.GRAVITE_AUCUN, ""
            zone = str(rng.choice(config.ZONES_TACHES[typ]))

            if panne:
                _, depart, duree, p_cat, p_grav, p_desc, _cout = panne
                rang = jours_ouvres_panne(depart, duree).index(jour)  # 0 = premier jour ouvré de panne
                statut = config.STATUT_PANNE if rang < 2 else config.STATUT_PIECE
                if rang == 0:
                    cat, grav, desc = p_cat, p_grav, p_desc
                    heures = round(float(rng.uniform(1.0, 3.0)), 1)
                    carb = round(heures * ref * rng.normal(1.0, 0.05))
            else:
                heures = round(float(np.clip(rng.normal(7.4, 1.0), 4.5, 9.5)), 1)
                facteur = facteur_conso.get(eid, 1.0) * rng.normal(1.0, 0.05)
                if eid == "PH-02" and ecart_jours in (4, 9):  # pics de consommation
                    facteur *= 1.45
                carb = round(heures * ref * facteur)
                if rng.random() < 0.035:  # incident mineur sans immobilisation
                    cat, desc = _DEMO_INCIDENTS_MINEURS[int(rng.integers(len(_DEMO_INCIDENTS_MINEURS)))]
                    grav = config.GRAVITE_MINEURE

            lignes.append(dict(
                id=new_id(), date=jour.isoformat(), engin_id=eid, type_engin=typ,
                heures=heures, carburant_l=carb, zone_tache=zone, statut=statut,
                categorie_incident=cat, gravite_hse=grav, description_incident=desc,
                saisi_par=chefs[idx % 2],
                horodatage=f"{jour} 17:{int(rng.integers(0, 59)):02d}:{int(rng.integers(0, 59)):02d}",
            ))

        # Vidange réalisée pendant la période : remet le compteur d'alerte à zéro
        if vidange_il_y_a is not None:
            date_vid = (fin - timedelta(days=vidange_il_y_a)).isoformat()
            fait = sum(l["heures"] for l in lignes if l["engin_id"] == eid and l["date"] <= date_vid)
            maint.append(dict(
                id=new_id(), date=date_vid, engin_id=eid, type_intervention=config.INTERVENTION_VIDANGE,
                horametre=round(h0 + fait, 1), cout_fcfa=65000,
                description="Vidange moteur + filtres à huile et gasoil",
                saisi_par="Directeur de Projet (directeur)", horodatage=f"{date_vid} 16:00:00",
            ))

        # Réparations facturées pour les pannes déjà résolues
        for _, depart, duree, p_cat, _g, p_desc, cout in pannes_par_engin.get(eid, []):
            if cout > 0:
                date_rep = fin - timedelta(days=depart - duree)
                maint.append(dict(
                    id=new_id(), date=date_rep.isoformat(), engin_id=eid, type_intervention="Réparation",
                    horametre=round(h0 + float(np.sum([l["heures"] for l in lignes if l["engin_id"] == eid and l["date"] <= date_rep.isoformat()])), 1),
                    cout_fcfa=cout, description=p_desc, saisi_par="Directeur de Projet (directeur)",
                    horodatage=f"{date_rep} 15:30:00",
                ))

    return flotte, pd.DataFrame(lignes, columns=SAISIES_COLS), pd.DataFrame(maint, columns=MAINTENANCE_COLS)
