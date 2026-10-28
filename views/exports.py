"""
Vue « Rapports & données » — rapport hebdomadaire CSV, sauvegarde / restauration,
édition du parc d'engins et outils d'administration.
"""
from datetime import timedelta

import pandas as pd
import streamlit as st

from core import config, data, kpi, ui


def render() -> None:
    ui.page_header("Rapports & données", "Exports, sauvegardes et paramétrage du parc")
    t1, t2, t3, t4 = st.tabs(["Rapport hebdomadaire", "Sauvegarde & restauration", "Parc d'engins", "Administration"])
    with t1:
        _rapport_hebdo()
    with t2:
        _sauvegarde()
    with t3:
        _parc()
    with t4:
        _administration()


def _csv_fr(df: pd.DataFrame) -> bytes:
    """CSV lisible directement par Excel en version française (; , UTF-8 avec BOM)."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


# --------------------------------------------------------------------------- #
# Rapport hebdomadaire
# --------------------------------------------------------------------------- #
def _rapport_hebdo() -> None:
    flotte, saisies, maint = data.load_flotte(), data.load_saisies(), data.load_maintenance()
    if saisies.empty:
        st.info("Aucune saisie à exporter pour le moment.")
        return

    dernier = saisies["date"].max().date()
    ref = st.date_input("Semaine contenant le", value=dernier, max_value=data.today_local(), format="DD/MM/YYYY",
                        help="La semaine va du lundi au dimanche.")
    lundi = ref - timedelta(days=ref.weekday())
    dimanche = lundi + timedelta(days=6)
    st.caption(f"Semaine du **{ui.fmt_date(lundi)}** au **{ui.fmt_date(dimanche)}**")

    prix = st.session_state.get("prix_gasoil", config.PRIX_GASOIL_DEFAUT)
    df = kpi.enrich(saisies, flotte, prix)
    semaine = df[(df["date"].dt.date >= lundi) & (df["date"].dt.date <= dimanche)]
    if semaine.empty:
        st.warning("Aucune saisie sur cette semaine.")
        return

    etat = kpi.etat_maintenance(flotte, saisies, maint)
    rapport = kpi.rapport_hebdo(semaine, etat, flotte)
    st.dataframe(rapport, hide_index=True, width="stretch")
    st.caption(f"Coûts calculés avec un gasoil à {ui.fmt(prix)} {config.CURRENCY}/L (modifiable dans le tableau de bord).")

    detail = semaine[[
        "date", "engin_id", "type_engin", "heures", "carburant_l", "lh", "zone_tache", "statut",
        "gravite_hse", "categorie_incident", "description_incident", "saisi_par", "horodatage",
    ]].copy()
    detail["date"] = detail["date"].dt.strftime("%Y-%m-%d")
    detail = detail.rename(columns={
        "date": "Date", "engin_id": "Engin", "type_engin": "Type", "heures": "Heures", "carburant_l": "Carburant (L)",
        "lh": "L/h", "zone_tache": "Zone / tâche", "statut": "Statut", "gravite_hse": "Gravité HSE",
        "categorie_incident": "Nature incident", "description_incident": "Description", "saisi_par": "Saisi par",
        "horodatage": "Horodatage",
    })

    suffixe = f"{lundi:%Y-%m-%d}_au_{dimanche:%Y-%m-%d}"
    c1, c2, _ = st.columns([1, 1, 1])
    c1.download_button(
        "Télécharger le rapport hebdomadaire (CSV)", _csv_fr(rapport), file_name=f"rapport_chantier_{suffixe}.csv",
        mime="text/csv", type="primary", width="stretch",
    )
    c2.download_button(
        "Détail journalier de la semaine (CSV)", _csv_fr(detail), file_name=f"detail_saisies_{suffixe}.csv",
        mime="text/csv", width="stretch",
    )


# --------------------------------------------------------------------------- #
# Sauvegarde / restauration
# --------------------------------------------------------------------------- #
_FICHIERS = {
    "Saisies terrain": (config.SAISIES_CSV, data.SAISIES_COLS, data.replace_saisies, data.load_saisies),
    "Maintenance": (config.MAINTENANCE_CSV, data.MAINTENANCE_COLS, data.replace_maintenance, data.load_maintenance),
    "Parc d'engins": (config.FLOTTE_CSV, data.FLOTTE_COLS, data.save_flotte, data.load_flotte),
}


def _sauvegarde() -> None:
    st.markdown(
        "Sur **Streamlit Community Cloud**, le disque est temporaire : les données saisies peuvent être "
        "perdues lors d'un redémarrage de l'application. **Téléchargez une sauvegarde régulièrement** "
        "et restaurez-la ci-dessous si nécessaire."
    )
    ui.section("Télécharger les données brutes")
    cols = st.columns(len(_FICHIERS))
    for col, (nom, (chemin, _cols, _w, _l)) in zip(cols, _FICHIERS.items()):
        contenu = chemin.read_bytes() if chemin.exists() else b""
        col.download_button(nom, contenu, file_name=chemin.name, mime="text/csv", width="stretch", key=f"dl_{chemin.name}")

    ui.section("Restaurer depuis une sauvegarde")
    nom = st.selectbox("Fichier à restaurer", list(_FICHIERS))
    chemin, colonnes, remplacer, _ = _FICHIERS[nom]
    fichier = st.file_uploader("Fichier CSV (sauvegarde précédemment téléchargée)", type="csv", key=f"up_{chemin.name}")
    if fichier is not None:
        try:
            df = pd.read_csv(fichier, dtype=str, keep_default_na=False)
        except Exception as exc:
            st.error(f"Lecture impossible : {exc}")
            return
        manquantes = [c for c in colonnes if c not in df.columns]
        if manquantes:
            st.error(f"Colonnes manquantes : {', '.join(manquantes)}")
            return
        st.success(f"{len(df)} ligne(s) détectée(s). Le contenu actuel de « {nom} » sera **remplacé**.")
        if st.button("Confirmer la restauration", type="primary"):
            remplacer(df)
            st.toast(f"« {nom} » restauré ({len(df)} lignes).", icon="✅")
            st.rerun()


# --------------------------------------------------------------------------- #
# Parc d'engins
# --------------------------------------------------------------------------- #
def _parc() -> None:
    st.markdown(
        "Ajoutez, modifiez ou retirez des engins. Ne changez pas l'**identifiant** d'un engin déjà utilisé : "
        "ses saisies passées ne seraient plus rattachées."
    )
    flotte = data.load_flotte()
    edite = st.data_editor(
        flotte, num_rows="dynamic", hide_index=True, width="stretch", key="editeur_parc",
        column_config={
            "engin_id": st.column_config.TextColumn("Identifiant", required=True, help="Ex. PH-01"),
            "type_engin": st.column_config.SelectboxColumn("Type", options=config.TYPES_ENGINS, required=True),
            "designation": st.column_config.TextColumn("Marque / modèle"),
            "immatriculation": st.column_config.TextColumn("Immatriculation / n° série"),
            "conso_ref_lh": st.column_config.NumberColumn("Conso réf. (L/h)", min_value=0.1, format="%.1f", required=True),
            "cout_entretien_h": st.column_config.NumberColumn(f"Entretien ({config.CURRENCY}/h)", min_value=1, format="%d", required=True),
            "intervalle_vidange_h": st.column_config.NumberColumn("Intervalle vidange (h)", min_value=1, format="%d", required=True),
            "horametre_initial": st.column_config.NumberColumn("Horamètre initial (h)", min_value=0, format="%.0f"),
        },
    )
    if st.button("Enregistrer le parc", type="primary"):
        edite = edite.copy()
        edite["engin_id"] = edite["engin_id"].fillna("").astype(str).str.strip().str.upper()
        erreurs = data.validate_flotte(edite)
        if erreurs:
            for e in erreurs:
                st.error(e)
        else:
            data.save_flotte(edite)
            st.toast("Parc d'engins enregistré.", icon="✅")
            st.rerun()


# --------------------------------------------------------------------------- #
# Administration
# --------------------------------------------------------------------------- #
def _administration() -> None:
    st.markdown(
        "Ces actions modifient définitivement les données. Pensez à **télécharger une sauvegarde** avant."
    )
    with st.container(border=True):
        st.markdown("**Passer en production : vider les saisies et la maintenance**")
        st.caption("Supprime les données de démonstration. Le parc d'engins est conservé : adaptez-le d'abord dans l'onglet « Parc d'engins ».")
        ok = st.checkbox("Je confirme vouloir supprimer toutes les saisies et interventions", key="confirm_clear")
        st.button("Vider les données opérationnelles", disabled=not ok, on_click=_vider)

    with st.container(border=True):
        st.markdown("**Recharger le jeu de données de démonstration**")
        st.caption("Remplace le parc, les saisies et la maintenance par 5 semaines de données fictives.")
        ok2 = st.checkbox("Je confirme vouloir tout remplacer par les données de démonstration", key="confirm_demo")
        st.button("Recharger la démo", disabled=not ok2, on_click=_recharger_demo)


# Les actions destructives passent par des callbacks : elles s'exécutent avant le rerun,
# ce qui permet de décocher la case de confirmation juste après.
def _vider() -> None:
    data.clear_operational_data()
    st.session_state["confirm_clear"] = False
    st.toast("Données opérationnelles supprimées.", icon="🗑️")


def _recharger_demo() -> None:
    data.seed_demo()
    st.session_state["confirm_demo"] = False
    st.toast("Données de démonstration rechargées.", icon="✅")
