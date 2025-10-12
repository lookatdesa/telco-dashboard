import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import login_page, logout_button

# Configurazione pagina
st.set_page_config(
    page_title="Contract Management Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Autenticazione
if not login_page(form_key="login_overview"):
    st.stop()

# Configurazioni colori e costanti
DOMAIN_COLORS = {
    'networking': '#3498db',
    'IT': '#2ecc71',
    'sicurezza': '#e74c3c',
    'telecomunicazioni': '#f39c12'
}

ITEM_TYPE_COLORS = {
    'HARDWARE': '#3498db',
    'SOFTWARE': '#9b59b6',
    'SERVICE': '#e67e22'
}

# Directory base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'

# Funzione di caricamento dati con caching
@st.cache_data
def load_data():
    """Carica tutti i dataset necessari"""
    try:
        contracts = pd.read_csv(DATA_DIR / 'contracts.csv')
        items = pd.read_csv(DATA_DIR / 'items.csv')
        suppliers = pd.read_csv(DATA_DIR / 'suppliers.csv')
        
        # Conversione date (rimuove timezone se presente)
        date_columns = ['start_date', 'end_date']
        for col in date_columns:
            if col in contracts.columns:
                contracts[col] = pd.to_datetime(contracts[col], errors='coerce', utc=True)
                contracts[col] = contracts[col].dt.tz_localize(None)
        
        # Calcolo status contratti
        today = pd.Timestamp.now().tz_localize(None)
        contracts['status'] = contracts['end_date'].apply(
            lambda x: 'Scaduto' if pd.notna(x) and x < today 
            else 'In scadenza' if pd.notna(x) and x < today + timedelta(days=90)
            else 'Attivo'
        )
        
        return contracts, items, suppliers
    except Exception as e:
        st.error(f"Errore nel caricamento dei dati: {e}")
        return None, None, None

# Caricamento dati
contracts_df, items_df, suppliers_df = load_data()

# Sidebar
with st.sidebar:
    st.title("📊 Contract Dashboard")
    st.markdown("---")

    logout_button()
    
    # Info dataset
    if contracts_df is not None:
        st.metric("Contratti", len(contracts_df))
        st.metric("Fornitori", len(suppliers_df))
        st.metric("Items", len(items_df))
        
    st.markdown("---")
    st.markdown("### Navigazione")
    st.markdown("""
    1. 📊 **Overview** - Vista generale
    2. 📋 **Contratti** - Dettaglio contratti
    3. 📦 **Items** - Analisi articoli
    4. 🏢 **Suppliers** - Gestione fornitori
    """)

# Main content
st.title("📊 Overview - Contract Management Dashboard")
st.markdown("---")

if contracts_df is None:
    st.error("⚠️ Impossibile caricare i dati. Verifica che i file CSV siano presenti nella directory.")
    st.stop()

# KPI Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_contracts = len(contracts_df)
    active_contracts = len(contracts_df[contracts_df['status'] == 'Attivo'])
    st.metric(
        label="📋 Contratti Totali",
        value=total_contracts,
        delta=f"{active_contracts} attivi"
    )

with col2:
    total_suppliers = len(suppliers_df)
    supplier_contracts = contracts_df.groupby('supplier').size()
    top_supplier = supplier_contracts.idxmax() if len(supplier_contracts) > 0 else "N/A"
    st.metric(
        label="🏢 Fornitori Attivi",
        value=total_suppliers,
        delta=f"Top: {top_supplier[:20]}..."
    )

with col3:
    total_value = contracts_df['total_amount'].sum()
    active_value = contracts_df[contracts_df['status'] == 'Attivo']['total_amount'].sum()
    st.metric(
        label="💶 Valore Totale",
        value=f"€{total_value:,.0f}",
        delta=f"€{active_value:,.0f} attivi"
    )

with col4:
    total_items = len(items_df)
    hw_count = len(items_df[items_df['item_type'] == 'HARDWARE'])
    sw_count = len(items_df[items_df['item_type'] == 'SOFTWARE'])
    service_count = len(items_df[items_df['item_type'] == 'SERVICE'])
    st.metric(
        label="📦 Items Totali",
        value=total_items,
        delta=f"HW:{hw_count} SW:{sw_count} SV:{service_count}"
    )

st.markdown("---")

# Alert Section
st.subheader("🚨 Alert e Notifiche")
col_alert1, col_alert2 = st.columns(2)

with col_alert1:
    expiring = contracts_df[contracts_df['status'] == 'In scadenza']
    st.warning(f"⚠️ **{len(expiring)} contratti in scadenza** (prossimi 90 giorni)")
    if len(expiring) > 0:
        with st.expander("Vedi dettagli"):
            st.dataframe(
                expiring[['contract_id', 'supplier', 'end_date', 'total_amount']],
                hide_index=True
            )

with col_alert2:
    low_confidence = items_df[items_df['class_confidence_level'] == 'LOW']
    st.info(f"🔍 **{len(low_confidence)} items** con bassa confidence da validare")
    if len(low_confidence) > 0:
        with st.expander("Vedi dettagli"):
            st.dataframe(
                low_confidence[['item_description', 'classification_label', 'class_final_score']].head(10),
                hide_index=True
            )

st.markdown("---")

# Visualizzazioni principali
col_viz1, col_viz2 = st.columns(2)

with col_viz1:
    st.subheader("📈 Valore Contratti per Dominio")
    domain_value = contracts_df.groupby('contract_domain')['total_amount'].sum().reset_index()
    domain_value = domain_value.sort_values('total_amount', ascending=False)
    
    fig_domain = px.pie(
        domain_value,
        values='total_amount',
        names='contract_domain',
        color='contract_domain',
        color_discrete_map=DOMAIN_COLORS,
        hole=0.4
    )
    fig_domain.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_domain, use_container_width=True)

