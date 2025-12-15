import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Stock Dashboard", page_icon="👑")

# CSS: Giao diện tối tân & Đánh dấu chủ quyền
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.5rem !important; color: #00e676;}
    h1, h2, h3 {color: #2979ff !important;}
    .stDataFrame {border: 1px solid #444; border-radius: 8px;}
    
    /* Footer đánh dấu chủ quyền */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        color: #888;
        text-align: center;
        font-size: 12px;
        padding: 5px;
        border-top: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- TỪ ĐIỂN TÀI CHÍNH ---
TRANS_MAP = {
    'Total Revenue': '1. Tổng Doanh Thu',
    'Operating Revenue': '   - Doanh thu Hoạt động',
    'Cost Of Revenue': '2. Giá Vốn Hàng Bán',
    'Gross Profit': '3. Lợi Nhuận Gộp',
    'Operating Expense': '4. Chi Phí Hoạt Động',
    'Operating Income': '5. Lợi Nhuận Từ HĐKD',
    'Net Income': '9. Lợi Nhuận Sau Thuế (Lãi Ròng)',
    'EBITDA': '10. EBITDA',
    'Basic EPS': '11. EPS Cơ Bản (VND)',
    'Total Assets': 'A. TỔNG TÀI SẢN',
    'Current Assets': '   I. Tài sản Ngắn hạn',
    'Cash And Cash Equivalents': '      1. Tiền & Tương đương tiền',
    'Inventory': '      2. Hàng Tồn kho',
    'Total Liabilities Net Minority Interest': 'B. TỔNG NỢ PHẢI TRẢ',
    'Stockholders Equity': 'C. VỐN CHỦ SỞ HỮU',
    'Operating Cash Flow': '1. Dòng Tiền Từ Kinh Doanh',
    'Investing Cash Flow': '2. Dòng Tiền Từ Đầu Tư',
    'Financing Cash Flow': '3. Dòng Tiền Tài Chính',
    'Free Cash Flow': '-> Dòng Tiền Tự Do (FCF)'
}

# --- SIDEBAR: KHU VỰC ĐÁNH DẤU CHỦ QUYỀN ---
st.sidebar.title("🎛️ Trạm Điều Khiển")

# 👇👇👇 DÒNG CHỮ KHẲNG ĐỊNH CHỦ QUYỀN CỦA NGÀI 👇👇👇
st.sidebar.success("👑 **Chủ sở hữu: Thăng Long**")
st.sidebar.caption("🚀 Hệ thống phân tích độc quyền")
st.sidebar.markdown("---")

symbol = st.sidebar.text_input("Mã CP (VD: FPT)", value="FPT").upper()

time_options = {
    "1 Ngày (15p)": "1d", "5 Ngày (15p)": "5d",
    "1 Tháng": "1mo", "3 Tháng": "3mo", "6 Tháng": "6mo",
    "1 Năm": "1y", "3 Năm": "3y", "5 Năm": "5y", "Tất cả": "max"
}
sel_time = st.sidebar.selectbox("Khung thời gian", list(time_options.keys()), index=5)
period = time_options[sel_time]

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Cấu hình Chart")
show_ma = st.sidebar.checkbox("MA (20 & 50)", True)
show_bb = st.sidebar.checkbox("Bollinger Bands", True)
show_macd = st.sidebar.checkbox("MACD (Xu hướng)", True)
show_rsi = st.sidebar.checkbox("RSI (Động lượng)", True)

# --- HÀM TẢI DỮ LIỆU ---
@st.cache_data(ttl=300)
def load_data_v6(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    interval = "15m" if time in ["1d", "5d"] else "1d"
    try:
        df = stock.history(period=time, interval=interval)
        if len(df) > 20:
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=50, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.macd(append=True)
    except: df = pd.DataFrame()

    try: info = stock.info
    except: info = {}
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()
    try: cash = stock.cashflow
    except: cash = pd.DataFrame()
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()

    return df, info, fin, bal, cash, holders, interval

# --- HÀM XỬ LÝ SỐ LIỆU ---
def fmt_money(val):
    try:
        if isinstance(val, (int, float)): return val / 1_000_000_000
        return val
    except: return val

def clean_table(df):
    if df.empty: return pd.DataFrame()
    valid = [i for i in df.index if i in TRANS_MAP]
    if not valid: return df
    df_new = df.loc[valid].rename(index=TRANS_MAP)
    for col in df_new.columns:
        for idx in df_new.index:
            if "EPS" not in idx:
                df_new.loc[idx, col] = fmt_money(df_new.loc[idx, col])
    return df_new

# --- GIAO DIỆN CHÍNH ---
if symbol:
    hist, info, fin, bal, cash, holders, interval = load_data_v6(symbol, period)
    
    if not hist.empty:
        # HEADER
        st.title(f"💎 {info.get('longName', symbol)}")
        
        cur = hist['Close'].iloc[-1]
        pre = hist['Close'].iloc[-2] if len(hist)>1 else cur
        chg = ((cur-pre)/pre)*100
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Giá Khớp", f"{cur:,.0f}", f"{chg:.2f}%")
        c2.metric("Vốn hóa", f"{info.get('marketCap',0)/1e9:,.0f} Tỷ")
        c3.metric("P/E", f"{info.get('trailingPE', 'N/A')}")
        
        try:
            rev = fin.loc['Total Revenue'].iloc[0]
            profit = fin.loc['Net Income'].iloc[0]
            margin = (profit/rev)*100
            c4.metric("Biên Lãi Ròng", f"{margin:.1f}%")
        except: c4.metric("Biên Lãi Ròng", "N/A")
            
        c5.metric("ROE", f"{info.get('returnOnEquity',0)*100:.2f}%")

        st.divider()

        tab1, tab2, tab3 = st.tabs(["📊 BIỂU ĐỒ CHUYÊN SÂU", "💰 BÁO CÁO TÀI CHÍNH", "🏢 HỒ SƠ & LÃNH ĐẠO"])

        # TAB 1: BIỂU ĐỒ
        with tab1:
            row_heights = [0.5, 0.15, 0.2, 0.15]
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=row_heights)

            # Giá
            fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Giá'), row=1, col=1)
            if show_ma:
                if 'SMA_20' in hist.columns: fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_20'], line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
                if 'SMA_50' in hist.columns: fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_50'], line=dict(color='blue', width=1), name='MA50'), row=1, col=1)
            if show_bb and 'BBU_20_2.0' in hist.columns:
                 fig.add_trace(go.Scatter(x=hist.index, y=hist['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='Upper'), row=1, col=1)
                 fig.add_trace(go.Scatter(x=hist.index, y=hist['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='Lower', fill='tonexty'), row=1, col=1)
            
            # Volume
            colors = ['red' if r['Open'] - r['Close'] >= 0 else '#00e676' for i, r in hist.iterrows()]
            fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], marker_color=colors, name='Vol'), row=2, col=1)

            # MACD
            if show_macd and 'MACD_12_26_9' in hist.columns:
                fig.add_trace(go.Scatter(x=hist.index, y=hist['MACD_12_26_9'], line=dict(color='cyan', width=1.5), name='MACD'), row=3, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist['MACDs_12_26_9'], line=dict(color='orange', width=1), name='Signal'), row=3, col=1)
                hist_colors = ['red' if val < 0 else 'green' for val in hist['MACDh_12_26_9']]
                fig.add_trace(go.Bar(x=hist.index, y=hist['MACDh_12_26_9'], marker_color=hist_colors, name='Hist'), row=3, col=1)

            # RSI
            if show_rsi and 'RSI_14' in hist.columns:
                fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI_14'], line=dict(color='#ab47bc', width=2), name='RSI'), row=4, col=1)
                fig.add_hline(y=70, row=4, col=1, line_dash="dot", line_color="red")
                fig.add_hline(y=30, row=4, col=1, line_dash="dot", line_color="green")

            fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

        # TAB 2 & 3
        with tab2:
            st.info("ℹ️ Đơn vị: Tỷ VNĐ")
            c_left, c_right = st.columns(2)
            with c_left:
                st.subheader("📋 Kết quả kinh doanh")
                st.dataframe(clean_table(fin).style.format("{:,.2f}"), use_container_width=True)
                st.subheader("💵 Dòng tiền")
                st.dataframe(clean_table(cash).style.format("{:,.2f}"), use_container_width=True)
            with c_right:
                st.subheader("⚖️ Cân đối kế toán")
                st.dataframe(clean_table(bal).style.format("{:,.2f}"), use_container_width=True)

        with tab3:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("### Mô tả doanh nghiệp")
                st.write(info.get('longBusinessSummary', 'Chưa có mô tả.'))
            with c2:
                try: emp = f"{info.get('fullTimeEmployees', 0):,}" 
                except: emp = "N/A"
                st.success(f"👥 **Nhân sự:** {emp}")
                st.info(f"🏭 **Ngành:** {info.get('industry', 'N/A')}")
                st.divider()
                st.subheader("👑 Cổ đông lớn")
                if not holders.empty:
                    try:
                        if holders.shape[1] == 2: holders.columns = ['% Nắm giữ', 'Tên']
                        st.dataframe(holders, use_container_width=True)
                    except: st.dataframe(holders)
                else: st.write("Không có dữ liệu.")
    else:
        st.error(f"⚠️ Không tìm thấy mã {symbol}")

# --- FOOTER ĐÁNH DẤU CHỦ QUYỀN ---
st.markdown("""
<div class="footer">
    <p>Developed by <b>Thăng Long</b> | Data © Yahoo Finance | Powered by Streamlit</p>
</div>
""", unsafe_allow_html=True)
