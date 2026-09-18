# import streamlit as st
# import pandas as pd
# import requests
# import re
# import json
# import time
# from datetime import datetime
# import plotly.express as px

# # Import from your shared_config
# from Main.shared_config import (
#     get_groq_client, get_tavily_key, safe_json_parse, style_plotly_dark, ACCENT_MAP, PLOT_COLORS
# )

# def _hex_to_rgb(hex_color: str) -> str:
#     try:
#         hex_color = hex_color.lstrip('#')
#         r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
#         return f"{r},{g},{b}"
#     except:
#         return "255,92,10"

# # =========================================================
# # 🌐 1. DYNAMIC COMPANY DATA FETCH (100% ONLINE)
# # =========================================================
# @st.cache_data(ttl=3600, show_spinner=False)
# def fetch_company_data_dynamic(company: str, period: str):
#     start_year = int(period.split("-")[0].replace("FY ", "").strip())
#     target_year = start_year + 1
#     current_year = datetime.now().year
#     short_fy = f"FY{str(target_year)[-2:]}"

#     default_data = {
#         "company": company, "estimated_annual_cr": 0.0, "q1_cr": 0.0, "q2_cr": 0.0, "q3_cr": 0.0, "q4_cr": 0.0,
#         "units_annual": 0, "units_q1": 0, "units_q2": 0, "units_q3": 0, "units_q4": 0,
#         "growth_percent": "N/A", "source_url": "#", "data_source_type": "FADA / Live Web Fetch"
#     }

#     if start_year > current_year:
#         default_data["data_source_type"] = "Awaiting Data"
#         return default_data

#     search_term = company
#     if company == "Swaraj": search_term = "Swaraj Tractors"
#     elif company == "John Deere": search_term = "John Deere tractor India"
#     elif company == "TAFE": search_term = "TAFE Tractors"
#     elif company == "Mahindra": search_term = "Mahindra farm equipment tractor"
#     elif company == "Escorts Kubota": search_term = "Escorts Kubota agri machinery"
#     elif company == "Sonalika": search_term = "Sonalika International Tractors ITL" 

#     query = f"{search_term} tractor retail sales units India {start_year} {target_year} {short_fy} FADA"
#     tavily_text = ""

#     for attempt in range(4):
#         try:
#             tavily_resp = requests.post(
#                 "https://api.tavily.com/search",
#                 json={"api_key": get_tavily_key(), "query": query, "search_depth": "advanced", "max_results": 6},
#                 timeout=15
#             )
#             if tavily_resp.status_code == 200:
#                 data = tavily_resp.json()
#                 for res in data.get("results", []):
#                     tavily_text += res['content'] + " "
#                     if "sales" in res['url'].lower() or "fada" in res['url'].lower() or "auto" in res['url'].lower():
#                         default_data["source_url"] = res['url'] 
#                 if len(tavily_text) > 100:
#                     break 
#             time.sleep(0.1) 
#         except Exception:
#             time.sleep(0.1)

#     prompt = f"""
#     Extract ONLY the total tractor retail sales units in India for '{company}' in the financial year {start_year}-{target_year} ({short_fy}).
#     Use only official FADA or industry report numbers. DO NOT include car/auto sales.
#     Text: {tavily_text[:6000]}
#     Return ONLY JSON: {{"units_annual": 0, "growth_percent": "+0.0%"}}
#     If no clear number is found, set units_annual to 0. Do not invent data.
#     """
    
#     u_annual = 0
#     growth_val = "N/A"

#     for attempt in range(4):
#         try:
#             client = get_groq_client()
#             ai_res = client.chat.completions.create(
#                 messages=[{"role": "user", "content": prompt}],
#                 model="llama-3.3-70b-versatile",
#                 response_format={"type": "json_object"},
#                 temperature=0.0
#             )
            
#             ai_data = safe_json_parse(ai_res.choices[0].message.content)
#             u_annual = int(ai_data.get("units_annual", 0))
#             growth_val = str(ai_data.get("growth_percent", "N/A"))
            
#             if u_annual > 0:
#                 if growth_val != "N/A" and not growth_val.startswith(("+", "-")) and growth_val[0].isdigit():
#                     growth_val = "+" + growth_val
#                 break
#             time.sleep(0.1)
#         except Exception:
#             time.sleep(0.1)

#     if u_annual == 0 and tavily_text:
#         patterns = [r'(\d{1,3}(?:,\d{3})+|\d{4,7})\s*(?:tractors|units)', r'(\d+(?:\.\d+)?)\s*lakh\s*(?:tractors|units)']
#         for pat in patterns:
#             match = re.search(pat, tavily_text, re.IGNORECASE)
#             if match:
#                 val_str = match.group(1).replace(',', '')
#                 if 'lakh' in pat: u_annual = int(float(val_str) * 100000)
#                 else: u_annual = int(val_str)
#                 break

#     if u_annual > 600000: u_annual = 0

#     default_data["units_annual"] = u_annual
#     default_data["growth_percent"] = growth_val if growth_val != "N/A" else "N/A"
#     default_data["estimated_annual_cr"] = u_annual * 0.065 

#     ann_rev = default_data["estimated_annual_cr"]
#     ann_u = default_data["units_annual"]
    
#     default_data["q1_cr"], default_data["q2_cr"], default_data["q3_cr"], default_data["q4_cr"] = ann_rev*0.20, ann_rev*0.25, ann_rev*0.35, ann_rev*0.20
#     default_data["q4_is_est"] = True

#     default_data["units_q1"], default_data["units_q2"], default_data["units_q3"], default_data["units_q4"] = int(ann_u*0.20), int(ann_u*0.25), int(ann_u*0.35), int(ann_u*0.20)

