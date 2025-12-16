import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
from datetime import datetime

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Oracle V8", page_icon="🔮")

# CSS: Giao diện chuyên gia
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.3rem !important; color: #00e676;}
    h1, h2, h3 {color: #2979ff !important;}
    .stDataFrame {border: 1px solid #444; border-radius: 8px;}
    
    /* Signal Badges */
    .signal-box {padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px; font-weight: bold; color: white;}
    .bg-buy {background-color: #00c853; border: 2px solid #00e676;}
    .bg-sell {background-color: #d50000; border: 2px solid #ff5252;}
    .bg-wait {background-color: #ff6d00; border: 2px solid #ffab00;}
    
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #0e1117; color: #888; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #333;}
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
mode = st.sidebar.radio("Chọn Chế Độ:", ["🔮 Phân Tích Chuyên Sâu", "⚡ Máy Quét Cơ Hội (Scanner)"])

# --- HÀM TÍNH TOÁN CHIẾN LƯỢC (BỘ NÃO V8) ---
def analyze_strategy_v8(df):
    if df.empty or len(df) < 50: return None
    
    # Lấy dữ liệu mới nhất
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    close = last['Close']
    rsi = last['RSI_14']
    ma50 = last['SMA_50']
    macd = last['MACD_12_26_9']
    macds = last['MACDs_12_26_9']
    atr = last['ATRr_14'] # Average True Range (Đo biến động)
    
    score = 5.0 # Điểm cơ bản
    reasons = []
    
    # 1. PHÂN TÍCH XU HƯỚNG (TREND)
    if close > ma50:
        score += 2
        reasons.append("✅ Giá nằm trên MA50 (Xu hướng Tăng)")
    else:
        score -= 2
        reasons.append("⚠️ Giá nằm dưới MA50 (Xu hướng Giảm/Yếu)")
        
    # 2. ĐỘNG LƯỢNG (MOMENTUM - RSI)
    if rsi < 30:
        score += 3
        reasons.append("✅ RSI Quá bán (Vùng giá rẻ)")
    elif rsi > 70:
        score -= 3
        reasons.append("⚠️ RSI Quá mua (Rủi ro chỉnh)")
    else:
        reasons.append(f"ℹ️ RSI Trung tính ({rsi:.1f})")
        
    # 3. MACD (Đảo chiều)
    if macd > macds:
        score += 1
        reasons.append("✅ MACD cắt lên Signal (Đà tăng)")
    else:
        score -= 1
        reasons.append("⚠️ MACD cắt xuống Signal (Đà giảm)")
        
    # TỔNG HỢP TÍN HIỆU
    action = "NẮM GIỮ / QUAN SÁT"
    css_class = "bg-wait"
    
    if score >= 7:
        action = "KHUYẾN NGHỊ: MUA"
        css_class = "bg-buy"
    elif score <= 3:
        action = "KHUYẾN NGHỊ: BÁN"
        css_class = "bg-sell"
        
    # TÍNH TOÁN MỤC TIÊU (TARGET & STOPLOSS) DỰA TRÊN ATR
    # ATR là biên độ dao động trung bình. Stoploss thường là 2 lần ATR.
    stop_loss = close - (2 * atr)
    target_1 = close + (2 * atr)  # R:R = 1:1
    target_2 = close + (4 * atr)  # R:R = 1:2 (Lãi gấp đôi lỗ)
    
    return {
        "score": score,
        "action": action,
        "css": css_class,
        "reasons": reasons,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "roi_1": ((target_1 - close)/close)*100,
        "roi_2": ((target_2 - close)/close)*100,
        "atr": atr
    }

# --- HÀM TẢI DỮ LIỆU ---
@st.cache_data(ttl=300)
def load_data_v8(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    # Lấy khung ngày (1d) để tính toán chiến lược chuẩn nhất
    # Nếu muốn xem Intraday thì chart vẽ riêng, còn tính toán dùng nến ngày
    try:
        df = stock.history(period="1y") # Lấy 1 năm để đủ dữ liệu tính MA200 nếu cần
        if len(df) > 50:
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=50, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.macd(append=True)
            df.ta.atr(length=14, append=True) # QUAN TRỌNG: Tính ATR để đo biến động
    except: df = pd.DataFrame()

    # Dữ liệu hiển thị (Chart) có thể theo khung thời gian user chọn
    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        chart_df = stock.history(period=time, interval=interval)
        if not chart_df.empty: # Tính chỉ báo cho chart hiển thị
             chart_df.ta.sma(length=20, append=True)
             chart_df.ta.bbands(length=20, std=2, append=True)
    except: chart_df = pd.DataFrame()

    try: info = stock.info
    except: info = {}
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()
    try: cash = stock.cashflow
    except: cash = pd.DataFrame()
    try: news = stock.news
    except: news = []

    return df, chart_df, info, fin, bal, cash, news

# --- HÀM HỖ TRỢ ---
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
# GIAO DIỆN 1: PHÂN TÍCH CHUYÊN SÂU
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    symbol = st.sidebar.text_input("Mã CP", value="HPG").upper()
    period = st.sidebar.selectbox("Khung thời gian Chart", ["1d", "5d", "1mo", "6mo", "1y"], index=3)
    
    if symbol:
        # df: Dùng để tính toán chiến lược (Daily) | chart_df: Dùng để vẽ biểu đồ (User chọn)
        df_calc, chart_df, info, fin, bal, cash, news = load_data_v8(symbol, period)
        
        if not chart_df.empty:
            st.title(f"🔮 {info.get('longName', symbol)}")
            
            # --- PHÂN TÍCH CHIẾN LƯỢC (AI STRATEGY) ---
            strategy = analyze_strategy_v8(df_calc)
            
            if strategy:
                # 1. HỘP TÍN HIỆU CHÍNH
                st.markdown(f"""
                <div class="signal-box {strategy['css']}">
                    <h2>{strategy['action']} (Điểm: {strategy['score']}/10)</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # 2. BẢNG KẾ HOẠCH GIAO DỊCH (TRADING PLAN)
                st.subheader("📋 Kế Hoạch Giao Dịch (Tham khảo)")
                c1, c2, c3, c4 = st.columns(4)
                
                cur_price = df_calc['Close'].iloc[-1]
                
                c1.metric("1. Giá vào lệnh (Entry)", f"{cur_price:,.0f} ₫")
                c2.metric("2. Cắt lỗ (Stoploss)", f"{strategy['stop_loss']:,.0f} ₫", 
                          f"-{((cur_price - strategy['stop_loss'])/cur_price)*100:.2f}%", delta_color="inverse")
                
                c3.metric("3. Mục tiêu 1 (Ngắn hạn)", f"{strategy['target_1']:,.0f} ₫", 
                          f"+{strategy['roi_1']:.2f}%")
                
                c4.metric("4. Mục tiêu 2 (Trung hạn)", f"{strategy['target_2']:,.0f} ₫", 
                          f"+{strategy['roi_2']:.2f}%")
                
                # 3. LÝ DO KHUYẾN NGHỊ
                with st.expander("🧐 Tại sao AI đưa ra nhận định này?"):
                    for reason in strategy['reasons']:
                        st.write(reason)
                    st.caption(f"*Biên độ biến động (ATR): {strategy['atr']:,.0f} đồng/phiên. Stoploss và Target được tính dựa trên biên độ này để tránh bị quét lệnh oan.*")

            st.divider()
            
            # --- TABS (GIỮ NGUYÊN TỪ V7) ---
            t1, t2, t3 = st.tabs(["📊 Biểu đồ", "💰 Tài chính", "📰 Tin tức"])
            
            with t1:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
                fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name='Giá'), row=1, col=1)
                
                if 'SMA_20' in chart_df.columns:
                    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['SMA_20'], line=dict(color='orange'), name='MA20'), row=1, col=1)
                if 'BBU_20_2.0' in chart_df.columns:
                     fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Up'), row=1, col=1)
                     fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Low', fill='tonexty'), row=1, col=1)
                
                vol_colors = ['red' if r['Open'] > r['Close'] else 'green' for i, r in chart_df.iterrows()]
                fig.add_trace(go.Bar(x=chart_df.index, y=chart_df['Volume'], marker_color=vol_colors, name='Vol'), row=2, col=1)
                
                fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
                
            with t2:
                c1, c2 = st.columns(2)
                with c1: 
                    st.subheader("Kết quả kinh doanh")
                    st.dataframe(clean_table(fin).style.format("{:,.2f}"))
                with c2: 
                    st.subheader("Cân đối kế toán")
                    st.dataframe(clean_table(bal).style.format("{:,.2f}"))
            
            with t3:
                if news:
                    for n in news:
                        try:
                            ts = n.get('providerPublishTime', 0)
                            dt = datetime.fromtimestamp(ts).strftime('%d/%m %H:%M')
                            st.markdown(f"**{dt}** - [{n.get('title')}]({n.get('link')})")
                        except: pass
                else:
                    st.info("Không có tin tức mới.")
                    st.markdown(f"[Tra cứu Google News](https://www.google.com/search?q=tin+tuc+co+phieu+{symbol}&tbm=nws)")

# ==========================================
# GIAO DIỆN 2: SCANNER (BẢN ORACLE)
# ==========================================
elif mode == "⚡ Máy Quét Cơ Hội (Scanner)":
    st.title("⚡ Máy Quét Cơ Hội Đầu Tư (Oracle Scanner)")
    input_str = st.text_area("Danh sách mã:", value="HPG, VCB, SSI, VND, FPT, MWG, VNM, MSN, DIG, CEO, NVL")
    
    if st.button("🚀 PHÂN TÍCH TOÀN BỘ"):
        tickers = [x.strip().upper() for x in input_str.split(',')]
        results = []
        my_bar = st.progress(0, text="AI đang phân tích...")
        
        for i, ticker in enumerate(tickers):
            my_bar.progress((i + 1) / len(tickers), text=f"Đang chấm điểm: {ticker}...")
            try:
                # Tải dữ liệu và tính toán
                df_calc, _, _, _, _, _, _ = load_data_v8(ticker, "1y")
                strat = analyze_strategy_v8(df_calc)
                
                if strat:
                    results.append({
                        "Mã": ticker,
                        "Giá": f"{df_calc['Close'].iloc[-1]:,.0f}",
                        "Điểm": strat['score'],
                        "Hành động": strat['action'].replace("KHUYẾN NGHỊ: ", ""),
                        "Lãi Kỳ Vọng": f"{strat['roi_2']:.1f}%"
                    })
            except: pass
            
        my_bar.empty()
        
        if results:
            res_df = pd.DataFrame(results)
            # Sắp xếp theo Điểm cao nhất
            res_df = res_df.sort_values(by="Điểm", ascending=False)
            
            def color_row(val):
                if 'MUA' in val: return 'color: #00e676; font-weight: bold'
                if 'BÁN' in val: return 'color: #ff5252; font-weight: bold'
                return ''

            st.dataframe(res_df.style.map(color_row, subset=['Hành động']), use_container_width=True)
            
            top_pick = res_df.iloc[0]
            if top_pick['Điểm'] >= 7:
                st.balloons()
                st.success(f"🏆 Cổ phiếu tiềm năng nhất: **{top_pick['Mã']}** ({top_pick['Điểm']}/10 điểm) - Mục tiêu lãi: {top_pick['Lãi Kỳ Vọng']}")
        else:
            st.error("Không có dữ liệu.")

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V8 - The Oracle</div>', unsafe_allow_html=True)
