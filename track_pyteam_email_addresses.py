#!/usr/bin/env python3
#
# Keep track of the Python Team email address harmonization to tracker
#
# Copyright (c) 2021 Sandro Tosi <morph@debian.org>
# License: MIT

import datetime
import json

import dateutil
import matplotlib.dates as mdates
import psycopg2
from matplotlib import pyplot as plt


DATAFILE = 'data/pyteam_email_addresses.json'
TODAY = datetime.date.today().isoformat()
DATA = json.loads(open(DATAFILE).read())
QUERY = """
SELECT maintainer_email, COUNT(*)
  FROM sources
 WHERE release = 'sid'
   AND maintainer_email LIKE '%python%'
   AND maintainer_email NOT IN ('gst-python1.0@packages.debian.org', 'pkg-python-debian-maint@lists.alioth.debian.org')
 GROUP BY maintainer_email;
"""
LINEWIDTH = {"team+python@tracker.debian.org": 4}

conn = psycopg2.connect("postgresql://udd-mirror:udd-mirror@udd-mirror.debian.net/udd")
cursor = conn.cursor()

cursor.execute(QUERY)
todaydata = cursor.fetchall()

for emailaddr, count in todaydata:
    if emailaddr in DATA:
        DATA[emailaddr][TODAY] = count
    else:
        DATA[emailaddr] = {TODAY: count}

with open(DATAFILE, 'w') as f:
    json.dump(DATA, f, indent=2)

plt_locator = mdates.DayLocator()
plt_formatter = mdates.AutoDateFormatter(plt_locator)
fig, ax = plt.subplots()
fig.set_size_inches(16, 10)
ax.xaxis.set_major_locator(plt_locator)
ax.xaxis.set_major_formatter(plt_formatter)
for k, v in DATA.items():
    ax.plot(list(map(dateutil.parser.parse, DATA[k].keys())), DATA[k].values(), label=f"{k} ({v.get(TODAY, 0)})", linewidth=LINEWIDTH.get(k, 1.5))
plt.xticks(rotation=18, ha='right')
plt.grid()
fig.tight_layout()
ax.legend(loc='center left')
plt.savefig('images/python_team_emails.svg')
