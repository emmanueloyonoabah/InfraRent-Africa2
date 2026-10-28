"""
Composants d'interface : feuille de style, cartes KPI, bandeau d'alerte,
formatage des nombres (à la française) et thème Plotly commun.
"""
import html

import pandas as pd
import streamlit as st

from core import config

C = config.COLORS


# --------------------------------------------------------------------------- #
# Formatage
# --------------------------------------------------------------------------- #
def fmt(valeur, decimales: int = 0, unite: str = "") -> str:
    """12345.6 -> '12 345,6' (espace insécable, virgule décimale)."""
    if valeur is None or pd.isna(valeur):
        return "–"
    texte = f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return f"{texte} {unite}".strip() if unite else texte


def fmt_date(d) -> str:
    return "–" if pd.isna(d) else pd.Timestamp(d).strftime("%d/%m/%Y")


# --------------------------------------------------------------------------- #
# Feuille de style
# --------------------------------------------------------------------------- #
_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {{ font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }}
.stApp {{ background: {C['bg']}; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 3.6rem; padding-bottom: 3rem; max-width: 1280px; }}

/* Barre latérale */
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {C['grey_light']}; }}
.side-user {{ background: {C['bg']}; border-left: 4px solid {C['navy']}; border-radius: 6px;
             padding: .6rem .8rem; margin-bottom: .6rem; }}
.side-user b {{ color: {C['navy']}; display: block; font-size: .92rem; }}
.side-user span {{ color: {C['steel']}; font-size: .78rem; }}

/* En-tête de page */
.page-head {{ background: linear-gradient(100deg, {C['navy']} 0%, {C['navy_light']} 100%);
             color: #fff; border-radius: 10px; padding: 1.1rem 1.5rem; margin-bottom: 1.1rem;
             display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }}
