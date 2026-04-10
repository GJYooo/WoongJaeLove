import streamlit as st
import pandas as pd
import random
import os
import time
import json
import base64

@st.cache_data
def get_audio_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def play_sound(file_path):
    if not st.session_state.get('sound_on', True):
        return
    b64_string = get_audio_base64(file_path)
    # 재생 시마다 고유한 ID를 부여하여 브라우저 버퍼링을 방지합니다.
    timestamp = time.time()
    md = f"""
        <audio autoplay="true" id="audio_{timestamp}">
            <source src="data:audio/mp3;base64,{b64_string}" type="audio/mp3">
        </audio>
        """
    st.markdown(md, unsafe_allow_html=True)


# --- [팝업창 함수 정의] ---
@st.dialog("📖 사용방법 가이드", width="large")
def show_manual():
    st.image("manual.png", use_container_width=True)
    st.caption("닫으려면 창 바깥쪽을 클릭하거나 우측 상단 X를 누르세요.")

# --- [설정] 페이지 레이아웃 및 디자인 ---
st.set_page_config(page_title="2026 형실연 중간고사 연습", layout="wide", page_icon="⚖️")

SHEET_ID = "14ShaWll86F40k94P_M40aq8TNwB19a3XvO1w6Xxik1s"
GID_MAP = {
    2021: "2095370762",
    2022: "1893230281",
    2023: "1090949368",
    2024: "781284367",
    2025: "251633672",
    2026: "0"
}

