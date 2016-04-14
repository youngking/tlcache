#!/usr/bin/env python
# encoding: utf-8
from contextlib import contextmanager
from functools import wraps
import logging

from . import cache

_DEFAULT_FILE_THRESHOLD = 100000
_DEFAULT_FILE_TIMEOUT = 86400


class TLCache(cache.BaseCache):

    def __init__(self, cache_dir, threshold=1000, default_timeout=300):
        self._simple_cache = cache.SimpleCache(
            threshold=threshold, default_timeout=default_timeout)
        self._file_cache = cache.FileSystemCache(cache_dir, threshold=_DEFAULT_FILE_THRESHOLD,
                                                 default_timeout=_DEFAULT_FILE_TIMEOUT)

        self._refresh_cache = False

    def set(self, key, value, timeout=None):
        self._simple_cache.set(key, value, timeout)
        return self._file_cache.set(key, value)

    def clearall(self):
        self._simple_cache.clear()
        self._file_cache.clear()

    @contextmanager
    def with_refresh(self):
        try:
            self._refresh_cache = True
            yield
        finally:
            self._refresh_cache = False

    def cache(self, namespace=None, timeout=None):
        def wrapper(f):
            @wraps(f)
            def call(*args, **kwargs):
                cache_key = cache.generate_cache_key(
                    namespace, f, *args, **kwargs)
                rv = self._simple_cache.get(cache_key)
                if not rv or self._refresh_cache:
                    try:
                        rv = f(*args, **kwargs)
                        if rv:
                            self.set(cache_key, rv, timeout=timeout)
                    except Exception as e:
                        rv = self._simple_cache.get(cache_key) or self._file_cache.get(cache_key)
                        if not rv:
                            raise e
                        else:
                            logging.warn("function: %s is failed: %s, args: %s, kwargs: %s",
                                         f, e, args, kwargs, exc_info=1)
                return rv

            return call

        return wrapper
