import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

# --- 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YD0AolMY-Ed6vNogf3L04OuaLV3RFLbJxHEd56UISzE/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 데이터 로드 ---
def load_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name)
        if df.empty:
            return pd.DataFrame()

        # 헤더 자동 탐색
        header_row = 0
        for i in range(min(len(df), 20)):
            if df.iloc[i].notna().any():
                header_row = i
                break

        df.columns = df.iloc[header_row].astype(str).str.strip()
        df = df.iloc[header_row + 1:].reset_index(drop=True)

        return df.astype(str).replace(['nan', 'None', 'NaN', 'NaT'], '').fillna('')
    except Exception as e:
        st.error(f"❌ 시트 로드 오류 ({worksheet_name}) : {e}")
        return pd.DataFrame()

# 시트 이름 기준 (권장)
df_summary = load_data("요약")
df_history = load_data("거래내역")

# --- 유틸 함수 ---
def find_col(df, keywords):
    for col in df.columns:
        if any(k in col for k in keywords):
            return col
    return None

def require_col(col, msg):
    if not col:
        st.error(f"❌ {msg}")
        st.stop()

# --- 사이드바 ---
st.sidebar.title("📊 관리 메뉴")
menu = st.sidebar.radio(
    "이동할 페이지",
    ["🔍 거래처 검색 및 상세", "📅 전체 현황 리스트", "✍️ 거래내역 입력", "⚙️ 거래처 정보 관리"]
)

# ==============================
# 1. 거래처 상세 조회
# ==============================
if menu == "🔍 거래처 검색 및 상세":
    st.subheader("🔍 거래처 상세 조회")

    if df_summary.empty:
        st.warning("거래처 데이터가 없습니다.")
        st.stop()

    name_col = find_col(df_summary, ['업체명', '상호'])
    status_col = find_col(df_summary, ['상태', '비고', '구분'])

    require_col(name_col, "업체명 컬럼을 찾을 수 없습니다.")

    active_df = df_summary.copy()
    if status_col:
        active_df = active_df[
            ~active_df[status_col].str.strip().str.contains('종료|중단', regex=True)
        ]

    if active_df.empty:
        st.warning("활성 거래처가 없습니다.")
        st.stop()

    target_name = st.selectbox(
        "거래처를 선택하세요",
        ["선택하세요"] + sorted(active_df[name_col].unique())
    )

    if target_name != "선택하세요":
        matched = active_df[active_df[name_col] == target_name]
        if matched.empty:
            st.warning("해당 거래처 정보를 찾을 수 없습니다.")
            st.stop()

        info = matched.iloc[0]

        content_col = find_col(df_summary, ['내용', '품목', '거래내용'])
        manager_col = find_col(df_summary, ['담당자', '대표', '성함'])
        phone_col = find_col(df_summary, ['연락처', '전화', '휴대폰'])

        st.markdown(f"### 🏢 {target_name} 기본 정보")
        c1, c2, c3 = st.columns(3)

        c1.info(f"**📝 주요 거래내용**\n\n{info.get(content_col, '정보없음')}")
        c2.info(f"**👤 담당자**\n\n{info.get(manager_col, '정보없음')}")
        c3.info(f"**📞 연락처**\n\n{info.get(phone_col, '정보없음')}")

        st.divider()
        st.write("#### 📜 거래 내역")

        hist_name_col = find_col(df_history, ['업체명', '상호'])
        if hist_name_col:
            hist = df_history[df_history[hist_name_col] == target_name]
            if hist.empty:
                st.info("거래 내역이 없습니다.")
            else:
                st.dataframe(hist, use_container_width=True)

# ==============================
# 2. 전체 현황
# ==============================
elif menu == "📅 전체 현황 리스트":
    st.subheader("📅 전체 거래처 현황")

    if df_summary.empty:
        st.warning("데이터가 없습니다.")
        st.stop()

    show_all = st.checkbox("종료/중단 업체 포함", value=False)
    display_df = df_summary.copy()

    status_col = find_col(display_df, ['상태', '비고', '구분'])
    if status_col and not show_all:
        display_df = display_df[
            ~display_df[status_col].str.strip().str.contains('종료|중단', regex=True)
        ]

    st.dataframe(display_df, use_container_width=True)

# ==============================
# 3. 거래내역 입력
# ==============================
elif menu == "✍️ 거래내역 입력":
    st.subheader("✍️ 거래 내역 입력")

    if df_summary.empty:
        st.warning("거래처 정보가 없습니다.")
        st.stop()

    name_col = find_col(df_summary, ['업체명', '상호'])
    require_col(name_col, "업체명 컬럼이 필요합니다.")

    with st.form("history_form"):
        c1, c2 = st.columns(2)
        target = c1.selectbox("업체명", sorted(df_summary[name_col].unique()))
        date = c2.date_input("거래일자", datetime.now())
        amount = c1.number_input("금액", step=1000)
        memo = c2.text_input("적요")

        if st.form_submit_button("입력"):
            st.success(f"✅ {target} / {amount:,.0f}원 입력 완료 (시뮬레이션)")
            st.info("※ 실제 저장은 서비스 계정 설정 후 가능합니다.")

# ==============================
# 4. 거래처 관리
# ==============================
elif menu == "⚙️ 거래처 정보 관리":
    st.subheader("⚙️ 거래처 관리")

    if df_summary.empty:
        st.warning("거래처 데이터가 없습니다.")
        st.stop()

    name_col = find_col(df_summary, ['업체명', '상호'])
    require_col(name_col, "업체명 컬럼을 찾을 수 없습니다.")

    t1, t2 = st.tabs(["🆕 신규 등록", "✏️ 수정 / 종료"])

    with t1:
        with st.form("add_client"):
            st.text_input("업체명 *")
            st.text_input("담당자")
            st.text_input("연락처")
            st.text_area("거래 내용")
            if st.form_submit_button("등록"):
                st.success("신규 거래처 등록 완료 (시뮬레이션)")

    with t2:
        edit_name = st.selectbox("업체 선택", df_summary[name_col].unique())
        target_row = df_summary[df_summary[name_col] == edit_name].iloc[0]

        with st.form("update_client"):
            st.text_input("담당자", value=target_row.get(find_col(df_summary, ['담당자']), ''))
            st.text_input("연락처", value=target_row.get(find_col(df_summary, ['연락처']), ''))

            status_col = find_col(df_summary, ['상태', '비고', '구분'])
            current_status = target_row.get(status_col, '')
            end_flag = st.checkbox("거래 종료", value=('종료' in current_status))

            if st.form_submit_button("수정"):
                st.warning(f"'{edit_name}' 정보 수정 처리됨 (시뮬레이션)")
