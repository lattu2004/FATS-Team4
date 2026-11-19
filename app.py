import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

st.set_page_config(
    page_title="인천공항 스마트 보안검색대 추천 시스템", layout="centered"
)

st.title("인천공항 TAM 기반 스마트 보안검색대 추천 시스템")
st.markdown(
    "인천국제공항공사 공식 OpenAPI(`getDepartureCongestion`)로 수집한"
    " 실시간 APOC 출국장 혼잡도 데이터를 바탕으로 **가장 여유로운"
    " 보안검색대를 안내**하는 스마트 발권 화면입니다."
)
st.markdown("---")

SERVICE_KEY = "ddaabc379ff683cc00174904ea4b4c1e945a8a951a12f886ecded9fe791c9c16"
BASE_URL = "https://apis.data.go.kr/B551177/statusOfDepartureCongestion"
FLOORPLAN_PATH = "t1_floorplan.jpg"

st.subheader("시스템 설정 및 승객 정보")
terminal_id = st.selectbox(
    "터미널 선택", ["P01 (제1여객터미널)", "P03 (제2여객터미널)"]
)

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
  passenger_name = st.text_input("탑승객 성명", value="LEE/JUNWOO MR")
  flight_no = st.text_input("운항편명", value="TW245")
  departure_time = st.text_input("출발시간 (DEP)", value="15:30")
with col_p2:
  airline_name = st.text_input("항공사", value="티웨이항공")
  flight_date = st.text_input("탑승일 (DATE)", value="20NOV26")
  boarding_time = st.text_input("탑승시각 (BOARDING)", value="15:00")
with col_p3:
  origin_port = st.text_input("출발지 (FROM)", value="ICN SEOUL")
  destination = st.text_input("목적지 (TO)", value="NRT TOKYO")
  seat_no = st.text_input("좌석 (SEAT)", value="24A")

col_d1, col_d2, col_d3 = st.columns(3)
with col_d1:
  checkin_counter = st.text_input("체크인 카운터", value="A01-C34")
with col_d2:
  boarding_gate = st.text_input("탑승구 (GATE)", value="TBD")
with col_d3:
  zone_no = st.text_input("탑승구역 (ZONE)", value="ZONE 2")

t_id = "P01" if "P01" in terminal_id else "T2"
api_terminal_id = "P01" if "P01" in terminal_id else "P03"


def get_friendly_gate_name(gate_id):
  gate_map = {
      "DG1_W": "제1 출국장 (서편)",
      "DG1_E": "제1 출국장 (동편)",
      "DG2_W": "제2 출국장 (서편)",
      "DG2_E": "제2 출국장 (동편)",
      "DG3_W": "제3 출국장 (서편)",
      "DG3_E": "제3 출국장 (동편)",
      "DG4_W": "제4 출국장 (서편)",
      "DG4_E": "제4 출국장 (동편)",
      "DG5_W": "제5 출국장 (서편)",
      "DG5_E": "제5 출국장 (동편)",
      "DG6_W": "제6 출국장 (서편)",
      "DG6_E": "제6 출국장 (동편)",
  }
  return gate_map.get(gate_id, f"출국장 ({gate_id})")


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
    return now_min >= start_min or now_min <= end_min
  except Exception:
    return True


def get_base64_image(image_path: str):
  path = Path(image_path)
  if not path.exists():
    return None
  return base64.b64encode(path.read_bytes()).decode("utf-8")


