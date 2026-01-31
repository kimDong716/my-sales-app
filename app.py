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
        # 데이터 원본 읽기
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
        if df.empty:
            return pd.DataFrame()

        # [수정] 제목줄 자동 검색 최적화
        header_idx = 0
        found = False
        for i in range(min(len(df), 20)):
            row_vals = df.iloc[i].astype(str).tolist()
            # '업체명', '잔고', '일자' 중 하나라도 있으면 제목줄로 간주
            if any(k in "".join(row_vals) for k in ['업체명', '잔고', '일자']):
                header_idx = i
                found = True
                break
        
        if found:
            new_df = df.iloc[header_idx+1:].copy()
            new_df.columns = df.iloc[header_idx].astype(str).str.strip()
        else:
            new_df = df.copy()

        # [수정] 모든 컬럼의 NaN을 빈 문자열로 먼저 치환 (JSON 에러 방지)
        new_df = new_df.astype(str).replace(['nan', 'None', 'NaN', 'NAT'], '')

        # 숫자 변환이 필요한 컬럼 리스트 (시트 제목과 일치해야 함)
        num_cols = ['잔고', '매출', '수금', '회전일 초과 금액', '미수금', '잔액']
        for col in new_df.columns:
            if any(n in col for n in num_cols):
                # 숫자 외 문자 제거 후 변환, 에러시 0
                new_df[col] = pd.to_numeric(new_df[col].str.replace('[^0-9.-]', '', regex=True), errors='coerce').fillna(0)
        
        return new_df.reset_index(drop=True)
    except Exception as e:
        st.error(f"데이터 로드 에러 (ID {worksheet_id}): {e}")
        return pd.DataFrame()

# 데이터 로드
df_summary = load_data("621616384")
df_history = load_data("0")

# --- 스타일 함수 ---
def safe_style_df(df):
    if df.empty: return df
    
    # 1. 배경색 정의
    def apply_bg(x):
        colors = []
        for i in range(len(df.columns)):
            if 0 <= i <= 4: color = 'background-color: #FFEBEE' # 빨강
            elif 5 <= i <= 7: color = 'background-color: #FFFDE7' # 노랑
            else: color = 'background-color: #E3F2FD' # 파랑
            colors.append(color)
        return colors

    # 2. 숫자 형식 지정 (데이터가 실제 숫자인 컬럼만)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    format_dict = {col: "{:,.0f}" for col in numeric_cols}
    
    return df.style.format(format_dict).apply(apply_bg, axis=1)

# --- 메인 UI ---
st.title("💰 거래처 미수금 관리 시스템")

# 1. 상단 지표 (안전하게 계산)
if not df_summary.empty:
    # '잔고'와 '회전일' 단어가 포함된 컬럼 찾기
    bal_cols = [c for c in df_summary.columns if '잔고' in c]
    over_cols = [c for c in df_summary.columns if '회전일' in c and '금액' in c]
    
    val_bal = float(df_summary[bal_cols[0]].sum()) if bal_cols else 0.0
    val_overdue = float(df_summary[over_cols[0]].sum()) if over_cols else 0.0

    col1, col2 = st.columns(2)
    # f-string 포맷팅 전에 반드시 float 형변환 확인
    col1.metric("총 미수금액", f"{val_bal:,.0f}원")
    col2.metric("회전일 초과금액", f"{val_overdue:,.0f}원")

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴", ["전체 현황", "거래처별 상세조회", "신규 입력"])

if menu == "전체 현황":
    st.subheader("📊 전체 거래처 리스트")
    if not df_summary.empty:
        st.dataframe(safe_style_df(df_summary), use_container_width=True)

elif menu == "거래처별 상세조회":
    st.subheader("🔍 거래처별 내역 검색")
    if not df_summary.empty and '업체명' in df_summary.columns:
        # 업체명 리스트 (빈값 제거)
        client_list = sorted([str(c) for c in df_summary['업체명'].unique() if str(c).strip() != ""])
        target = st.selectbox("업체를 선택하세요", ["선택 안 함"] + client_list)
        
        if target != "선택 안 함":
            # 상세내역 필터링
            if not df_history.empty and '업체명' in df_history.columns:
                filtered = df_history[df_history['업체명'].astype(str) == target].copy()
                if not filtered.empty:
                    st.dataframe(safe_style_df(filtered), use_container_width=True)
                else:
                    st.info("거래 내역이 없습니다.")
            else:
                st.error("상세내역 시트의 '업체명' 컬럼을 확인할 수 없습니다.")

elif menu == "신규 입력":
    st.subheader("📝 신규 내역 입력")
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        date = c1.date_input("날짜")
        client = c2.selectbox("업체명", sorted([str(c) for c in df_summary['업체명'].unique() if str(c).strip() != ""]))
        pay_type = c1.radio("구분", ["매출", "수금(카드)", "수금(현금/이체)"], horizontal=True)
        amount = c2.number_input("금액", min_value=0, step=1000)
        memo = st.text_area("비고")
        
        if st.form_submit_button("기록하기 (시뮬레이션)"):
            st.success(f"{client} {pay_type} {amount:,.0f}원 입력 완료!")
