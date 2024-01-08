from datetime import datetime, date, timedelta
from glob import glob
import json
from pathlib import Path
import re

filespec = 'combined*.json'
dirpath = Path('.').absolute()
dirpath = dirpath / 'sample_data'
filepaths = list(glob(str(dirpath / filespec)))
filepath = filepaths[0]



with open(filepath) as f_in:
    text = f_in.read()

data = json.loads(text)
print(type(data))
print(data.keys())

marks = data['marks']

def pr(lines):
    print('\n'.join(str(x) for x in lines))


prev_mark_day = datetime(2000,1,1)
day_begun = False

def decode_time_string(input_time, time_string):
    # Decode a four-digit time string and return a timestamp.
    # Returns :
    #   (time, error_string) : (timedate, string or None)
    # Replaces input time-of-day with content from string, but will also move
    # into next day if hours>=24.
    global prev_mark_day, day_begun

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

    year, month, day = input_time.year, input_time.month, input_time.day
    result_time = datetime(year, month, day)
    if result_time > prev_mark_day:
        day_begun = False
        prev_mark_day = result_time

    if bool(time_prob) or hh > 9:
        # mark this day as 'begun', after which 00:00-07:55 --> next day
        day_begun = True

    if not time_prob:
        # If there is a recorded time, we expect it to be roughly earlier than
        # the comment record time.
        # We may refer to an early morning by hours from 24..30,
        # but we CAN also refers to an early morning of the next day directly
        # as hours 0000..0700 (say)
        record_hour = input_time.hour
        if day_begun:
            if hh >= 0 and hh < 8 and hh < (record_hour - 1):
                hh += 24
        result_time += timedelta(hours=hh, minutes=mm)
    else:
        result_time = input_time

    return (result_time, time_prob)


# Each comment-line in "standard format", should begin "tttt Lx[-x]"
def decode_comment_line(input_time, line):
    """
    Decode a single comment line.
    Return (timedate:datetime, level:float, problems:Set[str], took_pill:bool)
    """
    global skip_initial_missing_levels  #? debug usage only

    # Find pill *anywhere* in line (and remove)
    pill_match = re.search(r'\b(pill|almo(tryptan)?)\b',
                           line,
                           re.IGNORECASE)
    took_pill = pill_match is not None
    if took_pill:
        line = line[0:pill_match.start()] + line[pill_match.end() + 1:]

    time_match = re.search(r'\d\d\d\d', line)
    if time_match:
        time_string = time_match.group()  # ALWAYS a string (maybe empty)
        line = line[:time_match.start()] + line[time_match.end() + 1:]
    else:
        time_string = ""
    timestamp, time_error = decode_time_string(input_time, time_string)

    level_match = re.search(r'l(?P<lA>\d)(-(?P<lB>\d))?', line,
                           flags=re.IGNORECASE)
    if level_match:
        lA = level_match.group('lA')
        lB = level_match.group('lB')
    elif re.search(r'\b(ok|okay)\b', line, re.IGNORECASE):
        # NOTE: not including "better" : too often used as relative term
        lA, lB = 0, None
    elif took_pill:
        lA, lB = '2', ''  # Assume standard "l2" when a pill was taken
    else:
        lA, lB = None, None
    probs = set()
    level = None
    if time_error:
        probs.add(time_error)
    if lA is None:
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
    """
    Decode a "mark" dictionary

    Returns: (time:datetime, out_lines_data:List[str], out_lines:List[str])
        * time is the record-time of the mark
        * out_lines_data is decode-info from the comments line
          = List[(comment-timedate:datetime, level:float, problems:Set[str], took_pill:bool)]
        * out_lines is the corresponding raw-form comment string lines (split + stripped)

    Relevant elements (keys) of the 'mark' are interpreted: 'date', 'time', 'comment'
    N.B. several "marks" may belong to a single day (will need grouping).
    'comment' consists of multiple lines
    The mark 'time' is assigned to individual comments, *only* when timestamps absent in 'comment'
    """
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
skip_initial_missing_levels = 0
# for i_mark, mark in enumerate(marks):
#     try:
#         decode_mark(mark)
#     except AssertionError as e:
#         print(f"Failed @{i_mark}: {e}")
#         print_raw_mark(i_mark, mark)

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
i_noneoks = np.where(~marks_someok)[0]
print(f"First-all-ok={i_alloks[0]},  Last-all-ok={i_alloks[-1]}")
print(f"First-notall-ok={i_nalloks[0]},  Last-notall-ok={i_nalloks[-1]}")
print(f"First-some-ok={i_someoks[0]},  Last-some-ok={i_someoks[-1]}")
print(f"First-none-ok={i_noneoks[0]},  Last-none-ok={i_noneoks[-1]}")
# print(f"All noks :\n {i_noks}")



