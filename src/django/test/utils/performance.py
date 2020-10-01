import functools
import time

from django.db import connection, reset_queries


def query_debugger(func):
    """
    Function decorator which measures execution time and the number of queries executed.
    """
    @functools.wraps(func)
    def inner_func(*args, **kwargs):
        reset_queries()

        n_queries_start = len(connection.queries)

        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        n_queries_end = len(connection.queries)

        print(f"Function: {func.__name__}")
        print(f"Number of Queries: {n_queries_end - n_queries_start}")
        print(f"Finished in: {(end_time - start_time):.2f}s")
        return result

    return inner_func