def render_map_pin(gate_id, gate_lookup, recommended_id, top_pct, left_pct):
  info = gate_lookup.get(gate_id)
  is_rec = gate_id == recommended_id
  side = "서" if gate_id.endswith("_W") else "동"

  if not info or not info["_is_open"]:
    bg = "rgba(100, 116, 139, 0.86)"
    border = "1px solid #e2e8f0"
    line1 = f"{side}·미운영"
    line2 = ""
  else:
    wait_m = info["예상 대기시간(분)"]
    wait_p = info["대기 인원(명)"]
    bg = "rgba(5, 150, 105, 0.92)" if is_rec else "rgba(15, 41, 74, 0.86)"
    border = "1.5px solid #fde047" if is_rec else "1px solid #93c5fd"
    rec_tag = "★" if is_rec else ""
    line1 = f"{rec_tag}{side} {wait_m}분"
    line2 = f"{wait_p}명"

  sub_html = (
      f'<div style="font-size:8px; line-height:1.1; opacity:0.95;">{line2}</div>'
      if line2
      else ""
  )

  return (
      f'<div style="position:absolute; top:{top_pct}%; left:{left_pct}%;'
      " transform:translate(-50%, -50%);"
      f" background:{bg}; border:{border}; color:#ffffff;"
      " padding:2px 4px; border-radius:4px; font-size:8.5px; font-weight:700;"
      " line-height:1.15; text-align:center; white-space:nowrap;"
      ' box-shadow:0 1px 4px rgba(0,0,0,0.22); z-index:2;">'
      f"<div>{line1}</div>{sub_html}"
      "</div>"
  )



def render_gate_cell(gate_id, gate_lookup, recommended_id):
  info = gate_lookup.get(gate_id)
  is_rec = gate_id == recommended_id

  if not info:
    bg = "#f1f5f9"
    border = "1px solid #cbd5e1"
    status_text = "정보 없음"
    sub_text = "-"
    title_color = "#475569"
  elif not info["_is_open"]:
    bg = "#f1f5f9"
    border = "1px solid #cbd5e1"
    status_text = "미운영"
    sub_text = info["운영 시간"]
    title_color = "#64748b"
  else:
    wait_m = info["예상 대기시간(분)"]
    wait_p = info["대기 인원(명)"]
    if is_rec:
      bg = "#ecfdf5"
      border = "2px solid #059669"
      title_color = "#065f46"
    elif wait_m <= 10:
      bg = "#eff6ff"
      border = "1px solid #93c5fd"
      title_color = "#1e40af"
    elif wait_m <= 20:
      bg = "#fffbeb"
      border = "1px solid #fcd34d"
      title_color = "#92400e"
    else:
      bg = "#fef2f2"
      border = "1px solid #fca5a5"
      title_color = "#991b1b"
    status_text = f"{wait_m}분 · {wait_p}명"
    sub_text = "권장 출국장" if is_rec else "운영 중"

  side_label = "서편" if gate_id.endswith("_W") else "동편"
  badge_html = (
      '<div style="font-size:9px; font-weight:800; color:#ffffff;'
      " background:#059669; border-radius:4px; padding:1px 4px;"
      ' display:inline-block; margin-bottom:2px;">추천</div>'
      if is_rec
      else ""
  )

  return (
      f'<div style="background:{bg}; border:{border}; border-radius:8px;'
      ' padding:6px 4px; text-align:center; min-width:0;">'
      f"{badge_html}"
      f'<div style="font-size:10px; font-weight:700; color:{title_color};">{side_label}</div>'
      f'<div style="font-size:12px; font-weight:800; color:#0f172a; margin-top:1px;">{status_text}</div>'
      f'<div style="font-size:9px; color:#475569; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{sub_text}</div>'
      "</div>"
  )


