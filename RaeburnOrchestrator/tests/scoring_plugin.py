async def plugin_score(*, content: str, user_input: str, **_: str) -> float:
    return 1.0 if 'good' in content else 0.0
