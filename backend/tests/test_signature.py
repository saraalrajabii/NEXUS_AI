import pytest

from app.integrations.chatwoot.signature import SignatureError, compute_signature, verify_signature

BODY = b'{"event":"message_created"}'
TS = "1794859200"
NOW = 1794859200 + 10


def _verify(**overrides):
    args = dict(secret="s3cret", raw_body=BODY, timestamp=TS, signature=compute_signature("s3cret", TS, BODY), now=NOW)
    args.update(overrides)
    verify_signature(**args)


def test_valid_signature_passes():
    _verify()


def test_signature_format_matches_chatwoot():
    # Same formula as Chatwoot's lib/webhooks/trigger.rb: "sha256=" + HMAC_SHA256(secret, "ts.body")
    assert compute_signature("s3cret", TS, BODY).startswith("sha256=")
    assert len(compute_signature("s3cret", TS, BODY)) == len("sha256=") + 64


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"secret": "wrong"}, "does not match"),
        ({"raw_body": b'{"event":"message_created","x":1}'}, "does not match"),  # tampered body
        ({"now": int(TS) + 301}, "outside the allowed window"),  # replayed 5 min later
        ({"timestamp": None}, "missing"),
        ({"signature": None}, "missing"),
        ({"timestamp": "yesterday"}, "not a number"),
    ],
)
def test_invalid_requests_are_rejected(overrides, reason):
    with pytest.raises(SignatureError, match=reason):
        _verify(**overrides)