#     default_data["monthly_avg_cr"] = ann_rev / 12 if ann_rev else 0
#     default_data["monthly_avg_units"] = ann_u / 12 if ann_u else 0

#     return default_data

# # =========================================================
# # 📍 2. REGIONAL SALES FETCH (CITY/DISTRICT WISE)
# # =========================================================
# @st.cache_data(ttl=3600, show_spinner=False)
# def get_location_sales(state="All", district="All", city="All", year="2026"):
    
#     loc_parts = []
#     if state != "All": loc_parts.append(state)
#     if district != "All": loc_parts.append(district)
#     if city != "All": loc_parts.append(city)
#     location_str = ", ".join(loc_parts)

#     # Realistic proxy base units if API fails for small cities
#     base_units = 900000
#     if city != "All": base_units = 750
#     elif district != "All": base_units = 4500
#     elif state != "All": base_units = 55000

#     query = f"tractor registration sales units {year} in {location_str} brand-wise Mahindra TAFE Sonalika Escorts John Deere"
#     tavily_text = ""

#     for attempt in range(4):
#         try:
#             resp = requests.post(
#                 "https://api.tavily.com/search",
#                 json={"api_key": get_tavily_key(), "query": query, "search_depth": "advanced", "max_results": 5},
#                 timeout=15
#             )
#             if resp.status_code == 200:
#                 for res in resp.json().get("results", []):
#                     tavily_text += res['content'] + " "
#                 if len(tavily_text) > 50:
#                     break
#             time.sleep(0.1)
#         except Exception:
#             time.sleep(0.1)

#     prompt = f"""
#     Extract exact tractor retail units sold for each brand in location: {location_str} for year {year}.
#     Brands: Mahindra, TAFE, Sonalika, Escorts Kubota, John Deere.
#     Return JSON ONLY: {{"sales_data": [{{"brand": "Mahindra", "units": 1000}}], "summary": "short insight"}}
#     If no exact numbers are found, output units as 0. Do not invent.
#     Text: {tavily_text[:5000]}
#     """
    
#     final_data = []
#     summary = "Data fetched dynamically."

#     for attempt in range(4):
#         try:
#             client = get_groq_client()
#             ai_res = client.chat.completions.create(
#                 messages=[{"role": "user", "content": prompt}],
#                 model="llama-3.3-70b-versatile",
#                 response_format={"type": "json_object"},
#                 temperature=0.0
#             )
#             data = safe_json_parse(ai_res.choices[0].message.content)
#             if data.get("sales_data") and data["sales_data"][0].get("units", 0) > 0:
#                 final_data = data["sales_data"]
#                 summary = data.get("summary", f"Official Vahan extraction for {location_str}.")
#                 break
#             time.sleep(0.1)
#         except Exception:
#             time.sleep(0.1)

#     all_brands = ["Mahindra", "TAFE", "Sonalika", "Escorts Kubota", "John Deere"]
#     market_shares = {"Mahindra": 41.0, "TAFE": 18.0, "Sonalika": 12.5, "Escorts Kubota": 10.0, "John Deere": 8.5}

#     # If AI returned 0s (common for small cities), use statistical local proxy
#     if not final_data or sum([item.get("units", 0) for item in final_data]) == 0:
#         final_data = []
#         for brand in all_brands:
#             final_data.append({"brand": brand, "units": int(base_units * (market_shares[brand] / 100))})
#         summary = f"Exact FADA figures for {location_str} are unpublished. Displaying highly accurate statistical proxy estimates based on market ratio."

#     clean_data = []
#     for b in all_brands:
#         found = next((item for item in final_data if item.get("brand", "").lower() == b.lower() or b.lower() in item.get("brand", "").lower()), None)
#         units = int(found.get("units", 0)) if found else 0
#         clean_data.append({"brand": b, "units": units})

#     total = sum(d["units"] for d in clean_data)
#     for d in clean_data:
#         d["market_share"] = f"{(d['units'] / total * 100):.1f}%" if total > 0 else "N/A"

#     return {
#         "metadata": {"state": state, "district": district, "city": city, "query_location": location_str},
#         "sales_data": clean_data,
#         "summary": summary,
#         "total_units": total
#     }

# # =========================================================
# # 🔄 MASTER FETCH FUNCTION
# # =========================================================
# ALL_COMPANIES = ["Mahindra", "Escorts Kubota", "Sonalika", "TAFE", "Swaraj", "John Deere"]

# @st.cache_data(ttl=3600, show_spinner=False)
# def fetch_all_sales(period: str):
#     results = []
#     for co in ALL_COMPANIES:
#         results.append(fetch_company_data_dynamic(co, period))
#     return results

# # =========================================================
# # 🖥️ UI RENDERER (DASHBOARD)
# # =========================================================
# def render_sales_tab(market_data, period, selected_company):
#     clean_fy = period.replace("FY ", "")

#     if "sales_spotlight" not in st.session_state:
#         st.session_state.sales_spotlight = "Mahindra"

#     spotlight_company = st.session_state.sales_spotlight
#     if spotlight_company not in [d['company'] for d in market_data]:
#         spotlight_company = market_data[0]['company'] if market_data else "Mahindra"

#     st.markdown(f"""
#     <div class="sec-head">
#       <div class="sec-head-bar" style="background:#FF5C0A;"></div>
#       <div class="sec-head-title">OFFICIAL TRACTOR SALES DATA — {clean_fy}</div>
#       <div class="sec-head-badge">100% DYNAMIC FADA ENGINE</div>
#     </div>""", unsafe_allow_html=True)

#     spot = next((x for x in market_data if x['company'] == spotlight_company), market_data[0])
#     accent, glow = ACCENT_MAP.get(spot['company'], ("#FF5C0A", "rgba(255,92,10,.18)"))
#     g_sp = str(spot['growth_percent'])

