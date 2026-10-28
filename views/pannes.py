"""
Vue « Pannes & carnet de santé » — historique des immobilisations (MTBF / MTTR)
et fiche de vie complète de chaque engin.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config, data, kpi, ui

C = config.COLORS
_COULEURS_GRAVITE = {**config.GRAVITE_COLORS, config.GRAVITE_AUCUN: C["grey"]}


def render() -> None:
    ui.page_header("Pannes & carnet de santé", "Historique des immobilisations et fiche de vie de chaque engin")
    flotte, saisies, maint = data.load_flotte(), data.load_saisies(), data.load_maintenance()
    if saisies.empty:
        st.info("Aucune saisie pour le moment.")
        return
    onglet_pannes, onglet_carnet = st.tabs(["Historique des pannes", "Carnet de santé par engin"])
    with onglet_pannes:
        _historique(saisies)
    with onglet_carnet:
        _carnet(flotte, saisies, maint)


# --------------------------------------------------------------------------- #
# Historique des pannes
# --------------------------------------------------------------------------- #
def _historique(saisies: pd.DataFrame) -> None:
    c1, c2 = st.columns([2, 1])
    types = c1.multiselect("Types d'engins", config.TYPES_ENGINS, default=config.TYPES_ENGINS, key="pannes_types")
    seulement_en_cours = c2.toggle("Pannes en cours uniquement", value=False)

    sel = saisies[saisies["type_engin"].isin(types)]
    ep = kpi.episodes_pannes(sel)
    mtbf, mttr = kpi.mtbf_mttr(sel, ep)

    ui.kpi_row([
        ui.kpi_card("Pannes enregistrées", str(len(ep)), "", "épisodes d'immobilisation"),
        ui.kpi_card("Jours d'immobilisation", ui.fmt(ep["jours"].sum() if len(ep) else 0), "j", "cumul tous engins"),
        ui.kpi_card("MTBF", ui.fmt(mtbf, 0), "h", "heures de marche entre pannes"),
        ui.kpi_card("MTTR", ui.fmt(mttr, 1), "jours", "durée moyenne d'immobilisation"),
        ui.kpi_card("Pannes en cours", str(int(ep["en_cours"].sum())) if len(ep) else "0", "",
                    "engins actuellement à l'arrêt", "rouge" if len(ep) and ep["en_cours"].any() else "vert"),
    ])
    if ep.empty:
        st.success("Aucune panne enregistrée pour cette sélection.")
        return

    if seulement_en_cours:
        ep = ep[ep["en_cours"]]

    ui.section("Jours d'immobilisation par engin")
    par = ep.groupby(["engin_id", "gravite"])["jours"].sum().reset_index()
    fig = go.Figure()
    for grav in (config.GRAVITE_MAJEURE, config.GRAVITE_MINEURE, config.GRAVITE_AUCUN):
        d = par[par["gravite"] == grav]
        if not d.empty:
            libelle = "Non qualifiée" if grav == config.GRAVITE_AUCUN else f"Gravité {grav.lower()}"
            fig.add_bar(x=d["engin_id"], y=d["jours"], name=libelle, marker_color=_COULEURS_GRAVITE[grav])
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="Jours à l'arrêt")
    ui.show_fig(ui.style_fig(fig, hauteur=300))

    ui.section("Détail des épisodes")
    st.dataframe(_table_episodes(ep), hide_index=True, width="stretch")


def _table_episodes(ep: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Engin": ep["engin_id"],
        "Type": ep["type_engin"],
        "Début": ep["debut"].dt.strftime("%d/%m/%Y"),
        "Fin": ep["fin"].dt.strftime("%d/%m/%Y"),
        "Jours": ep["jours"],
        "État": ep.apply(lambda r: "🔴 En cours – " + r["statut_final"] if r["en_cours"] else "✅ Résolue", axis=1),
        "Gravité": ep["gravite"].replace(config.GRAVITE_AUCUN, "–"),
        "Nature": ep["categorie"],
        "Description": ep["description"],
    })


# --------------------------------------------------------------------------- #
# Carnet de santé
# --------------------------------------------------------------------------- #
def _carnet(flotte: pd.DataFrame, saisies: pd.DataFrame, maint: pd.DataFrame) -> None:
    libelles = {r.engin_id: f"{r.engin_id} · {r.designation}" for r in flotte.itertuples()}
    engin_id = st.selectbox("Engin", list(libelles), format_func=libelles.get, key="carnet_engin")
    fiche = flotte.set_index("engin_id").loc[engin_id]

    prix = st.session_state.get("prix_gasoil", config.PRIX_GASOIL_DEFAUT)
    df = kpi.enrich(saisies[saisies["engin_id"] == engin_id], flotte, prix)
    etat = kpi.etat_maintenance(flotte, saisies, maint).set_index("engin_id").loc[engin_id]
    s = kpi.summary(df)
    ecart = s["lh"] / fiche["conso_ref_lh"] - 1 if not pd.isna(s["lh"]) else float("nan")

    st.markdown(
        f"**{fiche['type_engin']}** · {fiche['designation']} · Immatriculation / n° de série : `{fiche['immatriculation']}`"
    )
    ui.kpi_row([
        ui.kpi_card("Horamètre cumulé", ui.fmt(etat["cumul"]), "h", f"initial : {ui.fmt(fiche['horametre_initial'])} h"),
        ui.kpi_card("Depuis dernière vidange", ui.fmt(etat["depuis_vidange"]), "h",
                    f"intervalle {ui.fmt(etat['intervalle_vidange_h'])} h", etat["niveau"]),
        ui.kpi_card("Disponibilité", ui.fmt(s["dispo"], 1), "%", f"{ui.fmt(s['jours_engins'])} jours suivis", kpi.niveau_dispo(s["dispo"])),
        ui.kpi_card("Consommation", ui.fmt(s["lh"], 1), "L/h",
                    f"réf. {ui.fmt(fiche['conso_ref_lh'], 1)} L/h ({ecart:+.0%})" if not pd.isna(ecart) else "", kpi.niveau_surconso(ecart)),
        ui.kpi_card("Coût de revient", ui.fmt(s["cout_horaire"]), f"{config.CURRENCY}/h", "carburant + entretien estimé"),
    ])
    if df.empty:
        st.info("Aucune saisie pour cet engin.")
        return

    g1, g2 = st.columns(2)
    with g1:
        ui.show_fig(_fig_statuts(df))
    with g2:
        ui.show_fig(_fig_conso_engin(df, float(fiche["conso_ref_lh"])))

    ui.section("Pannes de l'engin")
    ep = kpi.episodes_pannes(saisies[saisies["engin_id"] == engin_id])
    if ep.empty:
        st.caption("Aucune panne enregistrée.")
    else:
        st.dataframe(_table_episodes(ep).drop(columns=["Engin", "Type"]), hide_index=True, width="stretch")

    ui.section("Interventions de maintenance")
    m = maint[maint["engin_id"] == engin_id].sort_values("date", ascending=False)
    if m.empty:
        st.caption("Aucune intervention enregistrée.")
    else:
        st.dataframe(
            pd.DataFrame({
                "Date": m["date"].dt.strftime("%d/%m/%Y"), "Intervention": m["type_intervention"],
                "Horamètre (h)": m["horametre"], f"Coût ({config.CURRENCY})": m["cout_fcfa"], "Description": m["description"],
            }),
            hide_index=True, width="stretch",
            column_config={"Horamètre (h)": st.column_config.NumberColumn(format="%.0f"),
                           f"Coût ({config.CURRENCY})": st.column_config.NumberColumn(format="%d")},
        )
        st.caption(f"Coût cumulé des interventions : **{ui.fmt(m['cout_fcfa'].sum())} {config.CURRENCY}**")

    journal = df[["date", "heures", "carburant_l", "lh", "zone_tache", "statut", "gravite_hse", "description_incident", "saisi_par"]]
    st.download_button(
        "Télécharger le journal de cet engin (CSV)",
        journal.assign(date=journal["date"].dt.strftime("%Y-%m-%d")).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name=f"carnet_sante_{engin_id}.csv", mime="text/csv",
    )


def _fig_statuts(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for statut in config.STATUTS:
        d = df[df["statut"] == statut]
        if not d.empty:
            fig.add_bar(x=d["date"], y=[1] * len(d), name=statut, marker_color=config.STATUT_COLORS[statut],
                        hovertemplate="%{x|%d/%m/%Y}<br>" + statut + "<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.08)
    fig.update_yaxes(visible=False)
    return ui.style_fig(fig, hauteur=260, titre="Statut journalier")


def _fig_conso_engin(df: pd.DataFrame, reference: float) -> go.Figure:
    d = df.dropna(subset=["lh"])
    fig = go.Figure()
    fig.add_scatter(x=d["date"], y=d["lh"], mode="lines+markers", name="L/h mesuré",
                    line=dict(color=C["navy"], width=2), marker=dict(size=6))
    fig.add_hline(y=reference, line_dash="dot", line_color=C["steel"], annotation_text=f"réf. {reference:.1f} L/h")
    fig.add_hline(y=reference * (1 + config.SEUIL_SURCONSO_ROUGE), line_dash="dash", line_color=C["danger"],
                  annotation_text="seuil anormal", annotation_position="top left")
    fig.update_yaxes(title_text="L/h")
    return ui.style_fig(fig, hauteur=260, titre="Consommation journalière", legende=False)
