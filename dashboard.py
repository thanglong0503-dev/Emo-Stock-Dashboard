import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Immortal V10.1", page_icon="🐲")

# ==========================================
# 🛡️ PHẦN BẢO MẬT & BẢO TRÌ
# ==========================================
MAINTENANCE_MODE = False 

if MAINTENANCE_MODE:
    st.title("🚧 HỆ THỐNG ĐANG BẢO TRÌ")
    st.warning("Hệ thống Thăng Long đang được nâng cấp. Vui lòng quay lại sau!")
    st.stop()

if "PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("🔒 Mật khẩu Hoàng Gia:", type="password")
    if pwd != st.secrets["PASSWORD"]:
        st.info("Vui lòng nhập mật khẩu để truy cập hệ thống.")
        st.stop()

# ==========================================
# 🎨 GIAO DIỆN & TỪ ĐIỂN (ĐÃ FIX MÀU CHỮ)
# ==========================================
st.markdown("""
<style>
    /* Ép buộc nền tối cho toàn bộ app để đồng bộ */
    .stApp {background-color: #0e1117;}
    
    h1, h2, h3 {color: #64b5f6 !important;}
    [data-testid="stMetricValue"] {font-size: 1.3rem !important; color: #e0e0e0;}
    
    /* Card Tín hiệu */
    .rec-card {
        background-color: #1f2937; border: 1px solid #374151;
        border-radius: 10px; padding: 20px; text-align: center;
        margin-bottom: 20px;
    }
    .score-circle {
        display: inline-block; width: 60px; height: 60px; line-height: 60px;
        border-radius: 50%; font-size: 24px; font-weight: bold; color: white;
        margin-bottom: 10px;
    }
    .green-zone {background-color: #10b981; box-shadow: 0 0 15px #10b981;}
    .red-zone {background-color: #ef4444; box-shadow: 0 0 15px #ef4444;}
    .yellow-zone {background-color: #f59e0b; box-shadow: 0 0 15px #f59e0b;}
    
    /* Tin tức (ĐÃ SỬA: Thêm nền đen và chữ sáng) */
    .news-item {
        background-color: #262730; /* Nền xám đậm */
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px; 
        border: 1px solid #444;
        transition: transform 0.2s;
    }
    .news-item:hover {
        transform: scale(1.01);
        border-color: #64b5f6;
    }
    .news-title {
        color: #ffffff !important; /* Chữ trắng tinh */
        font-weight: bold;
        font-size: 16px;
        text-decoration: none;
        display: block;
        margin-bottom: 5px;
    }
    .news-meta {
        color: #fb8c00; /* Màu cam sáng cho ngày tháng */
        font-size: 13px;
    }
    
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: #9ca3af; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #374151;}
</style>
""", unsafe_allow_html=True)

# Từ điển Full 35 chỉ số
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
if MAINTENANCE_MODE: st.sidebar.error("🚧 Đang Bảo Trì")
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "⚡ Máy Quét (Scanner)"])

# ==========================================
# 🧠 BỘ NÃO XỬ LÝ
# ==========================================

@st.cache_data(ttl=600)
def load_news_google(symbol):
    try:
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        return feed.entries[:10]
    except: return []

