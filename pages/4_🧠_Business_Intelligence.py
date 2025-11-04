import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
from dashboard_utils import get_analyzer

st.set_page_config(page_title="Business Intelligence", page_icon="🧠", layout="wide")

# Configurazioni colori
ITEM_TYPE_COLORS = {
    'HARDWARE': '#3498db',
    'SOFTWARE': '#9b59b6',
    'SERVICE': '#e67e22'
}

CONFIDENCE_COLORS = {
    'HIGH': '#2ecc71',
    'MEDIUM': '#f39c12',
    'LOW': '#e74c3c'
}

DOMAIN_COLORS = {
    'networking': '#3498db',
    'IT': '#2ecc71',
    'sicurezza': '#e74c3c',
    'telecomunicazioni': '#f39c12'
}

# Directory base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'

# Caricamento dati
@st.cache_data
def load_data():
    contracts = pd.read_csv(DATA_DIR / 'contracts.csv')
    items = pd.read_csv(DATA_DIR / 'items.csv')
    suppliers = pd.read_csv(DATA_DIR / 'suppliers.csv')
    
    # Conversione date per contratti
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
    
    return contracts, items, suppliers

contracts_df, items_df, suppliers_df = load_data()

# Caricamento validazioni per items
VALIDATION_FILE = BASE_DIR / 'validated_items.json'

