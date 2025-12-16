import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB (BẮT BUỘC DÒNG ĐẦU TIÊN) ---
st.set_page_config(layout="wide", page_title="Stock Thang Long Ultimate", page_icon="🐲")

# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP (MULTI-USER)
# ==========================================

# Danh sách tài khoản
USERS_DB = {
    "admin": "admin123",      
    "stock": "stock123",          
    "guest": "123456",        
    "guest1": "123456",   
    "huydang": "123456",   
    "kieuoanh": "123456",   
    "uyennhi": "123456"   
}

# Khởi tạo session
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

# Chặn nếu chưa đăng nhập
if not st.session_state['logged_in']:
    login()
    st.stop()

# ==========================================
# 🎨 GIAO DIỆN & CẤU HÌNH CSS
# ==========================================
# Sidebar Logout
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.info(f"👤 Xin chào: **{st.session_state['user_name']}**")
if st.sidebar.button("👋 Đăng Xuất"):
    st.session_state['logged_in'] = False
    st.rerun()
st.sidebar.divider()

# CSS làm đẹp (QUAN TRỌNG ĐỂ HIỆN THẺ BÀI)
st.markdown("""
<style>
    h1, h2, h3 {color: #64b5f6 !important;}
    [data-testid="stMetricValue"] {font-size: 1.3rem !important; font-weight: bold !important; color: #4fc3f7 !important;}
    .rec-card {background-color: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 20px;}
    .score-circle {display: inline-block; width: 60px; height: 60px; line-height: 60px; border-radius: 50%; font-size: 24px; font-weight: bold; color: white; margin-bottom: 10px;}
    .green-zone {background-color: #10b981; box-shadow: 0 0 10px #10b981;}
    .red-zone {background-color: #ef4444; box-shadow: 0 0 10px #ef4444;}
    .yellow-zone {background-color: #f59e0b; box-shadow: 0 0 10px #f59e0b;}
    .news-item {padding: 10px; border-bottom: 1px solid #444;}
    .news-title {font-weight: bold; color: #90caf9; text-decoration: none;}
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: gray; text-align: center; padding: 5px; font-size: 12px; z-index: 100;}
</style>
""", unsafe_allow_html=True)

# Dữ liệu hằng số
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

# ==========================================
# 🧠 XỬ LÝ DỮ LIỆU (LOAD DATA)
# ==========================================
@st.cache_data(ttl=300)
def load_news_google(symbol):
    try:
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        return [{'title': e.title, 'link': e.link, 'published': e.get('published','')[:16]} for e in feed.entries[:10]]
    except: return []

