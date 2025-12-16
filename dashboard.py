import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser # Thư viện lấy tin Google News
from datetime import datetime

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Warlord V9", page_icon="🐲")

# --- CSS: GIAO DIỆN CAO CẤP ---
st.markdown("""
<style>
    .main {background-color: #0e1117;}
    h1, h2, h3 {color: #64b5f6 !important;}
    [data-testid="stMetricValue"] {font-size: 1.3rem !important; color: #e0e0e0;}
    
    /* Card Khuyến nghị */
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
    
    /* Tin tức */
    .news-item {
        padding: 10px; border-bottom: 1px solid #333; margin-bottom: 10px;
    }
    .news-item:hover {background-color: #2d3748; border-radius: 5px;}
    .news-source {font-size: 11px; color: #64b5f6; font-weight: bold;}
    .news-time {font-size: 11px; color: #888;}
    
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: #6b7280; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #374151;}
</style>
""", unsafe_allow_html=True)

# --- TỪ ĐIỂN TÀI CHÍNH ---
TRANS_MAP = {
    'Total Revenue': '1. Tổng Doanh Thu', 'Gross Profit': '3. Lợi Nhuận Gộp',
    'Net Income': '9. Lợi Nhuận Sau Thuế', 'Basic EPS': '11. EPS Cơ Bản',
    'Total Assets': 'A. TỔNG TÀI SẢN', 'Total Liabilities Net Minority Interest': 'B. TỔNG NỢ',
    'Stockholders Equity': 'C. VỐN CHỦ SỞ HỮU', 'Operating Cash Flow': '1. Dòng Tiền KD'
}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.success("👑 **Chủ sở hữu: Thăng Long**")
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "⚡ Máy Quét (Scanner)"])

# --- HÀM LẤY TIN TỨC GOOGLE NEWS (MỚI) ---
@st.cache_data(ttl=600) # Cache 10 phút
def load_news_google(symbol):
    try:
        # Tạo URL tìm kiếm tin tức tiếng Việt cho mã cổ phiếu
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        return feed.entries[:10] # Lấy 10 tin mới nhất
    except:
        return []

