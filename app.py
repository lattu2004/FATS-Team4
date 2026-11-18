import requests
import streamlit as st

# 페이지 디자인 설정
st.set_page_config(
    page_title="인천공항 스마트 보안검색대 추천 시스템", layout="centered"
)

st.title("✈️ 인천공항 TAM 기반 스마트 보안검색대 추천 시스템")
st.markdown(
    "실시간 출국장 혼잡도 API 데이터를 분석하여 **가장 쾌적한 보안검색대를"
    " 자동으로 매칭**하는 스마트 발권 프로토타입입니다."
)
st.markdown("---")

SERVICE_KEY = "ddaabc379ff683cc00174904ea4b4c1e945a8a951a12f886ecded9fe791c9c16"
BASE_URL = "https://apis.data.go.kr/B551177/statusOfDepartureCongestion"

st.subheader("🔑 시스템 설정 및 승객 정보")
terminal_id = st.selectbox(
    "터미널 선택", ["P01 (제1여객터미널)", "P03 (제2여객터미널)"]
)
passenger_name = st.text_input("탑승객 성명", value="이준우")
airline = st.text_input("편명 (Flight)", value="KE703 (ICN -> NRT)")

t_id = "P01" if "P01" in terminal_id else "P03"

# API의 영문/코드형 게이트 이름을 직관적인 한글 이름으로 예쁘게 바꿔주는 함수
def get_friendly_gate_name(gate_id):
  gate_map = {
      "Dgw_1": "제1 출국장 (동쪽)",
      "Dgw_2": "제2 출국장 (중앙동쪽)",
      "Dgw_3": "제3 출국장 (중앙서쪽)",
      "Dgw_4": "제4 출국장 (서쪽)",
      "Dgw_5": "제5 출국장 (동편 전용)",
      "Dgw_6": "제6 출국장 (서편 전용)",
  }
  return gate_map.get(gate_id, f"출국장 ({gate_id})")

if st.button("🚀 최적 보안검색대 배정 및 탑승권 발급"):
  url = f"{BASE_URL}/getDepartureCongestion"

  params = {
      "serviceKey": SERVICE_KEY,
      "numOfRows": "20",
      "pageNo": "1",
      "terminalId": t_id,
      "type": "json",
  }

  try:
    with st.spinner(
        "인천공항 APOC 서버에서 실시간 출국장 데이터를 수집하고 있습니다..."
    ):
      response = requests.get(url, params=params)
      data = response.json()

      response_obj = data.get("response", {})
      if isinstance(response_obj, list):
        response_obj = response_obj[0] if response_obj else {}

      body_obj = response_obj.get("body", {})
      if isinstance(body_obj, list):
        body_obj = body_obj[0] if body_obj else {}

      items_obj = body_obj.get("items", {})
      if isinstance(items_obj, list):
        items = items_obj
      elif isinstance(items_obj, dict):
        items = items_obj.get("item", [])
      else:
        items = []

      if isinstance(items, dict):
        items = [items]

      if not items:
        st.error(
            "❌ 데이터를 불러오지 못했습니다. API 트래픽 초과 여부나 인증키"
            " 상태를 확인해주세요."
        )
      else:
        valid_items = []
        for item in items:
          try:
            raw_gate_id = str(item.get("gateId", "Dgw_1"))
            friendly_name = get_friendly_gate_name(raw_gate_id)
            wait_time = int(item.get("waitTime", 999))
            wait_length = int(item.get("waitLength", 999))
            
            valid_items.append({
                "검색대 위치": friendly_name,
                "운영 시간": item.get("operatingTime"),
                "예상 대기시간(분)": wait_time,
                "대기 인원(명)": wait_length,
            })
          except:
            continue

        if not valid_items:
          st.warning(
              "⚠️ 유효한 게이트 데이터를 추출하지 못했습니다. 응답 데이터를"
              f" 확인해주세요: {data}"
          )
        else:
          best_gate = min(valid_items, key=lambda x: x["예상 대기시간(분)"])

          st.success("✅ 실시간 데이터 분석 및 동선 분산 매칭 완료!")

          st.markdown("### 🎫 [Smart Boarding Pass & Gate Recommendation]")
          st.info(f"**승객 성명:** {passenger_name}  |  **편명:** {airline}")

          col1, col2 = st.columns(2)
          with col1:
            st.metric(
                label="🎯 추천 보안검색대",
                value=f"{best_gate['검색대 위치']}",
                delta=f"예상 대기 {best_gate['예상 대기시간(분)']}분",
                delta_color="normal",
            )
          with col2:
            st.metric(
                label="👥 현재 대기 인원",
                value=f"{best_gate['대기 인원(명)']}명",
                delta="가장 원활함",
            )

          st.warning(
              f"📌 **시스템 가이드:** 중앙부 쏠림 현상을 방지하기 위해, 고객님께서는"
              f" 현재 가장 여유로운 **{best_gate['검색대 위치']}** (운영시간:"
              f" {best_gate['운영 시간']})로 이동하여 주시기 바랍니다."
          )

          with st.expander("📊 실시간 전체 출국장 비교 데이터 확인하기"):
            st.dataframe(valid_items)

  except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