@st.cache_data(ttl=300)
def load_data_final(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    
    # 1. Dữ liệu tính toán (2 năm để đủ cho EMA89)
    try:
        df_calc = stock.history(period="2y")
        if len(df_calc) > 100:
            # SuperTrend
            sti = ta.supertrend(df_calc['High'], df_calc['Low'], df_calc['Close'], length=10, multiplier=3)
            df_calc = df_calc.join(sti)
            # Indicators
            df_calc.ta.mfi(length=14, append=True)
            df_calc.ta.stochrsi(length=14, append=True)
            df_calc.ta.ema(length=34, append=True)
            df_calc.ta.ema(length=89, append=True)
            df_calc.ta.adx(length=14, append=True)
            df_calc.ta.atr(length=14, append=True)
            # MA cơ bản
            df_calc.ta.sma(length=20, append=True)
            df_calc.ta.sma(length=50, append=True)
    except: df_calc = pd.DataFrame()

    # 2. Dữ liệu vẽ biểu đồ (Chart)
    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.bbands(length=20, std=2, append=True)
    except: df_chart = pd.DataFrame()

    try: info = stock.info
    except: info = {}
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()
    try: cash = stock.cashflow
    except: cash = pd.DataFrame()
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    news = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news

# ==========================================
# 🧠 HÀM PHÂN TÍCH (LOGIC CỐT LÕI)
# ==========================================

# 1. Phân tích Kỹ Thuật (Smart V14)
def analyze_smart(df):
    if df.empty or len(df) < 100: return None
    now = df.iloc[-1]
    
    close = now['Close']
    try:
        # Tìm cột SuperTrend động
        st_col = [c for c in df.columns if 'SUPERT' in c][0] 
        supertrend = now[st_col]
    except: supertrend = close # Fallback nếu lỗi

    mfi = now.get('MFI_14', 50)
    k = now.get('STOCHRSIk_14_14_3_3', 50)
    d = now.get('STOCHRSId_14_14_3_3', 50)
    adx = now.get('ADX_14', 0)
    ema34 = now.get('EMA_34', 0)
    ema89 = now.get('EMA_89', 0)
    atr = now.get('ATRr_14', 0)

    score = 0; pros = []; cons = []

    # Logic
    if close > supertrend: score += 3; pros.append("SuperTrend: BÁO TĂNG")
    else: score -= 2; cons.append("SuperTrend: BÁO GIẢM")

    if ema34 > ema89 and close > ema34: score += 1; pros.append("Xu hướng dài hạn Tốt")
    elif close < ema89: score -= 1; cons.append("Gãy xu hướng dài hạn")

    if mfi < 20: score += 2; pros.append(f"MFI ({mfi:.0f}): Vùng gom hàng")
    elif mfi > 80: score -= 1; cons.append(f"MFI ({mfi:.0f}): Tiền vào quá nóng")

    if k < 20 and k > d: score += 2; pros.append("StochRSI: Đảo chiều Tăng")
    
    if adx > 25 and close > supertrend: pros.append(f"ADX ({adx:.0f}): Trend Tăng khỏe")

    # Tổng kết
    final_score = max(0, min(10, 4 + score))
    action, zone = "QUAN SÁT", "yellow-zone"
    if final_score >= 8: action, zone = "MUA MẠNH", "green-zone"
    elif final_score >= 6: action, zone = "MUA THĂM DÒ", "green-zone"
    elif final_score <= 3: action, zone = "BÁN / CẮT LỖ", "red-zone"
    
    stop_loss = close - 2*atr if close > supertrend else close + 2*atr
    take_profit = close + 3*atr if close > supertrend else close - 3*atr

    return {"score": final_score, "action": action, "zone": zone, "pros": pros, "cons": cons, "entry": close, "stop": stop_loss, "target": take_profit}

# 2. Phân tích Cơ Bản (Fundamental WOW)
def analyze_fundamental(info):
    if not info: return None
    score = 0; details = []
    
    pe = info.get('trailingPE', 0)
    if pe is None: pe = 0
    
    if 0 < pe < 12: score += 2; details.append(f"P/E Hấp dẫn ({pe:.1f}x)")
    elif 12 <= pe <= 20: score += 1; details.append(f"P/E Hợp lý ({pe:.1f}x)")
    else: details.append(f"P/E Khá cao ({pe:.1f}x)")
    
    roe = info.get('returnOnEquity', 0)
    if roe is None: roe = 0
    if roe > 0.15: score += 2; details.append(f"ROE Tốt ({roe:.1%})")
    
    debt = info.get('debtToEquity', 0)
    if debt is None: debt = 0
    if debt < 50: score += 1; details.append("Nợ vay thấp")

    # Xếp hạng
    health, color = ("YẾU KÉM", "#ef4444")
    if score >= 4: health, color = ("KIM CƯƠNG 💎", "#10b981")
    elif score >= 2: health, color = ("VỮNG MẠNH 💪", "#3b82f6")
    elif score >= 1: health, color = ("TRUNG BÌNH 😐", "#f59e0b")
    
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
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'))
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name='MA20'))
    if 'BBU_20_2.0' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='Upper'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='Lower', fill='tonexty'))
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 🖥️ MAIN UI (GIAO DIỆN CHÍNH)
# ==========================================
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét"])
if st.sidebar.button("🔄 Xóa Cache & Cập Nhật"):
    st.cache_data.clear(); st.rerun()

