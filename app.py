from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# 페이지 디자인 설정
st.set_page_config(
    page_title="인천공항 스마트 보안검색대 추천 시스템", layout="centered"
)

st.title("✈️ 인천공항 TAM 기반 스마트 보안검색대 추천 시스템")
st.markdown(
    "실시간 출국장 혼잡도 API 데이터를 분석하여 **가장 쾌적한 보안검색대를"
    " 자동으로 매칭**하는 스마트 발권 시스템입니다."
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


# 제1여객터미널 출국장(1~6번) 게이트 코드를 OpenAPI 명세서 기준 한글 이름으로 매칭하는 함수
def get_friendly_gate_name(gate_id):
  gate_map = {
      "DG1_W": "제1 출국장 (서측)",
      "DG1_E": "제1 출국장 (동측)",
      "DG2_W": "제2 출국장 (서측)",
      "DG2_E": "제2 출국장 (동측 / 스마트패스 전용레인)",
      "DG3_W": "제3 출국장 (서측)",
      "DG3_E": "제3 출국장 (동측)",
      "DG4_W": "제4 출국장 (서측)",
      "DG4_E": "제4 출국장 (동측)",
      "DG5_W": "제5 출국장 (서측)",
      "DG5_E": "제5 출국장 (동측)",
      "DG6_W": "제6 출국장 (서측)",
      "DG6_E": "제6 출국장 (동측)",
  }
  return gate_map.get(gate_id, f"출국장 ({gate_id})")


# 현재 한국 시각(KST) 기준 운영 중 여부 판별 함수
def is_currently_open(operating_time):
  if not operating_time or not isinstance(operating_time, str):
    return False

  cleaned = operating_time.strip().replace(" ", "")
  if not cleaned or "미운영" in cleaned or "운영종료" in cleaned:
    return False
  if "24시간" in cleaned:
    return True

  sep = "~" if "~" in cleaned else ("-" if "-" in cleaned else None)
  if not sep:
    return False

  try:
    parts = cleaned.split(sep)
    if len(parts) < 2:
      return False

    start_h, start_m = map(int, parts[0].split(":")[:2])
    end_h, end_m = map(int, parts[1].split(":")[:2])

    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    now_min = now_kst.hour * 60 + now_kst.minute
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m

    if end_min == 0:
      end_min = 24 * 60

    if start_min <= end_min:
      return start_min <= now_min <= end_min
    # 자정을 넘어가는 운영시간(예: 22:00~02:00) 처리
    return now_min >= start_min or now_min <= end_min
  except Exception:
    # 예상치 못한 문자열 포맷일 경우 오판 방지를 위해 True 반환 후 데이터 표에서 확인 가능하게 함
    return True


if st.button("🚀 최적 보안검색대 배정 및 탑승권 발급"):
  # 제2여객터미널 선택 시 API 미제공 안내 예외 처리
  if t_id == "P03":
    st.warning(
        "⚠️ 현재 인천국제공항공사 OpenAPI(V1.1) 정책상 제2여객터미널(P03)의"
        " 출국장 혼잡도 데이터는 '향후 제공 예정'입니다. 제1여객터미널(P01)을"
        " 선택해 시연해 주세요."
    )
    st.stop()

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
      response = requests.get(url, params=params, timeout=10)
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
            raw_gate_id = str(item.get("gateId", "DG1_E"))
            friendly_name = get_friendly_gate_name(raw_gate_id)
            operating_time = str(item.get("operatingTime", "") or "정보 없음")
            is_open = is_currently_open(operating_time)
            wait_time = int(item.get("waitTime", 999))
            wait_length = int(item.get("waitLength", 999))

            valid_items.append({
                "검색대 위치": friendly_name,
                "운영 여부": "운영 중" if is_open else "미운영/확인필요",
                "운영 시간": operating_time,
                "예상 대기시간(분)": wait_time,
                "대기 인원(명)": wait_length,
                "_is_open": is_open,
            })
          except Exception:
            continue

        if not valid_items:
          st.warning(
              "⚠️ 유효한 게이트 데이터를 추출하지 못했습니다. 응답 데이터를"
              f" 확인해주세요: {data}"
          )
        else:
          open_items = [x for x in valid_items if x["_is_open"]]
          target_pool = open_items if open_items else valid_items

          # 1순위: 예상 대기시간(분), 2순위: 대기 인원(명)
          best_gate = min(
              target_pool,
              key=lambda x: (x["예상 대기시간(분)"], x["대기 인원(명)"]),
          )

          st.success("✅ 실시간 데이터 분석 및 동선 분산 매칭 완료!")

          if not open_items:
            st.info(
                "ℹ️ 현재 시간대 운영 중으로 판별된 출국장이 없어 전체 조회"
                " 데이터 기준으로 안내합니다."
            )

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
            display_items = [
                {k: v for k, v in row.items() if not k.startswith("_")}
                for row in valid_items
            ]
            st.dataframe(display_items)

  except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
