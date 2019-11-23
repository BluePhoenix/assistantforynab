import collections
import glob
import datetime
import os
import pdb
import traceback

import ynabassistant as ya
import ynab_api


def get_log_path():
    log_name = str(ya.settings.start_time) + '-log.txt'
    return os.path.join(ya.settings.log_dir, log_name)


log_file = open(get_log_path(), 'a+')


def log_info(*x, sep=os.linesep, end=os.linesep * 2):
    formatted = []
    formatters = {ynab_api.TransactionDetail: ya.ynab.utils.format_transaction,
                  ynab_api.SubTransaction: ya.ynab.utils.format_subtransaction}
    for i in x:
        if type(i) in formatters:
            formatted.append(formatters[type(i)](i))
        else:
            formatted.append(i)
    _log(*formatted, verbosity=ya.settings.info_verbosity, sep=sep, end=end)


def log_debug(*x, sep=os.linesep, end=os.linesep * 2):
    _log(*x, verbosity=ya.settings.debug_verbosity, sep=sep, end=end)


def log_error(*x, sep=os.linesep, end=os.linesep * 2):
    _log(*x, verbosity=ya.settings.error_verbosity, sep=sep, end=end)


def _log(*x, verbosity=0, sep=' | ', end=os.linesep * 2):
    if verbosity <= ya.settings.log_verbosity:
        print(datetime.datetime.now(), end=os.linesep, file=log_file)
        print(*x, sep=sep, end=end, file=log_file)
    if verbosity <= ya.settings.print_verbosity:
        print(*x, sep=sep, end=end)


def to_datetime(d):
    if d is None:
        return None
    if type(d) is datetime.date:
        return datetime.datetime(*d.timetuple()[:3])
    assert type(d) is datetime.datetime
    return d


def newer_than(d, days_ago=30):
    d = to_datetime(d)
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days_ago)
    return d > cutoff


def clear_old_logs():
    log_debug('clear_old_logs')
    for name in glob.glob(ya.settings.log_dir):
        path = os.path.join(ya.settings.log_dir, name)
        modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        if not newer_than(modified_time, ya.settings.max_log_age_days):
            os.remove(path)


clear_old_logs()


def group_by(collection, key):
    grouped = collections.defaultdict(list)
    for c in collection:
        grouped[key(c)].append(c)
    return grouped


def by(collection, key):
    d = collections.OrderedDict()
    for c in collection:
        k = key(c)
        assert k not in d
        d[k] = c
    return d


def find_by(collection, predicate):  # TODO reverse arg order on all these to be function, iterable
    matches = list(filter(predicate, collection.values()))
    assert len(matches) <= 1
    if matches:
        return matches.pop()


separator = '\n' + '.' * 100 + '\n'


def equalish(a, b, precision=4):
    return round(a, precision) == round(b, precision)


def debug():
    pdb.set_trace()


def log_exception_debug():
    log_debug('DEBUG', traceback.format_exc())


def log_exception():
    log_error(traceback.format_exc())
    return


date_format = '%Y-%m-%d'


def format_date(d, df=date_format):
    return d.strftime(df)


def parse_date(d, df=date_format):
    return datetime.datetime.strptime(d, df)


one_day = datetime.timedelta(1)


def to_float_days(d):
    return d.total_seconds() / one_day.total_seconds()


def day_delta(a, b=None):
    a = to_datetime(a)
    b = to_datetime(b) or now()

    return abs(to_float_days(a - b))


def format_money(p):
    assert type(p) in (float, int)
    return ('' if p >= 0 else '-') + '$' + str(abs(round(p, 2)))


def filter_dict(d, whitelist):
    if not type(d) is dict:
        d = d.__dict__
    return {k: d[k] for k in d if k in whitelist}


def now():
    return datetime.datetime.now()


def _convert(obj, t):
    init_params = t.__init__.__code__.co_varnames
    d = obj.__dict__
    # [1:] slices off the `_` at start of variable names
    # because (I think) generated classes are overriding to_dict
    filtered = {k[1:]: d[k] for k in d if k[1:] in init_params}
    cast = {k: int(v) if type(v) is float else v for (k, v) in filtered.items()}
    return t(**cast)


def convert(obj, t):
    if type(obj) in (tuple, list):
        return list(map(lambda o: _convert(o, t), obj))
    return _convert(obj, t)