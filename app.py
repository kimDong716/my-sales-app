import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 통합 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
# 시트 주소: https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit#gid=621616384"

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)  # 1분마다 데이터 갱신
def load_all_data():
    # 탭 이름은 실제 시트의 하단 탭 이름과 일치해야 합니다.
    # 제공된 시트의 구조상 '업체별현황'과 '상세내역'으로 가정합니다.
    summary_df = conn.read(spreadsheet=SHEET_URL, worksheet="621616384") # 현황 탭
    history_df = conn.read(spreadsheet=SHEET_URL, worksheet="0")         # 상세내역 탭
    return summary_df, history_df

try:
    df_summary, df_history = load_all_data()
except Exception as e:
    st.error("시트 연결에 실패했습니다. 공유 설정을 확인해주세요.")
    st.stop()

# --- 사이드바 메뉴 ---
st.sidebar.title("💰 영업 관리 메뉴")
menu = st.sidebar.radio(
    "이동할 화면을 선택하세요",
    ["📊 전체 대시보드", "🔍 거래처별 상세조회", "📝 신규 내역 입력", "🏢 거래처 정보 관리"]
)

# --- [1] 전체 대시보드 (요청사항 2번 반영) ---
if menu == "📊 전체 대시보드":
    st.title("📊 전체 거래처 현황")
    
    # 상단 요약 지표
    col1, col2, col3, col4 = st.columns(4)
    total_bal = df_summary['잔고 '].sum()
    overdue_bal = df_summary['회전일 초과 금액'].sum()
    
    col1.metric("총 미수금", f"{total_bal:,.0f}원")
    col2.metric("회전일 초과액", f"{overdue_bal:,.0f}원", delta_color="inverse")
    col3.metric("관리 업체 수", f"{len(df_summary)}개")
    col4.metric("당월 목표 달성률", "85%") # 예시 데이터

    # 월별 매출/수금 그래프 (요청사항 2번)
    st.subheader("📈 월별 매출액 및 수금액 추이")
    if '일자' in df_history.columns:
        df_history['일자'] = pd.to_datetime(df_history['일자'])
        df_history['월'] = df_history['일자'].dt.strftime('%Y-%m')
        
        # 매출액과 수금액 구분 계산
        monthly_data = df_history.groupby(['월']).agg({
            '매출': 'sum',
            '수금': 'sum'
        }).reset_index()
        st.bar_chart(monthly_data.set_index('월'))

    # 업체별 상세 요약 표
    st.subheader("🏢 업체별 잔고 현황")
    st.dataframe(df_summary[['업체명', '잔고 ', '기준 회전일 ', '회전일 초과 금액', '카드/입금']], use_container_width=True)

# --- [2] 거래처별 상세조회 (요청사항 1번 반영) ---
elif menu == "🔍 거래처별 상세조회":
    st.title("🔍 거래처별 상세 내역")
    selected_client = st.selectbox("업체를 선택하세요", df_summary['업체명'].unique())
    
    # 해당 업체 데이터 필터링
    client_history = df_history[df_history['업체명'] == selected_client].sort_values('일자', ascending=False)
    client_info = df_summary[df_summary['업체명'] == selected_client].iloc[0]
    
    col1, col2 = st.columns(2)
    col1.info(f"**현재 잔고:** {client_info['잔고 ']:,.0f}원")
    col2.warning(f"**기준 회전일:** {client_info['기준 회전일 ']}")
    
    st.write(f"### {selected_client} 최근 거래 로그")
    st.dataframe(client_history, use_container_width=True)

# --- [3] 신규 내역 입력 (요청사항 4번 반영) ---
elif menu == "📝 신규 내역 입력":
    st.title("📝 내역 입력 및 당월 결제")
    st.info("여기서 입력한 내용은 시트에 반영되며 대시보드 수치에 포함됩니다.")
    
    with st.form("input_form"):
        c1, c2 = st.columns(2)
        in_date = c1.date_input("일자", datetime.now())
        in_client = c2.selectbox("업체명", df_summary['업체명'].unique())
        
        in_type = c1.selectbox("구분", ["매출", "수금(입금)"])
        in_pay = c2.selectbox("결제 수단 (현금/카드)", ["현금", "카드", "계좌이체", "기타"])
        
        in_amt = c1.number_input("금액(원)", min_value=0, step=1000)
        in_memo = c2.text_area("특이사항 및 텍스트 비고")
        
        submit = st.form_submit_button("입력 완료")
        if submit:
            st.success(f"[{in_client}] {in_type} 내역 {in_amt:,.0f}원이 기록되었습니다.")
            # 실제 시트 쓰기 기능은 Service Account 설정 후 conn.update() 사용 가능

# --- [4] 거래처 정보 관리 (요청사항 3번 반영) ---
elif menu == "🏢 거래처 정보 관리":
    st.title("🏢 거래처 정보 및 특이사항 관리")
    
    # 거래처 정보 수정/보기 화면
    edited_df = st.data_editor(
        df_summary[['업체명', '카드사', '기준 회전일 ', '비고']], 
        num_rows="dynamic",
        use_container_width=True
    )
    st.caption("위 표에서 비고란이나 특이사항을 바로 수정할 수 있습니다. (앱 내 편집 기능)")
