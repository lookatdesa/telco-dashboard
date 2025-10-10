# auth.py
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from pathlib import Path


def load_config():
    """Carica la configurazione dal file config.yml"""
    config_path = r"C:\code\telco-dashboard\config.yml"
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.load(file, Loader=SafeLoader)
        return config
    except FileNotFoundError:
        st.error(f"⚠️ File config.yml non trovato in: {config_path}")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Errore nel caricamento della configurazione: {e}")
        st.stop()


def init_authenticator():
    """Inizializza l'autenticatore"""
    config = load_config()
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    return authenticator, config


def login_page(form_key: str = "login_default"):
    """Mostra la pagina di login e gestisce l'autenticazione (solo v0.4+)"""
    # Se già autenticato, esci subito
    if st.session_state.get("authentication_status"):
        return True

    authenticator, _ = init_authenticator()

    # singola chiamata, con key univoca per pagina
    authenticator.login(key=form_key)

    # controllo stato dal session_state
    if st.session_state.get("authentication_status"):
        return True
    elif st.session_state.get("authentication_status") is False:
        st.error("❌ Username o password errati")
    else:
        st.warning("⏳ Inserisci username e password per accedere")

    return False


def logout_button(key: str = "logout_default"):
    """Mostra il pulsante di logout nella sidebar"""
    if not st.session_state.get("authentication_status"):
        return
    authenticator, _ = init_authenticator()
    with st.sidebar:
        st.markdown("---")
        if st.session_state.get("name"):
            st.markdown(f"👤 **Utente:** {st.session_state['name']}")
            st.caption(f"Username: {st.session_state.get('username', 'N/A')}")
        authenticator.logout(button_name="🔓 Logout", location="sidebar", key=key)