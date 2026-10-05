import logging

from retry import retry_call

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def flaky(outcomes):
    outcomes = list(outcomes)

    def operation():
        step = outcomes.pop(0)
        if step == "F":
            raise ConnectionError("simulated connection reset")
        return "row fetched"

    return operation


for label, pattern in [("success on first attempt", "S"), ("failure then success", "FS"), ("failure on all attempts", "FFF")]:
    print(f"\n=== {label} (pattern {pattern}) ===")
    try:
        print("result:", retry_call(flaky(pattern)))
    except ConnectionError as error:
        print("clean error result:", {"ok": False, "data": None, "error": f"storage error: {error}"})
