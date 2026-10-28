"""
Calculs métier : coûts, consommation, disponibilité, maintenance préventive, pannes.

Toutes les fonctions sont pures (DataFrame en entrée, DataFrame / valeur en sortie)
et n'utilisent pas Streamlit : elles restent testables et réutilisables.
"""
import numpy as np
import pandas as pd

from core import config


# --------------------------------------------------------------------------- #
# Enrichissement des saisies
# --------------------------------------------------------------------------- #
def enrich(saisies: pd.DataFrame, flotte: pd.DataFrame, prix_gasoil: float) -> pd.DataFrame:
    """Ajoute à chaque saisie : coûts, L/h et écart vs consommation de référence."""
    ref = flotte[["engin_id", "designation", "conso_ref_lh", "cout_entretien_h"]]
    df = saisies.merge(ref, on="engin_id", how="left")
    df["en_service"] = df["statut"] == config.STATUT_SERVICE
    df["cout_carburant"] = df["carburant_l"] * prix_gasoil
    df["cout_entretien"] = df["heures"] * df["cout_entretien_h"].fillna(0)
    df["cout_total"] = df["cout_carburant"] + df["cout_entretien"]
    df["lh"] = np.where(df["heures"] > 0, df["carburant_l"] / df["heures"].replace(0, np.nan), np.nan)
    df["ecart_conso"] = df["lh"] / df["conso_ref_lh"] - 1  # ex. 0.28 = +28 %
    return df


def niveau_surconso(ecart: float) -> str:
    if pd.isna(ecart):
        return "vert"
    if ecart >= config.SEUIL_SURCONSO_ROUGE:
        return "rouge"
    if ecart >= config.SEUIL_SURCONSO_ORANGE:
        return "orange"
    return "vert"


def niveau_dispo(dispo_pct: float) -> str:
    if pd.isna(dispo_pct):
        return "vert"
    if dispo_pct < config.SEUIL_DISPO_ROUGE:
        return "rouge"
    if dispo_pct < config.SEUIL_DISPO_ORANGE:
        return "orange"
    return "vert"


# --------------------------------------------------------------------------- #
# Agrégats
# --------------------------------------------------------------------------- #
def _ratio(num, den):
    return num / den if den and den > 0 else np.nan


def summary(df: pd.DataFrame) -> dict:
    """KPIs globaux sur un ensemble de saisies déjà enrichies."""
    if df.empty:
        return dict(heures=0.0, carburant=0.0, lh=np.nan, cout_horaire=np.nan, cout_total=0.0,
                    dispo=np.nan, nb_incidents=0, nb_majeurs=0, jours_engins=0)
    heures = df["heures"].sum()
    carburant = df["carburant_l"].sum()
    return dict(
        heures=heures,
        carburant=carburant,
        lh=_ratio(carburant, heures),
        cout_horaire=_ratio(df["cout_total"].sum(), heures),
        cout_total=df["cout_total"].sum(),
        dispo=df["en_service"].mean() * 100,
        nb_incidents=int((df["gravite_hse"] != config.GRAVITE_AUCUN).sum()),
        nb_majeurs=int((df["gravite_hse"] == config.GRAVITE_MAJEURE).sum()),
        jours_engins=len(df),
    )


def par_engin(df: pd.DataFrame, flotte: pd.DataFrame) -> pd.DataFrame:
    """Tableau de synthèse : une ligne par engin ayant au moins une saisie."""
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("engin_id").agg(
        type_engin=("type_engin", "first"),
        heures=("heures", "sum"),
        carburant=("carburant_l", "sum"),
        jours_saisis=("date", "count"),
        jours_service=("en_service", "sum"),
        cout_carburant=("cout_carburant", "sum"),
        cout_entretien=("cout_entretien", "sum"),
        cout_total=("cout_total", "sum"),
        incidents=("gravite_hse", lambda s: int((s != config.GRAVITE_AUCUN).sum())),
    ).reset_index()
    g = g.merge(flotte[["engin_id", "designation", "conso_ref_lh"]], on="engin_id", how="left")
    g["lh"] = g["carburant"] / g["heures"].replace(0, np.nan)
    g["ecart_conso"] = g["lh"] / g["conso_ref_lh"] - 1
    g["dispo"] = g["jours_service"] / g["jours_saisis"] * 100
    g["cout_horaire"] = g["cout_total"] / g["heures"].replace(0, np.nan)
    g["cout_horaire_carburant"] = g["cout_carburant"] / g["heures"].replace(0, np.nan)
    g["cout_horaire_entretien"] = g["cout_entretien"] / g["heures"].replace(0, np.nan)
    return g.sort_values("engin_id").reset_index(drop=True)


