import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import login_page, logout_button

st.set_page_config(page_title="Suppliers", page_icon="🏢", layout="wide")

# pages/4_🏢_Suppliers.py
if not login_page(form_key="login_suppliers"):
    st.stop()

logout_button()

# Configurazioni colori
DOMAIN_COLORS = {
    'networking': '#3498db',
    'IT': '#2ecc71',
    'sicurezza': '#e74c3c',
    'telecomunicazioni': '#f39c12'
}

# Caricamento dati
@st.cache_data
def load_data():
    suppliers = pd.read_csv(r'C:\code\telco-dashboard\data\suppliers.csv')
    contracts = pd.read_csv(r'C:\code\telco-dashboard\data\contracts.csv')
    items = pd.read_csv(r'C:\code\telco-dashboard\data\items.csv')
    return suppliers, contracts, items

suppliers_df, contracts_df, items_df = load_data()

# Calcolo statistiche per fornitore
@st.cache_data
def calculate_supplier_stats(suppliers_df, contracts_df):
    stats = []
    
    for idx, supplier in suppliers_df.iterrows():
        # Estrai il numero dall'ID (rimuovi prefisso "supplier_")
        supplier_id_num = str(supplier['id']).replace('supplier_', '')
        
        # Prova matching con supplier_id nei contratti
        supplier_contracts = contracts_df[contracts_df['supplier_id'].astype(str) == supplier_id_num]
        
        # Se non trova, prova con display_name
        if len(supplier_contracts) == 0:
            supplier_contracts = contracts_df[contracts_df['supplier'] == supplier['display_name']]
        
        # Se non trova, prova con canonical_name
        if len(supplier_contracts) == 0:
            supplier_contracts = contracts_df[contracts_df['supplier'] == supplier['canonical_name']]
        
        # Se ancora non trova, prova con supplier_name
        if len(supplier_contracts) == 0:
            supplier_contracts = contracts_df[contracts_df['supplier'] == supplier['supplier_name']]
        
        total_value = supplier_contracts['total_amount'].sum()
        n_contracts = len(supplier_contracts)
        
        stats.append({
            'id': supplier['id'],
            'supplier_slug': supplier['supplier_slug'],
            'supplier_name': supplier['supplier_name'],
            'canonical_name': supplier['canonical_name'],
            'display_name': supplier['display_name'],
            'specialization': supplier['specialization'],
            'address': supplier['address'],
            'total_value': total_value,
            'n_contracts': n_contracts
        })
    
    return pd.DataFrame(stats)

supplier_stats = calculate_supplier_stats(suppliers_df, contracts_df)

# Header
st.title("🏢 Gestione Fornitori")
st.markdown("Analizza i fornitori, esplora le specializzazioni e visualizza la distribuzione geografica")
st.markdown("---")

# KPI Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏢 Fornitori Totali", len(suppliers_df))

with col2:
    top_supplier = supplier_stats.nlargest(1, 'total_value').iloc[0] if len(supplier_stats) > 0 else None
    if top_supplier is not None:
        st.metric("🏆 Top Fornitore", top_supplier['display_name'][:20])
    else:
        st.metric("🏆 Top Fornitore", "N/A")

with col3:
    total_value = supplier_stats['total_value'].sum()
    st.metric("💰 Valore Totale", f"€{total_value:,.0f}")

with col4:
    specializations = suppliers_df['specialization'].nunique()
    st.metric("📊 Specializzazioni", specializations)

st.markdown("---")

# Filtri
st.subheader("🔍 Filtri")

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    search_name = st.text_input("🔎 Cerca per Nome", placeholder="Nome fornitore...")

with col_f2:
    spec_list = ['Tutti'] + sorted(suppliers_df['specialization'].dropna().unique().tolist())
    selected_spec = st.selectbox("📁 Specializzazione", spec_list)

with col_f3:
    sort_by = st.selectbox("🔄 Ordina per", ["Nome", "Valore Contratti", "N° Contratti"])

# Applicazione filtri
filtered_suppliers = supplier_stats.copy()

if search_name:
    filtered_suppliers = filtered_suppliers[
        filtered_suppliers['display_name'].str.contains(search_name, case=False, na=False) |
        filtered_suppliers['canonical_name'].str.contains(search_name, case=False, na=False)
    ]

