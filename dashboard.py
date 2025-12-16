import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Hybrid V14.1", page_icon="🐲")

# ==========================================
# 🛡️ PHẦN BẢO MẬT & BẢO TRÌ
# ==========================================
MAINTENANCE_MODE = False 

if MAINTENANCE_MODE:
    st.title("🚧 HỆ THỐNG ĐANG BẢO TRÌ")
    st.warning("Hệ thống Thăng Long đang được nâng cấp. Vui lòng quay lại sau!")
    st.stop()

if "PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("🔒 Mật khẩu:", type="password")
    if pwd != st.secrets["PASSWORD"]:
        st.info("Vui lòng nhập mật khẩu.")
        st.stop()

# ==========================================
# 📂 KHO MÃ CỔ PHIẾU (DỮ LIỆU)
# ==========================================
STOCK_GROUPS = {
    "🏆 VN30": "ACB,BCM,BID,BVH,CTG,FPT,GAS,GVR,HDB,HPG,MBB,MSN,MWG,PLX,POW,SAB,SHB,SSB,SSI,STB,TCB,TPB,VCB,VHM,VIB,VIC,VJC,VNM,VPB,VRE",
    "🏦 Ngân Hàng": "VCB,BID,CTG,TCB,VPB,MBB,ACB,STB,HDB,VIB,TPB,SHB,EIB,MSB,OCB,LPB,SSB",
    "📈 Chứng Khoán": "SSI,VND,VCI,HCM,SHS,MBS,FTS,BSI,CTS,VIX,AGR,ORS",
    "🏗️ Thép": "HPG,HSG,NKG,VSG,TLH,POM",
    "🏠 BĐS": "VHM,VIC,VRE,NVL,PDR,DIG,CEO,DXG,KDH,NLG,KBC,IDC,SZC",
    "🛢️ Dầu Khí": "GAS,PLX,PVD,PVS,PVC,BSR,OIL,PVT",
    "🐟 Thủy Sản": "VHC,ANV,IDI,CMX,FMC",
    "🛒 Bán Lẻ": "MWG,PNJ,DGW,FRT,PET,MSN",
    "⚡ Điện": "POW,REE,NT2,PC1,GEG,HDG,GEX"
}

# ==========================================
# 🎨 GIAO DIỆN DARK MODE PRO
# ==========================================
st.markdown("""
<style>
    h1, h2, h3 {color: #64b5f6 !important;}
    [data-testid="stMetricValue"] {font-size: 1.4rem !important; font-weight: bold !important;}
    [data-testid="stMetricLabel"] {font-size: 1rem !important; opacity: 0.8;}
    
    /* Card chứa biểu đồ Radar và Gauge (MỚI CHO V14) */
    .metric-card {
        background-color: #1f2937; border: 1px solid #374151;
        border-radius: 10px; padding: 15px; margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    .rec-card {background-color: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 20px;}
    .rec-card h3 {color: white !important;} 
    .score-circle {display: inline-block; width: 60px; height: 60px; line-height: 60px; border-radius: 50%; font-size: 24px; font-weight: bold; color: white; margin-bottom: 10px;}
    .green-zone {background-color: #10b981; box-shadow: 0 0 15px #10b981;}
    .red-zone {background-color: #ef4444; box-shadow: 0 0 15px #ef4444;}
    .yellow-zone {background-color: #f59e0b; box-shadow: 0 0 15px #f59e0b;}
    
    .news-item {padding: 10px; border-bottom: 1px solid #444; margin-bottom: 10px;}
    .news-item:hover {background-color: rgba(100, 181, 246, 0.1); border-radius: 5px;}
    .news-title {font-weight: bold; font-size: 16px; text-decoration: none; display: block; margin-bottom: 5px; color: inherit !important;}
    .news-meta {font-size: 12px; color: #888;}
    
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: #6b7280; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #374151; z-index: 100;}
</style>
""", unsafe_allow_html=True)

