import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import login_page, logout_button

st.set_page_config(page_title="Items", page_icon="📦", layout="wide")

# pages/3_📦_Items.py
if not login_page(form_key="login_items"):
    st.stop()

logout_button()

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

# Caricamento dati
@st.cache_data
def load_data():
    items = pd.read_csv(r'CC:\code\telco-dashboard\data\items.csv')
    contracts = pd.read_csv(r'C:\code\telco-dashboard\data\contracts.csv')
    return items, contracts

items_df, contracts_df = load_data()

# Caricamento validazioni (se esistono)
VALIDATION_FILE = 'validated_items.json'

def load_validations():
    if Path(VALIDATION_FILE).exists():
        with open(VALIDATION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_validation(item_id, validation_data):
    validations = load_validations()
    validations[str(item_id)] = validation_data
    with open(VALIDATION_FILE, 'w') as f:
        json.dump(validations, f, indent=2)

# Carica validazioni esistenti
validations = load_validations()

# Applica validazioni ai dati
items_display = items_df.copy()
for item_id, val_data in validations.items():
    mask = items_display['item_id'].astype(str) == item_id
    if mask.any():
        items_display.loc[mask, 'classification_label'] = val_data.get('corrected_classification', '')
        items_display.loc[mask, 'item_type'] = val_data.get('corrected_type', '')
        items_display.loc[mask, 'validated'] = True

if 'validated' not in items_display.columns:
    items_display['validated'] = False

# Header
st.title("📦 Analisi Items")
st.markdown("Esplora gli articoli estratti dai contratti, analizza le classificazioni e valida i dati")
st.markdown("---")

# KPI Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📦 Items Totali", len(items_df))

with col2:
    hw_pct = (len(items_df[items_df['item_type'] == 'HARDWARE']) / len(items_df) * 100) if len(items_df) > 0 else 0
    st.metric("🔵 Hardware", f"{hw_pct:.1f}%")

with col3:
    sw_pct = (len(items_df[items_df['item_type'] == 'SOFTWARE']) / len(items_df) * 100) if len(items_df) > 0 else 0
    st.metric("🟣 Software", f"{sw_pct:.1f}%")

with col4:
    sv_pct = (len(items_df[items_df['item_type'] == 'SERVICE']) / len(items_df) * 100) if len(items_df) > 0 else 0
    st.metric("🟠 Service", f"{sv_pct:.1f}%")

st.markdown("---")

# Filtri avanzati
st.subheader("🔍 Filtri Avanzati")

col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    item_types = ['Tutti'] + items_df['item_type'].dropna().unique().tolist()
    selected_type = st.selectbox("Tipo Item", item_types)

with col_f2:
    l1_classes = ['Tutti'] + sorted(items_df['class_l1'].dropna().unique().tolist())
    selected_l1 = st.selectbox("Classificazione L1", l1_classes)

with col_f3:
    # Filtra L2 in base a L1 selezionato
    if selected_l1 != 'Tutti':
        l2_classes = ['Tutti'] + sorted(items_df[items_df['class_l1'] == selected_l1]['class_l2'].dropna().unique().tolist())
    else:
        l2_classes = ['Tutti'] + sorted(items_df['class_l2'].dropna().unique().tolist())
    selected_l2 = st.selectbox("Classificazione L2", l2_classes)

with col_f4:
    # Filtra L3 in base a L2 selezionato
    if selected_l2 != 'Tutti':
        l3_classes = ['Tutti'] + sorted(items_df[items_df['class_l2'] == selected_l2]['class_l3'].dropna().unique().tolist())
    elif selected_l1 != 'Tutti':
        l3_classes = ['Tutti'] + sorted(items_df[items_df['class_l1'] == selected_l1]['class_l3'].dropna().unique().tolist())
    else:
        l3_classes = ['Tutti'] + sorted(items_df['class_l3'].dropna().unique().tolist())
    selected_l3 = st.selectbox("Classificazione L3", l3_classes)

col_f5, col_f6 = st.columns([2, 2])

with col_f5:
    confidence_levels = ['Tutti', 'HIGH', 'MEDIUM', 'LOW']
    selected_confidence = st.selectbox("Confidence Level", confidence_levels)

with col_f6:
    price_range = st.slider("Range Prezzo (€)", 0, int(items_df['total_price'].max()), (0, int(items_df['total_price'].max())))

col_f7, col_f8 = st.columns([2, 2])

with col_f7:
    bundle_filter = st.radio("Bundle", ["Tutti", "Solo Bundle", "Solo Non-Bundle"], horizontal=True)

with col_f8:
    multiyear_filter = st.radio("Multi-Year", ["Tutti", "Solo Multi-Year", "Solo Single"], horizontal=True)

# Applicazione filtri
filtered_items = items_display.copy()

if selected_type != 'Tutti':
    filtered_items = filtered_items[filtered_items['item_type'] == selected_type]

if selected_l1 != 'Tutti':
    filtered_items = filtered_items[filtered_items['class_l1'] == selected_l1]

if selected_l2 != 'Tutti':
    filtered_items = filtered_items[filtered_items['class_l2'] == selected_l2]

if selected_l3 != 'Tutti':
    filtered_items = filtered_items[filtered_items['class_l3'] == selected_l3]

if selected_confidence != 'Tutti':
    filtered_items = filtered_items[filtered_items['class_confidence_level'] == selected_confidence]

filtered_items = filtered_items[
    (filtered_items['total_price'] >= price_range[0]) & 
    (filtered_items['total_price'] <= price_range[1])
]

if bundle_filter == "Solo Bundle":
    filtered_items = filtered_items[filtered_items['is_bundle'] == True]
elif bundle_filter == "Solo Non-Bundle":
    filtered_items = filtered_items[filtered_items['is_bundle'] == False]

if multiyear_filter == "Solo Multi-Year":
    filtered_items = filtered_items[filtered_items['is_multi_year'] == True]
elif multiyear_filter == "Solo Single":
    filtered_items = filtered_items[filtered_items['is_multi_year'] == False]

st.markdown("---")

# Visualizzazioni
st.subheader("📊 Visualizzazioni")

tab_viz1, tab_viz2, tab_viz3 = st.tabs(["📈 Distribuzione", "🎯 Classificazione", "💰 Analisi Prezzi"])

with tab_viz1:
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        st.markdown("##### Composizione per Tipo")
        type_dist = filtered_items['item_type'].value_counts().reset_index()
        type_dist.columns = ['item_type', 'count']
        
        fig_type = px.pie(
            type_dist,
            values='count',
            names='item_type',
            color='item_type',
            color_discrete_map=ITEM_TYPE_COLORS,
            hole=0.4
        )
        fig_type.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_type, use_container_width=True)
    
    with col_v2:
        st.markdown("##### Confidence Level")
        conf_dist = filtered_items['class_confidence_level'].value_counts().reset_index()
        conf_dist.columns = ['confidence', 'count']
        
        fig_conf = px.bar(
            conf_dist,
            x='confidence',
            y='count',
            color='confidence',
            color_discrete_map=CONFIDENCE_COLORS
        )
        fig_conf.update_layout(showlegend=False)
        st.plotly_chart(fig_conf, use_container_width=True)