if selected_spec != 'Tutti':
    filtered_suppliers = filtered_suppliers[filtered_suppliers['specialization'] == selected_spec]

# Ordinamento
if sort_by == "Nome":
    filtered_suppliers = filtered_suppliers.sort_values('display_name')
elif sort_by == "Valore Contratti":
    filtered_suppliers = filtered_suppliers.sort_values('total_value', ascending=False)
else:
    filtered_suppliers = filtered_suppliers.sort_values('n_contracts', ascending=False)

st.markdown("---")

# Visualizzazioni
st.subheader("📊 Visualizzazioni")

col_viz1, col_viz2 = st.columns(2)

with col_viz1:
    st.markdown("##### 🏆 Top 10 Fornitori per Valore")
    top10 = supplier_stats.nlargest(10, 'total_value')
    
    fig_top10 = px.bar(
        top10,
        x='total_value',
        y='display_name',
        orientation='h',
        color='total_value',
        color_continuous_scale='Blues',
        labels={'total_value': 'Valore Totale (€)', 'display_name': 'Fornitore'}
    )
    fig_top10.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_top10, use_container_width=True)

with col_viz2:
    st.markdown("##### 📊 Distribuzione per Specializzazione")
    spec_dist = suppliers_df['specialization'].value_counts().reset_index()
    spec_dist.columns = ['specialization', 'count']
    
    fig_spec = px.pie(
        spec_dist,
        values='count',
        names='specialization',
        color='specialization',
        color_discrete_map=DOMAIN_COLORS,
        hole=0.4
    )
    fig_spec.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_spec, use_container_width=True)

# Seconda riga visualizzazioni
col_viz3, col_viz4 = st.columns(2)

with col_viz3:
    st.markdown("##### 📈 Treemap - Valore per Fornitore")
    
    treemap_data = supplier_stats[supplier_stats['total_value'] > 0].copy()
    
    if len(treemap_data) > 0:
        fig_treemap = px.treemap(
            treemap_data,
            path=['specialization', 'display_name'],
            values='total_value',
            color='specialization',
            color_discrete_map=DOMAIN_COLORS,
            hover_data=['n_contracts']
        )
        st.plotly_chart(fig_treemap, use_container_width=True)
    else:
        st.info("Nessun dato disponibile per la treemap")

with col_viz4:
    st.markdown("##### 📊 Numero Contratti per Fornitore")
    
    contracts_dist = supplier_stats.nlargest(10, 'n_contracts')
    
    fig_contracts = px.bar(
        contracts_dist,
        x='n_contracts',
        y='display_name',
        orientation='h',
        color='specialization',
        color_discrete_map=DOMAIN_COLORS,
        labels={'n_contracts': 'N° Contratti', 'display_name': 'Fornitore'}
    )
    fig_contracts.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_contracts, use_container_width=True)

st.markdown("---")

# Mappa Geografica
st.subheader("🗺️ Distribuzione Geografica Fornitori")

# Funzione per geocoding
@st.cache_data
def geocode_address(address):
    """Geocodifica un indirizzo"""
    if pd.isna(address) or address == '':
        return None, None
    
    try:
        geolocator = Nominatim(user_agent="contract_dashboard")
        time.sleep(1)  # Rate limiting
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
    except (GeocoderTimedOut, Exception):
        pass
    
    return None, None

# Filtra fornitori con indirizzo
suppliers_with_address = suppliers_df[suppliers_df['address'].notna() & (suppliers_df['address'] != '')].copy()

