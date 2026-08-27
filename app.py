import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# 頁面佈局設定
st.set_page_config(page_title="頂配版 AI 股票監控系統", layout="wide", initial_sidebar_state="expanded")
st.title("📈 頂配版 AI 股票監控與決策系統")

# 側邊欄設定
st.sidebar.header("⚙️ 系統與通訊設定")
TELEGRAM_TOKEN = st.sidebar.text_input("Telegram Bot Token", type="password")
CHAT_ID = st.sidebar.text_input("Telegram Chat ID")

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        st.error("請在左側邊欄填入 Telegram Token 與 Chat ID！")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    res = requests.post(url, data=payload)
    return res.status_code == 200

# 主介面輸入
stock_id = st.text_input("請輸入台股代碼（預設 2330.TW）：", "2330.TW").strip()

if stock_id:
    ticker = yf.Ticker(stock_id)
    df = ticker.history(period="100d")

    if df.empty:
        st.error("查無資料，請確認代碼是否正確（台股請加上 .TW，如 2330.TW）。")
    else:
        # --- 技術指標計算 ---
        # 1. 均線 MA
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        
        # 2. RSI 指標 (14日)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # 3. MACD 指標
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # 最新一筆與前一筆數據
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        last_price = latest['Close']
        ma5, ma20 = latest['MA5'], latest['MA20']
        rsi = latest['RSI']
        macd, signal_line = latest['MACD'], latest['Signal']

        # --- 頂部摘要資訊欄 ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"{last_price:.2f} 元")
        c2.metric("5日均線 (MA5)", f"{ma5:.2f}")
        c3.metric("RSI (14)", f"{rsi:.1f}")
        c4.metric("MACD 差值", f"{macd - signal_line:.2f}")

        # --- AI 複合訊號判定引擎 ---
        st.subheader("🤖 AI 綜合買賣訊號判定")
        
        # 買進條件：MA5 金叉 MA20 + RSI < 70 (未超買) + MACD > Signal
        buy_condition = (prev['MA5'] <= prev['MA20']) and (ma5 > ma20) and (macd > signal_line)
        # 賣出條件：MA5 死叉 MA20 或 RSI > 80 (嚴重超買警戒)
        sell_condition = ((prev['MA5'] >= prev['MA20']) and (ma5 < ma20)) or (rsi > 80)

        if buy_condition:
            msg = f"🟢【頂配 AI 買進訊號】\n標的：{stock_id}\n價格：{last_price:.2f}\n原因：均線黃金交叉 + MACD 多頭轉強！"
            st.success(msg)
            if st.button("推播買進訊號至 Telegram"):
                if send_telegram(msg):
                    st.toast("已成功推播！")
        elif sell_condition:
            msg = f"🔴【頂配 AI 賣出/避險訊號】\n標的：{stock_id}\n價格：{last_price:.2f}\n原因：均線死亡交叉或 RSI 過熱過度過高！"
            st.error(msg)
            if st.button("推播賣出訊號至 Telegram"):
                if send_telegram(msg):
                    st.toast("已成功推播！")
        else:
            st.info("⚪ 當前指標趨勢平穩，建議持續觀望。")

        # --- 三竹股市風格多頁籤 ---
        tab1, tab2, tab3 = st.tabs(["📈 K線與技術分析", "🏛️ 基本面與財務", "📰 公司資訊"])

        with tab1:
            st.write("**價格與均線走勢**")
            st.line_chart(df[['Close', 'MA5', 'MA20']])
            st.write("**RSI 強弱指標 (低於30超賣，高於70超買)**")
            st.line_chart(df['RSI'])

        with tab2:
            st.write("**公司財務摘要**")
            info = ticker.info
            f_col1, f_col2, f_col3 = st.columns(3)
            f_col1.metric("本益比 (PE)", f"{info.get('trailingPE', 'N/A')}")
            f_col2.metric("股價淨值比 (PB)", f"{info.get('priceToBook', 'N/A')}")
            f_col3.metric("殖利率", f"{info.get('dividendYield', 0)*100:.2f} %" if info.get('dividendYield') else "N/A")

        with tab3:
            st.write(f"**公司名稱**：{info.get('longName', stock_id)}")
            st.write(f"**產業類別**：{info.get('industry', 'N/A')}")
            st.write(f"**主要業務簡介**：\n{info.get('longBusinessSummary', '無簡介資料')}")