# --- BỘ NÃO AI V9 (NÂNG CẤP MẠNH MẼ) ---
def analyze_advanced(df):
    if df.empty or len(df) < 52: return None
    
    # Dữ liệu hiện tại
    now = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 1. Indicator Calculation
    close = now['Close']
    ma20 = now['SMA_20']
    ma50 = now['SMA_50']
    rsi = now['RSI_14']
    macd = now['MACD_12_26_9']
    macds = now['MACDs_12_26_9']
    adx = now['ADX_14'] # Sức mạnh xu hướng
    vol_now = now['Volume']
    vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
    
    # Ichimoku (Tính tay đơn giản)
    high9 = df['High'].rolling(9).max().iloc[-1]
    low9 = df['Low'].rolling(9).min().iloc[-1]
    tenkan = (high9 + low9) / 2
    
    high26 = df['High'].rolling(26).max().iloc[-1]
    low26 = df['Low'].rolling(26).min().iloc[-1]
    kijun = (high26 + low26) / 2
    
    # 2. HỆ THỐNG CHẤM ĐIỂM (Thang 10)
    score = 0
    reasons_buy = []
    reasons_sell = []
    
    # A. Xu hướng (Trend) - Tối đa 3 điểm
    if close > ma20 and close > ma50: 
        score += 2; reasons_buy.append("Giá trên MA20 & MA50 (Uptrend ngắn hạn)")
    if adx > 25: 
        score += 1; reasons_buy.append(f"ADX = {adx:.0f} (Xu hướng đang mạnh)")
    
    # B. Động lượng (Momentum) - Tối đa 3 điểm
    if rsi < 30: 
        score += 3; reasons_buy.append("RSI Quá bán (Vùng giá rẻ để gom)")
    elif 30 <= rsi <= 60: 
        score += 1
    elif rsi > 70: 
        score -= 2; reasons_sell.append("RSI Quá mua (Cẩn thận chỉnh)")
        
    if macd > macds: 
        score += 1; reasons_buy.append("MACD cắt lên Signal")
    else: 
        score -= 1; reasons_sell.append("MACD cắt xuống")

    # C. Ichimoku & Volume - Tối đa 4 điểm
    if close > tenkan and close > kijun: 
        score += 2; reasons_buy.append("Giá nằm trên Tenkan/Kijun (Ichimoku Tốt)")
    
    if vol_now > vol_avg * 1.2: # Vol đột biến 20%
        if close > df.iloc[-2]['Close']:
            score += 2; reasons_buy.append("Dòng tiền vào mạnh (Vol lớn giá tăng)")
        else:
            score -= 2; reasons_sell.append("Bị bán tháo mạnh (Vol lớn giá giảm)")
    elif vol_now < vol_avg * 0.5:
        reasons_sell.append("Tiền chưa vào (Vol yếu)")

    # 3. KẾT LUẬN
    # Chuẩn hóa điểm về 0-10
    final_score = max(0, min(10, 5 + score)) # 5 là điểm gốc
    
    action = "QUAN SÁT"
    zone = "yellow-zone"
    advice = "Thị trường lưỡng lự. Nên chờ tín hiệu xác nhận."
    
    if final_score >= 8:
        action = "MUA MẠNH"
        zone = "green-zone"
        advice = "Các chỉ báo đều rất tốt. Dòng tiền ủng hộ. Canh mua ngay!"
    elif final_score >= 6:
        action = "MUA THĂM DÒ"
        zone = "green-zone"
        advice = "Xu hướng tốt nhưng cần quản trị rủi ro. Mua 30% tỷ trọng."
    elif final_score <= 3:
        action = "BÁN / CẮT LỖ"
        zone = "red-zone"
        advice = "Xu hướng xấu. Nên thoát hàng bảo toàn vốn."
        
    # Tính Stoploss/Target (Dựa trên ATR)
    atr = now['ATRr_14']
    stoploss = close - (2 * atr)
    target = close + (3 * atr) # R:R = 1.5
    
    return {
        "score": final_score, "action": action, "zone": zone, "advice": advice,
        "pros": reasons_buy, "cons": reasons_sell,
        "entry": close, "stop": stoploss, "target": target, "r_r": "1:1.5"
    }

