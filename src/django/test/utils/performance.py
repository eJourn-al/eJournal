import functools
import json
import time
from contextlib import contextmanager
from pprint import pprint

from django.db import connections
from django.test.utils import CaptureQueriesContext


@contextmanager
def query_debug_manager(db_alias='default', label=None, verbose=False):
    """
    Python context manager which measures execution time and the number of queries executed.
    """
    start_time = time.perf_counter()

    with CaptureQueriesContext(connections[db_alias]) as context:
        yield

    end_time = time.perf_counter()

    if label:
        print(label)
    print(f'Number of Queries: {context.final_queries - context.initial_queries}')
    print(f'Finished in: {(end_time - start_time):.2f}s')

    if verbose:
        pprint(context.captured_queries)


def query_debug_decorator(func, db_alias='default', verbose=False):
    """
    Function decorator which measures execution time and the number of queries executed.
    """
    @functools.wraps(func)
    def inner_func(*args, **kwargs):
        with query_debug_manager(db_alias, label=f'Function: {func.__name__}', verbose=verbose):
            result = func(*args, **kwargs)

        return result
    return inner_func


def queries_invariant_to_db_size(
        call, add_state, call_args=[], call_kwargs={}, db_alias='default', max=float('inf'), verbose=False):
    """
    Asserts that the number of queries executed by call before and after the database state is changed remains equal.

    Args:
        call (func), function whose contents execution should be measured
        add_state, iterable consisting of callable elements which change the db state
        max (number), number of executed queries during call cannot exceed max
    """
    with CaptureQueriesContext(connections[db_alias]) as pre_add_context:
        call(*call_args, **call_kwargs)

    for elem in add_state:
        if isinstance(elem, tuple) or isinstance(elem, list):
            elem[0](**elem[1])
        else:
            elem()

    with CaptureQueriesContext(connections[db_alias]) as post_add_context:
        call(*call_args, **call_kwargs)

    if verbose:
        print('Queries captured before state was added:')
        pprint(pre_add_context.captured_queries)
        print('\nQueries captured after state was added:')
        pprint(post_add_context.captured_queries)

    assert len(pre_add_context.captured_queries) == len(post_add_context.captured_queries), \
        'Number of queries executed in call is not invariant to the provide state change(s)'
    assert len(pre_add_context.captured_queries) <= max, 'Executed queries exceed provided maximum'


@contextmanager
def assert_num_queries_less_than(value, db_alias='default', verbose=False):
    """
    Asserts that the number of queries in the executed block is less than value.

    Args:
        value (number), query check limit
        verbose (bool), flag used to display the executed queries on stdout on failure
    """
    with CaptureQueriesContext(connections[db_alias]) as context:
        yield

    if verbose:
        msg = '\n%s' % json.dumps(context.captured_queries, indent=4)
    else:
        msg = f'{len(context.captured_queries)} >= {value}'

    assert len(context.captured_queries) < value, msg


class QueryContext(CaptureQueriesContext):
    """Wrapper around CaptureQueriesContext, saves some imports and params"""
    def __init__(self, connection=connections['default']):
        super().__init__(connection)
