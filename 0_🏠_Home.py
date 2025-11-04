"""
Home Page 
====================

Welcome page for the Contract Management Dashboard.
"""

import streamlit as st

# ============================================================================
# PAGE CONFIGURATION (MUST BE FIRST)
# ============================================================================

st.set_page_config(
    page_title="Contract Management Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# AUTHENTICATION CHECK
# ============================================================================

from auth import require_authentication, show_user_info_sidebar

if not require_authentication():
    st.stop()

# Show user info in sidebar
show_user_info_sidebar()

# ============================================================================
# IMPORTS
# ============================================================================

from dashboard_utils import get_analyzer, format_currency

# ============================================================================
# HOME PAGE CONTENT
# ============================================================================

st.title("🏠 Contract Management Dashboard")
st.markdown("---")

st.markdown("""
## Welcome to the Contract Management Dashboard

This comprehensive dashboard provides strategic analysis of suppliers and competitive positioning insights for procurement decision-making.

### 📋 Available Sections

Navigate through the different analytical modules using the sidebar:

**📊 Market Overview**
- Market concentration analysis and supplier distribution
- Category-wise spending breakdown and market share visualization
- Top supplier rankings and competitive landscape overview

**🎯 Strategic Positioning**
- Strategic positioning matrix with price competitiveness vs spending impact
- Supplier quadrant analysis (Strategic Partners, Leverage Opportunities, Critical Negotiations, Rationalize/Exit)
- Interactive filtering by product categories and detailed supplier metrics

**🏆 Supplier Recommendations**
- Top-performing suppliers by category with comprehensive scoring
- Performance radar charts and supplier profile classifications
- Detailed competitiveness analysis and actionable recommendations

**🧠 Business Intelligence**
- Advanced analytics combining contracts, items, and supplier data
- Deep-dive analysis with integrated insights for strategic decision-making
- Custom filtering and multi-dimensional analysis capabilities

### 🚀 Getting Started

1. **Select a page** from the sidebar to begin your analysis
2. **Use filters** within each section to focus on specific categories or suppliers
3. **Explore interactive charts** by hovering, zooming, and clicking for detailed insights
4. **Review summary tables** for comprehensive data views and export capabilities

### 💡 Key Features

- **Real-time Analytics**: All calculations are performed dynamically based on current data
- **Interactive Visualizations**: Plotly-powered charts with full interactivity
- **Strategic Insights**: Business-ready analysis with actionable recommendations
- **Category Filtering**: Hierarchical filtering across L1, L2, and L3 product categories
- **Performance Metrics**: Comprehensive supplier scoring and classification systems

---

**👈 Select a page from the sidebar to start exploring your procurement insights!**
""")

# ============================================================================
# QUICK STATS PREVIEW
# ============================================================================

st.markdown("### 📈 Quick Dashboard Preview")

try:
    analyzer = get_analyzer()
    market_data = analyzer.calculate_market_overview()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🏢 Total Suppliers",
            f"{market_data['total_suppliers']:,}",
            help="Total number of unique suppliers"
        )
    
    with col2:
        st.metric(
            "💰 Market Value",
            format_currency(market_data['total_market_value']),
            help="Total procurement spending"
        )
    
    with col3:
        st.metric(
            "📋 Total Items",
            f"{market_data['total_items']:,}",
            help="Total procurement items"
        )
    
    with col4:
        st.metric(
            "📄 Active Contracts",
            f"{market_data['total_contracts']:,}",
            help="Number of unique contracts"
        )
    
    st.info("💡 **Tip**: Navigate to specific sections for detailed analysis and insights.")

except Exception as e:
    st.warning("⚠️ Data loading in progress. Please refresh the page if this message persists.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("🏠 Contract Management Dashboard • Strategic Procurement Intelligence")