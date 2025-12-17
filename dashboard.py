import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime
# --- THƯ VIỆN AI MỚI ---
try:
    from prophet import Prophet
    from prophet.plot import plot_plotly
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="ThangLong AI Prophet V20", page_icon="🔮")

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
    
    .rec-card {
        background-color: #1e293b; border: 1px solid #334155; 
        border-radius: 12px; padding: 20px; text-align: center; 
        margin-bottom: 20px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    }
    .rec-card h4 {color: #94a3b8 !important; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px;}
    
    [data-testid="stMetricValue"] {font-size: 1.5rem !important; font-weight: 800 !important; color: #38bdf8 !important;}
    [data-testid="stMetricLabel"] {color: #cbd5e1 !important;}
    
    .score-circle {
        display: inline-block; width: 70px; height: 70px; line-height: 70px; 
        border-radius: 50%; font-size: 28px; font-weight: 800; color: white; 
        margin-bottom: 10px; box-shadow: 0 0 15px rgba(0,0,0,0.3);
    }
    .green-zone {background: linear-gradient(135deg, #10b981, #059669);}
    .red-zone {background: linear-gradient(135deg, #ef4444, #b91c1c);}
    .yellow-zone {background: linear-gradient(135deg, #f59e0b, #d97706);}
    
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #0f172a; color: #64748b; text-align: center; font-size: 12px; padding: 10px; border-top: 1px solid #1e293b; z-index: 100;}
</style>
""", unsafe_allow_html=True)

# KHO DỮ LIỆU NGÀNH (V17)
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
    
    # 1. TÍNH TOÁN (V19 Logic)
    try:
        df_calc = stock.history(period="2y")
        if len(df_calc) > 100:
            sti = ta.supertrend(df_calc['High'], df_calc['Low'], df_calc['Close'], length=10, multiplier=3)
            df_calc = df_calc.join(sti) 
            df_calc.ta.mfi(length=14, append=True)
            df_calc.ta.stochrsi(length=14, append=True)
            df_calc.ta.ema(length=34, append=True); df_calc.ta.ema(length=89, append=True)
            df_calc.ta.adx(length=14, append=True); df_calc.ta.atr(length=14, append=True)
            df_calc.ta.rsi(length=14, append=True); df_calc.ta.cci(length=20, append=True)
            df_calc.ta.sma(length=20, close='Volume', prefix='VOL', append=True) 
            df_calc.ta.bbands(length=20, std=2, append=True)
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

    # 3. DỮ LIỆU TÀI CHÍNH (QUARTERLY - CẬP NHẬT 2025)
    try: info = stock.info
    except: info = {}
    try: fin = stock.quarterly_financials 
    except: fin = pd.DataFrame()
    try: bal = stock.quarterly_balance_sheet 
    except: bal = pd.DataFrame()
    try: cash = stock.quarterly_cashflow 
    except: cash = pd.DataFrame()
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    try: info['marketCap'] = stock.fast_info['market_cap']
    except: pass

    news = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news

# ==========================================
# 🧠 AI PREDICTION (PROPHET MODEL)
# ==========================================
def run_prophet_forecast(df, periods=90):
    if not PROPHET_AVAILABLE:
        return None, "⚠️ Chưa cài thư viện Prophet. Hãy chạy: pip install prophet"
    
    try:
        # Chuẩn bị dữ liệu cho Prophet (ds, y)
        df_prophet = df.reset_index()[['Date', 'Close']].copy()
        df_prophet.columns = ['ds', 'y']
        df_prophet['ds'] = df_prophet['ds'].dt.tz_localize(None) # Xóa timezone để tránh lỗi
        
        # Huấn luyện
        m = Prophet(daily_seasonality=True)
        m.fit(df_prophet)
        
        # Dự báo tương lai
        future = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
        
        # Vẽ biểu đồ
        fig = plot_plotly(m, forecast)
        fig.update_layout(
            title="🔮 AI Dự Báo Xu Hướng (90 Ngày Tới)",
            yaxis_title="Giá Dự Kiến",
            xaxis_title="Thời Gian",
            template="plotly_dark",
            height=600
        )
        return fig, None
    except Exception as e:
        return None, f"Lỗi dự báo: {str(e)}"

# ==========================================
# 🧠 PHÂN TÍCH (V19 LOGIC)
# ==========================================
def analyze_smart(df):
    if df.empty or len(df) < 100: return None
    now = df.iloc[-1]; prev = df.iloc[-2]
    close = now['Close']
    try: st_col = [c for c in df.columns if 'SUPERT' in c][0]; supertrend = now[st_col]
    except: supertrend = close 

    mfi = now.get('MFI_14', 50); k = now.get('STOCHRSIk_14_14_3_3', 50); d = now.get('STOCHRSId_14_14_3_3', 50)
    adx = now.get('ADX_14', 0); ema34 = now.get('EMA_34', 0); ema89 = now.get('EMA_89', 0); atr = now.get('ATRr_14', 0)
    rsi = now.get('RSI_14', 50); cci = now.get('CCI_20_0.015', 0)
    vol_now = now['Volume']; vol_avg = now.get('VOL_SMA_20', vol_now)
    bb_upper = now.get('BBU_20_2.0', 0); bb_lower = now.get('BBL_20_2.0', 0); bb_mid = now.get('BBM_20_2.0', close)
    bandwidth = 0
    if bb_mid > 0: bandwidth = (bb_upper - bb_lower) / bb_mid

    score = 0; pros = []; cons = []

    # VSA & Squeeze
    if vol_now > 1.5 * vol_avg and close > prev['Close']: score += 2; pros.append(f"🔥 VSA: Tiền vào ồ ạt")
    elif vol_now > 1.2 * vol_avg and close > prev['Close']: score += 1; pros.append("VSA: Dòng tiền tốt")
    if bandwidth < 0.10: 
        pros.append("⚡ Bollinger: Nút thắt cổ chai (Sắp nổ Vol)")
        if close > bb_upper: score += 2; pros.append("=> Breakout Lên!")
        elif close < bb_lower: score -= 2; cons.append("=> Breakdown Xuống!")

    # Trend & Momentum
    if close > supertrend: score += 2; pros.append("SuperTrend: BÁO TĂNG")
    else: score -= 2; cons.append("SuperTrend: BÁO GIẢM")
    if ema34 > ema89 and close > ema34: score += 1; pros.append("EMA System: Xu hướng Tốt")
    elif close < ema89: score -= 1; cons.append("EMA System: Gãy xu hướng")
    if rsi < 30: score += 1; pros.append(f"RSI ({rsi:.0f}): Quá bán")
    elif rsi > 70: score -= 1; cons.append(f"RSI ({rsi:.0f}): Quá mua")
    if mfi < 20: score += 1; pros.append("MFI: Cá mập gom hàng")
    if k < 20 and k > d: score += 1; pros.append("StochRSI: Đảo chiều Tăng")

    final_score = max(0, min(10, 4 + score))
    action, zone = "QUAN SÁT", "yellow-zone"
    if final_score >= 8: action, zone = "MUA MẠNH", "green-zone"
    elif final_score >= 6: action, zone = "MUA THĂM DÒ", "green-zone"
    elif final_score <= 3: action, zone = "BÁN / CẮT LỖ", "red-zone"
    
    stop_loss = close - 2*atr
    take_profit = close + 3*atr
    return {"score": final_score, "action": action, "zone": zone, "pros": pros, "cons": cons, "entry": close, "stop": stop_loss, "target": take_profit}

def analyze_fundamental(info, fin, bal, price_now):
    score = 0; details = []
    pe = 0; roe = 0; debt_ratio = 0; net_margin = 0; pb = 0; current_ratio = 0; net_growth = 0

    try:
        mkt_cap = info.get('marketCap', 0)
        pe = info.get('trailingPE', 0)
        if (pe is None or pe == 0) and not fin.empty and mkt_cap > 0:
            net_income = fin.loc['Net Income'].iloc[0] * 4 # Quý hóa năm
            if net_income > 0: pe = mkt_cap / net_income
            
        equity = 0
        if not bal.empty:
            try: equity = bal.loc['Stockholders Equity'].iloc[0];
            except: pass
        
        if not fin.empty and equity > 0:
            net_income = fin.loc['Net Income'].iloc[0] * 4
            roe = net_income / equity
            pb = mkt_cap / equity 
            revenue = fin.loc['Total Revenue'].iloc[0] * 4
            if revenue > 0: net_margin = net_income / revenue
            
            # Tăng trưởng Quý này vs Quý trước
            if len(fin.columns) >= 2:
                net_now = fin.loc['Net Income'].iloc[0]
                net_prev = fin.loc['Net Income'].iloc[1]
                if abs(net_prev) > 0: net_growth = (net_now - net_prev) / abs(net_prev)

        if not bal.empty and equity > 0:
            try:
                total_debt = bal.loc['Total Debt'].iloc[0]
                debt_ratio = (total_debt / equity) * 100
                curr_asset = bal.loc['Current Assets'].iloc[0]
                curr_liab = bal.loc['Current Liabilities'].iloc[0]
                if curr_liab > 0: current_ratio = curr_asset / curr_liab
            except: pass     
    except: pass

    if net_growth > 0.10: score += 2; details.append(f"🚀 LN Quý Tăng trưởng ({net_growth:.1%})")
    elif net_growth < -0.10: details.append(f"⚠️ LN Quý Suy giảm ({net_growth:.1%})")
    
    if 0 < pe < 15: score += 1; details.append(f"P/E Hấp dẫn ({pe:.1f}x)")
    if 0 < pb < 1.5: score += 1; details.append(f"P/B Rẻ ({pb:.1f}x)")
    if roe > 0.15: score += 2; details.append(f"ROE Xuất sắc ({roe:.1%})")
    if net_margin > 0.10: score += 1; details.append(f"Biên lãi ròng cao ({net_margin:.1%})")
    if 0 < debt_ratio < 60: score += 1; details.append(f"Nợ vay an toàn ({debt_ratio:.0f}%)")
    if current_ratio > 1.5: score += 1; details.append(f"Thanh khoản tốt ({current_ratio:.1f})")

    if score == 0 and len(details) == 0: details.append("Chưa đủ dữ liệu BCTC")
    health, color = ("TRUNG BÌNH", "#f59e0b")
    if score >= 6: health, color = ("KIM CƯƠNG 💎", "#10b981") 
    elif score >= 3: health, color = ("VỮNG MẠNH 💪", "#3b82f6")
    elif score < 3: health, color = ("YẾU KÉM ⚠️", "#ef4444")
    
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
    if 'MACD_12_26_9' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='#22d3ee', width=1.5), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], line=dict(color='#f472b6', width=1.5), name='Signal'), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], marker_color='#64748b', name='Hist'), row=3, col=1)
    fig.update_layout(height=700, template="plotly_dark", hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=True, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
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
        
        # --- SỬA LỖI TẠI ĐÂY: Thêm kiểm tra df_calc không được rỗng ---
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
                        with st.expander("🔍 Chi tiết Cơ Bản (Tự tính từ BCTC Quý)", expanded=True):
                            for d in fund['details']: 
                                if "cao" in d or "Kém" in d or "giảm" in d: st.warning(f"⚠️ {d}")
                                else: st.write(f"✅ {d}")

                # CÁC TAB DỮ LIỆU
                t1, t2, t3, t4, t5 = st.tabs(["📊 Biểu Đồ", "🔮 AI Prophet", "📰 Tin Tức", "💰 Tài Chính", "🏢 Hồ Sơ"])
                with t1: render_pro_chart(df_chart, symbol)
                with t2:
                    if PROPHET_AVAILABLE:
                        fig_ai, msg_ai = run_prophet_forecast(df_calc)
                        if fig_ai: st.plotly_chart(fig_ai, use_container_width=True)
                        else: st.error(msg_ai)
                    else: st.warning("⚠️ Chưa cài thư viện Prophet")
                with t3:
                    for item in news: st.markdown(f'<div class="news-item"><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a><div class="news-meta">🕒 {item["published"][:16]}</div></div>', unsafe_allow_html=True)
                with t4:
                    c_left, c_right = st.columns(2)
                    with c_left: st.subheader("Kinh Doanh (Quý)"); st.dataframe(clean_table(fin), use_container_width=True)
                    with c_right: st.subheader("Cân Đối Kế Toán (Quý)"); st.dataframe(clean_table(bal), use_container_width=True)
                    st.subheader("Lưu Chuyển Tiền Tệ")
                    st.dataframe(clean_table(cash), use_container_width=True)
                with t5:
                    c1, c2 = st.columns([2, 1])
                    with c1: st.write(info.get('longBusinessSummary', 'Hiện chưa có mô tả.'))
                    with c2:
                        st.info(f"Ngành: {info.get('industry', 'N/A')}")
                        st.success(f"Nhân sự: {safe_fmt(info.get('fullTimeEmployees', 'N/A'))}")
            
            except Exception as e:
                st.error(f"⚠️ Có lỗi khi xử lý dữ liệu mã {symbol}. Chi tiết: {e}")
        else:
            st.error(f"❌ Không tìm thấy dữ liệu cho mã '{symbol}'. Có thể mã bị sai hoặc mới lên sàn chưa đủ dữ liệu phân tích.")

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Máy Quét Siêu Hạng V20")
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
                    df, _, _, _, _, _, _, _ = load_data_final(t, "1y")
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
                        df, _, _, _, _, _, _, _ = load_data_final(t, "1y")
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

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V20 Ultimate - AI Prophet Edition</div>', unsafe_allow_html=True)

