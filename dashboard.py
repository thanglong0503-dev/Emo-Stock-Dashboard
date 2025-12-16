import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import feedparser
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Thăng Long Royal V15.2", page_icon="🐲")

# ==========================================
# 🎨 GIAO DIỆN HOÀNG GIA (ROYAL UI - V15.2)
# ==========================================
st.markdown("""
<style>
    :root { --primary-color: #3498db; }
    h1, h2, h3 { color: var(--text-color) !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    h1 { margin-bottom: 20px !important; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 800 !important; color: var(--primary-color) !important; }
    
    .modern-card {
        background-color: var(--secondary-background-color);
        border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); 
        border: 1px solid rgba(128, 128, 128, 0.2); margin-bottom: 20px;
    }
    .card-header { font-size: 1.2rem; font-weight: 700; margin-bottom: 15px; color: var(--text-color); display: flex; align-items: center; }
    .card-header i { margin-right: 10px; }
    
    .news-item-pro { padding: 12px; border-bottom: 1px solid rgba(128, 128, 128, 0.1); }
    .news-item-pro:hover { background-color: rgba(128, 128, 128, 0.05); border-radius: 8px; }
    .news-title-pro { font-weight: 600; font-size: 15px; text-decoration: none; display: block; margin-bottom: 6px; color: var(--text-color) !important; }
    .news-meta-pro { font-size: 11px; color: gray; }
    
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background: var(--secondary-background-color); color: gray; text-align: center; font-size: 12px; padding: 8px; border-top: 1px solid rgba(128,128,128,0.1); z-index: 100; }
</style>
""", unsafe_allow_html=True)

def create_modern_card(title, content_html, icon=""):
    icon_html = f'<i style="color: #3498db">{icon}</i>' if icon else ""
    st.markdown(f"""<div class="modern-card"><div class="card-header">{icon_html}{title}</div><div>{content_html}</div></div>""", unsafe_allow_html=True)

# ==========================================
# 🛡️ PHẦN BẢO MẬT & BẢO TRÌ
# ==========================================
MAINTENANCE_MODE = False 
if MAINTENANCE_MODE: st.title("🚧 HỆ THỐNG ĐANG BẢO TRÌ"); st.stop()
if "PASSWORD" in st.secrets:
    pwd = st.sidebar.text_input("🔒 Mật khẩu:", type="password")
    if pwd != st.secrets["PASSWORD"]: st.info("Vui lòng nhập mật khẩu."); st.stop()

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
    "🛒 Bán Lẻ": "MWG,PNJ,DGW,FRT,PET,MSN"
}

TRANS_MAP = {'Total Revenue': 'Tổng Doanh Thu', 'Net Income': 'LN Sau Thuế', 'Total Assets': 'Tổng Tài Sản', 'Total Liabilities Net Minority Interest': 'Tổng Nợ', 'Stockholders Equity': 'Vốn Chủ Sở Hữu'}

