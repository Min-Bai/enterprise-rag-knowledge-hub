from python_practice.day57.rate_limit import LoginRateLimiter


class FakeRedis:
    def __init__(self):
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


def test_login_rate_limiter_allows_requests_within_limit():
    client = FakeRedis()
    limiter = LoginRateLimiter(client=client, limit=2, window_seconds=60)

    assert limiter.is_allowed("127.0.0.1") is True
    assert limiter.is_allowed("127.0.0.1") is True
    assert client.expirations["rate_limit:login:127.0.0.1"] == 60


def test_login_rate_limiter_rejects_requests_over_limit():
    limiter = LoginRateLimiter(
        client=FakeRedis(),
        limit=2,
        window_seconds=60,
    )

    assert limiter.is_allowed("127.0.0.1") is True
    assert limiter.is_allowed("127.0.0.1") is True
    assert limiter.is_allowed("127.0.0.1") is False


def test_rate_limiter_supports_a_custom_key_prefix():
    client = FakeRedis()
    limiter = LoginRateLimiter(
        client=client,
        limit=1,
        window_seconds=60,
        key_prefix="rate_limit:ai:rewrite",
    )

    assert limiter.is_allowed("3") is True
    assert limiter.is_allowed("3") is False
    assert client.expirations["rate_limit:ai:rewrite:3"] == 60
