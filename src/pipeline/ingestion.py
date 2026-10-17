import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.pipeline.db import DatabaseManager

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Universal raw data ingestion and normalization pipeline."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def normalize_category(self, text: str) -> str:
        """Classifies text into broad sector categories."""
        t = text.lower()
        if any(k in t for k in ["computer", "laptop", "server", "software", "printer", "network"]):
            return "it_electronics"
        elif any(k in t for k in ["vehicle", "car", "bus", "truck", "tyre", "automobile"]):
            return "automotive_transport"
        elif any(k in t for k in ["medicine", "medical", "hospital", "pharma", "surgical"]):
            return "medical_healthcare"
        elif any(k in t for k in ["pipe", "valve", "pump", "casting", "sheet", "steel", "brass", "metal"]):
            return "metals_machinery"
        return "general_procurement"
