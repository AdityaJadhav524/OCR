import pytest
from dataclasses import dataclass
from core.models.entity import (
    EntityType, MergeEvidence, DocumentEntity, 
    NumericCandidate, EntityDecision, ReconstructionLog, NumericToken
)

# --- Mocks for TDD (to be replaced by real implementations) ---
@dataclass
class OCRToken:
    text: str
    x0: float
    x1: float
    y0: float
    y1: float
    confidence: float
    page_id: int = 0
    line_id: int = 0

def mock_tok(text: str, x0: float, x1: float, y0: float = 10.0, y1: float = 20.0, conf: float = 0.99, page: int = 0, line: int = 0) -> OCRToken:
    return OCRToken(text=text, x0=x0, x1=x1, y0=y0, y1=y1, confidence=conf, page_id=page, line_id=line)

from core.extractors.entity_grouper import group_entities
from core.extractors.entity_classifier import classify_entities

from core.extractors.entity_filter import filter_entities
from core.extractors.numeric_normalizer import normalize_entities

# ==============================================================================
# SUITE 1: RECONSTRUCTION (Geometric grouping of split elements)
# ==============================================================================
class TestSuite1_Reconstruction:
    def test_split_decimals_yes_bank(self):
        tokens = [mock_tok("161,835.", 100, 160), mock_tok("18", 162, 170)]
        entities = group_entities(tokens)
        assert len(entities) == 1
        assert entities[0].raw_text == "161,835. 18"
        assert entities[0].evidence.merged_by == "horizontal_merge"
        
    def test_split_decimals_federal_bank(self):
        tokens = [mock_tok("413534.1", 100, 150), mock_tok("0", 151, 155)]
        entities = group_entities(tokens)
        assert len(entities) == 1
        assert entities[0].raw_text == "413534.1 0"

    def test_split_comma(self):
        tokens = [mock_tok("1,", 100, 110), mock_tok("500.00", 112, 140)]
        entities = group_entities(tokens)
        assert len(entities) == 1
        assert entities[0].raw_text == "1, 500.00"

    def test_currency_symbol(self):
        tokens = [mock_tok("₹", 100, 105), mock_tok("15,000.00", 107, 150)]
        entities = group_entities(tokens)
        assert len(entities) == 1
        assert entities[0].raw_text == "₹ 15,000.00"

    def test_cr_dr_suffix(self):
        tokens = [mock_tok("5000.00", 100, 140), mock_tok("CR", 145, 155)]
        entities = group_entities(tokens)
        assert len(entities) == 1
        assert entities[0].raw_text == "5000.00 CR"

# ==============================================================================
# SUITE 2: GEOMETRY (Negative Rules)
# ==============================================================================
class TestSuite2_Geometry:
    def test_large_x_gap_rejection(self):
        tokens = [mock_tok("413534.1", 100, 150), mock_tok("0", 200, 205)]
        entities = group_entities(tokens)
        assert len(entities) == 2  # No merge!

    def test_different_baseline_rejection(self):
        tokens = [mock_tok("413534.1", 100, 150, y0=10, y1=20), mock_tok("0", 151, 155, y0=25, y1=35)]
        entities = group_entities(tokens)
        assert len(entities) == 2  # No merge!

    def test_different_font_height_rejection(self):
        tokens = [mock_tok("GRAND TOTAL", 100, 150, y0=10, y1=25), mock_tok("150.00", 152, 170, y0=15, y1=20)]
        entities = group_entities(tokens)
        assert len(entities) == 2  # No merge!
        
    def test_different_page_rejection(self):
        tokens = [mock_tok("1500.", 100, 150, page=1), mock_tok("00", 151, 170, page=2)]
        entities = group_entities(tokens)
        assert len(entities) == 2  # No merge across pages!

# ==============================================================================
# SUITE 3: OCR CORRUPTION & NORMALIZATION
# ==============================================================================
class TestSuite3_OCR_Corruption:
    def test_watermark_contamination_normalizer(self):
        entities = [DocumentEntity(raw_text="67882.00L128", bbox=[0,0,0,0], children=[0])]
        norm = normalize_entities(entities)[0]
        assert any(c.value == 67882.00 for c in norm.candidates)
        
    def test_trailing_noise(self):
        entities = [DocumentEntity(raw_text="161835.18-", bbox=[0,0,0,0], children=[0])]
        norm = normalize_entities(entities)[0]
        assert any(c.value == 161835.18 for c in norm.candidates)

    def test_missing_digits_no_invention(self):
        entities = [DocumentEntity(raw_text="728.66", bbox=[0,0,0,0], children=[0])]
        norm = normalize_entities(entities)[0]
        assert not any(c.value > 1000 for c in norm.candidates)
        assert any(c.value == 728.66 for c in norm.candidates)

# ==============================================================================
# SUITE 4: PARSER & FILTER (Declarative mapping and rejection)
# ==============================================================================
class TestSuite4_Parser_and_Filter:
    def test_entity_filter_rejects_garbage(self):
        entities = [
            DocumentEntity(raw_text="03/07/21", bbox=[0,0,0,0], children=[0], entity_type=EntityType.DATE, column_assignment="debit"),
            DocumentEntity(raw_text="GRAND TOTAL", bbox=[0,0,0,0], children=[1], entity_type=EntityType.TEXT, column_assignment="narration")
        ]
        decisions = filter_entities(entities)
        # Date inside numeric column should be dropped by filter
        assert decisions[0].action == "DROP"
        # Text inside narration is kept
        assert decisions[1].action == "KEEP"

# ==============================================================================
# SUITE 6: REGRESSION
# ==============================================================================
class TestSuite6_Regression:
    def test_tjsb_value_date_bleed(self):
        tokens = [mock_tok("03/07/21", 100, 140), mock_tok("5000.00", 170, 210)]
        entities = group_entities(tokens)
        assert len(entities) == 2
        
    def test_axis_ocr_punctuation(self):
        entities = [DocumentEntity(raw_text="161835:18", bbox=[0,0,0,0], children=[0])]
        norm = normalize_entities(entities)[0]
        assert any(c.value == 161835.18 for c in norm.candidates)
        
    def test_boi_broken_decimal(self):
        entities = [DocumentEntity(raw_text="87.03 4.17", bbox=[0,0,0,0], children=[0,1])]
        norm = normalize_entities(entities)[0]
        values = [c.value for c in norm.candidates]
        assert 87034.17 in values
        assert 87.03 in values
