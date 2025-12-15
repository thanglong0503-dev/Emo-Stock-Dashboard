import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Emo Stock Dashboard V5", page_icon="🐲")

# CSS: Tùy chỉnh giao diện
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.6rem !important; color: #4ecdc4;}
    h1, h2, h3 {color: #ff6b6b !important;}
</style>
""", unsafe_allow_html=True)

# --- TỪ ĐIỂN DỊCH THUẬT ---
TRANS_MAP = {
    'Total Revenue': 'Tổng Doanh thu',
    'Gross Profit': 'Lợi nhuận gộp',
    'Net Income': 'Lợi nhuận sau thuế',
    'Total Assets': 'Tổng Tài Sản',
    'Total Liabilities Net Minority Interest': 'Tổng Nợ phải trả',
    'Stockholders Equity': 'Vốn chủ sở hữu',
    'Operating Cash Flow': 'Dòng tiền từ KD'
}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trung Tâm Điều Khiển")
symbol = st.sidebar.text_input("Nhập mã CP (VD: VCB)", value="VCB").upper()

# 👇 NÂNG CẤP: Thêm nhiều mốc thời gian ngắn hạn
time_options = {
    "1 Ngày (Intraday)": "1d",
    "5 Ngày (Intraday)": "5d",
    "1 Tháng": "1mo",
    "3 Tháng": "3mo",
    "6 Tháng": "6mo",
    "1 Năm": "1y",
    "3 Năm": "3y",
    "5 Năm": "5y",
    "Tất cả": "max"
}
selected_period_name = st.sidebar.selectbox("Khung thời gian", list(time_options.keys()), index=5)
period = time_options[selected_period_name]

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Cấu hình Biểu đồ")
show_ma = st.sidebar.checkbox("Đường MA (20 & 50)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=False)
show_rsi = st.sidebar.checkbox("RSI (Sức mạnh giá)", value=True)

# --- HÀM TẢI DỮ LIỆU THÔNG MINH ---
@st.cache_data(ttl=300)
def load_data_v5(ticker_symbol, time_period):
    y_symbol = f"{ticker_symbol}.VN"
    stock = yf.Ticker(y_symbol)
    
    # 1. Xử lý Lịch sử giá (Tự động chỉnh Interval)
    # Nếu xem 1d, 5d -> Lấy nến 15 phút. Còn lại lấy nến Ngày.
    interval = "15m" if time_period in ["1d", "5d"] else "1d"
    
    try:
        df = stock.history(period=time_period, interval=interval)
        if not df.empty:
            # Chỉ tính chỉ báo nếu đủ dữ liệu (trên 20 nến)
            if len(df) > 20:
                try:
                    df.ta.sma(length=20, append=True)
                    df.ta.sma(length=50, append=True)
                    df.ta.rsi(length=14, append=True)
                    df.ta.bbands(length=20, std=2, append=True)
                except: pass
    except: df = pd.DataFrame()

    # 2. Các dữ liệu khác (Bọc kỹ để không lỗi)
    try: info = stock.info
    except: info = {}
    
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()
    
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    return df, info, fin, bal, holders, interval

# --- HÀM HỖ TRỢ HIỂN THỊ ---
def safe_fmt(val, fmt="{:,}"):
    """Hàm định dạng số an toàn, gặp lỗi trả về N/A chứ không sập app"""
    try:
        if val is None or val == 'N/A': return "N/A"
        if isinstance(val, str): return val
        return fmt.format(val)
    except: return str(val)

def process_financials(df):
    if df.empty: return pd.DataFrame()
    # Lọc dòng cần thiết
    valid_idx = [i for i in df.index if i in TRANS_MAP]
    if not valid_idx: return df
    
    df_new = df.loc[valid_idx].rename(index=TRANS_MAP)
    # Chia cho 1 Tỷ
    for col in df_new.columns:
        df_new[col] = df_new[col].apply(lambda x: x/1_000_000_000 if isinstance(x, (int, float)) else x)
    return df_new

# --- GIAO DIỆN CHÍNH ---
if symbol:
    hist_data, info, fin, bal, holders, interval = load_data_v5(symbol, period)
    
    if not hist_data.empty:
        # --- HEADER ---
        st.title(f"🐲 {info.get('longName', symbol)}")
        
        # Giá hiện tại (Lấy nến cuối cùng cho chính xác nhất với khung thời gian)
        now_price = hist_data['Close'].iloc[-1]
        
        # Tính thay đổi giá (So với nến trước đó)
        prev_price = hist_data['Close'].iloc[-2] if len(hist_data) > 1 else now_price
        change_pct = ((now_price - prev_price) / prev_price) * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Giá ({interval})", f"{now_price:,.0f} ₫", f"{change_pct:.2f}%")
        
        mk_cap = info.get('marketCap', 0)
        c2.metric("Vốn hóa", f"{mk_cap/1_000_000_000:,.0f} Tỷ" if mk_cap else "N/A")
        c3.metric("P/E", f"{info.get('trailingPE', 'N/A')}")
        roe = info.get('returnOnEquity')
        c4.metric("ROE", f"{roe*100:.2f}%" if roe else "N/A")

        st.divider()

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ", "💰 Tài chính", "🏢 Hồ sơ"])

        with tab1:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
            # Nến
            fig.add_trace(go.Candlestick(x=hist_data.index, open=hist_data['Open'], high=hist_data['High'], low=hist_data['Low'], close=hist_data['Close'], name='Giá'), row=1, col=1)
            
            # Chỉ báo (Chỉ vẽ nếu có dữ liệu)
            if show_ma and 'SMA_20' in hist_data.columns:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], line=dict(color='orange'), name='MA20'), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_50'], line=dict(color='blue'), name='MA50'), row=1, col=1)
            
            if show_bb and 'BBU_20_2.0' in hist_data.columns:
                 fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='Upper'), row=1, col=1)
                 fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='Lower', fill='tonexty'), row=1, col=1)

            # Volume
            fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'], marker_color='teal', name='Vol'), row=2, col=1)
            
            # RSI
            if show_rsi and 'RSI_14' in hist_data.columns:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI_14'], line=dict(color='purple'), name='RSI'), row=3, col=1)
                fig.add_hline(y=70, row=3, col=1, line_dash="dot", line_color="red")
                fig.add_hline(y=30, row=3, col=1, line_dash="dot", line_color="green")

            fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.caption("Đơn vị: Tỷ VNĐ")
            col_L, col_R = st.columns(2)
            with col_L:
                st.subheader("Kết quả kinh doanh")
                st.dataframe(process_financials(fin).style.format("{:,.2f}"), use_container_width=True)
            with col_R:
                st.subheader("Cân đối kế toán")
                st.dataframe(process_financials(bal).style.format("{:,.2f}"), use_container_width=True)

        with tab3:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"**Mô tả:** {info.get('longBusinessSummary', 'Chưa có mô tả')}")
            with c2:
                # 👇 FIX LỖI VALUE ERROR Ở ĐÂY (Dùng safe_fmt)
                employees = info.get('fullTimeEmployees', 'N/A')
                st.info(f"**Nhân sự:** {safe_fmt(employees)} người")
                st.info(f"**Ngành:** {info.get('industry', 'N/A')}")
                
                st.divider()
                st.subheader("Cổ đông lớn")
                # 👇 FIX LỖI CỘT Ở ĐÂY (Không ép đổi tên nếu cột không khớp)
                if not holders.empty:
                    try:
                        if holders.shape[1] == 2: holders.columns = ['% Nắm giữ', 'Tên']
                        st.dataframe(holders, use_container_width=True)
                    except:
                        st.dataframe(holders) # In bảng gốc nếu lỗi
                else:
                    st.write("Chưa có dữ liệu cổ đông.")

    else:
        st.error(f"⚠️ Không tìm thấy dữ liệu cho {symbol} trong khung {selected_period_name}.")
