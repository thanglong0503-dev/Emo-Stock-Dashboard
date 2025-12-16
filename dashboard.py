import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
from datetime import datetime

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Masterpiece V8.1", page_icon="🐲")
# 👇👇👇 CHÈN ĐOẠN CODE BẢO MẬT VÀO ĐÂY 👇👇👇

# 1. KIỂM TRA BẢO TRÌ (Nếu muốn đóng cửa thì đổi False thành True)
MAINTENANCE_MODE = False 

if MAINTENANCE_MODE:
    st.title("🚧 HỆ THỐNG ĐANG BẢO TRÌ")
    st.warning("Hệ thống Thăng Long đang được nâng cấp. Vui lòng quay lại sau!")
    st.stop() # Dừng lại, không chạy code bên dưới nữa

# 2. KIỂM TRA MẬT KHẨU
if "PASSWORD" in st.secrets: # Chỉ chạy khi đã set mật khẩu trên Cloud
    pwd_input = st.text_input("🔒 Nhập Mật Khẩu Hoàng Gia:", type="password")
    
    if pwd_input != st.secrets["PASSWORD"]:
        st.info("Hệ thống nội bộ Thăng Long. Xin mời nhập mật khẩu để tiếp tục.")
        st.stop() # Dừng lại, không hiện Dashboard nếu sai pass

# 👆👆👆 HẾT PHẦN BẢO MẬT 👆👆👆
# --- CSS: GIAO DIỆN "PROFESSIONAL DARK" (KHÔNG CHÓI) ---
st.markdown("""
<style>
    /* Tổng thể */
    .main {background-color: #0e1117;}
    h1, h2, h3 {color: #64b5f6 !important;} /* Xanh dương dịu */
    [data-testid="stMetricValue"] {font-size: 1.3rem !important; color: #e0e0e0;}
    
    /* Signal Box: Thiết kế dạng thẻ, không tô màu nền chói */
    .signal-card {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .sig-buy {border-left: 5px solid #10b981; color: #10b981;} /* Xanh ngọc */
    .sig-sell {border-left: 5px solid #ef4444; color: #ef4444;} /* Đỏ nhung */
    .sig-wait {border-left: 5px solid #f59e0b; color: #f59e0b;} /* Vàng nghệ */
    
    /* Text nổi bật */
    .big-score {font-size: 24px; font-weight: bold;}
    
    /* Footer */
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: #6b7280; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #374151;}
</style>
""", unsafe_allow_html=True)

# --- TỪ ĐIỂN TÀI CHÍNH (ĐẦY ĐỦ 35 CHỈ SỐ CỦA V7) ---
TRANS_MAP = {
    # Kết quả kinh doanh
    'Total Revenue': '1. Tổng Doanh Thu', 'Operating Revenue': '   - Doanh thu HĐ',
    'Cost Of Revenue': '2. Giá Vốn Hàng Bán', 'Gross Profit': '3. Lợi Nhuận Gộp',
    'Operating Expense': '4. Chi Phí Hoạt Động', 'Operating Income': '5. Lợi Nhuận Từ HĐKD',
    'Net Income': '9. Lợi Nhuận Sau Thuế', 'EBITDA': '10. EBITDA', 'Basic EPS': '11. EPS Cơ Bản',
    # Cân đối kế toán
    'Total Assets': 'A. TỔNG TÀI SẢN', 'Current Assets': '   I. Tài sản Ngắn hạn',
    'Cash And Cash Equivalents': '      1. Tiền & Tương đương tiền', 'Inventory': '      2. Hàng Tồn kho',
    'Total Liabilities Net Minority Interest': 'B. TỔNG NỢ', 'Stockholders Equity': 'C. VỐN CHỦ SỞ HỮU',
    # Dòng tiền
    'Operating Cash Flow': '1. Dòng Tiền KD', 'Investing Cash Flow': '2. Dòng Tiền Đầu Tư',
    'Financing Cash Flow': '3. Dòng Tiền Tài Chính', 'Free Cash Flow': '-> Dòng Tiền Tự Do'
}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.success("👑 **Chủ sở hữu: Thăng Long**")
mode = st.sidebar.radio("Chọn Chế Độ:", ["🔮 Phân Tích Chuyên Sâu", "⚡ Máy Quét (Scanner)"])

