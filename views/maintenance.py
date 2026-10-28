"""
Vue « Maintenance » — suivi des vidanges (alerte tous les 250 h par défaut),
enregistrement des interventions et historique.
"""
import pandas as pd
import streamlit as st

from core import auth, config, data, kpi, ui


def render() -> None:
    ui.page_header("Maintenance préventive", "Suivi des intervalles de vidange et des interventions")
    flotte, saisies, maint = data.load_flotte(), data.load_saisies(), data.load_maintenance()
    etat = kpi.etat_maintenance(flotte, saisies, maint)
    if etat.empty:
        st.info("Aucun engin dans le parc.")
        return

    c = etat["niveau"].value_counts()
    ui.kpi_row([
        ui.kpi_card("Vidange dépassée", str(c.get("rouge", 0)), "engin(s)", "≥ 100 % de l'intervalle", "rouge" if c.get("rouge", 0) else "vert"),
        ui.kpi_card("À planifier", str(c.get("orange", 0)), "engin(s)", f"≥ {config.SEUIL_ORANGE_VIDANGE:.0%} de l'intervalle", "orange" if c.get("orange", 0) else "vert"),
        ui.kpi_card("Conformes", str(c.get("vert", 0)), "engin(s)", "marge confortable", "vert"),
        ui.kpi_card("Coût maintenance (30 j)", ui.fmt(_cout_recent(maint) / 1e3), f"k{config.CURRENCY}", "interventions enregistrées"),
    ])

    ui.section("Suivi des vidanges par engin")
    cols = st.columns(3)
    for i, ligne in enumerate(etat.itertuples()):
        cols[i % 3].markdown(ui.engin_card(ligne), unsafe_allow_html=True)

    ui.section("Enregistrer une intervention")
    _formulaire(etat)

    ui.section("Historique des interventions")
    _historique(maint)


def _cout_recent(maint: pd.DataFrame, jours: int = 30) -> float:
    if maint.empty:
        return 0.0
    limite = pd.Timestamp(data.today_local()) - pd.Timedelta(days=jours)
    return float(maint.loc[maint["date"] >= limite, "cout_fcfa"].sum())


def _formulaire(etat: pd.DataFrame) -> None:
    user = auth.current_user()
    cumuls = etat.set_index("engin_id")["cumul"]
    with st.form("form_maintenance", clear_on_submit=True):
        a, b, c = st.columns([1.2, 1.2, 1])
        engin_id = a.selectbox("Engin", sorted(cumuls.index))
        type_interv = b.selectbox("Type d'intervention", config.TYPES_INTERVENTION)
        jour = c.date_input("Date", value=data.today_local(), max_value=data.today_local(), format="DD/MM/YYYY")
        d, e = st.columns(2)
        horametre = d.number_input(
            "Horamètre au moment de l'intervention (h)", min_value=0.0, step=1.0, format="%.0f",
            help="Laisser à 0 pour utiliser l'horamètre cumulé actuel de l'engin.",
        )
        cout = e.number_input(f"Coût ({config.CURRENCY})", min_value=0, step=5000)
        description = st.text_area("Description", height=80, placeholder="Pièces remplacées, atelier, remarques…")
        ok = st.form_submit_button("Enregistrer l'intervention", type="primary")
    st.caption("Une **vidange moteur** remet à zéro le compteur d'alerte de l'engin concerné.")

    if ok:
        h = horametre if horametre > 0 else float(cumuls[engin_id])
        data.save_maintenance(dict(
            date=jour, engin_id=engin_id, type_intervention=type_interv, horametre=round(h, 1), cout_fcfa=cout,
            description=description.strip(), saisi_par=f"{user['nom']} ({user['login']})",
            horodatage=data.now_local().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        # le toast survit au rerun, qui rafraîchit aussi le bandeau d'alerte
        st.toast(f"{type_interv} enregistrée pour {engin_id} (horamètre {ui.fmt(h)} h).", icon="✅")
        st.rerun()


def _historique(maint: pd.DataFrame) -> None:
    if maint.empty:
        st.caption("Aucune intervention enregistrée.")
        return
    t = maint.sort_values("date", ascending=False)
    table = pd.DataFrame({
        "Date": t["date"].dt.strftime("%d/%m/%Y"), "Engin": t["engin_id"], "Intervention": t["type_intervention"],
        "Horamètre (h)": t["horametre"], f"Coût ({config.CURRENCY})": t["cout_fcfa"],
        "Description": t["description"], "Enregistré par": t["saisi_par"],
    })
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            "Horamètre (h)": st.column_config.NumberColumn(format="%.0f"),
            f"Coût ({config.CURRENCY})": st.column_config.NumberColumn(format="%d"),
        },
    )
