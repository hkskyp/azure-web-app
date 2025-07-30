import streamlit as st

# --- 페이지 설정 ---
st.set_page_config(
    page_title="[lucasoft] | SW 개발 전문",
    page_icon="🚀",  # 이모지는 자유롭게 변경 가능
    layout="wide",
    initial_sidebar_state="expanded",  # 사이드바를 기본적으로 펼친 상태로 설정
)

pg = st.navigation(
    {
        "Home": [
            st.Page("home/intro.py", title="Home", icon="🏠"),
            st.Page("home/contact.py", title="Contact", icon="📧")
        ],
        "Developer":[
            st.Page("float-bits.py", title="IEEE 754 Floating Point Bit Representation Analyzer", icon="🔢"),
            st.Page("coordinate-converter.py", title="Geographic Coordinate Converter", icon="🗺️")
        ]
    }
)

pg.run()