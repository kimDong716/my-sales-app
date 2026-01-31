import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 통합 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_all_data():
    # 621616384는 '업체별현황' 시트의 GID입니다.
    summary_df = conn.read(spreadsheet=SHEET_URL, worksheet="621616384")
    # 0은 '거래내역' 시트의 GID입니다.
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="0")
    
    # [핵심 수정] 컬럼 이름 양옆의 공백을 강제로 제거합니다. ('잔고 ' -> '잔고')
    summary_df.columns = summary_df.columns.str.strip()
    history_df.columns = history_df.columns.str.strip()
    
    return summary_df, history_df

try:
    df_summary, df_history = load_all_data()
except Exception as e:
    st.error(f"시트 연결 실패: {e}")
    st.stop()

# --- 사이드바 메뉴 ---
st.sidebar.title("💰 영업 관리 메뉴")
menu = st.sidebar.radio(
    "이동할 화면을 선택하세요",
    ["📊 전체 대시보드", "🔍 거래처별 상세조회", "📝 신규 내역 입력", "🏢 거래처 정보 관리"]
)

# --- [1] 전체 대시보드 ---
if menu == "📊 전체 대시보드":
    st.title("📊 전체 거래처 현황")
    
    # 컬럼이 존재하는지 확인 후 계산 (KeyError 방지)
    if '잔고' in df_summary.columns:
        total_bal = pd.to_numeric(df_summary['잔고'], errors='coerce').sum()
        overdue_bal = pd.to_numeric(df_summary['회전일 초과 금액'], errors='coerce').sum() if '회전일 초과 금액' in df_summary.columns else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 미수금", f"{total_bal:,.0f}원")
        col2.metric("회전일 초과액", f"{overdue_bal:,.0f}원")
        col3.metric("관리 업체 수", f"{len(df_summary)}개")
    else:
        st.error("시트에서 '잔고' 컬럼을 찾을 수 없습니다. 시트의 제목 줄을 확인해주세요.")
        # 디버깅용: 실제 읽어온 컬럼명 표시
        st.write("현재 시트 컬럼명:", list(df_summary.columns))

    st.subheader("🏢 업체별 현황 요약")
    st.dataframe(df_summary, use_container_width=True)

# --- [2] 거래처별 상세조회 ---
elif menu == "🔍 거래처별 상세조회":
    st.title("🔍 거래처별 상세 내역")
    if '업체명' in df_summary.columns:
        selected_client = st.selectbox("업체를 선택하세요", df_summary['업체명'].unique())
        client_history = df_history[df_history['업체명'] == selected_client]
        st.write(f"### {selected_client} 거래 기록")
        st.dataframe(client_history, use_container_width=True)
    else:
        st.error("'업체명' 컬럼을 찾을 수 없습니다.")

# --- [3] 신규 내역 입력 ---
elif menu == "📝 신규 내역 입력":
    st.title("📝 내역 입력")
    st.warning("이 기능은 구글 시트 쓰기 권한(Service Account) 설정이 추가로 필요합니다. 현재는 입력 UI만 제공됩니다.")
    with st.form("input_form"):
        st.date_input("일자")
        st.selectbox("업체명", df_summary['업체명'].unique() if '업체명' in df_summary.columns else ["데이터 없음"])
        st.number_input("금액", min_value=0)
        st.text_area("비고")
        st.form_submit_button("저장하기")

# --- [4] 거래처 정보 관리 ---
elif menu == "🏢 거래처 정보 관리":
    st.title("🏢 거래처 정보 및 특이사항")
    st.write("아래 표에서 직접 수정이 가능합니다 (앱 내부용)")
    st.data_editor(df_summary, use_container_width=True)