# --- BỘ NÃO AI (LOGIC V8 - GIỮ NGUYÊN) ---
def analyze_strategy(df):
    if df.empty or len(df) < 50: return None
    last = df.iloc[-1]
    
    close = last['Close']
    rsi = last['RSI_14']
    ma50 = last['SMA_50']
    macd = last['MACD_12_26_9']
    macds = last['MACDs_12_26_9']
    atr = last['ATRr_14']
    
    score = 5.0
    reasons = []
    
    # 1. Trend
    if close > ma50: score += 2; reasons.append("✅ Xu hướng Tăng (Giá > MA50)")
    else: score -= 2; reasons.append("🔻 Xu hướng Giảm (Giá < MA50)")
        
    # 2. Momentum
    if rsi < 30: score += 3; reasons.append("✅ Quá bán (Vùng giá rẻ - RSI < 30)")
    elif rsi > 70: score -= 3; reasons.append("🔻 Quá mua (Nóng - RSI > 70)")
    else: reasons.append(f"ℹ️ RSI Trung tính ({rsi:.1f})")
        
    # 3. MACD
    if macd > macds: score += 1; reasons.append("✅ MACD cắt lên Signal")
    else: score -= 1; reasons.append("🔻 MACD cắt xuống Signal")
        
    # Kết luận
    action = "QUAN SÁT"
    css = "sig-wait"
    if score >= 7: action = "KHUYẾN NGHỊ MUA"; css = "sig-buy"
    elif score <= 3: action = "KHUYẾN NGHỊ BÁN"; css = "sig-sell"
        
    return {
        "score": score, "action": action, "css": css, "reasons": reasons,
        "entry": close, "stop_loss": close - (2*atr),
        "target_1": close + (2*atr), "target_2": close + (4*atr),
        "roi_2": ((4*atr)/close)*100
    }

