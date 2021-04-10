from datetime import datetime, date, timedelta
from glob import glob
import json
from pathlib import Path
import re

filespec = 'data_pr*.json'
dirpath = Path('.').absolute()
dirpath = dirpath / 'sample_data'
filepaths = list(glob(str(dirpath / filespec)))
filepath = filepaths[0]
#print(filepath)

with open(filepath) as f_in:
    text = f_in.read()

data = json.loads(text)
print(type(data))
print(data.keys())

marks = data['marks']

def pr(lines):
    print('\n'.join(str(x) for x in lines))


def decode_time_string(input_time, time_string):
    # Decode a four-digit time string and return a timestamp.
    # Returns :
    #   (time, error_string) : (timedate, string or None)
    # Replaces input time-of-day with content from string, but will also move
    # into next day if hours>=24.
    time_prob = None
    if time_string == '':
        time_prob = 'no time'
    if not time_prob:
        if len(time_string) != 4:
            time_prob = 'bad time length'
    if not time_prob:
        hh = int(time_string[:2])
        if (hh < 0 or hh > 30):
            # NOTE: *do* allow over-end numbers.  Translate into the next day.
            time_prob = 'bad time hours'
    if not time_prob:
        mm = int(time_string[2:])
        if (mm < 0 or mm > 59):
            time_prob = 'bad time mins'

    if not time_prob:
        year, month, day = input_time.year, input_time.month, input_time.day
        result_time = datetime(year, month, day)
        # If there is a recorded time, we expect it to be roughly earlier than
        # the comment record time.
        # We may refer to an early morning by hours from 24..30,
        # but we CAN also refers to an early morning of the next day directly
        # as hours 0000..0700 (say)
        record_hour = input_time.hour
        if hh >= 0 and hh < 8 and hh < (record_hour - 1):
            hh += 24
        result_time += timedelta(hours=hh, minutes=mm)
    else:
        result_time = input_time

    return (result_time, time_prob)

#
# # Each comment-line in "standard format", should begin "tttt Lx[-x]"
# # But plenty of lines may not obey this ...
# line_re = re.compile(
#     r"(?P<time>\d*)\?*\s*[^l]*\s*(l(?P<lA>\d)(-(?P<lB>\d))?)?",
#     flags=re.IGNORECASE)
#
# # NOTE: this should ALWAYS match, as everything is
#
# def decode_comment_line_OLD(input_time, line):
#     # Decode a single comment line.
#     # "OLD" version : single regexp approach
#     # Return (timedate, level, problems) : (datetime, float, iterable of string or None)
#     match = line_re.match(line)
#     if match is None:
#         assert False, "Match failed : should not happen"
#     time, lA, lB = (match.group(key) for key in ('time', 'lA', 'lB'))
#     timestamp, time_error = decode_time_string(input_time, time)
#     probs = set()
#     level = 0.0
#     if time_error:
#         probs.add(time_error)
#     if not lA:
#         if lB:
#             assert 1
#         assert not lB
#         probs.add('no level code')
#     else:
#         level = int(lA)
#         assert level >= 0 and level <= 5
#         if lB:
#             lB = int(lB)
#             if lB == level + 1:
#                 level = float(level) + 0.5
#             else:
#                 probs.add('lB/lA mismatch')
#         level = float(level)
#
#     if probs:
#         probs = sorted(probs)
#     else:
#         probs = None
#     return (timestamp, level, probs)


# Each comment-line in "standard format", should begin "tttt Lx[-x]"
def decode_comment_line(input_time, line):
    global skip_initial_missing_levels
    # Decode a single comment line.
    # Return (timedate, level, problems, took_pill) : (datetime, float, iterable of string or None, bool)
    # match = line_re.match(line)
    # if match is None:
    #     assert False, "Match failed : should not happen"
    # time, lA, lB = (match.group(key) for key in ('time', 'lA', 'lB'))
    time_match = re.match(r'^\d*', line)
    time_string = time_match.group()  # ALWAYS a string (maybe empty)
    timestamp, time_error = decode_time_string(input_time, time_string)
    line_rest = line[time_match.end():]
    level_match = re.search(r'l(?P<lA>\d)(-(?P<lB>\d))?', line_rest,
                           flags=re.IGNORECASE)
    pill_match = re.search(r'\b(pill|almo(tryptan))\b',
                           line_rest,
                           re.IGNORECASE)
    took_pill = pill_match is not None
    if level_match:
        lA = level_match.group('lA')
        lB = level_match.group('lB')
    elif took_pill:
        lA, lB = '2', ''  # Assume standard "l2" when a pill was taken
    else:
        lA, lB = None, None
    probs = set()
    level = None
    if time_error:
        probs.add(time_error)
    if not lA:
        assert not lB
        probs.add('no level code')
        if skip_initial_missing_levels == 0:
            t_dbg = 0
    else:
        if skip_initial_missing_levels > 0:
            skip_initial_missing_levels -= 1
        level = int(lA)
        assert level >= 0 and level <= 5
        if lB:
            lB = int(lB)
            if lB == level + 1:
                level = float(level) + 0.5
            else:
                probs.add('lB/lA mismatch')
        level = float(level)

    if probs:
        probs = sorted(probs)
    else:
        probs = None
        if lA == '0':
            t_dbg = 0
    return (timestamp, level, probs, took_pill)





