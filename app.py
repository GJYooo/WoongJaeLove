import streamlit as st
import pandas as pd
import random
import os
import time
import json

# --- [팝업창 함수 정의] ---
@st.dialog("📖 사용방법 가이드", width="large")
def show_manual():
    # 저장한 이미지 파일명을 넣으세요. (예: manual.png)
    st.image("manual.png", use_container_width=True)
    st.caption("닫으려면 창 바깥쪽을 클릭하거나 우측 상단 X를 누르세요.")

# --- [설정] 페이지 레이아웃 및 디자인 ---
st.set_page_config(page_title="형사법 기출 연습 (2021-2026)", layout="wide", page_icon="⚖️")

# 구글 시트 정보 (사용자가 제공한 ID)
SHEET_ID = "14ShaWll86F40k94P_M40aq8TNwB19a3XvO1w6Xxik1s"
# 시트별 GID 매핑 (구글 시트 하단 탭을 클릭했을 때 주소창의 gid= 뒤의 숫자입니다)
# 현재는 예시로 2026년이 gid=0이라고 가정합니다. 실제 시트의 gid로 수정하시면 됩니다.
GID_MAP = {
    2021: "2095370762", # 실제 gid로 수정 필요
    2022: "1893230281",
    2023: "1090949368",
    2024: "781284367",
    2025: "251633672",
    2026: "0"  # 제공해주신 링크의 gid가 0이므로 기본값 설정
}

