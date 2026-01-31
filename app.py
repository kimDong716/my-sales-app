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
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_id)
        if df.empty: return pd.DataFrame()

        # 제목줄 찾기
        header_idx = 0
        for i in range(min(len(df), 20)):
            row_vals = df.iloc[i].astype(str).tolist()
            if any(k in "".join(row_vals) for k in ['업체명', '잔고', '일자', '품목']):
                header_idx = i
                break
        
        new_df = df.iloc[header_idx+1:].copy()
        new_df.columns = df.iloc[header_idx].astype(str).str.strip()
        
        # NaN 처리 및 숫자 변환
        new_df = new_df.astype(str).replace(['nan', 'None', 'NaN', 'NaT'], '')
        num_cols = ['매출', '수금', '잔액', '잔고', '미수금', '회전일 초과 금액']
        
        for col in new_df.columns:
            if any(n in col for n in num_cols):
                new_df[col] = pd.to_numeric(new_df[col].str.replace('[^0-9.-]', '', regex=True), errors='coerce').fillna(0)
        
        return new_df.reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame()

df_summary = load_data("621616384")
df_history = load_data("0")

# --- 메인 UI ---
st.title("💰 거래처 미수금 관리 시스템")

menu = st.sidebar.radio("메뉴", ["전체 현황", "거래처별 상세조회", "신규 입력"])

if menu == "전체 현황":
    st.subheader("📊 전체 거래처 리스트")
    # 기존 스타일링 코드 적용 (생략 가능하나 이전과 동일하게 유지)
    st.dataframe(df_summary, use_container_width=True)

elif menu == "거래처별 상세조회":
    st.subheader("🔍 거래처별 정보 및 월별 통계")
    
    if not df_summary.empty and '업체명' in df_summary.columns:
        client_list = sorted([str(c) for c in df_summary['업체명'].unique() if str(c).strip() != ""])
        target = st.selectbox("업체를 선택하세요", ["선택하세요"] + client_list)
        
        if target != "선택하세요":
            # 1. 상단 업체 기본 정보 표시
            client_info = df_summary[df_summary['업체명'] == target].iloc[0]
            
            st.markdown(f"### 🏢 {target} 정보")
            info_col1, info_col2, info_col3 = st.columns(3)
            
            with info_col1:
                st.info(f"**📦 주요 품목**\n\n{client_info.get('품목', '정보 없음')}")
            with info_col2:
                st.info(f"**👤 담당자**\n\n{client_info.get('담당자', '정보 없음')}")
            with info_col3:
                st.info(f"**📞 연락처**\n\n{client_info.get('연락처', '정보 없음')}")
            
            st.divider()

            # 2. 하단 월별 기준 매출액/수금액/잔액 표시
            if not df_history.empty and '업체명' in df_history.columns:
                filtered = df_history[df_history['업체명'].astype(str) == target].copy()
                
                if not filtered.empty:
                    # 일자 컬럼을 날짜 형식으로 변환
                    filtered['일자'] = pd.to_datetime(filtered['일자'], errors='coerce')
                    filtered = filtered.dropna(subset=['일자']) # 날짜 없는 데이터 제외
                    
                    # '월' 컬럼 생성 (YYYY-MM)
                    filtered['월'] = filtered['일자'].dt.strftime('%Y-%m')
                    
                    # 월별 그룹화 (매출, 수금, 잔액 합계)
                    # 시트 컬럼명에 따라 '매출', '수금', '잔액'이 정확히 있어야 합니다.
                    group_cols = [c for c in ['매출', '수금', '잔액'] if c in filtered.columns]
                    monthly_summary = filtered.groupby('월')[group_cols].sum().reset_index()
                    
                    st.write("#### 📅 월별 실적 요약")
                    st.dataframe(
                        monthly_summary.style.format({c: "{:,.0f}" for c in group_cols}),
                        use_container_width=True
                    )
                    
                    with st.expander("전체 거래 내역 보기"):
                        st.dataframe(filtered.astype(str), use_container_width=True)
                else:
                    st.warning("해당 업체의 거래 상세 내역이 없습니다.")
            else:
                st.error("상세내역 시트(GID: 0)를 로드할 수 없거나 '업체명' 컬럼이 없습니다.")

elif menu == "신규 입력":
    st.subheader("📝 신규 내역 입력")
    # (기존 입력 폼 유지)
    st.info("입력 기능 구현 준비 중입니다.")
