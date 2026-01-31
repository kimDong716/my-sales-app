import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 (캐시 최적화) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600) # 10분간 캐시 유지하여 속도 향상
def load_full_data(worksheet_id):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
        # 데이터가 시작되는 헤더 행 자동 찾기
        header_idx = 0
        for i in range(min(len(df), 20)):
            row = df.iloc[i].astype(str).tolist()
            if any(k in "".join(row) for k in ['업체명', '잔고', '일자', '전화']):
                header_idx = i
                break
        df.columns = df.iloc[header_idx].str.strip()
        df = df.iloc[header_idx+1:].reset_index(drop=True)
        return df.replace(['nan', 'None', 'NaN'], '')
    except:
        return pd.DataFrame()

# 데이터 로드
df_summary = load_full_data("621616384")
df_history = load_full_data("0")

# --- 유틸리티 함수: 컬럼명 매칭 ---
def find_col(df, keywords):
    for col in df.columns:
        if any(k in col for k in keywords):
            return col
    return None

# --- 사이드바 메뉴 ---
menu = st.sidebar.radio("메뉴", ["🔍 거래처 검색 및 상세", "📊 전체 현황", "📝 신규 입력/수정"])

# --- 1. 거래처 검색 및 상세조회 ---
if menu == "🔍 거래처 검색 및 상세":
    st.subheader("🔍 거래처 통합 검색")
    
    search_query = st.text_input("업체명 또는 연락처 뒷번호를 입력하세요")
    
    if not df_summary.empty:
        # 검색 필터링
        name_col = find_col(df_summary, ['업체명', '상호'])
        tel_col = find_col(df_summary, ['연락처', '전화', '핸드폰'])
        
        filtered_summary = df_summary[
            df_summary[name_col].str.contains(search_query) | 
            df_summary[tel_col].str.contains(search_query)
        ] if search_query else df_summary

        if not filtered_summary.empty:
            target_name = st.selectbox("상세 조회할 업체를 선택하세요", filtered_summary[name_col].tolist())
            
            # 업체 상세 정보
            info = df_summary[df_summary[name_col] == target_name].iloc[0]
            
            st.markdown(f"### 🏢 {target_name} 상세 정보")
            c1, c2, c3 = st.columns(3)
            c1.info(f"**📝 거래내용**\n\n{info.get('품목', info.get('거래내용', '정보없음'))}")
            c2.info(f"**👤 담당자**\n\n{info.get('담당자', '정보없음')}")
            c3.info(f"**📞 연락처**\n\n{info.get(tel_col, '정보없음')}")

            # 월별 통계 로직 (오류 방지형)
            st.divider()
            date_col = find_col(df_history, ['일자', '날짜'])
            hist_name_col = find_col(df_history, ['업체명', '상호'])
            
            if date_col and hist_name_col:
                hist_df = df_history[df_history[hist_name_col] == target_name].copy()
                if not hist_df.empty:
                    hist_df[date_col] = pd.to_datetime(hist_df[date_col], errors='coerce')
                    hist_df = hist_df.dropna(subset=[date_col])
                    hist_df['월'] = hist_df[date_col].dt.strftime('%Y-%m')
                    
                    # 숫자 변환
                    for c in ['매출', '수금', '잔액']:
                        target_c = find_col(hist_df, [c])
                        if target_c:
                            hist_df[target_c] = pd.to_numeric(hist_df[target_c].astype(str).str.replace('[^0-9.-]', '', regex=True), errors='coerce').fillna(0)
                    
                    st.write("#### 📅 월별 실적 요약")
                    monthly = hist_df.groupby('월').sum(numeric_only=True)
                    st.dataframe(monthly.style.format("{:,.0f}"), use_container_width=True)
                else:
                    st.warning("상세 거래 내역이 없습니다.")
            else:
                st.error("상세 내역 시트에서 '일자' 컬럼을 찾을 수 없습니다.")

# --- 2. 전체 현황 (생략 - 기존 스타일링 유지) ---
elif menu == "📊 전체 현황":
    st.subheader("📊 전체 현황")
    st.dataframe(df_summary, use_container_width=True)

# --- 3. 신규 입력 및 수정 ---
elif menu == "📝 신규 입력/수정":
    tab1, tab2 = st.tabs(["🆕 신규 업체 등록", "✏️ 기존 업체 수정"])
    
    with tab1:
        with st.form("new_client"):
            st.write("새로운 거래처를 등록합니다.")
            new_name = st.text_input("업체명*")
            new_item = st.text_input("거래내용")
            new_boss = st.text_input("담당자")
            new_tel = st.text_input("연락처")
            if st.form_submit_button("등록 요청"):
                st.info("구글 시트 쓰기 권한 설정이 필요합니다. 입력하신 데이터: " + new_name)

    with tab2:
        if not df_summary.empty:
            edit_target = st.selectbox("수정할 업체", df_summary[find_col(df_summary, ['업체명'])].tolist())
            with st.form("edit_client"):
                # 기존 데이터 불러오기 시뮬레이션
                st.text_input("업체명", value=edit_target)
                st.text_input("거래내용(수정)")
                st.form_submit_button("수정 완료")
