import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime, timedelta
import requests
import streamlit.components.v1 as components

# --- THƯ VIỆN AI (PROPHET) ---
try:
    from prophet import Prophet
    from prophet.plot import plot_plotly
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="ThangLong Ultimate V36.1", page_icon="🐲")

# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP
# ==========================================
USERS_DB = {
    "admin": "admin123", "stock": "stock123", "guest": "123456",
    "guest1": "123456", "huydang": "123456", "kieuoanh": "123456", "uyennhi": "123456",
    "Mrquynh": "123456", "Msnhung": "123456", "thanhduc": "123456", "quyen": "123456"
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
# 🎨 GIAO DIỆN ADAPTIVE
# ==========================================
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.info(f"👤 Hi: **{st.session_state['user_name']}**")
if st.sidebar.button("👋 Đăng Xuất"): st.session_state['logged_in'] = False; st.rerun()
st.sidebar.divider()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif !important;}
    h1, h2, h3 {font-weight: 800 !important; text-shadow: 0px 0px 10px rgba(128,128,128,0.2);}
    
    .rec-card {
        background-color: var(--secondary-background-color); 
        border: 2px solid var(--text-color); 
        border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; 
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .rec-card h4 {color: var(--text-color) !important; opacity: 0.8; text-transform: uppercase; font-size: 0.85rem; font-weight: 700;}
    .rec-card h2 {color: var(--primary-color) !important; font-weight: 900 !important; font-size: 2rem !important;}
    [data-testid="stMetricValue"] {font-size: 1.6rem !important; font-weight: 900 !important; color: #0ea5e9 !important;}
    
    .score-circle {
        display: inline-block; width: 70px; height: 70px; line-height: 70px; 
        border-radius: 50%; font-size: 28px; font-weight: 900; color: white; 
        margin-bottom: 10px; box-shadow: 0 0 15px rgba(0,0,0,0.3);
    }
    .green-zone {background: linear-gradient(135deg, #10b981, #059669);}
    .red-zone {background: linear-gradient(135deg, #ef4444, #b91c1c);}
    .yellow-zone {background: linear-gradient(135deg, #f59e0b, #d97706);}
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%; background: var(--secondary-background-color); 
        color: var(--text-color); text-align: center; font-size: 12px; padding: 10px; 
        border-top: 1px solid var(--text-color); z-index: 100; opacity: 0.9;
    }
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

mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét", "📘 Hướng Dẫn & Quy Tắc"])
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
    try:
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        stock = yf.Ticker(t, session=session)
    except: stock = yf.Ticker(t)
    
    # 1. KỸ THUẬT
    try:
        df_calc = stock.history(period="2y")
        if len(df_calc) > 100:
            sti = ta.supertrend(df_calc['High'], df_calc['Low'], df_calc['Close'], length=10, multiplier=3)
            df_calc = df_calc.join(sti) 
            df_calc.ta.mfi(length=14, append=True); df_calc.ta.stochrsi(length=14, append=True)
            df_calc.ta.ema(length=34, append=True); df_calc.ta.ema(length=89, append=True)
            df_calc.ta.adx(length=14, append=True); df_calc.ta.atr(length=14, append=True)
            df_calc.ta.rsi(length=14, append=True); df_calc.ta.cci(length=20, append=True)
            df_calc.ta.sma(length=20, close='Volume', prefix='VOL', append=True) 
            df_calc.ta.bbands(length=20, std=2, append=True)
            df_calc.ta.sma(length=20, append=True); df_calc.ta.sma(length=50, append=True)
            # Ichimoku
            try:
                ichi = ta.ichimoku(df_calc['High'], df_calc['Low'], df_calc['Close'], tenkan=9, kijun=26, senkou=52)
                if ichi is not None: df_calc = pd.concat([df_calc, ichi[0]], axis=1)
            except: pass
    except: df_calc = pd.DataFrame()

    # 2. BIỂU ĐỒ (Cần dữ liệu để vẽ nến)
    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.bbands(length=20, std=2, append=True)
            # Ichimoku Chart
            if interval == '1d':
                try:
                    ichi_chart = ta.ichimoku(df_chart['High'], df_chart['Low'], df_chart['Close'])
                    if ichi_chart is not None: df_chart = pd.concat([df_chart, ichi_chart[0]], axis=1)
                except: pass
    except: df_chart = pd.DataFrame()

    # 3. INFO & BCTC (Sử dụng logic xử lý lỗi V36.1)
    try: info = stock.info
    except: info = {}
    
    # Fallback cơ bản để không lỗi code
    if info is None: info = {}
    try: 
        fast = stock.fast_info
        if info.get('marketCap') is None: info['marketCap'] = fast.get('market_cap', 0)
        if info.get('currentPrice') is None: info['currentPrice'] = fast.get('last_price', 0)
    except: pass
    
    info['longName'] = info.get('longName', f"Cổ Phiếu {ticker}")

    try: fin = stock.quarterly_financials; bal = stock.quarterly_balance_sheet; cash = stock.quarterly_cashflow; holders = stock.major_holders
    except: fin, bal, cash, holders = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try: dividends = stock.dividends; splits = stock.splits
    except: dividends, splits = pd.Series(dtype='float64'), pd.Series(dtype='float64')

    news = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news, dividends, splits

# ==========================================
# 🧠 MONTE CARLO SIMULATION
# ==========================================
def run_monte_carlo(df, days=30, simulations=1000):
    if df.empty: return None, None, None
    data = df['Close']; returns = data.pct_change().dropna()
    mu = returns.mean(); sigma = returns.std(); last_price = data.iloc[-1]
    drift = mu - 0.5 * sigma**2; Z = np.random.normal(0, 1, (days, simulations))
    daily_returns = np.exp(drift + sigma * Z)
    price_paths = np.zeros_like(daily_returns); price_paths[0] = last_price
    for t in range(1, days): price_paths[t] = price_paths[t-1] * daily_returns[t]
    simulation_df = pd.DataFrame(price_paths)
    
    fig = go.Figure()
    dates = [datetime.now() + timedelta(days=i) for i in range(days)]
    for i in range(min(50, simulations)): fig.add_trace(go.Scatter(x=dates, y=simulation_df.iloc[:, i], mode='lines', line=dict(width=1), opacity=0.3, showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=dates, y=simulation_df.mean(axis=1), mode='lines', line=dict(color='#22d3ee', width=4), name='Trung Bình'))
    fig.update_layout(title=dict(text=f"🌌 Đa Vũ Trụ: {simulations} Kịch Bản", font=dict(size=20)), yaxis_title="Giá", template="plotly_dark", height=600, hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=50,b=0))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
    
    final_prices = simulation_df.iloc[-1]
    stats = { "mean": final_prices.mean(), "top_5": np.percentile(final_prices, 95), "bot_5": np.percentile(final_prices, 5), "prob_up": (final_prices > last_price).mean() * 100 }
    fig_hist = px.histogram(final_prices, nbins=50, title="📊 Phân Phối Giá Cuối Kỳ")
    fig_hist.add_vline(x=last_price, line_dash="dash", line_color="red", annotation_text="Hiện Tại")
    fig_hist.update_layout(template="plotly_dark", showlegend=False, margin=dict(l=0,r=0,t=50,b=0))
    return fig, fig_hist, stats

# ==========================================
# 🧠 AI PREDICTION (FIXED V36.3: SAFE MODE)
# ==========================================
def run_prophet_forecast(df, periods=90):
    if not PROPHET_AVAILABLE: return None, "⚠️ Chưa cài thư viện Prophet."
    try:
        # Chuẩn bị dữ liệu
        df_prophet = df.reset_index()[['Date', 'Close']].copy()
        df_prophet.columns = ['ds', 'y']
        df_prophet['ds'] = df_prophet['ds'].dt.tz_localize(None)
        
        # --- 🛠️ FIX V36.3: CẤU HÌNH AN TOÀN ---
        m = Prophet(
            daily_seasonality=False,      # Bật sóng ngày
            weekly_seasonality=True,      # Bật sóng tuần
            yearly_seasonality=True,      # Bật sóng năm
            changepoint_prior_scale=0.05, # Độ nhạy trung bình (vừa đủ mượt, không quá giật)
            seasonality_mode='additive'   # <-- QUAN TRỌNG NHẤT: Chế độ 'Cộng' an toàn, tránh lỗi giá âm
        )
        
        m.fit(df_prophet)
        
        # Dự báo
        future = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
        
        # Vẽ biểu đồ
        fig = plot_plotly(m, forecast)
        
        # Tùy chỉnh màu sắc cho đẹp mắt
        fig.data[0].marker.color = '#22d3ee' # Màu nến thực tế (Xanh Neon)
        fig.data[1].line.color = '#f472b6'   # Màu đường dự báo (Hồng Phấn)
        # Cố gắng chỉnh màu vùng mây (nếu plotly cho phép truy cập)
        try: fig.data[2]['marker']['color'] = 'rgba(244, 114, 182, 0.2)' 
        except: pass

        fig.update_layout(
            title=dict(text="🔮 AI Prophet: Dự Báo Xu Hướng (Safe Mode)", font=dict(size=20)), 
            yaxis_title="Giá Dự Kiến", 
            template="plotly_dark", 
            height=600, 
            hovermode="x unified", 
            dragmode="pan", 
            margin=dict(l=0,r=0,t=50,b=0)
        )
        fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
        return fig, None
    except Exception as e: return None, f"Lỗi dự báo: {str(e)}"

# ==========================================
# 🧠 PHÂN TÍCH KỸ THUẬT
# ==========================================
def analyze_smart(df):
    if df.empty or len(df) < 50: return None
    now = df.iloc[-1]; prev = df.iloc[-2]; close = now['Close']
    try: st_col = [c for c in df.columns if 'SUPERT' in c][0]; supertrend = now[st_col]
    except: supertrend = close 
    mfi = now.get('MFI_14', 50); k = now.get('STOCHRSIk_14_14_3_3', 50); d = now.get('STOCHRSId_14_14_3_3', 50)
    ema34 = now.get('EMA_34', 0); ema89 = now.get('EMA_89', 0); atr = now.get('ATRr_14', 0); rsi = now.get('RSI_14', 50)
    vol_now = now['Volume']; vol_avg = now.get('VOL_SMA_20', vol_now)
    bb_upper = now.get('BBU_20_2.0', 0); bb_lower = now.get('BBL_20_2.0', 0); bb_mid = now.get('BBM_20_2.0', close)
    bandwidth = (bb_upper - bb_lower) / bb_mid if bb_mid > 0 else 0
    tenkan = now.get('ITS_9', 0); kijun = now.get('IKS_26', 0)
    
    score = 0; pros = []; cons = []
    
    if vol_now > 1.5 * vol_avg and close > prev['Close']: score += 2; pros.append(f"🔥 VSA: Tiền vào ồ ạt")
    elif vol_now > 1.2 * vol_avg and close > prev['Close']: score += 1; pros.append("VSA: Dòng tiền tốt")
    if bandwidth < 0.10: 
        pros.append("⚡ Bollinger: Nút thắt cổ chai")
        if close > bb_upper: score += 2; pros.append("=> Breakout Lên!")
        elif close < bb_lower: score -= 2; cons.append("=> Breakdown Xuống!")
    if close > supertrend: score += 2; pros.append("SuperTrend: BÁO TĂNG")
    else: score -= 2; cons.append("SuperTrend: BÁO GIẢM")
    if tenkan > 0 and kijun > 0:
        if tenkan > kijun and close > tenkan: score += 1; pros.append("Ichimoku: Xu hướng Tăng")
        elif tenkan < kijun: score -= 1; cons.append("Ichimoku: Xu hướng Giảm")
    if ema34 > ema89 and close > ema34: score += 1; pros.append("EMA System: Xu hướng Tốt")
    elif close < ema89: score -= 1; cons.append("EMA System: Gãy xu hướng")
    if rsi < 30: score += 1; pros.append(f"RSI ({rsi:.0f}): Quá bán")
    elif rsi > 70: score -= 1; cons.append(f"RSI ({rsi:.0f}): Quá mua")
    
    final_score = max(0, min(10, 4 + score))
    action, zone = "QUAN SÁT", "yellow-zone"
    if final_score >= 8: action, zone = "MUA MẠNH", "green-zone"
    elif final_score >= 6: action, zone = "MUA THĂM DÒ", "green-zone"
    elif final_score <= 3: action, zone = "BÁN / CẮT LỖ", "red-zone"
    stop_loss = close - 2*atr; take_profit = close + 3*atr
    return {"score": final_score, "action": action, "zone": zone, "pros": pros, "cons": cons, "entry": close, "stop": stop_loss, "target": take_profit}

# ==========================================
# 🧠 PHÂN TÍCH CƠ BẢN (FIXED V36.1: ANTI-UGLY)
# ==========================================
def analyze_fundamental(info, fin, bal, price_now):
    score = 0; details = []
    
    # 1. Kiểm tra dữ liệu đầu vào. Nếu Yahoo chặn, các giá trị này sẽ là None.
    pe = info.get('trailingPE')
    pb = info.get('priceToBook')
    roe = info.get('returnOnEquity')
    
    # Nếu không có dữ liệu quan trọng, trả về trạng thái "Chưa có dữ liệu" (Xám) thay vì "Yếu kém" (Đỏ)
    if pe is None and pb is None:
        return {"health": "CHƯA CÓ DỮ LIỆU", "color": "#9ca3af", "details": ["⚠️ Yahoo Finance chưa cập nhật BCTC.", "👉 Vui lòng xem tại CafeF/Vietstock."]}

    # Nếu có dữ liệu, tiến hành chấm điểm
    try:
        mkt_cap = info.get('marketCap', 0)
        
        # PE Logic
        if pe:
            if 0 < pe < 15: score += 2; details.append(f"P/E Hấp dẫn ({pe:.1f}x)")
            elif pe >= 15: details.append(f"P/E Khá cao ({pe:.1f}x)")
        
        # PB Logic
        if pb:
            if 0 < pb < 1.5: score += 1; details.append(f"P/B Rẻ ({pb:.1f}x)")
        
        # ROE Logic (Yahoo trả về dạng thập phân, ví dụ 0.21)
        if roe:
            roe_pct = roe * 100
            if roe_pct > 15: score += 2; details.append(f"ROE Xuất sắc ({roe_pct:.1f}%)")
            elif roe_pct > 10: score += 1; details.append(f"ROE Ổn định ({roe_pct:.1f}%)")
            else: details.append(f"ROE Thấp ({roe_pct:.1f}%)")
            
        if mkt_cap > 0: details.append(f"Vốn hóa: {mkt_cap/1e9:,.0f} tỷ")
        
        # Thử lấy thêm thông tin từ BCTC nếu có
        net_growth = 0
        if not fin.empty and len(fin.columns) >= 2:
            try:
                net_now = fin.loc['Net Income'].iloc[0]; net_prev = fin.loc['Net Income'].iloc[1]
                if abs(net_prev) > 0: 
                    net_growth = (net_now - net_prev) / abs(net_prev)
                    if net_growth > 0.1: score += 2; details.append(f"🚀 LN Tăng trưởng ({net_growth:.1%})")
            except: pass

    except: pass

    # Xếp hạng
    health, color = ("TRUNG BÌNH", "#f59e0b")
    if score >= 5: health, color = ("KIM CƯƠNG 💎", "#10b981") 
    elif score >= 3: health, color = ("VỮNG MẠNH 💪", "#3b82f6")
    elif score < 3: health, color = ("CẦN CẨN TRỌNG ⚠️", "#ef4444")
    
    return {"health": health, "color": color, "details": details}

# ==========================================
# 🛠️ HÀM HỖ TRỢ & CHART (V36 - SĂN NẾN NHẬT)
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

def identify_candlestick_patterns(df):
    # Logic nhận diện mẫu hình nến đơn giản, nhẹ, không dùng thư viện nặng
    patterns = []
    if len(df) < 3: return patterns
    
    # Duyệt qua 20 nến cuối cùng để đỡ rối
    subset = df.iloc[-20:].copy()
    
    for i in range(1, len(subset)):
        curr = subset.iloc[i]
        prev = subset.iloc[i-1]
        
        # 1. Bullish Engulfing (Nhấn chìm tăng)
        if (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and \
           (curr['Close'] > prev['Open']) and (curr['Open'] < prev['Close']):
            patterns.append({'Date': curr.name, 'Label': '▲ Engulf', 'Color': '#00ff00', 'Y': curr['Low']})
            
        # 2. Bearish Engulfing (Nhấn chìm giảm)
        elif (prev['Close'] > prev['Open']) and (curr['Close'] < curr['Open']) and \
             (curr['Close'] < prev['Open']) and (curr['Open'] > prev['Close']):
            patterns.append({'Date': curr.name, 'Label': '▼ Engulf', 'Color': '#ff0000', 'Y': curr['High']})
            
        # 3. Hammer (Búa - Đảo chiều tăng ở đáy)
        body = abs(curr['Close'] - curr['Open'])
        lower_shadow = min(curr['Close'], curr['Open']) - curr['Low']
        upper_shadow = curr['High'] - max(curr['Close'], curr['Open'])
        
        if (lower_shadow > 2 * body) and (upper_shadow < body) and (curr['Close'] < df['Close'].rolling(20).mean().iloc[-1]): # Đang ở vùng thấp
            patterns.append({'Date': curr.name, 'Label': '🔨 Hammer', 'Color': '#00ff00', 'Y': curr['Low']})

        # 4. Shooting Star (Sao đổi ngôi - Đảo chiều giảm ở đỉnh)
        if (upper_shadow > 2 * body) and (lower_shadow < body) and (curr['Close'] > df['Close'].rolling(20).mean().iloc[-1]): # Đang ở vùng cao
            patterns.append({'Date': curr.name, 'Label': '☄️ Star', 'Color': '#ff0000', 'Y': curr['High']})
            
    return patterns

def render_pro_chart(df, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'), row=1, col=1)
    
    # MA20
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
    
    # ICHIMOKU (V35)
    if 'ITS_9' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['ITS_9'], line=dict(color='#22d3ee', width=1.5), name='Tenkan'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['IKS_26'], line=dict(color='#ef4444', width=1.5), name='Kijun'), row=1, col=1)
    
    # FIBONACCI (V34)
    max_h = df['High'].max(); min_l = df['Low'].min(); diff = max_h - min_l
    if diff > 0:
        levels = [0.382, 0.5, 0.618]
        colors_fib = ['#94a3b8', '#facc15', '#eab308'] 
        for i, lvl in enumerate(levels):
            price_lvl = max_h - (diff * lvl)
            fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=price_lvl, y1=price_lvl, line=dict(color=colors_fib[i], width=1, dash="dot"), row=1, col=1)
    
    # --- VẼ NẾN NHẬT (V36 NEW) ---
    patterns = identify_candlestick_patterns(df)
    for p in patterns:
        fig.add_annotation(
            x=p['Date'], y=p['Y'], text=p['Label'],
            showarrow=True, arrowhead=1, arrowcolor=p['Color'],
            font=dict(color=p['Color'], size=11, weight="bold"),
            row=1, col=1
        )

    colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    
    fig.update_layout(height=700, template="plotly_dark", hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=True, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
    st.plotly_chart(fig, use_container_width=True)

def render_dividend_chart(dividends, splits):
    if not dividends.empty:
        div_df = dividends.reset_index()
        div_df.columns = ['Date', 'Amount']
        div_df['Date'] = div_df['Date'].dt.tz_localize(None)
        div_df = div_df[div_df['Date'] > datetime.now().replace(year=datetime.now().year - 5)]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=div_df['Date'], y=div_df['Amount'], marker_color='#10b981', name='Cổ tức (Tiền)', hovertemplate='Ngày: %{x|%d/%m/%Y}<br>💰 %{y:,.0f} đ<extra></extra>'))
        fig.update_layout(title=dict(text="💰 Lịch Sử Trả Cổ Tức (5 Năm)", font=dict(size=20)), yaxis_title="Số Tiền (VND)", xaxis_title="Thời Gian", template="plotly_dark", height=500, hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=50,b=0))
        fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("📋 Xem chi tiết lịch sử"): st.dataframe(div_df.sort_values('Date', ascending=False).style.format({"Amount": "{:,.0f} đ"}), use_container_width=True)
    else: st.info("Không có dữ liệu trả cổ tức trong thời gian gần đây.")
    if not splits.empty: st.subheader("✂️ Lịch Sử Chia Tách"); st.write(splits.sort_index(ascending=False).head(5))

# ==========================================
# 🖥️ MAIN UI
# ==========================================
if mode == "📘 Hướng Dẫn & Quy Tắc":
    st.header("📘 HƯỚNG DẪN SỬ DỤNG & BỘ QUY TẮC GIAO DỊCH")
    st.markdown("""
    ---
    ### 🎯 TRIẾT LÝ: "DÒNG TIỀN THÔNG MINH + TĂNG TRƯỞNG"
    1.  **Fundamental (Cơ bản):** Doanh nghiệp Tăng trưởng, Lãi thật, Nợ an toàn.
    2.  **Technical (Kỹ thuật):** Dòng tiền "Cá mập" vào, Giá Breakout.
    ---
    ### 🛠️ CÁCH SỬ DỤNG
    1.  **🔮 Phân Tích Chuyên Sâu:** Soi chi tiết từng mã (Biểu đồ, AI Prophet, BCTC, Cổ tức, Monte Carlo).
    2.  **📊 Bảng Giá & Máy Quét:** Lọc nhanh cơ hội toàn thị trường.
    3.  **📘 Hướng Dẫn:** Ôn lại quy tắc.
    ---
    ### 📜 BỘ QUY TẮC VÀNG
    #### ✅ MUA KHI:
    * **Điểm 8-10 (MUA MẠNH):** Vol nổ + SuperTrend Tăng + Breakout.
    * **Săn Nến Nhật:** Xuất hiện **Hammer** hoặc **Engulfing Tăng (▲)**.
    * **ĐK Cần:** Sức khỏe Doanh nghiệp phải là **Xanh (Kim Cương)** hoặc **Lam (Vững Mạnh)**.
    #### 🛑 BÁN KHI:
    * Giá thủng mức **"🛑 Cắt Lỗ"** hiển thị trên màn hình.
    * Xuất hiện **Shooting Star** hoặc **Engulfing Giảm (▼)**.
    """)

elif mode == "🔮 Phân Tích Chuyên Sâu":
    st.header("🔮 Phân Tích Chuyên Sâu")
    c1, c2 = st.columns([3, 1])
    with c1: symbol = st.text_input("Nhập Mã CP", value="HPG").upper()
    with c2: 
        if st.button("🔄 Cập nhật giá"): st.cache_data.clear(); st.rerun()

    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news, divs, splits = load_data_final(symbol, period)
        
        if not df_chart.empty and not df_calc.empty:
            try:
                price_now = df_calc.iloc[-1]['Close']
                long_name = info.get('longName', symbol)
                st.title(f"💎 {long_name}")
                
                strat = analyze_smart(df_calc)   
                fund = analyze_fundamental(info, fin, bal, price_now) 

                if strat:
                    col_tech, col_fund = st.columns(2)
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

                    with col_fund:
                        st.markdown(f"""
                        <div class="rec-card" style="border-left: 5px solid {fund['color']};">
                            <h4>🏢 SỨC KHỎE DOANH NGHIỆP</h4>
                            <div style="font-size: 36px; font-weight:bold; margin: 15px 0; color: {fund['color']}">{fund['health']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        with st.expander("🔍 Chi tiết Cơ Bản (BCTC Quý)", expanded=True):
                            for d in fund['details']: 
                                if "cao" in d or "Kém" in d or "giảm" in d or "Thấp" in d: st.warning(f"⚠️ {d}")
                                else: st.write(f"✅ {d}")

              # --- ĐOẠN CODE ĐÃ CĂN CHỈNH THỤT ĐẦU DÒNG CHUẨN ---
                
                # 1. Khai báo Tabs (Chú ý danh sách tên Tab phải khớp)
                t1, t_view, t2, t3, t4, t5, t6, t7 = st.tabs(["📊 Biểu Đồ & Săn Nến", "📉 TradingView Realtime", "🔮 AI Prophet", "🌌 Đa Vũ Trụ", "📰 Tin Tức", "💰 Tài Chính", "🏢 Hồ Sơ", "🎁 Cổ Tức"])
                
                # 2. Nội dung Tab 1
                with t1: 
                    render_pro_chart(df_chart, symbol)
                
                # 3. Nội dung Tab TradingView (QUAN TRỌNG: Các dòng bên dưới phải thụt vào)
               # --- THAY THẾ TOÀN BỘ NỘI DUNG BÊN TRONG with t_view: ---
                with t_view:
                    # Tiêu đề & Ô nhập liệu ĐỘC LẬP
                    st.subheader("📉 TradingView (Kênh Độc Lập)")
                    
                    # Tạo một ô nhập riêng, không dùng biến 'symbol' của hệ thống chính
                    # Mặc định để VNINDEX cho khác biệt
                    tv_independent_symbol = st.text_input("Nhập mã xem riêng (Ví dụ: VIC, BTCUSD, GOLD):", value="VNINDEX", key="tv_standalone")
                    
                    # Logic: Nếu người dùng không nhập gì thì lấy VNINDEX, có nhập thì lấy mã đó
                    target_symbol = tv_independent_symbol if tv_independent_symbol else "VNINDEX"

                    html_code = f"""
                    <div class="tradingview-widget-container">
                      <div id="tradingview_independent"></div>
                      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                      <script type="text/javascript">
                      new TradingView.widget(
                      {{
                      "width": "100%",
                      "height": 650,
                      "symbol": "{target_symbol}",
                      "interval": "D",
                      "timezone": "Asia/Ho_Chi_Minh",
                      "theme": "dark",
                      "style": "1",
                      "locale": "vi_VN",
                      "enable_publishing": false,
                      "withdateranges": true,
                      "hide_side_toolbar": false,
                      "allow_symbol_change": true,
                      "details": true,
                      "container_id": "tradingview_independent"
                      }}
                      );
                      </script>
                    </div>
                    """
                    components.html(html_code, height=700)
                    # ... (Phần code AI Prophet cũ giữ nguyên từ đây)
                with t2:
                    if PROPHET_AVAILABLE:
                        with st.spinner("🔮 AI đang tiên tri..."):
                            fig_ai, msg_ai = run_prophet_forecast(df_calc)
                        if fig_ai: st.plotly_chart(fig_ai, use_container_width=True)
                        else: st.error(msg_ai)
                    else: st.warning("⚠️ Chưa cài thư viện Prophet")
                with t3: # TAB MONTE CARLO
                    with st.spinner("🌌 Đang mở cổng đa vũ trụ..."):
                        fig_mc, fig_hist, stats = run_monte_carlo(df_calc)
                    
                    if fig_mc:
                        st.plotly_chart(fig_mc, use_container_width=True)
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Trung Bình", f"{stats['mean']:,.0f}")
                        m2.metric("Lạc Quan (Top 5%)", f"{stats['top_5']:,.0f}", delta="Best Case", delta_color="normal")
                        m3.metric("Bi Quan (Bot 5%)", f"{stats['bot_5']:,.0f}", delta="Worst Case", delta_color="inverse")
                        m4.metric("Xác Suất Tăng", f"{stats['prob_up']:.1f}%")
                        st.plotly_chart(fig_hist, use_container_width=True)
                    else: st.error("Không đủ dữ liệu mô phỏng.")
                with t4:
                    for item in news: st.markdown(f'<div class="news-item"><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a><div class="news-meta">🕒 {item["published"][:16]}</div></div>', unsafe_allow_html=True)
                with t5:
                    c_left, c_right = st.columns(2)
                    with c_left: st.subheader("Kinh Doanh (Quý)"); st.dataframe(clean_table(fin), use_container_width=True)
                    with c_right: st.subheader("Cân Đối Kế Toán (Quý)"); st.dataframe(clean_table(bal), use_container_width=True)
                    st.subheader("Lưu Chuyển Tiền Tệ")
                    st.dataframe(clean_table(cash), use_container_width=True)
                with t6:
                    c1, c2 = st.columns([2, 1])
                    with c1: 
                        summary = info.get('longBusinessSummary', '')
                        st.write(summary if summary else "Hiện chưa có mô tả.")
                    with c2:
                        st.info(f"Ngành: {info.get('industry', 'N/A')}")
                        st.success(f"Nhân sự: {safe_fmt(info.get('fullTimeEmployees', 'N/A'))}")
                with t7:
                    st.markdown(f"### 🗓️ Lịch Sự Kiện: [Xem trên CafeF](https://s.cafef.vn/Lich-su-kien/{symbol}.chn)")
                    render_dividend_chart(divs, splits)

            except Exception as e:
                st.error(f"⚠️ Có lỗi khi xử lý dữ liệu mã {symbol}. Chi tiết: {e}")
        else:
            st.error(f"❌ Không tìm thấy dữ liệu cho mã '{symbol}'. Có thể mã bị sai hoặc mới lên sàn chưa đủ dữ liệu phân tích.")

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Máy Quét Siêu Hạng V36.1")
    all_tabs = ["🛠️ Tự Nhập"] + list(STOCK_GROUPS.keys())
    tabs = st.tabs(all_tabs)
    with tabs[0]:
        inp = st.text_area("Nhập mã (ngăn cách bằng dấu phẩy):", value="HPG, SSI, VND, FPT, MWG, DIG, CEO", height=100)
        if st.button("🚀 QUÉT NGAY"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            res = []
            bar = st.progress(0, "Đang xử lý...")
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                try:
                    df, _, _, _, _, _, _, _, _, _ = load_data_final(t, "1y")
                    s = analyze_smart(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": f"{s['entry']:,.0f}"})
                except: pass
            bar.empty()
            st.dataframe(pd.DataFrame(res).sort_values(by="Điểm", ascending=False), use_container_width=True)
    
    for i, (name, stocks) in enumerate(STOCK_GROUPS.items()):
        with tabs[i+1]:
            if st.button(f"🚀 Quét Nhóm {name}", key=name):
                ticks = stocks.split(',')
                res = []
                bar = st.progress(0, f"Đang quét {name}...")
                for j, t in enumerate(ticks):
                    bar.progress((j+1)/len(ticks), f"Đang phân tích: {t}...")
                    try:
                        df, _, _, _, _, _, _, _, _, _ = load_data_final(t, "1y")
                        s = analyze_smart(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá": f"{s['entry']:,.0f}"})
                    except: pass
                bar.empty()
                if res:
                    df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                    def color_act(val):
                        if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                        if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                        return 'color: #f59e0b'
                    st.dataframe(df_res.style.map(color_act, subset=['Hành động']), use_container_width=True)
                    if not df_res.empty and df_res.iloc[0]['Điểm'] >= 7: 
                        st.success(f"💎 NGÔI SAO DÒNG {name}: **{df_res.iloc[0]['Mã']}** ({df_res.iloc[0]['Điểm']} điểm)")

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V36.1 Ultimate - Clean & Stable</div>', unsafe_allow_html=True)











