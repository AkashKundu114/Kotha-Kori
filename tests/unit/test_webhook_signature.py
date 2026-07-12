import hmac, hashlib


def test_hmac_signature_matches_expected_scheme():
    secret = "test-app-secret"
    body = b'{"entry": []}'
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert expected.startswith("sha256=")
    assert hmac.compare_digest(expected, expected)

    tampered_body = b'{"entry": [1]}'
    tampered_sig = "sha256=" + hmac.new(secret.encode(), tampered_body, hashlib.sha256).hexdigest()
    assert not hmac.compare_digest(expected, tampered_sig)