# --- SIDEBAR ---
st.sidebar.title("🎛️ Trạm Điều Khiển")
mode = st.sidebar.radio("Chế độ:", ["🔮 Phân Tích Chuyên Sâu", "📊 Bảng Giá & Máy Quét"])
if st.sidebar.button("🔄 Fix Lỗi & Cập Nhật"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# 🧠 XỬ LÝ DỮ LIỆU & PHÂN TÍCH
# ==========================================
@st.cache_data(ttl=300)
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
def load_data_full(ticker, time):
    t = f"{ticker}.VN"
    stock = yf.Ticker(t)
    try:
        df_calc = stock.history(period="1y")
        if len(df_calc) > 52:
            df_calc.ta.sma(length=20, append=True); df_calc.ta.sma(length=50, append=True)
            df_calc.ta.rsi(length=14, append=True); df_calc.ta.macd(append=True)
            df_calc.ta.adx(length=14, append=True); df_calc.ta.atr(length=14, append=True)
    except: df_calc = pd.DataFrame()

    try:
        interval = "15m" if time in ["1d", "5d"] else "1d"
        df_chart = stock.history(period=time, interval=interval)
        if not df_chart.empty:
            df_chart.ta.sma(length=20, append=True); df_chart.ta.bbands(length=20, std=2, append=True)
            df_chart.ta.rsi(length=14, append=True); df_chart.ta.macd(append=True)
    except: df_chart = pd.DataFrame()

    try: info = stock.info; 
    except: info = {}
    try: fin = stock.financials; 
    except: fin = pd.DataFrame()
    try: bal = stock.balance_sheet; 
    except: bal = pd.DataFrame()
    try: holders = stock.major_holders; 
    except: holders = pd.DataFrame()
    
    news_items = load_news_google(ticker)
    return df_calc, df_chart, info, fin, bal, holders, news_items

def analyze_smart(df):
    if df.empty or len(df) < 52: return None
    now = df.iloc[-1]
    close = now['Close']; ma20 = now['SMA_20']; ma50 = now['SMA_50']
    rsi = now['RSI_14']; macd = now['MACD_12_26_9']; macds = now['MACDs_12_26_9']
    adx = now['ADX_14']; atr = now['ATRr_14']
    
    # --- FIX LỖI VALUE ERROR TẠI ĐÂY ---
    score = 5
    pros = []
    cons = []
    # -----------------------------------

    if close > ma20 and close > ma50: score += 2; pros.append("Uptrend (Giá > MA20,50)")
    else: score -=1
    if adx > 25: score += 1; pros.append(f"Trend Mạnh (ADX>25)")
    if rsi < 30: score += 2; pros.append("RSI Quá bán (Hồi phục)")
    elif rsi > 70: score -= 1; cons.append("RSI Quá mua (Cẩn thận)")
    if macd > macds: score += 1; pros.append("MACD cắt lên")
    else: score -= 1; cons.append("MACD cắt xuống")
    
    final_score = max(0, min(10, score))
    action = "QUAN SÁT"
    if final_score >= 8: action = "MUA MẠNH"
    elif final_score >= 6: action = "MUA THĂM DÒ"
    elif final_score <= 3: action = "BÁN / CẮT LỖ"
    
    return {"score": final_score, "action": action, "pros": pros, "cons": cons, "entry": close, "stop": close - 2*atr, "target": close + 3*atr}

def analyze_fundamental_score(info):
    scores = {'Định Giá': 5, 'Sinh Lời': 5, 'Tăng Trưởng': 5, 'Sức Khỏe': 5, 'Hiệu Quả': 5}
    try:
        pe = info.get('trailingPE', 0); pe = 0 if pe is None else pe
        if 0 < pe < 15: scores['Định Giá'] = 8
        elif pe >= 25: scores['Định Giá'] = 3
        
        roe = info.get('returnOnEquity', 0); roe = 0 if roe is None else roe
        if roe > 0.15: scores['Sinh Lời'] = 8
        elif roe < 0.05: scores['Sinh Lời'] = 3
        
        rev_g = info.get('revenueGrowth', 0); rev_g = 0 if rev_g is None else rev_g
        if rev_g > 0.1: scores['Tăng Trưởng'] = 8
        elif rev_g < 0: scores['Tăng Trưởng'] = 3
    except: pass
    return scores

def safe_fmt(val):
    try: return f"{int(val):,}"
    except: return "N/A"

# --- VẼ CHART HTML (FIX LỖI TYPE ERROR) ---
def plot_gauge(score, action):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        title = {'text': f"KỸ THUẬT: {action}", 'font': {'size': 18}},
        gauge = {
            'axis': {'range': [None, 10], 'tickwidth': 1},
            'bar': {'color': "#3498db"}, 'bgcolor': "rgba(128,128,128,0.2)",
            'steps': [{'range': [0, 3], 'color': '#ef4444'}, {'range': [3, 7], 'color': '#f59e0b'}, {'range': [7, 10], 'color': '#10b981'}],
            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': score}}))
    fig.update_layout(height=250, margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)') 
    return fig

def plot_radar(scores):
    categories = list(scores.keys()); values = list(scores.values())
    categories = [*categories, categories[0]]; values = [*values, values[0]]
    fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', name='Điểm cơ bản', line_color='#3498db'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10], color='gray')), showlegend=False, height=250, margin=dict(l=40,r=40,t=30,b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_holders(df_holders):
    if df_holders.empty: return None
    try:
        labels = df_holders[1].tolist(); values = []
        for v in df_holders[0].tolist():
            try: values.append(float(v.strip('%')))
            except: values.append(0)
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0), paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        return fig
    except: return None

def render_pro_chart(df, symbol):
    row_h = [0.6, 0.2, 0.2]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Giá'), row=1, col=1)
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#fb8c00', width=1), name='MA20'), row=1, col=1)
    if 'BBU_20_2.0' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], line=dict(color='rgba(128,128,128,0.5)', dash='dot'), name='Upper'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], line=dict(color='rgba(128,128,128,0.5)', dash='dot'), name='Lower', fill='tonexty'), row=1, col=1)
    colors = ['#ef4444' if r['Open'] > r['Close'] else '#10b981' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    if 'MACD_12_26_9' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='#22d3ee', width=1.5), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], line=dict(color='#f472b6', width=1.5), name='Signal'), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], marker_color='#64748b', name='Hist'), row=3, col=1)
    fig.update_layout(height=700, template=None, hovermode="x unified", dragmode="pan", margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=True, xaxis=dict(showgrid=False, color='gray'), yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', color='gray'))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.05))
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})

