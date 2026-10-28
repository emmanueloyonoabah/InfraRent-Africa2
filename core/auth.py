"""
Authentification par rôles (st.session_state).

Les comptes viennent de `st.secrets["users"]` s'ils existent (déploiement),
sinon des comptes de démonstration définis dans config.py.

Format attendu dans .streamlit/secrets.toml :

    [users.directeur]
    password = "mot-de-passe"          # ou password_sha256 = "<empreinte>"
    role = "admin"                     # "admin" ou "chef"
    nom = "Directeur de Projet"
"""
import hashlib
import hmac

import streamlit as st

from core import config

SESSION_KEY = "auth_user"


# --------------------------------------------------------------------------- #
# Comptes
# --------------------------------------------------------------------------- #
def _sha256(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


def _secrets_users() -> dict | None:
    """Retourne les comptes définis dans st.secrets, ou None si absents."""
    try:
        if "users" in st.secrets:
            return {login: dict(infos) for login, infos in st.secrets["users"].items()}
    except Exception:  # pas de fichier secrets.toml en local : cas normal
        pass
    return None


def load_users() -> dict:
    return _secrets_users() or config.DEMO_USERS


def using_demo_accounts() -> bool:
    return _secrets_users() is None


def authenticate(login: str, password: str) -> dict | None:
    """Vérifie le couple login / mot de passe. Retourne le profil ou None."""
    infos = load_users().get(login.strip().lower())
    if not infos:
        return None
    if "password_sha256" in infos:
        attendu = infos["password_sha256"]
    else:
        attendu = _sha256(infos.get("password", ""))
    # comparaison en temps constant pour éviter les attaques par mesure de durée
    if hmac.compare_digest(_sha256(password), attendu):
        return {
            "login": login.strip().lower(),
            "role": infos.get("role", config.ROLE_CHEF),
            "nom": infos.get("nom", login),
        }
    return None


# --------------------------------------------------------------------------- #
# Session
# --------------------------------------------------------------------------- #
def current_user() -> dict | None:
    return st.session_state.get(SESSION_KEY)


def is_admin() -> bool:
    user = current_user()
    return bool(user and user["role"] == config.ROLE_ADMIN)


def logout() -> None:
    st.session_state.pop(SESSION_KEY, None)


def render_login() -> None:
    """Écran de connexion centré (sans barre latérale)."""
    st.markdown(
        '<style>[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none}</style>',
        unsafe_allow_html=True,
    )
    _, centre, _ = st.columns([1, 1.3, 1])
    with centre:
        st.markdown(
            f"""
            <div class="login-brand">
                <div class="login-logo">IR</div>
                <h1>{config.APP_NAME}</h1>
                <p>{config.APP_TAGLINE}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            login = st.text_input("Identifiant", placeholder="ex. chef1")
            password = st.text_input("Mot de passe", type="password")
            ok = st.form_submit_button("Se connecter", type="primary", width="stretch")
        if ok:
            profil = authenticate(login, password)
            if profil:
                st.session_state[SESSION_KEY] = profil
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")

        if using_demo_accounts():
            with st.expander("Comptes de démonstration"):
                st.caption(
                    "Affichés uniquement parce qu'aucun `secrets` n'est configuré. "
                    "Voir le README pour définir vos propres comptes avant de partager l'application."
                )
                for ident, infos in config.DEMO_USERS.items():
                    st.markdown(
                        f"- **{ident}** / `{infos['password']}` — {config.ROLE_LABELS[infos['role']]}"
                    )