.page-head h1 {{ color: #fff; font-size: 1.45rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.2; }}
.page-head p {{ color: #C9D6E6; margin: .15rem 0 0 0; font-size: .86rem; }}
.page-head .stamp {{ background: rgba(255,255,255,.12); border-radius: 6px; padding: .3rem .7rem;
                     font-size: .78rem; color: #E6EDF6; white-space: nowrap; }}

/* Cartes KPI */
.kpi {{ background: #fff; border-radius: 10px; padding: .8rem .9rem .7rem .9rem; min-height: 8.2rem;
       border: 1px solid {C['grey_light']}; border-top: 4px solid var(--accent, {C['navy']});
       box-shadow: 0 1px 2px rgba(18,53,91,.05); margin-bottom: .6rem; }}
.kpi-label {{ color: {C['steel']}; font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em;
             min-height: 2.1em; line-height: 1.05rem; }}
.kpi-value {{ color: {C['navy']}; font-size: 1.5rem; font-weight: 700; line-height: 1.3; margin-top: .1rem; white-space: nowrap; }}
.kpi-unit {{ font-size: .8rem; font-weight: 500; color: {C['steel']}; }}
.kpi-sub {{ color: {C['grey']}; font-size: .74rem; margin-top: .1rem; line-height: 1.2; }}

/* Bandeau d'alerte maintenance */
.alert-banner {{ border-radius: 10px; padding: .8rem 1.1rem; margin-bottom: 1rem; border-left: 8px solid; }}
.alert-banner .alert-title {{ font-weight: 700; font-size: .98rem; letter-spacing: .01em; }}
.alert-banner .alert-text {{ font-size: .86rem; margin-top: .25rem; }}
.alert-rouge  {{ background: #FBECEA; border-color: {C['danger']}; color: #7A1F18; }}
.alert-orange {{ background: #FEF2E5; border-color: {C['warn']};   color: #7A4308; }}
.alert-vert   {{ background: #E9F6EF; border-color: {C['ok']};     color: #17532F; }}
.chip {{ display: inline-block; border-radius: 999px; padding: .08rem .6rem; margin: .15rem .3rem .05rem 0;
        font-size: .78rem; font-weight: 600; color: #fff; }}
.chip-rouge {{ background: {C['danger']}; }} .chip-orange {{ background: {C['warn']}; }} .chip-vert {{ background: {C['ok']}; }}

/* Fiche maintenance d'un engin */
.engin-card {{ background: #fff; border: 1px solid {C['grey_light']}; border-radius: 10px;
              padding: .8rem .95rem; margin-bottom: .8rem; border-left: 6px solid var(--accent, {C['ok']}); }}
.engin-card .top {{ display: flex; justify-content: space-between; align-items: baseline; }}
.engin-card .id {{ font-weight: 700; color: {C['navy']}; font-size: 1.02rem; }}
.engin-card .meta {{ color: {C['steel']}; font-size: .78rem; margin-bottom: .45rem; }}
.engin-card .bar {{ background: {C['grey_light']}; border-radius: 6px; height: 10px; overflow: hidden; }}
.engin-card .bar > div {{ height: 100%; background: var(--accent, {C['ok']}); border-radius: 6px; }}
.engin-card .foot {{ display: flex; justify-content: space-between; font-size: .8rem; color: {C['steel']}; margin-top: .35rem; }}
.badge {{ border-radius: 5px; padding: .05rem .5rem; font-size: .72rem; font-weight: 700; color: #fff;
         background: var(--accent, {C['ok']}); text-transform: uppercase; letter-spacing: .03em; }}

/* Sections */
.section-title {{ color: {C['navy']}; font-weight: 700; font-size: 1.02rem; margin: 1.3rem 0 .4rem 0;
                 padding-bottom: .3rem; border-bottom: 2px solid {C['grey_light']}; }}

/* Écran de connexion */
.login-brand {{ text-align: center; margin: 2.5rem 0 1.2rem 0; }}
.login-logo {{ width: 62px; height: 62px; margin: 0 auto .7rem auto; border-radius: 14px; background: {C['navy']};
              color: #fff; font-weight: 800; font-size: 1.5rem; display: flex; align-items: center; justify-content: center;
              border-bottom: 5px solid {C['warn']}; }}
.login-brand h1 {{ color: {C['navy']}; font-size: 1.7rem; margin: 0; padding: 0; }}
.login-brand p {{ color: {C['steel']}; font-size: .9rem; margin: .2rem 0 0 0; }}

/* Boutons et onglets */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{ border-radius: 8px; font-weight: 600; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
[data-testid="stForm"] {{ background: #fff; border: 1px solid {C['grey_light']}; border-radius: 10px; padding: 1.1rem 1.2rem; }}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Composants
# --------------------------------------------------------------------------- #
def page_header(titre: str, sous_titre: str = "") -> None:
    maintenant = pd.Timestamp.now(tz=f"Etc/GMT-{config.UTC_OFFSET_HOURS}")
    st.markdown(
        f"""
        <div class="page-head">
          <div><h1>{html.escape(titre)}</h1><p>{html.escape(sous_titre)}</p></div>
          <div class="stamp">{config.APP_NAME} · {maintenant.strftime('%d/%m/%Y')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(titre: str) -> None:
    st.markdown(f'<div class="section-title">{html.escape(titre)}</div>', unsafe_allow_html=True)


def kpi_card(label: str, valeur: str, unite: str = "", sous_texte: str = "", niveau: str | None = None) -> str:
    accent = config.NIVEAU_COLORS.get(niveau, C["navy"])
    unite_html = f' <span class="kpi-unit">{html.escape(unite)}</span>' if unite else ""
    sub_html = f'<div class="kpi-sub">{html.escape(sous_texte)}</div>' if sous_texte else ""
    return (
        f'<div class="kpi" style="--accent:{accent}"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(valeur)}{unite_html}</div>{sub_html}</div>'
    )


def kpi_row(cartes: list[str]) -> None:
    for col, carte in zip(st.columns(len(cartes)), cartes):
        col.markdown(carte, unsafe_allow_html=True)


def maintenance_banner(etat: pd.DataFrame) -> None:
    """Bandeau d'alerte actif affiché en haut de chaque page administrateur."""
    if etat.empty:
        return
    rouges, oranges = etat[etat["niveau"] == "rouge"], etat[etat["niveau"] == "orange"]

    def chips(sous_df: pd.DataFrame, niveau: str) -> str:
        return "".join(
            f'<span class="chip chip-{niveau}">{html.escape(r.engin_id)} · {fmt(r.depuis_vidange)} h / {fmt(r.intervalle_vidange_h)} h</span>'
            for r in sous_df.itertuples()
        )

    if not rouges.empty:
        niveau, titre = "rouge", f"MAINTENANCE URGENTE – {len(rouges)} engin(s) ont dépassé l'intervalle de vidange"
        detail = chips(rouges, "rouge") + chips(oranges, "orange")
    elif not oranges.empty:
        niveau, titre = "orange", f"Maintenance à planifier – {len(oranges)} engin(s) approchent de la vidange"
        detail = chips(oranges, "orange")
    else:
        niveau, titre = "vert", "Maintenance préventive à jour – aucun engin proche du seuil de vidange"
        detail = ""
    st.markdown(
        f'<div class="alert-banner alert-{niveau}"><div class="alert-title">{html.escape(titre)}</div>'
        f'<div class="alert-text">{detail}</div></div>',
        unsafe_allow_html=True,
    )


def engin_card(row) -> str:
    """Fiche HTML de suivi vidange d'un engin (ligne issue de kpi.etat_maintenance)."""
    couleur = config.NIVEAU_COLORS[row.niveau]
    libelle = {"vert": "OK", "orange": "À planifier", "rouge": "Urgent"}[row.niveau]
    largeur = min(row.taux, 1.0) * 100
    reste = (
        f"Reste {fmt(row.restant)} h" if row.restant >= 0 else f"Dépassé de {fmt(-row.restant)} h"
    )
    return f"""
    <div class="engin-card" style="--accent:{couleur}">
      <div class="top"><span class="id">{html.escape(row.engin_id)}</span><span class="badge">{libelle}</span></div>
      <div class="meta">{html.escape(row.type_engin)} · {html.escape(str(row.designation))}</div>
      <div class="bar"><div style="width:{largeur:.0f}%"></div></div>
      <div class="foot"><span>{fmt(row.depuis_vidange)} / {fmt(row.intervalle_vidange_h)} h</span><span><b>{reste}</b></span></div>
      <div class="foot"><span>Horamètre : {fmt(row.cumul, 0)} h</span></div>
    </div>
    """


# --------------------------------------------------------------------------- #
# Thème Plotly
# --------------------------------------------------------------------------- #
def style_fig(fig, hauteur: int = 360, titre: str | None = None, legende: bool = True):
    fig.update_layout(
        template="plotly_white",
        height=hauteur,
        title=dict(text=titre, font=dict(size=14, color=C["navy"]), x=0, xanchor="left") if titre else None,
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=C["steel"]),
        margin=dict(l=10, r=10, t=48 if titre else 16, b=10),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=legende,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title=None),
        hoverlabel=dict(font_family="Inter, Segoe UI, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, linecolor=C["grey_light"])
    fig.update_yaxes(gridcolor="#EEF1F4", zeroline=False)
    return fig


def show_fig(fig) -> None:
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