TRANS_MAP = {
    'Total Revenue': '1. Tổng Doanh Thu', 'Operating Revenue': '   - Doanh thu HĐ',
    'Cost Of Revenue': '2. Giá Vốn Hàng Bán', 'Gross Profit': '3. Lợi Nhuận Gộp',
    'Operating Expense': '4. Chi Phí Hoạt Động', 'Operating Income': '5. Lợi Nhuận Từ HĐKD',
    'Net Income': '9. Lợi Nhuận Sau Thuế', 'EBITDA': '10. EBITDA', 'Basic EPS': '11. EPS Cơ Bản',
    'Total Assets': 'A. TỔNG TÀI SẢN', 'Current Assets': '   I. Tài sản Ngắn hạn',
    'Cash And Cash Equivalents': '      1. Tiền & Tương đương tiền', 'Inventory': '      2. Hàng Tồn kho',
    'Total Liabilities Net Minority Interest': 'B. TỔNG NỢ', 'Stockholders Equity': 'C. VỐN CHỦ SỞ HỮU',
    'Operating Cash Flow': '1. Dòng Tiền KD', 'Investing Cash Flow': '2. Dòng Tiền Đầu Tư',
    'Financing Cash Flow': '3. Dòng Tiền Tài Chính', 'Free Cash Flow': '-> Dòng Tiền Tự Do'
}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.success("👑 **Chủ sở hữu: Thăng Long**")
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét"])
if st.sidebar.button("🔄 Xóa Cache & Cập Nhật"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# 🧠 XỬ LÝ DỮ LIỆU & PHÂN TÍCH
# ==========================================

@st.cache_data(ttl=300)
def load_news_google(symbol):
    try:
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        clean_news = []
        for entry in feed.entries[:10]:
            clean_news.append({'title': entry.title, 'link': entry.link, 'published': entry.get('published', ''), 'source': entry.get('source', {}).get('title', 'Google News')})
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
    try: cash = stock.cashflow; 
    except: cash = pd.DataFrame()
    try: holders = stock.major_holders; 
    except: holders = pd.DataFrame()
    
    news_items = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news_items

# --- 1. CHẤM ĐIỂM KỸ THUẬT (LOGIC CŨ NHƯNG CẤU TRÚC CHO CHART MỚI) ---
def analyze_smart(df):
    if df.empty or len(df) < 52: return None
    now = df.iloc[-1]
    close = now['Close']; ma20 = now['SMA_20']; ma50 = now['SMA_50']
    rsi = now['RSI_14']; macd = now['MACD_12_26_9']; macds = now['MACDs_12_26_9']
    adx = now['ADX_14']; atr = now['ATRr_14']
    vol_now = now['Volume']; vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
    high9 = df['High'].rolling(9).max().iloc[-1]; low9 = df['Low'].rolling(9).min().iloc[-1]; tenkan = (high9 + low9)/2
    high26 = df['High'].rolling(26).max().iloc[-1]; low26 = df['Low'].rolling(26).min().iloc[-1]; kijun = (high26 + low26)/2

    score = 5 # Điểm gốc
    pros, cons = [], []
    
    if close > ma20 and close > ma50: score += 2; pros.append("Uptrend")
    else: score -=1
    
    if adx > 25: score += 1; pros.append(f"Trend Mạnh")
    
    if rsi < 30: score += 2; pros.append("Quá bán (Hồi phục)")
    elif rsi > 70: score -= 1; cons.append("Quá mua")
    
    if macd > macds: score += 1; pros.append("MACD Tốt")
    else: score -= 1; cons.append("MACD Xấu")
    
    if close > tenkan and close > kijun: score += 1; pros.append("Ichimoku Tốt")
    if vol_now > vol_avg*1.2 and close > df.iloc[-2]['Close']: score += 2; pros.append("Tiền vào mạnh")
    
    final_score = max(0, min(10, score))
    action = "QUAN SÁT"
    zone = "yellow-zone" # Mặc định
    if final_score >= 8: 
        action = "MUA MẠNH"
        zone = "green-zone"
    elif final_score >= 6: 
        action = "MUA THĂM DÒ"
        zone = "green-zone"
    elif final_score <= 3: 
        action = "BÁN / CẮT LỖ"
        zone = "red-zone"
    
    return {"score": final_score, "action": action, "zone": zone, "pros": pros, "cons": cons, "entry": close, "stop": close - 2*atr, "target": close + 3*atr}

# --- 2. CHẤM ĐIỂM CƠ BẢN (MỚI CHO V14) ---
def analyze_fundamental_score(info):
    scores = {}
    # Lấy chỉ số an toàn, nếu không có thì cho điểm trung bình
    pe = info.get('trailingPE', 0)
    if pe is None: pe = 0
    if 0 < pe < 15: scores['Định Giá'] = 8 # Rẻ
    elif 15 <= pe < 25: scores['Định Giá'] = 6 # Trung bình
    elif pe >= 25: scores['Định Giá'] = 3 # Đắt
    else: scores['Định Giá'] = 5 # N/A
    
    roe = info.get('returnOnEquity', 0)
    if roe is None: roe = 0
    if roe > 0.2: scores['Sinh Lời'] = 9
    elif roe > 0.1: scores['Sinh Lời'] = 6
    else: scores['Sinh Lời'] = 4
    
    rev_g = info.get('revenueGrowth', 0)
    if rev_g is None: rev_g = 0
    if rev_g > 0.15: scores['Tăng Trưởng'] = 9
    elif rev_g > 0.05: scores['Tăng Trưởng'] = 6
    else: scores['Tăng Trưởng'] = 3
    
    debt_eq = info.get('debtToEquity', 100)
    if debt_eq is None: debt_eq = 100
    if debt_eq < 50: scores['Sức Khỏe'] = 8
    elif debt_eq < 150: scores['Sức Khỏe'] = 5
    else: scores['Sức Khỏe'] = 3
    
    pm = info.get('profitMargins', 0)
    if pm is None: pm = 0
    if pm > 0.1: scores['Hiệu Quả'] = 8
    else: scores['Hiệu Quả'] = 4
    
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

def safe_fmt(val):
    try: return f"{int(val):,}"
    except: return "N/A"

# --- VẼ GAUGE CHART (ĐỒNG HỒ - MỚI) ---
def plot_gauge(score, action):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        title = {'text': f"KỸ THUẬT: {action}", 'font': {'size': 18, 'color': "white"}},
        gauge = {
            'axis': {'range': [None, 10], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#64b5f6"}, 'bgcolor': "black", 'borderwidth': 2, 'bordercolor': "gray",
            'steps': [{'range': [0, 3], 'color': '#ef4444'}, {'range': [3, 7], 'color': '#f59e0b'}, {'range': [7, 10], 'color': '#10b981'}],
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': score}}))
    fig.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    return fig

# --- VẼ RADAR CHART (BIỂU ĐỒ NHỆN - MỚI) ---
def plot_radar(scores):
    categories = list(scores.keys()); values = list(scores.values())
    categories = [*categories, categories[0]]; values = [*values, values[0]]
    fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', name='Điểm cơ bản', line_color='#29b6f6'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10], color='gray')), showlegend=False, height=250, margin=dict(l=40,r=40,t=30,b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    return fig

# --- VẼ PIE CHART (CỔ ĐÔNG - MỚI) ---
def plot_holders(df_holders):
    if df_holders.empty: return None
    try:
        labels = df_holders[1].tolist()
        values = []
        for v in df_holders[0].tolist():
            try: values.append(float(v.strip('%')))
            except: values.append(0)
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, showlegend=False)
        return fig
    except: return None

# --- VẼ CHART PRO (CŨ) ---
def render_pro_chart(df, symbol):
    row_h = [0.6, 0.2, 0.2]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'), row=1, col=1)
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
    if 'BBU_20_2.0' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='Lower', fill='tonexty'), row=1, col=1)
    colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    if 'MACD_12_26_9' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='#22d3ee', width=1.5), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], line=dict(color='#f472b6', width=1.5), name='Signal'), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], marker_color='#64748b', name='Hist'), row=3, col=1)
    fig.update_layout(height=700, template="plotly_dark", hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=True, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})