# ==========================================
# 🖥️ GIAO DIỆN CHÍNH
# ==========================================
if mode == "🔮 Phân Tích Chuyên Sâu":
    c1, c2 = st.columns([3, 1])
    with c1: symbol = st.text_input("🔍 Nhập Mã Cổ Phiếu (VD: HPG)", value="HPG").upper()
    with c2: 
        st.write("") 
        if st.button("🔄 Cập nhật"): st.cache_data.clear(); st.rerun()
    
    period = st.selectbox("⏱️ Khung thời gian", ["1d", "5d", "1mo", "6mo", "1y", "5y"], index=4)

    if symbol:
        df_calc, df_chart, info, fin, bal, holders, news = load_data_full(symbol, period)
        if not df_chart.empty:
            st.title(f"{info.get('longName', symbol)}")
            
            tech_res = analyze_smart(df_calc)
            fund_scores = analyze_fundamental_score(info)
            
            if tech_res:
                g1, g2 = st.columns(2)
                with g1:
                    # FIX LỖI TYPE ERROR: Chuyển chart sang HTML trước khi cộng chuỗi
                    gauge_html = plot_gauge(tech_res['score'], tech_res['action']).to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})
                    metrics_html = f"""<div style="display: flex; justify-content: space-around; margin-top: 15px; font-weight: 600;"><div>🎯 Giá: {tech_res['entry']:,.0f}</div><div>🛑 Cắt: {tech_res['stop']:,.0f}</div><div>🚀 Tiêu: {tech_res['target']:,.0f}</div></div>"""
                    create_modern_card("Sức Mạnh Kỹ Thuật", gauge_html + metrics_html, icon="🔭")

                with g2:
                    radar_html = plot_radar(fund_scores).to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})
                    fund_metrics_html = f"""<div style="text-align: center; margin-top: 15px; color: gray; font-size: 0.9rem;">P/E: {info.get('trailingPE','N/A')} | EPS: {info.get('trailingEps','N/A')}</div>"""
                    create_modern_card("Sức Khỏe Doanh Nghiệp", radar_html + fund_metrics_html, icon="🏢")

                with st.expander("Xem chi tiết lý do khuyến nghị"):
                    k1, k2 = st.columns(2)
                    with k1: 
                        st.subheader("✅ Điểm Cộng")
                        # FIX LỖI LOOP ATTRIBUTE: Kiểm tra list trước
                        if tech_res['pros']:
                            for p in tech_res['pros']: st.success(p)
                        else: st.write("Không có")
                    with k2: 
                        st.subheader("❌ Điểm Trừ")
                        if tech_res['cons']:
                            for c in tech_res['cons']: st.error(c)
                        else: st.write("Không có")

            t1, t2, t3, t4 = st.tabs(["📊 Biểu Đồ", "📰 Tin Tức", "💰 Tài Chính", "👥 Cổ Đông"])
            with t1: render_pro_chart(df_chart, symbol)
            with t2:
                for item in news: st.markdown(f'<div class="news-item-pro"><a href="{item["link"]}" target="_blank" class="news-title-pro">{item["title"]}</a><div class="news-meta-pro">🕒 {item["published"][:16]} | 🔗 {item["source"]}</div></div>', unsafe_allow_html=True)
            with t3:
                c_left, c_right = st.columns(2)
                # Sử dụng hàm clean_table để hiển thị tên tiếng Việt
                def clean_table(df):
                    if df.empty: return pd.DataFrame()
                    valid = [i for i in df.index if i in TRANS_MAP]
                    if not valid: return df
                    df_new = df.loc[valid].rename(index=TRANS_MAP)
                    return df_new
                
                with c_left: st.subheader("Kinh Doanh"); st.dataframe(clean_table(fin), use_container_width=True)
                with c_right: st.subheader("Cân Đối KT"); st.dataframe(clean_table(bal), use_container_width=True)
            with t4:
                c1, c2 = st.columns([2, 1])
                with c1: 
                    st.subheader("Giới thiệu"); st.write(info.get('longBusinessSummary', 'Chưa có mô tả.'))
                    st.subheader("Cơ Cấu Cổ Đông")
                    pie_fig = plot_holders(holders)
                    if pie_fig: st.plotly_chart(pie_fig, use_container_width=True)
                    else: st.dataframe(holders, use_container_width=True)
                with c2:
                    create_modern_card("Thông Tin Khác", f"""<div><b>Ngành:</b> {info.get('industry', 'N/A')}</div><div style="margin-top: 10px;"><b>Nhân sự:</b> {safe_fmt(info.get('fullTimeEmployees', 'N/A'))} người</div>""", icon="ℹ️")