# --- TẢI DỮ LIỆU (ROBUST) ---
@st.cache_data(ttl=300)
def load_data_v81(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    
    # Dữ liệu tính toán (Luôn lấy 1 năm để AI tính chuẩn)
    try:
        df_calc = stock.history(period="1y")
        if len(df_calc) > 50:
            df_calc.ta.sma(length=20, append=True)
            df_calc.ta.sma(length=50, append=True)
            df_calc.ta.rsi(length=14, append=True)
            df_calc.ta.bbands(length=20, std=2, append=True)
            df_calc.ta.macd(append=True)
            df_calc.ta.atr(length=14, append=True)
    except: df_calc = pd.DataFrame()

    # Dữ liệu vẽ biểu đồ (Theo khung user chọn)
    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.sma(length=50, append=True)
            df_chart.ta.bbands(length=20, std=2, append=True)
            df_chart.ta.rsi(length=14, append=True) # Thêm RSI cho chart
            df_chart.ta.macd(append=True) # Thêm MACD cho chart
    except: df_chart = pd.DataFrame()

    # Dữ liệu cơ bản (Khôi phục đầy đủ)
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
    try: news = stock.news
    except: news = []

    return df_calc, df_chart, info, fin, bal, cash, holders, news

# --- HỖ TRỢ HIỂN THỊ ---
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
    symbol = st.sidebar.text_input("Nhập Mã CP", value="HPG").upper()
    period = st.sidebar.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Cấu hình biểu đồ")
    show_ma = st.sidebar.checkbox("MA (20, 50)", True)
    show_bb = st.sidebar.checkbox("Bollinger Bands", True)
    show_macd = st.sidebar.checkbox("MACD", True)
    show_rsi = st.sidebar.checkbox("RSI", True)

    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news = load_data_v81(symbol, period)
        
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            
            # 1. AI SIGNAL CARD (Giao diện mới dịu mắt)
            strat = analyze_strategy(df_calc)
            if strat:
                st.markdown(f"""
                <div class="signal-card {strat['css']}">
                    <div class="big-score">{strat['action']} (Điểm: {strat['score']}/10)</div>
                    <div style="margin-top: 10px; font-size: 14px; color: #bbb;">
                        {' | '.join(strat['reasons'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Kế hoạch giao dịch (Hiển thị gọn gàng)
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Giá Vào", f"{strat['entry']:,.0f}")
                k2.metric("Cắt Lỗ (Stop)", f"{strat['stop_loss']:,.0f}")
                k3.metric("Mục Tiêu 1", f"{strat['target_1']:,.0f}")
                k4.metric("Mục Tiêu 2", f"{strat['target_2']:,.0f}", f"+{strat['roi_2']:.1f}%")
            
            st.divider()
            
            # 2. TAB CHI TIẾT (KHÔI PHỤC ĐẦY ĐỦ TỪ V7)
            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ", "💰 Tài Chính", "🏢 Hồ Sơ", "📰 Tin Tức"])
            
            # TAB 1: CHART 4 TẦNG (V6 Style)
            with t1:
                row_h = [0.5, 0.15, 0.2, 0.15]
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.03)
                
                # Giá
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Giá'), row=1, col=1)
                if show_ma:
                    if 'SMA_20' in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
                    if 'SMA_50' in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA_50'], line=dict(color='#2979ff', width=1), name='MA50'), row=1, col=1)
                if show_bb and 'BBU_20_2.0' in df_chart.columns:
                     fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Up'), row=1, col=1)
                     fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Low', fill='tonexty'), row=1, col=1)
                
                # Volume
                colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df_chart.iterrows()]
                fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], marker_color=colors, name='Vol'), row=2, col=1)
                
                # MACD
                if show_macd and 'MACD_12_26_9' in df_chart.columns:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MACD_12_26_9'], line=dict(color='#22d3ee'), name='MACD'), row=3, col=1)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MACDs_12_26_9'], line=dict(color='#f472b6'), name='Signal'), row=3, col=1)
                    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['MACDh_12_26_9'], marker_color='#64748b', name='Hist'), row=3, col=1)
                
                # RSI
                if show_rsi and 'RSI_14' in df_chart.columns:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI_14'], line=dict(color='#a78bfa', width=2), name='RSI'), row=4, col=1)
                    fig.add_hline(y=70, row=4, col=1, line_dash="dot", line_color="#ef4444")
                    fig.add_hline(y=30, row=4, col=1, line_dash="dot", line_color="#10b981")

                fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

            # TAB 2: TÀI CHÍNH (Full 3 bảng)
            with t2:
                st.caption("Đơn vị: Tỷ VNĐ")
                c_left, c_right = st.columns(2)
                with c_left:
                    st.subheader("Kết quả kinh doanh")
                    st.dataframe(clean_table(fin).style.format("{:,.2f}"), use_container_width=True)
                    st.subheader("Dòng tiền")
                    st.dataframe(clean_table(cash).style.format("{:,.2f}"), use_container_width=True)
                with c_right:
                    st.subheader("Cân đối kế toán")
                    st.dataframe(clean_table(bal).style.format("{:,.2f}"), use_container_width=True)
            
            # TAB 3: HỒ SƠ
            with t3:
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(info.get('longBusinessSummary', 'Đang cập nhật...'))
                with c2:
                    st.info(f"Ngành: {info.get('industry', 'N/A')}")
                    st.success(f"Nhân sự: {info.get('fullTimeEmployees', 'N/A')}")
                    st.write("---")
                    st.subheader("Cổ đông lớn")
                    try:
                        if not holders.empty and holders.shape[1] == 2: holders.columns = ['% Nắm', 'Tên']
                        st.dataframe(holders, use_container_width=True)
                    except: st.write("Chưa có dữ liệu")

            # TAB 4: TIN TỨC (Có Fallback Google)
            with t4:
                if news:
                    for n in news:
                        try:
                            dt = datetime.fromtimestamp(n.get('providerPublishTime',0)).strftime('%d/%m %H:%M')
                            st.markdown(f"**{dt}** | [{n.get('title')}]({n.get('link')})")
                        except: pass
                else:
                    st.warning("Yahoo Finance chưa cập nhật tin tức.")
                    st.markdown(f"👉 [Tìm trên Google News](https://www.google.com/search?q=tin+tuc+co+phieu+{symbol}&tbm=nws)")

# ==========================================
# GIAO DIỆN SCANNER (MÁY QUÉT)
# ==========================================
elif mode == "⚡ Máy Quét (Scanner)":
    st.title("⚡ Máy Quét Cơ Hội (Oracle Scanner)")
    input_str = st.text_area("Danh sách mã:", value="HPG, VCB, SSI, VND, FPT, MWG, VNM, MSN, DIG, CEO")
    
    if st.button("🚀 BẮT ĐẦU QUÉT"):
        tickers = [x.strip().upper() for x in input_str.split(',')]
        results = []
        bar = st.progress(0, "AI đang phân tích...")
        
        for i, ticker in enumerate(tickers):
            bar.progress((i+1)/len(tickers), f"Đang chấm điểm: {ticker}")
            try:
                df, _, _, _, _, _, _, _ = load_data_v81(ticker, "1y")
                strat = analyze_strategy(df)
                if strat:
                    results.append({
                        "Mã": ticker, "Giá": f"{strat['entry']:,.0f}",
                        "Điểm": strat['score'], "Hành động": strat['action'].replace("KHUYẾN NGHỊ ", ""),
                        "Lãi Kỳ Vọng": f"{strat['roi_2']:.1f}%"
                    })
            except: pass
        bar.empty()
        
        if results:
            res_df = pd.DataFrame(results).sort_values(by="Điểm", ascending=False)
            
            def color_sig(val):
                if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                return 'color: #f59e0b'
            
            st.dataframe(res_df.style.map(color_sig, subset=['Hành động']), use_container_width=True)
        else: st.error("Không có dữ liệu.")

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V8.1 - Masterpiece</div>', unsafe_allow_html=True)

