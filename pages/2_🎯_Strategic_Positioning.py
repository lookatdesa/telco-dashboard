import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dashboard_utils import get_analyzer, STRATEGIC_COLORS

st.set_page_config(
    page_title="Strategic Positioning - Strategic Dashboard", 
    page_icon="🎯", 
    layout="wide"
)

# ============================================================================
# STRATEGIC POSITIONING PAGE
# ============================================================================

st.title("🎯 Strategic Positioning")
st.markdown("**Supplier positioning matrix and strategic partnership analysis**")

from textwrap import dedent

with st.expander("ℹ️ Methodology & Matrix Construction"):
    st.markdown(dedent("""
    **📊 Matrix Dimensions:**

    **X-Axis – Spend Impact (0–100%)**
    - Normalized total spending per supplier  
    - 100% = supplier with highest total spending  
    - Reflects business volume and strategic importance  
                    
    **📐 Formula**
    ```
    Spend Impact = (Supplier Total Spending / Max Spending) × 100
    ```

    **Y-Axis – Price Competitiveness (0–100%)**
    - Percentile ranking of price performance  
    - 50% = median supplier in the market  
    - 90% = top 10% most competitive suppliers  
    - Based on mean total price comparison  
                    
    **📐 Formula**
    ```
    Supplier Mean Price = Mean(unit_price × quantity) for all FILTERED items of supplier
    Market Mean Price = Mean(unit_price × quantity) for all FILTERED items across all suppliers  
    Price Advantage = (Market Mean Price - Supplier Mean Price) / Market Mean Price
    Price Competitiveness = Percentile Rank of Price Advantage
    ```

    **Bubble Size – Contract Portfolio**
    - Number of unique contracts per supplier  
    - Larger bubbles = more diversified relationships  

    ---

    **🎯 Strategic Quadrants:**

    **Strategic Partners (Top-Right):**  
    High spending volume + competitive pricing. These are your key strategic suppliers offering both scale and value.

    **Leverage Opportunities (Top-Left):**  
    Competitive pricing but lower spending. Consider increasing business volume with these suppliers.

    **Critical Negotiations (Bottom-Right):**  
    High spending but expensive pricing. Priority targets for price negotiations and contract optimization.

    **Rationalize/Exit (Bottom-Left):**  
    Low spending and expensive pricing. Evaluate relationship necessity and consider supplier consolidation.

    **📐 Quadrant Logic**
    ```
    Strategic Partners: Spend Impact ≥ 50% AND Price Competitiveness ≥ 50%
    Leverage Opportunities: Spend Impact < 50% AND Price Competitiveness ≥ 50%
    Critical Negotiations: Spend Impact ≥ 50% AND Price Competitiveness < 50%
    Rationalize/Exit: Spend Impact < 50% AND Price Competitiveness < 50%
    ```
    """))

# Filtri per la matrice
st.markdown("### 🔧 Matrix Filters")

# Get analyzer
analyzer = get_analyzer()

col1, col2, col3 = st.columns(3)

with col1:
    l1_options = ["All"] + sorted(analyzer.items_clean['class_l1'].dropna().unique().tolist())
    selected_l1 = st.selectbox("Category L1", l1_options, key="matrix_l1")

with col2:
    if selected_l1 != "All":
        l2_data = analyzer.items_clean[analyzer.items_clean['class_l1'] == selected_l1]['class_l2'].dropna().unique()
        l2_options = ["All"] + sorted(l2_data.tolist())
    else:
        l2_options = ["All"] + sorted(analyzer.items_clean['class_l2'].dropna().unique().tolist())
    selected_l2 = st.selectbox("Category L2", l2_options, key="matrix_l2")

with col3:
    if selected_l2 != "All":
        if selected_l1 != "All":
            l3_data = analyzer.items_clean[
                (analyzer.items_clean['class_l1'] == selected_l1) &
                (analyzer.items_clean['class_l2'] == selected_l2)
            ]['class_l3'].dropna().unique()
        else:
            l3_data = analyzer.items_clean[analyzer.items_clean['class_l2'] == selected_l2]['class_l3'].dropna().unique()
        l3_options = ["All"] + sorted(l3_data.tolist())
    else:
        l3_options = ["All"] + sorted(analyzer.items_clean['class_l3'].dropna().unique().tolist())
    selected_l3 = st.selectbox("Category L3", l3_options, key="matrix_l3")

# CATEGORY FILTER ACTIVE INFO - AGGIUNTO
category_desc = []
if selected_l1 != "All":
    category_desc.append(f"L1: {selected_l1}")
