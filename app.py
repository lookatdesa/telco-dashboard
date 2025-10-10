import streamlit as st

# Configurazione iniziale
st.set_page_config(
    page_title="Contract Management Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Redirect automatico alla pagina Overview
st.switch_page("pages/1_📊_Overview.py")