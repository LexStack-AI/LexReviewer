"""Integration with Unstructured for PDF chunking and bounding-box extraction."""

import base64
import json
import os
from typing import List
import zlib

from dotenv import load_dotenv
from langchain_core.documents import Document
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared

from models import BoundingBox


class UnstructuredProvider:
    """Configure and call the Unstructured API, then normalize results to `Document`s."""

    def __init__(self) -> None:
        load_dotenv()
        unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if not unstructured_api_key:
            raise ValueError("UNSTRUCTURED_API_KEY is not set")
        self.unstructured_client = UnstructuredClient(api_key_auth=unstructured_api_key)

        # Chunking and layout parameters are driven via env vars for flexibility.
        self.max_characters = int(os.getenv("UNSTRUCTURED_MAX_CHARACTERS", "6000"))
        self.combine_under_n_chars = int(os.getenv("UNSTRUCTURED_COMBINE_UNDER_N_CHARS", "2250"))
        self.new_after_n_chars = int(os.getenv("UNSTRUCTURED_NEW_AFTER_N_CHARS", "4500"))
        self.overlap = int(os.getenv("UNSTRUCTURED_OVERLAP", "150"))
        self.overlap_all = bool(os.getenv("UNSTRUCTURED_OVERLAP_ALL", True))
        self.multipage_sections = bool(os.getenv("UNSTRUCTURED_MULTIPAGE_SELECTION", True))
        self.split_pdf_page = bool(os.getenv("UNSTRUCTURED_SPLIT_PDF_PAGE", True))
        self.split_pdf_allow_failed = bool(os.getenv("UNSTRUCTURED_SPLIT_PDF_ALLOW_FAILED", True))
        self.split_pdf_concurrency_level = int(os.getenv("UNSTRUCTURED_SPLIT_PDF_CONCURRENCY_LEVEL", "15"))
        self.strategy = str(os.getenv("UNSTRUCTURED_STRATEGY", "AUTO"))
        self.chunking_strategy = str(os.getenv("UNSTRUCTURED_CHUNKING_STRATEGY", "by_title"))
        self.chunk_bboxes_enabled = bool(os.getenv("CHUNK_BBOXES_ENABLED", True))

        self.strategy_map = {
            "AUTO": shared.Strategy.AUTO,
            "FAST": shared.Strategy.FAST,
            "HI_RES": shared.Strategy.HI_RES,
            "OCR_ONLY": shared.Strategy.OCR_ONLY,
        }

    async def get_chunks(self, document_base64: str, document_id: str) -> List[Document]:
        try:
            document_bytes = base64.b64decode(document_base64)
            strategy = self.strategy_map.get(self.strategy.upper(), shared.Strategy.AUTO)
            request_params = operations.PartitionRequest(
                partition_parameters=shared.PartitionParameters(
                    files=shared.Files(
                        content=document_bytes,
                        file_name=f"{document_id}.pdf",
                    ),
                    strategy=strategy,
                    coordinates=self.chunk_bboxes_enabled,
                    chunking_strategy= self.chunking_strategy,
                    max_characters = self.max_characters,
                    combine_under_n_chars = self.combine_under_n_chars,
                    new_after_n_chars = self.new_after_n_chars,
                    overlap = self.overlap,
                    overlap_all=self.overlap_all,
                    multipage_sections=self.multipage_sections,
                    split_pdf_page= self.split_pdf_page,
                    split_pdf_allow_failed= self.split_pdf_allow_failed,
                    split_pdf_concurrency_level= self.split_pdf_concurrency_level
                )
            )
            
            partition_response = self.unstructured_client.general.partition(
                request=request_params
            )
            chunks = [element for element in (partition_response.elements or [])]

            chunks_doc = []
            for i, chunk in enumerate(chunks, 1):
                bounding_boxes: List[BoundingBox] = []
                if self.chunk_bboxes_enabled:
                    elements = self.decode_orig_elements(chunk['metadata']["orig_elements"])
                
                    # Compile bounding boxes
                    for element in elements:
                        element_metadata = element["metadata"]
                        bounding_box: BoundingBox = self.get_chunk_bounding_boxes(element_metadata)
                        bounding_boxes.append(bounding_box)                

                chunk_id = i
                chunks_doc.append(
                    Document(
                        page_content=chunk["text"], 
                        id=chunk_id, 
                        metadata={
                            "document_id": document_id, 
                            "bounding_boxes": [bb.model_dump() for bb in bounding_boxes] if bounding_boxes else []
                        }
                    )
                )
            
            return chunks_doc
        except Exception as e:
            print(f"Error chunking document {document_id}: {e}")
            raise

    def decode_orig_elements(self, orig_elements: str) -> List[dict]:
        decoded_bytes = base64.b64decode(orig_elements)
        decompress_bytes = zlib.decompress(decoded_bytes)
        elements_str = decompress_bytes.decode('utf-8', errors='replace')
        elements = json.loads(elements_str)

        return elements

    def get_chunk_bounding_boxes(
        self,
        metadata: dict
    ) -> BoundingBox:
        layout_height = metadata["coordinates"]["layout_height"]
        layout_width = metadata["coordinates"]["layout_width"]
        page_number = metadata["page_number"]

        # Extract minimum and maximum, x and y values
        points = metadata["coordinates"]["points"]
        # Separate x and y coordinates
        x_values = [p[0] for p in points]
        y_values = [p[1] for p in points]

        # Find min and max
        min_x = min(x_values)
        max_x = max(x_values)
        min_y = min(y_values)
        max_y = max(y_values)
        
        return BoundingBox(
            leftPosition=(min_x * 100) / layout_width,
            topPosition=(min_y * 100) / layout_height,
            highlightWidth=((max_x - min_x) * 100) / layout_width,
            highlightHeight=((max_y - min_y) * 100) / layout_height,
            pageWidth=layout_width,
            pageHeight=layout_height,
            pageNumber=page_number
        )

