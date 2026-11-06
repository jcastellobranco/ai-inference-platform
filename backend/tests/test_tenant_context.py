from unittest.mock import MagicMock, patch
from app.db import tenant_session

def test_tenant_context_is_transaction_local():
    session = MagicMock()
    session.__enter__.return_value = session
    session.begin.return_value.__enter__.return_value = session
    with patch("app.db.SessionLocal", return_value=session):
        with tenant_session("11111111-1111-4111-8111-111111111111") as actual:
            assert actual is session
    statement, params = session.execute.call_args.args
    assert "set_config" in str(statement)
    assert params["tenant"] == "11111111-1111-4111-8111-111111111111"
