import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime, timedelta
import requests
import time

# --- THƯ VIỆN AI (PROPHET) ---
try:
    from prophet import Prophet
    from prophet.plot import plot_plotly
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="ThangLong Ultimate V40", page_icon="🐲")

# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP
# ==========================================
USERS_DB = {
    "admin": "admin123", "stock": "stock123", "guest": "123456",
    "guest1": "123456", "huydang": "123456", "kieuoanh": "123456", "uyennhi": "123456",
    "Mrquynh": "123456", "Msnhung": "123456", "thanhduc": "123456"
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

mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét", "📘 Hướng Dẫn & Quy Tắc"])
if st.sidebar.button("🔄 Xóa Cache & Cập Nhật"): st.cache_data.clear(); st.rerun()

# ==========================================
# 🧠 XỬ LÝ DỮ LIỆU (DNSE + SSI - V40)
# ==========================================
@st.cache_data(ttl=300)
def load_news_google(symbol):
    try:
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        return [{'title': e.title, 'link': e.link, 'published': e.get('published','')[:16]} for e in feed.entries[:10]]
    except: return []

# 1. LẤY GIÁ TỪ DNSE (ENTRADE) - Ít bị chặn nhất hiện nay
def get_data_dnse(ticker):
    try:
        end = int(datetime.now().timestamp())
        start = int((datetime.now() - timedelta(days=730)).timestamp()) # 2 năm
        url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?symbol={ticker}&from={start}&to={end}&resolution=1D"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=5).json()
        
        if resp and 't' in resp and len(resp['t']) > 0:
            df = pd.DataFrame({
                'Date': pd.to_datetime(resp['t'], unit='s'),
                'Open': resp['o'],
                'High': resp['h'],
                'Low': resp['l'],
                'Close': resp['c'],
                'Volume': resp['v']
            })
            df.set_index('Date', inplace=True)
            return df.sort_index()
    except Exception as e:
        # st.error(f"Lỗi DNSE: {e}")
        pass
    return pd.DataFrame()

# 2. LẤY CƠ BẢN TỪ SSI (iBOARD) - Rất chi tiết
def get_fundamental_ssi(ticker):
    data = {}
    try:
        url = f"https://iboard.ssi.com.vn/api/apiv2/securities/details?symbol={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=5).json()
        
        if resp and 'data' in resp and resp['data']:
            d = resp['data']
            data['shortName'] = d.get('repeating_company_name_vi', ticker)
            data['exchange'] = d.get('exchange', 'VN')
            data['priceToEarning'] = d.get('pe', 0)
            data['priceToBook'] = d.get('pb', 0)
            data['roe'] = d.get('roe', 0)
            data['marketCap'] = d.get('market_cap', 0)
            data['source'] = 'SSI'
            # SSI không trả về Nợ/VCSH trực tiếp ở API này, ta tạm để None để không báo sai
            data['debtOnEquity'] = None 
            return data
    except: pass
    
    # FALLBACK: Nếu SSI chặn, thử trả về data rỗng có đánh dấu
    return {'source': 'NONE'}

@st.cache_data(ttl=300)
def load_data_final(ticker, time_period):
    # 1. Load Chart (DNSE)
    df_calc = get_data_dnse(ticker)
    df_chart = pd.DataFrame()
    
    if not df_calc.empty:
        # Cắt data cho chart
        if time_period == "1d": df_chart = df_calc.tail(100) 
        elif time_period == "5d": df_chart = df_calc.tail(10) 
        elif time_period == "1mo": df_chart = df_calc.tail(22)
        elif time_period == "6mo": df_chart = df_calc.tail(130)
        elif time_period == "1y": df_chart = df_calc.tail(260)
        else: df_chart = df_calc

        # Tính toán kỹ thuật
        if len(df_calc) > 50:
            try:
                sti = ta.supertrend(df_calc['High'], df_calc['Low'], df_calc['Close'], length=10, multiplier=3)
                df_calc = df_calc.join(sti) 
                df_calc.ta.mfi(length=14, append=True); df_calc.ta.stochrsi(length=14, append=True)
                df_calc.ta.ema(length=34, append=True); df_calc.ta.ema(length=89, append=True)
                df_calc.ta.adx(length=14, append=True); df_calc.ta.atr(length=14, append=True)
                df_calc.ta.rsi(length=14, append=True); df_calc.ta.cci(length=20, append=True)
                df_calc.ta.sma(length=20, close='Volume', prefix='VOL', append=True) 
                df_calc.ta.bbands(length=20, std=2, append=True)
                df_calc.ta.sma(length=20, append=True); df_calc.ta.sma(length=50, append=True)
                ichi = ta.ichimoku(df_calc['High'], df_calc['Low'], df_calc['Close'], tenkan=9, kijun=26, senkou=52)
                if ichi is not None: df_calc = pd.concat([df_calc, ichi[0]], axis=1)
            except: pass
            
        if not df_chart.empty:
            try:
                df_chart.ta.sma(length=20, append=True)
                df_chart.ta.bbands(length=20, std=2, append=True)
                ichi_c = ta.ichimoku(df_chart['High'], df_chart['Low'], df_chart['Close'])
                if ichi_c is not None: df_chart = pd.concat([df_chart, ichi_c[0]], axis=1)
            except: pass

    # 2. Load Fundamental (SSI)
    fund_data = get_fundamental_ssi(ticker)
    
    news = load_news_google(ticker)
    return df_calc, df_chart, fund_data, news

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
# 🧠 AI PREDICTION
# ==========================================
def run_prophet_forecast(df, periods=90):
    if not PROPHET_AVAILABLE: return None, "⚠️ Chưa cài thư viện Prophet."
    try:
        df_prophet = df.reset_index()[['Date', 'Close']].copy()
        df_prophet.columns = ['ds', 'y']; df_prophet['ds'] = df_prophet['ds'].dt.tz_localize(None)
        m = Prophet(daily_seasonality=True); m.fit(df_prophet)
        future = m.make_future_dataframe(periods=periods); forecast = m.predict(future)
        fig = plot_plotly(m, forecast)
        fig.data[0].marker.color = '#22d3ee'; fig.data[1].line.color = '#f472b6'
        fig.update_layout(title=dict(text="🔮 AI Dự Báo", font=dict(size=20)), yaxis_title="Giá", template="plotly_dark", height=600, hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=50,b=0))
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

