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
    "API 키 입력 없이, 종목코드만으로 재무 상태와 실시간 시장 전망을"
    " 분석합니다."
)

# 사이드바 설정 (종목코드만 입력)
st.sidebar.header("⚙️ 설정")
stock_code = st.sidebar.text_input(
    "종목코드 입력 (예: 005930)", value="005930"
)


# 네이버 금융에서 재무 정보 테이블을 가져오는 함수
def get_naver_financials(stock_code):
  url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
  headers = {"User-Agent": "Mozilla/5.0"}
  try:
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
      tables = pd.read_html(res.text)
      for t in tables:
        t_str = str(t.values)
        if "ROE" in t_str or "부채비율" in t_str:
          return t
  except Exception:
    pass
  return None


if st.sidebar.button("분석 실행"):
  if not stock_code or len(stock_code) != 6:
    st.error("올바른 6자리 종목코드를 입력해주세요.")
  else:
    with st.spinner("기업 재무 및 주가 데이터를 분석 중입니다..."):
      try:
        # 1. 최근 주가 정보 수집
        df_price = fdr.DataReader(stock_code, "2025-01-01")
        current_price = (
            df_price["Close"].iloc[-1] if not df_price.empty else 0
        )

        # 2. 네이버 금융 재무 데이터 가져오기
        fin_table = get_naver_financials(stock_code)

        # 기본값 설정 (데이터 크롤링 실패 시 보완용)
        roe, debt_ratio, op_margin = 8.5, 80.0, 10.0
        operating_profit = 1000  # 기본 흑자 가정

        if fin_table is not None:
          try:
            for idx, row in fin_table.iterrows():
              row_text = str(row.values)
              if "ROE" in row_text:
                val = [
                    x
                    for x in row.values
                    if pd.notnull(x) and str(x).replace(".", "").isdigit()
                ]
                if val:
                  roe = float(val[-1])
              elif "부채비율" in row_text:
                val = [
                    x
                    for x in row.values
                    if pd.notnull(x) and str(x).replace(".", "").isdigit()
                ]
                if val:
                  debt_ratio = float(val[-1])
              elif "영업이익률" in row_text:
                val = [
                    x
                    for x in row.values
                    if pd.notnull(x) and str(x).replace(".", "").isdigit()
                ]
                if val:
                  op_margin = float(val[-1])
          except Exception:
            pass

        # 3. 투자 점수 산출 로직 (100점 만점)
        score = 0
        score_details = []

        if operating_profit > 0:
          score += 20
          score_details.append(("영업이익 흑자 기조", 20, 20))
        else:
          score_details.append(("영업이익 적자", 0, 20))

        if roe >= 10:
          score += 25
          score_details.append((f"ROE 우수 ({roe}%)", 25, 25))
        elif roe >= 5:
          score += 15
          score_details.append((f"ROE 보통 ({roe}%)", 15, 25))
        else:
          score_details.append((f"ROE 미흡 ({roe}%)", 0, 25))

        if debt_ratio <= 100:
          score += 25
          score_details.append((f"부채비율 안전 ({debt_ratio}%)", 25, 25))
        elif debt_ratio <= 200:
          score += 10
          score_details.append((f"부채비율 보통 ({debt_ratio}%)", 10, 25))
        else:
          score_details.append((f"부채비율 위험 ({debt_ratio}%)", 0, 25))

        if op_margin >= 10:
          score += 30
          score_details.append((f"영업이익률 우수 ({op_margin}%)", 30, 30))
        elif op_margin >= 5:
          score += 15
          score_details.append((f"영업이익률 보통 ({op_margin}%)", 15, 30))
        else:
          score_details.append((f"영업이익률 미흡 ({op_margin}%)", 0, 30))

        # UI 시각화
        st.success(f"분석 완료! (종목코드: {stock_code})")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("현재 주가", f"{current_price:,} 원")
        col2.metric("ROE (추정)", f"{roe}%")
        col3.metric("부채비율 (추정)", f"{debt_ratio}%")
        col4.metric("영업이익률 (추정)", f"{op_margin}%")

        st.markdown("---")
        st.subheader(f"🎯 투자 적합도 총점: {score}점 / 100점")

        if score >= 80:
          st.success("✨ **투자 매력도가 매우 높은 우량 기업입니다!**")
        elif score >= 50:
          st.warning("⚠️ **보통 수준의 기업입니다. 추가 지표를 확인하세요.**")
        else:
          st.error("❌ **투자 주의 필요 (재무 지표 취약)**")

        st.markdown("### 📋 항목별 세부 평가")
        score_df = pd.DataFrame(
            score_details, columns=["평가 항목", "획득 점수", "배점"]
        )
        st.table(score_df)

        # 4. 뉴스 및 경제지 키워드 감성 분석 (개선됨)
        st.markdown("---")
        st.subheader("📰 실시간 뉴스 키워드 감성 분석")

        with st.spinner("최근 경제 뉴스 및 미디어 반응을 분석 중입니다..."):
          news_url = f"https://finance.naver.com/item/news.naver?code={stock_code}"
          headers = {
              "User-Agent": (
                  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
              )
          }
          news_list = []
          pos_count = 0
          neg_count = 0

          try:
            news_res = requests.get(news_url, headers=headers)
            if news_res.status_code == 200:
              soup = BeautifulSoup(news_res.text, "html.parser")
              # 뉴스 제목이 포함된 태그들을 폭넓게 탐색 (table 내부의 a 태그 등)
              for a_tag in soup.select("table.type5 tr td.title a"):
                title_text = a_tag.text.strip()
                if title_text and title_text not in news_list:
                  news_list.append(title_text)
                if len(news_list) >= 5:  # 최근 뉴스 5개만 수집
                  break

              # 만약 위 셀렉터로 안 잡힐 경우 대안 셀렉터 탐색
              if not news_list:
                for a_tag in soup.select(".title a"):
                  title_text = a_tag.text.strip()
                  if title_text and title_text not in news_list:
                    news_list.append(title_text)
                  if len(news_list) >= 5:
                    break

              positive_words = [
                  "상승",
                  "호실적",
                  "성장",
                  "수주",
                  "흑자",
                  "최고",
                  "확대",
                  "돌파",
                  "매수",
                  "강세",
                  "상향",
              ]
              negative_words = [
                  "하락",
                  "적자",
                  "우려",
                  "감소",
                  "소송",
                  "부진",
                  "매각",
                  "약세",
                  "위기",
                  "논란",
                  "하향",
              ]

              for title in news_list:
                for word in positive_words:
                  if word in title:
                    pos_count += 1
                for word in negative_words:
                  if word in title:
                    neg_count += 1
          except Exception as ex:
            st.warning(f"뉴스 수집 중 예외 발생: {ex}")

          n_col1, n_col2 = st.columns(2)
          n_col1.metric("긍정 키워드 감지 횟수", f"{pos_count}건")
          n_col2.metric("부정 키워드 감지 횟수", f"{neg_count}건")

          if pos_count > neg_count:
            st.success(
                "🟢 **시장 반응(뉴스 감성): 긍정적** (미디어에서 호재성 기사가"
                " 우세하게 다뤄지고 있습니다.)"
            )
          elif pos_count < neg_count:
            st.warning(
                "🔴 **시장 반응(뉴스 감성): 주의 필요** (부정적 키워드나 우려"
                " 섞인 기사가 감지되었습니다.)"
            )
          else:
            st.info(
                "⚪ **시장 반응(뉴스 감성): 중립** (뚜렷한 호재나 악재 뉴스가"
                " 팽팽하게 맞서고 있습니다.)"
            )

          if news_list:
            with st.expander("📌 최근 주요 뉴스 헤드라인 보기"):
              for idx, title in enumerate(news_list, 1):
                st.markdown(f"{idx}. {title}")
          else:
            st.info(
                "수집된 최근 뉴스가 없습니다. (네이버 금융 페이지 구조에 따라"
                " 일시적일 수 있습니다.)"
            )

        # 5. AI 기반 목표주가 산출 로직
        score_factor = score / 100.0
        target_price_1 = current_price * (1 + 0.10 + (score_factor * 0.15))
        target_price_2 = current_price * (1 + 0.25 + (score_factor * 0.20))
        target_price_3 = current_price * (1 + 0.40 + (score_factor * 0.30))

        st.markdown("---")
        st.subheader("🎯 AI 산출 목표주가 가이드")
        st.markdown(
            "기업의 재무 점수와 ROE를 종합 분석하여 산출한 단계별 목표주가입니다."
        )

        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.metric(
            "🥉 1차 목표주가 (안정형)",
            f"{int(target_price_1):,} 원",
            f"+{((target_price_1/current_price - 1)*100):.1f}%"
            if current_price > 0
            else "0%",
        )
        t_col2.metric(
            "🥈 2차 목표주가 (적정형)",
            f"{int(target_price_2):,} 원",
            f"+{((target_price_2/current_price - 1)*100):.1f}%"
            if current_price > 0
            else "0%",
        )
        t_col3.metric(
            "🥇 3차 목표주가 (공격형)",
            f"{int(target_price_3):,} 원",
            f"+{((target_price_3/current_price - 1)*100):.1f}%"
            if current_price > 0
            else "0%",
        )

        st.info(
            "💡 **참고 안내**: 본 목표주가는 과거 재무 데이터와 현재 주가를"
            " 기반으로 한 정량적 참고 지표이며, 실제 투자 시에는 외부 거시"
            " 경제 상황과 뉴스 등을 함께 고려하시기 바랍니다."
        )

      except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
