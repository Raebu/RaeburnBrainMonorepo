from BusinessFactory.kpi_engine import record_kpi, snapshot_kpis


def test_kpi_record_and_snapshot():
    record_kpi("biz-test", "revenue", 100.0, {"currency": "USD"})
    snapshot = snapshot_kpis("biz-test", limit=5)
    assert snapshot
    assert any(entry.get("kpi") == "revenue" for entry in snapshot)
