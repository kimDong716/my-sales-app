import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10) # 실시간 반영을 위해 캐시 시간 단축
def load_data(worksheet_id):
    try:
        # worksheet_id가 문자열이면 그대로 사용, 숫자면 변환
        df = conn.read(spreadsheet=SHEET_URL, worksheet=str(worksheet_id))
        if df.empty: return pd.DataFrame()
        
        # 제목줄(Header) 자동 찾기: 데이터가 실제 시작되는 행을 찾음
        header_row = 0
        for i in range(len(df)):
            if df.iloc[i].notna().any():
                header_row = i
                break
        
        df.columns = df.iloc[header_row].astype(str).str.strip()
        df = df.iloc[header_row+1:].reset_index(drop=True)
        return df.fillna('')
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        return pd.DataFrame()

# 데이터 로드
df_summary = load_data("621616384") # Summary 시트
df_history = load_data("0")         # History 시트

# --- 유틸리티 함수 ---
def find_col(df, keywords):
    for col in df.columns:
        if any(k in str(col) for k in keywords):
            return col
    return None

# --- 사이드바 메뉴 ---
menu = st.sidebar.radio("메뉴", ["🔍 거래처 검색 및 상세", "📊 전체 현황", "✍️ 거래내역 입력", "⚙️ 거래처 추가 및 수정"])

# --- 1. 거래처 검색 및 상세조회 ---
if menu == "🔍 거래처 검색 및 상세":
    st.subheader("🔍 거래처 상세 조회")
    
    if not df_summary.empty:
        # '거래종료'가 아닌 업체만 필터링 (비고 또는 상태 열 기준)
        status_col = find_col(df_summary, ['상태', '비고', '구분'])
        active_df = df_summary.copy()
        if status_col:
            active_df = active_df[~active_df[status_col].str.contains('종료|중단', na=False)]

        name_col = find_col(active_df, ['업체명', '상호'])
        target_name = st.selectbox("거래처를 선택하세요", ["선택하세요"] + list(active_df[name_col].unique()))
        
        if target_name != "선택하세요":
            # 업체 상세 정보 (Summary에서 추출)
            info = active_df[active_df[name_col] == target_name].iloc[0]
            
            st.markdown(f"### 🏢 {target_name} 상세 정보")
            c1, c2, c3 = st.columns(3)
            
            # 실제 시트 컬럼명에 맞춰 매칭 (주요내용, 담당자, 연락처)
            content_col = find_col(df_summary, ['내용', '품목', '거래내용'])
            manager_col = find_col(df_summary, ['담당자', '대표', '성함'])
            phone_col = find_col(df_summary, ['연락처', '전화', '핸드폰'])
            
            c1.info(f"**📝 주요 거래내용**\n\n{info.get(content_col, '정보없음')}")
            c2.info(f"**👤 담당자**\n\n{info.get(manager_col, '정보없음')}")
            c3.info(f"**📞 연락처**\n\n{info.get(phone_col, '정보없음')}")

            # 상세 거래 내역 (History에서 추출)
            st.divider()
            st.write("#### 📅 최근 거래 내역")
            hist_name_col = find_col(df_history, ['업체명', '상호'])
            if hist_name_col:
                personal_hist = df_history[df_history[hist_name_col] == target_name]
                st.dataframe(personal_hist, use_container_width=True)

# --- 2. 전체 현황 (10행 제한 삭제) ---
elif menu == "📊 전체 현황":
    st.subheader("📊 전체 거래처 현황")
    # '거래종료' 업체 제외 옵션
    show_all = st.checkbox("거래 종료된 업체도 포함해서 보기", value=False)
    
    display_df = df_summary.copy()
    status_col = find_col(display_df, ['상태', '비고', '구분'])
    
    if not show_all and status_col:
        display_df = display_df[~display_df[status_col].str.
