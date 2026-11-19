import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# 페이지 디자인 설정
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
FLOORPLAN_PATH = "assets/t1_floorplan.jpg"

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


# 제1여객터미널 출국장(1~6번) 게이트 코드를 OpenAPI 명세서 기준 한글 이름으로 매칭하는 함수
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
  return gate_map.get(gate_id
