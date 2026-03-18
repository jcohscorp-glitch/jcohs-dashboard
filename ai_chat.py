# -*- coding: utf-8 -*-
"""Gemini AI 우측 패널 모듈 — 구글시트 Gemini Alpha 스타일"""

import streamlit as st
import google.generativeai as genai
import config

# Gemini 설정
genai.configure(api_key=config.GEMINI_API_KEY)

SYSTEM_PROMPT = """당신은 JCOHS 매출 대시보드의 AI 분석 어시스턴트입니다.
사용자가 제공하는 데이터 컨텍스트를 기반으로 매출, 광고, 키워드 등에 대한 질문에 답변합니다.

규칙:
1. 제공된 데이터 컨텍스트에는 여러 섹션(탭)의 데이터가 모두 포함되어 있습니다. 질문에 관련된 모든 섹션의 데이터를 종합하여 답변하세요.
2. 데이터에 없는 내용은 "현재 데이터에서 확인할 수 없습니다"라고 답하세요.
3. 답변은 한국어로, 간결하고 실행 가능한 인사이트 위주로 제공하세요.
4. 숫자는 읽기 쉽게 포맷하세요 (억, 백만 단위).
5. 가능하면 구체적인 액션 아이템을 제안하세요.
6. 답변은 마크다운 형식으로 깔끔하게 정리하세요.
7. 예산 변경 시뮬레이션에서 슬라이더 값은 현재 광고비 대비 증감률(%)을 의미합니다. 예: +65 = 현재 광고비에서 65% 증가.
8. 데이터 컨텍스트에 있는 수치를 적극 활용하여 구체적으로 답변하세요.
"""

# ═══════════════════════════════════════════════════════════════
#  패널 CSS
# ═══════════════════════════════════════════════════════════════
PANEL_CSS = """
<style>
/* AI 패널 헤더 */
.ai-header {
    background: linear-gradient(135deg, #4361EE 0%, #7209B7 100%);
    color: white;
    padding: 14px 18px;
    border-radius: 12px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.ai-header h4 {
    margin: 0;
    color: white !important;
    font-size: 1rem;
    font-weight: 700;
}
.ai-header .ai-badge {
    background: rgba(255,255,255,0.2);
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
}

/* 패널 우측 컬럼 스타일링 */
div[data-testid="stColumn"]:has(.ai-panel-marker) {
    background: linear-gradient(180deg, #fafbff 0%, #ffffff 100%);
    border-left: 2px solid rgba(67, 97, 238, 0.15);
    border-radius: 0 12px 12px 0;
    padding: 8px 4px !important;
}

/* 패널 내 구분선 */
div[data-testid="stColumn"]:has(.ai-panel-marker) hr {
    background: linear-gradient(90deg, transparent, rgba(67,97,238,0.15), transparent);
}

/* 채팅 메시지 스타일 */
div[data-testid="stColumn"]:has(.ai-panel-marker) [data-testid="stChatMessage"] {
    padding: 8px 10px;
    font-size: 0.88rem;
}

/* 사이즈 버튼 */
.size-btn-row { display: flex; gap: 4px; margin-bottom: 8px; }
</style>
"""


# ═══════════════════════════════════════════════════════════════
#  레이아웃 헬퍼
# ═══════════════════════════════════════════════════════════════
SIZE_RATIOS = {"S": [5, 1], "M": [7, 3], "L": [3, 2]}


def setup_layout(page_key: str):
    """페이지 상단에 AI 토글을 배치하고 레이아웃을 반환합니다.

    Returns:
        (main_col, ai_col)  — ai_col is None when panel is hidden
    """
    # 상태 초기화
    show_key = f"ai_show_{page_key}"
    size_key = f"ai_size_{page_key}"
    if show_key not in st.session_state:
        st.session_state[show_key] = False
    if size_key not in st.session_state:
        st.session_state[size_key] = "M"

    # 토글 버튼
    _left, _right = st.columns([8, 2])
    with _right:
        show = st.toggle("🤖 AI 어시스턴트", value=st.session_state[show_key],
                          key=f"ai_toggle_{page_key}")
        st.session_state[show_key] = show

    if show:
        ratio = SIZE_RATIOS.get(st.session_state[size_key], [7, 3])
        main_col, ai_col = st.columns(ratio, gap="medium")
        return main_col, ai_col
    else:
        return st.container(), None