# ==========================================
# 🖥️ GIAO DIỆN CHÍNH
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    st.header("🔮 Phân Tích Đa Chiều (Multi-Dimension)")
    col_input, col_ref = st.columns([3, 1])
    with col_input: symbol = st.text_input("Nhập Mã CP", value="HPG").upper()
    with col_ref:
        if st.button("🔄 Cập nhật giá"): st.cache_data.clear(); st.rerun()

    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news = load_data_full(symbol, period)
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            
            # --- PHẦN MỚI (V14): ĐỒNG HỒ & RADAR ---
            tech_res = analyze_smart(df_calc)
            fund_scores = analyze_fundamental_score(info)
            
            if tech_res:
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.subheader("🔭 Sức Mạnh Kỹ Thuật")
                    st.plotly_chart(plot_gauge(tech_res['score'], tech_res['action']), use_container_width=True)
                    st.markdown(f"**Giá:** {tech_res['entry']:,.0f} | **Mục tiêu:** {tech_res['target']:,.0f}")
                    st.markdown('</div>', unsafe_allow_html=True)
                with g2:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.subheader("🏢 Sức Khỏe Doanh Nghiệp")
                    st.plotly_chart(plot_radar(fund_scores), use_container_width=True)
                    st.caption(f"P/E: {info.get('trailingPE','N/A')} | EPS: {info.get('trailingEps','N/A')}")
                    st.markdown('</div>', unsafe_allow_html=True)

            # --- TABS CŨ ---
            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ Kỹ Thuật", "📰 Tin Tức", "💰 Tài Chính", "🏢 Hồ Sơ & Cổ Đông"])
            with t1: render_pro_chart(df_chart, symbol)
            with t2:
                for item in news: st.markdown(f'<div class="news-item"><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a><div class="news-meta">🕒 {item["published"][:16]} | 🔗 {item["source"]}</div></div>', unsafe_allow_html=True)
            with t3:
                c_left, c_right = st.columns(2)
                with c_left: st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin).style.format("{:,.2f}"), use_container_width=True)
                with c_right: st.subheader("Cân Đối KT"); st.dataframe(clean_table(bal).style.format("{:,.2f}"), use_container_width=True)
            with t4:
                c1, c2 = st.columns([2, 1])
                with c1: 
                    st.subheader("Giới thiệu"); st.write(info.get('longBusinessSummary', ''))
                    st.subheader("Cơ Cấu Cổ Đông (V14)")
                    # TÍNH NĂNG V14: PIE CHART
                    pie_fig = plot_holders(holders)
                    if pie_fig: st.plotly_chart(pie_fig, use_container_width=True)
                    else: st.dataframe(holders, use_container_width=True)
                with c2:
                    st.info(f"Ngành: {info.get('industry', 'N/A')}")
                    st.success(f"Nhân sự: {safe_fmt(info.get('fullTimeEmployees', 'N/A'))}")

