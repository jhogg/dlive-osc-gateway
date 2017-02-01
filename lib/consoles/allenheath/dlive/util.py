# allenheath/dlive/util.py - common utility functions
#
#

from __future__ import print_function

__all__ = ['calc_db']


def calc_db(**kw):
    """ Convert db to linear based on straight line calcs
       -oo = 0
    -128db = 1
       0db = 0x8000
    """

    factor = (128.0 / 0x8000)

    # --- Starting Point

    if 'linear' in kw:
        linear = kw.get('linear')
        if linear != None:
            db = (linear * factor) - 128.0
        else:
            linear, db = 0, -128.0
    else:
        db = kw.get('db_abs', None)

    print("Starting db %s" % db)

    # --- Handle relative adjustment
    if 'db_rel' in kw:
        db_rel = kw.get('db_rel')
        if (db == None):
            db = -128.0
        db += db_rel

    print("After rel %s" % db)

    # --- Enforce Limits

    if 'limit_lower' in kw:
        value = kw.get('limit_lower')
        db = max([-128.0, value, db])

    if 'limit_upper' in kw:
        value = kw.get('limit_upper')
        db = min([10.0, value, db])

    # --- Convert db back to linear

    if db < -128.0:
        linear = 0
    else:
        linear = int((db + 128.0) / factor)

    return (db, linear)
