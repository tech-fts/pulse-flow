from redis.asyncio import Redis

# Fixed-window rate limiter (1-second window).  Atomic via Lua.
FIXED_WINDOW_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local current = tonumber(redis.call("GET", key) or "0")

if current + 1 > limit then
    return 0
else
    redis.call("INCR", key, 1)
    if current == 0 then
        redis.call("EXPIRE", key, 1) -- 1 second window
    end
    return 1
end
"""


async def check_rate_limit(redis: Redis, key: str, limit: int = 100) -> bool:
    """Return ``True`` if the key is rate-limited (request should be rejected)."""
    allowed = await redis.eval(FIXED_WINDOW_LUA, 1, key, limit)
    return allowed == 0
