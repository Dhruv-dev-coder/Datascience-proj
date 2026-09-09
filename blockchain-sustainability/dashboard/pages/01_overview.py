"""PAGE 1 — Overview"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

st.title("⛓️ Consensus at a Turning Point")
st.markdown("### Analyzing Ethereum's 2022 Migration from Proof-of-Work to Proof-of-Stake")
st.divider()

col1, col2, col3 = st.columns(3)
col1.metric("Ethereum Merge Date", "Sep 15, 2022", "PoW → PoS")
col2.metric("Energy Reduction (Est.)", "~99.95%", "post-Merge")
col3.metric("Research Period", "2017 – 2024", "7 years of data")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📖 Research Question", "🔬 Methodology", "⛏️ PoW vs PoS", "🗺️ Project Map"])

with tab1:
    st.subheader("Central Research Question")
    st.info(
        "**Was Ethereum's transition from Proof-of-Work to Proof-of-Stake "
        "environmentally imperative and strategically sustainable?**"
    )
    st.markdown("""
    This software project computationally implements the research methodology of the thesis:
    
    > *"Consensus at a Turning Point: Analyzing Ethereum's 2022 Migration From PoW to PoS"*
    
    The project collects real blockchain metrics (transaction counts, hash rates, energy estimates),
    applies statistical analysis, builds ARIMA forecasting models, and generates a counterfactual
    "what-if" scenario where Ethereum had never migrated to PoS.
    
    #### Research Sub-Questions
    1. How strongly was Ethereum's **energy consumption associated with hash rate** during PoW?
    2. How strongly was energy consumption associated with **transaction activity**?
    3. What changed in Ethereum's energy profile **after the Merge**?
    4. How does Ethereum compare to **Bitcoin's continuing PoW** model?
    5. What does a **model-based counterfactual** suggest about a hypothetical continued-PoW Ethereum?
    
    #### Important Caveats
    - Energy consumption is **estimated**, not directly measured on-chain.
    - Correlation results are **statistical associations**, not causal proof.
    - The counterfactual forecast is a **model-based hypothetical** — not a factual reconstruction.
    """)

with tab2:
    st.subheader("Project Methodology")
    st.markdown("""
    | Step | Component | Tool |
    |------|-----------|------|
    | 1 | Data Ingestion | Coin Metrics API, Blockchain.com API, Digiconomist |
    | 2 | Database | PostgreSQL + SQLAlchemy ORM |
    | 3 | Preprocessing | Custom cleaning pipeline (gap filling, outlier detection) |
    | 4 | EDA | Plotly interactive charts |
    | 5 | Correlation Analysis | Pearson + Spearman, p-values |
    | 6 | Trend Analysis | Pre/post-Merge segmentation |
    | 7 | ARIMA Forecasting | Statsmodels ARIMA(5,1,2) + auto-order |
    | 8 | Counterfactual | PoW-era training → post-Merge projection |
    | 9 | Dashboard | Streamlit 10-page interactive app |
    
    #### Metric Definitions
    - **Transaction Count**: Number of confirmed blockchain transactions per day
    - **Hash Rate**: Computational power used by PoW miners (TH/s for ETH, EH/s for BTC)
    - **Energy Consumption**: Estimated electricity usage (TWh/year) — derived from hash rate × assumed hardware efficiency
    """)

with tab3:
    st.subheader("Proof-of-Work vs Proof-of-Stake")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div style="background: linear-gradient(135deg,#1a1200,#2a1f00); border: 1px solid #F7931A; 
                    border-radius: 12px; padding: 20px;">
        <h4 style="color:#F7931A">⛏️ Proof-of-Work (PoW)</h4>
        
        **Used by:** Bitcoin (ongoing), Ethereum (until Sep 2022)
        
        **Block Production:** Miners solve cryptographic puzzles  
        **Resource:** Computational hardware + electricity  
        **Security:** Requires majority of hash rate to attack  
        **Energy:** High — scales with hash rate  
        **Scalability:** Limited by block time and size  
        
        **Environmental concern:** Energy consumption scales with network security budget
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div style="background: linear-gradient(135deg,#00122a,#001f45); border: 1px solid #627EEA; 
                    border-radius: 12px; padding: 20px;">
        <h4 style="color:#627EEA">🪙 Proof-of-Stake (PoS)</h4>
        
        **Used by:** Ethereum (from Sep 2022 onward)
        
        **Block Production:** Validators stake ETH as collateral  
        **Resource:** Staked capital (not computation)  
        **Security:** Requires majority of staked ETH to attack  
        **Energy:** Very low — no mining computation needed  
        **Scalability:** Foundation for sharding and L2 scaling  
        
        **Environmental benefit:** Energy per transaction drops dramatically
        </div>
        """, unsafe_allow_html=True)

with tab4:
    st.subheader("Dashboard Navigation Map")
    st.markdown("""
    | Page | Content |
    |------|---------|
    | 🏠 Overview | Research context, PoW vs PoS primer |
    | ⟠ Ethereum | ETH metrics: transactions, hash rate, energy, Merge timeline |
    | ₿ Bitcoin | BTC metrics: transactions, hash rate, energy |
    | 📊 Correlation | Pearson/Spearman correlations, scatter plots, heatmap |
    | 📈 Trend Analysis | Pre/post-Merge comparison, rolling averages |
    | 🔮 ARIMA Forecast | Model fitting, evaluation metrics, future projection |
    | 🔄 Counterfactual | Hypothetical "no-Merge" PoW continuation forecast |
    | ⚖️ PoW vs PoS | Side-by-side sustainability comparison |
    | 📋 Methodology | Detailed technical documentation |
    | 📚 Data Sources | API sources, coverage, units, limitations |
    | **🔬 Research Proof** | **← START HERE: End-to-end analytical proof chain** |
    """)