# CSS: 가독성 및 디자인
st.markdown("""
    <style>
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
    }
    .stButton>button {
        height: 3.5em;
        font-size: 17px !important;
        font-weight: bold !important;
        color: #ffffff !important;
        background-color: #262730;
        border-radius: 10px;
    }
    .copyright {
        font-size: 0.85rem;
        color: #888888;
        line-height: 1.4;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 및 업데이트 로직] ---

def load_local_data(years):
    combined_df = pd.DataFrame()
    for year in years:
        filename = f"{year}.csv"
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename, encoding='utf-8-sig')
                # 연도를 문자열로 변환하여 소수점 발생 방지
                df['연도'] = str(year) 
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            except:
                df = pd.read_csv(filename, encoding='utf-8')
                df['연도'] = str(year)
                combined_df = pd.concat([combined_df, df], ignore_index=True)
    return combined_df

def update_from_sheets(current_db, selected_years):
    update_log = []
    updated_db = current_db.copy()
    
    for year in selected_years:
        gid = GID_MAP.get(year, "0")
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        
        try:
            sheet_df = pd.read_csv(url)
            # 문제 내용을 기준으로 해설 비교 및 업데이트
            for idx, row in sheet_df.iterrows():
                problem = row['문제']
                new_exp = row['해설']
                
                # 현재 로드된 데이터에서 같은 문제 찾기
                target_mask = updated_db['문제'] == problem
                if target_mask.any():
                    old_exp = updated_db.loc[target_mask, '해설'].values[0]
                    
                    # 해설이 달라진 경우에만 업데이트
                    if str(old_exp) != str(new_exp):
                        updated_db.loc[target_mask, '해설'] = new_exp
                        update_log.append({
                            "연도": f"{year}년",
                            "문제": problem[:30] + "...",
                            "이전 해설": old_exp,
                            "바뀐 해설": new_exp
                        })
        except Exception as e:
            st.sidebar.error(f"{year}년 시트 로드 실패: {e}")
            
    return updated_db, update_log

# --- [세션 상태 초기화] ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame()
if 'update_history' not in st.session_state:
    st.session_state.update_history = []
if 'wrong_notes' not in st.session_state:
    st.session_state.wrong_notes = pd.DataFrame(columns=['문제', '정답', '해설', '연도'])
if 'exam_list' not in st.session_state:
    st.session_state.exam_list = []
if 'idx' not in st.session_state:
    st.session_state.idx = 0
if 'answered' not in st.session_state:
    st.session_state.answered = False
if 'wn_idx' not in st.session_state:
    st.session_state.wn_idx = 0  # 오답 노의 현재 위치를 기억하는 변수
if 'total_solving_time' not in st.session_state: st.session_state.total_solving_time = 0.0
if 'q_start_time' not in st.session_state: st.session_state.q_start_time = None
if 'correct_count' not in st.session_state: st.session_state.correct_count = 0



# --- [사이드바] ---
with st.sidebar:
    st.title("⚖️ 설정")

    # 저작권 표기
    st.markdown(f"""
    <div class="copyright">
    15기 김새봄 선배님이 제공하신 파일 및 프로그램을 이용하여 만듬(16기 유각준)<br>
    <b>원래 나만 쓸 수 있는데 특별히 김사빈도 쓸 수 있음</b>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("📖 사용방법 보기", use_container_width=True):
        show_manual()
    st.divider()
    
    st.subheader("📅 범위 선택")
    available_years = [2021, 2022, 2023, 2024, 2025, 2026]
    selected_years = st.multiselect("학습 연도 선택", available_years, default=[2026])
    
    # 기본 데이터 로드 버튼
    if st.button("📁 선택 범위 데이터 불러오기", use_container_width=True):
        st.session_state.db = load_local_data(selected_years)
        st.success(f"{len(st.session_state.db)}개의 문항을 불러왔습니다.")

    st.divider()

    # 집단지성 반영 버튼
    st.subheader("🧠 집단지성 (해설 업데이트)")
    if st.button("✨ 집단지성 반영", use_container_width=True):
        if st.session_state.db.empty:
            st.warning("먼저 데이터를 불러와주세요.")
        else:
            with st.spinner("구글 시트에서 최신 해설을 가져오는 중..."):
                updated_db, logs = update_from_sheets(st.session_state.db, selected_years)
                st.session_state.db = updated_db
                st.session_state.update_history = logs
                if logs:
                    st.toast(f"{len(logs)}건의 해설이 업데이트되었습니다!")
                else:
                    st.toast("변경사항이 없습니다.")


    st.divider()
    
    # 업데이트 내역 확인 버튼 (내역이 있을 때만 표시)
    if st.session_state.update_history:
        with st.expander("🔍 최근 업데이트 내역 확인"):
            for log in st.session_state.update_history:
                st.markdown(f"**[{log['연도']}]** {log['문제']}")
                st.caption(f"이전: {log['이전 해설']}")
                st.markdown(f"새해설: {log['바뀐 해설']}")
                st.divider()

    st.divider()
    
    
    st.subheader("⏯️ 시험 진행상황")
    
    # [1] 현재 진행상황 데이터 구성
    if st.session_state.get('exam_list') and not st.session_state.get('is_finished', False):
        progress_data = {
            "exam_list": st.session_state.exam_list,
            "idx": st.session_state.idx,
            "correct_count": st.session_state.correct_count,
            "total_solving_time": st.session_state.total_solving_time,
            "selected_years": selected_years # 당시 선택했던 연도 정보
        }
        progress_json = json.dumps(progress_data, ensure_ascii=False)
        
        st.download_button(
            label="📥 현재 진행상황 저장",
            data=progress_json,
            file_name="quiz_progress.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.caption("진행 중인 시험이 없습니다.")

    # [2] 진행상황 불러오기
    uploaded_progress = st.file_uploader("📤 진행상황 불러오기 (.json)", type="json")
    if uploaded_progress:
        try:
            data = json.load(uploaded_progress)
            st.session_state.exam_list = data["exam_list"]
            st.session_state.idx = data["idx"]
            st.session_state.correct_count = data["correct_count"]
            st.session_state.total_solving_time = data["total_solving_time"]
            st.session_state.answered = False
            st.session_state.q_start_time = time.time() # 불러온 시점부터 다시 타이머 시작
            st.success("이전 진행상황을 불러왔습니다! '중간고사 연습' 탭으로 가세요.")
        except Exception as e:
            st.error(f"파일 형식이 잘못되었습니다: {e}")

    # 오답 데이터 백업 및 복구
    st.subheader("💾 데이터 관리")
    # 저장 버튼
    csv_data = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 내 오답노트 저장",
        data=csv_data,
        file_name="my_wrong_notes.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # 불러오기 버튼
    uploaded_file = st.file_uploader("📤 오답노트 복구", type="csv")
    if uploaded_file:
        st.session_state.wrong_notes = pd.read_csv(uploaded_file)
        st.success("오답노트 복구 완료!")

    st.divider()



# --- [메인 화면] ---
st.title("⚖️ 형사법 선택형 기출 연습")

tab1, tab2, tab3 = st.tabs(["📝 중간고사 연습", "❌ 오답 집중 복습", "📚 전체 조회"])

# 현재 로드된 데이터 참조
db = st.session_state.db

# --- Tab 1: 중간고사 연습 ---
with tab1:
    if db.empty:
        st.info("사이드바에서 데이터를 불러오세요.")
    else:
        # 시험 설정
        num = st.number_input("출제 문항 수", 1, len(db), min(10, len(db)), key="mid_num")
        if st.button("🚀 새 시험 시작", key="mid_start", use_container_width=True):
            st.session_state.exam_list = db.sample(n=num).to_dict('records')
            st.session_state.idx = 0
            st.session_state.answered = False
            st.session_state.correct_count = 0
            st.session_state.total_solving_time = 0.0  # 누적 풀이 시간 초기화
            st.session_state.q_start_time = time.time()  # 첫 번째 문제 시작 시간 기록
            st.rerun()

        if st.session_state.get('exam_list'):
            exam = st.session_state.exam_list
            curr_idx = st.session_state.idx
            
            # [A] 문제 풀이 모드
            if curr_idx < len(exam):
                q = exam[curr_idx]
                st.progress((curr_idx + 1) / len(exam))
                
                # 문제 출력 전, 만약 타이머가 안 돌아가고 있다면 (다음 문제로 넘어온 직후) 시작 시간 기록
                if not st.session_state.answered and st.session_state.q_start_time is None:
                    st.session_state.q_start_time = time.time()

                raw_year = str(q.get('연도', '미분류')).split('.')[0]
                st.write(f"**문제 {curr_idx + 1} / {len(exam)}** ({raw_year}년)")
                st.markdown(f'<div class="question-box">{q["문제"]}</div>', unsafe_allow_html=True)
                
                user_input = None
                b_cols = st.columns(3)
                with b_cols[0]: 
                    if st.button("O", key=f"o_{curr_idx}", use_container_width=True): user_input = "O"
                with b_cols[1]: 
                    if st.button("X", key=f"x_{curr_idx}", use_container_width=True): user_input = "X"
                with b_cols[2]: 
                    if st.button("?", key=f"q_{curr_idx}", use_container_width=True): user_input = "?"

                # 사용자가 답을 선택한 순간!
                if user_input and not st.session_state.answered:
                    # [핵심] 여기서 풀이 시간 측정 중단 및 누적
                    solve_duration = time.time() - st.session_state.q_start_time
                    st.session_state.total_solving_time += solve_duration
                    st.session_state.q_start_time = None # 타이머 초기화 (해설 읽는 동안은 안 돌아감)
                    
                    st.session_state.answered = True
                    correct_ans = str(q['정답']).strip().upper()
                    
                    if user_input == "?":
                        st.session_state.last_is_correct = False
                    else:
                        is_correct = (user_input == correct_ans)
                        st.session_state.last_is_correct = is_correct
                        if is_correct:
                            st.session_state.correct_count += 1
                    
                    if not st.session_state.last_is_correct:
                        if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                            st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, pd.DataFrame([q])], ignore_index=True)
                    
                    st.session_state.last_exp = q['해설']
                    st.session_state.last_ans = correct_ans

                # 해설 출력 구역 (여기에 머무는 시간은 통계에 포함되지 않음)
                if st.session_state.answered:
                    if st.session_state.last_is_correct:
                        st.success("정답입니다! ✨")
                    else:
                        st.error(f"오답입니다. (정답: {st.session_state.last_ans})")

                    with st.expander("📖 해설 보기", expanded=True):
                        st.write(st.session_state.last_exp)
                    
                    c_n1, c_n2 = st.columns(2)
                    with c_n1:
                        if st.session_state.last_is_correct:
                            if st.button("🤔 내 생각과 다름 ➡️ 오답노트 추가", key=f"manual_{curr_idx}", use_container_width=True):
                                if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                                    st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, pd.DataFrame([q])], ignore_index=True)
                                    st.toast("오답노트 수동 추가 완료!")
                    with c_n2:
                        btn_label = "결과 확인하기 📊" if curr_idx == len(exam) - 1 else "다음 문제 ➡️"
                        if st.button(btn_label, key=f"next_{curr_idx}", use_container_width=True):
                            st.session_state.idx += 1
                            st.session_state.answered = False
                            # 다음 문제를 위해 타이머는 위쪽 'if not answered' 구역에서 재시작됨
                            st.rerun()

            # [B] 시험 결과 리포트
            else:
                st.balloons()
                st.header("📊 순수 풀이 결과 리포트")
                st.caption("※ 해설을 읽은 시간은 포함되지 않은 '순수 문제 풀이' 통계입니다.")
                
                total_q = len(exam)
                correct_q = st.session_state.correct_count
                accuracy = (correct_q / total_q) * 100
                total_solve_time = st.session_state.total_solving_time
                avg_time = total_solve_time / total_q
                
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("맞은 문제", f"{correct_q} / {total_q}")
                col_res2.metric("정답률", f"{accuracy:.1f}%")
                col_res3.metric("순수 풀이 시간", f"{total_solve_time:.1f}초")
                
                col_res4, col_res5 = st.columns(2)
                col_res4.metric("문제당 평균 풀이 시간", f"{avg_time:.1f}초")
                
                st.divider()
                if st.button("새로운 시험 시작하기 🔄", use_container_width=True):
                    st.session_state.exam_list = []
                    st.session_state.idx = 0
                    st.session_state.total_solving_time = 0.0
                    st.rerun()



