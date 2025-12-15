import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Emo Stock Dashboard Final", page_icon="💎")

# CSS: Tùy chỉnh giao diện đẹp
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.6rem !important; color: #4ecdc4;}
    h1, h2, h3 {color: #ff6b6b !important;}
    .stDataFrame {border: 1px solid #333; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# --- TỪ ĐIỂN DỊCH THUẬT (Anh -> Việt) ---
TRANS_MAP = {
    'Total Revenue': 'Tổng Doanh thu',
    'Operating Revenue': 'Doanh thu Hoạt động',
    'Gross Profit': 'Lợi nhuận gộp',
    'Net Income': 'Lợi nhuận sau thuế',
    'Total Assets': 'Tổng Tài Sản',
    'Total Liabilities Net Minority Interest': 'Tổng Nợ phải trả',
    'Stockholders Equity': 'Vốn chủ sở hữu',
    'Operating Cash Flow': 'Dòng tiền từ KD',
    'Investing Cash Flow': 'Dòng tiền đầu tư',
    'Financing Cash Flow': 'Dòng tiền tài chính',
    'Free Cash Flow': 'Dòng tiền tự do',
    'Basic EPS': 'EPS Cơ bản'
}

# --- SIDEBAR: BỘ LỌC ---
st.sidebar.title("🎛️ Trung Tâm Điều Khiển")
symbol = st.sidebar.text_input("Nhập mã CP (VD: FPT)", value="FPT").upper()

# Cấu hình khung thời gian (Thêm Intraday)
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
@st.cache_data(ttl=300) # Lưu cache 5 phút
def load_data_final(ticker_symbol, time_period):
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

    # 2. Các dữ liệu khác (Dùng try-except để không sập app nếu Yahoo lỗi)
    try: info = stock.info
    except: info = {}
    
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()
    
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    return df, info, fin, bal, holders, interval

# --- HÀM HỖ TRỢ ĐỊNH DẠNG ---
def safe_fmt(val, fmt="{:,}"):
    """Định dạng số an toàn, gặp N/A thì trả về chữ N/A"""
    try:
        if val is None or val == 'N/A': return "N/A"
        return fmt.format(val)
    except: return str(val)

def process_financials(df):
    """Lọc dòng, dịch tiếng Việt và chia cho 1 Tỷ"""
    if df.empty: return pd.DataFrame()
    # Lọc dòng cần thiết
    valid_idx = [i for i in df.index if i in TRANS_MAP]
    if not valid_idx: return df
    
    df_new = df.loc[valid_idx].rename(index=TRANS_MAP)
    
    # Chia cho 1 Tỷ (Trừ dòng EPS)
    for col in df_new.columns:
        for idx in df_new.index:
            if "EPS" not in idx:
                val = df_new.loc[idx, col]
                if isinstance(val, (int, float)):
                    df_new.loc[idx, col] = val / 1_000_000_000
    return df_new

# --- GIAO DIỆN CHÍNH ---
if symbol:
    hist_data, info, fin, bal, holders, interval = load_data_final(symbol, period)
    
    if not hist_data.empty:
        # === HEADER ===
        st.title(f"💎 {info.get('longName', symbol)}")
        
        # Giá hiện tại (Lấy nến cuối cùng)
        now_price = hist_data['Close'].iloc[-1]
        
        # Tính thay đổi giá
        prev_price = hist_data['Close'].iloc[-2] if len(hist_data) > 1 else now_price
        change_pct = ((now_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
        
        # Hiển thị Metric
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Giá ({interval})", f"{now_price:,.0f} ₫", f"{change_pct:.2f}%")
        
        mk_cap = info.get('marketCap', 0)
        c2.metric("Vốn hóa", f"{mk_cap/1_000_000_000:,.0f} Tỷ" if mk_cap else "N/A")
        c3.metric("P/E", f"{info.get('trailingPE', 'N/A')}")
        roe = info.get('returnOnEquity')
        c4.metric("ROE", f"{roe*100:.2f}%" if roe else "N/A")

        st.divider()

        # === TABS NỘI DUNG ===
        tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ", "💰 Tài chính", "🏢 Hồ sơ"])

        # --- TAB 1: BIỂU ĐỒ ---
        with tab1:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
            
            # 1. Nến
            fig.add_trace(go.Candlestick(x=hist_data.index, open=hist_data['Open'], high=hist_data['High'], low=hist_data['Low'], close=hist_data['Close'], name='Giá'), row=1, col=1)
            
            # 2. Chỉ báo MA
            if show_ma:
                if 'SMA_20' in hist_data.columns: fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
                if 'SMA_50' in hist_data.columns: fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_50'], line=dict(color='blue', width=1), name='MA50'), row=1, col=1)
            
            # 3. Chỉ báo BB
            if show_bb and 'BBU_20_2.0' in hist_data.columns:
                 fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Upper'), row=1, col=1)
                 fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Lower', fill='tonexty'), row=1, col=1)

            # 4. Volume
            colors = ['red' if row['Open'] - row['Close'] >= 0 else 'green' for index, row in hist_data.iterrows()]
            fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'], marker_color=colors, name='Vol'), row=2, col=1)
            
            # 5. RSI
            if show_rsi and 'RSI_14' in hist_data.columns:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI_14'], line=dict(color='purple', width=2), name='RSI'), row=3, col=1)
                fig.add_hline(y=70, row=3, col=1, line_dash="dot", line_color="red")
                fig.add_hline(y=30, row=3, col=1, line_dash="dot", line_color="green")

            fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

        # --- TAB 2: TÀI CHÍNH ---
        with tab2:
            st.caption("ℹ️ Đơn vị tính: Tỷ VNĐ (Dữ liệu từ Yahoo Finance)")
            col_L, col_R = st.columns(2)
            
            with col_L:
                st.subheader("Kết quả kinh doanh")
                st.dataframe(process_financials(fin).style.format("{:,.2f}"), use_container_width=True)
            
            with col_R:
                st.subheader("Cân đối kế toán")
                st.dataframe(process_financials(bal).style.format("{:,.2f}"), use_container_width=True)

        # --- TAB 3: HỒ SƠ ---
        with tab3:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write(f"**Mô tả:** {info.get('longBusinessSummary', 'Chưa có mô tả từ Yahoo.')}")
            with c2:
                # Fix lỗi hiển thị Nhân sự
                employees = info.get('fullTimeEmployees', 'N/A')
                st.info(f"**Nhân sự:** {safe_fmt(employees)} người")
                st.info(f"**Ngành:** {info.get('industry', 'N/A')}")
                st.info(f"**Website:** {info.get('website', 'N/A')}")
                
                st.divider()
                st.subheader("Cổ đông lớn")
                # Fix lỗi hiển thị Cột
                if not holders.empty:
                    try:
                        # Yahoo thường trả về 2 cột: [% Nắm giữ, Tên]
                        if holders.shape[1] == 2: holders.columns = ['% Nắm giữ', 'Tên Cổ đông']
                        st.dataframe(holders, use_container_width=True)
                    except:
                        st.dataframe(holders)
                else:
                    st.write("Chưa có dữ liệu cổ đông.")

    else:
        st.error(f"⚠️ Không tìm thấy dữ liệu cho mã '{symbol}' trong khung thời gian này. Vui lòng thử mã khác hoặc khung thời gian dài hơn.")

else:
    st.info("👈 Mời My Lord nhập mã cổ phiếu để bắt đầu!")
