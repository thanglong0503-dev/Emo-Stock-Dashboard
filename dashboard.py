import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="ThangLong Stock Ultimate", page_icon="💎")

# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP
# ==========================================
USERS_DB = {
    "admin": "admin123", "stock": "stock123", "guest": "123456",
    "guest1": "123456", "huydang": "123456", "kieuoanh": "123456", "uyennhi": "123456"
}

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""

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
            else: st.error("❌ Sai thông tin!")

if not st.session_state['logged_in']: login(); st.stop()

# ==========================================
# 🎨 GIAO DIỆN DARK MODE PRO
# ==========================================
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.info(f"👤 Hi: **{st.session_state['user_name']}**")
if st.sidebar.button("👋 Đăng Xuất"): st.session_state['logged_in'] = False; st.rerun()
st.sidebar.divider()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif !important; color: #e2e8f0;}
    h1, h2, h3 {color: #ffffff !important; font-weight: 700 !important; text-shadow: 0px 0px 10px rgba(0,0,0,0.5);}
    .rec-card {background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 20px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);}
    .rec-card h4 {color: #94a3b8 !important; text-transform: uppercase; letter-spacing: 1px; font-size: 0.9rem;}
    [data-testid="stMetricValue"] {font-size: 1.6rem !important; font-weight: 800 !important; color: #38bdf8 !important;}
    [data-testid="stMetricLabel"] {color: #cbd5e1 !important;}
    .score-circle {display: inline-block; width: 80px; height: 80px; line-height: 80px; border-radius: 50%; font-size: 32px; font-weight: 800; color: white; margin-bottom: 15px; box-shadow: 0 0 20px rgba(0,0,0,0.3);}
    .green-zone {background: linear-gradient(135deg, #10b981, #059669);}
    .red-zone {background: linear-gradient(135deg, #ef4444, #b91c1c);}
    .yellow-zone {background: linear-gradient(135deg, #f59e0b, #d97706);}
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #0f172a; color: #64748b; text-align: center; font-size: 12px; padding: 10px; border-top: 1px solid #1e293b; z-index: 100;}
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
if st.sidebar.button("🔄 Xóa Cache & Cập Nhật"): st.cache_data.clear(); st.rerun()

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
def load_data_final(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    
    # 1. DỮ LIỆU TÍNH TOÁN
    try:
        df_calc = stock.history(period="2y")
        if len(df_calc) > 100:
            sti = ta.supertrend(df_calc['High'], df_calc['Low'], df_calc['Close'], length=10, multiplier=3)
            df_calc = df_calc.join(sti) 
            df_calc.ta.mfi(length=14, append=True)
            df_calc.ta.stochrsi(length=14, append=True)
            df_calc.ta.ema(length=34, append=True); df_calc.ta.ema(length=89, append=True)
            df_calc.ta.adx(length=14, append=True); df_calc.ta.atr(length=14, append=True)
            df_calc.ta.sma(length=20, append=True); df_calc.ta.sma(length=50, append=True)
    except: df_calc = pd.DataFrame()

    # 2. DỮ LIỆU BIỂU ĐỒ
    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.bbands(length=20, std=2, append=True)
    except: df_chart = pd.DataFrame()

    # 3. DỮ LIỆU TÀI CHÍNH (QUAN TRỌNG)
    try: info = stock.info # Có thể bị rỗng do lỗi Yahoo
    except: info = {}
    try: fin = stock.financials # Báo cáo lãi lỗ
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet # Bảng cân đối
    except: bal = pd.DataFrame()
    try: cash = stock.cashflow # Dòng tiền
    except: cash = pd.DataFrame()
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    # Thử lấy market cap từ fast_info (ổn định hơn info)
    try: 
        mkt_cap = stock.fast_info['market_cap']
        if info is None: info = {}
        info['marketCap'] = mkt_cap
    except: pass

    news = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news

# ==========================================
# 🧠 HÀM PHÂN TÍCH (ĐÃ SỬA ĐỂ TỰ TÍNH TOÁN)
# ==========================================
def analyze_smart(df):
    if df.empty or len(df) < 100: return None
    now = df.iloc[-1]
    close = now['Close']
    try: st_col = [c for c in df.columns if 'SUPERT' in c][0]; supertrend = now[st_col]
    except: supertrend = close 

    mfi = now.get('MFI_14', 50); k = now.get('STOCHRSIk_14_14_3_3', 50); d = now.get('STOCHRSId_14_14_3_3', 50)
    adx = now.get('ADX_14', 0); ema34 = now.get('EMA_34', 0); ema89 = now.get('EMA_89', 0); atr = now.get('ATRr_14', 0)

    score = 0; pros = []; cons = []
    if close > supertrend: score += 3; pros.append("SuperTrend: BÁO TĂNG (Bullish)")
    else: score -= 2; cons.append("SuperTrend: BÁO GIẢM (Bearish)")

    if ema34 > ema89 and close > ema34: score += 1; pros.append("EMA System: Xu hướng Tốt")
    elif close < ema89: score -= 1; cons.append("EMA System: Gãy xu hướng")

    if mfi < 20: score += 2; pros.append(f"MFI ({mfi:.0f}): Vùng gom hàng")
    elif mfi > 80: score -= 1; cons.append(f"MFI ({mfi:.0f}): Tiền vào quá nóng")
    elif mfi > 50 and mfi > df.iloc[-2]['MFI_14']: score += 1; pros.append("MFI: Dòng tiền vào")

    if k < 20 and k > d: score += 2; pros.append("StochRSI: Đảo chiều Tăng")
    if adx > 25 and close > supertrend: pros.append(f"ADX ({adx:.0f}): Trend Tăng khỏe")

    final_score = max(0, min(10, 4 + score))
    action, zone = "QUAN SÁT", "yellow-zone"
    if final_score >= 8: action, zone = "MUA MẠNH", "green-zone"
    elif final_score >= 6: action, zone = "MUA THĂM DÒ", "green-zone"
    elif final_score <= 3: action, zone = "BÁN / CẮT LỖ", "red-zone"
    
    # Sửa lại Stoploss cho chiều Mua
    stop_loss = close - 2*atr
    take_profit = close + 3*atr

    return {"score": final_score, "action": action, "zone": zone, "pros": pros, "cons": cons, "entry": close, "stop": stop_loss, "target": take_profit}

# --- CẢI TIẾN: TỰ TÍNH CHỈ SỐ CƠ BẢN KHI YAHOO LỖI ---
def analyze_fundamental(info, fin, bal, price_now):
    score = 0; details = []
    
    # 1. Lấy dữ liệu thô từ BCTC nếu Info bị lỗi
    try:
        # P/E Calculation
        pe = info.get('trailingPE', 0)
        if (pe is None or pe == 0) and not fin.empty:
            # Tự tính P/E = Price / (Net Income / Shares) hoặc Price / EPS
            # Đơn giản: Lấy lợi nhuận gần nhất
            net_income = fin.loc['Net Income'].iloc[0]
            # Giả định số lượng cổ phiếu (khó lấy chính xác nếu info lỗi, dùng vốn hóa/giá nếu có)
            mkt_cap = info.get('marketCap', 0)
            if mkt_cap > 0 and net_income > 0:
                pe = mkt_cap / net_income
            
        # ROE Calculation
        roe = info.get('returnOnEquity', 0)
        if (roe is None or roe == 0) and not fin.empty and not bal.empty:
            net_income = fin.loc['Net Income'].iloc[0]
            equity = bal.loc['Stockholders Equity'].iloc[0]
            if equity > 0: roe = net_income / equity
            
        # Debt Calculation
        debt_ratio = 0
        if not bal.empty:
            try:
                total_debt = bal.loc['Total Debt'].iloc[0]
                equity = bal.loc['Stockholders Equity'].iloc[0]
                if equity > 0: debt_ratio = (total_debt / equity) * 100
            except: pass
            
    except: 
        pe = 0; roe = 0; debt_ratio = 0

    # 2. Chấm điểm
    # P/E
    if 0 < pe < 12: score += 2; details.append(f"P/E Hấp dẫn ({pe:.1f}x)")
    elif 12 <= pe <= 20: score += 1; details.append(f"P/E Hợp lý ({pe:.1f}x)")
    elif pe > 20: details.append(f"P/E Khá cao ({pe:.1f}x)")
    
    # ROE
    if roe > 0.15: score += 2; details.append(f"ROE Tốt ({roe:.1%})")
    elif roe > 0.10: score += 1; details.append(f"ROE Ổn ({roe:.1%})")
    
    # Debt
    if 0 < debt_ratio < 60: score += 1; details.append(f"Nợ vay thấp ({debt_ratio:.0f}%)")
    elif debt_ratio > 150: details.append(f"⚠️ Nợ vay cao ({debt_ratio:.0f}%)")

    # Nếu không có dữ liệu gì cả
    if score == 0 and len(details) == 0:
        details.append("Không đủ dữ liệu BCTC để tính toán")

    health, color = ("TRUNG BÌNH", "#f59e0b")
    if score >= 4: health, color = ("KIM CƯƠNG 💎", "#10b981")
    elif score >= 2: health, color = ("VỮNG MẠNH 💪", "#3b82f6")
    elif score < 2: health, color = ("YẾU KÉM ⚠️", "#ef4444")
    
    return {"health": health, "color": color, "details": details}

# ==========================================
# 🛠️ HÀM HỖ TRỢ
# ==========================================
def clean_table(df):
    if df.empty: return pd.DataFrame()
    valid = [i for i in df.index if i in TRANS_MAP]
    if not valid: return df
    df_new = df.loc[valid].rename(index=TRANS_MAP)
    for col in df_new.columns:
        for idx in df_new.index:
            if isinstance(df_new.loc[idx, col], (int, float)): 
                df_new.loc[idx, col] = df_new.loc[idx, col] / 1e9
    return df_new

def safe_fmt(val):
    try: return f"{int(val):,}"
    except: return "N/A"

def render_pro_chart(df, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'), row=1, col=1)
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
    if 'BBU_20_2.0' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='Lower', fill='tonexty'), row=1, col=1)
    
    colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 🖥️ MAIN UI
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    st.header("🔮 Phân Tích Chuyên Sâu")
    c1, c2 = st.columns([3, 1])
    with c1: symbol = st.text_input("Nhập Mã CP", value="HPG").upper()
    with c2: 
        if st.button("🔄 Cập nhật giá"): st.cache_data.clear(); st.rerun()

    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news = load_data_final(symbol, period)
        if not df_chart.empty:
            price_now = df_calc.iloc[-1]['Close']
            long_name = info.get('longName', symbol)
            st.title(f"💎 {long_name}")
            
            # --- CHẠY PHÂN TÍCH ---
            strat = analyze_smart(df_calc)   
            # Truyền thêm fin, bal, price vào để tự tính toán
            fund = analyze_fundamental(info, fin, bal, price_now) 

            if strat:
                col_tech, col_fund = st.columns(2)
                
                # CỘT 1: KỸ THUẬT
                with col_tech:
                    st.markdown(f"""
                    <div class="rec-card" style="border-left: 5px solid {strat['zone'].split('-')[0]};">
                        <h4>🔭 GÓC NHÌN KỸ THUẬT</h4>
                        <div class="score-circle {strat['zone']}">{strat['score']}</div>
                        <h2 style="margin:0">{strat['action']}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    k1, k2, k3 = st.columns(3)
                    k1.metric("💰 Giá", f"{strat['entry']:,.0f}")
                    k2.metric("🛑 Cắt Lỗ", f"{strat['stop']:,.0f}", delta=f"-{(strat['entry']-strat['stop']):,.0f}", delta_color="normal") 
                    k3.metric("🎯 Mục Tiêu", f"{strat['target']:,.0f}", delta=f"+{(strat['target']-strat['entry']):,.0f}", delta_color="normal")
                    
                    with st.expander("🔍 Chi tiết Kỹ Thuật"):
                        for p in strat['pros']: st.success(f"+ {p}")
                        for c in strat['cons']: st.error(f"- {c}")

                # CỘT 2: CƠ BẢN (ĐÃ FIX LỖI TRỐNG TRƠN)
                with col_fund:
                    st.markdown(f"""
                    <div class="rec-card" style="border-left: 5px solid {fund['color']};">
                        <h4>🏢 SỨC KHỎE DOANH NGHIỆP</h4>
                        <div style="font-size: 36px; font-weight:bold; margin: 15px 0; color: {fund['color']}">{fund['health']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("🔍 Chi tiết Cơ Bản (Tự tính từ BCTC)", expanded=True):
                        for d in fund['details']: 
                            if "cao" in d: st.warning(f"⚠️ {d}")
                            else: st.write(f"✅ {d}")

            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ", "📰 Tin Tức", "💰 Tài Chính", "🏢 Hồ Sơ"])
            with t1: render_pro_chart(df_chart, symbol)
            with t2:
                for item in news: st.markdown(f'<div class="news-item"><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a><div class="news-meta">🕒 {item["published"][:16]}</div></div>', unsafe_allow_html=True)
            with t3:
                c_left, c_right = st.columns(2)
                with c_left: st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin), use_container_width=True)
                with c_right: st.subheader("Cân Đối Kế Toán"); st.dataframe(clean_table(bal), use_container_width=True)
            with t4:
                c1, c2 = st.columns([2, 1])
                with c1: 
                    summary = info.get('longBusinessSummary', 'Hiện chưa có mô tả từ Yahoo Finance cho mã này.')
                    st.write(summary)
                with c2:
                    st.info(f"Ngành: {info.get('industry', 'N/A')}")
                    st.success(f"Nhân sự: {safe_fmt(info.get('fullTimeEmployees', 'N/A'))}")

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Máy Quét Siêu Hạng")
    if st.button("🚀 QUÉT NGAY"):
        ticks = ["HPG", "SSI", "VND", "FPT", "MWG", "DIG", "CEO", "VCB", "STB", "TCB"]
        res = []
        bar = st.progress(0, "Đang xử lý...")
        for i, t in enumerate(ticks):
            bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
            try:
                df, _, _, _, _, _, _, _ = load_data_final(t, "1y")
                s = analyze_smart(df)
                if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": f"{s['entry']:,.0f}"})
            except: pass
        bar.empty()
        st.dataframe(pd.DataFrame(res).sort_values(by="Điểm", ascending=False), use_container_width=True)

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V15.5 Final Fix</div>', unsafe_allow_html=True)
