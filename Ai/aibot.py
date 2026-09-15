import streamlit as st
from Main.shared_config import get_groq_client


def render_aibot_tab(market_data, period):
    st.markdown("""
    <style>
    @keyframes radar-spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }
    @keyframes blink-dot  { 0%,100%{opacity:1} 50%{opacity:.25} }

    .ai-search-anim {
      display:flex; align-items:center; gap:16px;
      background:#1a0a0d; border:1px solid #E8002D;
      border-radius:10px; padding:14px 20px; margin-bottom:12px;
    }
    .ai-search-ring {
      width:34px; height:34px; border-radius:50%; flex-shrink:0;
      border:2px solid rgba(232,0,45,.25);
      border-top:2px solid #E8002D;
      animation:radar-spin 1s linear infinite;
    }
    .ai-status-dot {
      width:8px; height:8px; border-radius:50%;
      background:#0FE88A; box-shadow:0 0 10px #0FE88A;
      animation:blink-dot 2s infinite; flex-shrink:0;
    }
    .chat-bubble {
      border-radius:12px;
      padding:16px 20px;
      margin-bottom:14px;
      line-height:1.8;
    }
    .chat-user {
      background:#1c1014;
      border:1px solid #5a1520;
      border-left:4px solid #E8002D;
    }
    .chat-analyst {
      background:#0d1a14;
      border:1px solid #0f4a2a;
      border-left:4px solid #0FE88A;
    }
    .chat-role-label {
      font-family:'JetBrains Mono',monospace;
      font-size:9px; letter-spacing:2.5px;
      text-transform:uppercase; margin-bottom:10px;
    }
    .chat-content {
      font-family:'Barlow',sans-serif;
      font-size:14px; color:#FFFFFF !important;
      line-height:1.8; white-space:pre-wrap;
      font-weight:400;
    }
    </style>

    <div style="display:flex;align-items:center;gap:10px;
         margin-bottom:6px;padding-bottom:14px;border-bottom:1px solid #2a1018;">
      <div style="width:4px;height:26px;background:#E8002D;border-radius:2px;"></div>
      <div style="font-family:'Bebas Neue',sans-serif;font-size:21px;
           letter-spacing:3px;color:#FFFFFF;">AI ANALYST</div>
      <div style="margin-left:auto;background:#1a0508;border:1px solid #5a1520;
           border-radius:6px;padding:4px 12px;
           font-family:'JetBrains Mono',monospace;font-size:9px;
           letter-spacing:2px;color:#E8002D;text-transform:uppercase;">
        GROQ LLaMA 3.3-70B · LIVE
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;
         background:#0f0a0b;border:1px solid #3a1520;
         border-radius:10px;padding:12px 18px;margin-bottom:18px;">
      <div class="ai-status-dot"></div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
           letter-spacing:2px;text-transform:uppercase;color:#0FE88A;font-weight:700;">ONLINE</div>
      <div style="width:1px;height:14px;background:#3a1520;"></div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
           letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8;">
        LLaMA 3.3-70B · Live Market Data Injected
      </div>
      <div style="margin-left:auto;font-family:'Barlow',sans-serif;
           font-size:12px;color:#cbd5e1;font-weight:500;">
        Ask about strategy, competitors, sales, dealers or tractor trends
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:2.5px;
         text-transform:uppercase;color:#94a3b8;margin-bottom:10px;">⚡ QUICK PROMPTS</div>
    """, unsafe_allow_html=True)

    qp_cols = st.columns(4)
    quick_prompts = [
        "Mahindra vs John Deere — who leads in India?",
        "Which quarter shows Mahindra Tractor's best growth?",
        "Top dealer expansion strategy for Mahindra Tractors",
        "Escorts Kubota competitive threat assessment",
    ]
    for idx, (col, qp) in enumerate(zip(qp_cols, quick_prompts)):
        with col:
            if st.button(qp, key=f"qp_{idx}"):
                st.session_state.chat_messages.append({"role": "user", "content": qp})
                st.rerun()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    for msg in st.session_state.chat_messages:
        is_ai      = msg["role"] == "assistant"
        bubble_cls = "chat-analyst" if is_ai else "chat-user"
        role_color = "#0FE88A"     if is_ai else "#E8002D"
        role_lbl   = "🤖  ANALYST" if is_ai else "👤  YOU"

        st.markdown(
            f"""<div class="chat-bubble {bubble_cls}">
                  <div class="chat-role-label" style="color:{role_color};">{role_lbl}</div>
                  <div class="chat-content">{msg["content"]}</div>
                </div>""",
            unsafe_allow_html=True,
        )

    if q := st.chat_input("Ask about Mahindra Tractors, competitors, tractor tenders, market trends..."):
        st.session_state.chat_messages.append({"role": "user", "content": q})

        search_placeholder = st.empty()
        search_placeholder.markdown("""
        <div class="ai-search-anim">
          <div class="ai-search-ring"></div>
          <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;
                 text-transform:uppercase;color:#E8002D;margin-bottom:4px;font-weight:700;">
              ⚡ SEARCHING & ANALYZING
            </div>
            <div style="font-family:'Barlow',sans-serif;font-size:13px;color:#94a3b8;">
              Scanning live market data · Generating intelligence brief…
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        try:
            client = get_groq_client()
            market_ctx = "\n".join([
                f"- {item['company']}: Annual ₹{item['estimated_annual_cr']:,.0f} Cr | "
                f"Q1:{item['q1_cr']:,.0f} Q2:{item['q2_cr']:,.0f} Q3:{item['q3_cr']:,.0f} Q4:{item['q4_cr']:,.0f} | "
                f"YoY: {item['growth_percent']}"
                for item in market_data
            ])
            messages = [{
                "role": "system",
                "content": (
                    f"You are a senior Market Intelligence Analyst for the Indian Agricultural Tractor industry, "
                    f"with special focus on Mahindra Tractors competitive positioning against "
                    f"Escorts Kubota, Sonalika, TAFE, Swaraj, and John Deere. "
                    f"You also have expertise in government tractor tenders, procurement patterns, "
                    f"state agriculture department purchases, and GeM portal tenders. "
                    f"Current {period} live market data:\n{market_ctx}\n"
                    f"Provide data-driven, strategic insights. Lead with Mahindra Tractors perspective. "
                    f"Be concise and direct. When asked about tenders, refer to procurement patterns, "
                    f"seasonal demand, and competitor bid strategies in Indian agriculture sector."
                ),
            }]
            messages.extend([
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.chat_messages
            ])
            res   = client.chat.completions.create(messages=messages, model="llama-3.3-70b-versatile")
            reply = res.choices[0].message.content
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            search_placeholder.empty()
            st.rerun()

        except Exception as e:
            search_placeholder.empty()
            st.error("⚠️ AI API limit reached — please wait a moment and try again.")