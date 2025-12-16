import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Royal V15.3", page_icon="🐲")

# ==========================================
# 🎨 GIAO DIỆN HOÀNG GIA (ROYAL UI - STABLE)
# ==========================================
st.markdown("""
<style>
    /* Chỉnh màu sắc toàn trang */
    [data-testid="stAppViewContainer"] {
        background-color: #0e1117;
    }
    
    h1, h2, h3 { color: #64b5f6 !important; font-family: sans-serif; font-weight: 700; }
    
    /* Style cho các Metric (Số to) */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        color: #3498db !important;
    }
    
    /* Card giả lập bằng CSS cho Container */
    .css-card {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    .news-item {
        padding: 10px; border-bottom: 1px solid #333;
    }
    .news-title {
        font-weight: bold; color: #90caf9; text-decoration: none; font-size: 15px;
    }
    .news-meta { font-size: 12px; color: gray; }
    
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: gray; text-align: center; padding: 5px; border-top: 1px solid #333; z-index: 999; font-size: 12px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ CẤU HÌNH & DATA
# ==========================================
if "PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("🔒 Mật khẩu:", type="password")
    if pwd != st.secrets["PASSWORD"]: st.info("Vui lòng nhập mật khẩu."); st.stop()

STOCK_GROUPS = {
    "🏆 VN30": "ACB,BCM,BID,BVH,CTG,FPT,GAS,GVR,HDB,HPG,MBB,MSN,MWG,PLX,POW,SAB,SHB,SSB,SSI,STB,TCB,TPB,VCB,VHM,VIB,VIC,VJC,VNM,VPB,VRE",
    "🏦 Ngân Hàng": "VCB,BID,CTG,TCB,VPB,MBB,ACB,STB,HDB,VIB,TPB,SHB,EIB,MSB,OCB,LPB,SSB",
    "📈 Chứng Khoán": "SSI,VND,VCI,HCM,SHS,MBS,FTS,BSI,CTS,VIX,AGR,ORS",
    "🏗️ Thép": "HPG,HSG,NKG,VSG,TLH,POM",
    "🏠 BĐS": "VHM,VIC,VRE,NVL,PDR,DIG,CEO,DXG,KDH,NLG,KBC,IDC,SZC",
    "🛢️ Dầu Khí": "GAS,PLX,PVD,PVS,PVC,BSR,OIL,PVT",
    "🛒 Bán Lẻ": "MWG,PNJ,DGW,FRT,PET,MSN"
}

TRANS_MAP = {'Total Revenue': 'Tổng Doanh Thu', 'Operating Revenue': 'Doanh thu HĐ', 'Cost Of Revenue': 'Giá Vốn', 'Gross Profit': 'LN Gộp', 'Net Income': 'LN Sau Thuế', 'Total Assets': 'Tổng Tài Sản', 'Total Liabilities Net Minority Interest': 'Tổng Nợ', 'Stockholders Equity': 'Vốn Chủ'}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét"])
if st.sidebar.button("🔄 Cập Nhật Dữ Liệu"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# 🧠 XỬ LÝ DỮ LIỆU
# ==========================================
@st.cache_data(ttl=300)
def load_news_google(symbol):
    try:
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        clean_news = []
        for entry in feed.entries[:10]:
            clean_news.append({'title': entry.title, 'link': entry.link, 'published': entry.get('published', '')[:16], 'source': entry.get('source', {}).get('title', 'News')})
        return clean_news
    except: return []

@st.cache_data(ttl=300)
def load_data_full(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    try:
        df_calc = stock.history(period="1y")
        if len(df_calc) > 52:
            df_calc.ta.sma(length=20, append=True); df_calc.ta.sma(length=50, append=True)
            df_calc.ta.rsi(length=14, append=True); df_calc.ta.macd(append=True)
            df_calc.ta.adx(length=14, append=True); df_calc.ta.atr(length=14, append=True)
    except: df_calc = pd.DataFrame()

    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True); df_chart.ta.bbands(length=20, std=2, append=True)
            df_chart.ta.rsi(length=14, append=True); df_chart.ta.macd(append=True)
    except: df_chart = pd.DataFrame()

    try: info = stock.info; 
    except: info = {}
    try: fin = stock.financials; 
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet; 
    except: bal = pd.DataFrame()
    try: holders = stock.major_holders; 
    except: holders = pd.DataFrame()
    
    news_items = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, holders, news_items

def analyze_smart(df):
    if df.empty or len(df) < 52: return None
    now = df.iloc[-1]
    close = now['Close']; ma20 = now['SMA_20']; ma50 = now['SMA_50']
    rsi = now['RSI_14']; macd = now['MACD_12_26_9']; macds = now['MACDs_12_26_9']
    adx = now['ADX_14']; atr = now['ATRr_14']
    
    # --- ĐÃ FIX LỖI VALUE ERROR TẠI ĐÂY ---
    score = 5
    pros = []
    cons = []
    # --------------------------------------

    if close > ma20 and close > ma50: score += 2; pros.append("Uptrend (Giá > MA20, MA50)")
    else: score -=1
    if adx > 25: score += 1; pros.append(f"Trend Mạnh (ADX={adx:.0f})")
    if rsi < 30: score += 2; pros.append("RSI Quá bán (Hồi phục)")
    elif rsi > 70: score -= 1; cons.append("RSI Quá mua (Cẩn thận)")
    if macd > macds: score += 1; pros.append("MACD Cắt lên")
    else: score -= 1; cons.append("MACD Cắt xuống")
    
    final_score = max(0, min(10, score))
    action = "QUAN SÁT"
    if final_score >= 8: action = "MUA MẠNH"
    elif final_score >= 6: action = "MUA THĂM DÒ"
    elif final_score <= 3: action = "BÁN / CẮT LỖ"
    
    return {"score": final_score, "action": action, "pros": pros, "cons": cons, "entry": close, "stop": close - 2*atr, "target": close + 3*atr}

def analyze_fundamental_score(info):
    scores = {'Định Giá': 5, 'Sinh Lời': 5, 'Tăng Trưởng': 5, 'Sức Khỏe': 5, 'Hiệu Quả': 5}
    try:
        pe = info.get('trailingPE', 0); pe = 0 if pe is None else pe
        if 0 < pe < 15: scores['Định Giá'] = 8
        elif pe > 25: scores['Định Giá'] = 3
        
        roe = info.get('returnOnEquity', 0); roe = 0 if roe is None else roe
        if roe > 0.15: scores['Sinh Lời'] = 8
        
        rev = info.get('revenueGrowth', 0); rev = 0 if rev is None else rev
        if rev > 0.1: scores['Tăng Trưởng'] = 8
    except: pass
    return scores

def clean_table(df):
    if df.empty: return pd.DataFrame()
    valid = [i for i in df.index if i in TRANS_MAP]
    if not valid: return df
    df_new = df.loc[valid].rename(index=TRANS_MAP)
    for col in df_new.columns:
        for idx in df_new.index:
            if "EPS" not in idx and isinstance(df_new.loc[idx, col], (int, float)): df_new.loc[idx, col] = df_new.loc[idx, col] / 1e9
    return df_new

# --- BIỂU ĐỒ (PLOTLY) ---
def plot_gauge(score, action):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        title = {'text': f"{action}", 'font': {'size': 24, 'color': '#3498db'}},
        gauge = {
            'axis': {'range': [None, 10], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#3498db"}, 'bgcolor': "#1f2937",
            'steps': [{'range': [0, 3], 'color': '#ef4444'}, {'range': [3, 7], 'color': '#f59e0b'}, {'range': [7, 10], 'color': '#10b981'}],
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': score}}))
    fig.update_layout(height=220, margin=dict(l=20,r=20,t=30,b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    return fig

def plot_radar(scores):
    categories = list(scores.keys()); values = list(scores.values())
    categories = [*categories, categories[0]]; values = [*values, values[0]]
    fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', name='Cơ Bản', line_color='#29b6f6'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10], color='gray')), showlegend=False, height=220, margin=dict(l=40,r=40,t=20,b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    return fig

def plot_holders(df_holders):
    if df_holders.empty: return None
    try:
        labels = df_holders[1].tolist(); values = []
        for v in df_holders[0].tolist():
            try: values.append(float(v.strip('%')))
            except: values.append(0)
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, showlegend=False)
        return fig
    except: return None

def render_chart(df):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá')])
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange'), name='MA20'))
    fig.update_layout(height=500, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 🖥️ GIAO DIỆN CHÍNH
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    c1, c2 = st.columns([3, 1])
    with c1: symbol = st.text_input("🔍 Nhập Mã (VD: HPG)", value="HPG").upper()
    with c2: 
        st.write(""); 
        if st.button("🚀 Phân Tích"): st.rerun()
    
    if symbol:
        # Load dữ liệu
        df_calc, df_chart, info, fin, bal, holders, news = load_data_full(symbol, "1y")
        
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            
            # Phân tích
            tech = analyze_smart(df_calc)
            fund = analyze_fundamental_score(info)
            
            if tech:
                # --- KHU VỰC DASHBOARD ---
                col1, col2 = st.columns(2)
                
                with col1:
                    with st.container():
                        st.markdown("### 🔭 Sức Mạnh Kỹ Thuật")
                        # Vẽ trực tiếp Plotly (Không qua HTML để tránh lỗi)
                        st.plotly_chart(plot_gauge(tech['score'], tech['action']), use_container_width=True)
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Giá", f"{tech['entry']:,.0f}")
                        m2.metric("Cắt Lỗ", f"{tech['stop']:,.0f}")
                        m3.metric("Mục Tiêu", f"{tech['target']:,.0f}")
                        
                        with st.expander("Chi tiết tín hiệu"):
                            for p in tech['pros']: st.success(f"+ {p}")
                            for c in tech['cons']: st.error(f"- {c}")

                with col2:
                    with st.container():
                        st.markdown("### 🏢 Sức Khỏe Doanh Nghiệp")
                        st.plotly_chart(plot_radar(fund), use_container_width=True)
                        st.info(f"P/E: {info.get('trailingPE', 'N/A')} | EPS: {info.get('trailingEps', 'N/A')}")

                # --- TABS ---
                t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ", "📰 Tin Tức", "💰 Tài Chính", "👥 Cổ Đông"])
                
                with t1: render_chart(df_chart)
                
                with t2:
                    for n in news:
                        st.markdown(f"<div class='news-item'><a class='news-title' href='{n['link']}' target='_blank'>{n['title']}</a><div class='news-meta'>{n['published']}</div></div>", unsafe_allow_html=True)
                
                with t3:
                    c_left, c_right = st.columns(2)
                    with c_left: st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin), use_container_width=True)
                    with c_right: st.subheader("Cân Đối KT"); st.dataframe(clean_table(bal), use_container_width=True)
                
                with t4:
                    c_left, c_right = st.columns([2, 1])
                    with c_left:
                        if holders is not None and not holders.empty:
                            fig_pie = plot_holders(holders)
                            if fig_pie: st.plotly_chart(fig_pie, use_container_width=True)
                            else: st.dataframe(holders)
                        else: st.write("Không có dữ liệu cổ đông")
                    with c_right:
                        st.write(info.get('longBusinessSummary', ''))

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Bảng Giá & Máy Quét")
    
    # Tab Tự Nhập & Các Ngành
    tabs = st.tabs(["🛠️ Tự Nhập"] + list(STOCK_GROUPS.keys()))
    
    # Tab 1: Tự Nhập
    with tabs[0]:
        inp = st.text_area("Nhập mã (cách nhau dấu phẩy):", "HPG, VCB, SSI, VND")
        if st.button("🚀 Quét Ngay"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            res = []
            bar = st.progress(0)
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks))
                try:
                    df, _, _, _, _, _, _ = load_data_full(t, "1y")
                    s = analyze_smart(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": s['entry']})
                except: pass
            bar.empty()
            if res:
                st.dataframe(pd.DataFrame(res).sort_values("Điểm", ascending=False), use_container_width=True)
    
    # Các Tab Ngành
    for i, (name, stocks) in enumerate(STOCK_GROUPS.items()):
        with tabs[i+1]:
            if st.button(f"Quét {name}", key=name):
                ticks = stocks.split(',')
                res = []
                bar = st.progress(0)
                for j, t in enumerate(ticks):
                    bar.progress((j+1)/len(ticks))
                    try:
                        df, _, _, _, _, _, _ = load_data_full(t, "1y")
                        s = analyze_smart(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": s['entry']})
                    except: pass
                bar.empty()
                if res:
                    final_df = pd.DataFrame(res).sort_values("Điểm", ascending=False)
                    st.dataframe(final_df, use_container_width=True)
                    top = final_df.iloc[0]
                    if top['Điểm'] >= 7: st.success(f"💎 Top 1: {top['Mã']} ({top['Điểm']} điểm)")

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V15.3 - Redemption</div>', unsafe_allow_html=True)
