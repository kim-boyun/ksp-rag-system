"""
Streamlit UI for KSP RAG System
"""
import streamlit as st
import sys
from pathlib import Path

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

# Custom CSS
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
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .citation-box {
        background-color: #fff9e6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 3px solid #ffa500;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .doc-preview {
        background-color: #f5f5f5;
        padding: 0.8rem;
        border-radius: 0.3rem;
        font-size: 0.85rem;
        color: #333;
        margin: 0.3rem 0;
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
    
    # Example queries
    st.caption("예시 질문:")
    example_cols = st.columns(3)
    
    examples = [
        "온두라스 연금 시스템의 주요 특징은?",
        "What is the Knowledge Sharing Program?",
        "엘살바도르의 산업 발전 방안은?"
    ]
    
    for i, example in enumerate(examples):
        with example_cols[i]:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                query = example
                ask_button = True
    
    # Process query
    if ask_button and query:
        with st.spinner("🔍 검색 및 답변 생성 중..."):
            try:
                # Get response from pipeline
                response = st.session_state.pipeline.ask(query, use_rerank=use_rerank)
                
                # Extract citations
                citations = extract_citations(response.answer, response.retrieved_docs)
                
                # Save to history
                st.session_state.history.append({
                    "query": query,
                    "answer": response.answer,
                    "citations": citations,
                    "num_docs": len(response.retrieved_docs)
                })
                
                # Display results
                st.markdown("---")
                
                # Answer
                st.subheader("💬 답변")
                st.markdown(f'<div class="answer-box">{response.answer}</div>', unsafe_allow_html=True)
                
                # Citations
                if citations:
                    st.subheader("📚 인용 출처")
                    
                    for cite in citations:
                        doc_id = cite.get('doc_id', 'Unknown')
                        page_num = cite.get('page_num', 'N/A')
                        content_type = cite.get('content_type', 'text')
                        doc_num = cite.get('doc_num', '?')
                        
                        st.markdown(f"""
<div class="citation-box">
    <strong>📄 문서 {doc_num}</strong>: {doc_id}<br>
    <small>페이지: {page_num} | 유형: {content_type}</small>
</div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("인용 정보가 없습니다.")
                
                # Retrieved documents (expandable)
                with st.expander(f"📄 검색된 문서 ({len(response.retrieved_docs)}개)"):
                    for i, doc in enumerate(response.retrieved_docs, 1):
                        doc_id = doc.metadata.get('doc_id', 'Unknown')
                        page_num = doc.metadata.get('page_num', 'N/A')
                        chunk_id = doc.metadata.get('chunk_id', 'N/A')
                        content_type = doc.metadata.get('content_type', 'text')
                        
                        # Truncate doc_id
                        if len(doc_id) > 50:
                            doc_id_display = doc_id[:47] + "..."
                        else:
                            doc_id_display = doc_id
                        
                        # Truncate content
                        content_preview = doc.content[:300]
                        if len(doc.content) > 300:
                            content_preview += "..."
                        
                        st.markdown(f"""
**#{i}** (Score: {doc.score:.4f})  
**문서**: {doc_id_display}  
**페이지**: {page_num} | **청크**: {chunk_id} | **유형**: {content_type}
                        """)
                        
                        st.markdown(f'<div class="doc-preview">{content_preview}</div>', unsafe_allow_html=True)
                        st.markdown("---")
                
                # Metadata
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