def analyze_fundamental(fund_data):
    # V40: Xử lý thông minh khi thiếu dữ liệu
    score = 0; details = []
    
    if not fund_data or fund_data.get('source') == 'NONE':
        return {"health": "KHÔNG XÁC ĐỊNH", "color": "gray", "details": ["Server chặn kết nối dữ liệu cơ bản."]}

    # Lấy dữ liệu an toàn
    pe = fund_data.get('priceToEarning')
    pb = fund_data.get('priceToBook')
    roe = fund_data.get('roe')
    
    # Logic đánh giá: Chỉ đánh giá cái gì CÓ, không phạt cái KHÔNG CÓ
    valid_criteria = 0
    
    if pe is not None and pe > 0:
        if pe < 15: score += 2; details.append(f"P/E Hấp dẫn ({pe:.1f}x)")
        else: details.append(f"P/E Cao ({pe:.1f}x)")
        valid_criteria += 1
        
    if pb is not None and pb > 0:
        if pb < 1.5: score += 1; details.append(f"P/B Rẻ ({pb:.1f}x)")
        valid_criteria += 1
        
    if roe is not None:
        if roe > 15: score += 2; details.append(f"ROE Xuất sắc ({roe:.1f}%)")
        elif roe > 10: score += 1; details.append(f"ROE Ổn định ({roe:.1f}%)")
        elif roe > 0: details.append(f"ROE Thấp ({roe:.1f}%)")
        valid_criteria += 1
    
    details.append(f"Nguồn: {fund_data.get('source')}")

    # Xếp hạng dựa trên tiêu chí có sẵn
    if valid_criteria == 0:
        return {"health": "CHƯA ĐỦ DỮ LIỆU", "color": "gray", "details": ["Cần kiểm tra nguồn khác"]}
    
    # Chuẩn hóa điểm số
    health, color = ("TRUNG BÌNH", "#f59e0b")
    if score >= 4: health, color = ("KIM CƯƠNG 💎", "#10b981") 
    elif score >= 2: health, color = ("VỮNG MẠNH 💪", "#3b82f6")
    elif score < 2: health, color = ("CẦN CẨN TRỌNG ⚠️", "#ef4444")
    
    return {"health": health, "color": color, "details": details}

# ==========================================
# 🛠️ CHART & CANDLESTICK
# ==========================================
def identify_candlestick_patterns(df):
    patterns = []
    if len(df) < 3: return patterns
    subset = df.iloc[-20:].copy()
    for i in range(1, len(subset)):
        curr = subset.iloc[i]; prev = subset.iloc[i-1]
        if (prev['Close'] < prev['Open']) and (curr['Close'] > curr['Open']) and (curr['Close'] > prev['Open']) and (curr['Open'] < prev['Close']):
            patterns.append({'Date': curr.name, 'Label': '▲ Engulf', 'Color': '#00ff00', 'Y': curr['Low']})
        elif (prev['Close'] > prev['Open']) and (curr['Close'] < curr['Open']) and (curr['Close'] < prev['Open']) and (curr['Open'] > prev['Close']):
            patterns.append({'Date': curr.name, 'Label': '▼ Engulf', 'Color': '#ff0000', 'Y': curr['High']})
        body = abs(curr['Close'] - curr['Open'])
        lower_shadow = min(curr['Close'], curr['Open']) - curr['Low']
        upper_shadow = curr['High'] - max(curr['Close'], curr['Open'])
        if (lower_shadow > 2 * body) and (upper_shadow < body) and (curr['Close'] < df['Close'].rolling(20).mean().iloc[-1]):
            patterns.append({'Date': curr.name, 'Label': '🔨 Hammer', 'Color': '#00ff00', 'Y': curr['Low']})
        if (upper_shadow > 2 * body) and (lower_shadow < body) and (curr['Close'] > df['Close'].rolling(20).mean().iloc[-1]):
            patterns.append({'Date': curr.name, 'Label': '☄️ Star', 'Color': '#ff0000', 'Y': curr['High']})
    return patterns

