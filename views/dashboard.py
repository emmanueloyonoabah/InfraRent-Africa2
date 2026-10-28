"""
Vue « Tableau de bord » — KPIs financiers et opérationnels du parc.
"""
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core import config, data, kpi, ui

C = config.COLORS


def render() -> None:
    ui.page_header("Tableau de bord", "Coûts, consommation et disponibilité du parc d'engins")
    flotte, saisies = data.load_flotte(), data.load_saisies()
    if saisies.empty:
        st.info("Aucune saisie pour le moment. Les indicateurs apparaîtront dès les premiers relevés terrain.")
        return

    df = _filtres(flotte, saisies)
    if df.empty:
        st.warning("Aucune donnée pour cette sélection.")
        return

    _cartes_kpi(df)

    ui.section("Coûts et consommation par engin")
    synth = kpi.par_engin(df, flotte)
    g1, g2 = st.columns(2)
    with g1:
        ui.show_fig(_fig_cout_horaire(synth))
    with g2:
        ui.show_fig(_fig_conso(synth))

    ui.section("Disponibilité et activité")
    g3, g4 = st.columns(2)
    with g3:
        ui.show_fig(_fig_dispo(synth))
    with g4:
        ui.show_fig(_fig_evolution(df))

    ui.section("Surconsommations détectées")
    _table_anomalies(df)


# --------------------------------------------------------------------------- #
# Filtres
# --------------------------------------------------------------------------- #
def _filtres(flotte: pd.DataFrame, saisies: pd.DataFrame) -> pd.DataFrame:
    d_min, d_max = saisies["date"].min().date(), saisies["date"].max().date()
    debut_defaut = max(d_min, d_max - timedelta(days=27))
    with st.container(border=True):
        c1, c2, c3 = st.columns([1.3, 1.5, 1])
        periode = c1.date_input(
            "Période", value=(debut_defaut, d_max), min_value=d_min, max_value=d_max, format="DD/MM/YYYY"
        )
        types = c2.multiselect("Types d'engins", config.TYPES_ENGINS, default=config.TYPES_ENGINS)
        prix = c3.number_input(
            f"Prix du gasoil ({config.CURRENCY}/L)", min_value=100, max_value=2000, step=10,
            value=st.session_state.get("prix_gasoil", config.PRIX_GASOIL_DEFAUT),
            help="Sert au calcul du coût carburant et du coût de revient horaire.",
        )
        st.session_state["prix_gasoil"] = prix

    debut, fin = (periode[0], periode[-1]) if len(periode) else (debut_defaut, d_max)
    df = kpi.enrich(saisies, flotte, prix)
    masque = (df["date"].dt.date >= debut) & (df["date"].dt.date <= fin) & df["type_engin"].isin(types)
    return df[masque]


# --------------------------------------------------------------------------- #
# Cartes KPI
# --------------------------------------------------------------------------- #
def _cartes_kpi(df: pd.DataFrame) -> None:
    s = kpi.summary(df)
    ref_parc = (df["conso_ref_lh"] * df["heures"]).sum() / s["heures"] if s["heures"] else float("nan")
    ecart = s["lh"] / ref_parc - 1 if ref_parc and not pd.isna(s["lh"]) else float("nan")
    part_carb = df["cout_carburant"].sum() / s["cout_total"] if s["cout_total"] else 0

    ui.kpi_row([
        ui.kpi_card("Disponibilité du parc", ui.fmt(s["dispo"], 1), "%",
                    f"{ui.fmt(int(df['en_service'].sum()))} / {ui.fmt(s['jours_engins'])} jours-engins en service",
                    kpi.niveau_dispo(s["dispo"])),
        ui.kpi_card("Heures de marche", ui.fmt(s["heures"]), "h", f"{df['engin_id'].nunique()} engins actifs"),
        ui.kpi_card("Consommation moyenne", ui.fmt(s["lh"], 1), "L/h",
                    f"Réf. parc {ui.fmt(ref_parc, 1)} L/h ({ecart:+.0%})" if not pd.isna(ecart) else "",
                    kpi.niveau_surconso(ecart)),
        ui.kpi_card("Coût de revient horaire", ui.fmt(s["cout_horaire"]), f"{config.CURRENCY}/h",
                    f"Carburant {part_carb:.0%} · entretien {1 - part_carb:.0%}"),
        ui.kpi_card("Coût total estimé", ui.fmt(s["cout_total"] / 1e6, 2), f"M {config.CURRENCY}",
                    f"{ui.fmt(s['carburant'])} L de carburant"),
        ui.kpi_card("Incidents HSE", ui.fmt(s["nb_incidents"]), "",
                    f"dont {s['nb_majeurs']} majeur(s)", "rouge" if s["nb_majeurs"] else ("orange" if s["nb_incidents"] else "vert")),
    ])


