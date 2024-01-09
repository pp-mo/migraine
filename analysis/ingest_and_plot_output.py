import datetime
from datetime import datetime as make_dt
import numpy as np
from output_repr_modified import day_groups

import matplotlib.pyplot as plt


def fetch_els(els, key, n=1):
    i_at = els.index(f"'{key}:'") + 1
    result = els[i_at: i_at + n]
    if n == 1:
        (result,) = result
    return result


all_data = []
for daygroup in day_groups:
    day_entries = []
    for entry in daygroup:
        errs = fetch_els(entry, 'errors')
        if 'no level code' in errs or 'NOTIME-SKIP' in errs:
            continue
        year, month, day = [int(el) for el in fetch_els(entry, 'date', 3)]
        hour, minute = [int(el) for el in fetch_els(entry, 'time', 2)]
        level = fetch_els(entry, 'level')
        level = float(level)
        pill = fetch_els(entry, 'pill')
        pill = bool(int(pill))
        time = make_dt(year=year, month=month, day=day, hour=hour, minute=minute)
        all_data.append((time, level, pill))

all_data = sorted(all_data, key=lambda e: e[0])
timepoints = np.array([e[0] for e in all_data])
levels = np.array([e[1] for e in all_data])
pills = np.array([e[2] for e in all_data], dtype=float)
t_dbg = 0

# now we need to scan for individual attacks + insert missing "ok now" points after a
# decent interval.
# Proposal :
#   - where there is a break of >= 12 hours between 2 records
#   - insert a level-zero record at 3 hrs after the last
break_threshold = datetime.timedelta(hours=12.0)
break_offtime = datetime.timedelta(hours=3.0)
break_ontime = datetime.timedelta(minutes=1.0)

next_record_deltas = timepoints[1:] - timepoints[0:-1]
break_indices = np.array(np.where(next_record_deltas > break_threshold)[0] + 1)

attack_at = np.where(levels > 0.0)[0][0]
attack_starts = []
attack_ends = []

timepoints, levels, pills = [list(x) for x in (timepoints, levels, pills)]
while len(break_indices):
    i_break, break_indices = break_indices[0], break_indices[1:] + 2
    attack_starts.append(attack_at)
    attack_ends.append(i_break)
    attack_at = i_break  + 2
    timepoints[i_break:i_break] = [
        timepoints[i_break - 1] + break_offtime,
        timepoints[i_break] - break_ontime
    ]
    levels[i_break:i_break] = [0.0, 0.0]
    pills[i_break:i_break] = [False, False]

timepoints, levels, pills = [np.array(x) for x in (timepoints, levels, pills)]

years = np.arange(2017, 2024)
secs_in_day = 24.0 * 60. * 60.
for i_year, year in enumerate(years):
    v_offs = i_year * 10.0
    mth_days = [0] * 12
    for i_month in range(1, 13):
        start_day = make_dt(year, i_month, 1)
        if i_month == 12:
            end_day = make_dt(year + 1, 1, 1)
        else:
            end_day = make_dt(year, i_month + 1, 1)
        in_month = (timepoints >= start_day) & (timepoints < end_day)
        mth_timepoints = timepoints[in_month]
        mth_days[i_month - 1] = len(set(
            [make_dt(t.year, t.month, t.day) for t in mth_timepoints]
        ))

    print(f'{year} month_days: ',  ', '.join([
        f'{d:02d} ' for d in mth_days
    ]))

    start_day = make_dt(year, 1, 1)
    end_day = make_dt(year + 1, 1, 1)
    in_year = (timepoints >= start_day) & (timepoints < end_day)
    year_timepoints = timepoints[in_year]
    year_timepoints = np.array([
        (x - start_day).total_seconds()
        for x in year_timepoints
    ])
    year_timepoints = year_timepoints / secs_in_day
    year_levels = levels[in_year]
    year_pills = pills[in_year]
    plt.plot(year_timepoints, -v_offs + year_levels, label=year)

    for i_point in range(len(year_timepoints)):
        if year_pills[i_point]:
            plt.plot(year_timepoints[i_point], -v_offs + 5.5, '+', color='red')

    for i_month in range(1, 13):
        month_start_day = make_dt(year, i_month, 1)
        x_pt = (month_start_day - start_day).total_seconds() / secs_in_day
        plt.plot([x_pt, x_pt], [-v_offs, -v_offs + 5], '--', color='blue')

ax = plt.gca()
ax.yaxis.set_ticks(
    -10. * (years - years[0]),
    [str(x) for x in years]
)
plt.suptitle('all data by years')
plt.show()

profile_points_xs = [[] for _ in range(2017, 2024)]
profile_points_ys = [[] for _ in range(2017, 2024)]

# show_profile_scatter = True
show_profile_scatter = False

for i_attack, (i_start, i_end) in enumerate(zip(attack_starts, attack_ends)):
    i_year = timepoints[i_start].year - years[0]
    v_offs = 10.0 * i_year
    time_offs = timepoints[i_start: i_end] - timepoints[i_start]
    time_offs = np.array([t.total_seconds() for t in time_offs])
    if i_end > i_start:
        attack_levels = levels[i_start:i_end]
        max_level = attack_levels.max()
        t_centre = time_offs[attack_levels == max_level].mean()
        xs = (time_offs - t_centre) / secs_in_day
        ys = attack_levels
        profile_points_xs[i_year].extend(xs)
        profile_points_ys[i_year].extend(ys)
        if show_profile_scatter:
            plt.plot(
                xs, -v_offs + ys, '.',
                markersize=2.0, color='red'
            )
    else:
        err = "?"
        assert 0

if show_profile_scatter:
    xmin, xmax = -3.0, 3.0
    plt.hlines(
        -10. * (years - years[0]),
        xmin, xmax
    )
    ax = plt.gca()
    ax.yaxis.set_ticks(
        -10. * (years - years[0]),
        [str(x) for x in years]
    )
    plt.suptitle('profile scatters by year')
    plt.show()


for year, xs, ys in zip(years, profile_points_xs, profile_points_ys):
    xs = np.array(xs)
    meanlev = np.array(ys).mean()
    sd = np.std(xs)
    print(f'Year {year} : mean duration={2.0 * sd}  : mean intensity={meanlev}')

n_bins = 60
range_bins = np.linspace(-5.0, 5.0, n_bins + 1)
bin_centres = 0.5 * (range_bins[:-1] + range_bins[1:])
for year, xs, ys in zip(years, profile_points_xs, profile_points_ys):
    xs, ys = (np.array(x) for x in (xs, ys))
    v_offs = 10.0 * (year - 2017)
    bin_entries = [[0.0] for _ in range(n_bins)]
    for i_bin, (bmin, bmax) in enumerate(zip(range_bins[:-1], range_bins[1:])):
        b_bin_hits = ((bmin <= xs) & (xs < bmax))
        bin_entries[i_bin].extend(ys[b_bin_hits])
    profile = np.array(
        [np.mean(entries) for entries in bin_entries]
    )
    plt.plot(bin_centres[[0, -1]], [-v_offs - 0.1, -v_offs - 0.1], '--', color='lightgrey')
    plt.plot(bin_centres, -v_offs + profile, label=year)  # color='red'

plt.title('mean attack profile by year')
ax = plt.gca()
ax.yaxis.set_ticks(
    -10. * (years - years[0]),
    [str(x) for x in years]
)
plt.show()


