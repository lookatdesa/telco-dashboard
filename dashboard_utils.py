"""
Dashboard Core Module
====================

Central module containing all shared functions, configurations, constants,
and the main StrategyAnalyzer class for the Contract Management Dashboard.

This module provides:
- Data loading and caching functions
- Strategic analysis engine (StrategyAnalyzer class)
- Color schemes and UI configurations
- Shared utility functions
- All business logic for supplier and contract analysis

Usage:
    from dashboard_core import get_analyzer, CATEGORY_COLORS, QUADRANT_COLORS
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import warnings
from pathlib import Path

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# ============================================================================
# STREAMLIT CONFIGURATION
# ============================================================================

def configure_streamlit_page(page_title: str, page_icon: str, layout: str = "wide"):
    """Configure Streamlit page settings with consistent parameters"""
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )

# ============================================================================
# COLOR SCHEMES AND UI CONSTANTS
# ============================================================================

# Strategic quadrant colors
STRATEGIC_COLORS = {
    'Strategic Partners': '#2E8B57',      # Sea Green
    'Leverage Opportunities': '#4169E1',   # Royal Blue
    'Critical Negotiations': '#DC143C',     # Crimson
    'Rationalize/Exit': '#FF8C00'          # Dark Orange
}

# Category colors (L1 level)
CATEGORY_COLORS = {
    'HW': '#83c9ff',        # Blue
    'SW': '#ff2b2b',        # Red
    'SERVIZIO': '#0068c9'   # Orange
}

# Supplier size classification colors
SIZE_COLORS = {
    'Large': '#2ecc71',     # Green
    'Medium': '#f39c12',    # Orange
    'Small': '#95a5a6'      # Gray
}

# Performance level colors
PERFORMANCE_COLORS = {
    'Excellent': '#2ecc71', # Green
    'Good': '#3498db',      # Blue
    'Average': '#f39c12'    # Orange
}

# Engagement level colors
ENGAGEMENT_COLORS = {
    'High': '#e74c3c',      # Red
    'Medium': '#f39c12',    # Orange
    'Low': '#95a5a6'        # Gray
}

# Specialization focus colors
SPECIALIZATION_COLORS = {
    'Diversified': '#9b59b6',  # Purple
    'Focused': '#3498db',      # Blue
    'Specialist': '#e67e22'    # Orange
}

# Category icons for UI display
CATEGORY_ICONS = {
    'HW': '🖥️',
    'SW': '⚡',
    'SERVIZIO': '⚙️'
}

# ============================================================================
# DATA LOADING AND CACHING
# ============================================================================

# Directory base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'

@st.cache_data
def load_data():
    """
    Load CSV data files with caching for performance.
    
    Returns:
        tuple: (items_df, suppliers_df, contracts_df)
    """
    try:
        contracts = pd.read_csv(DATA_DIR / 'contracts.csv')
        items = pd.read_csv(DATA_DIR / 'items.csv')
        suppliers = pd.read_csv(DATA_DIR / 'suppliers.csv')
        
        return items_df, suppliers_df, contracts_df
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

@st.cache_resource
def get_analyzer():
    """
    Get cached StrategyAnalyzer instance.
    
    Returns:
        StrategyAnalyzer: Initialized analyzer with loaded data
    """
    items_df, suppliers_df, contracts_df = load_data()
    return StrategyAnalyzer(items_df, suppliers_df, contracts_df)

# ============================================================================
# STRATEGY ANALYZER CLASS
# ============================================================================

class StrategyAnalyzer:
    """
    Strategic Positioning Matrix Analysis Engine
    
    Main class for analyzing supplier performance, market positioning,
    and generating strategic insights for procurement decisions.
    """
    
    def __init__(self, items_df: pd.DataFrame, suppliers_df: pd.DataFrame, contracts_df: pd.DataFrame):
        """
        Initialize the strategy analyzer with data.
        
        Args:
            items_df: Items/procurement data
            suppliers_df: Supplier master data
            contracts_df: Contract information
        """
        self.items_df = items_df.copy()
        self.suppliers_df = suppliers_df.copy() 
        self.contracts_df = contracts_df.copy()
        
        # Standardize supplier names using mapping table
        self._standardize_supplier_names()
        
        # Clean and prepare data
        self.items_clean = self._clean_data()
        
        # Calculate base metrics
        self.total_market_value = self.items_clean['total_price'].sum()
        
    def _standardize_supplier_names(self):
        """
        Standardize supplier names using the suppliers mapping table.
        Maps supplier_id to display_name for consistent reporting.
        """
        # Create mapping from supplier_id to display_name
        supplier_mapping = {}
        
        for _, row in self.suppliers_df.iterrows():
            if pd.notna(row['id']) and str(row['id']).startswith('supplier_'):
                try:
                    supplier_id_numeric = str(row['id']).replace('supplier_', '')
                    supplier_id_numeric = int(float(supplier_id_numeric))
                    supplier_mapping[supplier_id_numeric] = row['display_name']
                except (ValueError, TypeError):
                    continue
        
        # Apply mapping to items data
        def map_supplier_id_to_name(supplier_id):
            try:
                supplier_id_numeric = int(float(supplier_id))
                return supplier_mapping.get(supplier_id_numeric, f"Unknown_Supplier_{supplier_id_numeric}")
            except (ValueError, TypeError):
                return f"Invalid_Supplier_{supplier_id}"
        
        self.items_df['supplier_display_name'] = self.items_df['supplier_id'].apply(map_supplier_id_to_name)
        
    def _clean_data(self):
        """
        Clean and filter data for analysis.
        
        Returns:
            pd.DataFrame: Cleaned items data
        """
        items_clean = self.items_df[
            (self.items_df['total_price'].notna()) & 
            (self.items_df['total_price'] > 0) &
            (self.items_df['supplier_id'].notna())
        ].copy()
        
        return items_clean
    
    def calculate_supplier_metrics(self, category_filter_l1=None, category_filter_l2=None, category_filter_l3=None):
        """
        Calculate comprehensive supplier metrics with optional category filters.
        
        Args:
            category_filter_l1: L1 category filter
            category_filter_l2: L2 category filter  
            category_filter_l3: L3 category filter
            
        Returns:
            pd.DataFrame: Supplier metrics with positioning data
        """
        df_filtered = self.items_clean.copy()
        
        # Apply category filters
        if category_filter_l1 and category_filter_l1 != "All":
            df_filtered = df_filtered[df_filtered['class_l1'] == category_filter_l1]
        if category_filter_l2 and category_filter_l2 != "All":
            df_filtered = df_filtered[df_filtered['class_l2'] == category_filter_l2]
        if category_filter_l3 and category_filter_l3 != "All":
            df_filtered = df_filtered[df_filtered['class_l3'] == category_filter_l3]
        
        if len(df_filtered) == 0:
            return pd.DataFrame()
        
        # Calculate base metrics per supplier
        supplier_metrics = df_filtered.groupby('supplier_display_name').agg({
            'total_price': ['mean', 'count', 'std', 'sum'],  # 4 columns (fixed: no duplicate key)
            'contract_number': 'nunique',                     # 1 column
            'class_l3': 'nunique'                            # 1 column  
        })

        # Now assign 6 column names instead of 7
        supplier_metrics.columns = ['mean_total_price', 'items_count', 'price_std', 'total_spending',
                                'contracts_count', 'l3_categories']

        # Add avg_price as calculated column if needed
        supplier_metrics['avg_price'] = supplier_metrics['mean_total_price']

        # Calculate price competitiveness (normalized)
        overall_mean_price = df_filtered['total_price'].mean()  # ← CAMBIATO da median()
        price_comp_raw = (overall_mean_price - supplier_metrics['mean_total_price']) / overall_mean_price  # ← CAMBIATO nome colonna
        
        min_score = price_comp_raw.min()
        max_score = price_comp_raw.max()
        
        if max_score != min_score:
            supplier_metrics['price_competitiveness'] = (
                (price_comp_raw - min_score) / (max_score - min_score)
            ).round(3)
        else:
            supplier_metrics['price_competitiveness'] = 0.5
        
        # Calculate spending impact (normalized)
        max_spending = supplier_metrics['total_spending'].max()
        supplier_metrics['spending_normalized'] = (
            supplier_metrics['total_spending'] / max_spending
        ).round(3)
        
        # Assign strategic quadrants
        def assign_quadrant(row):
            if row['price_competitiveness'] >= 0.5 and row['spending_normalized'] >= 0.5:
                return 'Strategic Partners'
            elif row['price_competitiveness'] >= 0.5 and row['spending_normalized'] < 0.5:
                return 'Leverage Opportunities'
            elif row['price_competitiveness'] < 0.5 and row['spending_normalized'] >= 0.5:
                return 'Critical Negotiation'
            else:
                return 'Rationalize/Exit'
        
        supplier_metrics['quadrant'] = supplier_metrics.apply(assign_quadrant, axis=1)
        supplier_metrics.reset_index(inplace=True)
        supplier_metrics.rename(columns={'supplier_display_name': 'supplier_name'}, inplace=True)
        
        return supplier_metrics
    
    def calculate_market_overview(self):
        """
        Calculate comprehensive market overview metrics.
        
        Returns:
            dict: Market overview statistics and metrics
        """
        # Basic counts
        total_items = len(self.items_clean)
        total_suppliers = self.items_clean['supplier_display_name'].nunique()
        total_contracts = self.items_clean['contract_number'].nunique()
        
        # Market share calculations
        supplier_spending = self.items_clean.groupby('supplier_display_name')['total_price'].sum().sort_values(ascending=False)
        supplier_market_share = (supplier_spending / self.total_market_value * 100).round(2)
        
        category_spending = self.items_clean.groupby('class_l1')['total_price'].sum().sort_values(ascending=False)
        category_market_share = (category_spending / self.total_market_value * 100).round(2)
        
        # Market concentration metrics (HHI - Herfindahl-Hirschman Index)
        hhi_suppliers = (supplier_market_share ** 2).sum()
        
        # HHI by category L1
        hhi_by_category = {}
        for category in self.items_clean['class_l1'].dropna().unique():
            cat_data = self.items_clean[self.items_clean['class_l1'] == category]
            cat_supplier_spending = cat_data.groupby('supplier_display_name')['total_price'].sum()
            cat_total = cat_supplier_spending.sum()
            if cat_total > 0:
                cat_market_share = (cat_supplier_spending / cat_total * 100)
                hhi_by_category[category] = (cat_market_share ** 2).sum()
        
        # Calculate 80% control (how many suppliers control 80% of market)
        cumulative_share = 0
        control_80_suppliers = 0
        for share in supplier_market_share.values:
            cumulative_share += share
            control_80_suppliers += 1
            if cumulative_share >= 80:
                break
        
        def interpret_hhi(hhi):
            """Interpret HHI concentration levels"""
            if hhi < 1500:
                return "Competitive Market"
            elif hhi < 2500:
                return "Moderately Concentrated"
            else:
                return "Highly Concentrated"
        
        return {
            'total_items': total_items,
            'total_suppliers': total_suppliers,
            'total_contracts': total_contracts,
            'total_market_value': self.total_market_value,
            'supplier_market_share': supplier_market_share,
            'category_market_share': category_market_share,
            'hhi_suppliers': hhi_suppliers,
            'hhi_interpretation': interpret_hhi(hhi_suppliers),
            'hhi_by_category': hhi_by_category,
            'top_10_concentration': supplier_market_share.head(10).sum(),
            'control_80_suppliers': control_80_suppliers
        }
    
    def get_top_suppliers_by_category(self, l1=None, l2=None, l3=None, min_items=5, min_contracts=1, top_n=3):
        """
        Get top suppliers by category with comprehensive performance profiles.
        
        Args:
            l1: L1 category filter
            l2: L2 category filter
            l3: L3 category filter
            min_items: Minimum items threshold
            top_n: Number of top suppliers to return
            
        Returns:
            pd.DataFrame: Top suppliers with performance metrics
        """
        df_filtered = self.items_clean.copy()
        
        # Apply category filters
        if l1 and l1 != "All":
            df_filtered = df_filtered[df_filtered['class_l1'] == l1]
        if l2 and l2 != "All":
            df_filtered = df_filtered[df_filtered['class_l2'] == l2]
        if l3 and l3 != "All":
            df_filtered = df_filtered[df_filtered['class_l3'] == l3]
        
        if len(df_filtered) == 0:
            return pd.DataFrame()
        
        # Calculate base metrics
        supplier_metrics = df_filtered.groupby('supplier_display_name').agg({
            'total_price': ['mean', 'count', 'std', 'sum'],  # FISSO: no chiavi duplicate
            'contract_number': 'nunique',
            'class_l3': 'nunique'
        }).round(2)

        # Assegna nomi colonne corretti (ora abbiamo esattamente 6 colonne)
        supplier_metrics.columns = ['mean_total_price', 'items_count', 'price_std', 'total_spending',
                                'contracts_count', 'l3_categories']

        # Aggiungi avg_price
        supplier_metrics['avg_price'] = supplier_metrics['mean_total_price']

        # Apply minimum items filter
        supplier_metrics = supplier_metrics[supplier_metrics['items_count'] >= min_items]
        
        # Apply minimum contracts filter
        supplier_metrics = supplier_metrics[supplier_metrics['contracts_count'] >= min_contracts]
   
        if len(supplier_metrics) == 0:
            print("Nessun supplier soddisfa i criteri minimum items")
            return pd.DataFrame()

        # Calculate price competitiveness
        category_mean_price = df_filtered['total_price'].mean()  # ← CAMBIATO da median()
        price_comp_raw = (category_mean_price - supplier_metrics['mean_total_price']) / category_mean_price  # ← CAMBIATO
        
        min_score = price_comp_raw.min()
        max_score = price_comp_raw.max()
        
        if max_score != min_score:
            supplier_metrics['price_competitiveness'] = (
                (price_comp_raw - min_score) / (max_score - min_score)
            ).round(3)
        else:
            supplier_metrics['price_competitiveness'] = 0.5
        
        # Calculate market share in category
        category_total_spending = supplier_metrics['total_spending'].sum()
        supplier_metrics['market_share_category'] = (
            supplier_metrics['total_spending'] / category_total_spending * 100
        ).round(2)
        
        # Performance radar metrics
        # 1. Market Presence
        max_spending_all = supplier_metrics['total_spending'].max()
        supplier_metrics['market_presence'] = (
            supplier_metrics['total_spending'] / max_spending_all
        ).round(3)
        
        # 2. Category Coverage (L3)
        max_l3_categories = supplier_metrics['l3_categories'].max()
        supplier_metrics['category_coverage'] = (
            supplier_metrics['l3_categories'] / max_l3_categories if max_l3_categories > 0 else 0
        ).round(3)
        
        # 3. Price Stability (inverse of volatility)
        supplier_metrics['price_volatility'] = supplier_metrics['price_std'] / supplier_metrics['avg_price']
        max_stability = 1 / (supplier_metrics['price_volatility'].min() + 0.001)
        supplier_metrics['price_stability'] = (
            1 / (supplier_metrics['price_volatility'] + 0.001) / max_stability
        ).round(3)
        
        # Supplier classifications
        # Size classification
        spending_33 = supplier_metrics['total_spending'].quantile(0.33)
        spending_66 = supplier_metrics['total_spending'].quantile(0.66)
        
        def classify_size(spending):
            if spending >= spending_66:
                return 'Large'
            elif spending >= spending_33:
                return 'Medium'
            else:
                return 'Small'
        
        supplier_metrics['supplier_size'] = supplier_metrics['total_spending'].apply(classify_size)
        
        # Performance level classification
        def classify_performance(score):
            if score >= 0.75:
                return 'Excellent'
            elif score >= 0.5:
                return 'Good'
            else:
                return 'Average'
        
        supplier_metrics['performance_level'] = supplier_metrics['price_competitiveness'].apply(classify_performance)
        
        # Engagement level classification
        contracts_33 = supplier_metrics['contracts_count'].quantile(0.33)
        contracts_66 = supplier_metrics['contracts_count'].quantile(0.66)
        
        def classify_engagement(contracts):
            if contracts >= contracts_66:
                return 'High'
            elif contracts >= contracts_33:
                return 'Medium'
            else:
                return 'Low'
        
        supplier_metrics['engagement_level'] = supplier_metrics['contracts_count'].apply(classify_engagement)
        
        # Specialization focus classification
        def classify_specialization(l3_count):
            if l3_count <= 3:
                return 'Specialist'
            elif l3_count <= 6:
                return 'Focused'
            else:
                return 'Diversified'
        
        supplier_metrics['specialization_focus'] = supplier_metrics['l3_categories'].apply(classify_specialization)
        
        # Sort by competitiveness and return top N
        supplier_metrics = supplier_metrics.sort_values('price_competitiveness', ascending=False)
        supplier_metrics.reset_index(inplace=True)
        supplier_metrics.rename(columns={'supplier_display_name': 'supplier_name'}, inplace=True)
        
        return supplier_metrics.head(top_n)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_category_options(analyzer, level='l1', parent_filter=None):
    """
    Get available category options for filtering.
    
    Args:
        analyzer: StrategyAnalyzer instance
        level: Category level ('l1', 'l2', 'l3')
        parent_filter: Parent category filter for hierarchical filtering
        
    Returns:
        list: Available category options
    """
    column_map = {
        'l1': 'class_l1',
        'l2': 'class_l2', 
        'l3': 'class_l3'
    }
    
    if level not in column_map:
        return ["All"]
    
    df = analyzer.items_clean
    
    # Apply parent filter if provided
    if parent_filter and level != 'l1':
        if level == 'l2' and parent_filter.get('l1') != "All":
            df = df[df['class_l1'] == parent_filter['l1']]
        elif level == 'l3':
            if parent_filter.get('l1') != "All":
                df = df[df['class_l1'] == parent_filter['l1']]
            if parent_filter.get('l2') != "All":
                df = df[df['class_l2'] == parent_filter['l2']]
    
    options = ["All"] + sorted(df[column_map[level]].dropna().unique().tolist())
    return options

def format_currency(value, decimals=0):
    """
    Format numeric value as currency.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
        
    Returns:
        str: Formatted currency string
    """
    if pd.isna(value):
        return "€0"
    return f"€{value:,.{decimals}f}"

def format_percentage(value, decimals=1):
    """
    Format numeric value as percentage.
    
    Args:
        value: Numeric value (0-100 scale)
        decimals: Number of decimal places
        
    Returns:
        str: Formatted percentage string
    """
    if pd.isna(value):
        return "0.0%"
    return f"{value:.{decimals}f}%"

def create_performance_radar(supplier_data, metrics=['price_competitiveness', 'market_presence', 'category_coverage', 'price_stability']):
    """
    Create radar chart for supplier performance metrics.
    
    Args:
        supplier_data: Supplier metrics data
        metrics: List of metrics to include in radar
        
    Returns:
        plotly.graph_objects.Figure: Radar chart
    """
    if len(supplier_data) == 0:
        return go.Figure()
    
    fig = go.Figure()
    
    for idx, row in supplier_data.iterrows():
        values = [row[metric] * 100 for metric in metrics]  # Convert to percentage
        values.append(values[0])  # Close the radar
        
        metric_labels = [metric.replace('_', ' ').title() for metric in metrics]
        metric_labels.append(metric_labels[0])  # Close the radar
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metric_labels,
            fill='toself',
            name=row['supplier_name']
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        height=400
    )
    
    return fig

# ============================================================================
# VERSION INFO
# ============================================================================

__version__ = "1.0.0"
__author__ = "Dashboard Development Team"
__description__ = "Core module for Contract Management Dashboard"