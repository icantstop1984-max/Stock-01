import FinanceDataReader as fdr
import pandas as pd
import requests
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="국내 주식 AI 익일 예측 및 보수적 정밀 분석 프로그램",
    layout="wide",
)

st.title("📈 국내 주식 실시간 재무 & AI 익일 주가 방향성 예측 대시보드")
st.markdown(
    "API 키 입력 없이 종목코드만으로 실시간 재무 제표, 1주일 시장 추세, 그리고 AI"
    " 익일 주가 방향성 예측을 수행합니다."
)

# 사이드바 설정 (종목코드만 입력)
st.sidebar.header("⚙️ 설정")
stock_code = st.sidebar.text_input(
    "종목코드 입력 (예: 005930)", value="005930"
)


# 네이버 금융에서 실제 재무 정보를 실시간으로 파싱하는 안전 함수
def get_naver_financials(code):
  url = f"https://finance.naver.com/item/main.naver?code={code}"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }
  try:
    res = requests.get(url, headers=headers, timeout=5)
    if res.status_code == 200:
      tables = pd.read_html(res.text)
      for t in tables:
        t_str = str(t.values)
        if "부채비율" in t_str or "ROE" in t_str or "영업이익률" in t_str:
          return t
  except Exception:
    pass
  return None


# 숫자 추출 헬퍼 함수
def extract_all_numbers(lst):
  nums = []
  for x in lst:
    cleaned = (
        str(x)
        .replace(",", "")
        .replace("%", "")
        .replace("E", "")
        .replace("N/A", "")
        .strip()
    )
    try:
      val = float(cleaned)
      nums.append(val)
    except ValueError:
      pass
  return nums


if st.sidebar.button("AI 정밀 분석 및 익일 예측 실행"):
  if not stock_code or len(stock_code) != 6:
    st.error("올바른 6자리 종목코드를 입력해주세요.")
  else:
    with st.spinner(
        "종목명, 시장 지수, 실시간 재무 및 AI 예측 모델을 실행 중입니다..."
    ):
      # 종목명 가져오기 (KRX 전 종목 리스트 활용)
      stock_name = "알 수 없는 종목"
      try:
        df_krx = fdr.StockListing("KRX")
        match = df_krx[df_krx["Code"] == stock_code]
        if not match.empty:
          stock_name = match["Name"].values[0]
      except Exception:
        pass

      # 1. 코스피 시장 지수 최근 1주일 추세 수집
      try:
        df_kospi = fdr.DataReader("KS11", "2025-01-01")
      except Exception:
        df_kospi = pd.DataFrame()

      kospi_current = (
          df_kospi["Close"].iloc[-1] if not df_kospi.empty else 2500
      )
      if len(df_kospi) >= 5:
        kospi_week_ago = df_kospi["Close"].iloc[-5]
      elif len(df_kospi) > 1:
        kospi_week_ago = df_kospi["Close"].iloc[0]
      else:
        kospi_week_ago = kospi_current

      kospi_weekly_change = (
          (kospi_current - kospi_week_ago) / kospi_week_ago
      ) * 100
      kospi_prev = (
          df_kospi["Close"].iloc[-2] if len(df_kospi) > 1 else kospi_current
      )
      kospi_daily_change = (
          (kospi_current - kospi_prev) / kospi_prev
      ) * 100

      # 코스닥 지수 수집
      try:
        df_kosdaq = fdr.DataReader("KQ11", "2025-01-01")
      except Exception:
        df_kosdaq = pd.DataFrame()
      kosdaq_current = (
          df_kosdaq["Close"].iloc[-1] if not df_kosdaq.empty else 800
      )

      # 상단 시장 지수 UI 표시
      st.subheader("🌐 실시간 국내 주요 시장 지수 및 1주일 추세")
      m_col1, m_col2 = st.columns(2)
      m_col1.metric(
          "코스피 (KOSPI)",
          f"{kospi_current:,.2f}",
          f"당일 {kospi_daily_change:+.2f}% / 1주 {kospi_weekly_change:+.2f}%",
      )
      m_col2.metric("코스닥 (KOSDAQ)", f"{kosdaq_current:,.2f}")
      st.markdown("---")

      # 2. 최근 종목 주가 정보 및 단기 모멘텀 수집
      try:
        df_price = fdr.DataReader(stock_code, "2025-01-01")
      except Exception:
        df_price = pd.DataFrame()

      current_price = (
          df_price["Close"].iloc[-1] if not df_price.empty else 50000
      )
      price_change_5d = 0.0
      if len(df_price) >= 5:
        p_start = df_price["Close"].iloc[-5]
        price_change_5d = ((current_price - p_start) / p_start) * 100

      # 