# --- Tab 2: 오답 집중 복습 (네비게이션 기능 추가) ---
with tab2:
    wn = st.session_state.wrong_notes
    if wn.empty:
        st.info("오답 노트가 비어 있습니다.")
    else:
        # 오답 개수에 따라 인덱스가 범위를 벗어나지 않도록 조정
        if st.session_state.wn_idx >= len(wn):
            st.session_state.wn_idx = 0

        # 상단 네비게이션 바
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        with col_nav1:
            if st.button("⬅️ 이전 오답", use_container_width=True, key="wn_prev"):
                st.session_state.wn_idx = (st.session_state.wn_idx - 1) % len(wn)
                st.rerun()
        with col_nav2:
            st.markdown(f"<p style='text-align: center; font-weight: bold;'>오답 {st.session_state.wn_idx + 1} / {len(wn)}</p>", unsafe_allow_html=True)
        with col_nav3:
            if st.button("다음 오답 ➡️", use_container_width=True, key="wn_next_nav"):
                st.session_state.wn_idx = (st.session_state.wn_idx + 1) % len(wn)
                st.rerun()

        # 현재 인덱스의 오답 가져오기
        q_wn = wn.iloc[st.session_state.wn_idx]
        
        # 연도 소수점 제거 로직
        raw_year_wn = str(q_wn.get('연도', '미분류')).split('.')[0]
        st.markdown(f'<div class="question-box"><b>[{raw_year_wn}년]</b><br><br>{q_wn["문제"]}</div>', unsafe_allow_html=True)
        
        # 정답 입력 버튼 섹션
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
                    # '확실함(!)' 선택 시 해당 항목 삭제
                    st.session_state.wrong_notes = wn.drop(wn.index[st.session_state.wn_idx]).reset_index(drop=True)
                    st.success("확실히 암기 완료! 오답 노트에서 제외되었습니다.")
                    # 인덱스 조정 (리스트가 줄어들었으므로)
                    if st.session_state.wn_idx >= len(st.session_state.wrong_notes) and len(st.session_state.wrong_notes) > 0:
                        st.session_state.wn_idx = 0
                    st.rerun()
                else:
                    st.info("정답입니다! (해설 확인 후 넘어가세요)")
            else:
                st.error("틀렸습니다! 다시 확인해 보세요.")
            
            with st.expander("📖 해설 확인", expanded=True):
                st.markdown(f"### 정답: {c_wn_ans}")
                st.write(q_wn['해설'])


# --- Tab 3: 전체 조회 ---
with tab3:
    st.header("📚 전체 문제 조회")
    st.dataframe(db, use_container_width=True)