#     if "+" in g_sp:
#         g_arrow, g_color = f"▲ {g_sp}", "#0FE88A"
#     elif "-" in g_sp:
#         g_arrow, g_color = f"▼ {g_sp}", "#FF2D55"
#     else:
#         g_arrow, g_color = g_sp, "#7b8db5"

#     st.markdown(f"""
#     <div style="background:linear-gradient(135deg,rgba({_hex_to_rgb(accent)},.13) 0%,rgba({_hex_to_rgb(accent)},.04) 100%);
#          border:1.5px solid rgba({_hex_to_rgb(accent)},.45);border-radius:12px;padding:18px 26px;margin-bottom:22px;
#          display:flex;align-items:center;gap:28px;">
#       <div style="flex-shrink:0;">
#         <div style="font-family:'Bebas Neue',sans-serif;font-size:28px;letter-spacing:4px;color:{accent};">{spot['company'].upper()}</div>
#         <div style="margin-top:6px;">
#             <a href="{spot['source_url']}" target="_blank" style="font-family:'JetBrains Mono',monospace;font-size:9px;color:{accent};border:1px solid {accent}55;padding:2px 6px;border-radius:4px;text-decoration:none;">🔗 SOURCE</a>
#         </div>
#       </div>
#       <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
#       <div>
#         <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">Annual Revenue (Est)</div>
#         <div style="font-size:34px;font-family:'Bebas Neue';color:#fff;">₹{spot['estimated_annual_cr']:,.2f} <span style="font-size:18px;">Cr</span></div>
#       </div>
#       <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
#       <div>
#         <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">Tractors Sold (Retail)</div>
#         <div style="font-size:34px;font-family:'Bebas Neue';color:#fff;">{spot['units_annual']:,.0f} <span style="font-size:18px;">Units</span></div>
#       </div>
#       <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
#       <div>
#         <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">YoY Growth</div>
#         <div style="font-size:28px;font-family:'Bebas Neue';color:{g_color};">{g_arrow}</div>
#       </div>
#     </div>""", unsafe_allow_html=True)

#     kpi_cols = st.columns(len(market_data))
#     for i, res in enumerate(market_data):
#         with kpi_cols[i]:
#             card_accent, card_glow = ACCENT_MAP.get(res['company'], ("#FF5C0A","rgba(255,92,10,.18)"))
#             mp_class = 'kpi-mahindra' if res['company'] == spotlight_company else ''
            
#             if st.button("", key=f"kpi_card_{i}_{res['company']}", help=f"Click to focus on {res['company']}"):
#                 st.session_state.sales_spotlight = res['company']
#                 st.rerun()

#             st.markdown(f"""
#             <div class="kpi-card {mp_class}" style="--_accent:{card_accent};--_glow:{card_glow};cursor:pointer;" onclick="document.querySelector('[data-testid=\"stButton\"]:has([key=\"kpi_card_{i}_{res['company']}\"])').click()">
#               <div>
#                 <div class="kpi-lbl">Revenue & Units &#183; {period}</div>
#                 <div class="kpi-company-name">{res['company']}</div>
#                 <div class="kpi-val">₹{res['estimated_annual_cr']:,.2f}<span> Cr</span></div>
#               </div>
#               <div style="margin-top:8px; display:flex; flex-direction:column; gap:2px;">
#                  <span style="font-size:8px;color:{'#FF2D55' if res['units_annual']==0 else '#0FE88A'};font-weight:bold;">{res['data_source_type']}</span>
#               </div>
#             </div>""", unsafe_allow_html=True)

#     st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

#     # TABLES
#     st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#1FD8F0;"></div>
#       <div class="sec-head-title">TABLE 1: ESTIMATED TRACTOR REVENUE (₹ CRORES)</div></div>""", unsafe_allow_html=True)

#     rev_dict = [{
#         "Company": item["company"],
#         "Monthly Avg": f"₹ {item['monthly_avg_cr']:,.2f}",
#         "Q1": f"₹ {item['q1_cr']:,.2f}",
#         "Q2": f"₹ {item['q2_cr']:,.2f}",
#         "Q3": f"₹ {item['q3_cr']:,.2f}",
#         "Q4": f"₹ {item['q4_cr']:,.2f}",
#         "Annual Total": f"₹ {item['estimated_annual_cr']:,.2f}"
#     } for item in market_data]
#     st.dataframe(pd.DataFrame(rev_dict), use_container_width=True, hide_index=True)

#     st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

#     st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#9D6FFF;"></div>
#       <div class="sec-head-title">TABLE 2: TRACTOR UNITS SOLD (FADA/RETAIL)</div></div>""", unsafe_allow_html=True)

#     units_dict = [{
#         "Company": item["company"],
#         "Monthly Avg": f"{item['monthly_avg_units']:,.0f}",
#         "Q1": f"{item['units_q1']:,.0f}",
#         "Q2": f"{item['units_q2']:,.0f}",
#         "Q3": f"{item['units_q3']:,.0f}",
#         "Q4": f"{item['units_q4']:,.0f}",
#         "Annual Total": f"{item['units_annual']:,.0f}",
#         "YoY Growth": item["growth_percent"]
#     } for item in market_data]
#     st.dataframe(pd.DataFrame(units_dict), use_container_width=True, hide_index=True)

#     st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

#     # CHARTS (ALL 3 RESTORED)
#     st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#0FE88A;"></div>
#       <div class="sec-head-title">1. QUARTERLY REVENUE TRAJECTORY (LINE CHART)</div></div>""", unsafe_allow_html=True)
    
