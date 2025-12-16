import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long V15.4 Stable", page_icon="🐲")

# ==========================================
# 🎨 GIAO DIỆN ROYAL UI (CSS GLOBAL)
# ==========================================
st.markdown("""
<style>
    /* Chỉnh màu chủ đạo */
    :root { --primary-color: #3498db; }
    
    /* Làm đẹp các container (giả lập Card) */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }

    /* Tiêu đề */
    h1, h2, h3 { color: #64b5f6 !important; }
    
    /* Metric số to */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        color: #3498db !important;
        font-weight: 700 !important;
    }
    
    /* Tab đẹp hơn */
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; border-radius: 5px;
        background-color: rgba(255, 255, 255, 0.05);
        border: none; color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3498db !important;
        color: white !important;
    }
    
    .news-item { padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .news-title { font-weight: bold; color: #90caf9; text-decoration: none; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background: #0e1117; color: gray; text-align: center; padding: 5px; font-size: 12px; border-top: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ DATA & LOGIC
# ==========================================
if "PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("🔒 Mật khẩu:", type="password")
    if pwd != st.secrets["PASSWORD"]: st.stop()

STOCK_GROUPS = {
    "🏆 VN30": "ACB,BCM,BID,BVH,CTG,FPT,GAS,GVR,HDB,HPG,MBB,MSN,MWG,PLX,POW,SAB,SHB,SSB,SSI,STB,TCB,TPB,VCB,VHM,VIB,VIC,VJC,VNM,VPB,VRE",
    "🏦 Ngân Hàng": "VCB,BID,CTG,TCB,VPB,MBB,ACB,STB,HDB,VIB,TPB,SHB,EIB,MSB,OCB,LPB,SSB",
    "📈 Chứng Khoán": "SSI,VND,VCI,HCM,SHS,MBS,FTS,BSI,CTS,VIX,AGR,ORS",
    "🏗️ Thép": "HPG,HSG,NKG,VSG,TLH,POM",
    "🏠 BĐS": "VHM,VIC,VRE,NVL,PDR,DIG,CEO,DXG,KDH,NLG,KBC,IDC,SZC",
    "🛢️ Dầu Khí": "GAS,PLX,PVD,PVS,PVC,BSR,OIL,PVT",
    "🛒 Bán Lẻ": "MWG,PNJ,DGW,FRT,PET,MSN"
}

st.sidebar.title("🎛️ Trạm Điều Khiển")
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét"])
if st.sidebar.button("🔄 Cập Nhật Dữ Liệu"):
    st.cache_data.clear()
    st.rerun()

# --- LOAD DATA ---
@st.cache_data(ttl=300)
def load_data_v15(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    try:
        df = stock.history(period="1y")
        if len(df) > 50:
            df.ta.sma(length=20, append=True); df.ta.sma(length=50, append=True)
            df.ta.rsi(length=14, append=True); df.ta.macd(append=True)
            df.ta.adx(length=14, append=True); df.ta.atr(length=14, append=True)
    except: df = pd.DataFrame()
    
    try:
        df_chart = stock.history(period=time, interval="15m" if time in ["1d","5d"] else "1d")
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True); df_chart.ta.bbands(length=20, std=2, append=True)
            df_chart.ta.rsi(length=14, append=True); df_chart.ta.macd(append=True)
    except: df_chart = pd.DataFrame()

    try: info = stock.info
    except: info = {}
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    # News
    try:
        rss = f"https://news.google.com/rss/search?q=cổ+phiếu+{ticker}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss)
        news = [{'title': e.title, 'link': e.link, 'published': e.get('published','')[:16]} for e in feed.entries[:10]]
    except: news = []
    
    return df, df_chart, info, fin, bal, holders, news

# --- ANALYZE ---
def analyze_tech(df):
    if df.empty or len(df)<50: return None
    now = df.iloc[-1]
    # Khởi tạo list rỗng chuẩn Python
    pros = []
    cons = []
    score = 5
    
    # Logic
    if now['Close'] > now.get('SMA_20', 0): score += 2; pros.append("Giá > MA20 (Tăng)")
    else: score -= 1
    if now.get('RSI_14', 50) < 30: score += 2; pros.append("RSI Quá bán (Hồi)")
    elif now.get('RSI_14', 50) > 70: score -= 1; cons.append("RSI Quá mua")
    if now.get('MACD_12_26_9', 0) > now.get('MACDs_12_26_9', 0): score += 1; pros.append("MACD Tốt")
    else: score -= 1; cons.append("MACD Xấu")
    
    final_score = max(0, min(10, score))
    action = "MUA MẠNH" if final_score >= 8 else "MUA THĂM DÒ" if final_score >= 6 else "QUAN SÁT" if final_score >= 4 else "BÁN"
    
    return {'score': final_score, 'action': action, 'pros': pros, 'cons': cons, 
            'entry': now['Close'], 'target': now['Close']*1.1, 'stop': now['Close']*0.95}

def analyze_fund(info):
    scores = {'Định Giá': 5, 'Sinh Lời': 5, 'Tăng Trưởng': 5, 'Sức Khỏe': 5, 'Hiệu Quả': 5}
    try:
        pe = info.get('trailingPE', 0)
        if pe is None: pe = 0
        if 0 < pe < 15: scores['Định Giá'] = 8
        elif pe > 25: scores['Định Giá'] = 3
        
        roe = info.get('returnOnEquity', 0)
        if roe is None: roe = 0
        if roe > 0.15: scores['Sinh Lời'] = 8
    except: pass
    return scores

# --- CHARTS ---
def plot_gauge(score, action):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        title = {'text': action, 'font': {'size': 20, 'color': '#3498db'}},
        gauge = {'axis': {'range': [None, 10]}, 'bar': {'color': "#3498db"},
                 'steps': [{'range': [0,3], 'color': '#ef4444'}, {'range': [3,7], 'color': '#f59e0b'}, {'range': [7,10], 'color': '#10b981'}]}
    ))
    fig.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'})
    return fig

def plot_radar(scores):
    fig = go.Figure(data=go.Scatterpolar(
        r=list(scores.values()) + [list(scores.values())[0]],
        theta=list(scores.keys()) + [list(scores.keys())[0]],
        fill='toself', line_color='#29b6f6'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False, height=250, margin=dict(l=40,r=40,t=20,b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'})
    return fig

def render_main_chart(df):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá')])
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange'), name='MA20'))
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 🖥️ MAIN UI
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    c1, c2 = st.columns([3, 1])
    with c1: symbol = st.text_input("Mã CP:", "HPG").upper()
    with c2: 
        st.write(""); 
        if st.button("🚀 Phân Tích"): st.rerun()
    
    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y"], index=4)

    if symbol:
        df, df_chart, info, fin, bal, holders, news = load_data_v15(symbol, period)
        
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            
            # --- PHẦN DASHBOARD (ĐÃ SỬA LỖI) ---
            tech = analyze_tech(df)
            fund = analyze_fund(info)
            
            if tech:
                col1, col2 = st.columns(2)
                
                # Card 1: Kỹ Thuật
                with col1:
                    st.subheader("🔭 Kỹ Thuật")
                    st.plotly_chart(plot_gauge(tech['score'], tech['action']), use_container_width=True)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Giá", f"{tech['entry']:,.0f}")
                    m2.metric("Cắt Lỗ", f"{tech['stop']:,.0f}")
                    m3.metric("Mục Tiêu", f"{tech['target']:,.0f}")
                    
                    with st.expander("Chi tiết tín hiệu"):
                        for p in tech['pros']: st.success(p)
                        for c in tech['cons']: st.error(c)

                # Card 2: Cơ Bản
                with col2:
                    st.subheader("🏢 Sức Khỏe DN")
                    st.plotly_chart(plot_radar(fund), use_container_width=True)
                    st.info(f"P/E: {info.get('trailingPE', 'N/A')} | EPS: {info.get('trailingEps', 'N/A')}")

            # --- TABS ---
            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ", "📰 Tin Tức", "💰 Tài Chính", "👥 Cổ Đông"])
            
            with t1: render_main_chart(df_chart)
            
            with t2:
                for n in news:
                    st.markdown(f"<div class='news-item'><a class='news-title' href='{n['link']}' target='_blank'>{n['title']}</a><div class='news-meta'>{n['published']}</div></div>", unsafe_allow_html=True)
            
            with t3:
                c_left, c_right = st.columns(2)
                with c_left: st.write("Kinh Doanh"); st.dataframe(fin, use_container_width=True)
                with c_right: st.write("Cân Đối"); st.dataframe(bal, use_container_width=True)
                
            with t4:
                c_left, c_right = st.columns([2, 1])
                with c_left:
                    if not holders.empty:
                        # Pie chart holders
                        try:
                            labels = holders[1].tolist(); values = [float(v.strip('%')) for v in holders[0].tolist()]
                            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
                            st.plotly_chart(fig, use_container_width=True)
                        except: st.dataframe(holders)
                with c_right:
                    st.write(info.get('longBusinessSummary', ''))

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Bảng Giá & Máy Quét")
    
    tabs = st.tabs(["🛠️ Tự Nhập"] + list(STOCK_GROUPS.keys()))
    
    # Tab Tự Nhập
    with tabs[0]:
        inp = st.text_area("Nhập mã (VD: HPG, VCB):", "HPG, VCB, SSI, VND, FPT")
        if st.button("🚀 Quét"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            res = []
            bar = st.progress(0)
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks))
                try:
                    df, _, _, _, _, _, _ = load_data_v15(t, "1y")
                    s = analyze_tech(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": s['entry']})
                except: pass
            bar.empty()
            if res:
                df_res = pd.DataFrame(res).sort_values("Điểm", ascending=False)
                # Tô màu
                def color_row(row):
                    return ['color: #10b981; font-weight: bold' if row['Điểm']>=8 else 'color: #ef4444' if row['Điểm']<=3 else '' for _ in row]
                st.dataframe(df_res.style.apply(color_row, axis=1), use_container_width=True)

    # Các Tab Ngành
    for i, (name, list_stocks) in enumerate(STOCK_GROUPS.items()):
        with tabs[i+1]:
            if st.button(f"Quét {name}", key=name):
                ticks = list_stocks.split(',')
                res = []
                bar = st.progress(0)
                for j, t in enumerate(ticks):
                    bar.progress((j+1)/len(ticks))
                    try:
                        df, _, _, _, _, _, _ = load_data_v15(t, "1y")
                        s = analyze_tech(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": s['entry']})
                    except: pass
                bar.empty()
                if res:
                    st.dataframe(pd.DataFrame(res).sort_values("Điểm", ascending=False), use_container_width=True)

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V15.4 - Final Stable</div>', unsafe_allow_html=True)
