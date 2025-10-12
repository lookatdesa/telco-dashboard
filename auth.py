# auth.py
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from pathlib import Path


def load_config():
    """Carica la configurazione dal file config.yml"""
    config_path = Path(__file__).parent / "config.yml"
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


def show_user_info():
    """Mostra le informazioni utente nella sidebar"""
    if st.session_state.get("authentication_status"):
        with st.sidebar:
            st.markdown("### 👤 Utente")
            st.markdown(f"**{st.session_state.get('name', 'N/A')}**")
            st.caption(f"@{st.session_state.get('username', 'N/A')}")
            
            if st.button("🔓 Logout", use_container_width=True, type="primary"):
                st.session_state["authentication_status"] = None
                st.session_state["name"] = None
                st.session_state["username"] = None
                st.rerun()
            
            st.markdown("---")


def login_page(form_key: str = "login_default"):
    """Mostra la pagina di login e gestisce l'autenticazione"""
    # Mostra info utente se già autenticato
    show_user_info()
    
    # Se già autenticato, esci subito
    if st.session_state.get("authentication_status"):
        return True

    authenticator, _ = init_authenticator()

    # Login con key univoca per pagina
    name, authentication_status, username = authenticator.login(key=form_key)

    # Salva nello stato
    if authentication_status:
        st.session_state["authentication_status"] = True
        st.session_state["name"] = name
        st.session_state["username"] = username
        st.rerun()
    elif authentication_status is False:
        st.error("❌ Username o password errati")
    else:
        st.warning("⏳ Inserisci username e password per accedere")

    return False


# Mantieni per retrocompatibilità ma non fa nulla
def logout_button(key: str = "logout_default"):
    """DEPRECATO - La funzione è ora integrata in login_page()"""
    pass