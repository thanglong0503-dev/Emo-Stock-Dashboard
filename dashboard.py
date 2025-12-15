import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Emo Pro Dashboard V2", page_icon="🚀")

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

# --- HÀM TẢI DỮ LIỆU (ĐÃ SỬA LỖI CACHE) ---
@st.cache_data(ttl=300)
def load_data_pro(ticker_symbol, time_period):
    try:
        y_symbol = f"{ticker_symbol}.VN"
        stock = yf.Ticker(y_symbol)
        
        # 1. Lấy lịch sử giá
        df = stock.history(period=time_period)
        
        if df.empty: return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

        # 2. Tính toán kỹ thuật
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        
        # 3. Lấy thông tin (Info)
        info = stock.info
        
        # 4. Lấy Báo cáo tài chính (Lấy luôn ở đây để lưu Cache được)
        fin = stock.financials
        bal = stock.balance_sheet
        
        # 👇 QUAN TRỌNG: Chỉ trả về Dữ liệu (DataFrame/Dict), KHÔNG trả về 'stock' object
        return df, info, fin, bal
        
    except Exception as e:
        print(f"Lỗi: {e}")
        return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

# --- GIAO DIỆN CHÍNH ---
if symbol:
    # Hứng 4 món dữ liệu trả về
    hist_data, info_data, financials, balance = load_data_pro(symbol, period)
    
    if not hist_data.empty:
        # --- HEADER ---
        st.title(f"🚀 {info_data.get('longName', symbol)}")
        
        current_price = info_data.get('currentPrice', 0)
        prev_close = info_data.get('previousClose', 0)
        delta_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Giá hiện tại", f"{current_price:,.0f} ₫", f"{delta_pct:.2f}%")
        mkt_cap = info_data.get('marketCap', 0)
        m2.metric("Vốn hóa", f"{mkt_cap/1_000_000_000:,.0f} Tỷ")
        m3.metric("P/E", f"{info_data.get('trailingPE', 'N/A')}")
        m4.metric("ROE", f"{info_data.get('returnOnEquity', 0)*100:.2f}%")

        st.divider()

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "💰 Sức khỏe Tài chính", "🏢 Hồ sơ Công ty"])

        # TAB 1: BIỂU ĐỒ
        with tab1:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.02, 
                                row_heights=[0.6, 0.2, 0.2],
                                subplot_titles=("Hành động Giá", "Khối lượng", "RSI"))

            # Nến
            fig.add_trace(go.Candlestick(x=hist_data.index,
                            open=hist_data['Open'], high=hist_data['High'],
                            low=hist_data['Low'], close=hist_data['Close'], name='Giá'), row=1, col=1)

            # Chỉ báo
            if show_ma:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], line=dict(color='orange', width=1), name='MA 20'), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_50'], line=dict(color='blue', width=1), name='MA 50'), row=1, col=1)
            
            if show_bb:
                bb_upper = hist_data[f'BBU_{20}_{2.0}']
                bb_lower = hist_data[f'BBL_{20}_{2.0}']
                fig.add_trace(go.Scatter(x=hist_data.index, y=bb_upper, line=dict(color='gray', width=1, dash='dot'), name='BB Upper'), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist_data.index, y=bb_lower, line=dict(color='gray', width=1, dash='dot'), name='BB Lower', fill='tonexty'), row=1, col=1)

            # Volume
            colors = ['#ef5350' if row['Open'] - row['Close'] >= 0 else '#26a69a' for index, row in hist_data.iterrows()]
            fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

            # RSI
            if show_rsi:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI_14'], line=dict(color='purple', width=2), name='RSI'), row=3, col=1)
                fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
