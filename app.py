import streamlit as st
import pandas as pd
import random
import os
import time
import json

# --- [1. 팝업창 및 페이지 설정] ---
@st.dialog("📖 사용방법 가이드", width="large")
def show_manual():
    if os.path.exists("manual.png"):
        st.image("manual.png", use_container_width=True)
    else:
        st.error("manual.png 파일을 찾을 수 없습니다. GitHub에 파일을 올려주세요.")
    st.caption("닫으려면 창 바깥쪽을 클릭하거나 우측 상단 X를 누르세요.")

st.set_page_config(page_title="형사법 기출 연습 (2021-2026)", layout="wide", page_icon="⚖️")

# --- [2. CSS 디자인 (간격 및 가독성)] ---
st.markdown("""
    <style>
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
    .stButton>button {
        height: 3em;
        font-size: 16px !important;
        font-weight: bold !important;
        color: #ffffff !important;
        background-color: #262730;
        border-radius: 8px;
    }
    /* 사이드바 촘촘하게 */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
    [data-testid="stSidebar"] hr { margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- [3. 데이터 로드 및 집단지성 로직] ---
SHEET_ID = "14ShaWll86F40k94P_M40aq8TNwB19a3XvO1w6Xxik1s"
GID_MAP = {2021: "2095370762", 2022: "1893230281", 2023: "1090949368", 2024: "781284367", 2025: "251633672", 2026: "0"}

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

def update_from_sheets(current_db, selected_years):
    update_log = []
    updated_db = current_db.copy()
    for year in selected_years:
        gid = GID_MAP.get(year, "0")
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        try:
            sheet_df = pd.read_csv(url)
            for idx, row in sheet_df.iterrows():
                target_mask = updated_db['문제'] == row['문제']
                if target_mask.any():
                    old_exp = updated_db.loc[target_mask, '해설'].values[0]
                    if str(old_exp) != str(row['해설']):
                        updated_db.loc[target_mask, '해설'] = row['해설']
                        update_log.append({"연도": f"{year}년", "문제": row['문제'][:30] + "...", "바뀐 해설": row['해설']})
        except: continue
    return updated_db, update_log

# --- [4. 세션 상태 초기화] ---
if 'db' not in st.session_state: st.session_state.db = pd.DataFrame()
if 'wrong_notes' not in st.session_state: st.session_state.wrong_notes = pd.DataFrame(columns=['문제', '정답', '해설', '연도'])
if 'exam_list' not in st.session_state: st.session_state.exam_list = []
if 'idx' not in st.session_state: st.session_state.idx = 0
if 'answered' not in st.session_state: st.session_state.answered = False
if 'correct_count' not in st.session_state: st.session_state.correct_count = 0
if 'total_solving_time' not in st.session_state: st.session_state.total_solving_time = 0.0
if 'q_start_time' not in st.session_state: st.session_state.q_start_time = None
if 'wn_idx' not in st.session_state: st.session_state.wn_idx = 0
if 'update_history' not in st.session_state: st.session_state.update_history = []

# --- [5. 사이드바 구역] ---
with st.sidebar:
    st.title("⚖️ 설정")
    if st.button("📖 사용방법 보기", use_container_width=True):
        show_manual()
    st.divider()
    
    st.subheader("📅 범위 선택")
    available_years = [2021, 2022, 2023, 2024, 2025, 2026]
    selected_years = st.multiselect("학습 연도 선택", available_years, default=[2026])
    if st.button("📁 데이터 불러오기", use_container_width=True):
        st.session_state.db = load_local_data(selected_years)
        st.success(f"{len(st.session_state.db)}개 문항 로드 완료!")

    st.divider()
    st.subheader("🧠 집단지성")
    if st.button("✨ 최신 해설 업데이트", use_container_width=True):
        if st.session_state.db.empty: st.warning("데이터를 먼저 불러오세요.")
        else:
            with st.spinner("업데이트 중..."):
                st.session_state.db, logs = update_from_sheets(st.session_state.db, selected_years)
                st.session_state.update_history = logs
                st.toast("업데이트 완료!")

    st.divider()
    st.subheader("⏯️ 진행상황 통합 저장(JSON)")
    if not st.session_state.db.empty:
        backup = {
            "exam_list": st.session_state.exam_list, "idx": st.session_state.idx,
            "correct_count": st.session_state.correct_count, "total_solving_time": st.session_state.total_solving_time,
            "wrong_notes": st.session_state.wrong_notes.to_dict('records'), "selected_years": selected_years
        }
        st.download_button("📥 전체 백업 저장", json.dumps(backup, ensure_ascii=False), "full_backup.json", "application/json", use_container_width=True)
    
    up_json = st.file_uploader("📤 백업 불러오기", type="json")
    if up_json:
        try:
            data = json.load(up_json)
            st.session_state.db = load_local_data(data.get("selected_years", [2026]))
            st.session_state.exam_list = data.get("exam_list", [])
            st.session_state.idx = data.get("idx", 0); st.session_state.correct_count = data.get("correct_count", 0)
            st.session_state.total_solving_time = data.get("total_solving_time", 0.0)
            st.session_state.wrong_notes = pd.DataFrame(data.get("wrong_notes", []))
            st.session_state.answered = False; st.session_state.q_start_time = time.time(); st.rerun()
        except: st.error("복구 실패")

    st.divider()
    st.subheader("💾 오답노트 개별 관리(CSV)")
    csv_data = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 오답노트만 저장", csv_data, "my_wrong_notes.csv", "text/csv", use_container_width=True)
    
    up_csv = st.file_uploader("📤 오답노트만 복구", type="csv")
    if up_csv:
        st.session_state.wrong_notes = pd.read_csv(up_csv)
        st.success("오답노트 복구 완료!"); st.rerun()

    st.divider()
    st.markdown(f"""
        <div style="font-size: 0.8rem; color: #888888; line-height: 1.2; margin-top: -10px;">
        16기 유각준<br>(15기 김새봄 선배님이 배포하신 프로그램의 작동방식을 거의 그대로 따랐으며, 로데이터도 그대로 사용함)
        </div>
    """, unsafe_allow_html=True)

# --- [6. 메인 화면] ---
st.title("⚖️ 형사법 선택형 기출 연습")
tab1, tab2, tab3 = st.tabs(["📝 중간고사 연습", "❌ 오답 집중 복습", "📚 전체 조회"])

db = st.session_state.db

with tab1:
    if db.empty: st.info("사이드바에서 '데이터 불러오기'를 눌러주세요.")
    else:
        num = st.number_input("문항 수", 1, len(db), min(10, len(db)), key="m_num")
        if st.button("🚀 새 시험 시작", use_container_width=True):
            st.session_state.exam_list = db.sample(n=num).to_dict('records')
            st.session_state.idx = 0; st.session_state.answered = False; st.session_state.correct_count = 0
            st.session_state.total_solving_time = 0.0; st.session_state.q_start_time = time.time(); st.rerun()

        if st.session_state.exam_list:
            idx, exam = st.session_state.idx, st.session_state.exam_list
            if idx < len(exam):
                q = exam[idx]
                if not st.session_state.answered and st.session_state.q_start_time is None: st.session_state.q_start_time = time.time()
                st.progress((idx + 1) / len(exam))
                ry = str(q.get('연도', '미분류')).split('.')[0]
                st.write(f"**문제 {idx+1} / {len(exam)}** ({ry}년)")
                st.markdown(f'<div class="question-box">{q["문제"]}</div>', unsafe_allow_html=True)
                
                u_in, c1, c2, c3 = None, *st.columns(3)
                with c1: 
                    if st.button("O", key=f"o_{idx}", use_container_width=True): u_in = "O"
                with c2: 
                    if st.button("X", key=f"x_{idx}", use_container_width=True): u_in = "X"
                with c3: 
                    if st.button("?", key=f"q_{idx}", use_container_width=True): u_in = "?"

                if u_in and not st.session_state.answered:
                    st.session_state.total_solving_time += (time.time() - st.session_state.q_start_time)
                    st.session_state.q_start_time = None; st.session_state.answered = True
                    ans = str(q['정답']).strip().upper()
                    is_correct = (u_in == ans) if u_in != "?" else False
                    st.session_state.last_is_correct = is_correct
                    if is_correct: st.session_state.correct_count += 1; st.success("정답입니다! ✨")
                    else: 
                        st.error(f"오답입니다. (정답: {ans})")
                        if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                            st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, pd.DataFrame([q])], ignore_index=True)

                if st.session_state.answered:
                    with st.expander("📖 해설 보기", expanded=True): st.write(q['해설'])
                    cn1, cn2 = st.columns(2)
                    with cn1:
                        if st.session_state.last_is_correct:
                            if st.button("🤔 오답노트 추가", key=f"ma_{idx}", use_container_width=True):
                                if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                                    st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, pd.DataFrame([q])], ignore_index=True)
                                    st.toast("추가 완료!")
                    with cn2:
                        label = "결과 확인 📊" if idx == len(exam)-1 else "다음 문제 ➡️"
                        if st.button(label, key=f"nx_{idx}", use_container_width=True):
                            st.session_state.idx += 1; st.session_state.answered = False; st.rerun()
            else:
                st.balloons(); st.header("📊 시험 결과 리포트")
                total_q, correct_q = len(exam), st.session_state.correct_count
                t_solve = st.session_state.total_solving_time
                r1, r2, r3 = st.columns(3)
                r1.metric("맞은 문제", f"{correct_q} / {total_q}")
                r2.metric("정답률", f"{(correct_q/total_q*100):.1f}%")
                r3.metric("순수 풀이 시간", f"{t_solve:.1f}초")
                st.metric("문제당 평균 시간", f"{(t_solve/total_q):.1f}초")
                if st.button("시험 종료 및 초기화 🔄", use_container_width=True): st.session_state.exam_list = []; st.rerun()

with tab2:
    wn = st.session_state.wrong_notes
    if wn.empty: st.info("오답 노트가 비어 있습니다.")
    else:
        if st.session_state.wn_idx >= len(wn): st.session_state.wn_idx = 0
        n1, n2, n3 = st.columns([1,2,1])
        with n1:
            if st.button("⬅️ 이전", key="wp"): st.session_state.wn_idx = (st.session_state.wn_idx - 1) % len(wn); st.rerun()
        with n2: st.markdown(f"<p style='text-align:center;'>{st.session_state.wn_idx + 1} / {len(wn)}</p>", unsafe_allow_html=True)
        with n3:
            if st.button("다음 ➡️", key="wn"): st.session_state.wn_idx = (st.session_state.wn_idx + 1) % len(wn); st.rerun()
        qw = wn.iloc[st.session_state.wn_idx]
        ry_w = str(qw.get('연도', '미분류')).split('.')[0]
        st.markdown(f'<div class="question-box"><b>[{ry_w}년]</b><br><br>{qw["문제"]}</div>', unsafe_allow_html=True)
        cw1, cw2 = st.columns(2)
        act = None
        with cw1:
            if st.button("O!", key="wo1"): act = "O!"
            if st.button("O", key="wo2"): act = "O"
        with cw2:
            if st.button("X!", key="wx1"): act = "X!"
            if st.button("X", key="wx2"): act = "X"
        if act:
            if act[0] == str(qw['정답']).strip().upper():
                if "!" in act:
                    st.session_state.wrong_notes = wn.drop(wn.index[st.session_state.wn_idx]).reset_index(drop=True)
                    st.success("삭제됨!"); st.rerun()
                else: st.info("정답!")
            else: st.error("오답!")
            with st.expander("📖 해설", expanded=True): st.write(qw['해설'])

with tab3:
    if not db.empty: st.dataframe(db, use_container_width=True)