elif mode == "📊 Bảng Giá & Máy Quét":
    # --- GIỮ NGUYÊN 100% CODE CỦA V13.2 ---
    st.title("📊 Bảng Giá & Máy Quét Đa Năng")
    if st.button("🔄 Cập nhật dữ liệu toàn thị trường"): st.cache_data.clear(); st.rerun()
    
    all_tabs = ["🛠️ Tự Nhập (Manual)"] + list(STOCK_GROUPS.keys())
    tabs = st.tabs(all_tabs)
    
    with tabs[0]:
        st.caption("Nhập danh sách mã cổ phiếu bất kỳ để quét (cách nhau dấu phẩy).")
        inp = st.text_area("Danh sách mã:", value="HPG, VCB, SSI, VND, FPT, MWG, DIG", height=100)
        if st.button("🚀 QUÉT DANH SÁCH TỰ NHẬP"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            if len(ticks) > 30: ticks = ticks[:30]; st.warning("⚠️ Chỉ quét 30 mã đầu tiên.")
            res = []
            bar = st.progress(0, "Đang xử lý...")
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                try:
                    df, _, _, _, _, _, _, _ = load_data_full(t, "1y")
                    s = analyze_smart(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": f"{s['entry']:,.0f}"})
                except: pass
            bar.empty()
            if res:
                df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                def color_act(val):
                    if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                    if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                    return 'color: #f59e0b'
                st.dataframe(df_res.style.map(color_act, subset=['Hành động']), use_container_width=True)
            else: st.error("Không tìm thấy dữ liệu.")

    for tab, name in zip(tabs[1:], list(STOCK_GROUPS.keys())):
        with tab:
            if st.button(f"🚀 Quét Nhóm {name}", key=name):
                ticks = STOCK_GROUPS[name].split(',')
                res = []
                bar = st.progress(0, f"Đang quét {name}...")
                for i, t in enumerate(ticks):
                    bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                    try:
                        df, _, _, _, _, _, _, _ = load_data_full(t, "1y")
                        s = analyze_smart(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": f"{s['entry']:,.0f}"})
                    except: pass
                bar.empty()
                if res:
                    df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                    def color_act(val):
                        if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                        if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                        return 'color: #f59e0b'
                    st.dataframe(df_res.style.map(color_act, subset=['Hành động']), use_container_width=True)
                    if df_res.iloc[0]['Điểm'] >= 7: st.success(f"💎 NGÔI SAO DÒNG {name}: **{df_res.iloc[0]['Mã']}** ({df_res.iloc[0]['Điểm']} điểm)")

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V14.1 - The Perfect Hybrid</div>', unsafe_allow_html=True)