if len(suppliers_with_address) > 0:
    st.info(f"📍 Trovati {len(suppliers_with_address)} fornitori con indirizzo")
    
    # Geocoding
    with st.spinner("🌍 Geocodifica indirizzi in corso..."):
        coords = []
        for idx, row in suppliers_with_address.iterrows():
            lat, lon = geocode_address(row['address'])
            coords.append({'lat': lat, 'lon': lon})
        
        suppliers_with_address['lat'] = [c['lat'] for c in coords]
        suppliers_with_address['lon'] = [c['lon'] for c in coords]
    
    # Filtra solo quelli geocodificati con successo
    suppliers_mapped = suppliers_with_address.dropna(subset=['lat', 'lon'])
    
    if len(suppliers_mapped) > 0:
        st.success(f"✅ Geocodificati {len(suppliers_mapped)} fornitori")
        
        # Crea mappa
        center_lat = suppliers_mapped['lat'].mean()
        center_lon = suppliers_mapped['lon'].mean()
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        
        # Aggiungi marker per ogni fornitore
        for idx, row in suppliers_mapped.iterrows():
            # Trova stats del fornitore
            supplier_stat = supplier_stats[supplier_stats['id'] == row['id']]
            
            if len(supplier_stat) > 0:
                stat = supplier_stat.iloc[0]
                popup_text = f"""
                <b>{row['display_name']}</b><br>
                Specializzazione: {row['specialization']}<br>
                Contratti: {stat['n_contracts']}<br>
                Valore: €{stat['total_value']:,.2f}<br>
                Indirizzo: {row['address']}
                """
            else:
                popup_text = f"""
                <b>{row['display_name']}</b><br>
                Specializzazione: {row['specialization']}<br>
                Indirizzo: {row['address']}
                """
            
            # Colore marker per specializzazione
            color = DOMAIN_COLORS.get(row['specialization'], 'gray')
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=8,
                popup=folium.Popup(popup_text, max_width=300),
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)
        
        st_folium(m, width=None, height=500)
    else:
        st.warning("⚠️ Nessun fornitore geocodificato con successo")
else:
    st.warning("⚠️ Nessun fornitore con indirizzo disponibile")

st.markdown("---")

# Tabella Fornitori Master
st.subheader("📋 Tabella Fornitori")

# Preparazione dati per visualizzazione
display_suppliers = filtered_suppliers.copy()
display_suppliers['total_value_fmt'] = display_suppliers['total_value'].apply(
    lambda x: f"€{x:,.2f}" if pd.notna(x) and x > 0 else "€0.00"
)

# Merge con suppliers_df per avere tutte le info
display_suppliers = display_suppliers.merge(
    suppliers_df[['id', 'known_technologies', 'typical_categories']],
    on='id',
    how='left'
)

st.dataframe(
    display_suppliers[['display_name', 'specialization', 'n_contracts', 'total_value_fmt', 
                      'known_technologies', 'typical_categories']],
    column_config={
        "display_name": "Fornitore",
        "specialization": "Specializzazione",
        "n_contracts": st.column_config.NumberColumn("N° Contratti", format="%d"),
        "total_value_fmt": "Valore Totale",
        "known_technologies": st.column_config.TextColumn("Tecnologie", width="medium"),
        "typical_categories": st.column_config.TextColumn("Categorie", width="medium")
    },
    hide_index=True,
    use_container_width=True,
    height=400
)

st.markdown("---")

# Dettaglio Fornitore
st.subheader("🔍 Dettaglio Fornitore")

