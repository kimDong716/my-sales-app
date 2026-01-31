import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60) # 속도 개선을 위해 1분간 캐시
def load_full_data(worksheet_id):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
        if df.empty: return pd.DataFrame()

        # 데이터 시작 지점(제목줄) 찾기
        header_idx = 0
        for i in range(min(len(df), 20)):
            row_str = df.iloc[i].astype(str).tolist()
            if any(k in "".join(row_str) for k in ['업체명', '상호', '일자', '잔고']):
                header_idx = i
                break
        
        columns = df.iloc[header_idx].astype(str).str.strip().tolist()
        new_df = df.iloc[header_idx+1:].copy()
        new_df.columns = [c if (c and c != 'nan') else f"Col_{i}" for i, c in enumerate(columns)]
        
        return new_df.astype(str).replace(['nan', 'None', 'NaN', 'NaT', ''], '0')
    except Exception as e:
        return pd.DataFrame()

# 데이터 로드
df_summary = load_full_data("621616384")
df_history = load_full_data("0")

# --- 유틸리티 함수 ---
def find_col(df, keywords):
    """키워드가 포함된 실제 컬럼명을 반환"""
    for col in df.columns:
        if any(k in str(col) for k in keywords):
            return str(col)
    return None

def to_num(s):
    """숫자 형식 변환 (문자열 제거)"""
    try:
        return pd.to_numeric(str(s).replace(',', '').replace(' ', '').replace('원', ''), errors='coerce')
    except:
        return 0

# --- 사이드바 메뉴 ---
menu = st.sidebar.radio("메뉴", ["🔍 거래처 검색 및 상세", "📊 전체 현황", "📝 신규 입력/수정"])

# --- 1. 거래처 검색 및 상세조회 ---
if menu == "🔍 거래처 검색 및 상세":
    st.subheader("🔍 거래처 통합 검색")
    search_query = st.text_input("업체명 또는 연락처 뒷번호를 입력하세요").strip()
    
    if not df_summary.empty:
        name_col = find_col(df_summary, ['업체명', '상호'])
        tel_col = find_col(df_summary, ['연락처', '전화', '핸드폰', '휴대폰'])
        
        # 검색 필터
        mask = df_summary[name_col].str.contains(search_query, na=False)
        if tel_col:
            mask |= df_summary[tel_col].str.contains(search_query, na=False)
        
        filtered_summary = df_summary[mask] if search_query else df_summary

        if not filtered_summary.empty:
            target_name = st.selectbox("업체 선택", filtered_summary[name_col].unique())
            info = df_summary[df_summary[name_col] == target_name].iloc[0]
            
            # 상단 정보 박스
            st.markdown(f"### 🏢 {target_name}")
            c1, c2, c3 = st.columns(3)
            # 컬럼명이 '품목' 혹은 '거래내용'일 수 있으므로 유연하게 대처
            c1.info(f"**📝 거래내용**\n\n{info.get(find_col(df_summary, ['거래내용', '품목', '내용']), '정보없음')}")
            c2.info(f"**👤 담당자**\n\n{info.get(find_col(df_summary, ['담당자', '대표', '이름']), '정보없음')}")
            c3.info(f"**📞 연락처**\n\n{info.get(tel_col, '정보없음')}")

            # 월별 요약 계산
            st.divider()
            date_col = find_col(df_history, ['일자', '날짜'])
            hist_name_col = find_col(df_history, ['업체명', '상호'])
            
            if date_col and hist_name_col:
                hist_df = df_history[df_history[hist_name_col] == target_name].copy()
                if not hist_df.empty:
                    # 날짜 변환
                    hist_df[date_col] = pd.to_datetime(hist_df[date_col], errors='coerce')
                    hist_df = hist_df.dropna(subset=[date_col])
                    hist_df['월'] = hist_df[date_col].dt.strftime('%Y-%m')
                    
                    # 수치 데이터 안전하게 변환
                    summary_data = {}
                    for k in ['매출', '수금', '잔액']:
                        actual_col = find_col(hist_df, [k])
                        if actual_col:
                            hist_df[actual_col] = hist_df[actual_col].apply(to_num).fillna(0)
                            summary_data[k] = actual_col
                        else:
                            # 컬럼이 없으면 0으로 채운 가상 컬럼 생성
                            hist_df[k] = 0
                            summary_data[k] = k
                    
                    st.write("#### 📅 월별 실적 요약")
                    # 찾은 실제 컬럼명들을 사용하여 그룹화
                    monthly = hist_df.groupby('월')[[summary_data['매출'], summary_data['수금'], summary_data['잔액']]].sum()
                    st.dataframe(monthly.style.format("{:,.0f}"), use_container_width=True)
                else:
                    st.warning("상세 거래 내역이 없습니다.")
            else:
                st.error("상세 내역 시트 구조를 읽을 수 없습니다.")

# --- 2. 전체 현황 (10행 제한) ---
elif menu == "📊 전체 현황":
    st.subheader("📊 전체 거래처 현황 (상위 10개)")
    if not df_summary.empty:
        # 10개 행만 먼저 보여주기
        st.dataframe(df_summary.head(10), use_container_width=True)
        with st.expander("나머지 전체 리스트 보기"):
            st.dataframe(df_summary, use_container_width=True)

# --- 3. 신규 입력/수정 ---
elif menu == "📝 신규 입력/수정":
    st.warning("⚠️ 실제 구글 시트 저장 기능을 활성화하려면 '서비스 계정 JSON 키' 설정이 필요합니다.")
    st.info("현재는 UI 테스트만 가능합니다.")
    with st.form("input_test"):
        st.text_input("업체명")
        st.number_input("금액", step=1000)
        st.form_submit_button("저장 테스트")