with tab_viz2:
    st.markdown("##### Sunburst - Classificazione Gerarchica")
    
    # Prepara dati per sunburst
    sunburst_data = filtered_items[['class_l1', 'class_l2', 'class_l3', 'total_price']].dropna()
    
    if len(sunburst_data) > 0:
        fig_sunburst = px.sunburst(
            sunburst_data,
            path=['class_l1', 'class_l2', 'class_l3'],
            values='total_price',
            color='class_l1',
            height=600
        )
        st.plotly_chart(fig_sunburst, use_container_width=True)
    else:
        st.info("Nessun dato disponibile per la classificazione gerarchica")

with tab_viz3:
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.markdown("##### Scatter: Prezzo vs Confidence")
        scatter_data = filtered_items[['total_price', 'class_final_score', 'item_type', 'item_description']].dropna()
        
        if len(scatter_data) > 0:
            fig_scatter = px.scatter(
                scatter_data,
                x='total_price',
                y='class_final_score',
                color='item_type',
                color_discrete_map=ITEM_TYPE_COLORS,
                hover_data=['item_description'],
                labels={'total_price': 'Prezzo Totale (€)', 'class_final_score': 'Confidence Score'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col_p2:
        st.markdown("##### Box Plot: Distribuzione Prezzi per L1")
        box_data = filtered_items[['class_l1', 'total_price']].dropna()
        
        if len(box_data) > 0:
            fig_box = px.box(
                box_data,
                x='class_l1',
                y='total_price',
                color='class_l1',
                labels={'total_price': 'Prezzo Totale (€)', 'class_l1': 'Classe L1'}
            )
            fig_box.update_layout(showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)

st.markdown("---")

# Quality Check Section
st.subheader("🔍 Quality Check")

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

# Items da validare
if low_conf_count > 0:
    with st.expander("📋 Items con Low Confidence da Validare"):
        low_conf_items = items_display[items_display['class_confidence_level'] == 'LOW']
        st.dataframe(
            low_conf_items[['item_description', 'classification_label', 'class_final_score', 'validated']],
            hide_index=True,
            use_container_width=True
        )

st.markdown("---")

# Sistema di Validazione Manuale
st.subheader("✏️ Sistema di Validazione Manuale")

st.info("💡 Seleziona un item dalla tabella sottostante per correggere la classificazione")

# Tabella Items Dettagliata
st.markdown("##### 📋 Tabella Completa Items")

# Preparazione dati per visualizzazione
display_data = filtered_items.copy()

# Badge
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

# Formattazione prezzi
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
    height=400
)

# Form di validazione
st.markdown("---")
st.markdown("##### ✏️ Form di Validazione")

col_form1, col_form2 = st.columns([2, 1])

with col_form1:
    item_to_validate = st.selectbox(
        "Seleziona Item da Validare",
        filtered_items['item_id'].tolist(),
        format_func=lambda x: f"{x} - {filtered_items[filtered_items['item_id']==x].iloc[0]['item_description'][:50]}..."
    )

with col_form2:
    st.write("")
    st.write("")
    if st.button("🔄 Reset Validazione", use_container_width=True):
        if str(item_to_validate) in validations:
            del validations[str(item_to_validate)]
            with open(VALIDATION_FILE, 'w') as f:
                json.dump(validations, f, indent=2)
            st.success("✅ Validazione resettata!")
            st.rerun()

if item_to_validate:
    selected_item = filtered_items[filtered_items['item_id'] == item_to_validate].iloc[0]
    
    st.markdown("**📝 Item Selezionato:**")
    st.info(f"{selected_item['item_description']}")
    
    col_curr1, col_curr2, col_curr3 = st.columns(3)
    
    with col_curr1:
        st.write(f"**Tipo Attuale:** {selected_item['item_type']}")
    with col_curr2:
        st.write(f"**Class Attuale:** {selected_item['classification_label']}")
    with col_curr3:
        st.write(f"**Confidence:** {selected_item['class_confidence_level']} ({selected_item['class_final_score']:.2f})")
    
    st.markdown("---")
    
    with st.form("validation_form"):
        st.markdown("**🔧 Correzioni:**")
        
        col_val1, col_val2 = st.columns(2)
        
        with col_val1:
            new_type = st.selectbox(
                "Tipo Corretto",
                ['HARDWARE', 'SOFTWARE', 'SERVICE'],
                index=['HARDWARE', 'SOFTWARE', 'SERVICE'].index(selected_item['item_type']) if pd.notna(selected_item['item_type']) else 0
            )
            
            # Classificazione L1
            l1_options = items_df['class_l1'].dropna().unique().tolist()
            current_l1_idx = l1_options.index(selected_item['class_l1']) if pd.notna(selected_item['class_l1']) and selected_item['class_l1'] in l1_options else 0
            new_l1 = st.selectbox("Classe L1", l1_options, index=current_l1_idx)
        
        with col_val2:
            # Classificazione L2
            l2_options = items_df['class_l2'].dropna().unique().tolist()
            current_l2_idx = l2_options.index(selected_item['class_l2']) if pd.notna(selected_item['class_l2']) and selected_item['class_l2'] in l2_options else 0
            new_l2 = st.selectbox("Classe L2", l2_options, index=current_l2_idx)
            
            # Classificazione L3
            l3_options = items_df['class_l3'].dropna().unique().tolist()
            current_l3_idx = l3_options.index(selected_item['class_l3']) if pd.notna(selected_item['class_l3']) and selected_item['class_l3'] in l3_options else 0
            new_l3 = st.selectbox("Classe L3", l3_options, index=current_l3_idx)
        
        notes = st.text_area("Note", placeholder="Aggiungi note sulla correzione...")
        
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

st.markdown("---")

# Export
st.subheader("📤 Export Dati")

col_exp1, col_exp2 = st.columns([3, 1])

with col_exp1:
    st.info("💾 Esporta gli items filtrati con le validazioni applicate")

with col_exp2:
    if st.button("📥 Download Excel", use_container_width=True):
        from io import BytesIO
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_items.to_excel(writer, sheet_name='Items', index=False)
            
            # Sheet validazioni
            if len(validations) > 0:
                val_df = pd.DataFrame.from_dict(validations, orient='index')
                val_df.to_excel(writer, sheet_name='Validazioni')
        
        st.download_button(
            label="⬇️ Scarica",
            data=output.getvalue(),
            file_name=f"items_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")
st.caption("Pagina Items - Contract Management Dashboard")