def render_pro_chart(df, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'), row=1, col=1)
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
    if 'ITS_9' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['ITS_9'], line=dict(color='#22d3ee', width=1.5), name='Tenkan'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['IKS_26'], line=dict(color='#ef4444', width=1.5), name='Kijun'), row=1, col=1)
    
    max_h = df['High'].max(); min_l = df['Low'].min(); diff = max_h - min_l
    if diff > 0:
        levels = [0.382, 0.5, 0.618]; colors_fib = ['#94a3b8', '#facc15', '#eab308'] 
        for i, lvl in enumerate(levels):
            price_lvl = max_h - (diff * lvl)
            fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=price_lvl, y1=price_lvl, line=dict(color=colors_fib[i], width=1, dash="dot"), row=1, col=1)
    
    patterns = identify_candlestick_patterns(df)
    for p in patterns:
        fig.add_annotation(x=p['Date'], y=p['Y'], text=p['Label'], showarrow=True, arrowhead=1, arrowcolor=p['Color'], font=dict(color=p['Color'], size=11, weight="bold"), row=1, col=1)

    colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    fig.update_layout(height=700, template="plotly_dark", hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=True, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
    st.plotly_chart(fig, use_container_width=True)

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
    with c1: symbol = st.text_input("Nhập Mã CP (Ví dụ: HPG, OIL, BSR)", value="MBB").upper()
    with c2: 
        if st.button("🔄 Cập nhật giá"): st.cache_data.clear(); st.rerun()

    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    if symbol:
        # Load Data V40 (DNSE + SSI)
        df_calc, df_chart, fund_data, news = load_data_final(symbol, period)
        
        if not df_chart.empty and not df_calc.empty:
            try:
                price_now = df_calc.iloc[-1]['Close']
                long_name = fund_data.get('shortName', symbol)
                st.title(f"💎 {long_name} ({symbol})")
                
                strat = analyze_smart(df_calc)   
                fund = analyze_fundamental(fund_data) 

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
                        with st.expander("🔍 Chi tiết Cơ Bản", expanded=True):
                            for d in fund['details']: 
                                if "cao" in d and "Nợ" in d: st.warning(f"⚠️ {d}")
                                elif "Thấp" in d and "ROE" in d: st.warning(f"⚠️ {d}")
                                else: st.write(f"✅ {d}")

                t1, t2, t3, t4, t5 = st.tabs(["📊 Biểu Đồ & Săn Nến", "🔮 AI Prophet", "🌌 Đa Vũ Trụ", "📰 Tin Tức", "🏢 Hồ Sơ"])
                with t1: render_pro_chart(df_chart, symbol)
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
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.subheader("Thông Tin")
                        st.info(f"Nguồn Dữ Liệu: {fund_data.get('source', 'Unknown')}")
                        st.write(f"Tên: {fund_data.get('shortName', symbol)}")
                    with c2:
                        st.subheader("Chỉ Số")
                        pe_val = fund_data.get('priceToEarning')
                        st.write(f"P/E: {pe_val:.1f}" if pe_val else "P/E: N/A")
                        pb_val = fund_data.get('priceToBook')
                        st.write(f"P/B: {pb_val:.1f}" if pb_val else "P/B: N/A")
                        roe_val = fund_data.get('roe')
                        st.write(f"ROE: {roe_val:.1f}%" if roe_val else "ROE: N/A")

            except Exception as e:
                st.error(f"⚠️ Có lỗi khi xử lý dữ liệu mã {symbol}. Chi tiết: {e}")
        else:
            st.error(f"❌ Không tìm thấy dữ liệu cho mã '{symbol}'. Hệ thống đã thử các nguồn dự phòng nhưng đều thất bại do chặn IP. Vui lòng thử lại sau.")

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Máy Quét Siêu Hạng V40")
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
                    df, _, _, _ = load_data_final(t, "1y")
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
                        df, _, _, _ = load_data_final(t, "1y")
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

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V40 Ultimate - DNSE/SSI Alliance</div>', unsafe_allow_html=True)
