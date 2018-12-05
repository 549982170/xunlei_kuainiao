#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018-12-03 19:41
# @Author  : yves175


class URLError(IOError):
    # URLError is a sub-type of IOError, but it doesn't share any of
    # the implementation.  need to override __init__ and __str__.
    # It sets self.args for compatibility with other EnvironmentError
    # subclasses, but args doesn't have the typical format with errno in
    # slot 0 and strerror in slot 1.  This may be better than nothing.
    def __init__(self, reason):
        self.args = reason,
        self.reason = reason

    def __str__(self):
        return '<urlopen error %s>' % self.reason