#     line_data = []
#     for item in market_data:
#         line_data.extend([
#             {"Company": item["company"], "Quarter": "Q1", "Revenue (₹ Cr)": item["q1_cr"]},
#             {"Company": item["company"], "Quarter": "Q2", "Revenue (₹ Cr)": item["q2_cr"]},
#             {"Company": item["company"], "Quarter": "Q3", "Revenue (₹ Cr)": item["q3_cr"]},
#             {"Company": item["company"], "Quarter": "Q4", "Revenue (₹ Cr)": item["q4_cr"]},
#         ])
#     df_line = pd.DataFrame(line_data)
#     if not df_line.empty and df_line["Revenue (₹ Cr)"].sum() > 0:
#         fig_line = px.line(df_line, x="Quarter", y="Revenue (₹ Cr)", color="Company", color_discrete_map=PLOT_COLORS, markers=True)
#         st.plotly_chart(style_plotly_dark(fig_line), use_container_width=True)

#     st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

#     # RESTORED DONUT CHART
#     st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#FF2D55;"></div>
#       <div class="sec-head-title">2. REVENUE MARKET SHARE (DONUT CHART)</div></div>""", unsafe_allow_html=True)
    
#     pie_df = pd.DataFrame(market_data)
#     if pie_df["estimated_annual_cr"].sum() > 0:
#         fig_pie = px.pie(pie_df, values="estimated_annual_cr", names="company", hole=0.55, color="company", color_discrete_map=PLOT_COLORS)
#         fig_pie.update_traces(textinfo='percent+label', textposition='inside', hovertemplate="<b>%{label}</b><br>₹%{value:,.2f} Cr<br>%{percent:.1%}")
#         fig_pie.update_layout(height=400, showlegend=True, margin=dict(t=20, b=20))
#         st.plotly_chart(style_plotly_dark(fig_pie), use_container_width=True)

#     st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

#     # RESTORED BAR CHART
#     st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#3B82F6;"></div>
#       <div class="sec-head-title">3. TOTAL UNITS SOLD COMPARISON (BAR CHART)</div></div>""", unsafe_allow_html=True)
    
#     if pie_df["units_annual"].sum() > 0:
#         fig_units = px.bar(pie_df, x="company", y="units_annual", color="company", color_discrete_map=PLOT_COLORS, text="units_annual")
#         fig_units.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
#         fig_units.update_layout(height=400, showlegend=False, yaxis_title="Total Units Sold", xaxis_title="Company", margin=dict(t=20, b=20))
#         st.plotly_chart(style_plotly_dark(fig_units), use_container_width=True)


#     # =========================================================
#     # 🌍 3. REGIONAL REGISTRATION INTELLIGENCE (NEW LOGIC)
#     # =========================================================
#     st.markdown("---")
#     st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#EAB308;"></div>
#       <div class="sec-head-title">REGIONAL REGISTRATION INTELLIGENCE (VAHAN)</div>
#       <div class="sec-head-badge">AI LOCATION FILTER</div></div>""", unsafe_allow_html=True)

#     col_s, col_d, col_c, col_btn = st.columns([1, 1, 1, 1])
#     with col_s:
#         state_list = ["All", "Punjab", "Haryana", "Maharashtra", "Uttar Pradesh", "Madhya Pradesh", "Gujarat", "Rajasthan", "Karnataka"]
#         state_sel = st.selectbox("State", state_list)
#     with col_d:
#         district_sel = st.text_input("District", value="All")
#     with col_c:
#         city_sel = st.text_input("City", value="All")
#     with col_btn:
#         st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 
#         fetch_regional = st.button("Fetch Regional Data", use_container_width=True)

#     if fetch_regional:
#         # SUPER FAST LOGIC FOR "ALL"
#         if state_sel == "All" and district_sel == "All" and city_sel == "All":
#             st.markdown(f"#### 📍 Sales Snapshot: Across India (National Aggregate)")
#             st.markdown(f"""
#             <div style="background:rgba(234, 179, 8, 0.1); border-left: 3px solid #EAB308; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
#                 <p style="margin:0; color:#fff;">💡 <b>AI Insight:</b> Displaying consolidated national unit sales data for {clean_fy}.</p>
#             </div>
#             """, unsafe_allow_html=True)
            
#             national_df = pd.DataFrame([{"Brand": item["company"], "Units Registered": item["units_annual"]} for item in market_data])
#             total_national = national_df["Units Registered"].sum()
#             national_df["Market Share"] = (national_df["Units Registered"] / total_national * 100).apply(lambda x: f"{x:.1f}%") if total_national > 0 else "N/A"
#             st.markdown(f"<p style='color: #0FE88A; font-weight: bold;'>Total Indian Market Size (Tracked): {total_national:,.0f} Units</p>", unsafe_allow_html=True)
#             st.dataframe(national_df, use_container_width=True, hide_index=True)
            
#         else:
#             with st.spinner(f"Scraping local Vahan data for {state_sel} > {district_sel} > {city_sel}..."):
#                 target_yr = period.split("-")[0].replace("FY ", "").strip()
#                 reg_data = get_location_sales(state=state_sel, district=district_sel, city=city_sel, year=target_yr)
                
#                 st.markdown(f"#### 📍 Sales Snapshot: {reg_data['metadata']['query_location']}")
                
#                 st.markdown(f"""
#                 <div style="background:rgba(234, 179, 8, 0.1); border-left: 3px solid #EAB308; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
#                     <p style="margin:0; color:#fff;">💡 <b>AI Insight:</b> {reg_data['summary']}</p>
#                 </div>
#                 """, unsafe_allow_html=True)
                
#                 reg_df = pd.DataFrame(reg_data['sales_data'])
#                 if not reg_df.empty and 'units' in reg_df.columns:
#                     total_loc_units = reg_data['total_units']
#                     st.markdown(f"<p style='color: #0FE88A; font-weight: bold;'>Total Units Sold in this Region: {total_loc_units:,.0f}</p>", unsafe_allow_html=True)
                    
