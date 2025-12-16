import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Stock V13.2", page_icon="⚡")
# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP ĐA NGƯỜI DÙNG (NEW)
# ==========================================

# 1. DANH SÁCH TÀI KHOẢN (SỔ HỘ KHẨU)
# Ngài hãy sửa/thêm người dùng tại đây. Cấu trúc: "Tên_Đăng_Nhập": "Mật_Khẩu"
USERS_DB = {
    "admin": "admin123",      # Tài khoản của Ngài
    "stock": "stock123",          # Tài khoản cho khách VIP
    "guest": "123456",        # Tài khoản khách thường
    "guest1": "123456",   # Tài khoản dự phòng
    "huydang": "123456",   # Tài khoản khách
    "kieuoanh": "123456",   # Tài khoản khách
    "uyennhi": "123456"   # Tài khoản khách
}

# 2. KHỞI TẠO TRẠNG THÁI ĐĂNG NHẬP
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

# 3. HÀM XỬ LÝ ĐĂNG NHẬP
def login():
    st.title("🔐 STOCK THANG LONG")
    st.write("Đăng nhập để tiếp tục.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        username = st.text_input("Tên đăng nhập:")
        password = st.text_input("Mật khẩu:", type="password")
        
        if st.button("🚪 Đăng Nhập", type="primary"):
            if username in USERS_DB and USERS_DB[username] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = username
                st.success("✅ Xác minh thành công! Đang mở cổng...")
                st.rerun() # Tải lại trang để vào trong
            else:
                st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")

# 4. KIỂM TRA: NẾU CHƯA ĐĂNG NHẬP -> DỪNG LẠI & HIỆN FORM LOGIN
if not st.session_state['logged_in']:
    login()
    st.stop() # Dừng toàn bộ code phía sau, không cho xem nội dung

# ==========================================
# 🚀 NỘI DUNG CHÍNH (CHỈ CHẠY KHI ĐÃ LOGIN)
# ==========================================

# --- SIDEBAR: HIỂN THỊ NGƯỜI DÙNG & LOGOUT ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
st.sidebar.info(f"👤 Xin chào: **{st.session_state['user_name']}**") # Hiện tên người đang dùng

if st.sidebar.button("👋 Đăng Xuất"):
    st.session_state['logged_in'] = False
    st.session_state['user_name'] = ""
    st.rerun()

st.sidebar.divider() # Đường kẻ phân cách
# ==========================================
# 🛡️ PHẦN BẢO MẬT & BẢO TRÌ
# ==========================================
MAINTENANCE_MODE = False 

if MAINTENANCE_MODE:
    st.title("🚧 HỆ THỐNG ĐANG BẢO TRÌ")
    st.warning("Hệ thống Thăng Long đang được nâng cấp. Vui lòng quay lại sau!")
    st.stop()

if "PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("🔒 Mật khẩu:", type="password")
    if pwd != st.secrets["PASSWORD"]:
        st.info("Vui lòng nhập mật khẩu.")
        st.stop()

# ==========================================
# 📂 KHO MÃ CỔ PHIẾU
# ==========================================
STOCK_GROUPS = {
    "🏆 VN30": "ACB,BCM,BID,BVH,CTG,FPT,GAS,GVR,HDB,HPG,MBB,MSN,MWG,PLX,POW,SAB,SHB,SSB,SSI,STB,TCB,TPB,VCB,VHM,VIB,VIC,VJC,VNM,VPB,VRE",
    "🏦 Ngân Hàng": "VCB,BID,CTG,TCB,VPB,MBB,ACB,STB,HDB,VIB,TPB,SHB,EIB,MSB,OCB,LPB,SSB",
    "📈 Chứng Khoán": "SSI,VND,VCI,HCM,SHS,MBS,FTS,BSI,CTS,VIX,AGR,ORS",
    "🏗️ Thép": "HPG,HSG,NKG,VSG,TLH,POM",
    "🏠 BĐS": "VHM,VIC,VRE,NVL,PDR,DIG,CEO,DXG,KDH,NLG,KBC,IDC,SZC",
    "🛢️ Dầu Khí": "GAS,PLX,PVD,PVS,PVC,BSR,OIL,PVT",
    "🐟 Thủy Sản": "VHC,ANV,IDI,CMX,FMC",
    "🛒 Bán Lẻ": "MWG,PNJ,DGW,FRT,PET,MSN",
    "⚡ Điện": "POW,REE,NT2,PC1,GEG,HDG,GEX"
}

# ==========================================
# 🎨 GIAO DIỆN PRO
# ==========================================
st.markdown("""
<style>
    h1, h2, h3 {color: #64b5f6 !important;}
    [data-testid="stMetricValue"] {font-size: 1.4rem !important; font-weight: bold !important;}
    [data-testid="stMetricLabel"] {font-size: 1rem !important; opacity: 0.8;}
    .rec-card {background-color: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 20px;}
    .rec-card h3 {color: white !important;} 
    .score-circle {display: inline-block; width: 60px; height: 60px; line-height: 60px; border-radius: 50%; font-size: 24px; font-weight: bold; color: white; margin-bottom: 10px;}
    .green-zone {background-color: #10b981; box-shadow: 0 0 15px #10b981;}
    .red-zone {background-color: #ef4444; box-shadow: 0 0 15px #ef4444;}
    .yellow-zone {background-color: #f59e0b; box-shadow: 0 0 15px #f59e0b;}
    .news-item {padding: 10px; border-bottom: 1px solid #444; margin-bottom: 10px;}
    .news-item:hover {background-color: rgba(100, 181, 246, 0.1); border-radius: 5px;}
    .news-title {font-weight: bold; font-size: 16px; text-decoration: none; display: block; margin-bottom: 5px; color: inherit !important;}
    .news-meta {font-size: 12px; color: #888;}
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #111827; color: #6b7280; text-align: center; font-size: 12px; padding: 5px; border-top: 1px solid #374151; z-index: 100;}
</style>
""", unsafe_allow_html=True)

TRANS_MAP = {
    'Total Revenue': '1. Tổng Doanh Thu', 'Operating Revenue': '   - Doanh thu HĐ',
    'Cost Of Revenue': '2. Giá Vốn Hàng Bán', 'Gross Profit': '3. Lợi Nhuận Gộp',
    'Operating Expense': '4. Chi Phí Hoạt Động', 'Operating Income': '5. Lợi Nhuận Từ HĐKD',
    'Net Income': '9. Lợi Nhuận Sau Thuế', 'EBITDA': '10. EBITDA', 'Basic EPS': '11. EPS Cơ Bản',
    'Total Assets': 'A. TỔNG TÀI SẢN', 'Current Assets': '   I. Tài sản Ngắn hạn',
    'Cash And Cash Equivalents': '      1. Tiền & Tương đương tiền', 'Inventory': '      2. Hàng Tồn kho',
    'Total Liabilities Net Minority Interest': 'B. TỔNG NỢ', 'Stockholders Equity': 'C. VỐN CHỦ SỞ HỮU',
    'Operating Cash Flow': '1. Dòng Tiền KD', 'Investing Cash Flow': '2. Dòng Tiền Đầu Tư',
    'Financing Cash Flow': '3. Dòng Tiền Tài Chính', 'Free Cash Flow': '-> Dòng Tiền Tự Do'
}

# --- SIDEBAR ---
st.sidebar.title("🎛️ SETTING")
st.sidebar.success("👑 **Developed: THANG LONG**")
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét"])

# --- NÚT CLEAR CACHE (NEW V13.2) ---
if st.sidebar.button("🔄 Xóa Cache & Cập Nhật"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# 🧠 XỬ LÝ DỮ LIỆU
# ==========================================

@st.cache_data(ttl=300) # Mặc định lưu 5 phút, bấm nút Refresh sẽ xóa cái này
def load_news_google(symbol):
    try:
        rss_url = f"https://news.google.com/rss/search?q=cổ+phiếu+{symbol}&hl=vi&gl=VN&ceid=VN:vi"
        feed = feedparser.parse(rss_url)
        clean_news = []
        for entry in feed.entries[:10]:
            clean_news.append({'title': entry.title, 'link': entry.link, 'published': entry.get('published', ''), 'source': entry.get('source', {}).get('title', 'Google News')})
        return clean_news
    except: return []

@st.cache_data(ttl=300)
def load_data_v13(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    try:
        df_calc = stock.history(period="2y") # Lấy 2 năm cho đủ dữ liệu
        if len(df_calc) > 100:
            # 1. SuperTrend (Quan trọng nhất)
            sti = ta.supertrend(df_calc['High'], df_calc['Low'], df_calc['Close'], length=10, multiplier=3)
            df_calc = df_calc.join(sti) 
            
            # 2. Các chỉ báo cao cấp khác
            df_calc.ta.mfi(length=14, append=True) # Dòng tiền
            df_calc.ta.stochrsi(length=14, append=True) # Điểm nổ
            df_calc.ta.ema(length=34, append=True) # Sóng ngắn
            df_calc.ta.ema(length=89, append=True) # Sóng dài
            df_calc.ta.adx(length=14, append=True)
            df_calc.ta.atr(length=14, append=True)
            
            # Giữ lại MA cơ bản để vẽ biểu đồ nếu cần
            df_calc.ta.sma(length=20, append=True)
            df_calc.ta.sma(length=50, append=True)
    except: df_calc = pd.DataFrame()

    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True)
            df_chart.ta.bbands(length=20, std=2, append=True)
            df_chart.ta.rsi(length=14, append=True)
            df_chart.ta.macd(append=True)
    except: df_chart = pd.DataFrame()

    try: info = stock.info; 
    except: info = {}
    try: fin = stock.financials; 
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet; 
    except: bal = pd.DataFrame()
    try: cash = stock.cashflow; 
    except: cash = pd.DataFrame()
    try: holders = stock.major_holders; 
    except: holders = pd.DataFrame()
    
    news_items = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, cash, holders, news_items

def analyze_smart(df):
    if df.empty or len(df) < 100: return None
    now = df.iloc[-1]
    
    # Lấy dữ liệu
    close = now['Close']
    # Tìm cột SuperTrend (tên cột này hay thay đổi nên phải tìm động)
    st_col = [c for c in df.columns if 'SUPERT' in c][0] 
    supertrend = now[st_col]
    
    mfi = now.get('MFI_14', 50)
    k = now.get('STOCHRSIk_14_14_3_3', 50) # StochRSI K
    d = now.get('STOCHRSId_14_14_3_3', 50) # StochRSI D
    adx = now.get('ADX_14', 0)
    ema34 = now.get('EMA_34', 0)
    ema89 = now.get('EMA_89', 0)
    atr = now.get('ATRr_14', 0)

    score = 0
    pros = []
    cons = []
def analyze_fundamental(info):
    if not info: return None
    
    score = 0
    details = []
    
    # 1. Định giá P/E (Rẻ hay Đắt?)
    pe = info.get('trailingPE', 0)
    # P/E trung bình VN khoảng 13-15. Dưới 12 là rẻ, trên 20 là đắt (tương đối)
    if 0 < pe < 12: 
        score += 2; details.append(f"P/E Hấp dẫn ({pe:.1f}x)")
    elif 12 <= pe <= 20: 
        score += 1; details.append(f"P/E Hợp lý ({pe:.1f}x)")
    else: 
        details.append(f"P/E Khá cao ({pe:.1f}x)")
        
    # 2. Hiệu quả sinh lời ROE (Lãnh đạo làm ăn thế nào?)
    roe = info.get('returnOnEquity', 0)
    if roe > 0.20: # Trên 20% là xuất sắc
        score += 2; details.append(f"ROE Xuất sắc ({roe:.1%})")
    elif roe > 0.12: # Trên 12% là ổn
        score += 1; details.append(f"ROE Ổn định ({roe:.1%})")
        
    # 3. Tăng trưởng doanh thu (Công ty có lớn lên không?)
    rev_growth = info.get('revenueGrowth', 0)
    if rev_growth > 0.15: 
        score += 2; details.append(f"Tăng trưởng mạnh ({rev_growth:.1%})")
    elif rev_growth > 0:
        score += 1
        
    # 4. Sức khỏe tài chính (Nợ/Vốn chủ)
    debt = info.get('debtToEquity', 0)
    if debt < 50: # Nợ ít
        score += 2; details.append("Cấu trúc vốn An toàn (Nợ thấp)")
    elif debt > 150:
        details.append("⚠️ Cảnh báo: Nợ vay cao")

    # 5. Định giá Benjamin Graham (Giá trị thực ước tính)
    # Công thức: Căn bậc 2 của (22.5 * EPS * BVPS)
    try:
        eps = info.get('trailingEps', 0)
        bvps = info.get('bookValue', 0)
        if eps > 0 and bvps > 0:
            graham_price = (22.5 * eps * bvps) ** 0.5
            details.append(f"💎 Giá trị thực (Graham): {graham_price:,.0f}")
    except: pass

    # Xếp hạng Cơ bản
    health = "YẾU KÉM"
    color = "red"
    if score >= 7: health, color = "KIM CƯƠNG 💎", "green"
    elif score >= 4: health, color = "VỮNG MẠNH 💪", "blue"
    elif score >= 2: health, color = "TRUNG BÌNH 😐", "orange"
    
    return {"health": health, "color": color, "details": details, "score": score}
    # --- Gọi hàm phân tích cơ bản ---
    fund = analyze_fundamental(info)
            
            # --- GIAO DIỆN WOW ---
            # Chia màn hình thành 2 cột: Trái (Kỹ thuật - Cũ), Phải (Cơ bản - Mới)
            col_tech, col_fund = st.columns(2)
            
            with col_tech:
                # (Đây là code hiển thị Kỹ thuật cũ của Ngài, giữ nguyên)
                st.markdown(f"""
                <div class="rec-card" style="border-left: 5px solid {strat['zone'].split('-')[0]};">
                    <h4>🔭 GÓC NHÌN KỸ THUẬT</h4>
                    <div class="score-circle {strat['zone']}">{strat['score']}</div>
                    <h2 style="margin:0">{strat['action']}</h2>
                    <p style="color:gray; font-size:12px">Định thời điểm Mua/Bán</p>
                </div>
                """, unsafe_allow_html=True)
                # Hiển thị chi tiết kỹ thuật...
                st.info(f"🎯 Mục tiêu: {strat['target']:,.0f} | 🛑 Cắt lỗ: {strat['stop']:,.0f}")

            with col_fund:
                # (Đây là phần CƠ BẢN MỚI - Cực Wow)
                if fund:
                    st.markdown(f"""
                    <div class="rec-card" style="border-left: 5px solid {fund['color']};">
                        <h4>🏢 SỨC KHỎE DOANH NGHIỆP</h4>
                        <div style="font-size: 40px; margin: 10px 0;">{fund['health']}</div>
                        <p style="color:gray; font-size:12px">Chất lượng Doanh nghiệp</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Hiển thị các tiêu chí cơ bản dưới dạng Progress Bar hoặc List đẹp
                    st.write("🔍 **Soi Cơ Bản:**")
                    for d in fund['details']:
                        if "Cảnh báo" in d: st.error(d)
                        elif "Giá trị thực" in d: st.info(d)
                        else: st.success(f"✅ {d}")
                else:
                    st.warning("Thiếu dữ liệu cơ bản từ nguồn.")
    # --- LOGIC CAO CẤP V14 ---
    
    # 1. SuperTrend (Vua xu hướng) - Chiếm trọng số cao nhất
    if close > supertrend:
        score += 3; pros.append("SuperTrend: BÁO TĂNG (Bullish)")
    else:
        score -= 2; cons.append("SuperTrend: BÁO GIẢM (Bearish)")

    # 2. Hệ thống EMA (Sonic R)
    if ema34 > ema89 and close > ema34:
        score += 1; pros.append("EMA System: Xu hướng dài hạn Tốt")
    elif close < ema89:
        score -= 1; cons.append("EMA System: Gãy xu hướng dài hạn")

    # 3. Dòng tiền thông minh (MFI) - Thay cho RSI thường
    if mfi > 80:
        score -= 1; cons.append(f"MFI ({mfi:.0f}): Tiền vào quá nóng")
    elif mfi < 20:
        score += 2; pros.append(f"MFI ({mfi:.0f}): Vùng gom hàng (Quá bán)")
    elif mfi > 50 and mfi > df.iloc[-2]['MFI_14']:
        score += 1; pros.append("MFI: Dòng tiền đang vào dần")

    # 4. StochRSI (Điểm nổ ngắn hạn)
    if k < 20 and k > d: # Cắt lên ở vùng đáy
        score += 2; pros.append("StochRSI: Tín hiệu Đảo chiều Tăng")
    
    # 5. ADX (Độ mạnh xu hướng)
    if adx > 25:
        if close > supertrend: pros.append(f"ADX ({adx:.0f}): Trend Tăng khỏe")
        
    # --- TỔNG KẾT ---
    # Cộng thêm 4 điểm cơ bản để thang điểm rơi vào 0-10
    final_score = max(0, min(10, 4 + score)) 
    
    action, zone = "QUAN SÁT", "yellow-zone"
    if final_score >= 8: action, zone = "MUA MẠNH", "green-zone"
    elif final_score >= 6: action, zone = "MUA THĂM DÒ", "green-zone"
    elif final_score <= 3: action, zone = "BÁN / CẮT LỖ", "red-zone"
    
    # Stoploss thông minh theo SuperTrend và ATR
    stop_loss = close - 2*atr if close > supertrend else close + 2*atr
    take_profit = close + 3*atr if close > supertrend else close - 3*atr

    return {
        "score": final_score, "action": action, "zone": zone, 
        "pros": pros, "cons": cons, 
        "entry": close, "stop": stop_loss, "target": take_profit
    }

def clean_table(df):
    if df.empty: return pd.DataFrame()
    valid = [i for i in df.index if i in TRANS_MAP]
    if not valid: return df
    df_new = df.loc[valid].rename(index=TRANS_MAP)
    for col in df_new.columns:
        for idx in df_new.index:
            if "EPS" not in idx and isinstance(df_new.loc[idx, col], (int, float)): df_new.loc[idx, col] = df_new.loc[idx, col] / 1e9
    return df_new

def safe_fmt(val):
    try: return f"{int(val):,}"
    except: return "N/A"

def render_pro_chart(df, symbol):
    row_h = [0.6, 0.2, 0.2]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'), row=1, col=1)
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
    if 'SMA_50' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='#2979ff', width=1), name='MA50'), row=1, col=1)
    if 'BBU_20_2.0' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], line=dict(color='gray', dash='dot'), name='Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], line=dict(color='gray', dash='dot'), name='Lower', fill='tonexty'), row=1, col=1)
    colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    if 'MACD_12_26_9' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='#22d3ee', width=1.5), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], line=dict(color='#f472b6', width=1.5), name='Signal'), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], marker_color='#64748b', name='Hist'), row=3, col=1)
    fig.update_layout(height=700, template="plotly_dark", hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=True, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})

# ==========================================
# 🖥️ GIAO DIỆN CHÍNH
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    st.header("🔮 Phân Tích Chuyên Sâu")
    col_input, col_ref = st.columns([3, 1])
    with col_input:
        symbol = st.text_input("Nhập Mã CP", value="HPG").upper()
    with col_ref:
        if st.button("🔄 Cập nhật giá"): st.cache_data.clear(); st.rerun()

    period = st.selectbox("Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)
    
    if symbol:
        df_calc, df_chart, info, fin, bal, cash, holders, news = load_data_v13(symbol, period)
        if not df_chart.empty:
            st.title(f"💎 {info.get('longName', symbol)}")
            strat = analyze_smart(df_calc)
            if strat:
                c1, c2 = st.columns([1, 2])
                with c1: st.markdown(f'<div class="rec-card"><div class="score-circle {strat["zone"]}">{strat["score"]}</div><h3>{strat["action"]}</h3></div>', unsafe_allow_html=True)
                with c2:
                    k1, k2 = st.columns(2)
                    with k1: 
                        for p in strat['pros']: st.success(f"+ {p}")
                    with k2: 
                        for c in strat['cons']: st.error(f"- {c}")
                    st.divider()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Giá Hiện Tại", f"{strat['entry']:,.0f}")
                    m2.metric("Cắt Lỗ (Gợi ý)", f"{strat['stop']:,.0f}")
                    m3.metric("Mục Tiêu (Gợi ý)", f"{strat['target']:,.0f}")

            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ Kỹ Thuật", "📰 Tin Tức", "💰 Tài Chính", "🏢 Hồ Sơ"])
            with t1: render_pro_chart(df_chart, symbol)
            with t2:
                for item in news: st.markdown(f'<div class="news-item"><a href="{item["link"]}" target="_blank" class="news-title">{item["title"]}</a><div class="news-meta">🕒 {item["published"][:16]} | 🔗 {item["source"]}</div></div>', unsafe_allow_html=True)
            with t3:
                c_left, c_right = st.columns(2)
                with c_left: st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin).style.format("{:,.2f}"), use_container_width=True); st.subheader("Dòng Tiền"); st.dataframe(clean_table(cash).style.format("{:,.2f}"), use_container_width=True)
                with c_right: st.subheader("Cân Đối Kế Toán"); st.dataframe(clean_table(bal).style.format("{:,.2f}"), use_container_width=True)
            with t4:
                c1, c2 = st.columns([2, 1])
                with c1: st.write(info.get('longBusinessSummary', ''))
                with c2:
                    st.info(f"Ngành: {info.get('industry', 'N/A')}")
                    st.success(f"Nhân sự: {safe_fmt(info.get('fullTimeEmployees', 'N/A'))}")
                    try: st.dataframe(holders, use_container_width=True)
                    except: pass

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Bảng Giá & Máy Quét Đa Năng")
    if st.button("🔄 Cập nhật dữ liệu toàn thị trường"): st.cache_data.clear(); st.rerun()
    
    all_tabs = ["🛠️ Tự Nhập (Manual)"] + list(STOCK_GROUPS.keys())
    tabs = st.tabs(all_tabs)
    
    with tabs[0]:
        st.caption("Nhập danh sách mã cổ phiếu bất kỳ để quét (cách nhau dấu phẩy).")
        inp = st.text_area("Danh sách mã:", value="HPG, VCB, SSI, VND, FPT, MWG, DIG", height=100)
        if st.button("🚀 QUÉT DANH SÁCH TỰ NHẬP"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            if len(ticks) > 30: ticks = ticks[:30]; st.warning("⚠️ Chỉ quét 30 mã đầu tiên.")
            res = []
            bar = st.progress(0, "Đang xử lý...")
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                try:
                    df, _, _, _, _, _, _, _ = load_data_v13(t, "1y")
                    s = analyze_smart(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": f"{s['entry']:,.0f}"})
                except: pass
            bar.empty()
            if res:
                df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                def color_act(val):
                    if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                    if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                    return 'color: #f59e0b'
                st.dataframe(df_res.style.map(color_act, subset=['Hành động']), use_container_width=True)
            else: st.error("Không tìm thấy dữ liệu.")

    for tab, name in zip(tabs[1:], list(STOCK_GROUPS.keys())):
        with tab:
            if st.button(f"🚀 Quét Nhóm {name}", key=name):
                ticks = STOCK_GROUPS[name].split(',')
                res = []
                bar = st.progress(0, f"Đang quét {name}...")
                for i, t in enumerate(ticks):
                    bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                    try:
                        df, _, _, _, _, _, _, _ = load_data_v13(t, "1y")
                        s = analyze_smart(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": f"{s['entry']:,.0f}"})
                    except: pass
                bar.empty()
                if res:
                    df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                    def color_act(val):
                        if 'MUA' in val: return 'color: #10b981; font-weight: bold'
                        if 'BÁN' in val: return 'color: #ef4444; font-weight: bold'
                        return 'color: #f59e0b'
                    st.dataframe(df_res.style.map(color_act, subset=['Hành động']), use_container_width=True)
                    if df_res.iloc[0]['Điểm'] >= 7: st.success(f"💎 NGÔI SAO DÒNG {name}: **{df_res.iloc[0]['Mã']}** ({df_res.iloc[0]['Điểm']} điểm)")

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V13.2 - Realtime</div>', unsafe_allow_html=True)











