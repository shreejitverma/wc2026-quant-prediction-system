import tempfile
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from wc2026.ingest.base import HTTPClient, RawStore


def test_raw_store():
    with tempfile.TemporaryDirectory() as td:
        store = RawStore(td)
        dt = datetime(2026,1,1, tzinfo=UTC)
        p = store.write("src1", "f1.txt", "hello", dt=dt)
        assert p.exists()
        assert store.exists("src1", "f1.txt", dt=dt)
        assert store.read("src1", "f1.txt", dt=dt) == b"hello"
        assert store.read_text("src1", "f1.txt", dt=dt) == "hello"
        
        store.write("src1", "f1.txt", "world", dt=dt, overwrite=False)
        assert store.read_text("src1", "f1.txt", dt=dt) == "hello"
        
        meta = store.meta("src1", "f1.txt", dt=dt)
        assert meta["source"] == "src1"
        assert store.fetched_at("src1", "f1.txt", dt=dt) is not None
        
        p.with_suffix(".txt.meta.json").write_text("{}")
        assert store.fetched_at("src1", "f1.txt", dt=dt) is None
        
        dates = store.list_dates("src1")
        assert len(dates) == 1
        assert store.latest_date("src1") == dates[0]
        
        assert len(store.list_dates("src2")) == 0
        assert store.latest_date("src2") is None

@patch('httpx.Client.get')
def test_http_client(mock_get):
    with tempfile.TemporaryDirectory() as td:
        store = RawStore(td)
        with HTTPClient(store, min_request_interval=0.0) as client:
            resp = MagicMock()
            resp.status_code = 200
            resp.content = b'{"a": 1}'
            resp.json.return_value = {"a": 1}
            mock_get.return_value = resp
            
            p = client.fetch("http://test.com", "src1", "f1.json")
            assert p.exists()
            
            p_again = client.fetch("http://test.com", "src1", "f1.json", overwrite=False)
            assert p_again.exists()
            
            p2, data = client.fetch_json("http://test.com", "src1", "f2.json")
            assert data["a"] == 1
            
            # Error
            err_resp = MagicMock()
            err_resp.status_code = 404
            err_resp.raise_for_status.side_effect = httpx.HTTPStatusError("err", request=MagicMock(), response=err_resp)
            mock_get.return_value = err_resp
            with pytest.raises(httpx.HTTPStatusError):
                client.fetch("http://test.com/err", "src1", "f3.json")
