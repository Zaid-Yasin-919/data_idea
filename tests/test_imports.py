import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_imports():
    import src
    from src.config import DB_PATH, SCHEMA_PATH
    from src.models import IndustrialPlant, Organization, Tender, TenderItem
    from src.pipeline import DatabaseManager, IngestionPipeline
    from src.scrapers import BaseScraper, GeMScraper

    assert src.__version__ == "0.1.0"
    print("All package imports verified successfully.")

if __name__ == "__main__":
    test_imports()
