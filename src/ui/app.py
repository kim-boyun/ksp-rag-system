"""
KSP Knowledge Hub — Chatbot UI
"""
import sys
import time
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from ragapp.pipeline.rag_pipeline import RAGPipeline
from ragapp.config import get_config
from ragapp.prompts import extract_citations


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (인용·문서 렌더러는 유지 — 추후 재활성화 가능)
# ─────────────────────────────────────────────────────────────────────────────

def _display_name(metadata: dict) -> str:
    meta = metadata or {}
    path = meta.get("source_path") or ""
    if path:
        return Path(path).name
    doc_id = meta.get("doc_id") or ""
    if doc_id and doc_id != "Unknown":
        return doc_id
    chunk_id = meta.get("chunk_id") or ""
    if chunk_id:
        for sep in ("_p", "_table", "_figure"):
            if sep in chunk_id:
                return chunk_id.split(sep)[0]
        return chunk_id
    return "Unknown"


def _short_name(name: str, max_len: int = 48) -> str:
    stem = Path(name).stem
    suffix = Path(name).suffix
    if len(name) <= max_len:
        return name
    return stem[: max_len - len(suffix) - 1] + "…" + suffix


def _relevance_label(score: float) -> tuple[str, str]:
    pct = min(score, 1.0)
    if pct >= 0.75:
        return "높음", "#059669"
    if pct >= 0.45:
        return "보통", "#D97706"
    return "낮음", "#94A3B8"


def _content_type_icon(ct: str) -> str:
    icons = {"table": "📊", "figure": "🖼️", "text": "📝"}
    return icons.get((ct or "text").lower(), "📝")


# ── 인용 출처 렌더러 (추후 재활성화 가능) ─────────────────────────────────────
def _render_citations(citations: list, docs: list):
    pass  # reserved


# ── 참고 문서 렌더러 (답변 하단 expander) ─────────────────────────────────────
def _normalize_scores_to_01(docs: list) -> list:
    """이번 결과 내 최소·최대로 점수를 0~1로 표준화."""
    if not docs:
        return []
    min_s = min(d.score for d in docs)
    max_s = max(d.score for d in docs)
    if max_s <= min_s:
        return [1.0] * len(docs)
    return [(d.score - min_s) / (max_s - min_s) for d in docs]


def _render_source_docs(docs: list, citations: list):
    if not docs:
        return
    cited_nums = {c.get("doc_num") for c in (citations or [])}
    norm_scores = _normalize_scores_to_01(docs)
    with st.expander(f"📄 참고 문서 ({len(docs)}건)", expanded=False):
        st.caption(
            "점수는 이번 결과 안에서 0~1로 표준화했습니다. 1에 가까울수록 상대적으로 관련도가 높습니다."
        )
        for i, doc in enumerate(docs, 1):
            name = _short_name(_display_name(doc.metadata))
            page = doc.metadata.get("page_num", "N/A")
            ct = doc.metadata.get("content_type", "text")
            ct_icon = _content_type_icon(ct)
            norm_score = norm_scores[i - 1] if i <= len(norm_scores) else 0.0
            rel_label, rel_color = _relevance_label(norm_score)
            cited_marker = " 🔗" if i in cited_nums else ""
            preview = doc.content[:200].strip().replace("\n", " ")
            if len(doc.content) > 200:
                preview += "…"
            st.markdown(
                f"**{i}. {name}{cited_marker}** &nbsp; {ct_icon} {ct} · 페이지 {page} &nbsp; "
                f"<span style='font-size:0.75rem;color:{rel_color};background:{rel_color}22;padding:2px 6px;border-radius:4px;'>{rel_label} {norm_score:.2f}</span>  \n"
                f"<span style='font-size:0.82rem;color:#64748B;'>{preview}</span>",
                unsafe_allow_html=True,
            )
            if i < len(docs):
                st.markdown(
                    "<hr style='border:none;border-top:1px solid #E2E8F0;margin:8px 0;'>",
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="KSP Knowledge Hub",
    page_icon="📘",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── 전역 ── */
.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 780px !important;
}

/* ── 헤더 타이틀 ── */
.chat-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
}
.chat-logo {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #2563EB 0%, #0EA5E9 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    box-shadow: 0 3px 10px rgba(37,99,235,0.25);
}
.chat-title {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0;
    color: #0F172A;
}
.chat-subtitle {
    font-size: 0.8rem;
    color: #64748B;
    margin: 0;
}

