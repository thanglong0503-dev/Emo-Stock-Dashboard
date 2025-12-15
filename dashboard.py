import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta  # <-- THƯ VIỆN MỚI ĐỂ TÍNH CHỈ BÁO KỸ THUẬT

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Emo Pro Dashboard V2", page_icon="🚀")

# CSS tùy chỉnh cho đẹp
st.markdown("""
<style>
    [data-testid="stMetricValue"] {font-size: 1.8rem !important;}
    h1, h2, h3 {color: #4ecdc4 !important;} # Màu xanh ngầu
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: BỘ ĐIỀU KHIỂN ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
symbol = st.sidebar.text_input("Nhập mã CP (VD: FPT)", value="FPT").upper()
period = st.sidebar.selectbox("Khung thời gian", ["6mo", "1y", "2y", "5y", "max"], index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Chỉ báo Kỹ thuật")
# Các nút bật/tắt chỉ báo
show_ma = st.sidebar.checkbox("Đường MA (20 & 50)", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=False)
show_rsi = st.sidebar.checkbox("RSI (Sức mạnh giá)", value=True)

# --- HÀM TẢI & XỬ LÝ DỮ LIỆU (NÂNG CẤP) ---
@st.cache_data(ttl=300) # Lưu bộ nhớ đệm 5 phút để load nhanh hơn
def load_data_pro(ticker_symbol, time_period):
    try:
        y_symbol = f"{ticker_symbol}.VN"
        stock = yf.Ticker(y_symbol)
        
        # 1. Lấy lịch sử giá
        df = stock.history(period=time_period)
        
        if df.empty: return pd.DataFrame(), {}, None

        # 2. Tính toán các chỉ báo kỹ thuật (Dùng pandas_ta)
        # MA (Moving Average)
        df.ta.sma(length=20, append=True) # Tạo cột SMA_20
        df.ta.sma(length=50, append=True) # Tạo cột SMA_50
        # RSI
        df.ta.rsi(length=14, append=True) # Tạo cột RSI_14
        # Bollinger Bands
        df.ta.bbands(length=20, std=2, append=True)
        
        # 3. Lấy thông tin cơ bản & Tài chính
        info = stock.info
        
        return df, info, stock # Trả về cả đối tượng stock để lấy BCTC
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame(), {}, None

# --- GIAO DIỆN CHÍNH ---
if symbol:
    # Tải dữ liệu
    hist_data, info_data, stock_obj = load_data_pro(symbol, period)
    
    if not hist_data.empty:
        # --- HEADER: THÔNG TIN TÓM TẮT ---
        st.title(f"🚀 {info_data.get('longName', symbol)}")
        
        # Tính toán thay đổi giá
        current_price = info_data.get('currentPrice', 0)
        prev_close = info_data.get('previousClose', 0)
        delta_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0

        # Hiển thị 4 chỉ số quan trọng nhất
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Giá hiện tại", f"{current_price:,} ₫", f"{delta_pct:.2f}%")
        # Định dạng số lớn (Tỷ/Triệu) cho dễ đọc
        mkt_cap = info_data.get('marketCap', 0)
        m2.metric("Vốn hóa", f"{mkt_cap/1_000_000_000:,.0f} Tỷ")
        m3.metric("P/E (Định giá)", f"{info_data.get('trailingPE', 'N/A'):.2f}")
        m4.metric("ROE (Hiệu quả)", f"{info_data.get('returnOnEquity', 0)*100:.2f}%")

        st.divider()

        # --- TẠO TAB GIAO DIỆN ---
        tab1, tab2, tab3 = st.tabs(["📊 Biểu đồ Kỹ thuật", "💰 Sức khỏe Tài chính", "🏢 Hồ sơ Công ty"])

        # === TAB 1: BIỂU ĐỒ KỸ THUẬT "NGẦU" ===
        with tab1:
            # Tạo khung biểu đồ 3 ngăn (Giá, Volume, RSI)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.02, 
                                row_heights=[0.6, 0.2, 0.2], # Ngăn trên cùng cao nhất
                                subplot_titles=("Hành động Giá", "Khối lượng", "RSI (Quá mua/Quá bán)"))

            # 1. Vẽ Nến Nhật (Candlestick) - Ngăn 1
            fig.add_trace(go.Candlestick(x=hist_data.index,
                            open=hist_data['Open'], high=hist_data['High'],
                            low=hist_data['Low'], close=hist_data['Close'], name='Nến Nhật'), row=1, col=1)

            # 2. Vẽ các đường chỉ báo (Nếu được bật bên Sidebar) - Ngăn 1
            if show_ma:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], line=dict(color='orange', width=1.5), name='MA 20 (Ngắn hạn)'), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_50'], line=dict(color='blue', width=1.5), name='MA 50 (Trung hạn)'), row=1, col=1)
            
            if show_bb:
                # Vẽ dải trên và dưới của Bollinger Bands
                bb_upper = hist_data[f'BBU_{20}_{2.0}']
                bb_lower = hist_data[f'BBL_{20}_{2.0}']
                fig.add_trace(go.Scatter(x=hist_data.index, y=bb_upper, line=dict(color='gray', width=1, dash='dot'), name='BB Upper'), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist_data.index, y=bb_lower, line=dict(color='gray', width=1, dash='dot'), name='BB Lower', fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

            # 3. Vẽ Volume (Khối lượng) - Ngăn 2
            colors = ['#ef5350' if row['Open'] - row['Close'] >= 0 else '#26a69a' for index, row in hist_data.iterrows()]
            fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

            # 4. Vẽ RSI - Ngăn 3
            if show_rsi:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['RSI_14'], line=dict(color='#9c27b0', width=2), name='RSI'), row=3, col=1)
                # Kẻ vạch báo động 30 và 70
                fig.add_hline(y=70, line_dash="dot", line_color="red", annotation_text="Quá mua (Cẩn thận)", row=3, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="green", annotation_text="Quá bán (Cơ hội)", row=3, col=1)

            # Tút tát lại giao diện biểu đồ
            fig.update_layout(height=700, xaxis_rangeslider_visible=False, template="plotly_dark", hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

        # === TAB 2: SỨC KHỎE TÀI CHÍNH ===
        with tab2:
            st.subheader("Lợi nhuận & Doanh thu (Tỷ VNĐ)")
            try:
                # Lấy báo cáo kết quả kinh doanh (Income Statement)
                financials = stock_obj.financials
                if not financials.empty:
                    # Lọc và đổi đơn vị sang Tỷ đồng cho dễ đọc
                    important_rows = ['Total Revenue', 'Gross Profit', 'Net Income']
                    df_fin_view = financials.loc[important_rows] / 1_000_000_000
                    # Đổi tên dòng sang tiếng Việt
                    df_fin_view.index = ['Tổng Doanh thu', 'Lợi nhuận gộp', 'Lợi nhuận ròng (Sau thuế)']
                    # Định dạng số hiển thị 2 số thập phân
                    st.dataframe(df_fin_view.style.format("{:,.2f} Tỷ"), use_container_width=True)
                else:
                    st.warning("Chưa có dữ liệu báo cáo tài chính từ Yahoo.")

                st.divider()
                
                st.subheader("Bảng Cân đối kế toán tóm tắt (Tỷ VNĐ)")
                balance = stock_obj.balance_sheet
                if not balance.empty:
                     # Lấy Tổng tài sản, Tổng Nợ, Vốn chủ sở hữu
                    important_balance = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity']
                    df_bal_view = balance.loc[important_balance] / 1_000_000_000
                    df_bal_view.index = ['Tổng Tài Sản', 'Tổng Nợ Phải Trả', 'Vốn Chủ Sở Hữu']
                    st.dataframe(df_bal_view.style.format("{:,.2f} Tỷ"), use_container_width=True)

            except Exception as e:
                st.error(f"Không lấy được BCTC chi tiết: {e}")

        # === TAB 3: HỒ SƠ CÔNG TY ===
        with tab3:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Mô tả doanh nghiệp")
                st.write(info_data.get('longBusinessSummary', 'Đang cập nhật...'))
            with c2:
                st.subheader("Thông tin cơ bản")
                st.info(f"**Lĩnh vực:** {info_data.get('industry', 'N/A')}")
                st.info(f"**Nhân sự:** {info_data.get('fullTimeEmployees', 'N/A'):,} người")
                st.info(f"**Website:** {info_data.get('website', 'N/A')}")

    else:
        st.error(f"⚠️ Không tìm thấy mã '{symbol}'. Vui lòng kiểm tra lại (VD: FPT, VCB...)")

else:
    st.info("👈 Nhập mã cổ phiếu bên thanh điều khiển để bắt đầu phân tích!")