if mode == "🔮 Phân Tích Chuyên Sâu":
    st.header("🔮 Phân Tích Chuyên Sâu")
    c1, c2 = st.columns([3, 1])
    with c1: symbol = st.text_input("Nhập Mã CP", "HPG").upper()
    with c2: 
        if st.button("🚀 Phân Tích"): st.cache_data.clear(); st.rerun()
    
    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)

    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news = load_data_final(symbol, period)
        
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            
            # --- 1. CHẠY PHÂN TÍCH ---
            strat = analyze_smart(df_calc)
            fund = analyze_fundamental(info)
            
            # --- 2. HIỂN THỊ KẾT QUẢ (PHẦN NÀY LÀ CÁI NGÀI CẦN NHẤT) ---
            if strat:
                col_tech, col_fund = st.columns(2)
                
                # Cột Kỹ Thuật (TRÁI)
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
                    # Hiển thị chi tiết lý do (Nút bấm xem thêm)
                    with st.expander("🔍 Chi tiết Kỹ Thuật", expanded=True):
                        for p in strat['pros']: st.success(f"+ {p}")
                        for c in strat['cons']: st.error(f"- {c}")

                # Cột Cơ Bản (PHẢI)
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
                    else: st.warning("Thiếu dữ liệu cơ bản")

            # --- 3. TABS (Biểu đồ, Tin tức...) ---
            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ", "📰 Tin Tức", "💰 Tài Chính", "🏢 Hồ Sơ"])
            with t1: render_pro_chart(df_chart, symbol)
            with t2:
                for n in news: st.markdown(f'<div class="news-item"><a href="{n["link"]}" target="_blank" class="news-title">{n["title"]}</a><div class="news-meta">{n["published"]}</div></div>', unsafe_allow_html=True)
            with t3:
                c1, c2 = st.columns(2)
                with c1: st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin), use_container_width=True)
                with c2: st.subheader("Cân Đối"); st.dataframe(clean_table(bal), use_container_width=True)
            with t4:
                st.write(info.get('longBusinessSummary', ''))
                try: st.dataframe(holders, use_container_width=True)
                except: pass

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Máy Quét Siêu Hạng")
    tabs = st.tabs(["🛠️ Tự Nhập"] + list(STOCK_GROUPS.keys()))
    
    with tabs[0]:
        inp = st.text_area("Nhập mã (VD: HPG, SSI):", "HPG, VCB, SSI, VND, FPT")
        if st.button("🚀 Quét Ngay"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            res = []
            bar = st.progress(0)
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks))
                try:
                    df, _, _, _, _, _, _, _ = load_data_final(t, "2y")
                    s = analyze_smart(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": s['entry'], "Mục Tiêu": s['target']})
                except: pass
            bar.empty()
            if res:
                df_res = pd.DataFrame(res).sort_values("Điểm", ascending=False)
                st.dataframe(df_res, use_container_width=True)
    
    for i, (name, stocks) in enumerate(STOCK_GROUPS.items()):
        with tabs[i+1]:
            if st.button(f"Quét {name}", key=name):
                ticks = stocks.split(',')
                res = []
                bar = st.progress(0)
                for j, t in enumerate(ticks):
                    bar.progress((j+1)/len(ticks))
                    try:
                        df, _, _, _, _, _, _, _ = load_data_final(t, "2y")
                        s = analyze_smart(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": s['entry']})
                    except: pass
                bar.empty()
                if res:
                    st.dataframe(pd.DataFrame(res).sort_values("Điểm", ascending=False), use_container_width=True)

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V14.5 - Ultimate Edition (Full Feature)</div>', unsafe_allow_html=True)
