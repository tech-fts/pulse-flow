from redis.asyncio import Redis

TOKEN_BUCKET_LUA = """
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

async def is_rate_limited(redis: Redis, key: str, limit: int = 1000) -> bool:
    allowed = await redis.eval(TOKEN_BUCKET_LUA, 1, key, limit)
    return allowed == 0


