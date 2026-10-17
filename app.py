import FinanceDataReader as fdr
from bs4 import BeautifulSoup
import pandas as pd
import requests
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="국내 주식 재무제표 분석 및 투자 판단 프로그램", layout="wide"
)

st.title("📈 국내 주식 재무제표 분석 및 투자 판단 대시보드")
st.markdown(
    "DART API와 FinanceDataReader를 활용해 기업의 재무 상태를 분석하고"
    " 평가합니다."
)

# 사이드바 설정 (API 키 및 입력)
st.sidebar.header("⚙️ 설정")
dart_api_key = st.sidebar.text_input(
    "DART API Key 입력",
    type="password",
    help="https://opendart.fss.or.kr 에서 무료로 발급받으실 수 있습니다.",
)
stock_code = st.sidebar.text_input(
    "종목코드 입력 (예: 005930)", value="005930"
)
analysis_year = st.sidebar.selectbox(
    "분석 기준 연도", [2026, 2025, 2024, 2023, 2022], index=0
)


# DART 재무제표 데이터를 직접 가져오는 함수
def get_dart_financials(api_key, corp_code, year):
  url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
  params = {
      "crtfc_key": api_key,
      "corp_code": corp_code,
      "bsns_year": str(year),
      "reprt_code": "11011",  # 사업보고서
  }
  response = requests.get(url, params=params)
  if response.status_code == 200:
    data = response.json()
    if data.get("status") == "000":
      return data.get("list", [])
  return []


# 고유번호(corp_code) 조회를 위한 함수
def get_corp_code(api_key, stock_code):
  import io
  import zipfile
  import xml.etree.ElementTree as ET

  url = "https://opendart.fss.or.kr/api/corpCode.xml"
  params = {"crtfc_key": api_key}
  res = requests.get(url, params=params)

  if res.status_code == 200 and res.content.startswith(b"PK"):
    try:
      z = zipfile.ZipFile(io.BytesIO(res.content))
      for filename in z.namelist():
        if filename.endswith(".xml"):
          xml_data = z.read(filename)
          root = ET.fromstring(xml_data)
          for corp in root.findall("list"):
            code = corp.find("stock_code")
            if code is not None and code.text == stock_code:
              c_code = corp.find("corp_code")
              return c_code.text if c_code is not None else None
    except Exception:
      return None
  return None


if st.sidebar.button("분석 실행"):
  if not dart_api_key:
    st.error("DART API Key를 입력해주세요.")
  elif not stock_code or len(stock_code) != 6:
    st.error("올바른 6자리 종목코드를 입력해주세요.")
  else:
    with st.spinner("DART 및 주가 데이터를 수집하고 분석하는 중입니다..."):
      try:
        # 1. 고유번호 조회
        corp_code = get_corp_code(dart_api_key, stock_code)
        if not corp_code:
          st.error(
              "해당 종목코드의 DART 고유번호를 찾을 수 없습니다. 종목코드나"
              " API Key를 확인해주세요."
          )
        else:
          # 2. 재무제표 데이터 가져오기
          fin_list = get_dart_financials(
              dart_api_key, corp_code, analysis_year
          )

          # 최근 주가 정보 수집
          df_price = fdr.DataReader(stock_code, "2025-01-01")
          current_price = (
              df_price["Close"].iloc[-1] if not df_price.empty else 0
          )

          # 데이터 추출 헬퍼 함수
          def find_val(item_name):
            for item in fin_list:
              if item.get("account_nm") == item_name and item.get(
                  "fs_div"
              ) in ["CFS", "OF"]:
                val = item.get("thstrm_amount", "0")
                if val and val != "-":
                  return float(str(val).replace(",", ""))
            for item in fin_list:
              if item_name in item.get("account_nm", ""):
                val = item.get("thstrm_amount", "0")
                if val and val != "-":
                  return float(str(val).replace(",", ""))
            return 0.0

          revenue = find_val("매출액")
          if revenue == 0:
            revenue = find_val("수익(매출액)")

          operating_profit = find_val("영업이익")
          net_income = find_val("당기순이익")
          if net_income == 0:
            net_income = find_val("법인세차감전순이익")

          total_liabilities = find_val("부채총계")
          total_equity = find_val("자본총계")

          # 지표 계산
          roe = (
              (net_income / total_equity) * 100
              if total_equity > 0
              else 0.0
          )
          debt_ratio = (
              (total_liabilities / total_equity) * 100
              if total_equity > 0
              else 0.0
          )
          op_margin = (
              (operating_profit / revenue) * 100 if revenue > 0 else 0.0
          )

          # 3. 투자 점수 산출 로직 (100점 만점)
          score = 0
          score_details = []

          if operating_profit > 0:
            score += 20
            score_details.append(("영업이익 흑자", 20, 20))
          else:
            score_details.append(("영업이익 적자", 0, 20))

          if roe >= 10:
            score += 25
            score_details.append((f"ROE 우수 ({roe:.2f}%)", 25, 25))
          elif roe >= 5:
            score += 15
            score_details.append((f"ROE 보통 ({roe:.2f}%)", 15, 25))
          else:
            score_details.append((f"ROE 미흡 ({roe