# --------------------------------------------------------------------------- #
# Graphiques
# --------------------------------------------------------------------------- #
def _fig_cout_horaire(synth: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=synth["engin_id"], y=synth["cout_horaire_carburant"], name="Carburant", marker_color=C["navy"],
                hovertemplate="%{x}<br>Carburant : %{y:,.0f} FCFA/h<extra></extra>")
    fig.add_bar(x=synth["engin_id"], y=synth["cout_horaire_entretien"], name="Entretien estimé", marker_color=C["grey"],
                hovertemplate="%{x}<br>Entretien : %{y:,.0f} FCFA/h<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text=f"{config.CURRENCY} / heure")
    return ui.style_fig(fig, titre="Coût de revient horaire")


def _fig_conso(synth: pd.DataFrame) -> go.Figure:
    couleurs = [config.NIVEAU_COLORS[kpi.niveau_surconso(e)] for e in synth["ecart_conso"]]
    fig = go.Figure()
    fig.add_bar(x=synth["engin_id"], y=synth["lh"], marker_color=couleurs, name="Consommation mesurée",
                customdata=synth["ecart_conso"] * 100,
                hovertemplate="%{x}<br>%{y:.1f} L/h (%{customdata:+.0f} % vs réf.)<extra></extra>")
    fig.add_scatter(x=synth["engin_id"], y=synth["conso_ref_lh"], mode="markers", name="Référence constructeur",
                    marker=dict(symbol="line-ew", size=30, line=dict(width=3, color=C["navy"])),
                    hovertemplate="%{x}<br>Réf. : %{y:.1f} L/h<extra></extra>")
    fig.update_yaxes(title_text="Litres / heure")
    return ui.style_fig(fig, titre="Consommation L/h vs référence (rouge : > +30 %, orange : > +15 %)")


def _fig_dispo(synth: pd.DataFrame) -> go.Figure:
    d = synth.sort_values("dispo")
    couleurs = [config.NIVEAU_COLORS[kpi.niveau_dispo(x)] for x in d["dispo"]]
    fig = go.Figure(go.Bar(
        x=d["dispo"], y=d["engin_id"], orientation="h", marker_color=couleurs,
        text=[f"{x:.0f} %" for x in d["dispo"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>Disponibilité : %{x:.1f} %<extra></extra>",
    ))
    fig.add_vline(x=config.SEUIL_DISPO_ORANGE, line_dash="dot", line_color=C["steel"],
                  annotation_text=f"objectif {config.SEUIL_DISPO_ORANGE:.0f} %", annotation_position="top")
    fig.update_xaxes(range=[0, 108], title_text="% des jours en service")
    return ui.style_fig(fig, titre="Taux de disponibilité par engin", legende=False)


def _fig_evolution(df: pd.DataFrame) -> go.Figure:
    j = df.groupby("date").agg(heures=("heures", "sum"), carburant=("carburant_l", "sum")).reset_index()
    j["lh"] = j["carburant"] / j["heures"].replace(0, float("nan"))
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=j["date"], y=j["heures"], name="Heures de marche (parc)", marker_color=C["navy_light"], opacity=0.85,
                secondary_y=False)
    fig.add_scatter(x=j["date"], y=j["lh"], name="L/h moyen", mode="lines+markers",
                    line=dict(color=C["warn"], width=2.5), marker=dict(size=5), secondary_y=True)
    fig.update_yaxes(title_text="Heures / jour", secondary_y=False)
    fig.update_yaxes(title_text="L/h", showgrid=False, tickformat=".1f", secondary_y=True)
    return ui.style_fig(fig, titre="Activité quotidienne du parc")


# --------------------------------------------------------------------------- #
# Tableau des anomalies
# --------------------------------------------------------------------------- #
def _table_anomalies(df: pd.DataFrame) -> None:
    anomalies = kpi.surconsommations(df)
    if anomalies.empty:
        st.success("Aucune surconsommation détectée sur la période (seuil : +15 % vs référence).")
        return
    st.caption(
        f"{len(anomalies)} journée(s) dépassent la consommation de référence de plus de "
        f"{config.SEUIL_SURCONSO_ORANGE:.0%} — piste : fuite, vol de carburant, injecteurs, ralenti excessif."
    )
    pastille = {"orange": "🟠 À surveiller", "rouge": "🔴 Anormale"}
    table = pd.DataFrame({
        "Date": anomalies["date"].dt.strftime("%d/%m/%Y"),
        "Engin": anomalies["engin_id"],
        "Désignation": anomalies["designation"],
        "Heures": anomalies["heures"],
        "Carburant (L)": anomalies["carburant_l"],
        "L/h mesuré": anomalies["lh"],
        "L/h réf.": anomalies["conso_ref_lh"],
        "Écart": anomalies["ecart_conso"],
        "Niveau": anomalies["niveau"].map(pastille),
        "Saisi par": anomalies["saisi_par"],
    })
    st.dataframe(
        table, hide_index=True, width="stretch", height=min(420, 38 + 35 * len(table)),
        column_config={
            "Heures": st.column_config.NumberColumn(format="%.1f"),
            "Carburant (L)": st.column_config.NumberColumn(format="%.0f"),
            "L/h mesuré": st.column_config.NumberColumn(format="%.1f"),
            "L/h réf.": st.column_config.NumberColumn(format="%.1f"),
            "Écart": st.column_config.NumberColumn(format="percent"),
        },
    )
