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
        st.error("manual.png 파일을 찾을 수 없습니다.")
    st.caption("닫으려면 창 바깥쪽을 클릭하거나 우측 상단 X를 누르세요.")

st.set_page_config(page_title="형사법 기출 연습 (2021-2026)", layout="wide", page_icon="⚖️")

# --- [2. CSS 디자인] ---
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
        height: 3em; font-size: 16px !important; font-weight: bold !important;
        color: #ffffff !important; background-color: #262730; border-radius: 8px;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
    [data-testid="stSidebar"] hr { margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- [3. 데이터 로드 로직] ---
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

# --- [4. 세션 상태 초기화 (중요: selected_years 추가)] ---
if 'db' not in st.session_state: st.session_state.db = pd.DataFrame()
if 'wrong_notes' not in st.session_state: st.session_state.wrong_notes = pd.DataFrame(columns=['문제', '정답', '해설', '연도'])
if 'exam_list' not in st.session_state: st.session_state.exam_list = []
if 'idx' not in st.session_state: st.session_state.idx = 0
if 'answered' not in st.session_state: st.session_state.answered = False
if 'correct_count' not in st.session_state: st.session_state.correct_count = 0
if 'total_solving_time' not in st.session_state: st.session_state.total_solving_time = 0.0
if 'q_start_time' not in st.session_state: st.session_state.q_start_time = None
if 'wn_idx' not in st.session_state: st.session_state.wn_idx = 0
if 'last_restored' not in st.session_state: st.session_state.last_restored = None
# 현재 선택된 연도를 세션에 저장 (백업 불러오기 시 UI와 동기화 위함)
if 'selected_years' not in st.session_state: st.session_state.selected_years = [2026]

# --- [5. 사이드바 구역] ---
with st.sidebar:
    st.title("⚖️ 설정")
    if st.button("📖 사용방법 보기", use_container_width=True):
        show_manual()
    st.divider()
    
    st.subheader("📅 범위 선택")
    available_years = [2021, 2022, 2023, 2024, 2025, 2026]
    # 위젯의 현재 값을 세션 변수와 연동
    st.session_state.selected_years = st.multiselect("학습 연도 선택", available_years, default=st.session_state.selected_years)
    
    if st.button("📁 선택 범위 데이터 불러오기", use_container_width=True):
        st.session_state.db = load_local_data(st.session_state.selected_years)
        st.toast(f"{len(st.session_state.db)}개 문항 로드 완료!")

    st.divider()
    st.subheader("⏯️ 진행상황 통합 저장(JSON)")
    # 백업 데이터 구성
    backup = {
        "exam_list": st.session_state.exam_list, "idx": st.session_state.idx,
        "correct_count": st.session_state.correct_count, "total_solving_time": st.session_state.total_solving_time,
        "wrong_notes": st.session_state.wrong_notes.to_dict('records'), 
        "selected_years": st.session_state.selected_years # 저장 당시 연도 포함
    }
    st.download_button("📥 전체 상태 백업 저장", json.dumps(backup, ensure_ascii=False), "quiz_backup.json", "application/json", use_container_width=True)
    
    up_json = st.file_uploader("📤 백업 불러오기", type="json", key="restore_uploader")
    if up_json and st.session_state.last_restored != up_json.name:
        try:
            data = json.load(up_json)
            # [핵심 수정] 불러온 파일의 연도 정보를 세션에 먼저 주입 (UI 자동 변경됨)
            restored_years = data.get("selected_years", [2026])
            st.session_state.selected_years = restored_years
            
            # 데이터 로드 및 상태 복구
            st.session_state.db = load_local_data(restored_years)
            st.session_state.exam_list = data.get("exam_list", [])
            st.session_state.idx = data.get("idx", 0)
            st.session_state.correct_count = data.get("correct_count", 0)
            st.session_state.total_solving_time = data.get("total_solving_time", 0.0)
            st.session_state.wrong_notes = pd.DataFrame(data.get("wrong_notes", []))
            st.session_state.answered = False
            st.session_state.q_start_time = time.time()
            st.session_state.last_restored = up_json.name
            should_rerun = True
        except: st.error("복구 실패")
            
    if should_rerun:
        st.rerun()
        
    st.divider()
    st.subheader("💾 오답노트 개별 관리(CSV)")
    csv_data = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 오답노트만 저장", csv_data, "my_wrong_notes.csv", "text/csv", use_container_width=True)
    up_csv = st.file_uploader("📤 오답노트만 복구", type="csv")
    if up_csv:
        try: st.session_state.wrong_notes = pd.read_csv(up_csv); st.toast("복구 완료!")
        except: st.sidebar.error("CSV 읽기 실패")

    st.divider()
    st.markdown(f"""
        <div style="font-size: 0.8rem; color: #888888; line-height: 1.2; margin-top: -10px;">
        16기 유각준<br>(15기 김새봄 선배님 프로그램 벤치마킹 및 로데이터 사용)<br>
        <span style="color: #555555;"><b>원래 나만 쓰려고 만들었는데 특별히 김사빈도 쓸 수 있음</b></span>
        </div>
    """, unsafe_allow_html=True)

# --- [6. 메인 화면 - 탭 구성] ---
st.title("⚖️ 형사법 선택형 기출 연습")
tab1, tab2, tab3 = st.tabs(["📝 중간고사 연습", "❌ 오답 집중 복습", "📚 전체 조회"])

# --- Tab 1: 중간고사 연습 ---
with tab1:
    if st.session_state.db.empty: st.info("사이드바에서 '데이터 불러오기'를 눌러주세요.")
    else:
        num = st.number_input("문항 수", 1, len(st.session_state.db), min(10, len(st.session_state.db)), key="m_num")
        if st.button("🚀 새 시험 시작", use_container_width=True, key="start_exam_btn"):
            st.session_state.exam_list = st.session_state.db.sample(n=num).to_dict('records')
            st.session_state.idx = 0; st.session_state.answered = False; st.session_state.correct_count = 0
            st.session_state.total_solving_time = 0.0; st.session_state.q_start_time = time.time(); st.rerun()

        if st.session_state.exam_list:
            idx, exam = st.session_state.idx, st.session_state.exam_list
            if idx < len(exam):
                q = exam[idx]
                if not st.session_state.answered and st.session_state.q_start_time is None:
                    st.session_state.q_start_time = time.time()
                
                st.progress((idx + 1) / len(exam))
                ry = str(q.get('연도', '미분류')).split('.')[0]
                st.write(f"**문제 {idx+1} / {len(exam)}** ({ry}년)")
                st.markdown(f'<div class="question-box">{q["문제"]}</div>', unsafe_allow_html=True)
                
                u_in, c1, c2, c3 = None, *st.columns(3)
                with c1: 
                    if st.button("⭕ O", key=f"o_{idx}", use_container_width=True): u_in = "O"
                with c2: 
                    if st.button("❌ X", key=f"x_{idx}", use_container_width=True): u_in = "X"
                with c3: 
                    if st.button("❓ ?", key=f"q_{idx}", use_container_width=True): u_in = "?"

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
                            if st.button("🤔 내 생각과 다름 ➡️ 오답노트 추가", key=f"ma_{idx}", use_container_width=True):
                                if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                                    st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, pd.DataFrame([q])], ignore_index=True)
                                    st.toast("추가 완료!")
                    with cn2:
                        label = "결과 확인 📊" if idx == len(exam)-1 else "다음 문제 ➡️"
                        if st.button(label, key=f"nx_{idx}", use_container_width=True):
                            st.session_state.idx += 1; st.session_state.answered = False; st.rerun()
            else:
                st.balloons(); st.header("📊 시험 결과 리포트")
                total_q = len(exam); acc = (st.session_state.correct_count / total_q) * 100
                t_solve = st.session_state.total_solving_time
                r1, r2, r3 = st.columns(3)
                r1.metric("맞은 문제", f"{st.session_count} / {total_q}" if 'st.session_count' in locals() else f"{st.session_state.correct_count} / {total_q}")
                r1.metric("맞은 문제", f"{st.session_state.correct_count} / {total_q}")
                r2.metric("정답률", f"{acc:.1f}%")
                r3.metric("순수 풀이 시간", f"{t_solve:.1f}초")
                st.metric("문제당 평균 시간", f"{(t_solve/total_q):.1f}초")
                if st.button("시험 종료 및 초기화 🔄", use_container_width=True): 
                    st.session_state.exam_list = []; st.session_state.idx = 0; st.rerun()

