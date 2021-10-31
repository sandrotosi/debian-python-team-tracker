#!/usr/bin/env python3
#
# Keep track of the Python Team email address harmonization to tracker
#
# Copyright (c) 2021 Sandro Tosi <morph@debian.org>
# License: MIT

import datetime
import email.utils
import json
from collections import defaultdict

import dateutil
import matplotlib.dates as mdates
import psycopg2
from matplotlib import pyplot as plt

DATAFILE = 'data/pyteam_email_addresses.json'
TODAY = datetime.date.today().isoformat()
DATA = json.loads(open(DATAFILE).read())

MAINT_QUERY = """
SELECT maintainer_email, source, version
  FROM sources
 WHERE release = 'sid'
   AND maintainer_email LIKE '%python%'
   AND maintainer_email NOT IN ('gst-python1.0@packages.debian.org', 'pkg-python-debian-maint@lists.alioth.debian.org');
"""
UPLDR_QUERY = """
SELECT uploaders, source, version
  FROM sources
 WHERE release = 'sid'
   AND uploaders LIKE '%python%';
"""

LINEWIDTH = {"team+python@tracker.debian.org": 4}

conn = psycopg2.connect("postgresql://udd-mirror:udd-mirror@udd-mirror.debian.net/udd")
conn.set_client_encoding('UTF-8')
cursor = conn.cursor()

# process Maintainers
cursor.execute(MAINT_QUERY)
todaydata = cursor.fetchall()

data = defaultdict(list)

for emailaddr, source, version in todaydata:
    data[emailaddr].append((source, version))

# process Uploaders
cursor.execute(UPLDR_QUERY)
todaydata = cursor.fetchall()

# the field can contain multiple address, so we need to parse it further
for emailaddrs, source, version in todaydata:
    for emailaddr in emailaddrs.split(', '):
        name, addr = email.utils.parseaddr(emailaddr)
        if 'python' in addr and addr not in ('gijs@pythonic.nl', 'debian-python@lists.debian.org'):
            data[addr].append((source, version))

for emailaddr, pkgs in data.items():
    if emailaddr in DATA:
        DATA[emailaddr][TODAY] = len(pkgs)
    else:
        DATA[emailaddr] = {TODAY: len(pkgs)}

with open(DATAFILE, 'w') as f:
    json.dump(DATA, f, indent=2)

# Generate the progress image
plt_locator = mdates.AutoDateLocator()
plt_formatter = mdates.AutoDateFormatter(plt_locator)
fig, ax = plt.subplots()
fig.set_size_inches(16, 10)
ax.xaxis.set_major_locator(plt_locator)
ax.xaxis.set_major_formatter(plt_formatter)
for k, v in DATA.items():
    ax.plot(list(map(dateutil.parser.parse, DATA[k].keys())), DATA[k].values(), label=f"{k} ({v.get(TODAY, 0)})", linewidth=LINEWIDTH.get(k, 1.5))
ax.axvline(datetime.date(2021, 9, 5), ymin=0, ymax=1, color='red', linestyle='dashed')
ax.annotate('Added uploaders data', xy=(datetime.date(2021, 9, 5), 300), xytext=(datetime.date(2021, 9, 1), 200), arrowprops=dict(facecolor='red'), xycoords='data', color='red')
plt.xticks(rotation=18, ha='right')
plt.grid()
fig.tight_layout()
ax.legend(loc='center left')
plt.savefig('images/python_team_emails.svg')

# Generate the updated README.md page
with open('README.md.top') as f:
    mdpage = f.readlines()

mdpage.extend(['', '# Packages with outdated email address', ''])

for addr in sorted(data.keys()):
    if addr == 'team+python@tracker.debian.org':
        continue

    pkgs = data[addr]
    mdpage.append(f"## `{addr}`")
    mdpage.append(f"Total packages: {len(pkgs)}")

    pkgs.sort(key=lambda x: x[0])

    start = 1
    stop = 1
    _l = ['', '| # | Package | Version |', '| --- | --- | --- |']

    for i, pkg in enumerate(pkgs):
        stop = i + 1
        _l.append(f"| {stop} | [{pkg[0]}](https://tracker.debian.org/{pkg[0]}) | {pkg[1]} |")

        if stop % 50 == 0:
            mdpage.extend(['<details>', f'<summary><b>{start}..{stop}</b></summary>', ''])
            mdpage.extend(_l)
            mdpage.append('</details>')
            start = stop + 1
            stop = 0
            _l = ['| # | Package | Version |', '| --- | --- | --- |']

    mdpage.extend(['<details>', f'<summary><b>{start}..{stop}</b></summary>', ''])
    mdpage.extend(_l)
    mdpage.append('</details>')
    mdpage.append('')

with open('README.md', 'w') as f:
    f.write('\n'.join(mdpage))
