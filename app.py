import streamlit as st
import pandas as pd
import random

# --- 설정 및 초기화 ---
st.set_page_config(page_title="변시 형사법 마스터", layout="wide", page_icon="⚖️")

# 데이터 소스 (구글 스프레드시트 공유 시 'CSV로 웹에 게시'한 URL을 입력하면 실시간 동기화됨)
# 우선은 사용자가 처음에 제공한 데이터를 기본값으로 설정합니다.
DEFAULT_DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT-본인의_구글시트_ID/pub?output=csv"

if 'db' not in st.session_state:
    st.session_state.db = None
if 'wrong_notes' not in st.session_state:
    st.session_state.wrong_notes = pd.DataFrame(columns=['문제', '정답', '해설'])
if 'current_exam' not in st.session_state:
    st.session_state.current_exam = []
if 'exam_idx' not in st.session_state:
    st.session_state.exam_idx = 0
if 'show_result' not in st.session_state:
    st.session_state.show_result = False

# --- 함수 정의 ---
def load_data(url):
    try:
        df = pd.read_csv(url)
        return df
    except:
        # 데이터 로드 실패 시 예시 데이터 반환 (사용자가 준 텍스트 기반)
        data = {
            "문제": ["피해자의 승낙이 객관적으로 존재하는데도 불구하고 행위자가 이를 알지 못하고 행위한 경우에는 위법성조각사유의 전제사실의 착오가 되어 위법성이 조각되지 않는다.", "묵시적 승낙이 있는 경우에도 피해자의 승낙에 의해 위법성이 조각될 수 있다."],
            "정답": ["X", "O"],
            "해설": ["주관적 정당화요소가 결여된 경우에 해당한다.", "2008도6940 판례 참조"]
        }
        return pd.DataFrame(data)

def start_exam(num_q):
    all_indices = list(range(len(st.session_state.db)))
    selected_indices = random.sample(all_indices, min(num_q, len(all_indices)))
    st.session_state.current_exam = st.session_state.db.iloc[selected_indices].to_dict('records')
    st.session_state.exam_idx = 0
    st.session_state.show_result = False

# --- 사이드바 (설정 및 집단지성) ---
with st.sidebar:
    st.title("⚙️ 프로그램 설정")
    
    # 1. 데이터 업데이트 (집단지성)
    st.subheader("🌐 집단지성 해설 업데이트")
    sheet_url = st.text_input("구글 시트 CSV URL", DEFAULT_DATA_URL)
    if st.button("🔄 최신 해설로 업데이트"):
        st.session_state.db = load_data(sheet_url)
        st.success("데이터가 성공적으로 업데이트되었습니다!")
    
    if st.session_state.db is None:
        st.session_state.db = load_data(sheet_url)

    st.divider()
    
    # 2. 오답 노트 관리
    st.subheader("💾 오답 노트 백업/복구")
    # 파일 내보내기
    csv = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 오답노트 다운로드(CSV)", csv, "wrong_notes.csv", "text/csv")
    
    # 파일 불러오기
    uploaded_wrong = st.file_uploader("📤 오답노트 불러오기", type="csv")
    if uploaded_wrong:
        st.session_state.wrong_notes = pd.read_csv(uploaded_wrong)
        st.success("오답노트를 불러왔습니다.")

# --- 메인 화면 레이아웃 ---
st.title("🎓 변시 형사법 선택형 연습")

menu = st.tabs(["📝 중간고사 모드", "❌ 오답 노트 모드", "📖 전체 문제 보기"])

