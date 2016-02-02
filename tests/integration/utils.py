import time

def retry(assertion_callable, retry_time=10, wait_between_tries=0.1, exception_to_retry=AssertionError):
    start = time.time()
    while True:
        try:
            return assertion_callable()
        except exception_to_retry as e:
            if time.time() - start >= retry_time:
                raise e
            time.sleep(wait_between_tries)