def load_validations():
    if VALIDATION_FILE.exists():
        with open(VALIDATION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_validation(item_id, validation_data):
    validations = load_validations()
    validations[str(item_id)] = validation_data
    with open(VALIDATION_FILE, 'w') as f:
        json.dump(validations, f, indent=2)

validations = load_validations()

# Calcolo statistiche fornitori
@st.cache_data
def calculate_supplier_stats(suppliers_df, contracts_df):
    stats = []
    
    for idx, supplier in suppliers_df.iterrows():
        supplier_id_num = str(supplier['id']).replace('supplier_', '')
        
        supplier_contracts = contracts_df[contracts_df['supplier_id'].astype(str) == supplier_id_num]
        
        if len(supplier_contracts) == 0:
            supplier_contracts = contracts_df[contracts_df['supplier'] == supplier['display_name']]
        
        if len(supplier_contracts) == 0:
            supplier_contracts = contracts_df[contracts_df['supplier'] == supplier['canonical_name']]
        
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

def get_contract_items(contract_id, items_df):
    """
    Trova gli items associati a un contratto usando diverse strategie di matching
    """
    
    # Strategia 1: Match diretto con contract_id completo
    contract_items = items_df[items_df['contract_number'].astype(str) == str(contract_id)]
    
    if len(contract_items) == 0:
        # Strategia 2: Match con le ultime cifre del contract_id
        try:
            # Prova con le ultime 2 cifre
            last_2_digits = str(contract_id)[-2:]
            contract_items = items_df[items_df['contract_number'].astype(str) == last_2_digits]
        except:
            pass
    
    if len(contract_items) == 0:
        # Strategia 3: Match con le ultime 3 cifre
        try:
            last_3_digits = str(contract_id)[-3:]
            contract_items = items_df[items_df['contract_number'].astype(str) == last_3_digits]
        except:
            pass
    
    if len(contract_items) == 0:
        # Strategia 4: Match parziale (contract_id contiene contract_number)
        contract_items = items_df[items_df['contract_number'].apply(
            lambda x: str(x) in str(contract_id) if pd.notna(x) else False
        )]
    
    if len(contract_items) == 0:
        # Strategia 5: Match inverso (contract_number contiene parte di contract_id)
        contract_items = items_df[items_df['contract_number'].apply(
            lambda x: str(contract_id)[-4:] in str(x) if pd.notna(x) else False
        )]
    
    return contract_items

supplier_stats = calculate_supplier_stats(suppliers_df, contracts_df)

# Header
st.title("🧠 Business Intelligence")
st.markdown("Analisi integrata di contratti, items e fornitori per insights strategici")
st.markdown("---")

# Main tabs
tab_contracts, tab_items, tab_suppliers = st.tabs(["📋 Contratti", "📦 Items", "🏢 Suppliers"])

# ==================== TAB CONTRATTI ====================
with tab_contracts:
    st.header("📋 Gestione Contratti")
    st.markdown("Esplora i contratti, naviga tra le versioni e analizza gli items associati")
    
    # Filtri contratti
    st.subheader("🔍 Filtri")
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)

    with col_f1:
        search_contract = st.text_input("🔢 Numero Contratto", placeholder="Es: 7010148320", key="contract_search")

    with col_f2:
        # Create supplier mapping avoiding duplicate keys
        supplier_mapping = {}
        for _, row in suppliers_df.iterrows():
            if pd.notna(row['display_name']) and row['display_name'] not in supplier_mapping:
                supplier_mapping[row['display_name']] = row['canonical_name']
            if pd.notna(row['supplier_name']) and row['supplier_name'] not in supplier_mapping:
                supplier_mapping[row['supplier_name']] = row['canonical_name']
        
        contracts_df['canonical_name'] = contracts_df['supplier'].map(supplier_mapping).fillna(contracts_df['supplier'])
        
        canonical_names = ['Tutti'] + sorted(contracts_df['canonical_name'].dropna().unique().tolist())
        selected_canonical = st.selectbox("🏢 Fornitore (Canonical)", canonical_names, key="contract_supplier")

    with col_f3:
        domains_list = ['Tutti'] + sorted(contracts_df['contract_domain'].dropna().unique().tolist())
        selected_domain = st.selectbox("🏷️ Dominio", domains_list, key="contract_domain")

    with col_f4:
        status_list = ['Tutti', 'Attivo', 'In scadenza', 'Scaduto']
        selected_status = st.selectbox("📊 Status", status_list, key="contract_status")

    with col_f5:
        show_all_versions = st.checkbox("🔄 Mostra tutte le versioni", value=False, key="contract_versions")

    search_text = st.text_input("🔎 Ricerca full-text", placeholder="Cerca in oggetto, termini, clausole...", key="contract_fulltext")

    # Applicazione filtri contratti
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
        height=400,
        key="contracts_table"
    )

    # Dettaglio Contratto
    st.subheader("📄 Dettaglio Contratto")

    contract_ids = filtered_df['contract_id'].unique().tolist()
    if len(contract_ids) > 0:
        selected_contract_id = st.selectbox(
            "Seleziona un contratto da analizzare:",
            contract_ids,
            format_func=lambda x: f"{x} - {filtered_df[filtered_df['contract_id']==x].iloc[0]['supplier']}",
            key="contract_detail_select"
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
                format_func=lambda x: f"v{x}" + (" (latest)" if x == max(versions_list) else ""),
                key="contract_version_select"
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
                    terminology = json.loads(selected_contract['terminology_mapping'])
                    if terminology:
                        for key, value in terminology.items():
                            st.write(f"- **{key}:** {value}")
                    else:
                        st.write("Nessun mapping disponibile")
                except (json.JSONDecodeError, TypeError):
                    st.write("Formato mapping non valido")
            else:
                st.write("Nessun mapping disponibile")
        
        with tab2:
            st.markdown("#### 💰 Termini di Pagamento")
            if pd.notna(selected_contract['payment_terms']):
                st.info(selected_contract['payment_terms'])
            else:
                st.write("Non specificati")
            
            st.markdown("#### ⚖️ Penali")
            if pd.notna(selected_contract['penalties']):
                st.warning(selected_contract['penalties'])
            else:
                st.write("Non specificate")
            
            st.markdown("#### 📋 Clausole di Chiusura")
            if pd.notna(selected_contract['ending_clauses']):
                st.write(selected_contract['ending_clauses'])
            else:
                st.write("Nessuna clausola di chiusura")
        
        with tab3:
            st.markdown("#### 📦 Items del Contratto")
            
            contract_items = get_contract_items(selected_contract['contract_id'], items_df)
            
            if len(contract_items) > 0:
                # Statistiche Items
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                
                with col_stat1:
                    hw_count = len(contract_items[contract_items['item_type'] == 'HARDWARE'])
                    st.metric("🔵 Hardware", hw_count)
                
                with col_stat2:
                    sw_count = len(contract_items[contract_items['item_type'] == 'SOFTWARE'])
                    st.metric("🟣 Software", sw_count)
                
                with col_stat3:
                    service_count = len(contract_items[contract_items['item_type'] == 'SERVICE'])
                    st.metric("🟠 Service", service_count)
                
                with col_stat4:
                    total_value_items = contract_items['total_price'].sum()
                    st.metric("💰 Valore Items", f"€{total_value_items:,.2f}")
                
                # Tabella Items
                display_items = contract_items[['item_id', 'item_description', 'item_type', 'unit_price', 'quantity', 'total_price']].copy()
                display_items['unit_price_fmt'] = display_items['unit_price'].apply(lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A")
                display_items['total_price_fmt'] = display_items['total_price'].apply(lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A")
                
                st.dataframe(
                    display_items[['item_id', 'item_description', 'item_type', 'unit_price_fmt', 'quantity', 'total_price_fmt']],
                    column_config={
                        "item_id": "ID",
                        "item_description": st.column_config.TextColumn("Descrizione", width="large"),
                        "item_type": "Tipo",
                        "unit_price_fmt": "Prezzo Unitario",
                        "quantity": st.column_config.NumberColumn("Quantità"),
                        "total_price_fmt": "Totale"
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="contract_items_table"
                )
            else:
                st.info("Nessun item trovato per questo contratto")
        
        with tab4:
            st.markdown("#### 📄 Storico delle Versioni")
            
            versions_display = contract_versions[['version', 'start_date', 'end_date', 'total_amount']].copy()
            versions_display['start_date_fmt'] = versions_display['start_date'].dt.strftime('%d/%m/%Y')
            versions_display['end_date_fmt'] = versions_display['end_date'].dt.strftime('%d/%m/%Y') 
            versions_display['total_amount_fmt'] = versions_display['total_amount'].apply(lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A")
            versions_display['is_current'] = versions_display['version'] == max(versions_list)
            
            st.dataframe(
                versions_display[['version', 'start_date_fmt', 'end_date_fmt', 'total_amount_fmt', 'is_current']],
                column_config={
                    "version": st.column_config.NumberColumn("Versione", format="v%d"),
                    "start_date_fmt": "Data Inizio",
                    "end_date_fmt": "Data Fine", 
                    "total_amount_fmt": "Valore",
                    "is_current": st.column_config.CheckboxColumn("Corrente")
                },
                hide_index=True,
                use_container_width=True,
                key="contract_versions_table"
            )
            
            if len(contract_versions) > 1:
                st.markdown("##### 📈 Evoluzione del Valore")
                versions_chart = contract_versions.sort_values('version')
                fig_versions = px.line(
                    versions_chart,
                    x='version',
                    y='total_amount',
                    markers=True,
                    labels={'version': 'Versione', 'total_amount': 'Valore (€)'}
                )
                st.plotly_chart(fig_versions, use_container_width=True, key="contract_versions_chart")

# ==================== TAB ITEMS ====================
with tab_items:
    st.header("📦 Gestione Items")
    st.markdown("Esplora gli items, verifica le classificazioni e valida manualmente i risultati")
    
    # Filtri Items
    st.subheader("🔍 Filtri")
    col_i1, col_i2, col_i3, col_i4 = st.columns(4)

    with col_i1:
        type_filter = st.selectbox("🏷️ Tipo Item", ['Tutti', 'HARDWARE', 'SOFTWARE', 'SERVICE'], key="items_type")

    with col_i2:
        confidence_filter = st.selectbox("📊 Confidence Level", ['Tutti', 'HIGH', 'MEDIUM', 'LOW'], key="items_confidence")

    with col_i3:
        l1_options = ['Tutti'] + sorted(items_df['class_l1'].dropna().unique().tolist())
        l1_filter = st.selectbox("🎯 Classe L1", l1_options, key="items_l1")

    with col_i4:
        validated_filter = st.selectbox("✅ Stato Validazione", ['Tutti', 'Validati', 'Non Validati'], key="items_validated")

    search_item = st.text_input("🔎 Cerca Item", placeholder="Cerca nella descrizione...", key="items_search")

    # Applicazione filtri items
    filtered_items = items_df.copy()

    # Aggiungi colonna validated
    filtered_items['validated'] = filtered_items['item_id'].apply(lambda x: str(x) in validations)

    if type_filter != 'Tutti':
        filtered_items = filtered_items[filtered_items['item_type'] == type_filter]

    if confidence_filter != 'Tutti':
        filtered_items = filtered_items[filtered_items['class_confidence_level'] == confidence_filter]

    if l1_filter != 'Tutti':
        filtered_items = filtered_items[filtered_items['class_l1'] == l1_filter]

    if validated_filter == 'Validati':
        filtered_items = filtered_items[filtered_items['validated'] == True]
    elif validated_filter == 'Non Validati':
        filtered_items = filtered_items[filtered_items['validated'] == False]

    if search_item:
        filtered_items = filtered_items[
            filtered_items['item_description'].astype(str).str.lower().str.contains(search_item.lower(), na=False)
        ]

    # Statistiche items
    st.subheader(f"📊 Statistiche Items ({len(filtered_items)} risultati)")

    items_display = filtered_items.copy()

    col_q1, col_q2, col_q3 = st.columns(3)

    with col_q1:
        low_conf_count = len(items_display[items_display['class_confidence_level'] == 'LOW'])
        st.metric("⚠️ Low Confidence", low_conf_count)

    with col_q2:
        no_classification = len(items_display[items_display['classification_label'].isna()])
        st.metric("❌ Senza Classificazione", no_classification)

    with col_q3:
        validated_count = len(items_display[items_display['validated'] == True])
        st.metric("✅ Validati", validated_count)

    if low_conf_count > 0:
        with st.expander("📋 Items con Low Confidence da Validare"):
            low_conf_items = items_display[items_display['class_confidence_level'] == 'LOW']
            st.dataframe(
                low_conf_items[['item_description', 'classification_label', 'class_final_score', 'validated']],
                hide_index=True,
                use_container_width=True,
                key="items_low_conf_table"
            )

    # Sistema di Validazione
    st.subheader("✏️ Sistema di Validazione Manuale")

    st.info("💡 Seleziona un item dalla tabella sottostante per correggere la classificazione")

    st.markdown("##### 📋 Tabella Completa Items")

    display_data = filtered_items.copy()

    type_emoji = {'HARDWARE': '🔵', 'SOFTWARE': '🟣', 'SERVICE': '🟠'}
    display_data['type_badge'] = display_data['item_type'].apply(
        lambda x: f"{type_emoji.get(x, '')} {x}" if pd.notna(x) else "N/A"
    )

    conf_emoji = {'HIGH': '🟢', 'MEDIUM': '🟡', 'LOW': '🔴'}
    display_data['conf_badge'] = display_data['class_confidence_level'].apply(
        lambda x: f"{conf_emoji.get(x, '')} {x}" if pd.notna(x) else "N/A"
    )

    display_data['validated_badge'] = display_data['validated'].apply(
        lambda x: "✅ Si" if x else "⏳ No"
    )

    display_data['total_price_fmt'] = display_data['total_price'].apply(
        lambda x: f"€{x:,.2f}" if pd.notna(x) else "N/A"
    )

    st.dataframe(
        display_data[['item_id', 'item_description', 'type_badge', 'classification_label', 
                      'conf_badge', 'total_price_fmt', 'validated_badge']],
        column_config={
            "item_id": "ID",
            "item_description": st.column_config.TextColumn("Descrizione", width="large"),
            "type_badge": "Tipo",
            "classification_label": "Classificazione",
            "conf_badge": "Confidence",
            "total_price_fmt": "Prezzo",
            "validated_badge": "Validato"
        },
        hide_index=True,
        use_container_width=True,
        height=400,
        key="items_full_table"
    )

    st.markdown("##### ✏️ Form di Validazione")

    col_form1, col_form2 = st.columns([2, 1])

    with col_form1:
        item_to_validate = st.selectbox(
            "Seleziona Item da Validare",
            filtered_items['item_id'].tolist(),
            format_func=lambda x: f"{x} - {filtered_items[filtered_items['item_id']==x].iloc[0]['item_description'][:50]}...",
            key="items_validate_select"
        )

    with col_form2:
        st.write("")
        st.write("")
        if st.button("🔄 Reset Validazione", use_container_width=True, key="items_reset_validation"):
            if str(item_to_validate) in validations:
                del validations[str(item_to_validate)]
                with open(VALIDATION_FILE, 'w') as f:
                    json.dump(validations, f, indent=2)
                st.success("✅ Validazione resettata!")
                st.rerun()

    if item_to_validate:
        selected_item = filtered_items[filtered_items['item_id'] == item_to_validate].iloc[0]
        
        st.markdown("**🔍 Item Selezionato:**")
        st.info(f"{selected_item['item_description']}")
        
        col_curr1, col_curr2, col_curr3 = st.columns(3)
        
        with col_curr1:
            st.write(f"**Tipo Attuale:** {selected_item['item_type']}")
        with col_curr2:
            st.write(f"**Class Attuale:** {selected_item['classification_label']}")
        with col_curr3:
            st.write(f"**Confidence:** {selected_item['class_confidence_level']} ({selected_item['class_final_score']:.2f})")
        
        with st.form("items_validation_form"):
            st.markdown("**🔧 Correzioni:**")
            
            col_val1, col_val2 = st.columns(2)
            
            with col_val1:
                new_type = st.selectbox(
                    "Tipo Corretto",
                    ['HARDWARE', 'SOFTWARE', 'SERVICE'],
                    index=['HARDWARE', 'SOFTWARE', 'SERVICE'].index(selected_item['item_type']) if pd.notna(selected_item['item_type']) else 0,
                    key="items_new_type"
                )
                
                l1_options = items_df['class_l1'].dropna().unique().tolist()
                current_l1_idx = l1_options.index(selected_item['class_l1']) if pd.notna(selected_item['class_l1']) and selected_item['class_l1'] in l1_options else 0
                new_l1 = st.selectbox("Classe L1", l1_options, index=current_l1_idx, key="items_new_l1")
            
            with col_val2:
                l2_options = items_df['class_l2'].dropna().unique().tolist()
                current_l2_idx = l2_options.index(selected_item['class_l2']) if pd.notna(selected_item['class_l2']) and selected_item['class_l2'] in l2_options else 0
                new_l2 = st.selectbox("Classe L2", l2_options, index=current_l2_idx, key="items_new_l2")
                
                l3_options = items_df['class_l3'].dropna().unique().tolist()
                current_l3_idx = l3_options.index(selected_item['class_l3']) if pd.notna(selected_item['class_l3']) and selected_item['class_l3'] in l3_options else 0
                new_l3 = st.selectbox("Classe L3", l3_options, index=current_l3_idx, key="items_new_l3")
            
            notes = st.text_area("Note", placeholder="Aggiungi note sulla correzione...", key="items_validation_notes")
            
            submitted = st.form_submit_button("💾 Salva Validazione", use_container_width=True)
            
            if submitted:
                validation_data = {
                    'original_classification': selected_item['classification_label'],
                    'corrected_classification': f"{new_l1}/{new_l2}/{new_l3}",
                    'corrected_type': new_type,
                    'corrected_by': "user",
                    'corrected_at': datetime.now().isoformat(),
                    'notes': notes
                }
                
                save_validation(item_to_validate, validation_data)
                st.success("✅ Validazione salvata con successo!")
                st.rerun()

    # Export
    st.subheader("📤 Export Dati")

    col_exp1, col_exp2 = st.columns([3, 1])

    with col_exp1:
        st.info("💾 Esporta gli items filtrati con le validazioni applicate")

    with col_exp2:
        if st.button("📥 Download Excel", use_container_width=True, key="items_export"):
            from io import BytesIO
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                filtered_items.to_excel(writer, sheet_name='Items', index=False)
                
                if len(validations) > 0:
                    val_df = pd.DataFrame.from_dict(validations, orient='index')
                    val_df.to_excel(writer, sheet_name='Validazioni')
            
            st.download_button(
                label="⬇️ Scarica",
                data=output.getvalue(),
                file_name=f"items_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="items_download"
            )

# ==================== TAB SUPPLIERS ====================
with tab_suppliers:
    st.header("🏢 Gestione Fornitori")
    st.markdown("Analizza i fornitori, esplora le specializzazioni e visualizza la distribuzione geografica")
    
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
        avg_contracts = supplier_stats['n_contracts'].mean()
        st.metric("📋 Avg Contratti", f"{avg_contracts:.1f}")

    # Filtri Fornitori
    st.subheader("🔍 Filtri")
    col_s1, col_s2, col_s3 = st.columns(3)

    with col_s1:
        specializations = ['Tutti'] + sorted(suppliers_df['specialization'].dropna().unique().tolist())
        spec_filter = st.selectbox("🎯 Specializzazione", specializations, key="suppliers_specialization")

    with col_s2:
        min_value = st.number_input("💰 Valore Minimo (€)", min_value=0, value=0, step=1000, key="suppliers_min_value")

    with col_s3:
        min_contracts = st.number_input("📋 Min Contratti", min_value=0, value=0, step=1, key="suppliers_min_contracts")

    search_supplier = st.text_input("🔎 Cerca Fornitore", placeholder="Nome, slug, indirizzo...", key="suppliers_search")

    # Applicazione filtri fornitori
    filtered_suppliers = supplier_stats.copy()

    if spec_filter != 'Tutti':
        filtered_suppliers = filtered_suppliers[filtered_suppliers['specialization'] == spec_filter]

    if min_value > 0:
        filtered_suppliers = filtered_suppliers[filtered_suppliers['total_value'] >= min_value]

    if min_contracts > 0:
        filtered_suppliers = filtered_suppliers[filtered_suppliers['n_contracts'] >= min_contracts]

    if search_supplier:
        search_lower = search_supplier.lower()
        filtered_suppliers = filtered_suppliers[
            filtered_suppliers['display_name'].astype(str).str.lower().str.contains(search_lower, na=False) |
            filtered_suppliers['supplier_slug'].astype(str).str.lower().str.contains(search_lower, na=False) |
            filtered_suppliers['address'].astype(str).str.lower().str.contains(search_lower, na=False)
        ]

    st.subheader(f"🏢 Fornitori ({len(filtered_suppliers)} risultati)")

    if len(filtered_suppliers) > 0:
        # Visualizzazioni
        col_viz1, col_viz2 = st.columns(2)

        with col_viz1:
            # Top 10 per valore
            st.markdown("##### 💰 Top 10 per Valore")
            top_10_value = filtered_suppliers.nlargest(10, 'total_value')
            fig_top_value = px.bar(
                top_10_value,
                x='total_value',
                y='display_name',
                orientation='h',
                labels={'total_value': 'Valore Totale (€)', 'display_name': ''},
                color='total_value',
                color_continuous_scale='Blues'
            )
            fig_top_value.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_top_value, use_container_width=True, key="suppliers_top_value")

        with col_viz2:
            # Distribuzione per specializzazione
            st.markdown("##### 🎯 Distribuzione Specializzazioni")
            spec_dist = filtered_suppliers['specialization'].value_counts()
            if len(spec_dist) > 0:
                fig_spec = px.pie(
                    values=spec_dist.values,
                    names=spec_dist.index,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig_spec, use_container_width=True, key="suppliers_specialization_dist")

        # Tabella fornitori
        display_suppliers = filtered_suppliers.copy()
        display_suppliers['total_value_fmt'] = display_suppliers['total_value'].apply(lambda x: f"€{x:,.0f}")

        st.dataframe(
            display_suppliers[['display_name', 'specialization', 'total_value_fmt', 'n_contracts', 'address']],
            column_config={
                "display_name": "Nome Fornitore",
                "specialization": "Specializzazione", 
                "total_value_fmt": "Valore Totale",
                "n_contracts": st.column_config.NumberColumn("N° Contratti"),
                "address": st.column_config.TextColumn("Indirizzo", width="large")
            },
            hide_index=True,
            use_container_width=True,
            height=400,
            key="suppliers_table"
        )

        # Dettaglio Fornitore
        st.subheader("📄 Dettaglio Fornitore")

        if len(filtered_suppliers) > 0:
            # Crea un dizionario per il mapping nome -> valore per evitare lookup ripetuti
            supplier_value_map = dict(zip(filtered_suppliers['display_name'], filtered_suppliers['total_value']))
            
            selected_supplier = st.selectbox(
                "Seleziona un fornitore da analizzare:",
                list(supplier_value_map.keys()),
                format_func=lambda x: f"{x} - €{supplier_value_map[x]:,.0f}",
                key="suppliers_detail_select"
            )

            if selected_supplier:
                supplier_detail = filtered_suppliers[filtered_suppliers['display_name'] == selected_supplier].iloc[0]
            
            col_det1, col_det2, col_det3 = st.columns(3)
            
            with col_det1:
                st.metric("💰 Valore Totale", f"€{supplier_detail['total_value']:,.0f}")
                st.metric("📋 Contratti", supplier_detail['n_contracts'])
            
            with col_det2:
                st.metric("🎯 Specializzazione", supplier_detail['specialization'])
                avg_contract_value = supplier_detail['total_value'] / supplier_detail['n_contracts'] if supplier_detail['n_contracts'] > 0 else 0
                st.metric("💵 Avg per Contratto", f"€{avg_contract_value:,.0f}")
            
            with col_det3:
                st.metric("🏷️ Slug", supplier_detail['supplier_slug'])
                st.metric("📍 Indirizzo", supplier_detail['address'][:30] + "..." if len(str(supplier_detail['address'])) > 30 else supplier_detail['address'])

            # Informazioni aggiuntive dal dataset suppliers
            supplier_info = suppliers_df[suppliers_df['display_name'] == selected_supplier]
            if len(supplier_info) > 0:
                supplier_full = supplier_info.iloc[0]
                
                with st.expander("📋 Informazioni Dettagliate"):
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.markdown("##### 🏷️ Naming")
                        st.write(f"**Canonical Name:** {supplier_full['canonical_name']}")
                        st.write(f"**Supplier Name:** {supplier_full['supplier_name']}")
                        st.write(f"**Display Name:** {supplier_full['display_name']}")
                        
                        st.markdown("##### 🎯 Caratteristiche")
                        if pd.notna(supplier_full['known_technologies']):
                            st.write(f"**Tecnologie:** {supplier_full['known_technologies']}")
                        if pd.notna(supplier_full['typical_categories']):
                            st.write(f"**Categorie:** {supplier_full['typical_categories']}")
                    
                    with col_info2:
                        st.markdown("##### 🔄 Varianti Nome")
                        if pd.notna(supplier_full['name_variants']):
                            try:
                                variants = json.loads(supplier_full['name_variants'])
                                if variants:
                                    for variant in variants:
                                        st.write(f"- {variant}")
                                else:
                                    st.write("Nessuna variante disponibile")
                            except (json.JSONDecodeError, TypeError):
                                st.write("Formato varianti non valido")
                        else:
                            st.write("Nessuna variante disponibile")
                
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
                        use_container_width=True,
                        key="suppliers_contracts_detail_table"
                    )
                else:
                    st.info("Nessun contratto trovato per questo fornitore")
                
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
                    st.plotly_chart(fig_trend, use_container_width=True, key="suppliers_trend")

    else:
        st.warning("⚠️ Nessun fornitore trovato con i filtri applicati")

    # Export
    st.subheader("📤 Export Dati")

    col_exp1, col_exp2 = st.columns([3, 1])

    with col_exp1:
        st.info("💾 Esporta l'elenco completo dei fornitori con le statistiche")

    with col_exp2:
        if st.button("📥 Download Excel", use_container_width=True, key="suppliers_export"):
            from io import BytesIO
            
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                export_data = supplier_stats.merge(
                    suppliers_df[['id', 'address', 'known_technologies', 'typical_categories']],
                    on='id',
                    how='left'
                )
                export_data.to_excel(writer, sheet_name='Fornitori', index=False)
                
                contracts_export = contracts_df[['contract_id', 'supplier', 'contract_subject', 
                                                'start_date', 'end_date', 'total_amount']]
                contracts_export.to_excel(writer, sheet_name='Contratti per Fornitore', index=False)
            
            st.download_button(
                label="⬇️ Scarica",
                data=output.getvalue(),
                file_name=f"suppliers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="suppliers_download"
            )

st.markdown("---")
st.caption("Business Intelligence Dashboard - Contract Management System")