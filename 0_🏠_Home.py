import streamlit as st

# Configurazione iniziale
st.set_page_config(
    page_title="Contract Management Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Pagina di benvenuto
st.title("📊 Contract Management Dashboard")
st.markdown("---")

st.markdown("""
## Benvenuto nel Contract Management Dashboard

Questa è la dashboard per la gestione e l'analisi dei contratti.

### 📋 Sezioni Disponibili

Utilizza la barra laterale per navigare tra le diverse sezioni:

- **📊 Overview** - Vista generale dei KPI e statistiche principali
- **📋 Contratti** - Gestione e analisi dettagliata dei contratti
- **📦 Items** - Analisi degli articoli e classificazioni
- **🏢 Suppliers** - Gestione fornitori e distribuzione geografica

### 🔐 Autenticazione

Per accedere alle sezioni, utilizza le tue credenziali di login.

---

**Seleziona una pagina dalla barra laterale per iniziare** 👈
""")

st.info("💡 Usa il menu nella barra laterale per navigare tra le pagine")