# CSS: 가독성 및 디자인
st.markdown("""
    <style>
    /* 문제 박스 디자인 */
    .question-box {
        background-color: #f1f3f5;
        color: #000000 !important;
        padding: 20px;
        border-radius: 12px;
        border-left: 8px solid #2e7d32;
        margin-bottom: 10px;
        font-size: 1.1rem;
        font-weight: 500;
        line-height: 1.5;
    }
    
    /* 버튼 디자인 */
    .stButton>button {
        width: 100% !important; 
        height: 3em;
        font-size: 16px !important;
        font-weight: bold !important;
        color: #ffffff !important;
        background-color: #262730;
        border-radius: 8px;
    }

    
    
    .correct-feedback-text {
        background-color: #e6ffed; /* 연한 초록색 배경 */
        color: #1a7f37; /* 진한 초록색 글씨 */
        padding: 5px 10px; /* 내부 여백 */
        border-radius: 5px; /* 모서리 둥글게 */
        font-weight: bold; /* 글씨 굵게 */
    }
    .wrong-feedback-text {
        background-color: #ffebe8; /* 연한 빨간색 배경 */
        color: #b02a37; /* 진한 빨간색 글씨 */
        padding: 5px 15px;
        border-radius: 5px;
        font-weight: bold;
    }

    div[data-testid="stHorizontalBlock"] {
        align-items: center !important
    }

    
    /* 사이드바 내부 간격 촘촘하게 조절 */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.3rem !important; 
    }
    [data-testid="stSidebar"] hr {
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 및 업데이트 로직] ---
@st.cache_data
def load_local_data(years):
    combined_df = pd.DataFrame()
    for year in years:
        filename = f"{year}.csv"
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename, encoding='utf-8-sig')
                df['연도'] = str(year) 
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            except:
                df = pd.read_csv(filename, encoding='utf-8')
                df['연도'] = str(year)
                combined_df = pd.concat([combined_df, df], ignore_index=True)
    return combined_df

@st.cache_data(ttl=600) 
def fetch_sheet_data(url):
    try:
        return pd.read_csv(url)
    except:
        return None
        
def update_from_sheets(selected_years):
    update_log = []
    if not st.session_state.db.empty:
        for year in selected_years:
            gid = GID_MAP.get(year, "0")
            url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
            try:
                sheet_df = fetch_sheet_data(url)
                for _, row in sheet_df.iterrows():
                    problem = row['문제']
                    new_exp = row['해설']
                    
                    # A. 전체 DB 업데이트 및 마킹
                    mask = st.session_state.db['문제'] == problem
                    if mask.any():
                        old_exp = st.session_state.db.loc[mask, '해설'].values[0]
                        if str(old_exp) != str(new_exp):
                            st.session_state.db.loc[mask, '해설'] = new_exp
                            st.session_state.db.loc[mask, '해설업데이트'] = True # 🏷️ 마킹 추가
                            
                            update_log.append({"연도": f"{year}년", "문제": problem[:30] + "...", "이전 해설": old_exp, "바뀐 해설": new_exp})
                    
                    # B. 현재 풀고 있는 시험지(exam_list) 마킹
                    for q_item in st.session_state.exam_list:
                        if q_item['문제'] == problem:
                            q_item['해설'] = new_exp
                            q_item['해설업데이트'] = True # 🏷️ 마킹 추가
                    
                    # C. 현재 오답노트(wrong_notes) 마킹
                    wn_mask = st.session_state.wrong_notes['문제'] == problem
                    if wn_mask.any():
                        st.session_state.wrong_notes.loc[wn_mask, '해설'] = new_exp
                        st.session_state.wrong_notes.loc[wn_mask, '해설업데이트'] = True # 🏷️ 마킹 추가
            except: continue
    return update_log


# --- [세션 상태 초기화] ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame()
if 'selected_years' not in st.session_state: 
    st.session_state.selected_years = [2026] # 초기 연도 설정
if 'last_restored_file' not in st.session_state:
    st.session_state.last_restored_file = None # 중복 복구 방지용
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
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0 # 업로더 초기화용 키
if 'total_solving_time' not in st.session_state:
    st.session_state.total_solving_time = 0.0
if 'q_start_time' not in st.session_state:
    st.session_state.q_start_time = None
if 'correct_count' not in st.session_state:
    st.session_state.correct_count = 0
if 'sound_on' not in st.session_state:
    st.session_state.sound_on = True  # 기본값은 '켜짐'
if 'auto_update' not in st.session_state:
    st.session_state.auto_update = True
if 'exam_finished_celebrated' not in st.session_state:
    st.session_state.exam_finished_celebrated = False


# --- [사이드바] ---
with st.sidebar:
    st.title("⚖️ 설정")
    st.toggle("🔊 효과음 활성화", key="sound_on")
    st.toggle("🌐 자동 해설 업데이트", key="auto_update", help="데이터를 불러올 때 구글 시트(집단지성)의 해설을 자동으로 반영합니다.")
    st.divider()

    if st.button("📖 사용방법 보기", use_container_width=True):
        show_manual()
    st.divider()


    st.subheader("⏯️ 시험 진행상황")
    
    # [1] 현재 진행상황 데이터 구성
    if st.session_state.get('exam_list') and not st.session_state.get('is_finished', False):
        progress_data = {
            "exam_list": st.session_state.exam_list,
            "idx": st.session_state.idx,
            "correct_count": st.session_state.correct_count,
            "total_solving_time": st.session_state.total_solving_time,
            "selected_years": st.session_state.selected_years # 당시 선택했던 연도 정보
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

    st.divider()

# [2] 진행상황 불러오기 수정본 (호환성 및 가짜에러 방지)
    up_json = st.file_uploader("📤 진행상황 불러오기", type="json", key=f"json_up_{st.session_state.uploader_key}")
    if up_json:
        try:
            data = json.load(up_json)
            
            # --- 호환성 체크: 키가 없으면 기본값 사용 (.get 사용) ---
            restored_years = data.get("selected_years", [2026])
            st.session_state.selected_years = restored_years 
            
            # 데이터 로드
            st.session_state.db = load_local_data(restored_years)
            if st.session_state.auto_update:
                logs = update_from_sheets(st.session_state.selected_years)
                st.session_state.update_history = logs
                
            # 진행 상태 복구 (키가 없어도 에러나지 않게 .get 활용)
            st.session_state.exam_list = data.get("exam_list", [])
            st.session_state.idx = data.get("idx", 0)
            st.session_state.correct_count = data.get("correct_count", 0)
            st.session_state.total_solving_time = data.get("total_solving_time", 0.0)
            
            if "wrong_notes" in data:
                st.session_state.wrong_notes = pd.DataFrame(data["wrong_notes"])
            
            st.session_state.answered = False
            st.session_state.q_start_time = time.time()
            st.session_state.uploader_key += 1 # 성공했으니 업로더 비우기
            
            st.toast("복구가 완료되었습니다! 🎉")
            time.sleep(0.5)
            
            should_rerun = True 

        except Exception as e:
            # RerunException인 경우 에러 메시지를 띄우지 않음
            if "Rerun" not in str(type(e)):
                st.error(f"진짜 복구 실패: {e}")
            else:
                should_rerun = True

    if 'should_rerun' in locals() and should_rerun:
        st.rerun()
            
    st.divider()
    
    st.subheader("📅 범위 선택")
    available_years = [2021, 2022, 2023, 2024, 2025, 2026]
    st.multiselect("학습 연도 선택", available_years, key="selected_years")
    
    # 기본 데이터 로드 버튼
    if st.button("📁 선택 범위 데이터 불러오기", use_container_width=True):
        st.session_state.db = load_local_data(st.session_state.selected_years)
        if st.session_state.auto_update:
            with st.spinner("최신 해설 동기화 중..."):
                logs = update_from_sheets(st.session_state.selected_years)
                st.session_state.update_history = logs
                if logs:
                    st.toast(f"{len(logs)}건의 해설이 실시간 반영되었습니다! 🎉")
                else:
                    st.toast("이미 최신 상태입니다. ✅")
                time.sleep(0.5)
                st.rerun()
            st.success(f"{len(st.session_state.db)}개 문항 로드 및 해설 동기화 완료!")
        else:
            st.session_state.update_history = []
            st.success(f"{len(st.session_state.db)}개 문항 로드 완료!")

    st.divider()
    
    # 업데이트 내역 확인 버튼 (내역이 있을 때만 표시)
    if st.session_state.update_history:
        with st.expander("🔍 최근 업데이트 내역 확인"):
            for log in st.session_state.update_history:
                st.markdown(f"**[{log.get('연도', '미분류')}]** {log.get('문제', '문제 정보 없음')}")
                st.caption(f"이전: {log.get('이전 해설', '정보 없음')}")
                st.markdown(f"새해설: {log.get('바뀐 해설', '정보 없음')}")
                st.divider()
    
    should_rerun = False

    st.subheader("💾 데이터 관리")
    csv_dn = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 내 오답노트 저장", csv_dn, "my_wrong_notes.csv", "text/csv", use_container_width=True)
    
    # [버그 수정] CSV 불러오기
    up_csv = st.file_uploader("📤 오답노트 복구", type="csv", key=f"csv_up_{st.session_state.uploader_key}")
    if up_csv:
        try:
            st.session_state.wrong_notes = pd.read_csv(up_csv)
            st.session_state.uploader_key += 1 # 버튼 초기화
            st.toast("오답노트 복구 완료! ✅")
            time.sleep(0.5)
            should_rerun = True
        except: st.error("CSV 복구 실패")

    st.divider()

    # 저작권 표기
    st.markdown(f"""
    <div class="copyright">
    <br>
    16기 유각준 <br>
    (15기 김새봄 선배님이 배포하신 프로그램 및 데이터를 이용하여 만듬)<br>
    </div>    
    """, unsafe_allow_html=True)

# --- [메인 화면] ---
st.title("⚖️ 2026 형실연 중간고사 연습")

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
            st.session_state.exam_finished_celebrated = False
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
                st.write(f"### 📝 문제 {curr_idx + 1} / {len(exam)}")
                st.progress((curr_idx + 1) / len(exam))
                
                # 문제 출력 전, 만약 타이머가 안 돌아가고 있다면 (다음 문제로 넘어온 직후) 시작 시간 기록
                if not st.session_state.answered and st.session_state.q_start_time is None:
                    st.session_state.q_start_time = time.time()

                raw_year_display = str(q.get('연도', '미분류')).split('.')[0]
                clean_question = str(q["문제"]).replace('<', '〈').replace('>', '〉')

                update_tag = ""
                if q.get('해설업데이트') == True:
                    update_tag = " <span style='color: #ff4b4b; font-size: 0.8rem; border: 1px solid #ff4b4b; padding: 2px 5px; border-radius: 5px; margin-left: 10px;'>해설 업데이트</span>"
                
                # 화면에 출력
                st.markdown(f'<div class="question-box"><b>[{raw_year_display}년]</b>{update_tag}<br><br>{clean_question}</div>', unsafe_allow_html=True)
                
                user_input = None
                b_cols = st.columns(3)
                with b_cols[0]: 
                    if st.button("O", key=f"o_{curr_idx}", use_container_width=True, shortcut="o"): user_input = "O"
                with b_cols[1]: 
                    if st.button("X", key=f"x_{curr_idx}", use_container_width=True, shortcut="x"): user_input = "X"
                with b_cols[2]: 
                    if st.button("?", key=f"q_{curr_idx}", use_container_width=True, shortcut="q"): user_input = "?"

                if user_input and not st.session_state.answered:
                    solve_duration = time.time() - st.session_state.q_start_time
                    st.session_state.total_solving_time += solve_duration
                    st.session_state.q_start_time = None 
                    
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

                if st.session_state.answered:
                    if st.session_state.last_is_correct:
                        play_sound("correct.mp3") 
                        col_feedback_img, col_feedback_text = st.columns([0.05, 0.95], gap="small") 
                        with col_feedback_img:
                            st.image("correct.jpeg", width=50) 
                        with col_feedback_text:
                            st.markdown("<span class='correct-feedback-text'>정답입니다!</span>", unsafe_allow_html=True)
                    else:
                        play_sound("wrong.mp3") 
                        col_feedback_img, col_feedback_text = st.columns([0.05, 0.95], gap="small") 
                        with col_feedback_img:
                            st.image("wrong.jpeg", width=50)
                        with col_feedback_text:
                            st.markdown("<span class='wrong-feedback-text'>틀렸습니다! 다시 확인해 보세요.</span>", unsafe_allow_html=True)

                    with st.expander("📖 해설 보기", expanded=True):
                        current_correct_ans = str(q['정답']).strip().upper()
                        st.markdown(f"### 정답: {current_correct_ans}") 
                        st.write(st.session_state.last_exp)
                    
                    c_n1, c_n2 = st.columns(2)
                    with c_n1:
                        if st.session_state.last_is_correct:
                            if st.button("🤔 오답노트 추가", key=f"manual_{curr_idx}", use_container_width=True, shortcut="w"):
                                if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                                    st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, pd.DataFrame([q])], ignore_index=True)
                                    st.toast("오답노트 수동 추가 완료!")
                    with c_n2:
                        btn_label = "결과 확인하기 📊" if curr_idx == len(exam) - 1 else "다음 문제 ➡️"
                        if st.button(btn_label, key=f"next_{curr_idx}", use_container_width=True, shortcut="Enter"):
                            st.session_state.idx += 1
                            st.session_state.answered = False
                            # 다음 문제를 위해 타이머는 위쪽 'if not answered' 구역에서 재시작됨
                            st.rerun()

            # [B] 시험 결과 리포트
            else:
                if not st.session_state.exam_finished_celebrated:
                    st.balloons()
                    st.session_state.exam_finished_celebrated = True 
                st.header("📊 문제풀이 결과 리포트")
                st.caption("※ 해설을 읽은 시간은 포함되지 않고 문제를 푼 시간만 포함")
                
                total_q = len(exam)
                correct_q = st.session_state.correct_count
                accuracy = (correct_q / total_q) * 100
                total_solve_time = st.session_state.total_solving_time
                avg_time = total_solve_time / total_q
                
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("맞은 문제", f"{correct_q} / {total_q}")
                col_res2.metric("정답률", f"{accuracy:.1f}%")
                col_res3.metric("풀이 시간", f"{total_solve_time:.1f}초")
                
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
        # --- [셔플 버튼 추가 구역] ---
        col_shuffle1, col_shuffle2 = st.columns([3, 1])
        with col_shuffle1:
            st.subheader(f"관리 중인 오답: {len(wn)}개")
        with col_shuffle2:
            # 버튼을 누르면 데이터프레임을 무작위로 샘플링하여 다시 저장
            if st.button("🔀 오답 순서 섞기", use_container_width=True, key="shuffle_wn"):
                st.session_state.wrong_notes = wn.sample(frac=1).reset_index(drop=True)
                st.session_state.wn_idx = 0 # 순서가 바뀌었으므로 첫 번째 문제부터 시작
                st.toast("오답 순서가 무작위로 섞였습니다! 🎲")
                time.sleep(0.5)
                st.rerun()
        st.divider()

        # (이후 기존 네비게이션 및 문제 출력 로직...)
        if st.session_state.wn_idx >= len(wn):
            st.session_state.wn_idx = 0

        # 상단 네비게이션 바
        n1, n2, n3 = st.columns([1, 2, 1])
        with n1:
            if st.button("⬅️ 이전 오답", use_container_width=True, key="wn_prev", shortcut="ArrowLeft"):
                st.session_state.wn_idx = (st.session_state.wn_idx - 1) % len(wn); st.rerun()
        with n2:
            st.markdown(f"<p style='text-align: center; font-weight: bold;'>오답 {st.session_state.wn_idx + 1} / {len(wn)}</p>", unsafe_allow_html=True)
        with n3:
            if st.button("다음 오답 ➡️", use_container_width=True, key="wn_next_nav", shortcut="ArrowRight"):
                st.session_state.wn_idx = (st.session_state.wn_idx + 1) % len(wn); st.rerun()
        
        # 현재 인덱스의 오답 가져오기
        q_wn = wn.iloc[st.session_state.wn_idx]
        raw_year_wn_display = str(q_wn.get('연도', '미분류')).split('.')[0]
        clean_question_wn = str(q_wn["문제"]).replace('<', '〈').replace('>', '〉')

        update_tag_wn = ""
        if q_wn.get('해설업데이트') == True:
            update_tag_wn = " <span style='color: #ff4b4b; font-size: 0.8rem; border: 1px solid #ff4b4b; padding: 2px 5px; border-radius: 5px; margin-left: 10px;'>해설 업데이트</span>"
            
        st.markdown(f'<div class="question-box"><b>[{raw_year_wn_display}년]</b>{update_tag_wn}<br><br>{clean_question_wn}</div>', unsafe_allow_html=True)
        
        # 정답 입력 버튼 섹션
        cw1, cw2 = st.columns(2)
        user_choice_wn = None
        with cw1:
            if st.button("O", key="wo_o_btn", use_container_width=True, shortcut="Shift+o"): user_choice_wn = "O"
        with cw2:
            if st.button("X", key="wo_x_btn", use_container_width=True, shortcut="Shift+x"): user_choice_wn = "X"
        
        if user_choice_wn:
            c_wn_ans = str(q_wn['정답']).strip().upper()
            feedback_wn_message = ""
            
            if user_choice_wn == c_wn_ans: # 정답인 경우
                play_sound("correct.mp3")
                col_feedback_img, col_feedback_text = st.columns([0.05, 0.95], gap="small") 
                with col_feedback_img:
                    st.image("correct.jpeg", width=50) 
                with col_feedback_text:
                    st.markdown("<span class='correct-feedback-text'>정답입니다!</span>", unsafe_allow_html=True)
            else: # 오답인 경우
                play_sound("wrong.mp3")
                col_feedback_img, col_feedback_text = st.columns([0.05, 0.95], gap="small") 
                with col_feedback_img:
                    st.image("wrong.jpeg", width=50)
                with col_feedback_text:
                    st.markdown("<span class='wrong-feedback-text'>틀렸습니다! 다시 확인해 보세요.</span>", unsafe_allow_html=True)
                    
            
            with st.expander("📖 해설 확인", expanded=True):
                st.markdown(f"### 정답: {c_wn_ans}")
                st.write(q_wn['해설'])

        st.markdown("---")
        if st.button("✅ 오답노트에서 이 문제 제거", use_container_width=True, key="remove_from_wn_manual_permanent", shortcut="d"): # 버튼 key 변경
            st.session_state.wrong_notes = wn.drop(wn.index[st.session_state.wn_idx]).reset_index(drop=True)
            st.toast("선택한 문제가 오답 노트에서 제거되었습니다.")
            
            if len(st.session_state.wrong_notes) == 0:
                st.session_state.wn_idx = 0 # 오답노트가 비면 인덱스 초기화
            elif st.session_state.wn_idx >= len(st.session_state.wrong_notes):
                st.session_state.wn_idx = len(st.session_state.wrong_notes) - 1 # 마지막 문제 제거 시 이전 문제로 이동
            
            st.rerun()
        
        st.caption("이 문제를 완전히 이해하고 기억했다면 위 버튼을 눌러 오답노트에서 제거할 수 있습니다.")


# --- Tab 3: 전체 조회 ---
with tab3:
    st.header("📚 전체 문제 조회")
    st.dataframe(db, use_container_width=True)