elif mode == "📊 Bảng Giá & Máy Quét":
    st.title("📊 Bảng Giá & Máy Quét")
    if st.button("🔄 Cập nhật dữ liệu"): st.cache_data.clear(); st.rerun()
    
    all_tabs = ["🛠️ Tự Nhập"] + list(STOCK_GROUPS.keys())
    tabs = st.tabs(all_tabs)
    
    def style_dataframe(df):
        def color_act(val):
            if 'MUA MẠNH' in val: return 'color: #10b981; font-weight: 800;'
            if 'MUA THĂM DÒ' in val: return 'color: #10b981; font-weight: 600;'
            if 'BÁN' in val: return 'color: #ef4444; font-weight: 700;'
            return 'color: #f59e0b; font-weight: 500;'
        return df.style.map(color_act, subset=['Hành động']).format({"Giá TT": "{:,.0f}"})

    with tabs[0]:
        st.info("Nhập danh sách mã cần quét (cách nhau dấu phẩy).")
        inp = st.text_area("Danh sách mã:", value="HPG, VCB, SSI, VND, FPT, MWG", height=80)
        if st.button("🚀 KÍCH HOẠT RADAR"):
            ticks = [x.strip().upper() for x in inp.split(',') if x.strip()]
            if len(ticks) > 30: ticks = ticks[:30]; st.warning("⚠️ Chỉ quét 30 mã đầu.")
            res = []
            bar = st.progress(0, "Đang khởi động...")
            for i, t in enumerate(ticks):
                bar.progress((i+1)/len(ticks), f"Đang phân tích: {t}...")
                try:
                    df, _, _, _, _, _, _ = load_data_full(t, "1y")
                    s = analyze_smart(df)
                    if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": s['entry']})
                except: pass
            bar.empty()
            if res:
                df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                st.dataframe(style_dataframe(df_res), use_container_width=True)
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
                        df, _, _, _, _, _, _ = load_data_full(t, "1y")
                        s = analyze_smart(df)
                        if s: res.append({"Mã": t, "Điểm": s['score'], "Hành động": s['action'], "Giá TT": s['entry']})
                    except: pass
                bar.empty()
                if res:
                    df_res = pd.DataFrame(res).sort_values(by="Điểm", ascending=False)
                    st.dataframe(style_dataframe(df_res), use_container_width=True)

st.markdown('<div class="footer">Developed by <b>Thăng Long</b> | V15.2 - Bug Free</div>', unsafe_allow_html=True)
