import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# 👇 ĐÃ SỬA: Bỏ 'stock_eval' đi để không bị lỗi nữa
from vnstock import stock_historical_data, company_overview 
from datetime import datetime, timedelta

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Emo Stock Dashboard")

# --- CSS TÙY CHỈNH ---
st.markdown("""
<style>
    .metric-card {
        background-color: #0e1117;
        border: 1px solid #262730;
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: BỘ LỌC ---
st.sidebar.title("🔍 Bộ Lọc Cổ Phiếu")
symbol = st.sidebar.text_input("Nhập mã CK (VD: HPG)", value="HPG").upper()
days_back = st.sidebar.slider("Số ngày phân tích", 30, 730, 365)

# --- HÀM LẤY DỮ LIỆU ---
def load_data(symbol, days):
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        df = stock_historical_data(symbol, start_date, end_date, "1D", "stock")
        if not df.empty:
            # Tính chỉ báo kỹ thuật
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA50'] = df['close'].rolling(window=50).mean()
            
            # Tính RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
        return df
    except:
        return pd.DataFrame()

# --- GIAO DIỆN CHÍNH ---
st.title(f"📊 Phân Tích Chuyên Sâu: {symbol}")

# TẢI DỮ LIỆU
data = load_data(symbol, days_back)

if not data.empty:
    latest = data.iloc[-1]
    prev = data.iloc[-2]
    change = latest['close'] - prev['close']
    pct_change = (change / prev['close']) * 100
    
    # --- HEADER: GIÁ & CHỈ SỐ ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Giá hiện tại", f"{int(latest['close']):,}", f"{pct_change:.2f}%")
    col2.metric("Khối lượng", f"{int(latest['volume']):,}")
    
    # Lấy thông tin cơ bản
    try:
        profile = company_overview(symbol)
        # Xử lý an toàn nếu không lấy được chỉ số
        pe = profile['priceToEarning'][0] if 'priceToEarning' in profile else "N/A"
        roe = profile['roe'][0] if 'roe' in profile else "N/A"
        col3.metric("P/E", f"{pe}")
        col4.metric("ROE", f"{roe}")
    except:
        col3.metric("P/E", "-")
        col4.metric("ROE", "-")

    # --- BIỂU ĐỒ (CANDLESTICK + RSI) ---
    st.subheader("📈 Biểu đồ Kỹ thuật")
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.7, 0.3])

    # Nến
    fig.add_trace(go.Candlestick(x=data['time'],
                    open=data['open'], high=data['high'],
                    low=data['low'], close=data['close'], name='Giá'), row=1, col=1)
    
    # MA Lines
    fig.add_trace(go.Scatter(x=data['time'], y=data['MA20'], line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data['time'], y=data['MA50'], line=dict(color='blue', width=1), name='MA50'), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=data['time'], y=data['RSI'], line=dict(color='purple', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # DỮ LIỆU BẢNG
    with st.expander("Xem dữ liệu chi tiết"):
        st.dataframe(data.sort_values(by='time', ascending=False), use_container_width=True)

else:
    st.error(f"Không tìm thấy dữ liệu hoặc mã {symbol} bị lỗi. Vui lòng kiểm tra lại.")