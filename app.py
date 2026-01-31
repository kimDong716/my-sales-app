import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data(worksheet_id):
    try:
        # 데이터를 읽어옴
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
        
        # 제목줄(Header) 자동 찾기 로직
        header_idx = 0
        for i in range(min(len(df), 10)):  # 상위 10줄 내에서 검색
            row_values = df.iloc[i].astype(str).tolist()
            if any(k in "".join(row_values) for k in ['업체명', '잔고', '일자']):
                header_idx = i
                break
        
        # 헤더 아래부터 데이터 추출 및 컬럼명 재설정
        new_df = df.iloc[header_idx+1:].copy()
        new_df.columns = df.iloc[header_idx].astype(str).str.strip()
        
        # [중요] NaN 결측치를 데이터 타입별로 완전 제거
        # 1. 숫자가 포함될 가능성이 있는 컬럼 리스트
        potential_nums = ['잔고', '매출', '수금', '회전일 초과 금액', '미수금', '잔액']
        
        for col in new_df.columns:
            if col in potential_nums:
                # 숫자 외 문자 제거 후 숫자로 변환, 실패시 0
                new_df[col] = pd.to_numeric(new_df[col].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce').fillna(0)
            else:
                # 문자는 빈 문자열로 채움 (NaN 방지)
                new_df[col] = new_df[col].astype(str).replace(['nan', 'None', 'NaN'], '')
        
        return new_df.reset_index(drop=True)
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        return pd.DataFrame()

# 데이터 로드
df_summary = load_data("621616384")
df_history = load_data("0")

# --- 스타일 함수 (JSON 에러 방지용) ---
def safe_style_df(df):
    if df.empty: return df
    
    # 배경색 지정 로직
    def apply_bg(x):
        colors = []
        for i, col in enumerate(df.columns):
            if 0 <= i <= 4: color = 'background-color: #FFEBEE' # 파스텔 빨강
            elif 5 <= i <= 7: color = 'background-color: #FFFDE7' # 파스텔 노랑
            else: color = 'background-color: #E3F2FD' # 파스텔 파랑
            colors.append(color)
        return colors

    # 숫자 컬럼만 골라내기
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # 스타일 적용 및 결측치 문자열 처리
    return df.style.format({col: "{:,.0f}" for col in numeric_cols}, na_rep="") \
                   .apply(apply_bg, axis=1)

# --- 메인 UI ---
st.title("💰 거래처 미수금 관리 시스템")

# 1. 상단 지표
if not df_summary.empty:
    col1, col2 = st.columns(2)
    
    # 컬럼명이 정확하지 않을 수 있어 '잔고'가 들어간 컬럼을 찾음
    bal_col = [c for c in df_summary.columns if '잔고' in c]
    over_col = [c for c in df_summary.columns if '회전일' in c]
    
    total_bal = df_summary[bal_col[0]].sum() if bal_col else 0
    total_overdue = df_summary[over_col[0]].sum() if over_col else 0

    col1.metric("총 미수금액", f"{total_bal:,.0f}원")
    col2.metric("회전일 초과금액", f"{total_overdue:,.0f}원")

# 메뉴 선택
menu = st.sidebar.radio("메뉴", ["전체 현황", "거래처별 상세조회", "신규 입력"])

if menu == "전체 현황":
    st.subheader("📊 전체 거래처 리스트")
    if not df_summary.empty:
        st.dataframe(safe_style_df(df_summary), use_container_width=True)

elif menu == "거래처별 상세조회":
    st.subheader("🔍 거래처별 내역 검색")
    if not df_summary.empty and '업체명' in df_summary.columns:
        # 빈 업체명 제외하고 리스트업
        client_list = [c for c in df_summary['업체명'].unique() if str(c).strip() != ""]
        target = st.selectbox("조회할 업체를 선택하세요", ["업체를 선택하세요"] + client_list)
        
        if target != "업체를 선택하세요" and not df_history.empty:
            # 상세내역에서 선택한 업체만 필터링
            filtered = df_history[df_history['업체명'] == target].copy()
            if not filtered.empty:
                st.dataframe(safe_style_df(filtered), use_container_width=True)
            else:
                st.info("해당 업체의 상세 거래 내역이 없습니다.")

elif menu == "신규 입력":
    st.subheader("📝 신규 내역 입력")
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        date = c1.date_input("날짜")
        client = c2.selectbox("업체명", [c for c in df_summary['업체명'].unique() if str(c).strip() != ""])
        pay_type = c1.radio("구분", ["매출", "수금(카드)", "수금(현금/이체)"], horizontal=True)
        amount = c2.number_input("금액", min_value=0, step=1000)
        memo = st.text_area("비고")
        
        if st.form_submit_button("입력 완료"):
            st.success(f"{client} - {pay_type} {amount:,.0f}원 저장 시뮬레이션 성공!")
