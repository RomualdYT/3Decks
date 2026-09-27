from tools.audit_public_config import issues


def test_public_configuration_audit_checks_nested_values_without_exposing_them():
    assert issues({"token": "", "obs": {"password": ""}}) == set()
    assert issues({"nested": [{"access_token": "private-value"}]}) == {"nonempty credential"}
    for path in ("/Users/example/file", r"C:\Users\example\file", "C:/Users/example/file"):
        assert issues({"action": {"value": path}}) == {"personal profile path"}
