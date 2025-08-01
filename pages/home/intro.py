import streamlit as st
from PIL import Image

# --- 페이지 설정 ---
st.set_page_config(
    page_title="[lucasoft] | SW 개발 전문",
    page_icon="🚀",  # 이모지는 자유롭게 변경 가능
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.container():
    st.subheader("안녕하세요! 저희는 [루카소프트]입니다.")
    st.title("고객의 아이디어를 현실로 만드는 SW 개발 파트너")
    st.write("웹, 앱, AI 기반 솔루션까지. 비즈니스 성장을 위한 최적의 기술을 제공합니다.")
    st.markdown(
        """
        <div style="margin-top: 20px;">
            <a href="/" target="_self" class="button">서비스 둘러보기</a>
        </div>
        """,
        unsafe_allow_html=True
    )
st.write("---")
left_column, right_column = st.columns(2)
with left_column:
    st.header("우리가 하는 일")
    st.write(
        """
        저희 [루카소프트]는 다년간의 경험을 갖춘 전문가들로 구성된 소프트웨어 개발 회사입니다.
        - **웹/앱 개발**: 최신 기술 스택을 활용한 반응형 웹사이트와 안정적인 모바일 앱을 개발합니다.
        - **AI 솔루션**: 머신러닝, 딥러닝 기술을 활용하여 데이터 기반의 지능형 서비스를 구축합니다.
        - **UI/UX 디자인**: 사용자 중심의 직관적이고 아름다운 디자인을 설계합니다.
        - **클라우드/인프라**: 확장성과 안정성을 고려한 최적의 클라우드 아키텍처를 설계하고 구축합니다.
        
        고객과의 긴밀한 소통을 통해 비즈니스 목표에 정확히 부합하는 결과물을 만들어냅니다.
        """
    )
with right_column:
    st.image(Image.open("pages/home/intro.png"))