/* ── 다크 모드 ── */
[data-theme="dark"] .chat-title {
    color: #F8FAFC !important;
}
[data-theme="dark"] .chat-subtitle {
    color: #CBD5E1 !important;
}
[data-theme="dark"] [data-testid="stSidebar"] {
    background: #1E293B !important;
    border-right: 1px solid #334155 !important;
}
[data-theme="dark"] [data-testid="stSidebar"] p,
[data-theme="dark"] [data-testid="stSidebar"] span,
[data-theme="dark"] [data-testid="stSidebar"] label,
[data-theme="dark"] [data-testid="stSidebar"] .stMarkdown {
    color: #E2E8F0 !important;
}
[data-theme="dark"] [data-testid="stSidebar"] small,
[data-theme="dark"] [data-testid="stSidebar"] .stCaptionContainer {
    color: #94A3B8 !important;
}
[data-theme="dark"] [data-testid="stSidebar"] .stButton > button {
    background: #2563EB !important;
    color: #FFFFFF !important;
    border: 1px solid #3B82F6 !important;
}
[data-theme="dark"] [data-testid="stSidebar"] .stButton > button:hover {
    background: #1D4ED8 !important;
}

/* ── 사이드바 라이트 모드 버튼 ── */
[data-testid="stSidebar"] .stButton > button {
    background: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 500;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1D4ED8;
    color: #FFFFFF;
}

/* ── 채팅 말풍선 ── */
[data-testid="stChatMessage"] {
    border-radius: 12px;
    padding: 4px 0;
}

