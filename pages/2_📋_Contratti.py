import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import login_page, logout_button

st.set_page_config(page_title="Contratti", page_icon="📋", layout="wide")

# Autenticazione
if not login_page(form_key="login_contratti"):
    st.stop()

logout_button()

# Directory base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'

# Caricamento dati
@st.cache_data
def load_data():
    contracts = pd.read_csv(DATA_DIR / 'contracts.csv')
    items = pd.read_csv(DATA_DIR / 'items.csv')
    
    # Conversione date
    contracts['start_date'] = pd.to_datetime(contracts['start_date'], errors='coerce', utc=True)
    contracts['end_date'] = pd.to_datetime(contracts['end_date'], errors='coerce', utc=True)
    contracts['start_date'] = contracts['start_date'].dt.tz_localize(None)
    contracts['end_date'] = contracts['end_date'].dt.tz_localize(None)
    
    # Calcolo status
    today = pd.Timestamp.now().tz_localize(None)
    contracts['status'] = contracts['end_date'].apply(
        lambda x: 'Scaduto' if pd.notna(x) and x < today 
        else 'In scadenza' if pd.notna(x) and x < today + timedelta(days=90)
        else 'Attivo'
    )
    
    return contracts, items

contracts_df, items_df = load_data()

# Header
st.title("📋 Gestione Contratti")
st.markdown("Esplora i contratti, naviga tra le versioni e analizza gli items associati")
st.markdown("---")

# Filtri
st.subheader("🔍 Filtri")
col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)

with col_f1:
    search_contract = st.text_input("🔢 Numero Contratto", placeholder="Es: 7010148320")

with col_f2:
    suppliers_df = pd.read_csv(DATA_DIR / 'suppliers.csv')
    supplier_mapping = dict(zip(suppliers_df['display_name'], suppliers_df['canonical_name']))
    supplier_mapping.update(dict(zip(suppliers_df['supplier_name'], suppliers_df['canonical_name'])))
    contracts_df['canonical_name'] = contracts_df['supplier'].map(supplier_mapping).fillna(contracts_df['supplier'])
    
    canonical_names = ['Tutti'] + sorted(contracts_df['canonical_name'].dropna().unique().tolist())
    selected_canonical = st.selectbox("🏢 Fornitore (Canonical)", canonical_names)

with col_f3:
    domains_list = ['Tutti'] + sorted(contracts_df['contract_domain'].dropna().unique().tolist())
    selected_domain = st.selectbox("🏷️ Dominio", domains_list)

with col_f4:
    status_list = ['Tutti', 'Attivo', 'In scadenza', 'Scaduto']
    selected_status = st.selectbox("📊 Status", status_list)

with col_f5:
    show_all_versions = st.checkbox("🔄 Mostra tutte le versioni", value=False)

search_text = st.text_input("🔎 Ricerca full-text", placeholder="Cerca in oggetto, termini, clausole...")

st.markdown("---")

# Applicazione filtri
filtered_df = contracts_df.copy()

if search_contract:
    filtered_df = filtered_df[filtered_df['contract_id'].astype(str).str.contains(search_contract, na=False)]

if selected_canonical != 'Tutti':
    filtered_df = filtered_df[filtered_df['canonical_name'] == selected_canonical]

if selected_domain != 'Tutti':
    filtered_df = filtered_df[filtered_df['contract_domain'] == selected_domain]

if selected_status != 'Tutti':
    filtered_df = filtered_df[filtered_df['status'] == selected_status]

if search_text:
    search_text_lower = search_text.lower()
    filtered_df = filtered_df[
        filtered_df['contract_subject'].astype(str).str.lower().str.contains(search_text_lower, na=False) |
        filtered_df['payment_terms'].astype(str).str.lower().str.contains(search_text_lower, na=False) |
        filtered_df['penalties'].astype(str).str.lower().str.contains(search_text_lower, na=False)
    ]

if not show_all_versions:
    filtered_df = filtered_df.sort_values('version', ascending=False).groupby('contract_id').first().reset_index()

# Tabella contratti
st.subheader(f"📋 Contratti ({len(filtered_df)} risultati)")

