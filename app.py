import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data(worksheet_id):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=str(worksheet_id))
        if df.empty: return pd.DataFrame()
        
        # 제목줄 자동 찾기 (데이터가 있는 첫 행)
        header_row = 0
        for i in range(min(len(df), 20)):
            if df.iloc[i].notna().any():
                header_row = i
                break
        
        df.columns = df.iloc[header_row].astype(str).str.strip()
        df = df.iloc[header_row+1:].reset_index(drop=True)
        # 모든 데이터를 문자열로 변환하되, 'nan'은 빈칸으로 처리
        return df.astype(str).replace(['nan', 'None', 'NaN', 'NaT'], '')
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        return pd.DataFrame()

# 데이터 로드
df_summary = load_data("621616384") 
df_history = load_data("0")

# --- 유틸리티 함수 ---
def find_col(df, keywords):
    for col in df.columns:
        if any(k in str(col) for k in keywords):
            return str(col)
    return None

# --- 사이드바 메뉴 ---
st.sidebar.title("📊 관리 메뉴")
menu = st.sidebar.radio("이동할 페이지", ["🔍 거래처 검색 및 상세", "📅 전체 현황 리스트", "✍️ 거래내역 입력", "⚙️ 거래처 정보 관리"])

# --- 1. 거래처 검색 및 상세조회 ---
if menu == "🔍 거래처 검색 및 상세":
    st.subheader("🔍 거래처 상세 조회")
    
    if not df_summary.empty:
        name_col = find_col(df_summary, ['업체명', '상호'])
        status_col = find_col(df_summary, ['상태', '비고', '구분'])
        
        # '종료'된 업체 제외 리스트 생성
        active_df = df_summary.copy()
        if status_col:
            active_df = active_df[~active_df[status_col].str.contains('종료|중단', na=False)]

        target_name = st.selectbox("거래처를 선택하세요", ["선택하세요"] + list(active_df[name_col].unique()))
        
        if target_name != "선택하세요":
            # 업체 상세 정보 매칭
            info = active_df[active_df[name_col] == target_name].iloc[0]
            
            st.markdown(f"### 🏢 {target_name} 기본 정보")
            c1, c2, c3 = st.columns(3)
            
            # 유연한 컬럼 매칭
            content_col = find_col(df_summary, ['내용', '품목', '거래내용'])
            manager_col = find_col(df_summary, ['담당자', '대표', '성함'])
            phone_col = find_col(df_summary, ['연락처', '전화', '핸드폰', '휴대폰'])
            
            c1.info(f"**📝 주요 거래내용**\n\n{info.get(content_col, '정보없음')}")
            c2.info(f"**👤 담당자**\n\n{info.get(manager_col, '정보없음')}")
            c3.info(f"**📞 연락처**\n\n{info.get(phone_col, '정보없음')}")

            # 상세 거래 내역
            st.divider()
            st.write("#### 📜 해당 업체 거래 기록")
            hist_name_col = find_col(df_history, ['업체명', '상호'])
            if hist_name_col:
                personal_hist = df_history[df_history[hist_name_col] == target_name]
                if not personal_hist.empty:
                    st.dataframe(personal_hist, use_container_width=True)
                else:
                    st.write("기록된 거래 내역이 없습니다.")

# --- 2. 전체 현황 (제한 없음) ---
elif menu == "📅 전체 현황 리스트":
    st.subheader("📅 전체 거래처 현황")
    show_all = st.checkbox("거래 종료/중단 업체 포함하기", value=False)
    
    display_df = df_summary.copy()
    status_col = find_col(display_df, ['상태', '비고', '구분'])
    
    if not show_all and status_col:
        # 종료/중단 글자가 포함되지 않은 행만 필터링
        display_df = display_df[~display_df[status_col].str.contains('종료|중단', na=False)]
    
    st.dataframe(display_df, use_container_width=True)

# --- 3. 거래내역 입력 ---
elif menu == "✍️ 거래내역 입력":
    st.subheader("✍️ 새로운 거래 내역 기록")
    if not df_summary.empty:
        with st.form("history_input"):
            c1, c2 = st.columns(2)
            name_col = find_col(df_summary, ['업체명', '상호'])
            target = c1.selectbox("업체명", df_summary[name_col].unique())
            date = c2.date_input("거래일자", datetime.now())
            amount = c1.number_input("금액(원)", step=1000)
            memo = c2.text_input("거래 상세 내용 (적요)")
            
            if st.form_submit_button("내역 서버 전송"):
                st.success(f"✅ {target} / {amount:,.0f}원 입력 시뮬레이션 완료")
                st.info("실제 시트 저장은 서비스 계정 설정이 필요합니다.")

# --- 4. 거래처 정보 관리 (추가/수정/종료) ---
elif menu == "⚙️ 거래처 정보 관리":
    st.subheader("⚙️ 거래처 마스터 관리")
    t1, t2 = st.tabs(["🆕 신규 거래처 등록", "✏️ 정보 수정 및 거래 종료"])
    
    with t1:
        with st.form("add_client"):
            st.text_input("업체명(상호) *")
            st.text_input("담당자 성함")
            st.text_input("연락처")
            st.text_area("주요 거래 품목/내용")
            if st.form_submit_button("거래처 등록"):
                st.info("신규 거래처 정보가 입력되었습니다.")
                
    with t2:
        if not df_summary.empty:
            name_col = find_col(df_summary, ['업체명', '상호'])
            edit_name = st.selectbox("수정할 업체를 선택하세요", df_summary[name_col].unique())
            target_row = df_summary[df_summary[name_col] == edit_name].iloc[0]
            
            with st.form("update_client"):
                st.text_input("담당자 변경", value=str(target_row.get(find_col(df_summary, ['담당자']), '')))
                st.text_input("연락처 변경", value=str(target_row.get(find_col(df_summary, ['연락처']), '')))
                
                status_col = find_col(df_summary, ['상태', '비고', '구분'])
                current_status = str(target_row.get(status_col, ''))
                is_end = st.checkbox("거래 종료 (체크 시 리스트에서 숨김)", value=('종료' in current_status))
                
                if st.form_submit_button("정보 업데이트 확인"):
                    st.warning(f"'{edit_name}' 업체의 정보를 변경합니다.")
                    