# 1. 중간고사 모드
with menu[0]:
    st.header("1. midterm.exe - 무작위 출제")
    col1, col2 = st.columns([1, 3])
    with col1:
        num_q = st.number_input("문항 수 설정", min_value=1, max_value=len(st.session_state.db), value=5)
        if st.button("🚀 시험 시작"):
            start_exam(num_q)
            st.rerun()
            
    if st.session_state.current_exam:
        q_list = st.session_state.current_exam
        idx = st.session_state.exam_idx
        
        if idx < len(q_list):
            curr_q = q_list[idx]
            st.progress((idx+1) / len(q_list))
            st.write(f"**문제 {idx+1} / {len(q_list)}**")
            st.info(curr_q['문제'])
            
            # 입력 방식 (설명 기반: O, X, O?, X?, ?)
            ans_col = st.columns(5)
            user_input = None
            with ans_col[0]: 
                if st.button("O"): user_input = "O"
            with ans_col[1]: 
                if st.button("X"): user_input = "X"
            with ans_col[2]: 
                if st.button("O? (확신없음)"): user_input = "O?"
            with ans_col[3]: 
                if st.button("X? (확신없음)"): user_input = "X?"
            with ans_col[4]: 
                if st.button("? (모름)"): user_input = "?"

            if user_input:
                # 판정 로직
                is_correct = user_input[0] == curr_q['정답'] if user_input != "?" else False
                needs_wrong_note = ("?" in user_input) or (not is_correct)
                
                if needs_wrong_note:
                    # 오답노트 추가
                    if curr_q['문제'] not in st.session_state.wrong_notes['문제'].values:
                        new_row = pd.DataFrame([curr_q])
                        st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, new_row], ignore_index=True)
                    st.error(f"결과: {'정답이지만 확신 없음' if is_correct else '오답'} ➡️ 오답 노트에 기록되었습니다.")
                else:
                    st.success("완벽한 정답입니다! 🎉")
                
                st.session_state.show_result = True
                st.session_state.last_result = {"정답": curr_q['정답'], "해설": curr_q['해설']}

            if st.session_state.show_result:
                st.write(f"**정답: {st.session_state.last_result['정답']}**")
                st.write(f"**해설:** {st.session_state.last_result['해설']}")
                if st.button("다음 문제 ➡️"):
                    st.session_state.exam_idx += 1
                    st.session_state.show_result = False
                    st.rerun()
        else:
            st.balloons()
            st.success("시험 종료! 오답 노트를 확인하세요.")
            if st.button("새 시험 시작"):
                st.session_state.current_exam = []
                st.rerun()

# 2. 오답 노트 모드
with menu[1]:
    st.header("2. wrong_note.exe - 집중 복습")
    if len(st.session_state.wrong_notes) == 0:
        st.write("클린 상태입니다! 틀린 문제가 없습니다.")
    else:
        st.write(f"현재 관리 중인 오답: **{len(st.session_state.wrong_notes)}개**")
        
        # 오답 노트는 하나씩 넘기며 풀기
        if 'wn_idx' not in st.session_state: st.session_state.wn_idx = 0
        
        wn_idx = st.session_state.wn_idx % len(st.session_state.wrong_notes)
        curr_wn = st.session_state.wrong_notes.iloc[wn_idx]
        
        st.warning(f"오답 문제:")
        st.write(curr_wn['문제'])
        
        col_wn1, col_wn2 = st.columns(2)
        wn_input = None
        with col_wn1:
            if st.button("O!"): wn_input = "O!"
            if st.button("O"): wn_input = "O"
        with col_wn2:
            if st.button("X!"): wn_input = "X!"
            if st.button("X"): wn_input = "X"
            
        if wn_input:
            is_wn_correct = wn_input[0] == curr_wn['정답']
            if is_wn_correct:
                if "!" in wn_input:
                    st.session_state.wrong_notes = st.session_state.wrong_notes.drop(st.session_state.wrong_notes.index[wn_idx]).reset_index(drop=True)
                    st.success("확실히 아는 문제로 판정되어 오답 노트에서 삭제되었습니다! ✨")
                else:
                    st.info("정답입니다. (아직 오답 노에 유지)")
            else:
                st.error("또 틀렸습니다. 다시 공부하세요!")
            
            st.write(f"**정답: {curr_wn['정답']}**")
            st.write(f"**해설:** {curr_wn['해설']}")
            
            if st.button("다음 오답 보기 ➡️"):
                st.session_state.wn_idx += 1
                st.rerun()

# 3. 전체 데이터 보기 (집단지성 링크)
with menu[2]:
    st.header("3. 데이터 조회 및 수정")
    st.write("해설이 부족하거나 수정이 필요하면 아래 링크를 통해 직접 참여하세요.")
    st.markdown("[🔗 구글 스프레드시트 바로가기 (집단지성)](https://docs.google.com/spreadsheets/d/your_spreadsheet_link)")
    st.dataframe(st.session_state.db, use_container_width=True)