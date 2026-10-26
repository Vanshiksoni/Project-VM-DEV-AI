import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.services.indexer import (
    get_knowledge_base_signature,
    has_knowledge_base_changed,
    ensure_realtime_sync,
    build_index,
)
from backend.app.services.cache import get_cache, set_cache, make_cache_key, clear_cache

client = TestClient(app)


def test_realtime_document_lifecycle():
    test_filename = "_test_realtime_cloud_policy.md"
    test_content = """# Cloud Security Protocol

## Cloud Backup Policy
All Kubernetes and Docker microservices must maintain automated daily snapshots stored in an encrypted off-site cloud bucket with a 30-day retention schedule.
"""

    # 1. Save new document via real-time content endpoint
    res = client.post(
        "/documents/content",
        json={"filename": test_filename, "content": test_content}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["filename"] == test_filename
    assert data["chunks_indexed"] > 0

    # 2. Verify /documents status includes the new file
    doc_res = client.get("/documents")
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    source_filenames = [s["filename"] for s in doc_data["sources"]]
    assert test_filename in source_filenames

    # 3. Query the chat pipeline for this new real-time content
    ask_res = client.post(
        "/ask",
        json={"question": "What is the cloud backup policy retention schedule?"}
    )
    assert ask_res.status_code == 200
    ask_data = ask_res.json()
    # It should match the newly indexed chunk
    assert len(ask_data["sources"]) > 0
    matched_source = ask_data["sources"][0]
    assert matched_source["filename"] == test_filename
    assert "30-day" in ask_data["answer"] or "retention" in ask_data["answer"].lower() or "Cloud Backup" in matched_source["section"]

    # 4. Clean up by deleting the document
    del_res = client.delete(f"/documents/{test_filename}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "success"

    # 5. Verify /documents no longer contains it
    doc_res2 = client.get("/documents")
    doc_data2 = doc_res2.json()
    source_filenames2 = [s["filename"] for s in doc_data2["sources"]]
    assert test_filename not in source_filenames2


def test_cache_invalidation_on_reindex():
    # Cache a dummy query
    test_key = make_cache_key("test question")
    set_cache(test_key, {"answer": "stale cached answer"})
    assert get_cache(test_key) is not None

    # Reindex
    reindex_res = client.post("/documents/reindex")
    assert reindex_res.status_code == 200
    assert reindex_res.json()["cache_cleared"] >= 1

    # Cache should now be purged
    assert get_cache(test_key) is None