def surconsommations(df: pd.DataFrame) -> pd.DataFrame:
    """Journées où la consommation dépasse le seuil orange vs la référence."""
    if df.empty:
        return df
    anomalies = df[df["ecart_conso"] >= config.SEUIL_SURCONSO_ORANGE].copy()
    anomalies["niveau"] = anomalies["ecart_conso"].map(niveau_surconso)
    return anomalies.sort_values("ecart_conso", ascending=False)


# --------------------------------------------------------------------------- #
# Maintenance préventive (vidange)
# --------------------------------------------------------------------------- #
def etat_maintenance(flotte: pd.DataFrame, saisies: pd.DataFrame, maintenance: pd.DataFrame) -> pd.DataFrame:
    """
    Pour chaque engin :
      cumul          = horamètre initial + somme des heures saisies
      derniere_vid   = horamètre de la dernière vidange (sinon horamètre initial)
      depuis_vidange = cumul - derniere_vid
      niveau         = vert / orange (>= 80 % de l'intervalle) / rouge (>= intervalle)
    """
    heures = saisies.groupby("engin_id")["heures"].sum()
    vid = maintenance[maintenance["type_intervention"] == config.INTERVENTION_VIDANGE]
    derniere = vid.sort_values("date").groupby("engin_id").agg(
        derniere_vid_h=("horametre", "last"), derniere_vid_date=("date", "last")
    )
    e = flotte.set_index("engin_id").join(heures.rename("heures_saisies")).join(derniere)
    e["heures_saisies"] = e["heures_saisies"].fillna(0.0)
    e["cumul"] = e["horametre_initial"] + e["heures_saisies"]
    e["derniere_vid_h"] = e["derniere_vid_h"].fillna(e["horametre_initial"])
    e["depuis_vidange"] = (e["cumul"] - e["derniere_vid_h"]).clip(lower=0)
    e["restant"] = e["intervalle_vidange_h"] - e["depuis_vidange"]
    e["taux"] = e["depuis_vidange"] / e["intervalle_vidange_h"]
    e["niveau"] = np.select(
        [e["taux"] >= 1.0, e["taux"] >= config.SEUIL_ORANGE_VIDANGE], ["rouge", "orange"], default="vert"
    )
    e["_ordre"] = e["niveau"].map({"rouge": 0, "orange": 1, "vert": 2})
    e = e.reset_index().sort_values(["_ordre", "taux"], ascending=[True, False])
    return e.drop(columns="_ordre").reset_index(drop=True)


def statut_actuel(saisies: pd.DataFrame) -> pd.DataFrame:
    """Dernier statut connu de chaque engin."""
    if saisies.empty:
        return pd.DataFrame(columns=["engin_id", "statut", "date"])
    return saisies.sort_values("date").groupby("engin_id").tail(1)[["engin_id", "statut", "date"]]