with tab2:
    wn = st.session_state.wrong_notes
    if wn.empty: st.info("오답 노트가 비어 있습니다.")
    else:
        if st.session_state.wn_idx >= len(wn): st.session_state.wn_idx = 0
        n1, n2, n3 = st.columns([1,2,1])
        with n1:
            if st.button("⬅️ 이전", key="wn_p"): st.session_state.wn_idx = (st.session_state.wn_idx - 1) % len(wn); st.rerun()
        with n2: st.markdown(f"<p style='text-align:center;'>{st.session_state.wn_idx + 1} / {len(wn)}</p>", unsafe_allow_html=True)
        with n3:
            if st.button("다음 ➡️", key="wn_n"): st.session_state.wn_idx = (st.session_state.wn_idx + 1) % len(wn); st.rerun()
        
        qw = wn.iloc[st.session_state.wn_idx]
        ry_w = str(qw.get('연도', '미분류')).split('.')[0]
        st.markdown(f'<div class="question-box"><b>[{ry_w}년]</b><br><br>{qw["문제"]}</div>', unsafe_allow_html=True)
        cw1, cw2 = st.columns(2)
        act = None
        with cw1:
            if st.button("O !", key="w_o1"): act = "O!"
            if st.button("O", key="w_o2"): act = "O"
        with cw2:
            if st.button("X !", key="w_x1"): act = "X!"
            if st.button("X", key="w_x2"): act = "X"
        if act:
            if act[0] == str(qw['정답']).strip().upper():
                if "!" in act:
                    st.session_state.wrong_notes = wn.drop(wn.index[st.session_state.wn_idx]).reset_index(drop=True)
                    st.toast("삭제됨!"); time.sleep(0.5); st.rerun()
                else: st.info("정답!")
            else: st.error("오답!")
            with st.expander("📖 해설", expanded=True): st.write(qw['해설'])

with tab3:
    if not st.session_state.db.empty: st.dataframe(st.session_state.db, use_container_width=True)
