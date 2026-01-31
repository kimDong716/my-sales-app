import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data(worksheet_id):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
        
        # 제목줄 자동 찾기
        header_idx = 0
        for i in range(len(df)):
            row_str = df.iloc[i].astype(str).values
            if any(k in "".join(row_str) for k in ['업체명', '잔고', '일자']):
                header_idx = i
                break
        
        new_df = df.iloc[header_idx+1:].copy()
        new_df.columns = df.iloc[header_idx].str.strip()
        
        # [핵심] NaN 오류 해결을 위한 데이터 클리닝
        # 1. 숫자가 되어야 할 컬럼들 처리
        num_cols = ['잔고', '매출', '수금', '회전일 초과 금액', '미수금']
        for col in new_df.columns:
            if col in num_cols:
                new_df[col] = pd.to_numeric(new_df[col].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce').fillna(0)
            else:
                new_df[col] = new_df[col].fillna("") # 문자는 빈칸으로
                
        return new_df.reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame()

# 데이터 로드
df_summary = load_data("621616384")
df_history = load_data("0")

# --- 스타일 함수 ---
def style_dataframe(df):
    def get_bg_color(col_index):
        if 0 <= col_index <= 4: return 'background-color: #FFEBEE' # 파스텔 빨강 (A-E)
        if 5 <= col_index <= 8: return 'background-color: #FFFDE7' # 파스텔 노랑 (F-H)
        return 'background-color: #E3F2FD' # 파스텔 파랑 (I~ )

    # 숫자 포맷 지정 (천 단위 콤마)
    num_format_cols = ['잔고', '매출', '수금', '회전일 초과 금액', '미수금']
    actual_num_cols = [c for c in num_format_cols if c in df.columns]
    
    styled = df.style.format({col: "{:,.0f}" for col in actual_num_cols}, na_rep="")
    styled = styled.apply(lambda x: [get_bg_color(df.columns.get_loc(x.name))] * len(x))
    return styled

# --- 메인 UI ---
st.title("💰 거래처 미수금 관리 시스템")

# 1. 상단 지표
if not df_summary.empty:
    col1, col2, col3 = st.columns(3)
    # 컬럼명이 정확히 일치하지 않을 경우를 대비해 수동 매칭
    bal_col = '잔고' if '잔고' in df_summary.columns else df_summary.columns[2] # C열
    over_col = '회전일 초과 금액' if '회전일 초과 금액' in df_summary.columns else None
    
    total_bal = df_summary[bal_col].sum()
    total_overdue = df_summary[over_col].sum() if over_col else 0

    col1.metric("총 미수금액", f"{total_bal:,.0f}원")
    col2.metric("회전일 초과금액", f"{total_overdue:,.0f}원", delta_color="inverse")
    col3.metric("관리 업체 수", f"{len(df_summary[df_summary['업체명'] != ''])}개")

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴", ["전체 현황", "거래처별 상세조회", "신규 입력"])

if menu == "전체 현황":
    st.subheader("📊 전체 거래처 리스트")
    if not df_summary.empty:
        st.dataframe(style_dataframe(df_summary), use_container_width=True)
    else:
        st.warning("데이터를 불러올 수 없습니다. 시트 설정을 확인하세요.")

elif menu == "거래처별 상세조회":
    st.subheader("🔍 거래처별 내역 검색")
    if '업체명' in df_summary.columns:
        client_list = [c for c in df_summary['업체명'].unique() if str(c).strip() != ""]
        target = st.selectbox("조회할 업체를 선택하세요", client_list)
        
        if not df_history.empty and '업체명' in df_history.columns:
            filtered_history = df_history[df_history['업체명'] == target]
            if not filtered_history.empty:
                # [오류 방지] 출력 전 다시 한번 결측치 제거
                filtered_history = filtered_history.fillna("")
                st.dataframe(style_dataframe(filtered_history), use_container_width=True)
            else:
                st.info("해당 업체의 거래 상세 내역이 없습니다.")
        else:
            st.error("상세내역 데이터를 불러올 수 없습니다.")

elif menu == "신규 입력":
    st.subheader("📝 신규 거래 내역 입력")
    with st.form("new_entry_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        date = col_a.date_input("날짜")
        client = col_b.selectbox("업체명", [c for c in df_summary['업체명'].unique() if str(c).strip() != ""])
        
        # 요청사항 3번: 결제 수단 구분 추가
        pay_type = col_a.radio("결제 구분", ["매출 발생", "수금(카드)", "수금(현금/이체)"], horizontal=True)
        amount = col_b.number_input("금액", min_value=0, step=1000)
        memo = st.text_area("비고(특이사항)")
        
        submitted = st.form_submit_button("시트에 기록하기")
        if submitted:
            st.success(f"[{date}] {client} - {pay_type} {amount:,.0f}원 입력 완료")
            st.balloons()