with col_viz2:
    st.subheader("🏆 Top 10 Fornitori per Valore")
    supplier_value = contracts_df.groupby('supplier')['total_amount'].sum().reset_index()
    supplier_value = supplier_value.sort_values('total_amount', ascending=True).tail(10)
    
    fig_suppliers = px.bar(
        supplier_value,
        x='total_amount',
        y='supplier',
        orientation='h',
        color='total_amount',
        color_continuous_scale='Blues'
    )
    fig_suppliers.update_layout(showlegend=False, xaxis_title="Valore (€)", yaxis_title="")
    st.plotly_chart(fig_suppliers, use_container_width=True)

# Seconda riga visualizzazioni
col_viz3, col_viz4 = st.columns(2)

with col_viz3:
    st.subheader("📊 Composizione Items (HW/SW/SERVICE)")
    item_composition = items_df.groupby('item_type')['total_price'].sum().reset_index()
    
    fig_items = px.bar(
        item_composition,
        x='item_type',
        y='total_price',
        color='item_type',
        color_discrete_map=ITEM_TYPE_COLORS,
        text='total_price'
    )
    fig_items.update_traces(texttemplate='€%{text:,.0f}', textposition='outside')
    fig_items.update_layout(showlegend=False, xaxis_title="", yaxis_title="Valore (€)")
    st.plotly_chart(fig_items, use_container_width=True)

with col_viz4:
    st.subheader("📅 Status Contratti")
    status_counts = contracts_df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    
    status_colors = {'Attivo': '#2ecc71', 'In scadenza': '#f39c12', 'Scaduto': '#e74c3c'}
    
    fig_status = px.pie(
        status_counts,
        values='count',
        names='status',
        color='status',
        color_discrete_map=status_colors
    )
    fig_status.update_traces(textposition='inside', textinfo='percent+label+value')
    st.plotly_chart(fig_status, use_container_width=True)

st.markdown("---")

# Timeline contratti
st.subheader("📈 Timeline Contratti Attivi")
timeline_data = contracts_df[contracts_df['status'].isin(['Attivo', 'In scadenza'])].copy()
timeline_data['year_month'] = timeline_data['start_date'].dt.to_period('M').astype(str)
timeline_monthly = timeline_data.groupby('year_month')['total_amount'].sum().reset_index()

fig_timeline = px.line(
    timeline_monthly,
    x='year_month',
    y='total_amount',
    markers=True,
    title="Valore contratti per mese di inizio"
)
fig_timeline.update_layout(xaxis_title="Mese", yaxis_title="Valore (€)")
st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")

# Quick Stats Tables
col_table1, col_table2 = st.columns(2)

with col_table1:
    st.subheader("🆕 Ultimi 5 Contratti")
    latest_contracts = contracts_df.sort_values('start_date', ascending=False).head(5)
    st.dataframe(
        latest_contracts[['contract_id', 'supplier', 'start_date', 'total_amount']],
        hide_index=True,
        use_container_width=True
    )

with col_table2:
    st.subheader("💰 Top 5 Items per Valore")
    top_items = items_df.nlargest(5, 'total_price')
    st.dataframe(
        top_items[['item_description', 'item_type', 'total_price']],
        hide_index=True,
        use_container_width=True
    )

st.markdown("---")

# Export section
st.subheader("📤 Export Dati")
col_export1, col_export2 = st.columns([3, 1])

with col_export1:
    st.info("💡 Esporta un riepilogo completo in formato Excel con tutti i KPI e le statistiche principali")

with col_export2:
    if st.button("📥 Download Excel", use_container_width=True):
        from io import BytesIO
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: KPI Summary
            kpi_data = pd.DataFrame({
                'Metrica': ['Contratti Totali', 'Contratti Attivi', 'Fornitori', 'Items Totali', 'Valore Totale (€)'],
                'Valore': [total_contracts, active_contracts, total_suppliers, total_items, total_value]
            })
            kpi_data.to_excel(writer, sheet_name='KPI Summary', index=False)
            
            # Sheet 2: Contratti Attivi
            active_df = contracts_df[contracts_df['status'] == 'Attivo']
            active_df.to_excel(writer, sheet_name='Contratti Attivi', index=False)
            
            # Sheet 3: Top Fornitori
            supplier_value.to_excel(writer, sheet_name='Top Fornitori', index=False)
            
            # Sheet 4: Distribuzione Dominio
            domain_value.to_excel(writer, sheet_name='Per Dominio', index=False)
        
        st.download_button(
            label="⬇️ Scarica Report",
            data=output.getvalue(),
            file_name=f"contract_overview_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")
st.caption("Contract Management Dashboard v1.0 - Developed with Streamlit")