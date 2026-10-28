"""
Vue « HSE » — Hygiène, Sécurité, Environnement : incidents déclarés sur le terrain.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import config, data, ui

C = config.COLORS


def render() -> None:
    ui.page_header("HSE · Hygiène, Sécurité, Environnement", "Incidents et pannes signalés par les chefs de chantier")
    saisies = data.load_saisies()
    if saisies.empty:
        st.info("Aucune saisie pour le moment.")
        return

    with st.container(border=True):
        c1, c2 = st.columns([1.4, 1])
        d_min, d_max = saisies["date"].min().date(), saisies["date"].max().date()
        periode = c1.date_input("Période", value=(d_min, d_max), min_value=d_min, max_value=d_max, format="DD/MM/YYYY")
        gravites = c2.multiselect("Gravité", [config.GRAVITE_MINEURE, config.GRAVITE_MAJEURE],
                                  default=[config.GRAVITE_MINEURE, config.GRAVITE_MAJEURE])
    debut, fin = (periode[0], periode[-1]) if len(periode) else (d_min, d_max)

    periode_df = saisies[(saisies["date"].dt.date >= debut) & (saisies["date"].dt.date <= fin)]
    inc = periode_df[periode_df["gravite_hse"].isin(gravites)]
    heures = periode_df["heures"].sum()
    majeurs_tous = saisies[saisies["gravite_hse"] == config.GRAVITE_MAJEURE]

    if majeurs_tous.empty:
        jours_sans = "–"
        sous = "aucun incident majeur enregistré"
    else:
        jours_sans = str((pd.Timestamp(data.today_local()) - majeurs_tous["date"].max()).days)
        sous = f"dernier : {ui.fmt_date(majeurs_tous['date'].max())}"
    n_maj = int((inc["gravite_hse"] == config.GRAVITE_MAJEURE).sum())
    n_min = int((inc["gravite_hse"] == config.GRAVITE_MINEURE).sum())

    ui.kpi_row([
        ui.kpi_card("Incidents déclarés", str(len(inc)), "", "sur la période et la sélection"),
        ui.kpi_card("Majeurs", str(n_maj), "", "arrêt prolongé, blessure, accident", "rouge" if n_maj else "vert"),
        ui.kpi_card("Mineurs", str(n_min), "", "sans arrêt prolongé", "orange" if n_min else "vert"),
        ui.kpi_card("Fréquence", ui.fmt(len(inc) / heures * 1000 if heures else float("nan"), 1), "/ 1 000 h",
                    "incidents par 1 000 h de marche"),
        ui.kpi_card("Jours sans incident majeur", jours_sans, "j", sous, "vert" if jours_sans not in ("–", "0") else "orange"),
    ])
    if inc.empty:
        st.success("Aucun incident pour cette sélection.")
        return

    ui.section("Analyse des incidents")
    g1, g2 = st.columns(2)
    with g1:
        ui.show_fig(_fig_semaine(inc))
    with g2:
        ui.show_fig(_fig_categories(inc))

    ui.section("Registre des incidents")
    reg = inc.sort_values("date", ascending=False)
    table = pd.DataFrame({
        "Date": reg["date"].dt.strftime("%d/%m/%Y"),
        "Gravité": reg["gravite_hse"].map({config.GRAVITE_MAJEURE: "🔴 Majeure", config.GRAVITE_MINEURE: "🟠 Mineure"}),
        "Engin": reg["engin_id"],
        "Type": reg["type_engin"],
        "Nature": reg["categorie_incident"],
        "Description": reg["description_incident"],
        "Statut engin": reg["statut"],
        "Déclaré par": reg["saisi_par"],
    })
    st.dataframe(table, hide_index=True, width="stretch")


def _fig_semaine(inc: pd.DataFrame) -> go.Figure:
    d = inc.assign(semaine=inc["date"].dt.to_period("W-SUN").dt.start_time)
    d = d.groupby(["semaine", "gravite_hse"]).size().reset_index(name="n")
    fig = go.Figure()
    for grav in (config.GRAVITE_MAJEURE, config.GRAVITE_MINEURE):
        x = d[d["gravite_hse"] == grav]
        if not x.empty:
            fig.add_bar(x=x["semaine"], y=x["n"], name=grav, marker_color=config.GRAVITE_COLORS[grav],
                        hovertemplate="Semaine du %{x|%d/%m/%Y}<br>%{y} incident(s)<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat="%d/%m", title_text="Semaine (lundi)")
    fig.update_yaxes(title_text="Nombre d'incidents", dtick=1)
    return ui.style_fig(fig, titre="Incidents par semaine")


def _fig_categories(inc: pd.DataFrame) -> go.Figure:
    d = inc.groupby(["categorie_incident", "gravite_hse"]).size().reset_index(name="n")
    ordre = d.groupby("categorie_incident")["n"].sum().sort_values().index
    fig = go.Figure()
    for grav in (config.GRAVITE_MAJEURE, config.GRAVITE_MINEURE):
        x = d[d["gravite_hse"] == grav]
        if not x.empty:
            fig.add_bar(y=x["categorie_incident"], x=x["n"], orientation="h", name=grav,
                        marker_color=config.GRAVITE_COLORS[grav])
    fig.update_layout(barmode="stack")
    fig.update_yaxes(categoryorder="array", categoryarray=list(ordre))
    fig.update_xaxes(dtick=1, title_text="Nombre d'incidents")
    return ui.style_fig(fig, titre="Répartition par nature")
