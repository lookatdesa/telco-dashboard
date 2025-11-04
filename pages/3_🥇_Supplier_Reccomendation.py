"""
Supplier Recommendations Page
============================

Top-performing suppliers with detailed performance metrics and strategic insights.
Provides actionable recommendations for supplier selection and optimization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dashboard_utils import (
    get_analyzer,
    SPECIALIZATION_COLORS,
    PERFORMANCE_COLORS,
    SIZE_COLORS,
    ENGAGEMENT_COLORS,
    get_category_options,
    configure_streamlit_page,
    format_currency,
    format_percentage
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

configure_streamlit_page(
    page_title="Supplier Recommendations - Strategic Dashboard",
    page_icon="🏆",
    layout="wide"
)

# ============================================================================
# SUPPLIER RECOMMENDATIONS PAGE
# ============================================================================

st.title("🏆 Supplier Recommendations")
st.markdown("**Top-performing suppliers with detailed performance metrics and strategic insights**")

# ============================================================================
# METHODOLOGY & INTERPRETATION
# ============================================================================

with st.expander("ℹ️ Methodology & Supplier Metrics"):
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown("""
        **📊 Supplier Recommendation Metrics:**
        
        **🎯 Price Competitiveness (0-100):**
        - Percentile ranking of price performance in category
        - 100 = Most competitive supplier (best prices)
        - 50 = Median supplier performance
        - Based on median unit price vs category median
        
        **📐 Formula:**
        ```
        Supplier Mean Price = Mean(unit_price × quantity) for all FILTERED items of supplier
        Market Mean Price = Mean(unit_price × quantity) for all FILTERED items across all suppliers  
        Price Advantage = (Market Mean Price - Supplier Mean Price) / Market Mean Price
        Price Competitiveness = Percentile Rank of Price Advantage
        ```
        
        **💰 Spending Impact (0-100):**
        - Normalized total spending per supplier in category
        - 100 = Supplier with highest total spending in category
        - Reflects business volume and strategic importance
        - Market presence indicator
        
        **📐 Formula:**
        ```
        Spending Impact = (Supplier Category Spending / Max Category Spending) × 100
        ```
        
        **💵 Total Spending:**
        - Sum of all procurement spending with this supplier
        - Includes all contracts and items in filtered category
        - Key indicator of supplier relationship value
        """)
    
    with col_info2:
        st.markdown("""
        **📋 Additional Business Metrics:**
        
        **📊 Avg Price:**
        - Average unit price across all items from supplier
        - Weighted by item frequency, not quantity
        - Useful for price comparison and benchmarking
        
        **📄 Contracts:**
        - Number of unique contracts with this supplier
        - Indicates relationship depth and engagement level
        - Higher count suggests established partnership
        
        **📦 Items:**
        - Number of distinct procurement items
        - Shows supplier catalog breadth in category
        - Higher count indicates category expertise
        
        **🎯 Recommendation Logic:**
        Suppliers are ranked by price competitiveness, with additional consideration for market presence, category coverage, and price stability.
        
        **📐 Ranking Criteria:**
        ```
        Primary: Price Competitiveness (descending)
        Secondary: Market Presence
        Tertiary: Category Coverage
        Quality: Price Stability
        ```
        """)

# ============================================================================
# FILTERS AND PARAMETERS
# ============================================================================

st.markdown("### 🔧 Category Filters")

# Get analyzer
analyzer = get_analyzer()

col1, col2, col3 = st.columns(3)

with col1:
    l1_options = get_category_options(analyzer, 'l1')
    selected_l1 = st.selectbox("Category L1", l1_options, key="rec_l1")

with col2:
    l2_options = get_category_options(analyzer, 'l2', {'l1': selected_l1})
    selected_l2 = st.selectbox("Category L2", l2_options, key="rec_l2")

with col3:
    l3_options = get_category_options(analyzer, 'l3', {'l1': selected_l1, 'l2': selected_l2})
    selected_l3 = st.selectbox("Category L3", l3_options, key="rec_l3")

# Parameters
col1, col2, col3 = st.columns(3)

with col1:
    min_items = st.slider("Minimum Items per Supplier", 1, 20, 5)

with col2:
    min_contracts = st.slider("Minimum Contracts per Supplier", 1, 10, 1)

with col3:
    top_n = st.slider("Number of Top Suppliers", 1, 10, 3)

# Category filter active info
category_desc = []
if selected_l1 != "All":
    category_desc.append(f"L1: {selected_l1}")
if selected_l2 != "All":
    category_desc.append(f"L2: {selected_l2}")
if selected_l3 != "All":
    category_desc.append(f"L3: {selected_l3}")

if category_desc:
    st.info(f"📁 **Category Filter Active:** {' | '.join(category_desc)}")

# ============================================================================
# SUPPLIER RECOMMENDATIONS
# ============================================================================

# Get top suppliers with complete profile
top_suppliers = analyzer.get_top_suppliers_by_category(
    l1=selected_l1 if selected_l1 != "All" else None,
    l2=selected_l2 if selected_l2 != "All" else None,
    l3=selected_l3 if selected_l3 != "All" else None,
    min_items=min_items,
    min_contracts=min_contracts,  # NEW!
    top_n=top_n
)

if not top_suppliers.empty:
    
    # Display suppliers with clean card style
    for i, (_, supplier) in enumerate(top_suppliers.iterrows(), 1):
        
        # Container for each supplier card
        with st.container():
            
            # Simple header with name and icon
            rank_emojis = ["🥇", "🥈", "🥉"]
            rank_emoji = rank_emojis[i-1] if i <= 3 else "📊"
            
            # Simple supplier name
            st.markdown(f"## {rank_emoji} {supplier['supplier_name']}")
            
            # Main layout: Key Strengths on left, Metrics on right
            col_left, col_right = st.columns([1, 2])
            
            with col_left:
                st.markdown("**Key Strengths:**")
                strengths = []
                if supplier['price_competitiveness'] >= 0.8:
                    strengths.append("💰 Competitive Pricing")
                if supplier['market_presence'] >= 0.7:
                    strengths.append("💼 Strong Market Presence") 
                if supplier['category_coverage'] >= 0.6:
                    strengths.append("🎯 Good Category Coverage")
                if supplier['price_stability'] >= 0.7:
                    strengths.append("📈 Price Stability")
                
                if not strengths:
                    strengths.append("📊 Reliable Supplier")
                
                for strength in strengths[:3]:  # Max 3 strengths
                    st.markdown(f"• {strength}")
            
            with col_right:
                # Metrics grid 3x2 - ORIGINAL METRICS
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                
                # Row 1
                with metric_col1:
                    price_score = int(supplier['price_competitiveness'] * 100)
                    st.markdown("🎯 **Price Competitiveness**")
                    st.markdown(f"**{price_score}/100**")
                
                with metric_col2:
                    spending_score = int(supplier['market_presence'] * 100)
                    st.markdown("💰 **Spending Impact**")
                    st.markdown(f"**{spending_score}/100**")
                
                with metric_col3:
                    st.markdown("💵 **Total Spending**")
                    st.markdown(f"**{format_currency(supplier['total_spending'])}**")
                
                # Row 2
                metric_col4, metric_col5, metric_col6 = st.columns(3)
                
                with metric_col4:
                    st.markdown("📊 **Avg Price**")
                    st.markdown(f"**{format_currency(supplier['avg_price'], 2)}**")
                
                with metric_col5:
                    st.markdown("📄 **Contracts**")
                    st.markdown(f"**{supplier['contracts_count']:.0f}**")
                
                with metric_col6:
                    st.markdown("📦 **Items**")
                    st.markdown(f"**{supplier['items_count']:.0f}**")
            
            # Enhanced details expander
            with st.expander(f"🤔 Why choose {supplier['supplier_name']}?"):
                
                explanation_col1, explanation_col2 = st.columns(2)
                
                with explanation_col1:
                    st.markdown("**🎯 Key Advantages:**")
                    
                    # Smart recommendations based on metrics
                    advantages = []
                    
                    if supplier['price_competitiveness'] >= 0.8:
                        cost_savings = (1 - (1 - supplier['price_competitiveness'])) * 100
                        advantages.append(f"💰 **Cost Savings:** Top {cost_savings:.0f}% price performance - potential for significant procurement savings")
                    
                    if supplier['market_presence'] >= 0.7:
                        advantages.append(f"🏢 **Proven Scale:** {format_currency(supplier['total_spending'])} relationship value demonstrates capacity for large volumes")
                    
                    if supplier['contracts_count'] >= 3:
                        advantages.append(f"🤝 **Established Partnership:** {supplier['contracts_count']:.0f} active contracts show deep business relationship")
                    
                    if supplier['l3_categories'] >= 5:
                        advantages.append(f"🎯 **Category Expert:** {supplier['l3_categories']:.0f} product categories - comprehensive solution provider")
                    
                    # Price stability analysis
                    volatility_pct = (supplier['price_std'] / supplier['avg_price'] * 100) if supplier['avg_price'] > 0 else 0
                    if volatility_pct < 15:
                        advantages.append(f"📈 **Price Stability:** {volatility_pct:.1f}% price volatility - predictable cost planning")
                    
                    if not advantages:
                        advantages.append("📊 Reliable supplier with consistent performance metrics")
                    
                    for advantage in advantages[:4]:  # Max 4 advantages
                        st.markdown(f"• {advantage}")
                
                with explanation_col2:
                    st.markdown("**💡 Strategic Recommendations:**")
                    
                    # Smart action recommendations
                    recommendations = []
                    
                    if supplier['price_competitiveness'] >= 0.8 and supplier['market_presence'] < 0.5:
                        recommendations.append("📈 **Expand Volume:** Excellent pricing - consider consolidating more spend with this supplier")
                    
                    if supplier['market_presence'] >= 0.7 and supplier['price_competitiveness'] < 0.6:
                        recommendations.append("💬 **Price Negotiation:** Large volume gives leverage - negotiate better rates")
                    
                    if supplier['contracts_count'] >= 5:
                        recommendations.append("🤝 **Strategic Partnership:** Consider preferred supplier status and long-term agreements")
                    
                    if supplier['specialization_focus'] == 'Specialist' and supplier['l3_categories'] <= 3:
                        recommendations.append("🎯 **Niche Expert:** Ideal for specialized requirements in specific categories")
                    elif supplier['specialization_focus'] == 'Diversified' and supplier['l3_categories'] >= 7:
                        recommendations.append("🌐 **One-Stop Solution:** Perfect for category consolidation and simplified vendor management")
                    
                    if supplier['performance_level'] == 'Excellent':
                        recommendations.append("🌟 **Fast Track:** Prioritize for new procurement opportunities")
                    
                    # Risk considerations
                    if supplier['market_presence'] >= 0.8:
                        recommendations.append("⚠️ **Monitor Dependency:** High spend concentration - ensure backup options")
                    
                    if not recommendations:
                        recommendations.append("📋 Suitable for standard procurement needs with regular performance monitoring")
                    
                    for rec in recommendations[:4]:  # Max 4 recommendations
                        st.markdown(f"• {rec}")
                
                # Bottom insights section
                st.markdown("---")
                col_insight1, col_insight2, col_insight3 = st.columns(3)
                
                with col_insight1:
                    market_share = supplier['market_share_category']
                    if market_share >= 20:
                        st.info(f"🏆 **Market Leader**\n{market_share:.1f}% category share")
                    elif market_share >= 10:
                        st.info(f"📊 **Significant Player**\n{market_share:.1f}% category share")
                    else:
                        st.info(f"🔍 **Niche Provider**\n{market_share:.1f}% category share")
                
                with col_insight2:
                    spend_per_contract = supplier['total_spending'] / supplier['contracts_count'] if supplier['contracts_count'] > 0 else 0
                    if spend_per_contract >= 100000:
                        st.info(f"💼 **Large Deals**\n{format_currency(spend_per_contract)} avg/contract")
                    elif spend_per_contract >= 50000:
                        st.info(f"📈 **Medium Scale**\n{format_currency(spend_per_contract)} avg/contract")
                    else:
                        st.info(f"🔹 **Flexible Scale**\n{format_currency(spend_per_contract)} avg/contract")
                
                with col_insight3:
                    items_per_contract = supplier['items_count'] / supplier['contracts_count'] if supplier['contracts_count'] > 0 else 0
                    if items_per_contract >= 20:
                        st.info(f"📦 **Complex Orders**\n{items_per_contract:.0f} items/contract")
                    elif items_per_contract >= 10:
                        st.info(f"📋 **Standard Orders**\n{items_per_contract:.0f} items/contract")
                    else:
                        st.info(f"🎯 **Focused Orders**\n{items_per_contract:.0f} items/contract")
            
            st.markdown("---")

else:
    st.warning("📊 No suppliers meet the minimum criteria for the selected filters. Try reducing the minimum items threshold or adjusting your category selection.")
    st.info("💡 **Suggestions:**\n- Reduce minimum items per supplier\n- Select broader categories\n- Increase number of top suppliers")

st.markdown("---")
st.caption("🏆 Supplier Recommendations • Strategic Intelligence Dashboard")