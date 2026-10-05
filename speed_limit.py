import asyncio
import time

_buckets = {}

MIN_RATE = 1024
MIN_BURST = 16 * 1024


class Bucket:

    def __init__(self, rate):
        self.rate = max(int(rate), MIN_RATE)
        self.capacity = max(self.rate, MIN_BURST)
        self.tokens = self.capacity
        self.last = time.monotonic()

    def refill(self):

        now = time.monotonic()
        elapsed = now - self.last

        if elapsed > 0:
            self.last = now
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )

    async def consume(self, amount):

        while True:

            self.refill()

            if self.tokens >= amount:
                self.tokens -= amount
                return

            deficit = amount - self.tokens

            wait = deficit / self.rate

            await asyncio.sleep(
                min(max(wait, 0.004), 0.5)
            )


def get_bucket(client_id, rate):

    bucket = _buckets.get(client_id)

    real_rate = max(
        int(rate),
        MIN_RATE
    )

    if bucket is None or bucket.rate != real_rate:

        bucket = Bucket(real_rate)

        _buckets[client_id] = bucket

    return bucket


async def throttle(
    client_id,
    amount
):

    if amount <= 0:
        return

    bucket = get_bucket(
        client_id,
        0
    )

    await bucket.consume(amount)


def reset_bucket(client_id):

    _buckets.pop(
        client_id,
        None
    )
