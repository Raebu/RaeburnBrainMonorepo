from BusinessFactory import BusinessFactory


def test_business_factory_creates_and_runs_plan():
    factory = BusinessFactory()
    biz = factory.create_business("demo", ["marketing", "dev"])
    assert biz.business_id == "demo"
    result = factory.run_initial_plan("demo")
    assert result["mission_id"]
    assert "result" in result
