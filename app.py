
import streamlit as st

st.set_page_config(
    page_title="GGF Beverage Dashboard",
    page_icon="🥤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# HEADER
# ============================================================

st.title("🥤 GGF Beverage Business Dashboard")

st.markdown(
    """
    Explore beverage sales performance, product profitability,
    raw-material price trends, and potential forecasting scenarios
    through an interactive business analytics dashboard.
    """
)

st.divider()

# ============================================================
# DASHBOARD OVERVIEW
# ============================================================

st.subheader("📊 Dashboard Overview")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 💰 Sales Performance")
    st.write(
        """
        Analyze transaction trends, sales revenue, product performance,
        and category contributions to identify key business drivers.
        """
    )

    st.markdown("### 🧃 Product Analysis")
    st.write(
        """
        Explore product and SKU performance to understand sales
        distribution and identify high-performing products.
        """
    )

with col2:
    st.markdown("### 🌱 Raw Material Analysis")
    st.write(
        """
        Examine historical raw-material prices and their movements
        to understand potential cost and profitability implications.
        """
    )

    st.markdown("### 🔮 Forecasting & Scenarios")
    st.write(
        """
        Explore potential future trends and compare forecasting
        scenarios to support business planning and decision-making.
        """
    )

st.divider()

# ============================================================
# HOW TO USE
# ============================================================

st.subheader("🚀 How to Get Started")

st.markdown(
    """
    1. Select a dashboard page from the **sidebar**.
    2. Apply available filters, such as date, product, or category.
    3. Review KPIs, charts, and tables to explore business performance.
    4. Use the findings to identify trends, opportunities, and areas
       that may require further investigation.
    """
)

st.info(
    "**Note:** This dashboard is intended for exploratory business "
    "analysis and decision support. Forecasts and scenario results "
    "are estimates, not guaranteed outcomes or audited financial figures."
)

st.caption(
    "GGF Beverage Business Dashboard | Sales Analytics & Business Insights"
)