#debug...
prev_mark_day = datetime(2000,1,1)
day_begun = False
for i_mark in range(1664,1667):
    decode_mark(marks[i_mark])


# print('')
# for i_mark in range(1231, 1234):
#     print_raw_mark(i_mark, marks[i_mark])
#     print('\n'.join(str(x) for x in decode_mark(marks[i_mark])))

# Show ALL the nasties...

out_mode = "intermediate"

out_lines = []

# for i_mark in i_noneoks:
# for i_mark in range(260, 280):
prev_date = datetime(2000,1,1)
latest_date = prev_date
for i_mark in range(len(mark_linesets)):
    mark_time = mark_times[i_mark]
    infos = mark_linesets[i_mark]
    lines = mark_lines[i_mark]
    if not lines:
        continue

    # show raw CSV output split by entry day (for humans only)
    current_date = datetime(mark_time.year, mark_time.month, mark_time.day)
    if current_date > latest_date:
        out_lines.append('')
    latest_date = current_date

    if i_mark not in i_alloks:
        print('')
        print(f'i_mark = {i_mark}')

    for i_line, (info, line) in enumerate(zip(infos, lines)):
        errs = info[2]
        if errs is None:
            errs = ""
            ok_str = "   "
        else:
            assert i_mark not in i_alloks
            if i_mark in i_someoks:
                ok_str = "-?-"
            else:
                ok_str = "XXX"

        # if info[2] is not None:
        pill_str = 'PILL' if info[3] else ''
        # ok_str = '=!' if not errs else ''
        lev = info[1]
        if lev is not None:
            lev = '{:0.1f}'.format(lev)
        else:
            lev = ' --'

        if 'no time' in errs and not pill_str:
            ok_str = "SKIPPED!"

        # if 'no level code' in errs and 'no time' in errs:
        # if errs and 'no time' not in errs and 'no level code' not in errs:
        # if errs: # and errs != ['no level code']:
        print(f'@{i_line:03d} {ok_str} T{info[0]} L{lev} {pill_str.ljust(4)}  \\{line}\\ {errs!s}')

        # # Skip out from certain errors
        # if 'no time' in errs and not pill_str:
        #     # Simply skip these ones : they seem to have no value
        #     continue

        line_els = [
            'i-mark:', i_mark,
            'i-line:', i_line
        ]
        line_els += [
            'mark-time:', str(mark_time)
        ]

        tref = info[0]
        fwd_date = "- - -" if tref >= prev_date else "BACK!"
        prev_date = tref
        line_els += [
            "date-fwd:", fwd_date,
            "datetime:",
            tref.year, tref.month, tref.day,
            tref.hour, tref.minute
        ]

        line_els += [
            "pill:", 1 if pill_str else 0
        ]
        line_els += [
            "level:", -1.0 if '--' in lev else float(lev)
        ]
        line_els += [
            "errors:", errs
        ]
        # escape the line content : must not have
        line_els += [
            'raw:', line
        ]

        line_els = [repr(el) for el in line_els]
        out_lines.append(', '.join(line_els))

# import matplotlib.pyplot as plt
# plt.plot(~marks_ok)
# plt.show()

# for i_line, line in enumerate(out_lines):
#     print(f'line#{i_line:04} : "{line}"')

filepth = Path(filepath)
basename = filepth.name
extension_string = '.json'
assert basename.endswith(extension_string)
outname = "output_" + basename[:-len(extension_string)] + ".csv"
pth_out = filepth.parent / outname
with open(pth_out, 'wt') as f_out:
    f_out.write('\n'.join(out_lines))

t_dbg = 0