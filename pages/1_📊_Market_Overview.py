"""
Market Overview Page
===================

Comprehensive market insights and supplier concentration analysis.
Shows market distribution, top suppliers, and category-specific analytics.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dashboard_utils import (
    get_analyzer, 
    CATEGORY_COLORS, 
    CATEGORY_ICONS,
    configure_streamlit_page,
    format_currency,
    format_percentage
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

configure_streamlit_page(
    page_title="Market Overview - Strategic Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# MARKET OVERVIEW PAGE
# ============================================================================

st.title("📊 Market Overview")
st.markdown("**Comprehensive market insights and supplier concentration analysis**")
st.markdown("---")

# Get analyzer and calculate market data
analyzer = get_analyzer()
market_data = analyzer.calculate_market_overview()

# ============================================================================
# KEY METRICS SECTION
# ============================================================================

# First row of metrics (3 columns)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "🏢 Suppliers",
        f"{market_data['total_suppliers']:,}",
        help="Number of unique suppliers in the portfolio"
    )

with col2:
    st.metric(
        "📋 Items",
        f"{market_data['total_items']:,}",
        help="Total number of procurement items"
    )

with col3:
    st.metric(
        "📄 Contracts",
        f"{market_data['total_contracts']:,}",
        help="Number of unique contracts (excluding versions)"
    )

# Second row of metrics (3 columns)
col4, col5, col6 = st.columns(3)

with col4:
    st.metric(
        "💰 Market Value",
        format_currency(market_data['total_market_value']),
        help="Total spending across all suppliers and categories"
    )

with col5:
    st.metric(
        "🔝 Top 10 Share",
        format_percentage(market_data['top_10_concentration']),
        help="Market share of top 10 suppliers"
    )

with col6:
    st.metric(
        "⚡ 80% Control",
        f"{market_data['control_80_suppliers']} suppliers",
        help="Number of suppliers controlling 80% of market"
    )

st.markdown("---")

# ============================================================================
# MARKET DISTRIBUTION CHARTS
# ============================================================================

# First row: Market Share by Category + Top 15 Suppliers
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📈 Market Share by Category")
    
    fig_categories_pie = px.pie(
        values=market_data['category_market_share'].values,
        names=market_data['category_market_share'].index,
        title="",
        color_discrete_map=CATEGORY_COLORS
    )
    fig_categories_pie.update_layout(height=400)
    st.plotly_chart(fig_categories_pie, use_container_width=True)

with col2:
    st.markdown("### 🏆 Top 15 Suppliers by Market Share")
    
    top_15_suppliers = market_data['supplier_market_share'].head(15)
    
    # Reverse order for better visualization (top 1 at top)
    fig_suppliers = px.bar(
        x=top_15_suppliers.values[::-1],  # Reverse values
        y=top_15_suppliers.index[::-1],   # Reverse names
        orientation='h',
        title="",
        labels={'x': 'Market Share (%)', 'y': ''},
        color=top_15_suppliers.values[::-1],
        color_continuous_scale='Blues'
    )
    
    fig_suppliers.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_suppliers, use_container_width=True)

st.markdown("---")

# ============================================================================
# TOP SUPPLIERS BY CATEGORY
# ============================================================================

st.markdown("### 🎯 Top Suppliers by Category")

# Calculate top suppliers for each L1 category
categories = ['SERVIZIO', 'HW', 'SW']
col1, col2, col3 = st.columns(3)

for idx, category in enumerate(categories):
    # Filter data for category
    category_data = analyzer.items_clean[analyzer.items_clean['class_l1'] == category]
    
    if len(category_data) > 0:
        # Calculate market share for category
        category_suppliers = category_data.groupby('supplier_display_name')['total_price'].sum().sort_values(ascending=False)
        category_total = category_suppliers.sum()
        category_market_share = (category_suppliers / category_total * 100).round(1)
        
        # Get top 10 suppliers for this category
        top_10_category = category_market_share.head(10)
        
        # Create chart with consistent colors
        fig_category = px.bar(
            x=top_10_category.values[::-1],  # Reverse for top at top
            y=top_10_category.index[::-1],   # Reverse names
            orientation='h',
            title=f"{CATEGORY_ICONS[category]} {category}",
            labels={'x': 'Market Share (%)', 'y': ''},
            color_discrete_sequence=[CATEGORY_COLORS.get(category, '#3498db')]
        )
        
        fig_category.update_layout(
            height=400, 
            showlegend=False,
            title=dict(font=dict(size=16)),
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        # Display in corresponding column
        if idx == 0:
            with col1:
                st.plotly_chart(fig_category, use_container_width=True)
        elif idx == 1:
            with col2:
                st.plotly_chart(fig_category, use_container_width=True)
        else:
            with col3:
                st.plotly_chart(fig_category, use_container_width=True)

st.markdown("---")

# ============================================================================
# SUPPLIER × CATEGORY HEATMAP
# ============================================================================

st.markdown("### 🔥 Market Share Distribution Heatmap")

# Create heatmap data with TOP 15 SUPPLIERS
top_15_supplier_names = market_data['supplier_market_share'].head(15).index
categories_l1 = market_data['category_market_share'].index

heatmap_data = []
heatmap_text = []

# REVERSE ORDER: Top supplier at bottom, #15 at top
for supplier in reversed(top_15_supplier_names):
    supplier_row = []
    text_row = []
    for category in categories_l1:
        # Calculate market share % for this combination
        supplier_cat_spending = analyzer.items_clean[
            (analyzer.items_clean['supplier_display_name'] == supplier) &
            (analyzer.items_clean['class_l1'] == category)
        ]['total_price'].sum()
        
        market_share_pct = (supplier_cat_spending / analyzer.total_market_value * 100)
        supplier_row.append(market_share_pct)
        text_row.append(f"{market_share_pct:.1f}%" if market_share_pct > 0 else "")
    
    heatmap_data.append(supplier_row)
    heatmap_text.append(text_row)

# Create heatmap with Plotly - FULL WIDTH
fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_data,
    x=categories_l1,
    y=list(reversed(top_15_supplier_names)),  # REVERSE Y LABELS TOO
    colorscale='Blues',
    text=heatmap_text,
    texttemplate="%{text}",
    textfont={"size": 10},
    showscale=True,
    colorbar=dict(title="Market Share %"),
    hoverongaps=False
))

fig_heatmap.update_layout(
    title="Supplier × Category Market Share Distribution (%)",
    height=500,  # Taller for 15 suppliers
    xaxis_title="Category L1",
    yaxis_title="Top 15 Suppliers (Ranked by Total Market Share)",
    font=dict(size=11)
)

# FULL WIDTH
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")
st.caption("📊 Market Overview • Strategic Intelligence Dashboard")