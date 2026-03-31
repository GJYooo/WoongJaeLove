import streamlit as st
import pandas as pd
import random
import os

# --- [설정] 페이지 레이아웃 및 디자인 ---
st.set_page_config(page_title="형사법 기출 퀴즈 (2021-2026)", layout="wide", page_icon="⚖️")

# CSS: 버튼 디자인 및 가독성 향상
st.markdown("""
    <style>
    .stButton>button { height: 3.5em; font-size: 18px; font-weight: bold; border-radius: 12px; transition: 0.3s; }
    .stButton>button:hover { background-color: #f0f2f6; border-color: #4CAF50; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
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
                df = pd.read_csv(filename)
                df['연도'] = f"{year}년" # 어느 연도 문제인지 표시용
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            except Exception as e:
                st.error(f"{year}.csv 파일을 읽는 중 오류 발생: {e}")
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

# --- [사이드바: 범위 설정 및 관리] ---
with st.sidebar:
    st.title("⚙️ 설정 및 관리")
    
    st.subheader("📅 출제 범위 선택")
    # 2021~2026년 선택 박스
    available_years = [2021, 2022, 2023, 2024, 2025, 2026]
    selected_years = st.multiselect("연도를 선택하세요 (중복 가능)", available_years, default=[2026])
    
    st.divider()
    
    st.subheader("💾 오답노트 백업")
    # 오답 노트 CSV 다운로드 (UTF-8-SIG로 엑셀 한글 깨짐 방지)
    csv_data = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 내 오답노트 저장 (CSV)", csv_data, "my_wrong_notes.csv", "text/csv")
    
    # 오답 노트 불러오기
    uploaded_file = st.file_uploader("📤 오답노트 복구", type="csv")
    if uploaded_file:
        st.session_state.wrong_notes = pd.read_csv(uploaded_file)
        st.success("데이터 복구 완료!")

# --- [메인 UI] ---
st.title("⚖️ 형사법 선택형 기출 마스터")
tab_midterm, tab_wrong, tab_db = st.tabs(["📝 중간고사 (midterm)", "❌ 오답 노트 (wrong_note)", "📚 문제 은행 조회"])

# 데이터 로드 (선택된 연도 기반)
db = load_selected_data(selected_years)

# --- Tab 1: 중간고사 모드 (midterm.exe 로직) ---
with tab_midterm:
    if db.empty:
        st.warning("선택한 연도의 CSV 파일이 없습니다. GitHub 저장소를 확인해주세요.")
    else:
        st.header("무작위 기출 연습")
        c_setup1, c_setup2 = st.columns([1, 2])
        with c_setup1:
            num = st.number_input("출제 문항 수", 1, len(db), min(10, len(db)))
        with c_setup2:
            if st.button("🚀 새 시험 시작 (범위 내 랜덤)"):
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
                
                # 문제 출력 박스
                st.markdown(f'<div class="question-box">{q["문제"]}</div>', unsafe_allow_html=True)
                
                # 정답 입력 섹션 (이미지 요구사항 반영: O, X, O?, X?, ?)
                user_input = None
                btn_cols = st.columns(5)
                with btn_cols[0]: 
                    if st.button("⭕ O"): user_input = "O"
                with btn_cols[1]: 
                    if st.button("❌ X"): user_input = "X"
                with btn_cols[2]: 
                    if st.button("❓ O?"): user_input = "O?"
                with btn_cols[3]: 
                    if st.button("❓ X?"): user_input = "X?"
                with btn_cols[4]: 
                    if st.button("❗ ?"): user_input = "?"

                if user_input:
                    st.session_state.answered = True
                    correct_ans = str(q['정답']).strip().upper()
                    is_correct = user_input[0] == correct_ans if user_input != "?" else False
                    uncertain = "?" in user_input # 확신 없는 경우 (O?, X?, ?)
                    
                    # 오답 노트 기록: 틀렸거나, 찍어서 맞혔거나
                    if not is_correct or uncertain:
                        if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                            new_row = pd.DataFrame([q])
                            st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, new_row], ignore_index=True)
                        st.error(f"결과: {('정답(확신없음)' if is_correct else '오답/모름')} ➡️ 오답 노트에 자동 저장되었습니다.")
                    else:
                        st.success("완벽한 정답입니다! ✨")
                    
                    st.session_state.last_exp = q['해설']
                    st.session_state.last_ans = correct_ans

                if st.session_state.answered:
                    with st.expander("📖 정답 및 해설 보기", expanded=True):
                        st.markdown(f"### 정답: {st.session_state.last_ans}")
                        st.write(st.session_state.last_exp)
                    if st.button("다음 문제로 이동 ➡️"):
                        st.session_state.idx += 1
                        st.session_state.answered = False
                        st.rerun()
            else:
                st.balloons()
                st.success("모든 문제를 다 풀었습니다! 오답 노트를 확인하세요.")
                if st.button("처음으로 돌아가기"):
                    st.session_state.exam_list = []
                    st.rerun()

# --- Tab 2: 오답 노트 모드 (wrong_note.exe 로직) ---
with tab2:
    st.header("오답 노트 집중 복습")
    wn = st.session_state.wrong_notes
    if wn.empty:
        st.info("현재 오답 노트가 비어 있습니다. 완벽하네요!")
    else:
        st.subheader(f"관리 중인 오답: {len(wn)}개")
        # 가장 오래된 오답부터 순차적으로 제시
        q_wn = wn.iloc[0]
        st.markdown(f'<div class="question-box"><b>[출처: {q_wn.get("연도", "미분류")}]</b><br><br>{q_wn["문제"]}</div>', unsafe_allow_html=True)
        
        c_wn1, c_wn2 = st.columns(2)
        wn_act = None
        with c_wn1:
            if st.button("⭕ O! (확실히 알겠음)"): wn_act = "O!"
            if st.button("⭕ O (아직 긴가민가함)"): wn_act = "O"
        with c_wn2:
            if st.button("❌ X! (확실히 알겠음)"): wn_act = "X!"
            if st.button("❌ X (아직 긴가민가함)"): wn_act = "X"
            
        if wn_act:
            correct_wn_ans = str(q_wn['정답']).strip().upper()
            if wn_act[0] == correct_wn_ans:
                if "!" in wn_act: # 확실히 아는 경우 삭제
                    st.session_state.wrong_notes = wn.drop(wn.index[0]).reset_index(drop=True)
                    st.success("확신 판정! 오답 노트에서 삭제되었습니다. 🎉")
                else:
                    st.info("정답입니다. (오답 노트에 유지됩니다)")
            else:
                st.error("틀렸습니다! 아직 더 공부가 필요합니다.")
            
            with st.expander("📖 해설 확인", expanded=True):
                st.markdown(f"### 정답: {correct_wn_ans}")
                st.write(q_wn['해설'])
            
            if st.button("다음 오답 확인 ➡️"):
                st.rerun()

# --- Tab 3: 문제 은행 조회 ---
with tab3:
    st.header(f"📚 선택 범위 내 전체 문제 ({len(db)}개)")
    st.dataframe(db, use_container_width=True)