if selected_l2 != "All":
    category_desc.append(f"L2: {selected_l2}")
if selected_l3 != "All":
    category_desc.append(f"L3: {selected_l3}")

if category_desc:
    st.info(f"📁 **Category Filter Active:** {' | '.join(category_desc)}")

# Calcola metriche con filtri - VERSIONE CORRETTA
df_filtered = analyzer.items_clean.copy()

# Applica filtri
if selected_l1 and selected_l1 != "All":
    df_filtered = df_filtered[df_filtered['class_l1'] == selected_l1]
if selected_l2 and selected_l2 != "All":
    df_filtered = df_filtered[df_filtered['class_l2'] == selected_l2]
if selected_l3 and selected_l3 != "All":
    df_filtered = df_filtered[df_filtered['class_l3'] == selected_l3]

if len(df_filtered) == 0:
    st.warning("📊 No data available for the selected filters. Try adjusting your selection.")
else:
    # Calcola metriche per fornitore con NORMALIZZAZIONE CORRETTA
    supplier_metrics = df_filtered.groupby('supplier_display_name').agg({
        'total_price': ['mean', 'median', 'count', 'std', 'sum'],  # ← UNIFICATO in una sola riga
        'contract_number': 'nunique',
        'quantity': 'sum'
    }).round(2)

    supplier_metrics.columns = ['avg_total_price', 'mean_total_price', 'items_count', 'price_std', 
                            'total_spending', 'contracts_count', 'total_quantity']  # ← 7 colonne

    # PRICE COMPETITIVENESS: Normalizzazione PERCENTILE
    overall_mean_price = df_filtered['total_price'].mean()  # ← CAMBIATO da median()
    price_comp_raw = (overall_mean_price - supplier_metrics['mean_total_price']) / overall_mean_price  # ← CAMBIATO

    # Usa normalizzazione percentile invece di min-max
    supplier_metrics['price_competitiveness'] = (
        pd.Series(price_comp_raw).rank(pct=True, method='min')
    ).round(3)
    
    # SPENDING: Normalizzazione Min-Max (manteniamo come prima)
    max_spending = supplier_metrics['total_spending'].max()
    supplier_metrics['spending_normalized'] = (
        supplier_metrics['total_spending'] / max_spending
    ).round(3)
    
    # Assegna quadrante
    def assign_quadrant(row):
        if row['price_competitiveness'] >= 0.5 and row['spending_normalized'] >= 0.5:
            return 'Strategic Partners'
        elif row['price_competitiveness'] >= 0.5 and row['spending_normalized'] < 0.5:
            return 'Leverage Opportunities'
        elif row['price_competitiveness'] < 0.5 and row['spending_normalized'] >= 0.5:
            return 'Critical Negotiations'
        else:
            return 'Rationalize/Exit'
    
    supplier_metrics['quadrant'] = supplier_metrics.apply(assign_quadrant, axis=1)
    supplier_metrics.reset_index(inplace=True)
    supplier_metrics.rename(columns={'supplier_display_name': 'supplier_name'}, inplace=True)
    
    # Prepara dataframe per la matrice strategica
    positioning_df = supplier_metrics.copy()
    
    # Converti le metriche normalizzate in scala 0-100 per visualizzazione
    positioning_df['total_spend_normalized'] = (positioning_df['spending_normalized'] * 100).round(1)
    positioning_df['performance_score'] = (positioning_df['price_competitiveness'] * 100).round(1)
    positioning_df['total_contracts'] = positioning_df['contracts_count']
    
    # Definisci i colori per i quadranti strategici
    def get_strategic_color(row):
        spend_normalized = row['total_spend_normalized']
        performance = row['performance_score']
        
        if spend_normalized >= 50 and performance >= 50:
            return 'Strategic Partners'
        elif spend_normalized >= 50 and performance < 50:
            return 'Critical Negotiations'
        elif spend_normalized < 50 and performance >= 50:
            return 'Leverage Opportunities'
        else:
            return 'Rationalize/Exit'
    
    positioning_df['strategic_category'] = positioning_df.apply(get_strategic_color, axis=1)
    
    # Scatter plot della matrice strategica
    fig_strategic = px.scatter(
        positioning_df,
        x='total_spend_normalized',
        y='performance_score',
        size='total_contracts',
        color='strategic_category',
        hover_name='supplier_name',
        hover_data={
            'total_spend_normalized': False,
            'performance_score': False, 
            'total_contracts': False,
            'strategic_category': False,
            'total_spending': True,  # SPESA TOTALE CORRETTA
            'avg_total_price': True   # PREZZO MEDIO CORRETTO
        },
        title="Strategic Positioning Matrix",
        color_discrete_map=STRATEGIC_COLORS,
        labels={
            'total_spend_normalized': 'Spend Impact (%)',
            'performance_score': 'Price Competitiveness (%)',
            'total_contracts': 'Contracts'
        },
        size_max=15  # DIMENSIONE MASSIMA RIDOTTA
    )
    
    # REGOLA DIMENSIONE DELLE BOLLE E HOVER PERSONALIZZATO
    fig_strategic.update_traces(
        marker=dict(
            sizemin=3,  # DIMENSIONE MINIMA PICCOLA MA VISIBILE
            sizemode='diameter',
            sizeref=2. * max(positioning_df['total_contracts']) / (12**2),  # SCALA CONTENUTA
            line=dict(width=1, color='white')  # BORDO BIANCO PER MIGLIORE VISIBILITÀ
        ),
        hovertemplate=(
            "<b>%{hovertext}</b><br>" +
            "<b>Matrix Positioning:</b><br>" +
            "🎯 Price Competitiveness: %{y:.1f}% <br>" +
            "💰 Spend Impact: %{x:.1f}% <br>" +
            "📄 Number of Contracts: %{marker.size}<br>" +
            "<extra></extra>"
        )
    )
    
    # PERSONALIZZA IL COLORE DEL BOX HOVER PER OGNI QUADRANTE
    for trace in fig_strategic.data:
        if hasattr(trace, 'name') and trace.name in STRATEGIC_COLORS:
            trace.update(
                hoverlabel=dict(
                    bgcolor=STRATEGIC_COLORS[trace.name],
                    bordercolor="white", 
                    font=dict(color="white", size=12)
                )
            )
    
    # Aggiungi linee di demarcazione dei quadranti
    fig_strategic.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
    fig_strategic.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Aggiungi annotazioni dei quadranti
    def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f'rgba({r},{g},{b},{alpha})'

    ALPHA = 0.60  # ~50% di opacità

    fig_strategic.add_annotation(
        x=75, y=75, text="Strategic<br>Partners",
        showarrow=False, font_size=12, font_color="white",
        bgcolor=hex_to_rgba(STRATEGIC_COLORS['Strategic Partners'], ALPHA)
    )

    fig_strategic.add_annotation(
        x=25, y=75, text="Leverage<br>Opportunities",
        showarrow=False, font_size=12, font_color="white",
        bgcolor=hex_to_rgba(STRATEGIC_COLORS['Leverage Opportunities'], ALPHA)
    )

    fig_strategic.add_annotation(
        x=75, y=25, text="Critical<br>Negotiations",
        showarrow=False, font_size=12, font_color="white",
        bgcolor=hex_to_rgba(STRATEGIC_COLORS['Critical Negotiations'], ALPHA)
    )

    fig_strategic.add_annotation(
        x=25, y=25, text="Rationalize/<br>Exit",
        showarrow=False, font_size=12, font_color="white",
        bgcolor=hex_to_rgba(STRATEGIC_COLORS['Rationalize/Exit'], ALPHA)
    )
    
    # LAYOUT CORRETTO - LEGENDA SOTTO E ALLINEATA A SINISTRA
    fig_strategic.update_layout(
        height=600,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.08,  # SOTTO IL GRAFICO
            xanchor="left",
            x=0  # ALLINEATA A SINISTRA
        ),
        margin=dict(b=80)  # Margine inferiore per la legenda
    )
    
    st.plotly_chart(fig_strategic, use_container_width=True)
    
    # BUBBLE SIZE INFO - SENZA SFONDO, SOTTO IL GRAFICO
    st.markdown("💡 **Bubble Size** = Number of Contracts per Supplier")
    
    # Statistiche per quadrante strategico
    col_quad1, col_quad2, col_quad3, col_quad4 = st.columns(4)
    
    quadrant_stats = positioning_df.groupby('strategic_category').agg({
        'supplier_name': 'count',
        'total_spending': 'sum',
        'performance_score': 'mean'
    }).round(1)
    
    with col_quad1:
        if 'Strategic Partners' in quadrant_stats.index:
            stats = quadrant_stats.loc['Strategic Partners']
            st.metric(
                "🌟 Strategic Partners",
                f"{stats['supplier_name']} suppliers",
                delta=f"€{stats['total_spending']:,.0f} spend"
            )
        else:
            st.metric("🌟 Strategic Partners", "0 suppliers")
    
    with col_quad2:
        if 'Leverage Opportunities' in quadrant_stats.index:
            stats = quadrant_stats.loc['Leverage Opportunities']
            st.metric(
                "📈 Leverage Opps",
                f"{stats['supplier_name']} suppliers",
                delta=f"€{stats['total_spending']:,.0f} spend"
            )
        else:
            st.metric("📈 Leverage Opps", "0 suppliers")
    
    with col_quad3:
        if 'Critical Negotiations' in quadrant_stats.index:
            stats = quadrant_stats.loc['Critical Negotiations']
            st.metric(
                "⚠️ Critical Neg.",
                f"{stats['supplier_name']} suppliers",
                delta=f"€{stats['total_spending']:,.0f} spend"
            )
        else:
            st.metric("⚠️ Critical Neg.", "0 suppliers")
    
    with col_quad4:
        if 'Rationalize/Exit' in quadrant_stats.index:
            stats = quadrant_stats.loc['Rationalize/Exit']
            st.metric(
                "🚪 Rationalize",
                f"{stats['supplier_name']} suppliers",
                delta=f"€{stats['total_spending']:,.0f} spend"
            )
        else:
            st.metric("🚪 Rationalize", "0 suppliers")

    # ============================================================================
    # TABELLA SUMMARY COMPLETA
    # ============================================================================
    
    st.markdown("---")
    st.markdown("### 📊 Complete Supplier Matrix Summary")
    
    # Crea tabella completa
    summary_df = positioning_df[['supplier_name', 'strategic_category', 'performance_score', 
                                'total_spend_normalized', 'total_spending', 'avg_total_price', 
                                'contracts_count', 'items_count']].copy()
    
    # Rinomina colonne
    summary_df.columns = [
        'Supplier Name', 'Strategic Quadrant', 'Price Competitiveness (%)', 
        'Spend Impact (%)', 'Total Spending (€)', 'Avg Unit Price (€)',
        'Contracts', 'Items'
    ]
    
    # Formatta valori
    summary_df['Total Spending (€)'] = summary_df['Total Spending (€)'].apply(lambda x: f"€{x:,.0f}")
    summary_df['Avg Unit Price (€)'] = summary_df['Avg Unit Price (€)'].apply(lambda x: f"€{x:,.2f}")
    summary_df['Price Competitiveness (%)'] = summary_df['Price Competitiveness (%)'].apply(lambda x: f"{x:.1f}%")
    summary_df['Spend Impact (%)'] = summary_df['Spend Impact (%)'].apply(lambda x: f"{x:.1f}%")
    
    # Ordina per quadrante e performance
    quadrant_order = ['Strategic Partners', 'Leverage Opportunities', 'Critical Negotiations', 'Rationalize/Exit']
    summary_df['quadrant_order'] = summary_df['Strategic Quadrant'].map({q: i for i, q in enumerate(quadrant_order)})
    summary_df = summary_df.sort_values(['quadrant_order', 'Price Competitiveness (%)'], ascending=[True, False])
    summary_df = summary_df.drop('quadrant_order', axis=1)
    
    # Funzione per colorare le righe in base al quadrante
    def highlight_quadrant(row):
        color = STRATEGIC_COLORS.get(row['Strategic Quadrant'], '')
        return [f'background-color: {color}20'] * len(row)  # Aggiunge trasparenza (20 in hex ≈ 12% opacity)
    
    # Mostra tabella completa con colori
    st.dataframe(
        summary_df.style.apply(highlight_quadrant, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Supplier Name": st.column_config.TextColumn("Supplier Name", width="medium"),
            "Strategic Quadrant": st.column_config.TextColumn("Quadrant", width="medium"),
            "Price Competitiveness (%)": st.column_config.TextColumn("Price Comp.", width="small"),
            "Spend Impact (%)": st.column_config.TextColumn("Spend Impact", width="small"),
            "Total Spending (€)": st.column_config.TextColumn("Total Spending", width="medium"),
            "Avg Unit Price (€)": st.column_config.TextColumn("Avg Price", width="small"),
            "Contracts": st.column_config.NumberColumn("Contracts", width="small"),
            "Items": st.column_config.NumberColumn("Items", width="small")
        }
    )

st.markdown("---")
st.caption("🎯 Strategic Positioning • Advanced Supplier Analysis")