def render_panel(ai_col, page_key: str, contexts: dict):
    """우측 AI 패널을 렌더링합니다.

    Args:
        ai_col: st.columns()에서 반환된 우측 컬럼 (None이면 스킵)
        page_key: 페이지 키 (예: "p1", "p2", "p3")
        contexts: {탭이름: 데이터요약텍스트} 딕셔너리
    """
    if ai_col is None:
        return

    with ai_col:
        # 마커 (CSS 타겟용)
        st.markdown('<div class="ai-panel-marker"></div>', unsafe_allow_html=True)
        st.markdown(PANEL_CSS, unsafe_allow_html=True)

        # 헤더
        st.markdown("""
        <div class="ai-header">
            <span style="font-size:1.3rem;">🤖</span>
            <h4>Gemini AI</h4>
            <span class="ai-badge">FLASH 2.5</span>
        </div>
        """, unsafe_allow_html=True)

        # 사이즈 조절
        size_key = f"ai_size_{page_key}"
        sc1, sc2, sc3 = st.columns(3)
        for col, (label, sz) in zip([sc1, sc2, sc3], [("S", "S"), ("M", "M"), ("L", "L")]):
            with col:
                btn_type = "primary" if st.session_state.get(size_key) == sz else "secondary"
                if st.button(label, key=f"ai_sz_{page_key}_{sz}",
                             use_container_width=True, type=btn_type):
                    st.session_state[size_key] = sz
                    st.rerun()

        # 포커스 영역 선택 (힌트용 — 전체 데이터는 항상 전달)
        tab_names = list(contexts.keys())
        selected_tab = st.selectbox("📊 포커스 영역", tab_names,
                                     key=f"ai_ctx_{page_key}",
                                     help="AI 답변 시 집중할 영역 (전체 데이터는 항상 참조)")

        # ★ 핵심: 모든 컨텍스트를 합산하여 전달 (탭 선택과 무관하게 전체 데이터 참조)
        all_context_parts = []
        for tab_name, ctx_text in contexts.items():
            marker = " ◀ [현재 포커스]" if tab_name == selected_tab else ""
            all_context_parts.append(f"=== [{tab_name}]{marker} ===\n{ctx_text}")
        data_summary = "\n\n".join(all_context_parts)

        st.markdown("---")

        # 채팅 히스토리 (페이지 단위 — 탭 변경해도 대화 유지)
        history_key = f"chat_{page_key}"
        if history_key not in st.session_state:
            st.session_state[history_key] = []

        # 메시지 컨테이너 (스크롤 가능)
        msg_box = st.container(height=480)
        with msg_box:
            if not st.session_state[history_key]:
                st.markdown("""
                <div style="text-align:center; padding:40px 10px; color:#999;">
                    <p style="font-size:2rem;">💬</p>
                    <p style="font-size:0.9rem;">데이터에 대해<br>궁금한 점을 물어보세요</p>
                    <p style="font-size:0.75rem; color:#bbb;">
                        예: "이번 달 목표 달성 가능성은?"<br>
                        "ROAS가 가장 높은 채널은?"<br>
                        "광고비 효율을 높이려면?"
                    </p>
                </div>
                """, unsafe_allow_html=True)
            for msg in st.session_state[history_key]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 입력 (form 사용 — chat_input은 페이지당 1개 제한)
        with st.form(key=f"ai_form_{page_key}", clear_on_submit=True):
            user_input = st.text_input(
                "질문", placeholder="데이터에 대해 질문하세요...",
                label_visibility="collapsed", key=f"ai_text_{page_key}",
            )
            fc1, fc2 = st.columns([3, 1])
            with fc1:
                submitted = st.form_submit_button("전송", use_container_width=True,
                                                   type="primary")
            with fc2:
                cleared = st.form_submit_button("🗑️", use_container_width=True)

        if cleared:
            st.session_state[history_key] = []
            st.rerun()

        if submitted and user_input:
            st.session_state[history_key].append({"role": "user", "content": user_input})

            try:
                model = _get_model()
                context = _build_context(data_summary, selected_tab)

                # 대화 히스토리 → Gemini 포맷
                messages = [
                    {"role": "user", "parts": [context + "\n\n위 데이터를 참고하여 답변해주세요."]},
                    {"role": "model", "parts": ["네, 위의 전체 데이터를 참고하여 답변하겠습니다. 어떤 질문이든 해주세요."]},
                ]
                for msg in st.session_state[history_key][:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    messages.append({"role": role, "parts": [msg["content"]]})
                messages.append({"role": "user", "parts": [user_input]})

                chat = model.start_chat(history=messages[:-1])
                response = chat.send_message(user_input)
                answer = response.text

            except Exception as e:
                answer = f"⚠️ AI 응답 오류: {str(e)}"

            st.session_state[history_key].append({"role": "assistant", "content": answer})
            st.rerun()


# ═══════════════════════════════════════════════════════════════
#  Gemini 모델
# ═══════════════════════════════════════════════════════════════
def _get_model():
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )


def _build_context(data_summary: str, focus_tab: str) -> str:
    return (
        f"[대시보드 전체 데이터 컨텍스트]\n"
        f"[사용자 포커스 영역: {focus_tab}]\n\n"
        f"{data_summary}"
    )


# ═══════════════════════════════════════════════════════════════
#  데이터 요약 헬퍼
# ═══════════════════════════════════════════════════════════════
def summarize_dataframe(df, name: str, max_rows: int = 20) -> str:
    """DataFrame을 텍스트 요약으로 변환"""
    if df is None or df.empty:
        return f"{name}: 데이터 없음"

    lines = [f"[{name}] ({len(df)}행 x {len(df.columns)}열)"]
    lines.append(f"컬럼: {', '.join(df.columns.tolist())}")

    num_cols = df.select_dtypes(include="number").columns.tolist()
    if num_cols:
        stats = []
        for col in num_cols[:10]:
            total = df[col].sum()
            mean = df[col].mean()
            if total > 1e8:
                stats.append(f"  {col}: 합계={total/1e8:.2f}억, 평균={mean/1e6:.1f}백만")
            elif total > 1e6:
                stats.append(f"  {col}: 합계={total/1e6:.1f}백만, 평균={mean:,.0f}")
            else:
                stats.append(f"  {col}: 합계={total:,.0f}, 평균={mean:,.1f}")
        lines.append("수치 요약:\n" + "\n".join(stats))

    sample = df.head(max_rows).to_string(index=False, max_colwidth=30)
    lines.append(f"상위 {min(max_rows, len(df))}행:\n{sample}")

    return "\n".join(lines)


def summarize_metrics(**kwargs) -> str:
    """KPI 메트릭을 텍스트로 변환"""
    lines = []
    for key, value in kwargs.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