display_df = filtered_df.copy()
display_df['start_date_fmt'] = display_df['start_date'].dt.strftime('%d/%m/%Y')
display_df['end_date_fmt'] = display_df['end_date'].dt.strftime('%d/%m/%Y')
display_df['total_amount_fmt'] = display_df['total_amount'].apply(lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A")

status_emoji = {'Attivo': '🟢', 'In scadenza': '🟡', 'Scaduto': '🔴'}
display_df['status_badge'] = display_df['status'].apply(lambda x: f"{status_emoji.get(x, '')} {x}")

columns_to_show = ['contract_id', 'version', 'supplier', 'contract_domain', 'contract_subject', 
                   'start_date_fmt', 'end_date_fmt', 'total_amount_fmt', 'number_of_items', 'status_badge']

st.dataframe(
    display_df[columns_to_show],
    column_config={
        "contract_id": "Contract ID",
        "version": st.column_config.NumberColumn("Ver.", format="%d"),
        "supplier": "Fornitore",
        "contract_domain": "Dominio",
        "contract_subject": st.column_config.TextColumn("Oggetto", width="large"),
        "start_date_fmt": "Data Inizio",
        "end_date_fmt": "Data Fine",
        "total_amount_fmt": "Valore Totale",
        "number_of_items": st.column_config.NumberColumn("N° Items", format="%d"),
        "status_badge": "Status"
    },
    hide_index=True,
    use_container_width=True,
    height=400
)

st.markdown("---")

# Dettaglio Contratto
st.subheader("📄 Dettaglio Contratto")

contract_ids = filtered_df['contract_id'].unique().tolist()
if len(contract_ids) > 0:
    selected_contract_id = st.selectbox(
        "Seleziona un contratto da analizzare:",
        contract_ids,
        format_func=lambda x: f"{x} - {filtered_df[filtered_df['contract_id']==x].iloc[0]['supplier']}"
    )
    
    contract_versions = contracts_df[contracts_df['contract_id'] == selected_contract_id].sort_values('version', ascending=False)
    
    col_ver1, col_ver2 = st.columns([3, 1])
    
    with col_ver1:
        if len(contract_versions) > 1:
            st.info(f"ℹ️ Questo contratto ha **{len(contract_versions)} versioni** disponibili")
    
    with col_ver2:
        versions_list = contract_versions['version'].tolist()
        selected_version = st.selectbox(
            "Versione:",
            versions_list,
            format_func=lambda x: f"v{x}" + (" (latest)" if x == max(versions_list) else "")
        )
    
    if selected_version != max(versions_list):
        st.warning(f"⚠️ Stai visualizzando la versione {selected_version} (non corrente)")
    
    selected_contract = contract_versions[contract_versions['version'] == selected_version].iloc[0]
    
    st.markdown("### 📋 Informazioni Generali")
    
    col_h1, col_h2, col_h3 = st.columns(3)
    
    with col_h1:
        st.metric("Contract ID", selected_contract['contract_id'])
        st.metric("Versione", f"v{selected_contract['version']}")
    
    with col_h2:
        st.metric("Fornitore", selected_contract['supplier'])
        st.metric("Cliente", selected_contract['client'])
    
    with col_h3:
        st.metric("Dominio", selected_contract['contract_domain'])
        status_emoji_map = {'Attivo': '🟢', 'In scadenza': '🟡', 'Scaduto': '🔴'}
        st.metric("Status", f"{status_emoji_map.get(selected_contract['status'], '')} {selected_contract['status']}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Overview", "💰 Termini Economici", "📦 Items", "📄 Storico Versioni"])
    
    with tab1:
        st.markdown("#### Oggetto del Contratto")
        st.info(selected_contract['contract_subject'])
        
        col_ov1, col_ov2 = st.columns(2)
        
        with col_ov1:
            st.markdown("#### 📅 Date")
            st.write(f"**Inizio:** {selected_contract['start_date'].strftime('%d/%m/%Y') if pd.notna(selected_contract['start_date']) else 'N/A'}")
            st.write(f"**Fine:** {selected_contract['end_date'].strftime('%d/%m/%Y') if pd.notna(selected_contract['end_date']) else 'N/A'}")
            
            if pd.notna(selected_contract['start_date']) and pd.notna(selected_contract['end_date']):
                duration = (selected_contract['end_date'] - selected_contract['start_date']).days
                st.write(f"**Durata:** {duration} giorni (~{duration/365:.1f} anni)")
        
        with col_ov2:
            st.markdown("#### 💰 Valore")
            st.write(f"**Totale:** €{selected_contract['total_amount']:,.2f}" if pd.notna(selected_contract['total_amount']) else "N/A")
            st.write(f"**Items:** {selected_contract['number_of_items']}")
            st.write(f"**HW:** {selected_contract['hw_items']} | **SW:** {selected_contract['sw_items']} | **Service:** {selected_contract['service_items']}")
        
        st.markdown("#### 🏷️ Terminology Mapping")
        if pd.notna(selected_contract['terminology_mapping']):
            try:
                import json
                terminology = json.loads(selected_contract['terminology_mapping'].replace("'", '"'))
                for key, value in terminology.items():
                    st.markdown(f"**{key}:** {value}")
            except:
                st.text(selected_contract['terminology_mapping'])
        else:
            st.write("Nessun mapping disponibile")
        
        st.markdown("#### 🔍 Expected Patterns")
        if pd.notna(selected_contract['expected_patterns']):
            patterns = selected_contract['expected_patterns'].split('|')
            cols = st.columns(len(patterns))
            for i, pattern in enumerate(patterns):
                with cols[i]:
                    st.info(pattern)
        else:
            st.write("Nessun pattern specificato")
    
    with tab2:
        st.markdown("#### 💳 Payment Terms")
        st.text_area("Payment Terms", value=selected_contract['payment_terms'] if pd.notna(selected_contract['payment_terms']) else "Non specificato", height=150, disabled=True, label_visibility="collapsed")
        
        st.markdown("#### ⚠️ Penalties")
        st.text_area("Penalties", value=selected_contract['penalties'] if pd.notna(selected_contract['penalties']) else "Non specificate", height=150, disabled=True, key="penalties", label_visibility="collapsed")

        st.markdown("#### 📋 Ending Clauses")
        st.text_area("Ending Clauses", value=selected_contract['ending_clauses'] if pd.notna(selected_contract['ending_clauses']) else "Non specificate", height=200, disabled=True, key="clauses", label_visibility="collapsed")
        
    with tab3:
        st.markdown("#### 📦 Items del Contratto")
        
        contract_items = items_df[items_df['contract_id'] == selected_contract['contract_id']].copy()
        
        if len(contract_items) > 0:
            col_g1, col_g2 = st.columns([2, 2])
            
            with col_g1:
                group_by = st.selectbox("Raggruppa per:", ["Nessuno", "Item Type", "Classificazione L1", "Bundle"])
            
            with col_g2:
                st.metric("Totale Items", len(contract_items))
                st.metric("Valore Totale Items", f"€{contract_items['total_price'].sum():,.2f}")
            
            if group_by != "Nessuno":
                if group_by == "Item Type":
                    grouped = contract_items.groupby('item_type').agg({
                        'total_price': 'sum',
                        'item_id': 'count'
                    }).reset_index()
                    grouped.columns = ['Tipo', 'Valore Totale', 'N° Items']
                    st.dataframe(grouped, hide_index=True)
                    st.markdown("---")
            
            st.markdown("##### Dettaglio Items")
            
            display_items = contract_items.copy()
            
            type_emoji = {'HARDWARE': '🔵', 'SOFTWARE': '🟣', 'SERVICE': '🟠'}
            display_items['type_badge'] = display_items['item_type'].apply(
                lambda x: f"{type_emoji.get(x, '')} {x}" if pd.notna(x) else "N/A"
            )
            
            display_items['unit_price_fmt'] = display_items['unit_price'].apply(
                lambda x: f"€{x:,.2f}" if pd.notna(x) and x > 0 else "N/A"
            )
            display_items['total_price_fmt'] = display_items['total_price'].apply(
                lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A"
            )
            
            st.dataframe(
                display_items[['item_description', 'type_badge', 'classification_label', 
                             'quantity', 'unit_price_fmt', 'total_price_fmt', 
                             'is_multi_year', 'duration_years']],
                column_config={
                    "item_description": st.column_config.TextColumn("Descrizione", width="large"),
                    "type_badge": "Tipo",
                    "classification_label": "Classificazione",
                    "quantity": st.column_config.NumberColumn("Qtà", format="%d"),
                    "unit_price_fmt": "Prezzo Unit.",
                    "total_price_fmt": "Totale",
                    "is_multi_year": st.column_config.CheckboxColumn("Multi-Year"),
                    "duration_years": st.column_config.NumberColumn("Anni", format="%d")
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
            
            if st.button("📥 Esporta Items di questo contratto (Excel)"):
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    contract_items.to_excel(writer, sheet_name='Items', index=False)
                
                st.download_button(
                    label="⬇️ Download",
                    data=output.getvalue(),
                    file_name=f"items_contract_{selected_contract_id}_v{selected_version}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("⚠️ Nessun item trovato per questo contratto")
    
    with tab4:
        st.markdown("#### 📄 Timeline Versioni")
        
        if len(contract_versions) > 1:
            for idx, row in contract_versions.iterrows():
                col_t1, col_t2, col_t3 = st.columns([1, 3, 2])
                
                with col_t1:
                    if row['version'] == max(versions_list):
                        st.success(f"**v{row['version']}**")
                        st.caption("(latest)")
                    else:
                        st.info(f"**v{row['version']}**")
                
                with col_t2:
                    st.write(f"**Data:** {row['start_date'].strftime('%d/%m/%Y') if pd.notna(row['start_date']) else 'N/A'}")
                    st.write(f"**Offer ID:** {row['offer_id']}")
                
                with col_t3:
                    st.metric("Valore", f"€{row['total_amount']:,.2f}" if pd.notna(row['total_amount']) else "N/A")
                    st.metric("Items", row['number_of_items'])
                
                st.markdown("---")
            
            st.markdown("#### 🔍 Comparatore Versioni")
            
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                version_a = st.selectbox("Versione A", versions_list, index=0, key="ver_a")
            
            with col_c2:
                version_b = st.selectbox("Versione B", versions_list, index=min(1, len(versions_list)-1), key="ver_b")
            
            if version_a != version_b:
                contract_a = contract_versions[contract_versions['version'] == version_a].iloc[0]
                contract_b = contract_versions[contract_versions['version'] == version_b].iloc[0]
                
                st.markdown("##### Confronto")
                
                comparison_data = {
                    'Campo': ['Valore Totale', 'N° Items', 'HW Items', 'SW Items', 'Service Items', 'Data Fine'],
                    f'v{version_a}': [
                        f"€{contract_a['total_amount']:,.2f}" if pd.notna(contract_a['total_amount']) else "N/A",
                        contract_a['number_of_items'],
                        contract_a['hw_items'],
                        contract_a['sw_items'],
                        contract_a['service_items'],
                        contract_a['end_date'].strftime('%d/%m/%Y') if pd.notna(contract_a['end_date']) else "N/A"
                    ],
                    f'v{version_b}': [
                        f"€{contract_b['total_amount']:,.2f}" if pd.notna(contract_b['total_amount']) else "N/A",
                        contract_b['number_of_items'],
                        contract_b['hw_items'],
                        contract_b['sw_items'],
                        contract_b['service_items'],
                        contract_b['end_date'].strftime('%d/%m/%Y') if pd.notna(contract_b['end_date']) else "N/A"
                    ]
                }
                
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, hide_index=True, use_container_width=True)
                
                items_a = items_df[items_df['contract_id'] == contract_a['contract_id']]
                items_b = items_df[items_df['contract_id'] == contract_b['contract_id']]
                
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    st.markdown(f"**Items in v{version_a}:** {len(items_a)}")
                    if len(items_a) > 0:
                        with st.expander("Vedi lista"):
                            st.dataframe(items_a[['item_description', 'total_price']], hide_index=True)
                
                with col_d2:
                    st.markdown(f"**Items in v{version_b}:** {len(items_b)}")
                    if len(items_b) > 0:
                        with st.expander("Vedi lista"):
                            st.dataframe(items_b[['item_description', 'total_price']], hide_index=True)
            
        else:
            st.info("ℹ️ Questo contratto ha una sola versione")

else:
    st.warning("⚠️ Nessun contratto trovato con i filtri applicati")

st.markdown("---")
st.caption("Pagina Contratti - Contract Management Dashboard")