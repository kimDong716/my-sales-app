import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 (캐시 최적화) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def load_full_data(worksheet_id):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
        if df.empty: return pd.DataFrame()

        # 제목줄 찾기: '업체명'이나 '일자'가 포함된 행을 찾음
        header_idx = 0
        for i in range(min(len(df), 20)):
            row_str = df.iloc[i].astype(str).tolist()
            if any(k in "".join(row_str) for k in ['업체명', '상호', '일자', '잔고']):
                header_idx = i
                break
        
        # 컬럼명 설정 및 데이터 정리
        columns = df.iloc[header_idx].astype(str).str.strip().tolist()
        new_df = df.iloc[header_idx+1:].copy()
        new_df.columns = columns
        
        # [중요] 컬럼명 자체에 NaN이 섞여있을 경우 처리
        new_df.columns = [c if c != 'nan' else f"Unknown_{i}" for i, c in enumerate(new_df.columns)]
        
        return new_df.astype(str).replace(['nan', 'None', 'NaN'], '')
    except Exception as e:
        st.error(f"데이터 로드 실패 (ID: {worksheet_id}): {e}")
        return pd.DataFrame()

# 데이터 로드
df_summary = load_full_data("621616384")
df_history = load_full_data("0")

# --- 유틸리티 함수 (TypeError 방지용) ---
def find_col(df, keywords):
    for col in df.columns:
        col_str = str(col) # 강제 문자열 변환
        if any(k in col_str for k in keywords):
            return col_str
    return None

# --- 사이드바 메뉴 ---
menu = st.sidebar.radio("메뉴", ["🔍 거래처 검색 및 상세", "📊 전체 현황", "📝 신규 입력/수정"])

# --- 1. 거래처 검색 및 상세조회 ---
if menu == "🔍 거래처 검색 및 상세":
    st.subheader("🔍 거래처 통합 검색")
    search_query = st.text_input("업체명 또는 연락처 뒷번호를 입력하세요").strip()
    
    if not df_summary.empty:
        name_col = find_col(df_summary, ['업체명', '상호'])
        tel_col = find_col(df_summary, ['연락처', '전화', '핸드폰'])
        
        # 검색 필터링
        mask = df_summary[name_col].str.contains(search_query, na=False)
        if tel_col:
            mask |= df_summary[tel_col].str.contains(search_query, na=False)
        
        filtered_summary = df_summary[mask] if search_query else df_summary

        if not filtered_summary.empty:
            target_name = st.selectbox("상세 조회할 업체를 선택하세요", filtered_summary[name_col].unique())
            
            # 업체 상세 정보 (Summary 시트에서 추출)
            info = df_summary[df_summary[name_col] == target_name].iloc[0]
            
            st.markdown(f"### 🏢 {target_name} 상세 정보")
            c1, c2, c3 = st.columns(3)
            # 정보 매칭 (컬럼명이 정확하지 않아도 키워드로 매칭)
            c1.info(f"**📝 거래내용**\n\n{info.get('거래내용', info.get('품목', '정보없음'))}")
            c2.info(f"**👤 담당자**\n\n{info.get('담당자', '정보없음')}")
            c3.info(f"**📞 연락처**\n\n{info.get(tel_col, '정보없음') if tel_col else '정보없음'}")

            # 월별 통계 (History 시트에서 추출)
            st.divider()
            date_col = find_col(df_history, ['일자', '날짜'])
            hist_name_col = find_col(df_history, ['업체명', '상호'])
            
            if date_col and hist_name_col:
                hist_df = df_history[df_history[hist_name_col] == target_name].copy()
                if not hist_df.empty:
                    hist_df[date_col] = pd.to_datetime(hist_df[date_col], errors='coerce')
                    hist_df = hist_df.dropna(subset=[date_col])
                    hist_df['월'] = hist_df[date_col].dt.strftime('%Y-%m')
                    
                    # 숫자 변환 및 합산
                    for c in ['매출', '수금', '잔액']:
                        target_c = find_col(hist_df, [c])
                        if target_c:
                            hist_df[target_c] = pd.to_numeric(hist_df[target_c].str.replace('[^0-9.-]', '', regex=True), errors='coerce').fillna(0)
                    
                    st.write("#### 📅 월별 실적 요약")
                    monthly = hist_df.groupby('월')[['매출', '수금', '잔액']].sum(numeric_only=True)
                    st.dataframe(monthly.style.format("{:,.0f}"), use_container_width=True)
                else:
                    st.warning("상세 거래 내역이 없습니다.")
            else:
                st.error("상세 내역 시트의 구조를 파악할 수 없습니다. ('일자' 컬럼 확인)")

# --- 2. 전체 현황 (10행 제한) ---
elif menu == "📊 전체 현황":
    st.subheader("📊 전체 거래처 요약 (상위 10개)")
    if not df_summary.empty:
        # 10번 열까지만 보여주기 (컬럼 슬라이싱)
        display_df = df_summary.iloc[:10, :].reset_index(drop=True)
        st.dataframe(display_df, use_container_width=True)
        
        with st.expander("전체 리스트 보기"):
            st.dataframe(df_summary, use_container_width=True)
    else:
        st.warning("데이터가 없습니다.")

# --- 3. 신규 입력 (생략 - 이전 폼 유지) ---
elif menu == "📝 신규 입력/수정":
    st.info("실제 시트 저장 기능은 서비스 계정 설정 후 활성화됩니다.")
