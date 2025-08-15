import streamlit as st
import requests
import pandas as pd
import json
import base64
import time
from io import BytesIO

# 페이지 설정
st.set_page_config(
    page_title="AI 독서 문제 생성기",
    page_icon="📚",
    layout="wide"
)

# n8n webhook URL 설정
N8N_BASE_URL = "https://juyeon.app.n8n.cloud/webhook"  # 여기에 실제 n8n URL 입력
POLL_INTERVAL_SEC = 3       # 폴링 주기(초)
POLL_MAX_WAIT_SEC = 600     # 최대 대기(초) — 10분

# 세션 상태 초기화
if 'uploaded_books' not in st.session_state:
    st.session_state.uploaded_books = []
if 'generated_questions' not in st.session_state:
    st.session_state.generated_questions = []
if 'ns_map' not in st.session_state:
    st.session_state.ns_map = {}

# CSS 스타일
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .success-message {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        color: #155724;
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.title("📚 AI 독서 문제 생성기")
st.markdown("---")

# 사이드바
with st.sidebar:
    st.header("📖 업로드된 책 목록")
    if st.session_state.uploaded_books:
        for book in st.session_state.uploaded_books:
            st.write(f"• {book}")
    else:
        st.write("아직 업로드된 책이 없습니다.")

# 메인 컨텐츠
tab1, tab2, tab3 = st.tabs(["📤 책 업로드", "📝 문제 생성", "📊 생성된 문제"])

# 탭 1: 책 업로드
with tab1:
    st.header("1단계: 책 파일 업로드")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader(
            "PDF 또는 Word 파일을 선택하세요",
            type=['pdf', 'docx'],
            help="최대 파일 크기: 200MB"
        )
        
    with col2:
        book_title_kr = st.text_input("책 제목 (한글)", placeholder="예: 가방 들어주는 아이")
        book_title_en = st.text_input("책 제목 (영문)", placeholder="예: bag_carrying_child")
        
    if st.button("📚 책 업로드", disabled=not (uploaded_file and book_title_kr and book_title_en)):
        with st.spinner("책을 업로드하고 처리 중입니다..."):
            try:
                # 파일을 base64로 인코딩
                file_bytes = uploaded_file.read()
                file_b64 = base64.b64encode(file_bytes).decode()
                
                # n8n webhook 호출
                response = requests.post(
                    f"{N8N_BASE_URL}/book-upload",
                    json={
                        "file": file_b64,
                        "filename": uploaded_file.name,
                        "bookTitleKr": book_title_kr,
                        "bookTitleEn": book_title_en
                    },
                    timeout=1200  # 20분 타임아웃
                )
                
                if response.status_code == 200:
                    st.success(f"✅ '{book_title_kr}' 업로드 완료!")
                    st.session_state.uploaded_books.append(book_title_kr)
                    st.session_state.ns_map[book_title_kr] = book_title_en  # 🔥 이 줄 추가
                    st.balloons()
                else:
                    st.error(f"❌ 업로드 실패: {response.text}")
                    
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")

# 탭 2: 문제 생성
with tab2:
    st.header("2단계: 문제 생성")

    col1, col2, col3, col4 = st.columns(4)  # 3을 4로 변경

    with col1:
        selected_book = st.selectbox(
            "책 선택",
            options=st.session_state.uploaded_books,
            disabled=len(st.session_state.uploaded_books) == 0
        )

    with col2:
        category = st.selectbox(
            "문제 카테고리",
            options=["전체 (50문항)", "이해", "사고", "표현", "논리적 사고", "어휘"]
        )

    with col3:
        if category == "전체 (50문항)":
            question_count = 50
            st.info("전체 카테고리: 50문항")
        else:
            question_count = st.number_input(
                "문제 개수",
                min_value=1,
                max_value=20,
                value=10
            )

    with col4:
     difficulty_range = st.selectbox(
        "난이도 범위",
        options=["전체 (1-5점)", "쉬움 (1-2점)", "보통 (3점)", "어려움 (4-5점)"]
    )        

    # ⬇️ 이 블록을 tab2 내부(여기)로 들여쓰기!
    if st.button("🎯 문제 생성", disabled=not selected_book):
        with st.spinner(f"'{selected_book}'에서 {category} 문제 {question_count}개를 생성 중입니다..."):
            try:
                payload = {
                    "bookTitleKr": selected_book,
                    "bookTitleEn": st.session_state.ns_map.get(
                        selected_book, 
                        selected_book.replace(" ", "_").lower()
                    ),
                    "category": category if category != "전체 (50문항)" else "all",
                    "questionCount": question_count,
                    "difficultyRange": difficulty_range
                }

                resp = requests.post(
                    f"{N8N_BASE_URL}/generate-questions",
                    json=payload,
                    timeout=600
                )

                if resp.status_code == 202:
                    ack = resp.json()
                    job_id = ack.get("jobId")
                    if not job_id:
                        st.error("❌ jobId가 없습니다. n8n 응답을 확인하세요.")
                        st.stop()

                    st.info("문제를 생성 중입니다... (최대 10분)")
                    start = time.time()

                    while True:
                        try:
                            r = requests.get(
                                f"{N8N_BASE_URL}/job-result",
                                params={"jobId": job_id},
                                timeout=15
                            )
                            if r.status_code == 200:
                                data = r.json()
                                if data.get("status") == "done":
                                    questions = data.get("questions", [])
                                    if not questions:
                                        st.error("❌ 생성 결과가 비어 있습니다.")
                                        break

                                    st.session_state.generated_questions = questions
                                    st.success(f"✅ {len(questions)}개 문제 생성 완료!")

                                    st.subheader("📋 생성된 문제 미리보기")
                                    with st.expander("첫 3개 문제 보기"):
                                        for i, q in enumerate(questions[:3]):
                                            st.write(f"**문제 {i+1}. [{q.get('category','')}][{q.get('difficulty','')}]**")
                                            st.write(q.get('question',''))
                                            st.write(f"(A) {q.get('choiceA','')}")
                                            st.write(f"(B) {q.get('choiceB','')}")
                                            st.write(f"(C) {q.get('choiceC','')}")
                                            st.write("---")
                                    break

                            if time.time() - start > POLL_MAX_WAIT_SEC:
                                st.error("⏳ 대기 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
                                break
                            time.sleep(POLL_INTERVAL_SEC)

                        except Exception:
                            if time.time() - start > POLL_MAX_WAIT_SEC:
                                st.error("⏳ 대기 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
                                break
                            time.sleep(POLL_INTERVAL_SEC)

                elif resp.status_code == 200:
                    result = resp.json()
                    if isinstance(result, dict) and result.get('success'):
                        questions = result.get('questions', [])
                    elif isinstance(result, list):
                        questions = result
                    else:
                        questions = [result] if result else []

                    if questions:
                        # parse_error 처리 추가
                        if questions and len(questions) > 0 and 'parse_error' in str(questions[0].get('category', '')):
                            # explanation 필드에서 실제 문제 텍스트 가져오기
                            raw_text = questions[0].get('explanation', '')
                            st.warning("⚠️ 문제 파싱 중 오류가 발생했습니다. 원본 텍스트를 표시합니다.")
                            
                            # 원본 텍스트 표시
                            with st.expander("생성된 문제 원본 보기"):
                                st.text(raw_text)
                            
                            # 간단한 파싱 시도 (선택사항)
                            # 여기서 간단한 문제 추출 로직을 추가할 수 있습니다
                            st.info("문제가 생성되었으나 형식 변환 중 오류가 발생했습니다. n8n 워크플로우의 'question parsing' 노드를 확인해주세요.")
                        else:
                            # 정상적으로 파싱된 경우
                            st.session_state.generated_questions = questions
                            st.success(f"✅ {len(questions)}개 문제 생성 완료!")
                            
                            # 미리보기
                            st.subheader("📋 생성된 문제 미리보기")
                            with st.expander("첫 3개 문제 보기"):
                                for i, q in enumerate(questions[:3]):
                                    st.write(f"**문제 {i+1}. [{q.get('category','')}][{q.get('difficulty','')}]**")
                                    st.write(q.get('question',''))
                                    st.write(f"(A) {q.get('choiceA','')}")
                                    st.write(f"(B) {q.get('choiceB','')}")
                                    st.write(f"(C) {q.get('choiceC','')}")
                                    st.write("---")
                    else:
                        st.error("❌ 문제가 생성되지 않았습니다. 다시 시도해주세요.")
                else:
                    st.error(f"❌ 문제 생성 실패: {resp.text}")

            except requests.exceptions.Timeout:
                st.error("❌ 최초 요청이 타임아웃되었습니다. 잠시 후 다시 시도해주세요.")
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")

# 탭 3: 생성된 문제
with tab3:
    st.header("3단계: 생성된 문제 확인 및 다운로드")
    
    if st.session_state.generated_questions:
        # 데이터프레임 생성
        df = pd.DataFrame(st.session_state.generated_questions)
        
        # 통계 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 문제 수", len(df))
        with col2:
            if 'category' in df.columns:
                st.metric("카테고리 수", df['category'].nunique())
        with col3:
            if 'difficulty' in df.columns:
                try:
                    avg_difficulty = df['difficulty'].str.extract('(\d)').astype(float).mean().round(1)
                    st.metric("평균 난이도", avg_difficulty)
                except:
                    st.metric("평균 난이도", "N/A")
        
        # 문제 테이블 표시
        st.subheader("📊 문제 목록")
        st.dataframe(df, use_container_width=True)
        
        # 다운로드 버튼
        col1, col2 = st.columns(2)
        
        with col1:
            # Excel 다운로드
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='문제')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Excel 다운로드",
                data=excel_data,
                file_name=f"문제_{selected_book}_{category}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with col2:
            # CSV 다운로드
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"문제_{selected_book}_{category}.csv",
                mime="text/csv"
            )
    else:
        st.info("아직 생성된 문제가 없습니다. '문제 생성' 탭에서 문제를 생성해주세요.")

# 푸터
st.markdown("---")
st.markdown("Made with using Streamlit & n8n by Jo")