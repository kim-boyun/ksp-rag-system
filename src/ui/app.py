"""
Streamlit UI for KSP RAG System
"""
import streamlit as st
import sys
from pathlib import Path


def _display_name(metadata: dict) -> str:
    """원본 파일명 우선 → doc_id → chunk_id에서 추출 → Unknown"""
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

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ragapp.pipeline.rag_pipeline import RAGPipeline
from ragapp.config import get_config
from ragapp.prompts import extract_citations


# Page config
st.set_page_config(
    page_title="KSP RAG System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (라이트/다크 모드 모두 가독성 확보)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .answer-box {
        background-color: #f0f8ff;
        color: #1a1a1a;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .citation-box {
        background-color: #fff9e6;
        color: #1a1a1a;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 3px solid #ffa500;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .doc-preview {
        background-color: #f5f5f5;
        color: #333;
        padding: 0.8rem;
        border-radius: 0.3rem;
        font-size: 0.85rem;
        margin: 0.3rem 0;
    }
    /* 다크 모드 */
    [data-theme="dark"] .answer-box {
        background-color: #1e3a5f;
        color: #e8f4fc;
        border-left-color: #60a5fa;
    }
    [data-theme="dark"] .citation-box {
        background-color: #422006;
        color: #fef3c7;
        border-left-color: #f59e0b;
    }
    [data-theme="dark"] .doc-preview {
        background-color: #334155;
        color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'pipeline' not in st.session_state:
        st.session_state.pipeline = None
    if 'config' not in st.session_state:
        st.session_state.config = None
    if 'history' not in st.session_state:
        st.session_state.history = []


def load_pipeline(use_rerank: bool = False):
    """Load or reload RAG pipeline"""
    try:
        config = get_config()
        st.session_state.config = config
        st.session_state.pipeline = RAGPipeline(use_rerank=use_rerank)
        return True
    except Exception as e:
        st.error(f"파이프라인 초기화 실패: {e}")
        return False


def main():
    """Main Streamlit app"""
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">🔍 KSP RAG System</div>', unsafe_allow_html=True)
    st.markdown("**Knowledge Sharing Program 문서 검색 및 질의응답 시스템**")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # Load config
        if st.session_state.config is None:
            config = get_config()
            st.session_state.config = config
        else:
            config = st.session_state.config
        
        # Display current configuration
        st.subheader("현재 설정")
        st.info(f"""
**모드**: {config.mode}  
**Retriever**: {config.retriever_mode}  
**LLM Provider**: {config.llm_provider}
        """)
        
        # Advanced options
        st.subheader("고급 옵션")
        use_rerank = st.checkbox("LLM 리랭킹 사용", value=False, help="검색 결과를 LLM으로 재정렬 (품질 향상, 속도 저하)")
        
        # Reload pipeline button
        if st.button("🔄 파이프라인 재로드", help="설정 변경 후 클릭"):
            with st.spinner("파이프라인 재로드 중..."):
                if load_pipeline(use_rerank=use_rerank):
                    st.success("✅ 파이프라인이 재로드되었습니다")
                    st.rerun()
        
        # System info
        with st.expander("🔧 시스템 정보"):
            st.json({
                "mode": config.mode,
                "retriever_mode": config.retriever_mode,
                "llm_provider": config.llm_provider,
                "top_k": config.top_k,
                "rerank_top_k": config.rerank_top_k,
                "llm_model": config.llm_model if config.llm_provider == "local_api" else config.server_llm_model
            })
        
        # History
        if st.session_state.history:
            st.subheader("📜 히스토리")
            if st.button("🗑️ 히스토리 지우기"):
                st.session_state.history = []
                st.rerun()
            
            for i, item in enumerate(reversed(st.session_state.history[-5:])):
                with st.expander(f"Q{len(st.session_state.history)-i}: {item['query'][:30]}..."):
                    st.text(item['query'])
    
    # Main content
    st.markdown("---")
    
    # Initialize pipeline
    if st.session_state.pipeline is None:
        with st.spinner("파이프라인 초기화 중..."):
            if not load_pipeline(use_rerank=use_rerank):
                st.stop()
    
    # Query input
    st.subheader("💬 질문하기")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "질문을 입력하세요",
            placeholder="예: 온두라스 연금 시스템의 주요 특징은 무엇인가요?",
            label_visibility="collapsed"
        )
    
    with col2:
        ask_button = st.button("🔍 검색", type="primary", use_container_width=True)
    
    # Example queries (raw 문서 주제 기반: 남아공 인프라/농촌개발, 카자흐스탄 중소기업/신용보증)
    st.caption("예시 질문:")
    example_cols = st.columns(3)
    examples = [
        "남아공 통합 인프라 구축전략의 핵심 내용은?",
        "농촌개발계획 수립과 관련된 주요 내용을 요약해 주세요.",
        "카자흐스탄 중소기업 육성을 위한 정책의 특징은?",
        "신용보증제도와 신용평가시스템 구축 방안은?",
        "KSP(Knowledge Sharing Program)란 무엇인가요?",
        "인프라 구축과 농촌 개발을 어떻게 연계할 수 있나요?",
    ]
    for i, example in enumerate(examples):
        with example_cols[i % 3]:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                query = example
                ask_button = True
    
    # Process query
    if ask_button and query:
        try:
            with st.spinner("🔍 검색 중..."):
                stream_gen, result_holder = st.session_state.pipeline.ask_stream(
                    query, use_rerank=use_rerank
                )

            st.markdown("---")
            st.subheader("💬 답변")
            message_placeholder = st.empty()
            accumulated = ""
            for chunk in stream_gen:
                accumulated += chunk
                message_placeholder.markdown(accumulated)

            response = result_holder.get("response")
            if not response:
                st.error("답변 생성 중 오류가 발생했습니다.")
                st.stop()

            # 스트리밍과 동일하게 마크다운으로 최종 표시
            message_placeholder.markdown(response.answer)

            citations = extract_citations(response.answer, response.retrieved_docs)
            st.session_state.history.append({
                "query": query,
                "answer": response.answer,
                "citations": citations,
                "num_docs": len(response.retrieved_docs),
            })

            # 출처 (인용 정보 + 검색된 문서 + 메타데이터)
            st.subheader("📚 출처")
            if citations:
                for cite in citations:
                    doc_num = cite.get('doc_num', '?')
                    doc = None
                    if 1 <= doc_num <= len(response.retrieved_docs):
                        doc = response.retrieved_docs[doc_num - 1]
                    display_name = _display_name(doc.metadata) if doc else cite.get('doc_id', 'Unknown')
                    page_num = cite.get('page_num', 'N/A')
                    content_type = cite.get('content_type', 'text')
                    st.markdown(f"""
<div class="citation-box">
    <strong>📄 문서 {doc_num}</strong>: {display_name}<br>
    <small>페이지: {page_num} | 유형: {content_type}</small>
</div>
                    """, unsafe_allow_html=True)
            else:
                st.info("인용 정보가 없습니다.")

            if len(response.retrieved_docs) == 0:
                st.warning(
                    "**검색된 문서가 0건입니다.** "
                    "Elasticsearch 인덱스가 비어 있거나 아직 구축되지 않았을 수 있습니다. "
                    "터미널에서 `make elastic-up` 후 `make index-elastic`을 실행한 뒤 다시 시도해 보세요."
                )

            with st.expander(f"📄 검색된 문서 ({len(response.retrieved_docs)}개)"):
                if len(response.retrieved_docs) == 0:
                    st.caption("인덱스 구축: make index-elastic (인제스트·청크는 이미 있어야 함)")
                for i, doc in enumerate(response.retrieved_docs, 1):
                    display_name = _display_name(doc.metadata)
                    page_num = doc.metadata.get('page_num', 'N/A')
                    chunk_id = doc.metadata.get('chunk_id', 'N/A')
                    content_type = doc.metadata.get('content_type', 'text')
                    doc_id_display = display_name[:47] + "..." if len(display_name) > 50 else display_name
                    content_preview = doc.content[:300] + ("..." if len(doc.content) > 300 else "")
                    st.markdown(f"""
**#{i}** (Score: {doc.score:.4f})  
**문서**: {doc_id_display}  
**페이지**: {page_num} | **청크**: {chunk_id} | **유형**: {content_type}
                    """)
                    st.markdown(f'<div class="doc-preview">{content_preview}</div>', unsafe_allow_html=True)
                    st.markdown("---")

            with st.expander("ℹ️ 메타데이터"):
                st.json(response.metadata)

        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
            import traceback
            with st.expander("상세 오류"):
                st.code(traceback.format_exc())
    
    elif ask_button:
        st.warning("⚠️ 질문을 입력해주세요.")
    
    # Footer
    st.markdown("---")
    st.caption("🚀 KSP RAG System | Docker-based Hybrid RAG with Local/Server Mode Support")


if __name__ == "__main__":
    main()
