import streamlit as st
import pandas as pd
import plotly.express as px
from shared_config import style_plotly_dark, PLOT_COLORS

def render_modelwise_tab(market_data, period):
    # Header for Tractor Market
    st.markdown("""
    <div class="sec-head">
      <div class="sec-head-bar" style="background:#E31837;box-shadow:0 0 14px rgba(227,24,55,.45);"></div>
      <div class="sec-head-title">TRACTOR MODEL REVENUE MATRIX (FY """ + str(period) + """)</div>
      <div class="sec-head-badge">100% DYNAMIC · LIVE DATA</div>
    </div>""", unsafe_allow_html=True)

    all_models = []
    
    # List of target companies to ensure we capture the right competitors
    target_competitors = ["Mahindra", "Swaraj", "Escorts", "Kubota", "Sonalika", "TAFE", "John Deere"]

    for item in market_data:
        comp = item.get('company', 'Unknown')
        
        # Sirf relevant companies ka data process karein
        if any(c.lower() in comp.lower() for c in target_competitors):
            models_list = item.get('models', [])

            for row in models_list:
                try:
                    sales_cr = float(row.get("Sales", 0))
                    price_unit = float(row.get("Price", 0))
                    qty = int(row.get("Quantity", 0))
                except (ValueError, TypeError):
                    sales_cr, price_unit, qty = 0.0, 0.0, 0
                
                # Math Logic: Calculate missing values dynamically
                if sales_cr > 0 and qty > 0 and price_unit == 0:
                    price_unit = (sales_cr * 10000000) / qty
                elif sales_cr > 0 and price_unit > 0 and qty == 0:
                    qty = int((sales_cr * 10000000) / price_unit)
                elif price_unit > 0 and qty > 0 and sales_cr == 0:
                    sales_cr = (qty * price_unit) / 10000000

                model_name = str(row.get("Model", "")).strip()
                
                if model_name and model_name.lower() not in ["", "unknown"]:
                    all_models.append({
                        "Company": comp,
                        "Tractor Model": model_name,
                        "Units Sold": qty,
                        "Market Price (₹)": price_unit,
                        "Total Revenue (₹ Cr)": sales_cr
                    })

    df_mod = pd.DataFrame(all_models)

    if df_mod.empty:
        st.warning("⚠️ Scraper is searching for live Tractor model data. No hardcoded records used.")
    else:
        # STRICT PRIORITY: Mahindra & Swaraj at the top
        def set_priority(name):
            name = name.lower()
            if 'mahindra' in name: return 0
            if 'swaraj' in name: return 1
            return 2

        df_mod['priority'] = df_mod['Company'].apply(set_priority)
        df_mod = df_mod.sort_values(by=['priority', 'Total Revenue (₹ Cr)'], ascending=[True, False]).drop('priority', axis=1)

        # Formatting for Display
        df_display = df_mod.copy()
        df_display['Units Sold'] = df_display['Units Sold'].apply(lambda x: f"{x:,}" if x > 0 else "Live Fetching...")
        df_display['Market Price (₹)'] = df_display['Market Price (₹)'].apply(lambda x: f"₹ {x:,.0f}" if x > 0 else "Analyzing...")
        df_display['Total Revenue (₹ Cr)'] = df_display['Total Revenue (₹ Cr)'].apply(lambda x: f"₹ {x:,.2f} Cr")

        # Live Status Indicator
        st.markdown("""
        <div style="background:rgba(227,24,55,.05);border-left:4px solid #E31837;
             padding:10px 15px;margin-bottom:20px;font-family:monospace;font-size:12px;color:#eee;">
          <span style="color:#E31837;font-weight:bold;">● LIVE STATUS:</span> 
          Fetching tractor model-wise units and pricing for <b>Mahindra & Competitors</b>. 
          No manual data entry allowed.
        </div>""", unsafe_allow_html=True)

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

        # Charts Section
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown('<p style="color:#E31837; font-weight:bold; border-bottom:1px solid #333;">REVENUE BY TRACTOR MODEL</p>', unsafe_allow_html=True)
            fig_bar = px.bar(df_mod, x="Tractor Model", y="Total Revenue (₹ Cr)", color="Company",
                             color_discrete_map=PLOT_COLORS, text_auto='.1f')
            fig_bar.update_layout(xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(style_plotly_dark(fig_bar), use_container_width=True)

        with c2:
            st.markdown('<p style="color:#1FD8F0; font-weight:bold; border-bottom:1px solid #333;">COMPETITOR MARKET MIX</p>', unsafe_allow_html=True)
            fig_pie = px.sunburst(df_mod, path=["Company", "Tractor Model"], values="Total Revenue (₹ Cr)",
                                  color="Company", color_discrete_map=PLOT_COLORS)
            st.plotly_chart(style_plotly_dark(fig_pie), use_container_width=True)