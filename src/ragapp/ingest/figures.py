"""
Figure/chart extraction and description for RAG.
Extracts images from PDFs at ingest time and produces text descriptions (no vision at query time).
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import io
from loguru import logger

from ragapp.ingest.chunkers import Chunk

# Optional imports (lazy to avoid hard dep on heavy libs)
def _import_pymupdf():
    try:
        import fitz  # pymupdf
        return fitz
    except ImportError:
        return None

def _import_pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def extract_figures_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract embedded images from a PDF. Each item: page_num, image_idx, image (PIL Image), ext.
    Skips very small images (likely icons/bullets).
    """
    fitz = _import_pymupdf()
    PilImage = _import_pil()
    if fitz is None:
        logger.warning("PyMuPDF (pymupdf) not installed. Install with: pip install pymupdf")
        return []
    if PilImage is None:
        logger.warning("Pillow (PIL) not installed. Install with: pip install Pillow")
        return []
    figures: List[Dict[str, Any]] = []
    min_width, min_height = 80, 80  # skip tiny images

    try:
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                xref_list = page.get_images()
                for image_idx, xref_info in enumerate(xref_list):
                    xref = xref_info[0]
                    try:
                        base = doc.extract_image(xref)
                        if not base:
                            continue
                        img_bytes = base["image"]
                        w, h = base.get("width", 0), base.get("height", 0)
                        if w < min_width or h < min_height:
                            continue
                        ext = base.get("ext", "png")
                        pil_image = PilImage.open(io.BytesIO(img_bytes)).convert("RGB")
                        figures.append({
                            "page_num": page_num + 1,
                            "image_idx": image_idx,
                            "image": pil_image,
                            "ext": ext,
                            "width": w,
                            "height": h,
                        })
                    except Exception as e:
                        logger.debug(f"Skip image xref={xref} on page {page_num+1}: {e}")
    except Exception as e:
        logger.warning(f"Failed to extract figures from {pdf_path.name}: {e}")

    logger.info(f"Extracted {len(figures)} figures from {pdf_path.name}")
    return figures


class FigureProcessor(ABC):
    """Base for turning an image into a short text description (for RAG indexing)."""

    @abstractmethod
    def describe(self, image) -> str:
        """Return a short text description of the image (chart, figure, etc.)."""
        pass


class BlipFigureProcessor(FigureProcessor):
    """
    Use BLIP (Salesforce/blip-image-captioning-base) for image captioning.
    Lighter than BLIP-2; runs on CPU but faster with GPU.
    """
    def __init__(self, model_name: str = "Salesforce/blip-image-captioning-base"):
        self.model_name = model_name
        self._processor = None
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            import torch
            logger.info(f"Loading BLIP figure model: {self.model_name}")
            self._processor = BlipProcessor.from_pretrained(self.model_name)
            self._model = BlipForConditionalGeneration.from_pretrained(self.model_name)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model.to(self._device)
        except Exception as e:
            logger.error(f"Failed to load BLIP model: {e}")
            raise

    def describe(self, image) -> str:
        self._load()
        import torch
        inputs = self._processor(images=image, return_tensors="pt").to(self._device)
        out = self._model.generate(**inputs, max_new_tokens=80)
        caption = self._processor.decode(out[0], skip_special_tokens=True).strip()
        return caption or "(no description)"


class DePlotFigureProcessor(FigureProcessor):
    """
    Use DePlot (google/deplot) for chart/plot images: chart -> table text.
    Best for charts and graphs; may be poor for photos. Uses Pix2Struct.
    """
    CHART_PROMPT = "Generate underlying data table of the figure below:"

    def __init__(self, model_name: str = "google/deplot"):
        self.model_name = model_name
        self._processor = None
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        try:
            from transformers import Pix2StructProcessor, Pix2StructForConditionalGeneration
            import torch
            logger.info(f"Loading DePlot figure model: {self.model_name}")
            self._processor = Pix2StructProcessor.from_pretrained(self.model_name)
            self._model = Pix2StructForConditionalGeneration.from_pretrained(self.model_name)
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model.to(self._device)
        except Exception as e:
            logger.error(f"Failed to load DePlot model: {e}")
            raise

    def describe(self, image) -> str:
        self._load()
        import torch
        inputs = self._processor(
            images=image,
            text=self.CHART_PROMPT,
            return_tensors="pt",
        ).to(self._device)
        out = self._model.generate(**inputs, max_new_tokens=512)
        text = self._processor.decode(out[0], skip_special_tokens=True).strip()
        if not text or len(text) < 10:
            return "(chart data could not be extracted)"
        return text


class OpenAIVisionFigureProcessor(FigureProcessor):
    """
    Use OpenAI Vision API (gpt-4o-mini or gpt-4o) to describe images.
    Requires OPENAI_API_KEY (or LLM_API_KEY) in env.
    """
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model = model
        self._client = None
        self._api_key = api_key

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
            from ragapp.config import get_config
            key = self._api_key or get_config().llm_api_key
            if not key:
                raise ValueError("OpenAI API key not set. Set LLM_API_KEY or pass api_key.")
            self._client = OpenAI(api_key=key)
            return self._client
        except Exception as e:
            logger.error(f"OpenAI client init failed: {e}")
            raise

    def describe(self, image) -> str:
        import base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image or chart in one or two concise sentences. Focus on data, labels, and meaning if it is a chart or graph.",
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
            max_tokens=150,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or "(no description)"


def figures_to_chunks(
    figures: List[Dict[str, Any]],
    processor: FigureProcessor,
    doc_id: str,
    source_path: str,
) -> List[Chunk]:
    """
    Run the figure processor on each extracted image and create one chunk per figure.
    """
    chunks: List[Chunk] = []
    for fig in figures:
        page_num = fig["page_num"]
        image_idx = fig["image_idx"]
        image = fig["image"]
        try:
            description = processor.describe(image)
        except Exception as e:
            logger.warning(f"Figure description failed page={page_num} idx={image_idx}: {e}")
            description = "(figure description unavailable)"
        chunk_id = f"{doc_id}_figure_p{page_num}_i{image_idx}"
        metadata: Dict[str, Any] = {
            "page_num": page_num,
            "figure_idx": image_idx,
            "width": fig.get("width"),
            "height": fig.get("height"),
        }
        chunk = Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            source_path=source_path,
            page_start=page_num,
            page_end=page_num,
            content=description,
            content_type="figure",
            metadata=metadata,
        )
        chunks.append(chunk)
    return chunks
