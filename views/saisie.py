"""
Vue « Saisie terrain » — seule page accessible au rôle Chef de Chantier.

Le type d'engin, l'engin et la date sont choisis hors du formulaire afin que la
liste des engins et celle des tâches se mettent à jour immédiatement ; le reste
est regroupé dans un formulaire unique (une seule validation, champs vidés après
enregistrement).
"""
import streamlit as st

from core import auth, config, data, kpi, ui


def render() -> None:
    ui.page_header("Saisie quotidienne des engins", "Relevé de fin de journée · à remplir pour chaque engin")
    user = auth.current_user()
    flotte = data.load_flotte()
    if flotte.empty:
        st.warning("Aucun engin n'est enregistré dans le parc. Un administrateur doit d'abord le renseigner.")
        return

    # -- 1. Identification de l'engin (hors formulaire : listes dépendantes) -----
    c1, c2, c3 = st.columns([1, 1.2, 1.6])
    jour = c1.date_input("Date du relevé", value=data.today_local(), max_value=data.today_local(), format="DD/MM/YYYY")
    type_engin = c2.selectbox("Type d'engin", config.TYPES_ENGINS)
    parc_type = flotte[flotte["type_engin"] == type_engin]
    if parc_type.empty:
        c3.selectbox("Engin", [], placeholder="Aucun engin de ce type")
        st.info("Aucun engin de ce type dans le parc.")
        return
    libelles = {
        r.engin_id: f"{r.engin_id} · {r.designation} ({r.immatriculation})" for r in parc_type.itertuples()
    }
    engin_id = c3.selectbox("Engin (identifiant / immatriculation)", list(libelles), format_func=libelles.get)
    engin = flotte.set_index("engin_id").loc[engin_id]

    deja = data.saisie_existe(jour, engin_id)
    if deja:
        st.warning(
            f"Une saisie existe déjà pour **{engin_id}** le {ui.fmt_date(jour)}. "
            "En enregistrant, vous la **remplacez** (correction)."
        )

    # -- 2. Formulaire de saisie -------------------------------------------------
    with st.form("form_saisie", clear_on_submit=True):
        f1, f2 = st.columns(2)
        heures = f1.number_input(
            "Heures de marche du jour (relevé horamètre)", min_value=0.0, max_value=24.0, value=0.0, step=0.5,
            format="%.1f", help="Heures de fonctionnement de l'engin sur la journée (différence d'horamètre).",
        )
        carburant = f2.number_input(
            "Carburant consommé / ajouté (litres)", min_value=0.0, max_value=2000.0, value=0.0, step=5.0,
            format="%.0f", help="Litres de gasoil ajoutés en fin de journée (plein à plein = consommation du jour).",
        )

        g1, g2 = st.columns(2)
        zone = g1.selectbox("Zone du chantier / tâche assignée", config.ZONES_TACHES[type_engin] + config.ZONES_AUTRES)
        statut = g2.radio("Statut opérationnel du jour", config.STATUTS, horizontal=True)

        st.markdown("**Signalement d'incident / panne (HSE)**")
        h1, h2 = st.columns(2)
        gravite = h1.selectbox(
            "Niveau de gravité", config.GRAVITES,
            help="Mineure : sans arrêt ni blessure. Majeure : arrêt prolongé, blessure, accident ou pollution.",
        )
        categorie = h2.selectbox("Nature de l'incident", config.CATEGORIES_INCIDENT)
        description = st.text_area(
            "Description (obligatoire si un incident est signalé)", height=90,
            placeholder="Ce qui s'est passé, où, pièce concernée, mesures immédiates…",
        )

        soumis = st.form_submit_button(
            "Enregistrer la saisie" + (" (remplace l'existante)" if deja else ""),
            type="primary", width="stretch",
        )

    st.caption(f"Saisie tracée au nom de **{user['nom']}** ({user['login']}) avec horodatage automatique.")

    if soumis:
        erreurs = _valider(heures, carburant, statut, gravite, description)
        if erreurs:
            for e in erreurs:
                st.error(e)
        else:
            data.save_saisie(
                dict(
                    date=jour, engin_id=engin_id, type_engin=type_engin, heures=heures, carburant_l=carburant,
                    zone_tache=zone, statut=statut,
                    categorie_incident=categorie if gravite != config.GRAVITE_AUCUN else "",
                    gravite_hse=gravite, description_incident=description.strip(),
                    saisi_par=f"{user['nom']} ({user['login']})",
                    horodatage=data.now_local().strftime("%Y-%m-%d %H:%M:%S"),
                ),
                remplacer=deja,
            )
            st.success(f"Saisie enregistrée pour {engin_id} – {ui.fmt_date(jour)}.")
            _retour_conso(heures, carburant, float(engin["conso_ref_lh"]))

    _recap_du_jour(user)


# --------------------------------------------------------------------------- #
def _valider(heures: float, carburant: float, statut: str, gravite: str, description: str) -> list[str]:
    erreurs = []
    if statut == config.STATUT_SERVICE and heures <= 0:
        erreurs.append("Statut « En service » : indiquez les heures de marche (supérieures à 0).")
    if heures > 0 and carburant <= 0:
        erreurs.append("Des heures de marche sont déclarées : indiquez aussi le carburant consommé.")
    if gravite != config.GRAVITE_AUCUN and not description.strip():
        erreurs.append("Un incident est signalé : décrivez-le dans le champ Description.")
    return erreurs


def _retour_conso(heures: float, carburant: float, reference: float) -> None:
    """Retour immédiat au conducteur : sa consommation du jour vs la référence."""
    if heures <= 0 or carburant <= 0:
        return
    lh = carburant / heures
    ecart = lh / reference - 1
    niveau = kpi.niveau_surconso(ecart)
    texte = f"Consommation du jour : **{ui.fmt(lh, 1)} L/h** (référence {ui.fmt(reference, 1)} L/h, {ecart:+.0%})."
    if niveau == "rouge":
        st.error(texte + " Surconsommation anormale : vérifiez la saisie, sinon alertez la maintenance.")
    elif niveau == "orange":
        st.warning(texte + " Légère surconsommation.")
    else:
        st.info(texte)


def _recap_du_jour(user: dict) -> None:
    saisies = data.load_saisies()
    ma_trace = f"{user['nom']} ({user['login']})"
    mes = saisies[(saisies["date"].dt.date == data.today_local()) & (saisies["saisi_par"] == ma_trace)]
    if not mes.empty:
        ids = ", ".join(sorted(mes["engin_id"].unique()))
        st.caption(f"Déjà saisis aujourd'hui par vous ({mes['engin_id'].nunique()}) : {ids}")