#                     reg_df.rename(columns={"brand": "Brand", "units": "Units Registered", "market_share": "Market Share"}, inplace=True)
#                     st.dataframe(reg_df, use_container_width=True, hide_index=True)


import streamlit as st
import pandas as pd
import requests
import re
import json
import time
from datetime import datetime
import plotly.express as px

# Import from your shared_config
from Main.shared_config import (
    get_groq_client, get_tavily_key, safe_json_parse, style_plotly_dark, ACCENT_MAP, PLOT_COLORS
)

def _hex_to_rgb(hex_color: str) -> str:
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"{r},{g},{b}"
    except:
        return "255,92,10"

# =========================================================
# 🌐 1. DYNAMIC COMPANY DATA FETCH (100% ONLINE, WORLDWIDE)
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_data_dynamic(company: str, period: str):
    start_year = int(period.split("-")[0].replace("FY ", "").strip())
    target_year = start_year + 1
    current_year = datetime.now().year
    short_fy = f"FY{str(target_year)[-2:]}"

    default_data = {
        "company": company, "estimated_annual_cr": 0.0, "q1_cr": 0.0, "q2_cr": 0.0, "q3_cr": 0.0, "q4_cr": 0.0,
        "units_annual": 0, "units_q1": 0, "units_q2": 0, "units_q3": 0, "units_q4": 0,
        "growth_percent": "N/A", "source_url": "#", "data_source_type": "Global Industry Report / Live Web Fetch"
    }

    if start_year > current_year:
        default_data["data_source_type"] = "Awaiting Data"
        return default_data

    search_term = company
    if company == "Swaraj": search_term = "Swaraj Tractors"
    elif company == "John Deere": search_term = "John Deere tractor global sales"
    elif company == "TAFE": search_term = "TAFE Tractors"
    elif company == "Mahindra": search_term = "Mahindra farm equipment tractor"
    elif company == "Escorts Kubota": search_term = "Escorts Kubota agri machinery"
    elif company == "Sonalika": search_term = "Sonalika International Tractors ITL"

    # NOTE: "India" removed from query — ab worldwide/global total sales dhoondhega
    query = f"{search_term} tractor global worldwide retail sales units {start_year} {target_year} {short_fy} annual report"
    tavily_text = ""

    for attempt in range(4):
        try:
            tavily_resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": get_tavily_key(), "query": query, "search_depth": "advanced", "max_results": 6},
                timeout=15
            )
            if tavily_resp.status_code == 200:
                data = tavily_resp.json()
                for res in data.get("results", []):
                    tavily_text += res['content'] + " "
                    if "sales" in res['url'].lower() or "report" in res['url'].lower() or "auto" in res['url'].lower():
                        default_data["source_url"] = res['url']
                if len(tavily_text) > 100:
                    break
            time.sleep(0.1)
        except Exception:
            time.sleep(0.1)

    prompt = f"""
    Extract ONLY the TOTAL WORLDWIDE (global, all countries combined) tractor retail sales units for '{company}' in the financial year {start_year}-{target_year} ({short_fy}).
    Use only official company annual reports, investor presentations, or credible industry sources. DO NOT include car/auto sales.
    If the source only gives a single country's number (e.g. only India or only USA), do NOT treat it as the global total — set units_annual to 0 instead.
    Text: {tavily_text[:6000]}
    Return ONLY JSON: {{"units_annual": 0, "growth_percent": "+0.0%"}}
    If no clear global number is found, set units_annual to 0. Do not invent data.
    """

    u_annual = 0
    growth_val = "N/A"

    for attempt in range(4):
        try:
            client = get_groq_client()
            ai_res = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.0
            )

            ai_data = safe_json_parse(ai_res.choices[0].message.content)
            u_annual = int(ai_data.get("units_annual", 0))
            growth_val = str(ai_data.get("growth_percent", "N/A"))

            if u_annual > 0:
                if growth_val != "N/A" and not growth_val.startswith(("+", "-")) and growth_val[0].isdigit():
                    growth_val = "+" + growth_val
                break
            time.sleep(0.1)
        except Exception:
            time.sleep(0.1)

    if u_annual == 0 and tavily_text:
        patterns = [r'(\d{1,3}(?:,\d{3})+|\d{4,7})\s*(?:tractors|units)', r'(\d+(?:\.\d+)?)\s*(?:million|lakh)\s*(?:tractors|units)']
        for pat in patterns:
            match = re.search(pat, tavily_text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(',', '')
                if 'million' in pat:
                    u_annual = int(float(val_str) * 1000000)
                elif 'lakh' in pat:
                    u_annual = int(float(val_str) * 100000)
                else:
                    u_annual = int(val_str)
                break

    # Global cap raised — worldwide totals for big players (e.g. John Deere, Mahindra) can run well above India-only caps
    if u_annual > 5000000: u_annual = 0

    default_data["units_annual"] = u_annual
    default_data["growth_percent"] = growth_val if growth_val != "N/A" else "N/A"
    default_data["estimated_annual_cr"] = u_annual * 0.065

    ann_rev = default_data["estimated_annual_cr"]
    ann_u = default_data["units_annual"]

    default_data["q1_cr"], default_data["q2_cr"], default_data["q3_cr"], default_data["q4_cr"] = ann_rev*0.20, ann_rev*0.25, ann_rev*0.35, ann_rev*0.20
    default_data["q4_is_est"] = True

    default_data["units_q1"], default_data["units_q2"], default_data["units_q3"], default_data["units_q4"] = int(ann_u*0.20), int(ann_u*0.25), int(ann_u*0.35), int(ann_u*0.20)

    default_data["monthly_avg_cr"] = ann_rev / 12 if ann_rev else 0
    default_data["monthly_avg_units"] = ann_u / 12 if ann_u else 0

    return default_data

# =========================================================
# 📍 2. REGIONAL SALES FETCH (COUNTRY / STATE / DISTRICT / CITY WISE)
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_location_sales(country="All", state="All", district="All", city="All", year="2026"):

    loc_parts = []
    if country != "All": loc_parts.append(country)
    if state != "All": loc_parts.append(state)
    if district != "All": loc_parts.append(district)
    if city != "All": loc_parts.append(city)
    location_str = ", ".join(loc_parts) if loc_parts else "Worldwide"

    # Realistic proxy base units if API fails for a given granularity.
    # Broader scope (whole world) -> bigger base; narrower (a single city) -> smaller base.
    if city != "All":
        base_units = 750
    elif district != "All":
        base_units = 4500
    elif state != "All":
        base_units = 55000
    elif country != "All":
        base_units = 900000
    else:
        base_units = 3000000  # Global / worldwide aggregate proxy

    query = f"tractor registration sales units {year} in {location_str} brand-wise Mahindra TAFE Sonalika Escorts John Deere Kubota New Holland Case IH"
    tavily_text = ""

    for attempt in range(4):
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": get_tavily_key(), "query": query, "search_depth": "advanced", "max_results": 5},
                timeout=15
            )
            if resp.status_code == 200:
                for res in resp.json().get("results", []):
                    tavily_text += res['content'] + " "
                if len(tavily_text) > 50:
                    break
            time.sleep(0.1)
        except Exception:
            time.sleep(0.1)

    prompt = f"""
    Extract exact tractor retail units sold for each brand in location: {location_str} for year {year}.
    Brands: Mahindra, TAFE, Sonalika, Escorts Kubota, John Deere.
    Return JSON ONLY: {{"sales_data": [{{"brand": "Mahindra", "units": 1000}}], "summary": "short insight"}}
    If no exact numbers are found, output units as 0. Do not invent.
    Text: {tavily_text[:5000]}
    """

    final_data = []
    summary = "Data fetched dynamically."

    for attempt in range(4):
        try:
            client = get_groq_client()
            ai_res = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.0
            )
            data = safe_json_parse(ai_res.choices[0].message.content)
            if data.get("sales_data") and data["sales_data"][0].get("units", 0) > 0:
                final_data = data["sales_data"]
                summary = data.get("summary", f"Official extraction for {location_str}.")
                break
            time.sleep(0.1)
        except Exception:
            time.sleep(0.1)

    all_brands = ["Mahindra", "TAFE", "Sonalika", "Escorts Kubota", "John Deere"]
    market_shares = {"Mahindra": 41.0, "TAFE": 18.0, "Sonalika": 12.5, "Escorts Kubota": 10.0, "John Deere": 8.5}

    # If AI returned 0s (common for small cities / less-documented regions), use statistical local proxy
    if not final_data or sum([item.get("units", 0) for item in final_data]) == 0:
        final_data = []
        for brand in all_brands:
            final_data.append({"brand": brand, "units": int(base_units * (market_shares[brand] / 100))})
        summary = f"Exact figures for {location_str} are unpublished. Displaying statistical proxy estimates based on approximate market ratio (reference distribution)."

    clean_data = []
    for b in all_brands:
        found = next((item for item in final_data if item.get("brand", "").lower() == b.lower() or b.lower() in item.get("brand", "").lower()), None)
        units = int(found.get("units", 0)) if found else 0
        clean_data.append({"brand": b, "units": units})

    total = sum(d["units"] for d in clean_data)
    for d in clean_data:
        d["market_share"] = f"{(d['units'] / total * 100):.1f}%" if total > 0 else "N/A"

    return {
        "metadata": {"country": country, "state": state, "district": district, "city": city, "query_location": location_str},
        "sales_data": clean_data,
        "summary": summary,
        "total_units": total
    }

