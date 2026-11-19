from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# 페이지 디자인 설정
st.set_page_config(
    page_title="인천공항 스마트 보안검색대 추천 시스템", layout="centered"
)

st.title("인천공항 TAM 기반 스마트 보안검색대 추천 시스템")
st.markdown(
    "실시간 출국장 혼잡도 API 데이터를 바탕으로 **가장 여유로운 보안검색대를"
    " 안내**하는 스마트 발권 화면입니다."
)
st.markdown("---")

SERVICE_KEY = "ddaabc379ff683cc00174904ea4b4c1e945a8a951a12f886ecded9fe791c9c16"
BASE_URL = "https://apis.data.go.kr/B551177/statusOfDepartureCongestion"

st.subheader("시스템 설정 및 승객 정보")
terminal_id = st.selectbox(
    "터미널 선택", ["P01 (제1여객터미널)", "P03 (제2여객터미널)"]
)

col_p1, col_p2 = st.columns(2)
with col_p1:
  passenger_name = st.text_input("탑승객 성명", value="이준우")
  flight_no = st.text_input("운항편명", value="TW245")
  departure_time = st.text_input("출발시간", value="15:30")
with col_p2:
  airline_name = st.text_input("항공사", value="트리니티항공")
  destination = st.text_input("목적지", value="도쿄/나리타 (NRT)")
  checkin_counter = st.text_input("체크인 카운터", value="A01-C34")

boarding_gate = st.text_input("탑승구 (미정 시 공란 가능)", value="")

t_id = "P01" if "P01" in terminal_id else "T2"
api_terminal_id = "P01" if "P01" in terminal_id else "P03"


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


if st.button("최적 보안검색대 배정 및 탑승권 발급"):
  # 제2여객터미널 선택 시 API 미제공 안내 예외 처리
  if api_terminal_id == "P03":
    st.warning(
        "현재 인천국제공항공사 OpenAPI(V1.1) 기준 제2여객터미널(P03) 출국장"
        " 혼잡도 데이터는 미제공(향후 제공 예정) 상태입니다. 제1여객터미널(P01)을"
        " 선택해 주세요."
    )
    st.stop()

  url = f"{BASE_URL}/getDepartureCongestion"

  params = {
      "serviceKey": SERVICE_KEY,
      "numOfRows": "20",
      "pageNo": "1",
      "terminalId": api_terminal_id,
      "type": "json",
  }

  try:
    with st.spinner("실시간 출국장 혼잡도 데이터를 불러오는 중입니다..."):
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
            "데이터를 불러오지 못했습니다. API 트래픽 한도나 인증키 상태를"
            " 확인해 주세요."
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
              f"유효한 출국장 데이터를 추출하지 못했습니다. 응답 확인: {data}"
          )
        else:
          open_items = [x for x in valid_items if x["_is_open"]]
          target_pool = open_items if open_items else valid_items

          # 1순위: 예상 대기시간(분), 2순위: 대기 인원(명)
          best_gate = min(
              target_pool,
              key=lambda x: (x["예상 대기시간(분)"], x["대기 인원(명)"]),
          )

          st.success("실시간 혼잡도 분석 및 추천 출국장 매칭이 완료되었습니다.")

          if not open_items:
            st.info(
                "현재 시간대 운영 중으로 확인된 출국장이 없어 전체 조회"
                " 데이터 기준으로 안내합니다."
            )

          terminal_short = "T1" if t_id == "P01" else "T2"
          gate_display = (
              boarding_gate.strip() if boarding_gate.strip() else "미정"
          )

          st.markdown("### BOARDING PASS")
          st.markdown(
              f"""
              <div style="border:1px solid #d0d7de; border-radius:12px; padding:20px; background-color:#ffffff; color:#111827;">
                <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #cbd5e1; padding-bottom:12px; margin-bottom:16px;">
                  <div>
                    <div style="font-size:12px; color:#64748b;">PASSENGER</div>
                    <div style="font-size:18px; font-weight:700;">{passenger_name}</div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-size:12px; color:#64748b;">DEPARTURE</div>
                    <div style="font-size:18px; font-weight:700;">{departure_time}</div>
                  </div>
                </div>
                <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:14px; margin-bottom:16px;">
                  <div>
                    <div style="font-size:12px; color:#64748b;">목적지</div>
                    <div style="font-size:15px; font-weight:600;">{destination}</div>
                  </div>
                  <div>
                    <div style="font-size:12px; color:#64748b;">운항편명 / 항공사</div>
                    <div style="font-size:15px; font-weight:600;">{flight_no} / {airline_name}</div>
                  </div>
                  <div>
                    <div style="font-size:12px; color:#64748b;">터미널</div>
                    <div style="font-size:15px; font-weight:600;">{terminal_short}</div>
                  </div>
                  <div>
                    <div style="font-size:12px; color:#64748b;">체크인 카운터</div>
                    <div style="font-size:15px; font-weight:600;">{checkin_counter}</div>
                  </div>
                  <div>
                    <div style="font-size:12px; color:#64748b;">탑승구</div>
                    <div style="font-size:15px; font-weight:600;">{gate_display}</div>
                  </div>
                  <div>
                    <div style="font-size:12px; color:#64748b;">권장 보안검색대</div>
                    <div style="font-size:15px; font-weight:700; color:#0f766e;">{best_gate['검색대 위치']}</div>
                  </div>
                </div>
              </div>
              """,
              unsafe_allow_html=True,
          )

          st.markdown("")
          col1, col2 = st.columns(2)
          with col1:
            st.metric(
                label="권장 보안검색대",
                value=f"{best_gate['검색대 위치']}",
                delta=f"예상 대기 {best_gate['예상 대기시간(분)']}분",
                delta_color="normal",
            )
          with col2:
            st.metric(
                label="현재 대기 인원",
                value=f"{best_gate['대기 인원(명)']}명",
                delta="기준 최단 대기",
            )

          st.warning(
              f"**안내:** 출국장 혼잡 완화를 위해 **{best_gate['검색대 위치']}**"
              f" (운영시간: {best_gate['운영 시간']}) 이용을 권장합니다."
          )

          with st.expander("실시간 전체 출국장 비교 데이터 보기"):
            display_items = [
                {k: v for k, v in row.items() if not k.startswith("_")}
                for row in valid_items
            ]
            st.dataframe(display_items)

  except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
