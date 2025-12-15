import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Emo Stock Dashboard V4", page_icon="🇻🇳")

# CSS: Tùy chỉnh giao diện đẹp & Font chữ
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.6rem !important; color: #4ecdc4;}
    h1, h2, h3 {color: #ff6b6b !important;}
    .stDataFrame {border: 1px solid #333; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# --- TỪ ĐIỂN VIỆT HÓA (Dịch các thuật ngữ tài chính) ---
TRANS_MAP = {
    # Kết quả kinh doanh
    'Total Revenue': 'Tổng Doanh thu',
    'Operating Revenue': 'Doanh thu Hoạt động',
    'Cost Of Revenue': 'Giá vốn hàng bán',
    'Gross Profit': 'Lợi nhuận gộp',
    'Operating Expense': 'Chi phí hoạt động',
    'Operating Income': 'Lợi nhuận từ HĐKD',
    'Net Income': 'Lợi nhuận sau thuế (Lãi ròng)',
    'EBITDA': 'EBITDA',
    'Diluted Average Shares': 'Số lượng cổ phiếu lưu hành',
    'Basic EPS': 'EPS Cơ bản',
    'Diluted EPS': 'EPS Pha loãng',
    # Cân đối kế toán
    'Total Assets': 'Tổng Tài Sản',
    'Current Assets': 'Tài sản ngắn hạn',
    'Cash And Cash Equivalents': 'Tiền & Tương đương tiền',
    'Inventory': 'Hàng tồn kho',
    'Total Liabilities Net Minority Interest': 'Tổng Nợ phải trả',
    'Current Liabilities': 'Nợ ngắn hạn',
    'Long Term Debt': 'Nợ dài hạn',
    'Stockholders Equity': 'Vốn chủ sở hữu',
    # Dòng tiền
    'Operating Cash Flow': 'Dòng tiền từ KD',
    'Investing Cash Flow': 'Dòng tiền đầu tư',
    'Financing Cash Flow': 'Dòng tiền tài chính',
    'Free Cash Flow': 'Dòng tiền tự do'
}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trung Tâm Điều Khiển")
symbol = st.sidebar.text_input("Nhập mã CP (VD: VCB)", value="VCB").upper()
period = st.sidebar.selectbox("Khung thời gian", ["6mo", "1y", "2y", "5y", "max"], index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Cấu hình Biểu đồ")
show_ma = st.sidebar.checkbox("Đường MA (20 & 50)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=False)
show_rsi = st.sidebar.checkbox("RSI (Sức mạnh giá)", value=True)

# --- HÀM TẢI DỮ LIỆU ---
@st.cache_data(ttl=300)
def load_data_v4(ticker_symbol, time_period):
    y_symbol = f"{ticker_symbol}.VN"
    stock = yf.Ticker(y_symbol)
    
    # 1. Lịch sử giá
    try:
        df = stock.history(period=time_period)
        if not df.empty:
            # Tính chỉ báo
            try:
                df.ta.sma(length=20, append=True)
                df.ta.sma(length=50, append=True)
                df.ta.rsi(length=14, append=True)
                df.ta.bbands(length=20, std=2, append=True)
            except: pass
    except: df = pd.DataFrame()

    # 2. Thông tin cơ bản
    try: info = stock.info
    except: info = {}

    # 3. Tài chính (Lấy 3 bảng chính)
    try: fin = stock.financials
    except: fin = pd.DataFrame()
    
    try: bal = stock.balance_sheet
    except: bal = pd.DataFrame()

    try: cash = stock.cashflow
    except: cash = pd.DataFrame()
    
    # 4. Cổ đông & Lãnh đạo
    try: holders = stock.major_holders
    except: holders = pd.DataFrame()
    
    return df, info, fin, bal, cash, holders

# --- HÀM XỬ LÝ BẢNG TÀI CHÍNH (Đổi ra Tỷ & Dịch tiếng Việt) ---
def process_financial_table(df):
    if df.empty: return pd.DataFrame()
    
    # 1. Dịch tên dòng (Index)
    # Chỉ lấy những dòng có trong từ điển để bảng gọn đẹp
    wanted_rows = [idx for idx in df.index if idx in TRANS_MAP]
    if not wanted_rows: 
        return df # Nếu không khớp dòng nào thì trả về bảng gốc
        
    df_clean = df.loc[wanted_rows]
    df_clean = df_clean.rename(index=TRANS_MAP)
    
    # 2. Chia cho 1 Tỷ (1.000.000.000) để số nhỏ lại
    # Lưu ý: Chỉ chia những dòng là tiền, dòng EPS hay Số lượng CP thì giữ nguyên
    for idx in df_clean.index:
        if "EPS" not in idx and "Số lượng" not in idx:
            df_clean.loc[idx] = df_clean.loc[idx] / 1_000_000_000
            
    return df_clean

# --- GIAO DIỆN CHÍNH ---
if symbol:
    hist_data, info, financials, balance, cashflow, holders = load_data_v4(symbol, period)
    
    if not hist_data.empty:
        # --- HEADER ---
        name = info.get('longName', symbol)
        st.title(f"🇻🇳 {name}")
        
        # Giá & Chỉ số
        price = info.get('currentPrice', hist_data['Close'].iloc[-1])
        prev = info.get('previousClose', hist_data['Close'].iloc[-2])
        change = ((price - prev)/prev)*100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Giá", f"{price:,.0f} ₫", f"{change:.2f}%")
        
        mk_cap_ty = info.get('marketCap', 0) / 1_000_000_000
        c2.metric("Vốn hóa", f"{mk_cap_ty:,.0f} Tỷ")
        c3.metric("P/E", f"{info.get('trailingPE', 'N/A')}")
        roe = info.get('returnOnEquity', 0)
        c4.metric("ROE", f"{roe*100:.2f}%" if roe else "N/A")

        st.divider()

        # --- TABS NỘI DUNG ---
        tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "💰 Báo cáo Tài chính (Tỷ VNĐ)", "🏢 Hồ sơ & Lãnh đạo"])

        # TAB 1: BIỂU ĐỒ
        with tab1:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.02)
            # Nến
            fig.add_trace(go.Candlestick(x=hist_data.index, open=hist_data['Open'], high=hist_data['High'], low=hist_data['Low'], close=hist_data['Close'], name='Giá'), row=1, col=1)
            # MA
            if show_ma:
                if 'SMA_20' in hist_data.columns: fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], line=dict(color='orange'), name='MA20'), row=1, col=1)
                if 'SMA_50' in hist_data.columns: fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_50'], line=dict(color='blue'), name='MA50'), row=1, col=1)
            # BB
            if show_bb and 'BBU_20_2.0' in hist_data.columns:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Upper'), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='BB Lower', fill='tonexty'), row=1, col=1)
            # Volume
            fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'], marker_color='teal', name='Vol'), row=2, col=1)
            # RSI
            if show_rsi and 'RSI_14' in hist_data.columns:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI_14'], line=dict(color='purple'), name='RSI'), row=3, col=1)
                fig.add_hline(y=70, row=3, col=1, line_dash="dot", line_color="red")
                fig.add_hline(y=30, row=3, col=1, line_dash="dot", line_color="green")
                
            fig.update_layout(height=700, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        # TAB 2: TÀI CHÍNH (Đã Việt hóa & Quy đổi)
        with tab2:
            st.caption("ℹ️ Đơn vị tính: Tỷ VNĐ (Ngoại trừ EPS và Số lượng cổ phiếu)")
            
            st.subheader("1. Kết quả kinh doanh")
            df_fin = process_financial_table(financials)
            st.dataframe(df_fin.style.format("{:,.2f}"), use_container_width=True)
            
            st.subheader("2. Cân đối kế toán")
            df_bal = process_financial_table(balance)
            st.dataframe(df_bal.style.format("{:,.2f}"), use_container_width=True)
            
            st.subheader("3. Dòng tiền")
            df_cash = process_financial_table(cashflow)
            st.dataframe(df_cash.style.format("{:,.2f}"), use_container_width=True)

        # TAB 3: HỒ SƠ & LÃNH ĐẠO
        with tab3:
            col_info, col_people = st.columns([1, 1])
            
            with col_info:
                st.subheader("Thông tin chung")
                st.info(f"**Ngành:** {info.get('industry', 'N/A')}")
                st.info(f"**Website:** {info.get('website', 'N/A')}")
                st.info(f"**Nhân sự:** {info.get('fullTimeEmployees', 'N/A'):,} người")
                st.write("**Mô tả:**")
                # Yahoo mô tả bằng tiếng Anh, ta hiển thị nguyên bản
                st.write(info.get('longBusinessSummary', 'Không có mô tả.'))
            
            with col_people:
                st.subheader("Ban Lãnh Đạo (Cán bộ chủ chốt)")
                # Lấy danh sách Officers từ Yahoo
                officers = info.get('companyOfficers', [])
                if officers:
                    for boss in officers[:5]: # Lấy 5 người đứng đầu
                        name = boss.get('name', 'N/A')
                        title = boss.get('title', 'N/A')
                        pay = boss.get('totalPay', 0)
                        # Dịch chức danh đơn giản
                        if 'CEO' in title or 'Chief Executive Officer' in title: title = "Tổng Giám Đốc (CEO)"
                        if 'Chairman' in title: title = "Chủ tịch HĐQT"
                        
                        st.success(f"👤 **{name}**")
                        st.caption(f"Chức vụ: {title}")
                else:
                    st.warning("Yahoo chưa cập nhật danh sách lãnh đạo cho mã này.")
                
                st.subheader("Cổ đông lớn")
                if not holders.empty:
                    try:
                        # Chỉ đổi tên nếu đúng là có 2 cột
                        if holders.shape[1] == 2:
                            holders.columns = ['% Nắm giữ', 'Tên Cổ đông']
                        st.dataframe(holders, use_container_width=True)
                    except:
                        # Nếu lỗi thì cứ in bảng gốc ra, không sửa tên nữa
                        st.dataframe(holders, use_container_width=True)
                else:
                    st.write("Chưa có dữ liệu cổ đông.")

    else:
        st.error(f"Không tìm thấy dữ liệu cho mã {symbol}")

