import streamlit as st
import pandas as pd
import random
import os

# --- [설정] 페이지 레이아웃 및 디자인 ---
st.set_page_config(page_title="형사법 기출 연습 (2021-2026)", layout="wide", page_icon="⚖️")

# CSS: 디자인 강화
st.markdown("""
    <style>
    .stButton>button { height: 3.5em; font-size: 18px; font-weight: bold; border-radius: 12px; }
    .question-box { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border-left: 5px solid #4CAF50; margin-bottom: 20px; font-size: 1.1rem; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 로직] ---
def load_selected_data(years):
    combined_df = pd.DataFrame()
    for year in years:
        filename = f"{year}.csv"
        if os.path.exists(filename):
            try:
                # UTF-8-SIG는 엑셀에서 만든 CSV의 한글 깨짐을 방지합니다.
                df = pd.read_csv(filename, encoding='utf-8-sig')
                df['연도'] = f"{year}년"
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            except:
                try:
                    # 일반 UTF-8 시도
                    df = pd.read_csv(filename, encoding='utf-8')
                    df['연도'] = f"{year}년"
                    combined_df = pd.concat([combined_df, df], ignore_index=True)
                except Exception as e:
                    st.error(f"{year}.csv 파일을 읽을 수 없습니다: {e}")
    return combined_df

# --- [세션 상태 초기화] ---
# 앱이 새로고침되어도 데이터가 유지되도록 설정
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
    st.title("⚙️ 설정 및 관리")
    
    st.subheader("📅 출제 범위 선택")
    available_years = [2021, 2022, 2023, 2024, 2025, 2026]
    selected_years = st.multiselect("연도를 선택하세요", available_years, default=[2026])
    
    st.divider()
    
    st.subheader("💾 데이터 관리")
    # 오답 노트 저장
    csv_data = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 내 오답노트 저장", csv_data, "my_wrong_notes.csv", "text/csv")
    
    # 오답 노트 불러오기
    uploaded_file = st.file_uploader("📤 오답노트 복구", type="csv")
    if uploaded_file:
        st.session_state.wrong_notes = pd.read_csv(uploaded_file)
        st.success("오답노트 복구 완료!")

# --- [메인 화면] ---
st.title("⚖️ 형사법 선택형 기출 연습")

# 탭 정의 (변수명을 tab1, tab2, tab3로 명확하게 지정)
tab1, tab2, tab3 = st.tabs(["📝 중간고사 모드", "❌ 오답 노트 모드", "📚 문제 은행 조회"])

# 선택된 연도 데이터 합치기
db = load_selected_data(selected_years)

# --- Tab 1: 중간고사 (midterm.exe) ---
with tab1:
    if db.empty:
        st.warning("선택한 연도의 CSV 파일이 없습니다. GitHub에 파일을 업로드해주세요.")
    else:
        st.header("무작위 기출 연습")
        c1, c2 = st.columns([1, 2])
        with c1:
            num = st.number_input("출제 문항 수", 1, len(db), min(10, len(db)), key="num_input")
        with c2:
            if st.button("🚀 새 시험 시작"):
                # 무작위 추출
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
                
                st.markdown(f'<div class="question-box">{q["문제"]}</div>', unsafe_allow_html=True)
                
                # 정답 입력 (O, X, O?, X?, ?)
                user_input = None
                b_cols = st.columns(5)
                with b_cols[0]: 
                    if st.button("⭕ O", key="btn_o"): user_input = "O"
                with b_cols[1]: 
                    if st.button("❌ X", key="btn_x"): user_input = "X"
                with b_cols[2]: 
                    if st.button("❓ O?", key="btn_oq"): user_input = "O?"
                with b_cols[3]: 
                    if st.button("❓ X?", key="btn_xq"): user_input = "X?"
                with b_cols[4]: 
                    if st.button("❗ ?", key="btn_q"): user_input = "?"

                if user_input:
                    st.session_state.answered = True
                    correct_ans = str(q['정답']).strip().upper()
                    is_correct = user_input[0] == correct_ans if user_input != "?" else False
                    uncertain = "?" in user_input
                    
                    if not is_correct or uncertain:
                        if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                            new_row = pd.DataFrame([q])
                            st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, new_row], ignore_index=True)
                        st.error(f"결과: {('정답(확신없음)' if is_correct else '오답/모름')} ➡️ 오답 노트에 저장")
                    else:
                        st.success("정답입니다! ✨")
                    
                    st.session_state.last_exp = q['해설']
                    st.session_state.last_ans = correct_ans

                if st.session_state.answered:
                    with st.expander("📖 정답 및 해설 보기", expanded=True):
                        st.markdown(f"### 정답: {st.session_state.last_ans}")
                        st.write(st.session_state.last_exp)
                    if st.button("다음 문제 ➡️", key="next_btn"):
                        st.session_state.idx += 1
                        st.session_state.answered = False
                        st.rerun()
            else:
                st.balloons()
                st.success("시험 종료!")

# --- Tab 2: 오답 노트 (wrong_note.exe) ---
with tab2:
    st.header("오답 노트 집중 복습")
    wn = st.session_state.wrong_notes
    if wn.empty:
        st.info("오답 노트가 비어 있습니다.")
    else:
        st.subheader(f"남은 오답: {len(wn)}개")
        q_wn = wn.iloc[0]
        st.markdown(f'<div class="question-box"><b>[출처: {q_wn.get("연도", "미분류")}]</b><br><br>{q_wn["문제"]}</div>', unsafe_allow_html=True)
        
        cw1, cw2 = st.columns(2)
        wn_act = None
        with cw1:
            if st.button("⭕ O! (확실함)", key="wn_o1"): wn_act = "O!"
            if st.button("⭕ O (헷갈림)", key="wn_o2"): wn_act = "O"
        with cw2:
            if st.button("❌ X! (확실함)", key="wn_x1"): wn_act = "X!"
            if st.button("❌ X (헷갈림)", key="wn_x2"): wn_act = "X"
            
        if wn_act:
            c_wn_ans = str(q_wn['정답']).strip().upper()
            if wn_act[0] == c_wn_ans:
                if "!" in wn_act:
                    st.session_state.wrong_notes = wn.drop(wn.index[0]).reset_index(drop=True)
                    st.success("삭제되었습니다!")
                else:
                    st.info("정답입니다! (리스트 유지)")
            else:
                st.error("틀렸습니다!")
            
            with st.expander("📖 해설 확인", expanded=True):
                st.write(f"**정답: {c_wn_ans}**")
                st.write(q_wn['해설'])
            if st.button("다음 오답 ➡️", key="next_wn"):
                st.rerun()

# --- Tab 3: 문제 은행 조회 ---
with tab3:
    st.header("📚 전체 문제 조회")
    st.dataframe(db, use_container_width=True)