import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Emo Stock Dashboard", page_icon="📈")

# --- CSS ---
st.markdown("""
<style>
    .metric-card {background-color: #0e1117; border: 1px solid #262730; padding: 15px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🔍 Bộ Lọc")
symbol = st.sidebar.text_input("Nhập mã (VD: NVL, HPG)", value="HPG").upper()
period = st.sidebar.selectbox("Khung thời gian", ["1y", "2y", "5y", "max"], index=2)

# --- HÀM LẤY DỮ LIỆU ---
def load_data(ticker_symbol, time_period):
    try:
        # Yahoo cần đuôi .VN
        stock = yf.Ticker(f"{ticker_symbol}.VN")
        hist = stock.history(period=time_period)
        info = stock.info
        return hist, info
    except:
        return pd.DataFrame(), {}

# --- GIAO DIỆN CHÍNH ---
st.title(f"🌍 Dashboard Quốc Tế: {symbol}")

if symbol:
    hist_data, info_data = load_data(symbol, period)
    
    if not hist_data.empty:
        # 1. HIỂN THỊ CHỈ SỐ CƠ BẢN
        current_price = info_data.get('currentPrice', 0)
        prev_close = info_data.get('previousClose', 0)
        delta = current_price - prev_close
        delta_pct = (delta / prev_close) * 100 if prev_close else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Giá hiện tại", f"{current_price:,} VND", f"{delta_pct:.2f}%")
        c2.metric("P/E", f"{info_data.get('trailingPE', 'N/A')}")
        c3.metric("P/B", f"{info_data.get('priceToBook', 'N/A')}")
        c4.metric("ROE", f"{info_data.get('returnOnEquity', 0)*100:.2f}%")

        # 2. BIỂU ĐỒ NẾN + KHỐI LƯỢNG
        st.subheader("📈 Biểu đồ Giá & Khối lượng")
        
        # Tạo biểu đồ 2 ngăn
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, row_heights=[0.7, 0.3])

        # Nến
        fig.add_trace(go.Candlestick(x=hist_data.index,
                        open=hist_data['Open'], high=hist_data['High'],
                        low=hist_data['Low'], close=hist_data['Close'], name='Giá'), row=1, col=1)
        
        # Khối lượng
        colors = ['red' if row['Open'] - row['Close'] >= 0 else 'green' for index, row in hist_data.iterrows()]
        fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

        fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        # 3. THÔNG TIN DOANH NGHIỆP
        with st.expander("🏢 Xem Hồ Sơ Doanh Nghiệp"):
            st.write(f"**Tên công ty:** {info_data.get('longName', '')}")
            st.write(f"**Lĩnh vực:** {info_data.get('industry', '')}")
            st.write(f"**Mô tả:** {info_data.get('longBusinessSummary', '')}")

    else:
        st.error(f"Không tìm thấy dữ liệu mã {symbol}. Hãy thử mã khác!")
