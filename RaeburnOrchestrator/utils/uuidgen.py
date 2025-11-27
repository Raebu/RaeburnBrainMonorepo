import uuid

def gen_session_id() -> str:
    return "sess_" + uuid.uuid4().hex[:8]