/* ── 상태 뱃지 ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.72rem;
    color: #64748B;
    padding: 3px 8px;
    background: #F1F5F9;
    border-radius: 6px;
    margin-bottom: 10px;
}
.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10B981;
    display: inline-block;
}
[data-theme="dark"] .status-badge {
    background: #1E293B;
    color: #CBD5E1;
}

/* ── 푸터 ── */
.chat-footer {
    text-align: center;
    font-size: 0.72rem;
    color: #94A3B8;
    margin-top: 1.5rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

WELCOME_MSG = "안녕하세요! KSP 지식공유사업 관련 문서에서 답변을 찾아드립니다. 궁금한 내용을 자유롭게 질문해 주세요. 😊"


def _init_state():
    defaults = {
        "pipeline": None,
        "config": None,
        "messages": [{"role": "assistant", "content": WELCOME_MSG}],
        "use_rerank": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _load_pipeline(use_rerank: bool = False) -> bool:
    try:
        config = get_config()
        st.session_state.config = config
        st.session_state.pipeline = RAGPipeline(use_rerank=use_rerank)
        return True
    except Exception as e:
        st.error(f"파이프라인 초기화 실패: {e}")
        return False


def _patch_config(top_k, rerank_top_k, bm25_boost, dense_boost, min_score):
    """사이드바 슬라이더 값을 런타임 config에 반영 (인덱스 재빌드 불필요)"""
    config = get_config()
    try:
        config.top_k = top_k
        config.rerank_top_k = rerank_top_k
        config.elastic_bm25_boost = bm25_boost
        config.elastic_dense_boost = dense_boost
        config.retrieval_min_score = min_score
    except Exception:
        # pydantic frozen 모델일 경우 setattr 우회
        object.__setattr__(config, "top_k", top_k)
        object.__setattr__(config, "rerank_top_k", rerank_top_k)
        object.__setattr__(config, "elastic_bm25_boost", bm25_boost)
        object.__setattr__(config, "elastic_dense_boost", dense_boost)
        object.__setattr__(config, "retrieval_min_score", min_score)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def _render_sidebar():
    with st.sidebar:
        # ── 헤더 ────────────────────────────────────────
        st.markdown(
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
            '<div style="width:36px;height:36px;background:linear-gradient(135deg,#2563EB,#0EA5E9);'
            'border-radius:9px;display:flex;align-items:center;justify-content:center;'
            'font-size:18px;flex-shrink:0;box-shadow:0 3px 8px rgba(37,99,235,0.3);">📘</div>'
            '<div>'
            '<div style="font-size:1.05rem;font-weight:700;line-height:1.3;">KSP Knowledge Hub</div>'
            '<div style="font-size:0.72rem;color:#94A3B8;line-height:1.3;">Knowledge Sharing Program Q&A</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        # ── 검색 파라미터 ──────────────────────────────
        st.markdown("#### 🔍 검색 설정")
        top_k = st.slider(
            "Top-K (초기 검색 문서 수)",
            min_value=1, max_value=30,
            value=st.session_state.get("_top_k", 12),
            step=1,
            help="Elasticsearch에서 처음 가져올 문서 수",
        )
        rerank_top_k = st.slider(
            "Rerank Top-K (최종 문서 수)",
            min_value=1, max_value=20,
            value=st.session_state.get("_rerank_top_k", 5),
            step=1,
            help="리랭킹 후 LLM 프롬프트에 넣을 문서 수",
        )

        st.markdown("#### ⚖️ 검색 가중치")
        bm25_boost = st.slider(
            "BM25 Boost",
            min_value=0.0, max_value=5.0,
            value=st.session_state.get("_bm25_boost", 1.0),
            step=0.1,
            help="키워드 검색(BM25) 가중치. 높을수록 키워드 매칭 강조",
        )
        dense_boost = st.slider(
            "Dense Boost",
            min_value=0.0, max_value=5.0,
            value=st.session_state.get("_dense_boost", 1.0),
            step=0.1,
            help="의미 벡터 검색 가중치. 높을수록 의미 유사도 강조",
        )
        min_score = st.slider(
            "최소 점수 비율",
            min_value=0.0, max_value=1.0,
            value=st.session_state.get("_min_score", 0.0),
            step=0.05,
            help="0이면 비활성. 최고 점수 대비 이 비율 미만 문서 제외 (0.4~0.5 권장)",
        )

        # 슬라이더 값 세션에 저장
        st.session_state["_top_k"] = top_k
        st.session_state["_rerank_top_k"] = rerank_top_k
        st.session_state["_bm25_boost"] = bm25_boost
        st.session_state["_dense_boost"] = dense_boost
        st.session_state["_min_score"] = min_score

        st.divider()

        # ── 리랭킹 토글 ────────────────────────────────
        use_rerank = st.toggle(
            "리랭킹 사용",
            value=st.session_state.use_rerank,
            help="LLM으로 검색 결과 재정렬. 품질 향상, 응답 속도 저하.",
        )
        if use_rerank != st.session_state.use_rerank:
            st.session_state.use_rerank = use_rerank
            st.session_state.pipeline = None

        st.divider()

        # ── 버튼 ────────────────────────────────────────
        if st.button("💬 대화 초기화", use_container_width=True):
            st.session_state.messages = [{"role": "assistant", "content": WELCOME_MSG}]
            st.rerun()

        if st.button("🔄 파이프라인 재로드", use_container_width=True):
            st.session_state.pipeline = None
            st.rerun()

        # ── 시스템 정보 ─────────────────────────────────
        with st.expander("시스템 정보", expanded=False):
            config = st.session_state.config
            if config:
                retriever_label = "Elasticsearch" if config.retriever_mode == "elastic" else "로컬"
                llm_model = (
                    config.llm_model
                    if config.llm_provider == "local_api"
                    else config.server_llm_model
                )
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">'
                    '<span style="width:7px;height:7px;border-radius:50%;background:#10B981;display:inline-block;"></span>'
                    '<span style="font-size:0.75rem;">연결됨</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"모드: `{config.mode}`")
                st.caption(f"검색: `{retriever_label}`")
                st.caption(f"인덱스: `{config.elastic_index_name}`")
                st.caption(f"LLM: `{llm_model}`")

    return top_k, rerank_top_k, bm25_boost, dense_boost, min_score, use_rerank


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _init_state()

    # 설정 로드
    if st.session_state.config is None:
        try:
            st.session_state.config = get_config()
        except Exception:
            st.session_state.config = None

    # 사이드바 렌더
    top_k, rerank_top_k, bm25_boost, dense_boost, min_score, use_rerank = _render_sidebar()

    # ── 파이프라인 초기화 ────────────────────────────────
    if st.session_state.pipeline is None:
        with st.spinner("시스템 초기화 중…"):
            if not _load_pipeline(use_rerank=use_rerank):
                st.stop()

    # ── 기존 대화 메시지 출력 ────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("docs"):
                _render_source_docs(msg["docs"], msg.get("citations", []))

    # ── 사용자 입력 ──────────────────────────────────────
    if prompt := st.chat_input("궁금한 내용을 입력하세요…"):
        prompt = (prompt or "").strip()
        if not prompt:
            st.toast("질문을 입력해 주세요.")
            st.stop()

        # 사용자 메시지 추가 & 출력
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # config 런타임 패치 (슬라이더 값 반영)
        _patch_config(top_k, rerank_top_k, bm25_boost, dense_boost, min_score)

        # 답변 생성
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("검색 및 답변 생성 중…")
            try:
                stream_gen, result_holder = st.session_state.pipeline.ask_stream(
                    prompt, use_rerank=use_rerank
                )

                # 스트리밍 출력
                accumulated = ""
                for chunk in stream_gen:
                    accumulated += chunk
                    placeholder.markdown(accumulated + "▌")

                response = result_holder.get("response")
                final_answer = response.answer if response else accumulated
                placeholder.markdown(final_answer)

                # 참고 문서 표시 & 히스토리 저장
                docs = response.retrieved_docs if response else []
                citations = extract_citations(final_answer, docs) if docs else []
                _render_source_docs(docs, citations)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_answer,
                    "docs": docs,
                    "citations": citations,
                })

            except Exception as e:
                err_msg = f"오류가 발생했습니다: {e}"
                placeholder.error(err_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": err_msg}
                )
                import traceback
                with st.expander("상세 오류"):
                    st.code(traceback.format_exc())

    # ── 푸터 ─────────────────────────────────────────────
    st.markdown(
        '<div class="chat-footer">'
        'KSP Knowledge Hub · Hybrid RAG (Elasticsearch + BGE) · Powered by LLM'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
