import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Emo Stock Dashboard V3", page_icon="🛡️")

# CSS tùy chỉnh
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.8rem !important;}
    h1, h2, h3 {color: #4ecdc4 !important;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
symbol = st.sidebar.text_input("Nhập mã CP (VD: FPT)", value="FPT").upper()
period = st.sidebar.selectbox("Khung thời gian", ["6mo", "1y", "2y", "5y", "max"], index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Chỉ báo Kỹ thuật")
show_ma = st.sidebar.checkbox("Đường MA (20 & 50)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=False)
show_rsi = st.sidebar.checkbox("RSI (Sức mạnh giá)", value=True)

# --- HÀM TẢI DỮ LIỆU "SIÊU BỀN" (Không bao giờ sập) ---
@st.cache_data(ttl=300)
def load_data_robust(ticker_symbol, time_period):
    # Khởi tạo giá trị rỗng mặc định
    df = pd.DataFrame()
    info = {}
    fin = pd.DataFrame()
    bal = pd.DataFrame()
    
    y_symbol = f"{ticker_symbol}.VN"
    stock = yf.Ticker(y_symbol)
    
    # 1. Cố lấy LỊCH SỬ GIÁ (Quan trọng nhất)
    try:
        df = stock.history(period=time_period)
        if not df.empty:
            # Tính toán chỉ báo kỹ thuật (nếu có giá)
            try:
                df.ta.sma(length=20, append=True)
                df.ta.sma(length=50, append=True)
                df.ta.rsi(length=14, append=True)
                df.ta.bbands(length=20, std=2, append=True)
            except: pass # Lỗi chỉ báo thì thôi, vẫn vẽ nến được
    except: pass

    # 2. Cố lấy THÔNG TIN CƠ BẢN
    try:
        info = stock.info
    except: pass

    # 3. Cố lấy BÁO CÁO TÀI CHÍNH (Hay lỗi nhất -> Để riêng)
    try:
        fin = stock.financials
        bal = stock.balance_sheet
    except: pass
    
    return df, info, fin, bal

# --- GIAO DIỆN CHÍNH ---
if symbol:
    # Hứng dữ liệu (Dù thiếu cái nào cũng không sao)
    hist_data, info_data, financials, balance = load_data_robust(symbol, period)
    
    # CHỈ CẦN CÓ GIÁ LÀ HIỆN DASHBOARD
    if not hist_data.empty:
        # --- HEADER ---
        name = info_data.get('longName', symbol) if info_data else symbol
        st.title(f"🛡️ {name}")
        
        # Xử lý giá hiện tại (Lấy từ Info hoặc lấy từ nến cuối cùng)
        if info_data and 'currentPrice' in info_data:
            price = info_data['currentPrice']
        else:
            price = hist_data['Close'].iloc[-1]
            
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Giá", f"{price:,.0f} ₫")
        
        # Các chỉ số khác (kiểm tra kỹ trước khi hiện)
        pe = info_data.get('trailingPE', 'N/A') if info_data else 'N/A'
        pb = info_data.get('priceToBook', 'N/A') if info_data else 'N/A'
        roe = f"{info_data.get('returnOnEquity', 0)*100:.2f}%" if info_data and info_data.get('returnOnEquity') else 'N/A'
        
        m3.metric("P/E", f"{pe}")
        m4.metric("ROE", f"{roe}")

        st.divider()

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ", "💰 Tài chính", "🏢 Hồ sơ"])

        # TAB 1: BIỂU ĐỒ (Luôn hiện nếu có hist_data)
        with tab1:
            try:
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.02, row_heights=[0.6, 0.2, 0.2])
                # Nến
                fig.add_trace(go.Candlestick(x=hist_data.index,
                                open=hist_data['Open'], high=hist_data['High'],
                                low=hist_data['Low'], close=hist_data['Close'], name='Giá'), row=1, col=1)
                # Volume
                fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'], marker_color='teal', name='Vol'), row=2, col=1)
                
                # Chỉ báo (Kiểm tra xem cột có tồn tại không mới vẽ)
                if show_ma and 'SMA_20' in hist_data.columns:
                    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], line=dict(color='orange'), name='MA20'), row=1, col=1)
                
                if show_rsi and 'RSI_14' in hist_data.columns:
                    fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI_14'], line=dict(color='purple'), name='RSI'), row=3, col=1)
                    fig.add_hline(y=70, row=3, col=1, line_dash="dot", line_color="red")
                    fig.add_hline(y=30, row=3, col=1, line_dash="dot", line_color="green")

                fig.update_layout(height=700, xaxis_rangeslider_visible=False, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Lỗi vẽ biểu đồ: {e}")

        # TAB 2: TÀI CHÍNH
        with tab2:
            if not financials.empty:
                st.dataframe(financials)
            else:
                st.warning("⚠️ Không lấy được dữ liệu Báo cáo tài chính (Do nguồn Yahoo bị chặn hoặc chưa cập nhật).")

        # TAB 3: HỒ SƠ
        with tab3:
            if info_data:
                st.write(f"**Mô tả:** {info_data.get('longBusinessSummary', 'Không có mô tả')}")
            else:
                st.warning("⚠️ Không lấy được thông tin hồ sơ.")

    else:
        st.error(f"❌ Không tìm thấy dữ liệu giá cho mã '{symbol}'. Vui lòng kiểm tra lại tên mã hoặc thử lại sau.")