# --- TẢI DỮ LIỆU ---
@st.cache_data(ttl=300)
def load_data_v9(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    
    # 1. Data tính toán (Luôn lấy 1 năm để tính chỉ báo chuẩn)
    try:
        df_calc = stock.history(period="1y")
        if len(df_calc) > 52:
            df_calc.ta.sma(length=20, append=True)
            df_calc.ta.sma(length=50, append=True)
            df_calc.ta.rsi(length=14, append=True)
            df_calc.ta.macd(append=True)
            df_calc.ta.adx(length=14, append=True) # Thêm ADX
            df_calc.ta.atr(length=14, append=True)
    except: df_calc = pd.DataFrame()

    # 2. Data vẽ chart (Theo user chọn)
    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.bbands(length=20, std=2, append=True)
            df_chart.ta.rsi(length=14, append=True)
            df_chart.ta.macd(append=True)
    except: df_chart = pd.DataFrame()

    # 3. Tài chính
    try: info = stock.info; 
    except: info = {}
    try: fin = stock.financials; 
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet; 
    except: bal = pd.DataFrame()
    
    # 4. Tin tức Google (Thay vì Yahoo)
    news_items = load_news_google(ticker)

    return df_calc, df_chart, info, fin, bal, news_items

# --- HỖ TRỢ ---
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
# GIAO DIỆN CHÍNH
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    symbol = st.sidebar.text_input("Mã CP", value="HPG").upper()
    period = st.sidebar.selectbox("Thời gian", ["1mo", "3mo", "6mo", "1y"], index=2)
    
    if symbol:
        df_calc, df_chart, info, fin, bal, news = load_data_v9(symbol, period)
        
        if not df_chart.empty:
            st.title(f"🐲 {info.get('longName', symbol)}")
            
            # --- PHẦN 1: BÁO CÁO CHIẾN LƯỢC V9 ---
            strat = analyze_advanced(df_calc)
            if strat:
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"""
                    <div class="rec-card">
                        <div class="score-circle {strat['zone']}">{strat['score']}</div>
                        <h3>{strat['action']}</h3>
                        <p style="font-size:14px; color:#aaa;">{strat['advice']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with c2:
                    st.subheader("📊 Chi Tiết Đánh Giá")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.markdown("**👍 Điểm Cộng:**")
                        for p in strat['pros']: st.success(f"+ {p}")
                    with cc2:
                        st.markdown("**👎 Điểm Trừ:**")
                        for c in strat['cons']: st.error(f"- {c}")
                        
                    st.divider()
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Giá Vào (Entry)", f"{strat['entry']:,.0f}")
                    k2.metric("Cắt Lỗ (Stop)", f"{strat['stop']:,.0f}")
                    k3.metric("Chốt Lời (Target)", f"{strat['target']:,.0f}")

            # --- PHẦN 2: TABS ---
            t1, t2, t3 = st.tabs(["📈 Biểu Đồ & Dòng Tiền", "📰 Tin Tức (Google)", "💰 Tài Chính"])
            
            with t1:
                row_h = [0.6, 0.2, 0.2]
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.03)
                
                # Price
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Giá'), row=1, col=1)
                if 'SMA_20' in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA_20'], line=dict(color='orange'), name='MA20'), row=1, col=1)
                if 'BBU_20_2.0' in df_chart.columns:
                     fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Up'), row=1, col=1)
                     fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Low', fill='tonexty'), row=1, col=1)
                
                # Volume
                colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df_chart.iterrows()]
                fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
                
                # MACD
                if 'MACD_12_26_9' in df_chart.columns:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MACD_12_26_9'], line=dict(color='#22d3ee'), name='MACD'), row=3, col=1)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MACDs_12_26_9'], line=dict(color='#f472b6'), name='Signal'), row=3, col=1)
                    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['MACDh_12_26_9'], marker_color='#64748b', name='Hist'), row=3, col=1)

                fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

            with t2:
                st.caption(f"Nguồn: Google News (Tổng hợp CafeF, Vietstock, VnEconomy...) cho {symbol}")
                if news:
                    for item in news:
                        try:
                            # Xử lý thời gian
                            pub_date = item.get('published', '')
                            # Cắt ngắn thời gian cho gọn
                            if len(pub_date) > 20: pub_date = pub_date[:16]
                            
                            st.markdown(f"""
                            <div class="news-item">
                                <a href="{item.link}" target="_blank" style="text-decoration:none; color:white; font-weight:bold;">{item.title}</a>
                                <div style="display:flex; justify-content:space-between; margin-top:5px;">
                                    <span class="news-source">Build by Thăng Long</span>
                                    <span class="news-time">{pub_date}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        except: pass
                else:
                    st.warning("Không tìm thấy tin tức gần đây.")

            with t3:
                c1, c2 = st.columns(2)
                with c1: st.dataframe(clean_table(fin).style.format("{:,.2f}"))
                with c2: st.dataframe(clean_table(bal).style.format("{:,.2f}"))

elif mode == "⚡ Máy Quét (Scanner)":
    st.title("⚡ Máy Quét V9")
    inp = st.text_area("Mã CP:", "HPG, VCB, SSI, VND, FPT, MWG, VNM, MSN, DIG, CEO")
    if st.button("🚀 Quét"):
        ticks = [x.strip().upper() for x in inp.split(',')]
        res = []
        bar = st.progress(0, "AI đang xử lý...")
        for i, t in enumerate(ticks):
            bar.progress((i+1)/len(ticks), f"Checking {t}...")
            try:
                df, _, _, _, _, _ = load_data_v9(t, "1y")
                s = analyze_advanced(df)
                if s:
                    res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá Vào": f"{s['entry']:,.0f}"})
            except: pass
        bar.empty()
        if res:
            df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
            def color_act(val):
                if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                return 'color: #f59e0b'
            st.dataframe(df_res.style.map(color_act, subset=['Hành động']), use_container_width=True)

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V9 - The Warlord</div>', unsafe_allow_html=True)
