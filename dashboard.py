import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Stock V13.2 Plus", page_icon="⚡")

# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP ĐA NGƯỜI DÙNG
# ==========================================
USERS_DB = {
    "admin": "admin123",      
    "stock": "stock123",          
    "guest": "123456",        
    "guest1": "123456",   
    "huydang": "123456",   
    "kieuoanh": "123456",   
    "uyennhi": "123456"   
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

def login():
    st.title("🔐 STOCK THANG LONG")
    st.write("Đăng nhập để tiếp tục.")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        username = st.text_input("Tên đăng nhập:")
        password = st.text_input("Mật khẩu:", type="password")
        if st.button("🚪 Đăng Nhập", type="primary"):
            if username in USERS_DB and USERS_DB[username] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = username
                st.success("✅ Thành công! Đang vào...")
                st.rerun()
            else:
                st.error("❌ Sai thông tin!")

if not st.session_state['logged_in']:
    login()
    st.stop()

# ==========================================
# 🎨 GIAO DIỆN & CẤU HÌNH CSS
# ==========================================
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.info(f"👤 Xin chào: **{st.session_state['user_name']}**")
if st.sidebar.button("👋 Đăng Xuất"):
    st.session_state['logged_in'] = False
    st.rerun()
st.sidebar.divider()

st.markdown("""
<style>
    h1, h2, h3 {color: #64b5f6 !important;}
    [data-testid="stMetricValue"] {font-size: 1.4rem !important; font-weight: bold !important;}
    .rec-card {background-color: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 20px;}
    .score-circle {display: inline-block; width: 60px; height: 60px; line-height: 60px; border-radius: 50%; font-size: 24px; font-weight: bold; color: white; margin-bottom: 10px;}
    .green-zone {background-color: #10b981; box-shadow: 0 0 15px #10b981;}
    .red-zone {background-color: #ef4444; box-shadow: 0 0 15px #ef4444;}
    .yellow-zone {background-color: #f59e0b; box-shadow: 0 0 15px #f59e0b;}
    .news-item {padding: 10px; border-bottom: 1px solid #444; margin-bottom: 10px;}
    .news-title {font-weight: bold; font-size: 16px; text-decoration: none; color: #90caf9;}
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: #6b7280; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #374151; z-index: 100;}
</style>
""", unsafe_allow_html=True)

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

TRANS_MAP = {'Total Revenue': '1. Tổng Doanh Thu', 'Net Income': '2. Lợi Nhuận Sau Thuế', 'Total Assets': '3. Tổng Tài Sản', 'Stockholders Equity': '4. Vốn Chủ Sở Hữu', 'Operating Cash Flow': '5. Dòng Tiền KD'}

mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét"])
if st.sidebar.button("🔄 Xóa Cache & Cập Nhật"):
    st.cache_data.clear(); st.rerun()

# ==========================================
# 🧠 XỬ LÝ DỮ LIỆU
# ==========================================
@st.cache_data(ttl=300)
def load_news_google(symbol):
    try:
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        return [{'title': e.title, 'link': e.link, 'published': e.get('published','')[:16]} for e in feed.entries[:10]]
    except: return []

@st.cache_data(ttl=300)
def load_data_v13(ticker, time):
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
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.bbands(length=20, std=2, append=True)
            df_chart.ta.rsi(length=14, append=True)
            df_chart.ta.macd(append=True)
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
    
    news = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news

# --- HÀM PHÂN TÍCH KỸ THUẬT (V13.2 CŨ) ---
def analyze_smart(df):
    if df.empty or len(df) < 52: return None
    now = df.iloc[-1]
    close = now['Close']; ma20 = now['SMA_20']; ma50 = now['SMA_50']
    rsi = now['RSI_14']; macd = now['MACD_12_26_9']; macds = now['MACDs_12_26_9']
    adx = now['ADX_14']; atr = now['ATRr_14']
    vol_now = now['Volume']; vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
    
    score = 0; pros = []; cons = []
    if close > ma20 and close > ma50: score += 2; pros.append("Uptrend")
    if adx > 25: score += 1; pros.append(f"ADX Mạnh ({adx:.0f})")
    if rsi < 30: score += 3; pros.append("RSI Quá bán")
    elif rsi > 70: score -= 2; cons.append("RSI Quá mua")
    if macd > macds: score += 1; pros.append("MACD cắt lên")
    else: score -= 1; cons.append("MACD cắt xuống")
    if vol_now > vol_avg*1.2: score += 1; pros.append("Tiền vào")
    
    final_score = max(0, min(10, 5 + score))
    action, zone = "QUAN SÁT", "yellow-zone"
    if final_score >= 8: action, zone = "MUA MẠNH", "green-zone"
    elif final_score >= 6: action, zone = "MUA THĂM DÒ", "green-zone"
    elif final_score <= 3: action, zone = "BÁN / CẮT LỖ", "red-zone"
    
    return {"score": final_score, "action": action, "zone": zone, "pros": pros, "cons": cons, "entry": close, "stop": close - 2*atr, "target": close + 3*atr}

# --- HÀM PHÂN TÍCH CƠ BẢN (MỚI THÊM VÀO) ---
def analyze_fundamental(info):
    if not info: return None
    score = 0; details = []
    
    # P/E
    pe = info.get('trailingPE', 0)
    if pe is None: pe = 0
    if 0 < pe < 12: score += 2; details.append(f"P/E Hấp dẫn ({pe:.1f}x)")
    elif 12 <= pe <= 20: score += 1; details.append(f"P/E Hợp lý ({pe:.1f}x)")
    else: details.append(f"P/E Khá cao ({pe:.1f}x)")
    
    # ROE
    roe = info.get('returnOnEquity', 0)
    if roe is None: roe = 0
    if roe > 0.15: score += 2; details.append(f"ROE Tốt ({roe:.1%})")
    
    # Debt
    debt = info.get('debtToEquity', 0)
    if debt is None: debt = 0
    if debt < 50: score += 1; details.append("Nợ vay thấp")

    # Xếp hạng
    health, color = ("TRUNG BÌNH", "#f59e0b") # Mặc định
    if score >= 4: health, color = ("KIM CƯƠNG 💎", "#10b981")
    elif score >= 2: health, color = ("VỮNG MẠNH 💪", "#3b82f6")
    elif score < 2: health, color = ("YẾU KÉM ⚠️", "#ef4444")
    
    return {"health": health, "color": color, "details": details}

# ==========================================
# 🛠️ HÀM HỖ TRỢ HIỂN THỊ
# ==========================================
def clean_table(df):
    if df.empty: return pd.DataFrame()
    valid = [i for i in df.index if i in TRANS_MAP]
    if not valid: return df
    df_new = df.loc[valid].rename(index=TRANS_MAP)
    for col in df_new.columns:
        for idx in df_new.index:
            if isinstance(df_new.loc[idx, col], (int, float)): df_new.loc[idx, col] = df_new.loc[idx, col] / 1e9
    return df_new

def safe_fmt(val):
    try: return f"{int(val):,}"
    except: return "N/A"

def render_pro_chart(df, symbol):
    row_h = [0.6, 0.2, 0.2]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'), row=1, col=1)
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
    if 'SMA_50' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='#2979ff', width=1), name='MA50'), row=1, col=1)
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
    st.header("🔮 Phân Tích Chuyên Sâu")
    c1, c2 = st.columns([3, 1])
    with c1: symbol = st.text_input("Nhập Mã CP", value="HPG").upper()
    with c2: 
        if st.button("🔄 Cập nhật giá"): st.cache_data.clear(); st.rerun()

    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news = load_data_v13(symbol, period)
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            
            # CHẠY PHÂN TÍCH
            strat = analyze_smart(df_calc)   # Kỹ thuật V13
            fund = analyze_fundamental(info) # Cơ bản (Mới thêm)

            # HIỂN THỊ KẾT QUẢ (2 CỘT)
            if strat:
                col_tech, col_fund = st.columns(2)
                
                # CỘT 1: KỸ THUẬT (V13)
                with col_tech:
                    st.markdown(f"""
                    <div class="rec-card" style="border-left: 5px solid {strat['zone'].split('-')[0]};">
                        <h4>🔭 GÓC NHÌN KỸ THUẬT</h4>
                        <div class="score-circle {strat['zone']}">{strat['score']}</div>
                        <h2 style="margin:0">{strat['action']}</h2>
                        <p style="color:gray; font-size:12px">Định thời điểm Mua/Bán</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.info(f"🎯 Mục tiêu: {strat['target']:,.0f} | 🛑 Cắt lỗ: {strat['stop']:,.0f}")
                    with st.expander("🔍 Chi tiết Kỹ Thuật", expanded=True):
                        for p in strat['pros']: st.success(f"+ {p}")
                        for c in strat['cons']: st.error(f"- {c}")

                # CỘT 2: CƠ BẢN (MỚI)
                with col_fund:
                    if fund:
                        st.markdown(f"""
                        <div class="rec-card" style="border-left: 5px solid {fund['color']};">
                            <h4>🏢 SỨC KHỎE DOANH NGHIỆP</h4>
                            <div style="font-size: 32px; font-weight:bold; margin: 15px 0; color: {fund['color']}">{fund['health']}</div>
                            <p style="color:gray; font-size:12px">Chất lượng Doanh nghiệp</p>
                        </div>
                        """, unsafe_allow_html=True)
                        with st.expander("🔍 Chi tiết Cơ Bản", expanded=True):
                            for d in fund['details']: st.write(f"✅ {d}")
                    else: st.warning("Chưa có dữ liệu cơ bản")

            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ Kỹ Thuật", "📰 Tin Tức", "💰 Tài Chính", "🏢 Hồ Sơ"])
            with t1: render_pro_chart(df_chart, symbol)
            with t2:
                for item in news: st.markdown(f'<div class="news-item"><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a><div class="news-meta">🕒 {item["published"][:16]}</div></div>', unsafe_allow_html=True)
            with t3:
                c_left, c_right = st.columns(2)
                with c_left: st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin).style.format("{:,.2f}"), use_container_width=True)
                with c_right: st.subheader("Cân Đối Kế Toán"); st.dataframe(clean_table(bal).style.format("{:,.2f}"), use_container_width=True)
            with t4:
                c1, c2 = st.columns([2, 1])
                with c1: st.write(info.get('longBusinessSummary', ''))
                with c2:
                    st.info(f"Ngành: {info.get('industry', 'N/A')}")
                    st.success(f"Nhân sự: {safe_fmt(info.get('fullTimeEmployees', 'N/A'))}")
                    try: st.dataframe(holders, use_container_width=True)
                    except: pass

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Bảng Giá & Máy Quét Đa Năng")
    if st.button("🔄 Cập nhật dữ liệu toàn thị trường"): st.cache_data.clear(); st.rerun()
    
    all_tabs = ["🛠️ Tự Nhập (Manual)"] + list(STOCK_GROUPS.keys())
    tabs = st.tabs(all_tabs)
    
    with tabs[0]:
        st.caption("Nhập danh sách mã cổ phiếu bất kỳ để quét (cách nhau dấu phẩy).")
        inp = st.text_area("Danh sách mã:", value="HPG, VCB, SSI, VND, FPT, MWG, DIG", height=100)
        if st.button("🚀 QUÉT DANH SÁCH TỰ NHẬP"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            res = []
            bar = st.progress(0, "Đang xử lý...")
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                try:
                    df, _, _, _, _, _, _, _ = load_data_v13(t, "1y")
                    s = analyze_smart(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": f"{s['entry']:,.0f}"})
                except: pass
            bar.empty()
            if res:
                df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                st.dataframe(df_res, use_container_width=True)

    for tab, name in zip(tabs[1:], list(STOCK_GROUPS.keys())):
        with tab:
            if st.button(f"🚀 Quét Nhóm {name}", key=name):
                ticks = STOCK_GROUPS[name].split(',')
                res = []
                bar = st.progress(0, f"Đang quét {name}...")
                for i, t in enumerate(ticks):
                    bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                    try:
                        df, _, _, _, _, _, _, _ = load_data_v13(t, "1y")
                        s = analyze_smart(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": f"{s['entry']:,.0f}"})
                    except: pass
                bar.empty()
                if res:
                    df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                    if not df_res.empty:
                        st.dataframe(df_res, use_container_width=True)
                        if df_res.iloc[0]['Điểm'] >= 7: st.success(f"💎 NGÔI SAO DÒNG {name}: **{df_res.iloc[0]['Mã']}** ({df_res.iloc[0]['Điểm']} điểm)")

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V13.2 Plus (Stable + Fundamental)</div>', unsafe_allow_html=True)
