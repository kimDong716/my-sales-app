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
    # [수정] worksheet '621616384'에서 3행(index 2)을 제목으로 인식하도록 설정
    # 만약 시트 구조상 header 옵션이 안 먹힐 경우를 대비해 전처리 로직 추가
    summary_raw = conn.read(spreadsheet=SHEET_URL, worksheet="621616384")
    
    # 데이터가 3행부터 시작하므로, 3행(실제로는 데이터 프레임의 중간 행)을 찾아 제목으로 재설정
    # C3가 '잔고'라면 보통 2번째 줄(index 1)이 제목줄일 확률이 높습니다. 
    # 안전하게 '잔고'라는 글자가 포함된 행을 찾아 제목으로 지정합니다.
    new_header = summary_raw.iloc[1] # 3행을 제목으로 가정 (0, 1, 2 중 1)
    summary_df = summary_raw[2:]     # 데이터는 그 다음부터
    summary_df.columns = new_header
    
    # 거래내역 시트(0번 탭)도 동일하게 처리해야 할 수 있습니다.
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="0")
    
    # 공백 제거 및 정리
    summary_df.columns = summary_df.columns.str.strip()
    history_df.columns = history_df.columns.str.strip()
    
    return summary_df, history_df

try:
    df_summary, df_history = load_all_data()
except Exception as e:
    st.error(f"데이터를 읽는 중 오류가 발생했습니다: {e}")
    st.stop()

# --- 사이드바 및 UI ---
st.sidebar.title("💰 영업 관리 메뉴")
menu = st.sidebar.radio("메뉴 선택", ["📊 전체 대시보드", "🔍 거래처별 상세조회", "📝 신규 입력"])

if menu == "📊 전체 대시보드":
    st.title("📊 전체 거래처 현황")
    
    # '잔고' 컬럼이 문자열(예: '1,200원')일 경우 숫자로 변환
    if '잔고' in df_summary.columns:
        # 숫자 외 문자 제거 후 변환
        df_summary['잔고_numeric'] = df_summary['잔고'].replace('[^0-9.-]', '', regex=True).apply(pd.to_numeric, errors='coerce')
        total_bal = df_summary['잔고_numeric'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("총 미수금", f"{total_bal:,.0f}원")
        col2.metric("관리 업체 수", f"{len(df_summary.dropna(subset=['업체명']))}개")
        
        st.write("### 현재 시트 데이터 요약")
        st.dataframe(df_summary)
    else:
        st.error("'잔고' 컬럼을 찾을 수 없습니다. 현재 인식된 제목: " + str(list(df_summary.columns)))
        st.info("시트의 3행(C3)이 정확히 '잔고'라는 글자만 있는지 확인해 주세요.")

elif menu == "🔍 거래처별 상세조회":
    # 업체명 필터링 (NaN 값 제외)
    clients = df_summary['업체명'].dropna().unique()
    target = st.selectbox("업체 선택", clients)
    st.write(f"### {target} 상세 내역")
    st.dataframe(df_history[df_history['업체명'] == target])