# =========================================================
# 🔄 MASTER FETCH FUNCTION
# =========================================================
ALL_COMPANIES = ["Mahindra", "Escorts Kubota", "Sonalika", "TAFE", "Swaraj", "John Deere"]

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_sales(period: str):
    results = []
    for co in ALL_COMPANIES:
        results.append(fetch_company_data_dynamic(co, period))
    return results

# =========================================================
# 🖥️ UI RENDERER (DASHBOARD)
# =========================================================
def render_sales_tab(market_data, period, selected_company):
    clean_fy = period.replace("FY ", "")

    if "sales_spotlight" not in st.session_state:
        st.session_state.sales_spotlight = "Mahindra"

    spotlight_company = st.session_state.sales_spotlight
    if spotlight_company not in [d['company'] for d in market_data]:
        spotlight_company = market_data[0]['company'] if market_data else "Mahindra"

    st.markdown(f"""
    <div class="sec-head">
      <div class="sec-head-bar" style="background:#FF5C0A;"></div>
      <div class="sec-head-title">GLOBAL TRACTOR SALES DATA — {clean_fy}</div>
      <div class="sec-head-badge">100% DYNAMIC WORLDWIDE SALES ENGINE</div>
    </div>""", unsafe_allow_html=True)

    spot = next((x for x in market_data if x['company'] == spotlight_company), market_data[0])
    accent, glow = ACCENT_MAP.get(spot['company'], ("#FF5C0A", "rgba(255,92,10,.18)"))
    g_sp = str(spot['growth_percent'])

    if "+" in g_sp:
        g_arrow, g_color = f"▲ {g_sp}", "#0FE88A"
    elif "-" in g_sp:
        g_arrow, g_color = f"▼ {g_sp}", "#FF2D55"
    else:
        g_arrow, g_color = g_sp, "#7b8db5"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba({_hex_to_rgb(accent)},.13) 0%,rgba({_hex_to_rgb(accent)},.04) 100%);
         border:1.5px solid rgba({_hex_to_rgb(accent)},.45);border-radius:12px;padding:18px 26px;margin-bottom:22px;
         display:flex;align-items:center;gap:28px;">
      <div style="flex-shrink:0;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:28px;letter-spacing:4px;color:{accent};">{spot['company'].upper()}</div>
        <div style="margin-top:6px;">
            <a href="{spot['source_url']}" target="_blank" style="font-family:'JetBrains Mono',monospace;font-size:9px;color:{accent};border:1px solid {accent}55;padding:2px 6px;border-radius:4px;text-decoration:none;">🔗 SOURCE</a>
        </div>
      </div>
      <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
      <div>
        <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">Annual Revenue (Est, Global)</div>
        <div style="font-size:34px;font-family:'Bebas Neue';color:#fff;">₹{spot['estimated_annual_cr']:,.2f} <span style="font-size:18px;">Cr</span></div>
      </div>
      <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
      <div>
        <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">Tractors Sold (Global Retail)</div>
        <div style="font-size:34px;font-family:'Bebas Neue';color:#fff;">{spot['units_annual']:,.0f} <span style="font-size:18px;">Units</span></div>
      </div>
      <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
      <div>
        <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">YoY Growth</div>
        <div style="font-size:28px;font-family:'Bebas Neue';color:{g_color};">{g_arrow}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    kpi_cols = st.columns(len(market_data))
    for i, res in enumerate(market_data):
        with kpi_cols[i]:
            card_accent, card_glow = ACCENT_MAP.get(res['company'], ("#FF5C0A","rgba(255,92,10,.18)"))
            mp_class = 'kpi-mahindra' if res['company'] == spotlight_company else ''

            if st.button("", key=f"kpi_card_{i}_{res['company']}", help=f"Click to focus on {res['company']}"):
                st.session_state.sales_spotlight = res['company']
                st.rerun()

            st.markdown(f"""
            <div class="kpi-card {mp_class}" style="--_accent:{card_accent};--_glow:{card_glow};cursor:pointer;" onclick="document.querySelector('[data-testid=\"stButton\"]:has([key=\"kpi_card_{i}_{res['company']}\"])').click()">
              <div>
                <div class="kpi-lbl">Global Revenue & Units &#183; {period}</div>
                <div class="kpi-company-name">{res['company']}</div>
                <div class="kpi-val">₹{res['estimated_annual_cr']:,.2f}<span> Cr</span></div>
              </div>
              <div style="margin-top:8px; display:flex; flex-direction:column; gap:2px;">
                 <span style="font-size:8px;color:{'#FF2D55' if res['units_annual']==0 else '#0FE88A'};font-weight:bold;">{res['data_source_type']}</span>
              </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # TABLES
    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#1FD8F0;"></div>
      <div class="sec-head-title">TABLE 1: ESTIMATED GLOBAL TRACTOR REVENUE (₹ CRORES)</div></div>""", unsafe_allow_html=True)

    rev_dict = [{
        "Company": item["company"],
        "Monthly Avg": f"₹ {item['monthly_avg_cr']:,.2f}",
        "Q1": f"₹ {item['q1_cr']:,.2f}",
        "Q2": f"₹ {item['q2_cr']:,.2f}",
        "Q3": f"₹ {item['q3_cr']:,.2f}",
        "Q4": f"₹ {item['q4_cr']:,.2f}",
        "Annual Total": f"₹ {item['estimated_annual_cr']:,.2f}"
    } for item in market_data]
    rev_df = pd.DataFrame(rev_dict)
    st.dataframe(rev_df, use_container_width=True, hide_index=True)
    total_global_rev = sum(item['estimated_annual_cr'] for item in market_data)
    st.markdown(f"<p style='color:#0FE88A;font-weight:bold;'>🌍 Total Worldwide Revenue (All Companies): ₹ {total_global_rev:,.2f} Cr</p>", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#9D6FFF;"></div>
      <div class="sec-head-title">TABLE 2: TRACTOR UNITS SOLD (GLOBAL RETAIL)</div></div>""", unsafe_allow_html=True)

    units_dict = [{
        "Company": item["company"],
        "Monthly Avg": f"{item['monthly_avg_units']:,.0f}",
        "Q1": f"{item['units_q1']:,.0f}",
        "Q2": f"{item['units_q2']:,.0f}",
        "Q3": f"{item['units_q3']:,.0f}",
        "Q4": f"{item['units_q4']:,.0f}",
        "Annual Total": f"{item['units_annual']:,.0f}",
        "YoY Growth": item["growth_percent"]
    } for item in market_data]
    st.dataframe(pd.DataFrame(units_dict), use_container_width=True, hide_index=True)
    total_global_units = sum(item['units_annual'] for item in market_data)
    st.markdown(f"<p style='color:#0FE88A;font-weight:bold;'>🌍 Total Worldwide Units Sold (All Companies): {total_global_units:,.0f} Units</p>", unsafe_allow_html=True)

    st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

    # CHARTS (ALL 3 RESTORED)
    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#0FE88A;"></div>
      <div class="sec-head-title">1. QUARTERLY REVENUE TRAJECTORY (LINE CHART)</div></div>""", unsafe_allow_html=True)

    line_data = []
    for item in market_data:
        line_data.extend([
            {"Company": item["company"], "Quarter": "Q1", "Revenue (₹ Cr)": item["q1_cr"]},
            {"Company": item["company"], "Quarter": "Q2", "Revenue (₹ Cr)": item["q2_cr"]},
            {"Company": item["company"], "Quarter": "Q3", "Revenue (₹ Cr)": item["q3_cr"]},
            {"Company": item["company"], "Quarter": "Q4", "Revenue (₹ Cr)": item["q4_cr"]},
        ])
    df_line = pd.DataFrame(line_data)
    if not df_line.empty and df_line["Revenue (₹ Cr)"].sum() > 0:
        fig_line = px.line(df_line, x="Quarter", y="Revenue (₹ Cr)", color="Company", color_discrete_map=PLOT_COLORS, markers=True)
        st.plotly_chart(style_plotly_dark(fig_line), use_container_width=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # RESTORED DONUT CHART
    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#FF2D55;"></div>
      <div class="sec-head-title">2. GLOBAL REVENUE MARKET SHARE (DONUT CHART)</div></div>""", unsafe_allow_html=True)

    pie_df = pd.DataFrame(market_data)
    if pie_df["estimated_annual_cr"].sum() > 0:
        fig_pie = px.pie(pie_df, values="estimated_annual_cr", names="company", hole=0.55, color="company", color_discrete_map=PLOT_COLORS)
        fig_pie.update_traces(textinfo='percent+label', textposition='inside', hovertemplate="<b>%{label}</b><br>₹%{value:,.2f} Cr<br>%{percent:.1%}")
        fig_pie.update_layout(height=400, showlegend=True, margin=dict(t=20, b=20))
        st.plotly_chart(style_plotly_dark(fig_pie), use_container_width=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # RESTORED BAR CHART
    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#3B82F6;"></div>
      <div class="sec-head-title">3. TOTAL UNITS SOLD COMPARISON (BAR CHART)</div></div>""", unsafe_allow_html=True)

    if pie_df["units_annual"].sum() > 0:
        fig_units = px.bar(pie_df, x="company", y="units_annual", color="company", color_discrete_map=PLOT_COLORS, text="units_annual")
        fig_units.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_units.update_layout(height=400, showlegend=False, yaxis_title="Total Units Sold", xaxis_title="Company", margin=dict(t=20, b=20))
        st.plotly_chart(style_plotly_dark(fig_units), use_container_width=True)


    # =========================================================
    # 🌍 3. REGIONAL REGISTRATION INTELLIGENCE (WORLDWIDE)
    # =========================================================
    st.markdown("---")
    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#EAB308;"></div>
      <div class="sec-head-title">REGIONAL REGISTRATION INTELLIGENCE (WORLDWIDE)</div>
      <div class="sec-head-badge">AI LOCATION FILTER</div></div>""", unsafe_allow_html=True)

    col_co, col_s, col_d, col_c, col_btn = st.columns([1, 1, 1, 1, 1])
    with col_co:
        country_sel = st.text_input("Country", value="All", placeholder="e.g. India, USA, Germany")
    with col_s:
        state_sel = st.text_input("State / Province", value="All")
    with col_d:
        district_sel = st.text_input("District", value="All")
    with col_c:
        city_sel = st.text_input("City", value="All")
    with col_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        fetch_regional = st.button("Fetch Regional Data", use_container_width=True)

    if fetch_regional:
        # SUPER FAST LOGIC FOR "ALL" -> global aggregate straight from already-fetched market_data
        if country_sel == "All" and state_sel == "All" and district_sel == "All" and city_sel == "All":
            st.markdown(f"#### 🌍 Sales Snapshot: Worldwide (Global Aggregate)")
            st.markdown(f"""
            <div style="background:rgba(234, 179, 8, 0.1); border-left: 3px solid #EAB308; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                <p style="margin:0; color:#fff;">💡 <b>AI Insight:</b> Displaying consolidated worldwide unit sales data for {clean_fy}.</p>
            </div>
            """, unsafe_allow_html=True)

            global_df = pd.DataFrame([{"Brand": item["company"], "Units Registered": item["units_annual"]} for item in market_data])
            total_global = global_df["Units Registered"].sum()
            global_df["Market Share"] = (global_df["Units Registered"] / total_global * 100).apply(lambda x: f"{x:.1f}%") if total_global > 0 else "N/A"
            st.markdown(f"<p style='color: #0FE88A; font-weight: bold;'>Total Worldwide Market Size (Tracked): {total_global:,.0f} Units</p>", unsafe_allow_html=True)
            st.dataframe(global_df, use_container_width=True, hide_index=True)

        else:
            loc_display = " > ".join([p for p in [country_sel, state_sel, district_sel, city_sel] if p != "All"])
            with st.spinner(f"Scraping regional registration data for {loc_display}..."):
                target_yr = period.split("-")[0].replace("FY ", "").strip()
                reg_data = get_location_sales(country=country_sel, state=state_sel, district=district_sel, city=city_sel, year=target_yr)

                st.markdown(f"#### 📍 Sales Snapshot: {reg_data['metadata']['query_location']}")

                st.markdown(f"""
                <div style="background:rgba(234, 179, 8, 0.1); border-left: 3px solid #EAB308; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                    <p style="margin:0; color:#fff;">💡 <b>AI Insight:</b> {reg_data['summary']}</p>
                </div>
                """, unsafe_allow_html=True)

                reg_df = pd.DataFrame(reg_data['sales_data'])
                if not reg_df.empty and 'units' in reg_df.columns:
                    total_loc_units = reg_data['total_units']
                    st.markdown(f"<p style='color: #0FE88A; font-weight: bold;'>Total Units Sold in this Region: {total_loc_units:,.0f}</p>", unsafe_allow_html=True)

                    reg_df.rename(columns={"brand": "Brand", "units": "Units Registered", "market_share": "Market Share"}, inplace=True)
                    st.dataframe(reg_df, use_container_width=True, hide_index=True)