@st.cache_data(ttl=300)
def load_data_v10(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    try:
        df_calc = stock.history(period="1y")
        if len(df_calc) > 52:
            df_calc.ta.sma(length=20, append=True)
            df_calc.ta.sma(length=50, append=True)
            df_calc.ta.rsi(length=14, append=True)
            df_calc.ta.macd(append=True)
            df_calc.ta.adx(length=14, append=True)
            df_calc.ta.atr(length=14, append=True)
    except: df_calc = pd.DataFrame()

    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.sma(length=50, append=True)
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
    
    news_items = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news_items

def analyze_smart(df):
    if df.empty or len(df) < 52: return None
    now = df.iloc[-1]
    
    close = now['Close']; ma20 = now['SMA_20']; ma50 = now['SMA_50']
    rsi = now['RSI_14']; macd = now['MACD_12_26_9']; macds = now['MACDs_12_26_9']
    adx = now['ADX_14']; atr = now['ATRr_14']
    vol_now = now['Volume']; vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
    
    high9 = df['High'].rolling(9).max().iloc[-1]; low9 = df['Low'].rolling(9).min().iloc[-1]
    tenkan = (high9 + low9)/2
    high26 = df['High'].rolling(26).max().iloc[-1]; low26 = df['Low'].rolling(26).min().iloc[-1]
    kijun = (high26 + low26)/2

    score = 0
    pros, cons = [], []
    
    if close > ma20 and close > ma50: score += 2; pros.append("Uptrend (Giá > MA20, MA50)")
    if adx > 25: score += 1; pros.append(f"ADX Mạnh ({adx:.0f})")
    
    if rsi < 30: score += 3; pros.append("RSI Quá bán (Giá rẻ)")
    elif rsi > 70: score -= 2; cons.append("RSI Quá mua (Nóng)")
    
    if macd > macds: score += 1; pros.append("MACD cắt lên")
    else: score -= 1; cons.append("MACD cắt xuống")
    
    if close > tenkan and close > kijun: score += 1; pros.append("Ichimoku Tốt")
    if vol_now > vol_avg*1.2 and close > df.iloc[-2]['Close']: score += 2; pros.append("Tiền vào mạnh")
    
    final_score = max(0, min(10, 5 + score))
    action, zone = "QUAN SÁT", "yellow-zone"
    if final_score >= 8: action, zone = "MUA MẠNH", "green-zone"
    elif final_score >= 6: action, zone = "MUA THĂM DÒ", "green-zone"
    elif final_score <= 3: action, zone = "BÁN / CẮT LỖ", "red-zone"
    
    return {
        "score": final_score, "action": action, "zone": zone, "pros": pros, "cons": cons,
        "entry": close, "stop": close - 2*atr, "target": close + 3*atr
    }

def clean_table(df):
    if df.empty: return pd.DataFrame()
    valid = [i for i in df.index if i in TRANS_MAP]
    if not valid: return df
    df_new = df.loc[valid].rename(index=TRANS_MAP)
    for col in df_new.columns:
        for idx in df_new.index:
            if "EPS" not in idx and isinstance(df_new.loc[idx, col], (int, float)):
                df_new.loc[idx, col] = df_new.loc[idx, col] / 1e9
    return df_new

# ==========================================
# 🖥️ GIAO DIỆN CHÍNH
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    symbol = st.sidebar.text_input("Nhập Mã CP", value="HPG").upper()
    period = st.sidebar.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Biểu đồ")
    show_ma = st.sidebar.checkbox("MA", True)
    show_bb = st.sidebar.checkbox("Bollinger", True)
    show_macd = st.sidebar.checkbox("MACD", True)
    show_rsi = st.sidebar.checkbox("RSI", True)

    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news = load_data_v10(symbol, period)
        
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            
            # CARD KHUYẾN NGHỊ
            strat = analyze_smart(df_calc)
            if strat:
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"""
                    <div class="rec-card">
                        <div class="score-circle {strat['zone']}">{strat['score']}</div>
                        <h3>{strat['action']}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    k1, k2 = st.columns(2)
                    with k1: 
                        for p in strat['pros']: st.success(f"+ {p}")
                    with k2: 
                        for c in strat['cons']: st.error(f"- {c}")
                    st.divider()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Giá Vào", f"{strat['entry']:,.0f}")
                    m2.metric("Cắt Lỗ", f"{strat['stop']:,.0f}")
                    m3.metric("Mục Tiêu", f"{strat['target']:,.0f}")

            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ", "📰 Tin Tức (Google)", "💰 Tài Chính", "🏢 Hồ Sơ"])
            
            with t1:
                row_h = [0.5, 0.15, 0.2, 0.15]
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.03)
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Giá'), row=1, col=1)
                if show_ma:
                    if 'SMA_20' in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
                    if 'SMA_50' in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA_50'], line=dict(color='#2979ff', width=1), name='MA50'), row=1, col=1)
                if show_bb and 'BBU_20_2.0' in df_chart.columns:
                     fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Up'), row=1, col=1)
                     fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Low', fill='tonexty'), row=1, col=1)
                colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df_chart.iterrows()]
                fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=colors, name='Vol'), row=2, col=1)
                if show_macd and 'MACD_12_26_9' in df_chart.columns:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MACD_12_26_9'], line=dict(color='#22d3ee'), name='MACD'), row=3, col=1)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MACDs_12_26_9'], line=dict(color='#f472b6'), name='Signal'), row=3, col=1)
                    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['MACDh_12_26_9'], marker_color='#64748b', name='Hist'), row=3, col=1)
                if show_rsi and 'RSI_14' in df_chart.columns:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI_14'], line=dict(color='#a78bfa', width=2), name='RSI'), row=4, col=1)
                    fig.add_hline(y=70, row=4, col=1, line_dash="dot", line_color="#ef4444")
                    fig.add_hline(y=30, row=4, col=1, line_dash="dot", line_color="#10b981")
                fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

            with t2:
                if news:
                    for item in news:
                        try:
                            dt = item.get('published', '')[:16]
                            # ĐÃ FIX: Dùng class news-item có background màu tối và chữ màu sáng
                            st.markdown(f"""
                            <div class="news-item">
                                <a href="{item.link}" target="_blank" class="news-title">{item.title}</a>
                                <div class="news-meta">🕒 {dt} | 🔗 {item.source.title}</div>
                            </div>""", unsafe_allow_html=True)
                        except: pass
                else: st.warning("Không có tin tức mới.")

            with t3:
                c_left, c_right = st.columns(2)
                with c_left:
                    st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin).style.format("{:,.2f}"), use_container_width=True)
                    st.subheader("Dòng Tiền"); st.dataframe(clean_table(cash).style.format("{:,.2f}"), use_container_width=True)
                with c_right:
                    st.subheader("Cân Đối Kế Toán"); st.dataframe(clean_table(bal).style.format("{:,.2f}"), use_container_width=True)

            with t4:
                c1, c2 = st.columns([2, 1])
                with c1: st.write(info.get('longBusinessSummary', ''))
                with c2:
                    st.info(f"Ngành: {info.get('industry', 'N/A')}")
                    st.success(f"Nhân sự: {info.get('fullTimeEmployees', 'N/A')}")
                    st.write("---")
                    st.subheader("Cổ đông")
                    try:
                        if not holders.empty and holders.shape[1] == 2: holders.columns = ['% Nắm', 'Tên']
                        st.dataframe(holders, use_container_width=True)
                    except: st.write("No Data")

elif mode == "⚡ Máy Quét (Scanner)":
    st.title("⚡ Máy Quét Cơ Hội V10")
    inp = st.text_area("Mã CP:", "HPG, VCB, SSI, VND, FPT, MWG, VNM, MSN, DIG, CEO")
    if st.button("🚀 Quét"):
        ticks = [x.strip().upper() for x in inp.split(',')]
        res = []
        bar = st.progress(0, "AI đang xử lý...")
        for i, t in enumerate(ticks):
            bar.progress((i+1)/len(ticks), f"Checking {t}...")
            try:
                df, _, _, _, _, _, _, _ = load_data_v10(t, "1y")
                s = analyze_smart(df)
                if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá Vào": f"{s['entry']:,.0f}"})
            except: pass
        bar.empty()
        if res:
            df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
            def color_act(val):
                if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                return 'color: #f59e0b'
            st.dataframe(df_res.style.map(color_act, subset=['Hành động']), use_container_width=True)

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V10.1 - High Contrast</div>', unsafe_allow_html=True)