if len(filtered_suppliers) > 0:
    selected_supplier_id = st.selectbox(
        "Seleziona un fornitore per vedere i dettagli:",
        filtered_suppliers['id'].tolist(),
        format_func=lambda x: filtered_suppliers[filtered_suppliers['id']==x].iloc[0]['display_name']
    )
    
    if selected_supplier_id:
        # Recupera dati completi del fornitore
        supplier_detail = suppliers_df[suppliers_df['id'] == selected_supplier_id].iloc[0]
        supplier_stat_detail = supplier_stats[supplier_stats['id'] == selected_supplier_id].iloc[0]
        
        with st.expander("📊 Informazioni Dettagliate", expanded=True):
            col_d1, col_d2, col_d3 = st.columns(3)
            
            with col_d1:
                st.markdown("##### 📇 Anagrafica")
                st.write(f"**Nome Canonico:** {supplier_detail['canonical_name']}")
                st.write(f"**Nome Display:** {supplier_detail['display_name']}")
                st.write(f"**Supplier Name:** {supplier_detail['supplier_name']}")
                st.write(f"**ID Fornitore:** {supplier_detail['id']}")
                
                if pd.notna(supplier_detail['address']):
                    st.write(f"**Indirizzo:** {supplier_detail['address']}")
            
            with col_d2:
                st.markdown("##### 🎯 Specializzazione")
                st.write(f"**Dominio:** {supplier_detail['specialization']}")
                
                if pd.notna(supplier_detail['known_technologies']):
                    st.write(f"**Tecnologie:** {supplier_detail['known_technologies']}")
                
                if pd.notna(supplier_detail['typical_categories']):
                    st.write(f"**Categorie:** {supplier_detail['typical_categories']}")
            
            with col_d3:
                st.markdown("##### 💰 Statistiche")
                st.metric("Contratti", supplier_stat_detail['n_contracts'])
                st.metric("Valore Totale", f"€{supplier_stat_detail['total_value']:,.2f}")
                
                if supplier_stat_detail['n_contracts'] > 0:
                    avg_value = supplier_stat_detail['total_value'] / supplier_stat_detail['n_contracts']
                    st.metric("Valore Medio", f"€{avg_value:,.2f}")
            
            # Varianti nome
            st.markdown("##### 🔤 Varianti Nome")
            if pd.notna(supplier_detail['name_variants']):
                variants = supplier_detail['name_variants'].split('|')
                cols_variants = st.columns(min(len(variants), 4))
                for i, variant in enumerate(variants[:4]):
                    with cols_variants[i]:
                        st.info(variant)
                if len(variants) > 4:
                    st.caption(f"...e altre {len(variants)-4} varianti")
            else:
                st.write("Nessuna variante disponibile")
            
            # Lista contratti del fornitore
            st.markdown("##### 📋 Contratti Associati")
            
            supplier_contracts = contracts_df[
                (contracts_df['supplier'] == supplier_detail['display_name']) |
                (contracts_df['supplier'] == supplier_detail['canonical_name']) |
                (contracts_df['supplier'] == supplier_detail['supplier_name'])
            ]
            
            if len(supplier_contracts) > 0:
                display_contracts = supplier_contracts[['contract_id', 'contract_subject', 'start_date', 
                                                        'end_date', 'total_amount']].copy()
                display_contracts['start_date'] = pd.to_datetime(display_contracts['start_date']).dt.strftime('%d/%m/%Y')
                display_contracts['end_date'] = pd.to_datetime(display_contracts['end_date']).dt.strftime('%d/%m/%Y')
                display_contracts['total_amount'] = display_contracts['total_amount'].apply(
                    lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A"
                )
                
                st.dataframe(
                    display_contracts,
                    column_config={
                        "contract_id": "Contract ID",
                        "contract_subject": st.column_config.TextColumn("Oggetto", width="large"),
                        "start_date": "Data Inizio",
                        "end_date": "Data Fine",
                        "total_amount": "Valore"
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Nessun contratto trovato per questo fornitore")
            
            # Trend storico
            if len(supplier_contracts) > 1:
                st.markdown("##### 📈 Trend Storico")
                
                trend_data = supplier_contracts.copy()
                trend_data['start_date'] = pd.to_datetime(trend_data['start_date'])
                trend_data = trend_data.sort_values('start_date')
                trend_data['year_month'] = trend_data['start_date'].dt.to_period('M').astype(str)
                
                trend_monthly = trend_data.groupby('year_month')['total_amount'].sum().reset_index()
                
                fig_trend = px.line(
                    trend_monthly,
                    x='year_month',
                    y='total_amount',
                    markers=True,
                    labels={'year_month': 'Periodo', 'total_amount': 'Valore (€)'}
                )
                st.plotly_chart(fig_trend, use_container_width=True)

else:
    st.warning("⚠️ Nessun fornitore trovato con i filtri applicati")

st.markdown("---")

# Export
st.subheader("📤 Export Dati")

col_exp1, col_exp2 = st.columns([3, 1])

with col_exp1:
    st.info("💾 Esporta l'elenco completo dei fornitori con le statistiche")

with col_exp2:
    if st.button("📥 Download Excel", use_container_width=True):
        from io import BytesIO
        from datetime import datetime
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: Fornitori con statistiche
            export_data = supplier_stats.merge(
                suppliers_df[['id', 'address', 'known_technologies', 'typical_categories']],
                on='id',
                how='left'
            )
            export_data.to_excel(writer, sheet_name='Fornitori', index=False)
            
            # Sheet 2: Dettaglio contratti per fornitore
            contracts_export = contracts_df[['contract_id', 'supplier', 'contract_subject', 
                                            'start_date', 'end_date', 'total_amount']]
            contracts_export.to_excel(writer, sheet_name='Contratti per Fornitore', index=False)
        
        st.download_button(
            label="⬇️ Scarica",
            data=output.getvalue(),
            file_name=f"suppliers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")
st.caption("Pagina Suppliers - Contract Management Dashboard")