# --------------------------------------------------------------------------- #
# Pannes : épisodes d'immobilisation, MTBF, MTTR
# --------------------------------------------------------------------------- #
def episodes_pannes(saisies: pd.DataFrame) -> pd.DataFrame:
    """
    Regroupe les jours consécutifs (saisies successives) où un engin n'est pas
    « En service » en un épisode de panne : début, fin, durée, gravité max, cause.
    """
    colonnes = ["engin_id", "type_engin", "debut", "fin", "jours", "statut_final", "gravite",
                "categorie", "description", "en_cours"]
    if saisies.empty:
        return pd.DataFrame(columns=colonnes)
    ordre_grav = {config.GRAVITE_AUCUN: 0, config.GRAVITE_MINEURE: 1, config.GRAVITE_MAJEURE: 2}
    derniere_date = saisies["date"].max()
    lignes = []
    for eid, g in saisies.sort_values("date").groupby("engin_id"):
        g = g.reset_index(drop=True)
        arret = g["statut"] != config.STATUT_SERVICE
        bloc = (arret != arret.shift()).cumsum()
        for _, ep in g[arret].groupby(bloc[arret]):
            grav = max(ep["gravite_hse"], key=lambda x: ordre_grav.get(x, 0))
            textes = ep[ep["description_incident"] != ""]
            fin_ep = ep["date"].iloc[-1]
            dernier_du_engin = fin_ep == g["date"].iloc[-1]
            lignes.append(dict(
                engin_id=eid, type_engin=ep["type_engin"].iloc[0],
                debut=ep["date"].iloc[0], fin=fin_ep, jours=len(ep),
                statut_final=ep["statut"].iloc[-1], gravite=grav,
                categorie=textes["categorie_incident"].iloc[0] if not textes.empty else "",
                description=textes["description_incident"].iloc[0] if not textes.empty else "",
                en_cours=bool(dernier_du_engin and fin_ep >= derniere_date - pd.Timedelta(days=1)),
            ))
    return pd.DataFrame(lignes, columns=colonnes).sort_values("debut", ascending=False).reset_index(drop=True)


def mtbf_mttr(saisies: pd.DataFrame, episodes: pd.DataFrame) -> tuple[float, float]:
    """MTBF (heures de marche par panne) et MTTR (jours moyens d'immobilisation par panne)."""
    if episodes.empty:
        return np.nan, np.nan
    return saisies["heures"].sum() / len(episodes), episodes["jours"].mean()


# --------------------------------------------------------------------------- #
# Rapport hebdomadaire
# --------------------------------------------------------------------------- #
def rapport_hebdo(df_semaine: pd.DataFrame, etat_maint: pd.DataFrame, flotte: pd.DataFrame) -> pd.DataFrame:
    """Synthèse hebdomadaire (une ligne par engin + ligne TOTAL PARC), prête pour Excel."""
    synth = par_engin(df_semaine, flotte)
    if synth.empty:
        return synth
    synth = synth.merge(
        etat_maint[["engin_id", "cumul", "depuis_vidange", "niveau"]], on="engin_id", how="left"
    )
    rapport = pd.DataFrame({
        "Engin": synth["engin_id"],
        "Type": synth["type_engin"],
        "Désignation": synth["designation"],
        "Heures de marche (h)": synth["heures"].round(1),
        "Carburant (L)": synth["carburant"].round(0),
        "Conso moyenne (L/h)": synth["lh"].round(2),
        "Conso référence (L/h)": synth["conso_ref_lh"],
        "Écart conso (%)": (synth["ecart_conso"] * 100).round(1),
        "Jours en service": synth["jours_service"].astype(int),
        "Jours saisis": synth["jours_saisis"],
        "Disponibilité (%)": synth["dispo"].round(1),
        f"Coût carburant ({config.CURRENCY})": synth["cout_carburant"].round(0),
        f"Coût entretien estimé ({config.CURRENCY})": synth["cout_entretien"].round(0),
        f"Coût total ({config.CURRENCY})": synth["cout_total"].round(0),
        f"Coût de revient horaire ({config.CURRENCY}/h)": synth["cout_horaire"].round(0),
        "Incidents HSE": synth["incidents"],
        "Horamètre cumulé (h)": synth["cumul"].round(1),
        "Heures depuis vidange (h)": synth["depuis_vidange"].round(1),
        "Alerte vidange": synth["niveau"].map({"vert": "OK", "orange": "À planifier", "rouge": "URGENT"}),
    })
    s = summary(df_semaine)
    total = {c: np.nan for c in rapport.columns}
    total.update({
        "Engin": "TOTAL PARC",
        "Heures de marche (h)": round(s["heures"], 1),
        "Carburant (L)": round(s["carburant"]),
        "Conso moyenne (L/h)": round(s["lh"], 2),
        "Jours en service": int(synth["jours_service"].sum()),
        "Jours saisis": int(synth["jours_saisis"].sum()),
        "Disponibilité (%)": round(s["dispo"], 1),
        f"Coût total ({config.CURRENCY})": round(s["cout_total"]),
        f"Coût de revient horaire ({config.CURRENCY}/h)": round(s["cout_horaire"]),
        "Incidents HSE": s["nb_incidents"],
    })
    return pd.concat([rapport, pd.DataFrame([total])], ignore_index=True)
