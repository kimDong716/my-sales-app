import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="거래처 관리 시스템", layout="wide")

st.title("📊 거래처 거래내역 및 미수금 현황")

# 데이터 불러오기 (실제로는 구글 시트 API나 CSV 연결)
# 여기서는 예시를 위해 시트 구조를 바탕으로 데이터를 생성합니다.
@st.cache_data
def load_data():
    # 실제 연동 시: df = pd.read_csv("your_google_sheet_url")
    data = {
        '업체명': ['인터페이스', '의료법인삼광의료재단', '(주)삼구아이앤씨'],
        '잔고': [1500000000, 1304689660, 1000000000],
        '기준 회전일': ['즉시', '90일', '즉시'],
        '회전일 초과 금액': [1500000000, 1132033410, 1000000000]
    }
    return pd.DataFrame(data)

df = load_data()

# 상단 요약 카드
col1, col2, col3 = st.columns(3)
col1.metric("총 잔고", f"{df['잔고'].sum():,}원")
col2.metric("최대 미수 업체", df.iloc[df['잔고'].idxmax()]['업체명'])
col3.metric("관리 업체 수", f"{len(df)}개")

# 상세 데이터 표
st.subheader("업체별 현황")
st.dataframe(df, use_container_width=True)

# 업체별 검색 필터
st.sidebar.header("필터링")
target_client = st.sidebar.selectbox("조회할 업체를 선택하세요", df['업체명'].unique())
client_info = df[df['업체명'] == target_client]
st.write(f"### {target_client} 상세 정보", client_info)