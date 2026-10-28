"""
InfraRent Africa — gestion de flotte d'engins de chantier (BTP, Cameroun).

Point d'entrée Streamlit :  streamlit run app.py

Organisation du projet
  app.py            ce fichier : configuration, connexion, navigation par rôle
  core/config.py    constantes métier, seuils, couleurs, comptes de démo
  core/auth.py      authentification (st.session_state + st.secrets)
  core/data.py      stockage CSV, jeu de données de démonstration
  core/kpi.py       calculs : coûts, L/h, disponibilité, vidange, MTBF/MTTR
  core/ui.py        feuille de style, cartes KPI, bandeau d'alerte, thème Plotly
  views/            une page par fichier (saisie, dashboard, maintenance, ...)
"""
import streamlit as st

from core import auth, config, data, kpi, ui
from views import dashboard, exports, hse, maintenance, pannes, saisie

st.set_page_config(
    page_title=f"{config.APP_NAME} · Gestion de flotte BTP",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="auto",
)
ui.inject_css()
data.init_storage()

# --------------------------------------------------------------------------- #
# 1. Connexion obligatoire
# --------------------------------------------------------------------------- #
user = auth.current_user()
if user is None:
    auth.render_login()
    st.stop()


# --------------------------------------------------------------------------- #
# 2. Pages selon le rôle
#    Le chef de chantier ne reçoit QUE la page de saisie : les autres pages
#    n'existent pas pour lui (même en tapant leur adresse dans le navigateur).
# --------------------------------------------------------------------------- #
def page_admin(module):
    """Enveloppe une vue administrateur : contrôle du rôle + bandeau d'alerte maintenance."""

    def _page() -> None:
        if not auth.is_admin():
            st.error("Accès réservé à l'administrateur.")
            st.stop()
        etat = kpi.etat_maintenance(data.load_flotte(), data.load_saisies(), data.load_maintenance())
        ui.maintenance_banner(etat)
        module.render()

    return _page


page_saisie = st.Page(saisie.render, title="Saisie terrain", icon=":material/edit_note:", url_path="saisie")

if auth.is_admin():
    pages = [
        st.Page(page_admin(dashboard), title="Tableau de bord", icon=":material/dashboard:", url_path="tableau-de-bord", default=True),
        st.Page(page_admin(maintenance), title="Maintenance", icon=":material/build:", url_path="maintenance"),
        st.Page(page_admin(pannes), title="Pannes & carnet de santé", icon=":material/health_and_safety:", url_path="pannes"),
        st.Page(page_admin(hse), title="HSE", icon=":material/shield:", url_path="hse"),
        page_saisie,
        st.Page(page_admin(exports), title="Rapports & données", icon=":material/download:", url_path="rapports"),
    ]
else:
    pages = [page_saisie]

navigation = st.navigation(pages, position="sidebar")

# --------------------------------------------------------------------------- #
# 3. Barre latérale : utilisateur connecté + déconnexion
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown(
        f'<div class="side-user"><b>{user["nom"]}</b><span>{config.ROLE_LABELS.get(user["role"], user["role"])}'
        f' · {user["login"]}</span></div>',
        unsafe_allow_html=True,
    )
    st.button("Se déconnecter", on_click=auth.logout, width="stretch")
    st.caption(f"{config.APP_NAME} · {config.APP_TAGLINE}")

navigation.run()
