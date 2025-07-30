import streamlit as st

st.set_page_config(page_title="문의하기", page_icon="📧", layout="wide")

st.title("프로젝트 문의하기 📧")
st.write("---")
st.write("아이디어를 현실로 만들 준비가 되셨나요? 저희에게 연락주시면, 빠른 시일 내에 답변드리겠습니다.")

# Formsubmit.co를 이용한 문의 폼
contact_form = """
<style>
input[type=text], input[type=email] {
  width: 100%;
  padding: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  margin-top: 6px;
  margin-bottom: 16px;
  resize: vertical;
}
textarea {
  width: 100%;
  height: 200px;
  padding: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  margin-top: 6px;
  margin-bottom: 16px;
  resize: vertical;
}

button[type=submit] {
  background-color: #007BFF; /* 주요 색상 */
  color: white;
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  width: 100%;
}

button[type=submit]:hover {
  background-color: #0056b3;
}</style>
<form action="https://formsubmit.co/hkskyp@gmail.com" method="POST">
    <input type="hidden" name="_captcha" value="false">
    <input type="text" name="name" placeholder="성함" required>
    <input type="email" name="email" placeholder="이메일 주소" required>
    <textarea name="message" placeholder="문의하실 내용을 입력해주세요." required></textarea>
    <button type="submit">보내기</button>
</form>
"""

st.markdown(contact_form, unsafe_allow_html=True)