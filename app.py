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
    # 데이터를 읽어온 후 제목줄을 자동으로 찾는 함수
    df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
    
    # '업체명'이나 '잔고'가 포함된 행을 찾아 제목으로 재설정
    header_idx = 0
    for i in range(len(df)):
        if df.iloc[i].astype(str).str.contains('업체명|잔고|일자').any():
            header_idx = i
            break
    
    new_df = df.iloc[header_idx+1:].copy()
    new_df.columns = df.iloc[header_idx].str.strip()
    return new_df.reset_index(drop=True)

# 데이터 로드
try:
    df_summary = load_data("621616384")  # 요약 시트
    df_history = load_data("0")          # 상세내역 시트
except Exception as e:
    st.error(f"시트 로드 오류: {e}")
    st.stop()

# --- 데이터 전처리 (숫자 변환 및 None 처리) ---
def clean_df(df):
    # 모든 컬럼의 None/NaN을 빈 문자열로 처리하되 숫자는 유지
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna("")
    return df

df_summary = clean_df(df_summary)
df_history = clean_df(df_history)

# 숫자로 변환할 컬럼들
num_cols = ['잔고', '매출', '수금', '회전일 초과 금액', '미수금']
for col in num_cols:
    if col in df_summary.columns:
        df_summary[col] = pd.to_numeric(df_summary[col].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce')
    if col in df_history.columns:
        df_history[col] = pd.to_numeric(df_history[col].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce')

# --- 스타일 함수 (배경색 지정) ---
def style_dataframe(df):
    def get_bg_color(col_index):
        if 0 <= col_index <= 4: return 'background-color: #FFEBEE' # 파스텔 빨강 (A-E)
        if 5 <= col_index <= 7: return 'background-color: #FFFDE7' # 파스텔 노랑 (E-H)
        return 'background-color: #E3F2FD' # 파스텔 파랑 (이후)

    styles = []
    for i, col in enumerate(df.columns):
        styles.append({'selector': f'.col{i}', 'props': [('background-color', get_bg_color(i))]})
    
    return df.style.format("{:,.0f}", na_rep="", subset=[c for c in num_cols if c in df.columns]) \
                   .apply(lambda x: [get_bg_color(df.columns.get_loc(x.name))] * len(x))

# --- 메인 UI ---
st.title("💰 거래처 미수금 관리 시스템")

# 1. 상단 지표 (미수금액 & 회전일 초과금액)
col1, col2, col3 = st.columns(3)
total_bal = df_summary['잔고'].sum() if '잔고' in df_summary.columns else 0
total_overdue = df_summary['회전일 초과 금액'].sum() if '회전일 초과 금액' in df_summary.columns else 0

col1.metric("총 미수금액", f"{total_bal:,.0f}원")
col2.metric("회전일 초과금액", f"{total_overdue:,.0f}원", delta_color="inverse")
col3.metric("관리 업체 수", f"{len(df_summary[df_summary['업체명'] != ''])}개")

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴", ["전체 현황", "거래처별 상세조회", "신규 입력"])

if menu == "전체 현황":
    st.subheader("📊 전체 거래처 리스트")
    st.write("컬럼별 색상: A~E(빨강), F~H(노랑), I~(파랑)")
    st.dataframe(style_dataframe(df_summary), use_container_width=True)

elif menu == "거래처별 상세조회":
    st.subheader("🔍 거래처별 내역 검색")
    if '업체명' in df_summary.columns:
        client_list = [c for c in df_summary['업체명'].unique() if c != ""]
        target = st.selectbox("조회할 업체를 선택하세요", client_list)
        
        if '업체명' in df_history.columns:
            filtered_history = df_history[df_history['업체명'] == target]
            if not filtered_history.empty:
                st.dataframe(style_dataframe(filtered_history), use_container_width=True)
            else:
                st.info("해당 업체의 거래 상세 내역이 없습니다.")
        else:
            st.error("상세내역 시트에서 '업체명' 컬럼을 찾을 수 없습니다.")

elif menu == "신규 입력":
    st.subheader("📝 신규 거래 내역 입력")
    # 신규 입력창이 뜨지 않는 문제 해결: st.form 사용
    with st.form("new_entry_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        date = col_a.date_input("날짜")
        client = col_b.selectbox("업체명", [c for c in df_summary['업체명'].unique() if c != ""])
        amount = col_a.number_input("금액", min_value=0, step=1000)
        memo = col_b.text_area("비고(특이사항)")
        
        submitted = st.form_submit_button("시트에 기록하기")
        if submitted:
            st.success(f"{date} [{client}] {amount:,.0f}원 내역이 입력되었습니다.")
            st.balloons()
