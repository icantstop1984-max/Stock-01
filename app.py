import FinanceDataReader as fdr
import pandas as pd
import streamlit as st

# 소문자로 설치된 opendartreader를 안전하게 불러오는 코드
try:
  import OpenDartReader
except ImportError:
  import opendartreader as OpenDartReader


# 페이지 설정
st.set_page_config(
    page_title="국내 주식 재무제표 분석 및 투자 판단 프로그램",
    layout="wide",
)

st.title("📈 국내 주식 재무제표 분석 및 투자 판단 대시보드")
st.markdown(
    "DART 전자공시와 FinanceDataReader를 활용해 기업의 재무 상태를 분석하고 투자 적합도를 평가합니다."
)

# 사이드바 설정 (API 키 입력)
st.sidebar.header("⚙️ 설정")
dart_api_key = st.sidebar.text_input(
    "DART API Key 입력",
    type="password",
    help="https://opendart.fss.or.kr 에서 무료로 발급받으실 수 있습니다.",
)
stock_code = st.sidebar.text_input(
    "종목코드 입력 (예: 005930)", value="005930"
)
analysis_year = st.sidebar.selectbox("분석 기준 연도", [2024, 2023, 2022], index=0)

if st.sidebar.button("분석 실행"):
  if not dart_api_key:
    st.error("DART API Key를 입력해주세요.")
  elif not stock_code or len(stock_code) != 6:
    st.error("올바른 6자리 종목코드를 입력해주세요.")
  else:
    with st.spinner("데이터를 수집하고 분석하는 중입니다..."):
      try:
        # 1. DART 및 주가 데이터 초기화
        dart = OpenDartReader(dart_api_key)

        # 재무제표 수집 (연결재무제표 기준)
        fin_state = dart.finstate(stock_code, analysis_year)

        if fin_state is None or fin_state.empty:
          st.error(
              "해당 연도의 재무제표 데이터를 가져올 수 없습니다. API Key나"
              " 종목코드를 확인해주세요."
          )
        else:
          # 최근 주가 및 시가총액 정보 수집
          df_price = fdr.DataReader(stock_code, "2025-01-01")
          current_price = (
              df_price["Close"].iloc[-1] if not df_price.empty else 0
          )

          # 주요 계정 추출 함수 (연결재무제표 우선)
          def get_account_value(df, account_name):
            row = df[df["account_nm"] == account_name]
            if not row.empty:
              # 당기(thstrm_amount) 값 추출 및 숫자로 변환
              val = row.iloc[0]["thstrm_amount"]
              if val:
                return float(str(val).replace(",", ""))
            return 0

          # 주요 재무 지표 추출
          revenue = get_account_value(fin_state, "매출액")
          if revenue == 0:
            revenue = get_account_value(fin_state, "수익(매출액)")

          operating_profit = get_account_value(fin_state, "영업이익")
          net_income = get_account_value(
              fin_state, "당기순이익"
          ) or get_account_value(fin_state, "법인세차감전순이익")
          total_assets = get_account_value(fin_state, "자산총계")
          total_liabilities = get_account_value(fin_state, "부채총계")
          total_equity = get_account_value(fin_state, "자본총계")

          # 지표 계산
          roe = (
              (net_income / total_equity) * 100
              if total_equity > 0
              else 0
          )
          debt_ratio = (
              (total_liabilities / total_equity) * 100
              if total_equity > 0
              else 0
          )
          op_margin = (
              (operating_profit / revenue) * 100 if revenue > 0 else 0
          )

          # 2. 투자 점수 산출 로직 (100점 만점)
          score = 0
          score_details = []

          # ① 영업이익 흑자 여부 (20점)
          if operating_profit > 0:
            score += 20
            score_details.append(("영업이익 흑자", 20, 20))
          else:
            score_details.append(("영업이익 적자", 0, 20))

          # ② ROE 10% 이상 (25점)
          if roe >= 10:
            score += 25
            score_details.append((f"ROE 우수 ({roe:.2f}%)", 25, 25))
          elif roe >= 5:
            score += 15
            score_details.append((f"ROE 보통 ({roe:.2f}%)", 15, 25))
          else:
            score_details.append((f"ROE 미흡 ({roe:.2f}%)", 0, 25))

          # ③ 부채비율 100% 미만 (25점)
          if debt_ratio <= 100:
            score += 25
            score_details.append((f"부채비율 안전 ({debt_ratio:.2f}%)", 25, 25))
          elif debt_ratio <= 200:
            score += 10
            score_details.append((f"부채비율 보통 ({debt_ratio:.2f}%)", 10, 25))
          else:
            score_details.append((f"부채비율 위험 ({debt_ratio:.2f}%)", 0, 25))

          # ④ 영업이익률 10% 이상 (30점)
          if op_margin >= 10:
            score += 30
            score_details.append((f"영업이익률 우수 ({op_margin:.2f}%)", 30, 30))
          elif op_margin >= 5:
            score += 15
            score_details.append((f"영업이익률 보통 ({op_margin:.2f}%)", 15, 30))
          else:
            score_details.append((f"영업이익률 미흡 ({op_margin:.2f}%)", 0, 30))

          # 3. UI 시각화
          st.success(
              f"분석 완료! (종목코드: {stock_code}, 기준연도:"
              f" {analysis_year}년)"
          )

          col1, col2, col3, col4 = st.columns(4)
          col1.metric("현재 주가", f"{current_price:,} 원")
          col2.metric("ROE", f"{roe:.2f}%")
          col3.metric("부채비율", f"{debt_ratio:.2f}%")
          col4.metric("영업이익률", f"{op_margin:.2f}%")

          st.markdown("---")
          st.subheader(
              f"🎯 투자 적합도 총점: {score}점 / 100점"
          )

          if score >= 80:
            st.success(
                "✨ **투자 매력도가 매우 높은 우량 기업입니다!** (재무 건전성 및"
                " 수익성이 뛰어납니다.)"
            )
          elif score >= 50:
            st.warning(
                "⚠️ **보통 수준의 기업입니다.** (일부 지표를 추가로 확인해"
                " 보세요.)"
            )
          else:
            st.error(
                "❌ **투자 주의 필요** (재무 지표상 취약한 부분이 많습니다.)"
            )

          # 평가 항목 상세 내역
          st.markdown("### 📋 항목별 세부 평가")
          score_df = pd.DataFrame(
              score_details, columns=["평가 항목", "획득 점수", "배점"]
          )
          st.table(score_df)

      except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
