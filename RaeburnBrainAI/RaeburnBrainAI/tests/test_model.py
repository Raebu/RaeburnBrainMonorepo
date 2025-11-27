from RaeburnBrainAI.model import ModelRegistry


def test_model_registry_defaults_to_local():
    registry = ModelRegistry.load_default()
    models = registry.models()
    assert models
    assert registry.choose()[0].name == models[0].name
