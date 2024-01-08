from datetime import datetime, date, timedelta
from glob import glob
import json
from pathlib import Path
import os.path

filespec = '*.json'
dirpath = Path('.').absolute()
dirpath = dirpath / 'sample_data'
filepaths = list(glob(str(dirpath / filespec)))

def mark_date(mark):
    time = datetime.fromisoformat(mark['date'])
    time = time.strftime("%Y-%m-%d")
    return time

for filepath in filepaths:
    with open(filepath) as f_in:
        text = f_in.read()
    data = json.loads(text)
    print('\nFILE: ', str(os.path.basename(filepath)))
    marks = data['marks']
    print('  start-date: ', mark_date(marks[0]))
    print('    date#1: ', mark_date(marks[0]))
    print('    date#-2: ', mark_date(marks[-2]))
    try:
        print('  end-date  : ', mark_date(marks[-1]))
    except TypeError:
        print('oops, bad date in last entry')
        print('last entry = ', marks[-1])

