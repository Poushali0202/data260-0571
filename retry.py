import logging
import time

log = logging.getLogger("retry")

ATTEMPTS = 3
BASE_DELAY = 0.2
MAX_DELAY = 1.0


def retry_call(operation, attempts=ATTEMPTS, base_delay=BASE_DELAY, max_delay=MAX_DELAY,
               retry_on=(ConnectionError, TimeoutError, OSError), sleep=time.sleep):
    for attempt in range(1, attempts + 1):
        try:
            result = operation()
            log.info("attempt %d/%d succeeded", attempt, attempts)
            return result
        except retry_on as error:
            if attempt == attempts:
                log.error("attempt %d/%d failed: %s; giving up", attempt, attempts, error)
                raise
            delay = min(max_delay, base_delay * 2 ** (attempt - 1))
            log.warning("attempt %d/%d failed: %s; retrying in %.1f s", attempt, attempts, error, delay)
            sleep(delay)
