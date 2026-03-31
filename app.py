import streamlit as st
import pandas as pd
import random
import os

# --- [설정] 페이지 레이아웃 및 디자인 ---
st.set_page_config(page_title="형사법 기출 연습 (2021-2026)", layout="wide", page_icon="⚖️")

# CSS: 문제 박스 가독성 및 버튼 색상 최적화
st.markdown("""
    <style>
    /* 문제 박스: 배경은 밝게, 글자는 무조건 검정색 */
    .question-box {
        background-color: #f1f3f5;
        color: #000000 !important;
        padding: 25px;
        border-radius: 12px;
        border-left: 8px solid #2e7d32;
        margin-bottom: 25px;
        font-size: 1.2rem;
        font-weight: 500;
        line-height: 1.6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* 버튼: 깔끔한 다크 모드 스타일 (글자는 흰색) */
    .stButton>button {
        height: 3.5em;
        font-size: 18px !important;
        font-weight: bold !important;
        color: #ffffff !important; /* 글자색 흰색 고정 */
        background-color: #262730;
        border-radius: 10px;
        border: 1px solid #454754;
        transition: 0.2s;
    }
    
    .stButton>button:hover {
        background-color: #3d3f4b;
        border-color: #4CAF50;
    }
    
    /* 강조 텍스트 */
    .highlight {
        color: #2e7d32;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 로직] ---
def load_selected_data(years):
    combined_df = pd.DataFrame()
    for year in years:
        filename = f"{year}.csv"
        if os.path.exists(filename):
            try:
                # 엑셀 저장용 utf-8-sig 및 일반 utf-8 모두 대응
                df = pd.read_csv(filename, encoding='utf-8-sig')
                df['연도'] = f"{year}년"
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            except:
                df = pd.read_csv(filename, encoding='utf-8')
                df['연도'] = f"{year}년"
                combined_df = pd.concat([combined_df, df], ignore_index=True)
    return combined_df

# --- [세션 상태 초기화] ---
if 'wrong_notes' not in st.session_state:
    st.session_state.wrong_notes = pd.DataFrame(columns=['문제', '정답', '해설', '연도'])
if 'exam_list' not in st.session_state:
    st.session_state.exam_list = []
if 'idx' not in st.session_state:
    st.session_state.idx = 0
if 'answered' not in st.session_state:
    st.session_state.answered = False

# --- [사이드바] ---
with st.sidebar:
    st.title("⚖️ 설정")
    st.subheader("📅 출제 연도 선택")
    available_years = [2021, 2022, 2023, 2024, 2025, 2026]
    selected_years = st.multiselect("학습할 연도를 체크하세요", available_years, default=[2026])
    
    st.divider()
    
    st.subheader("💾 오답 데이터")
    csv_data = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 내 오답노트 저장", csv_data, "my_wrong_notes.csv", "text/csv")
    
    uploaded_file = st.file_uploader("📤 오답노트 복구", type="csv")
    if uploaded_file:
        st.session_state.wrong_notes = pd.read_csv(uploaded_file)
        st.success("복구가 완료되었습니다!")

# --- [메인 화면] ---
st.title("⚖️ 형사법 선택형 기출 마스터")

tab1, tab2, tab3 = st.tabs(["📝 중간고사 연습", "❌ 오답 집중 복습", "📚 전체 조회"])

db = load_selected_data(selected_years)

# --- Tab 1: 중간고사 연습 ---
with tab1:
    if db.empty:
        st.warning("선택된 연도의 데이터 파일(.csv)을 찾을 수 없습니다.")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            num = st.number_input("출제 문항 수", 1, len(db), min(10, len(db)), key="mid_num")
        with c2:
            if st.button("🚀 새 시험 시작", key="mid_start"):
                st.session_state.exam_list = db.sample(n=num).to_dict('records')
                st.session_state.idx = 0
                st.session_state.answered = False
                st.rerun()

        if st.session_state.exam_list:
            exam = st.session_state.exam_list
            curr_idx = st.session_state.idx
            
            if curr_idx < len(exam):
                q = exam[curr_idx]
                st.progress((curr_idx + 1) / len(exam))
                st.write(f"**문제 {curr_idx + 1} / {len(exam)}** ({q.get('연도', '미분류')})")
                
                # 문제 출력 (검은 글씨 강제 적용된 박스)
                st.markdown(f'<div class="question-box">{q["문제"]}</div>', unsafe_allow_html=True)
                
                # 정답 입력 버튼 (흰색 글씨만 깔끔하게 남김)
                user_input = None
                b_cols = st.columns(5)
                with b_cols[0]: 
                    if st.button("O", key="o"): user_input = "O"
                with b_cols[1]: 
                    if st.button("X", key="x"): user_input = "X"
                with b_cols[2]: 
                    if st.button("O ?", key="oq"): user_input = "O?"
                with b_cols[3]: 
                    if st.button("X ?", key="xq"): user_input = "X?"
                with b_cols[4]: 
                    if st.button("?", key="q"): user_input = "?"

                if user_input:
                    st.session_state.answered = True
                    correct_ans = str(q['정답']).strip().upper()
                    is_correct = user_input[0] == correct_ans if user_input != "?" else False
                    uncertain = "?" in user_input
                    
                    if not is_correct or uncertain:
                        if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                            new_row = pd.DataFrame([q])
                            st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, new_row], ignore_index=True)
                        st.warning(f"기록: {('정답이지만 확신없음' if is_correct else '오답/모름')} ➡️ 오답 노트에 저장")
                    else:
                        st.success("정답입니다! 완벽합니다. ✨")
                    
                    st.session_state.last_exp = q['해설']
                    st.session_state.last_ans = correct_ans

                if st.session_state.answered:
                    with st.expander("📖 정답 및 해설 보기", expanded=True):
                        st.markdown(f"### 정답: {st.session_state.last_ans}")
                        st.write(st.session_state.last_exp)
                    if st.button("다음 문제 ➡️", key="mid_next"):
                        st.session_state.idx += 1
                        st.session_state.answered = False
                        st.rerun()
            else:
                st.balloons()
                st.success("시험이 종료되었습니다! 오답 노트를 확인해 보세요.")

# --- Tab 2: 오답 집중 복습 ---
with tab2:
    wn = st.session_state.wrong_notes
    if wn.empty:
        st.info("오답 노트가 깨끗합니다!")
    else:
        st.subheader(f"남은 오답: {len(wn)}개")
        q_wn = wn.iloc[0]
        st.markdown(f'<div class="question-box"><b>[출처: {q_wn.get("연도", "미분류")}]</b><br><br>{q_wn["문제"]}</div>', unsafe_allow_html=True)
        
        cw1, cw2 = st.columns(2)
        wn_act = None
        with cw1:
            if st.button("O !", key="wo1"): wn_act = "O!"
            if st.button("O", key="wo2"): wn_act = "O"
        with cw2:
            if st.button("X !", key="wx1"): wn_act = "X!"
            if st.button("X", key="wx2"): wn_act = "X"
            
        if wn_act:
            c_wn_ans = str(q_wn['정답']).strip().upper()
            if wn_act[0] == c_wn_ans:
                if "!" in wn_act:
                    st.session_state.wrong_notes = wn.drop(wn.index[0]).reset_index(drop=True)
                    st.success("확실히 암기 완료! 오답 노트에서 제외되었습니다.")
                else:
                    st.info("정답입니다! (해설 확인 후 다음으로 넘어가세요)")
            else:
                st.error("틀렸습니다! 다시 확인해 보세요.")
            
            with st.expander("📖 해설 확인", expanded=True):
                st.write(f"**정답: {c_wn_ans}**")
                st.write(q_wn['해설'])
            if st.button("다음 오답 보기 ➡️", key="wn_next"):
                st.rerun()

# --- Tab 3: 전체 조회 ---
with tab3:
    st.header("📚 범위 내 기출 DB")
    st.dataframe(db, use_container_width=True)