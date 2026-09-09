"""
Streamlit Dashboard — Blockchain Sustainability Research
=========================================================
Main entry point. Run with:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

# Ensure project root is on the Python path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Ethereum PoW → PoS — Sustainability Analysis",
    page_icon="⛓️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Blockchain Sustainability Research Dashboard — Ethereum Merge Analysis",
    },
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Main background */
.stApp {
    background: linear-gradient(135deg, #0D1117 0%, #0E1F3D 100%);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0E1117 0%, #161B22 100%);
    border-right: 1px solid #21262D;
}

/* Cards */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #161B22, #1C2333);
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

/* Section headers */
h1 { color: #E6EDF3; }
h2 { color: #C9D1D9; border-bottom: 1px solid #21262D; padding-bottom: 8px; }
h3 { color: #8B949E; }

/* Info boxes */
.stInfo, .stWarning, .stSuccess {
    border-radius: 8px;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 500;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}

/* Highlight gradient text */
.gradient-text {
    background: linear-gradient(90deg, #627EEA, #F7931A);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.2rem;
}

.merge-badge {
    background: linear-gradient(135deg, #FF4500, #FF6347);
    color: white;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}

.pow-badge {
    background: linear-gradient(135deg, #F7931A, #FFB347);
    color: #0D1117;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}

.pos-badge {
    background: linear-gradient(135deg, #627EEA, #8BA4FF);
    color: white;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar navigation ────────────────────────────────────────────────────────
PAGES = {
    "🏠  Overview":              "pages/01_overview.py",
    "⟠  Ethereum":              "pages/02_ethereum.py",
    "₿  Bitcoin":               "pages/03_bitcoin.py",
    "📊  Correlation Analysis":  "pages/04_correlation.py",
    "📈  Trend Analysis":        "pages/05_trends.py",
    "🔮  ARIMA Forecast":        "pages/06_arima.py",
    "🔄  Counterfactual PoW":   "pages/07_counterfactual.py",
    "⚖️  PoW vs PoS":           "pages/08_pow_vs_pos.py",
    "📋  Methodology":           "pages/09_methodology.py",
    "📚  Data Sources":          "pages/10_data_sources.py",
    "🔬  Research Proof":        "pages/11_proof.py",
}

with st.sidebar:
    st.markdown('<p class="gradient-text">BlockChain<br>Sustainability</p>', unsafe_allow_html=True)
    st.markdown("**Consensus at a Turning Point**")
    st.markdown("*Ethereum's 2022 PoW → PoS Migration*")
    st.divider()
    page = st.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    st.markdown(
        "**Ethereum Merge:** Sep 15, 2022 "
        '<span class="merge-badge">⚡ Historic</span>',
        unsafe_allow_html=True,
    )
    st.caption("Data: Coin Metrics · Blockchain.com · Digiconomist")

# ── Load the selected page ────────────────────────────────────────────────────
page_file = Path(__file__).parent / PAGES[page].replace("pages/", "pages/")
if page_file.exists():
    with open(page_file, encoding="utf-8") as f:
        exec(compile(f.read(), str(page_file), "exec"), {"__file__": str(page_file)})
else:
    st.error(f"Page not found: {page_file}")
