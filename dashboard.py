import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
from datetime import datetime

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Intelligent V7", page_icon="🐲")

# CSS: Giao diện Cyberpunk & Badge tín hiệu
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.4rem !important; color: #00e676;}
    h1, h2, h3 {color: #2979ff !important;}
    .stDataFrame {border: 1px solid #444; border-radius: 8px;}
    
    /* Signal Badges */
    .buy-signal {background-color: #00c853; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;}
    .sell-signal {background-color: #d50000; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;}
    .hold-signal {background-color: #ffab00; color: black; padding: 5px 10px; border-radius: 5px; font-weight: bold;}
    
    /* News Card */
    .news-card {background-color: #1e1e1e; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid #2979ff;}
    .news-title {font-size: 18px; font-weight: bold; color: #fff;}
    .news-meta {font-size: 12px; color: #888;}
    
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #0e1117; color: #888; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #333;}
</style>
""", unsafe_allow_html=True)

# --- TỪ ĐIỂN TÀI CHÍNH ---
TRANS_MAP = {
    'Total Revenue': 'Tổng Doanh Thu', 'Operating Revenue': 'Doanh thu HĐ',
    'Gross Profit': 'Lợi Nhuận Gộp', 'Net Income': 'Lợi Nhuận Sau Thuế',
    'Basic EPS': 'EPS Cơ Bản', 'Total Assets': 'Tổng Tài Sản',
    'Total Liabilities Net Minority Interest': 'Tổng Nợ', 'Stockholders Equity': 'Vốn Chủ Sở Hữu',
    'Operating Cash Flow': 'Dòng Tiền KD'
}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.success("👑 **Chủ sở hữu: Thăng Long**")

# Chế độ xem
mode = st.sidebar.radio("Chọn Chế Độ:", ["🔍 Phân Tích 1 Mã", "⚡ Lọc Cổ Phiếu (Scanner)"])

# --- HÀM TÍNH TÍN HIỆU (AI SIGNAL) ---
def get_signal(df):
    if df.empty or len(df) < 20: return "Không đủ dữ liệu", "gray"
    
    close = df['Close'].iloc[-1]
    rsi = df['RSI_14'].iloc[-1]
    ma20 = df['SMA_20'].iloc[-1]
    ma50 = df['SMA_50'].iloc[-1]
    
    # Logic Mua/Bán đơn giản (Ngài có thể yêu cầu Emo code phức tạp hơn)
    signal = "NẮM GIỮ (HOLD)"
    color = "hold-signal"
    
    # Điều kiện MUA
    if rsi < 30: 
        signal = "MUA MẠNH (Quá bán)"
        color = "buy-signal"
    elif close > ma20 and df['Close'].iloc[-2] < df['SMA_20'].iloc[-2]:
        signal = "MUA (Cắt lên MA20)"
        color = "buy-signal"
        
    # Điều kiện BÁN
    elif rsi > 70:
        signal = "BÁN NGAY (Quá mua)"
        color = "sell-signal"
    elif close < ma20 and df['Close'].iloc[-2] > df['SMA_20'].iloc[-2]:
        signal = "BÁN (Thủng MA20)"
        color = "sell-signal"
        
    return signal, color

# --- HÀM TẢI DỮ LIỆU ---
@st.cache_data(ttl=300)
def load_data_v7(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    interval = "15m" if time in ["1d", "5d"] else "1d"
    
    # 1. History & Indicators
    try:
        df = stock.history(period=time, interval=interval)
        if len(df) > 20:
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=50, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.macd(append=True)
    except: df = pd.DataFrame()

    # 2. Other Data
    try: info = stock.info
    except: info = {}
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    # 3. News (Tin tức)
    try: news = stock.news
    except: news = []

    return df, info, fin, bal, holders, news, stock

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
# GIAO DIỆN 1: PHÂN TÍCH CHI TIẾT 1 MÃ
# ==========================================
if mode == "🔍 Phân Tích 1 Mã":
    symbol = st.sidebar.text_input("Mã CP", value="FPT").upper()
    period = st.sidebar.selectbox("Thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=3)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Chart")
    show_ma = st.sidebar.checkbox("MA", True)
    show_bb = st.sidebar.checkbox("Bollinger", True)
    show_macd = st.sidebar.checkbox("MACD", True)
    
    if symbol:
        hist, info, fin, bal, holders, news, stock_obj = load_data_v7(symbol, period)
        
        if not hist.empty:
            # --- HEADER VÀ TÍN HIỆU ---
            col_title, col_sig = st.columns([3, 1])
            with col_title:
                st.title(f"💎 {info.get('longName', symbol)}")
            with col_sig:
                # Tính toán tín hiệu
                sig_text, sig_color = get_signal(hist)
                st.markdown(f'<div class="{sig_color}" style="text-align:center; margin-top:20px;">{sig_text}</div>', unsafe_allow_html=True)
            
            # Metrics
            cur = hist['Close'].iloc[-1]
            chg = ((cur - hist['Close'].iloc[-2])/hist['Close'].iloc[-2])*100
            rsi_val = hist['RSI_14'].iloc[-1] if 'RSI_14' in hist.columns else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Giá", f"{cur:,.0f}", f"{chg:.2f}%")
            m2.metric("RSI (14)", f"{rsi_val:.1f}")
            m3.metric("P/E", f"{info.get('trailingPE', 'N/A')}")
            m4.metric("Vốn hóa", f"{info.get('marketCap',0)/1e9:,.0f} Tỷ")
            
            st.divider()
            
            # --- TABS ---
            t1, t2, t3, t4 = st.tabs(["📊 Biểu đồ", "📰 Tin tức", "💰 Tài chính", "🏢 Hồ sơ"])
            
            with t1: # Chart
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.02)
                # Price
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Giá'), row=1, col=1)
                if show_ma:
                    if 'SMA_20' in hist.columns: fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_20'], line=dict(color='orange'), name='MA20'), row=1, col=1)
                if show_bb and 'BBU_20_2.0' in hist.columns:
                     fig.add_trace(go.Scatter(x=hist.index, y=hist['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Up'), row=1, col=1)
                     fig.add_trace(go.Scatter(x=hist.index, y=hist['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Low', fill='tonexty'), row=1, col=1)
                # Volume
                colors = ['red' if r['Open'] > r['Close'] else 'green' for i, r in hist.iterrows()]
                fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], marker_color=colors, name='Vol'), row=2, col=1)
                # MACD
                if show_macd and 'MACD_12_26_9' in hist.columns:
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['MACD_12_26_9'], line=dict(color='cyan'), name='MACD'), row=3, col=1)
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['MACDs_12_26_9'], line=dict(color='orange'), name='Signal'), row=3, col=1)
                    fig.add_trace(go.Bar(x=hist.index, y=hist['MACDh_12_26_9'], marker_color='gray', name='Hist'), row=3, col=1)
                
                fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
                
            with t2: # News
                st.subheader(f"Tin tức mới nhất về {symbol}")
                if news:
                    for n in news:
                        # Yahoo News thường trả về: title, link, publisher, thumbnail
                        try:
                            # Xử lý thời gian
                            pub_time = datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%d/%m/%Y %H:%M')
                            st.markdown(f"""
                            <div class="news-card">
                                <a href="{n.get('link')}" target="_blank" style="text-decoration:none;">
                                    <div class="news-title">{n.get('title')}</div>
                                </a>
                                <div class="news-meta">🕒 {pub_time} | ✍️ {n.get('publisher')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        except: pass
                else:
                    st.info("Hiện chưa tìm thấy tin tức mới từ nguồn Yahoo Finance cho mã này.")
            
            with t3: # Finance
                c1, c2 = st.columns(2)
                with c1: st.dataframe(clean_table(fin).style.format("{:,.2f}"))
                with c2: st.dataframe(clean_table(bal).style.format("{:,.2f}"))
                
            with t4: # Profile
                st.write(info.get('longBusinessSummary'))
                st.dataframe(holders)

# ==========================================
# GIAO DIỆN 2: BỘ LỌC CỔ PHIẾU (SCANNER)
# ==========================================
elif mode == "⚡ Lọc Cổ Phiếu (Scanner)":
    st.title("⚡ Máy Quét Tín Hiệu (Watchlist Scanner)")
    st.caption("Nhập danh sách mã cổ phiếu để hệ thống tự động tìm điểm mua/bán.")
    
    # Khu vực nhập liệu
    input_str = st.text_area("Nhập danh sách mã (cách nhau bởi dấu phẩy)", value="HPG, VCB, SSI, VND, FPT, MWG, VNM, MSN")
    scan_btn = st.button("🚀 BẮT ĐẦU QUÉT")
    
    if scan_btn:
        tickers = [x.strip().upper() for x in input_str.split(',')]
        results = []
        
        my_bar = st.progress(0, text="Đang khởi động máy quét...")
        
        for i, ticker in enumerate(tickers):
            # Cập nhật tiến độ
            my_bar.progress((i + 1) / len(tickers), text=f"Đang soi: {ticker}...")
            
            # Tải dữ liệu nhanh (3 tháng là đủ tính RSI/MA)
            try:
                stock = yf.Ticker(f"{ticker}.VN")
                df = stock.history(period="6mo") # Lấy 6 tháng cho chắc
                
                if len(df) > 20:
                    # Tính chỉ báo
                    df.ta.rsi(length=14, append=True)
                    df.ta.sma(length=20, append=True)
                    
                    # Lấy giá trị mới nhất
                    price = df['Close'].iloc[-1]
                    rsi = df['RSI_14'].iloc[-1]
                    
                    # Lấy tín hiệu
                    sig_text, sig_color = get_signal(df)
                    
                    # Đánh giá xu hướng ngắn hạn
                    trend = "Tăng" if price > df['SMA_20'].iloc[-1] else "Giảm"
                    
                    results.append({
                        "Mã": ticker,
                        "Giá": f"{price:,.0f}",
                        "Xu hướng": trend,
                        "RSI (14)": round(rsi, 1),
                        "Tín hiệu": sig_text
                    })
            except: pass
            
        my_bar.empty() # Xóa thanh tiến độ
        
        # Hiển thị kết quả
        if results:
            res_df = pd.DataFrame(results)
            
            # Tô màu cho bảng đẹp hơn
            def highlight_signal(val):
                color = ''
                if 'MUA' in val: color = 'background-color: #004d40; color: #00e676'
                elif 'BÁN' in val: color = 'background-color: #4a0000; color: #ff5252'
                return color

            st.dataframe(res_df.style.map(highlight_signal, subset=['Tín hiệu']), use_container_width=True)
            
            # Thống kê nhanh
            buy_count = len([x for x in results if 'MUA' in x['Tín hiệu']])
            st.success(f"✅ Tìm thấy {buy_count} mã có tín hiệu MUA trong danh sách theo dõi của Ngài!")
        else:
            st.error("Không quét được mã nào. Vui lòng kiểm tra lại danh sách.")

# --- FOOTER ---
st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V7 - Intelligent Eye</div>', unsafe_allow_html=True)