PROBLEMS_SET_NOINFO = sorted(['no level code', 'no time'])
PROBLEMS_SET_NOTIME = ['no time']

def decode_mark(mark):
    # Decode a "mark" dictionary
    # Relevant components: 'date', 'time', 'comment'
    # N.B. several "marks" may belong to a single day (need grouping).
    # mark 'time' should only be used when timestamps absent in 'comment'
    # 'comment' will consist of multiple lines
    time = datetime.fromisoformat(mark['date'] + " " + mark['time'])
    lines = mark['comment'].split('\n')
    lines = [line.strip() for line in lines]
    lines = [line for line in lines if len(line) > 0]
    lines_data = [decode_comment_line(time, line) for line in lines]
    # Strip out data lines where there is no info at all.
    out_lines = []
    out_lines_data = []
    for line, data in zip(lines, lines_data):
        if data[2] != PROBLEMS_SET_NOINFO:
            out_lines.append(line)
            out_lines_data.append(data)
    return (time, out_lines_data, out_lines)


# for mark in marks[1000:1020]:

def print_raw_mark(i_mark, mark):
    print(f"\n{i_mark} : {mark.keys()}")
    time = datetime.fromisoformat(mark['date'] + " " + mark['time'])
    print(f"  time={time!r}")
    for key, cont in mark.items():
        print(f"    @{key}: {cont!r}")

global skip_initial_missing_levels
skip_initial_missing_levels = 2
for i_mark, mark in enumerate(marks):
    try:
        decode_mark(mark)
    except AssertionError as e:
        print(f"Failed @{i_mark}: {e}")
        print_raw_mark(i_mark, mark)

decodes = [decode_mark(mark) for mark in marks]
# Each mark-decode is (mark-time, line-decodes)
mark_times = [decode[0] for decode in decodes]
assert all(t0 <= t1 for t0, t1 in zip(mark_times[:-1], mark_times[1:]))
mark_linesets = [decode[1] for decode in decodes]
mark_lines = [decode[2] for decode in decodes]

# Each line-decode is (time, level, errors)
mark_allok = [all(line_decode[2] is None for line_decode in lineset)
              for lineset in mark_linesets]
mark_someok = [not all(line_decode[2] is not None for line_decode in lineset)
               for lineset in mark_linesets]
import numpy as np
marks_ok = np.array(mark_allok)
marks_someok = np.array(mark_someok)
print(f"Num all-ok = {np.count_nonzero(marks_ok)}")
print(f"Num not-all-ok = {np.count_nonzero(~marks_ok)}")
print(f"Num some-ok = {np.count_nonzero(marks_someok)}")
print(f"Num none-ok = {np.count_nonzero(~marks_someok)}")
i_alloks = np.where(marks_ok)[0]
i_nalloks = np.where(~marks_ok)[0]
i_someoks = np.where(marks_someok)[0]
i_nsomeoks = np.where(~marks_someok)[0]
print(f"First-all-ok={i_alloks[0]},  Last-all-ok={i_alloks[-1]}")
print(f"First-notall-ok={i_nalloks[0]},  Last-notall-ok={i_nalloks[-1]}")
print(f"First-some-ok={i_someoks[0]},  Last-some-ok={i_someoks[-1]}")
print(f"First-none-ok={i_nsomeoks[0]},  Last-none-ok={i_nsomeoks[-1]}")
# print(f"All noks :\n {i_noks}")

# print('')
# for i_mark in range(1231, 1234):
#     print_raw_mark(i_mark, marks[i_mark])
#     print('\n'.join(str(x) for x in decode_mark(marks[i_mark])))

# Show ALL the nasties...

# sel_noks = i_nalloks[145:]
sel_noks = i_nalloks
# for i_mark in sel_noks:
for i_mark in range(len(mark_linesets)):
    infos = mark_linesets[i_mark]
    lines = mark_lines[i_mark]
    if not lines:
        continue
    if i_mark == 1237:
        t_dbg = 0
    print('')
    print(f'i_bad = {i_mark}')
    for i_line, (info, line) in enumerate(zip(infos, lines)):
        errs = info[2]
        if errs is None:
            errs = ''
        else:
            errs = f"   ##{errs}"
        # if info[2] is not None:
        pill_str = 'PILL' if info[3] else ''
        ok_str = '=!' if not errs else ''
        lev = info[1]
        if lev is not None:
            lev = '{:0.1f}'.format(lev)
        else:
            lev = ' --'
        print(f'@{i_line:03d} T{info[0]} L{lev} {pill_str.ljust(4)} {ok_str.ljust(2)}  \\{line}\\ {errs!s}')

# import matplotlib.pyplot as plt
# plt.plot(~marks_ok)
# plt.show()

t_dbg = 0