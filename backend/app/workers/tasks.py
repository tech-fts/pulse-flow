import asyncio
import json
import logging

from redis.asyncio import Redis

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
STREAMS = ["stream:critical", "stream:standard", "stream:bulk"]
CONSUMER_GROUP = "dispatch_workers"
CONSUMER_NAME = "worker_1"
DLQ_STREAM = "stream:dead_letter"


async def setup_consumer_groups(redis: Redis) -> None:
    """Create consumer groups for each priority stream if they don't exist."""
    for stream in STREAMS:
        try:
            await redis.xgroup_create(stream, CONSUMER_GROUP, id="0", mkstream=True)
        except Exception:
            pass  # Group already exists


async def process_event(event_data: dict) -> bool:
    """Deliver event via gateway (SendGrid / Twilio / AWS SES).

    Returns ``True`` on success, ``False`` on delivery failure.
    """
    channel = event_data.get("channel")
    payload = json.loads(event_data.get("payload", "{}"))
    logger.info(
        "Delivering %s event %s: %s",
        channel,
        event_data.get("event_id"),
        payload,
    )
    # ── Gateway integration point ─────────────────────────────────
    # e.g. await sendgrid.send(payload)
    return True


async def run_stream_worker() -> None:
    """Main worker loop: consume, process, retry, or move to DLQ."""
    redis = await get_redis()
    await setup_consumer_groups(redis)

    while True:
        try:
            entries = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={s: ">" for s in STREAMS},
                count=10,
                block=2000,
            )

            for stream_name, messages in entries:
                for message_id, data in messages:
                    retry_count = int(data.get("retry_count", 0))

                    try:
                        success = await process_event(data)
                        if success:
                            await redis.xack(stream_name, CONSUMER_GROUP, message_id)
                        else:
                            raise Exception("Delivery failed")
                    except Exception as exc:
                        logger.warning(
                            "Processing error on %s (retry %d/%d): %s",
                            message_id,
                            retry_count,
                            MAX_RETRIES,
                            exc,
                        )
                        if retry_count < MAX_RETRIES:
                            data["retry_count"] = str(retry_count + 1)
                            await redis.xadd(stream_name, data)
                            await redis.xack(stream_name, CONSUMER_GROUP, message_id)
                        else:
                            data["failed_reason"] = str(exc)
                            await redis.xadd(DLQ_STREAM, data)
                            await redis.xack(stream_name, CONSUMER_GROUP, message_id)
        except Exception as e:
            logger.error("Worker loop error: %s", e)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_stream_worker())