if st.button("최적 보안검색대 배정 및 탑승권 발급"):
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
    fetched_at = datetime.now(ZoneInfo("Asia/Seoul")).strftime(
        "%Y-%m-%d %H:%M:%S KST"
    )
    with st.spinner(
        "인천공항 APOC 연동 OpenAPI(getDepartureCongestion)에서 실시간"
        " 출국장 데이터를 수집하는 중입니다..."
    ):
      response = requests.get(url, params=params, timeout=10)
      status_code = response.status_code
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
        gate_lookup = {}
        for item in items:
          try:
            raw_gate_id = str(item.get("gateId", "")).strip()
            if not raw_gate_id:
              continue
            friendly_name = get_friendly_gate_name(raw_gate_id)
            operating_time = str(item.get("operatingTime", "") or "정보 없음")
            is_open = is_currently_open(operating_time)
            wait_time = int(item.get("waitTime", 999))
            wait_length = int(item.get("waitLength", 999))

            row_data = {
                "_gate_id": raw_gate_id,
                "검색대 위치": friendly_name,
                "운영 여부": "운영 중" if is_open else "미운영",
                "운영 시간": operating_time,
                "예상 대기시간(분)": wait_time,
                "대기 인원(명)": wait_length,
                "_is_open": is_open,
            }
            valid_items.append(row_data)
            gate_lookup[raw_gate_id] = row_data
          except Exception:
            continue

        if not valid_items:
          st.warning(
              f"유효한 출국장 데이터를 추출하지 못했습니다. 응답 확인: {data}"
          )
        else:
          open_items = [x for x in valid_items if x["_is_open"]]
          target_pool = open_items if open_items else valid_items

          best_gate = min(
              target_pool,
              key=lambda x: (x["예상 대기시간(분)"], x["대기 인원(명)"]),
          )
          recommended_id = best_gate["_gate_id"]

          st.success("실시간 혼잡도 분석 및 추천 출국장 매칭이 완료되었습니다.")

          if not open_items:
            st.info(
                "현재 시간대 운영 중으로 확인된 출국장이 없어 전체 조회"
                " 데이터 기준으로 안내합니다."
            )

          terminal_short = "T1" if t_id == "P01" else "T2"
          gate_display = (
              boarding_gate.strip() if boarding_gate.strip() else "TBD"
          )
          zone_display = zone_no.strip() if zone_no.strip() else "ZONE 1"
          seat_display = seat_no.strip() if seat_no.strip() else "-"

          st.markdown("### BOARDING PASS / 탑승권")

          source_badge_html = f"""
<div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; font-size: 12px; color: #1e3a8a;">
  <div><strong>데이터 출처:</strong> 인천국제공항공사 OpenAPI (<code>getDepartureCongestion</code> · APOC 실시간 연동)</div>
  <div style="font-weight: 600; color: #1d4ed8;">조회 기준 시각: {fetched_at}</div>
</div>
"""
          st.markdown(source_badge_html, unsafe_allow_html=True)

          boarding_pass_html = f"""
<div style="border: 1px solid #cbd5e1; border-radius: 14px; overflow: hidden; background: linear-gradient(135deg, #f8fafc 0%, #ffffff 55%, #eff6ff 100%); color: #0f172a; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="background: linear-gradient(90deg, #0f294a 0%, #1d4ed8 100%); color: #ffffff; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center;">
    <div style="font-weight: 800; letter-spacing: 0.8px; font-size: 15px;">{airline_name} &nbsp;|&nbsp; <span style="font-weight: 500; opacity: 0.9;">{flight_no}</span></div>
    <div style="font-size: 12px; letter-spacing: 1.2px; font-weight: 700; opacity: 0.95;">BOARDING PASS · {terminal_short}</div>
  </div>
  <div style="display: flex; flex-wrap: wrap;">
    <div style="flex: 2.3; min-width: 280px; padding: 18px 20px; border-right: 2px dashed #cbd5e1;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 14px;">
        <div>
          <div style="font-size: 10px; color: #64748b; font-weight: 700; letter-spacing: 0.6px;">PASSENGER NAME / 승객 성명</div>
          <div style="font-size: 17px; font-weight: 800; color: #0f172a; margin-top: 2px;">{passenger_name}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 10px; color: #64748b; font-weight: 700; letter-spacing: 0.6px;">DATE / 탑승일</div>
          <div style="font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 2px;">{flight_date}</div>
        </div>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; background: #f1f5f9; border-radius: 10px; padding: 10px 14px; margin-bottom: 16px;">
        <div>
          <div style="font-size: 10px; color: #64748b; font-weight: 700;">FROM</div>
          <div style="font-size: 15px; font-weight: 800; color: #0f172a;">{origin_port}</div>
        </div>
        <div style="font-size: 16px; font-weight: 800; color: #2563eb;">✈ ──▶</div>
        <div style="text-align: right;">
          <div style="font-size: 10px; color: #64748b; font-weight: 700;">TO</div>
          <div style="font-size: 15px; font-weight: 800; color: #0f172a;">{destination}</div>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px;">
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; background: #ffffff;">
          <div style="font-size: 10px; color: #64748b; font-weight: 700;">DEP TIME / 출발</div>
          <div style="font-size: 20px; font-weight: 900; color: #0f172a; margin-top: 2px;">{departure_time}</div>
        </div>
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; background: #ffffff;">
          <div style="font-size: 10px; color: #64748b; font-weight: 700;">BOARDING / 탑승</div>
          <div style="font-size: 20px; font-weight: 900; color: #1d4ed8; margin-top: 2px;">{boarding_time}</div>
        </div>
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; background: #ffffff;">
          <div style="font-size: 10px; color: #64748b; font-weight: 700;">GATE / 탑승구</div>
          <div style="font-size: 20px; font-weight: 900; color: #0f172a; margin-top: 2px;">{gate_display}</div>
        </div>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 12px; color: #334155; padding-top: 8px; border-top: 1px solid #e2e8f0;">
        <div><strong>CHECK-IN:</strong> {checkin_counter}</div>
        <div><strong>TERMINAL:</strong> {terminal_short}</div>
        <div><strong>SEAT:</strong> {seat_display}</div>
      </div>
    </div>
    <div style="flex: 1; min-width: 190px; padding: 18px 16px; display: flex; flex-direction: column; justify-content: space-between; background: #f8fafc;">
      <div>
        <div style="display: inline-block; background: #dbeafe; color: #1e40af; font-weight: 800; font-size: 12px; padding: 4px 10px; border-radius: 999px; margin-bottom: 12px;">{zone_display}</div>
        <div style="font-size: 10px; color: #64748b; font-weight: 700; letter-spacing: 0.5px;">RECOMMENDED SECURITY</div>
        <div style="font-size: 15px; font-weight: 800; color: #0f766e; margin-top: 3px; line-height: 1.3;">{best_gate['검색대 위치']}</div>
        <div style="font-size: 12px; color: #334155; margin-top: 6px;">예상 대기 <strong>{best_gate['예상 대기시간(분)']}분</strong> · 대기 <strong>{best_gate['대기 인원(명)']}명</strong></div>
      </div>
      <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid #cbd5e1;">
        <div style="height: 28px; background: repeating-linear-gradient(90deg, #0f172a 0px, #0f172a 2px, transparent 2px, transparent 4px, #0f172a 4px, #0f172a 5px, transparent 5px, transparent 8px); border-radius: 3px; opacity: 0.85;"></div>
        <div style="font-size: 10px; color: #64748b; text-align: center; margin-top: 4px; letter-spacing: 1px;">{flight_no} · {flight_date}</div>
      </div>
    </div>
  </div>
</div>
"""

          st.markdown(boarding_pass_html, unsafe_allow_html=True)

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

          st.markdown("### 제1여객터미널 평면도 기반 실시간 현황")
          img_b64 = get_base64_image(FLOORPLAN_PATH)

          gate_coords = {
    "DG1_W": (46, 91.5),
    "DG1_E": (46, 96.5),
    "DG2_W": (33, 81.5),
    "DG2_E": (33, 86.5),
    "DG3_W": (22, 65.5),
    "DG3_E": (22, 70.5),
    "DG4_W": (22, 34.5),
    "DG4_E": (22, 39.5),
    "DG5_W": (33, 18.5),
    "DG5_E": (33, 23.5),
    "DG6_W": (46, 5.5),
    "DG6_E": (46, 10.5),
}


          if img_b64:
            pins_html = "".join(
                render_map_pin(gid, gate_lookup, recommended_id, t, l)
                for gid, (t, l) in gate_coords.items()
            )
            overlay_map_html = (
                '<div style="position:relative; width:100%; border:1px solid'
                " #cbd5e1; border-radius:12px; overflow:hidden;"
                ' background:#ffffff; margin-bottom:12px;">'
                f'<img src="data:image/jpeg;base64,{img_b64}" style="width:100%; display:block;">'
                f"{pins_html}"
                "</div>"
            )
            st.markdown(overlay_map_html, unsafe_allow_html=True)
          else:
            st.info(
                f"평면도 이미지(`{FLOORPLAN_PATH}`)를 저장해 두면 평면도 위에"
                " 실시간 수치가 오버레이됩니다. 아래 우측→좌측(1~6번) 현황"
                " 보드를 함께 확인해 주세요."
            )

          right_to_left_gates = [3, 2, 1, 6, 5, 4]
          gate_blocks_html = []
          for g_num in right_to_left_gates:
            w_id = f"DG{g_num}_W"
            e_id = f"DG{g_num}_E"
            w_cell = render_gate_cell(w_id, gate_lookup, recommended_id)
            e_cell = render_gate_cell(e_id, gate_lookup, recommended_id)
            gate_blocks_html.append(
                '<div style="background:#ffffff; border:1px solid #e2e8f0;'
                ' border-radius:10px; padding:8px;">'
                f'<div style="text-align:center; font-size:12px; font-weight:800; color:#0f294a; margin-bottom:6px;">{g_num}번 출국장</div>'
                f'<div style="display:grid; grid-template-columns:1fr 1fr; gap:5px;">{w_cell}{e_cell}</div>'
                "</div>"
            )

          concourse_map_html = (
              '<div style="border:1px solid #cbd5e1; border-radius:14px;'
              " padding:16px; background:linear-gradient(180deg, #f1f5f9 0%,"
              " #f8fafc 100%); color:#0f172a;"
              " font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI',"
              ' Roboto, sans-serif;">'
              '<div style="display:flex; flex-wrap:wrap;'
              " justify-content:space-between; align-items:center; gap:8px;"
              ' margin-bottom:12px;">'
              '<div style="font-size:13px; font-weight:800;'
              ' color:#0f294a;">3층 출발장 출국장(우측 1번 → 좌측 6번 ·'
              " 서편/동편) 및 체크인(A~N) 구역 안내</div>"
              '<div style="font-size:11px; color:#475569;">표시 형식:'
              " <strong>예상 대기시간 · 대기인원</strong> (미운영 시"
              " <strong>미운영</strong>)</div>"
              "</div>"
              '<div style="display:flex; justify-content:space-between;'
              " font-size:11px; font-weight:800; color:#1e3a8a;"
              ' margin-bottom:6px; padding:0 4px;">'
              "<span>◀ W (서측 · 6~4번)</span>"
              "<span>E (동측 · 3~1번) ▶</span>"
              "</div>"
              '<div style="display:grid; grid-template-columns:repeat(3, 1fr);'
              ' gap:10px; margin-bottom:14px;">'
              + "".join(gate_blocks_html)
              + "</div>"
              '<div style="background:#e2e8f0; border-radius:999px;'
              " padding:8px 14px; display:flex; justify-content:space-between;"
              " align-items:center; font-size:11px; font-weight:700;"
              ' color:#334155;">'
              "<span>N · M · L · K · J · H</span>"
              '<span style="color:#0f294a;">체크인 카운터 라인 (좌 N ← → 우 A)</span>'
              "<span>G · F · E · D · C · B · A</span>"
              "</div>"
              "</div>"
          )
          st.markdown(concourse_map_html, unsafe_allow_html=True)

          with st.expander("실시간 전체 출국장 비교 데이터 보기"):
            display_items = [
                {k: v for k, v in row.items() if not k.startswith("_")}
                for row in valid_items
            ]
            st.dataframe(display_items)

          with st.expander("API 연동 및 원천 응답 확인"):
            st.markdown(
                f"- **데이터 출처:** 인천국제공항공사 OpenAPI"
                f" (`getDepartureCongestion` · APOC 실시간 연동)\n"
                f"- **조회 기준 시각:** `{fetched_at}`\n"
                f"- **요청 엔드포인트:** `{url}`\n"
                f"- **요청 파라미터:** `terminalId={api_terminal_id}`,"
                f" `type=json`, `numOfRows=20`, `pageNo=1`\n"
                f"- **HTTP 응답 상태:** `{status_code}`"
            )
            st.json(items)

  except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
