#!/usr/bin/python2
from calendar import day_name, month_name
import re
from datetime import datetime, timedelta, time
import sys
import email
from email.utils import parsedate
from itertools import takewhile, dropwhile
from tempfile import mkstemp
import os
from subprocess import check_call
from icalendar import Calendar, Event

days = [day.lower() for day in day_name]
days_abbr = [day.lower()[:3] for day in day_name]
days_abbr2 = [day.lower()[:4] for day in day_name]
months = [month.lower() for month in month_name][1:]
months_abbr = [month.lower()[:3] for month in month_name][1:]


def clean(text):
    lines = [line.strip() for line in text.splitlines()]
    lines = list(takewhile(lambda x: not (x.startswith("---") or x == "--"),
                           lines))
    lines.reverse()
    lines = list(dropwhile(lambda x: not x, lines))
    if lines[0].startswith(">"):
        lines = list(dropwhile(lambda x: x.startswith(">"), lines))
        lines = list(dropwhile(lambda x: not x, lines))
        lines = list(dropwhile(lambda x: x, lines))
    lines.reverse()
    lines = [line.strip() for line in lines if line]
    text = " ".join(line for line in lines if not line.startswith(">"))
    text = text.translate(None, ",.!?*\"()").lower()
    text = " ".join(text.split())
    return text


def parse_dates(text, ref=None):
    if not ref:
        ref = datetime.now().date()

    l = []

    def sub(match):
        groups = match.groupdict()
        date = ref.replace(day=int(groups["day"]), month=int(groups["month"]))
        if groups["year"]:
            date = date.replace(year=int(groups["year"]))
        l.append((date, match.span()))
        return "#" * (match.end() - match.start())

    text = re.sub(r"(?P<month>\d{1,2})/(?P<day>\d{2})"
                  "(/(?P<year>\d{2,4}))?", sub, text)
    text = re.sub(r"(?P<year>\d{4})-(?P<month>\d{2})"
                  "-(?P<day>\d{2})", sub, text)

    def sub(match):
        groups = match.groupdict()
        try:
            idx = months.index(groups["month"])
        except ValueError:
            idx = months_abbr.index(groups["month"])
        date = ref.replace(day=int(groups["day_num"]),
                           month=idx + 1)
        l.append((date, match.span()))
        return "#" * (match.end() - match.start())

    text = re.sub(r"((?P<day>" + "|".join(days) + "|".join(days_abbr)
                  + "|".join(days_abbr2) + ") )?"
                  + r"(?P<month>" + "|".join(months)
                  + "|".join(months_abbr) + ")"
                  + r" (?P<day_num>\d{1,2})(st|rd|th|nd)?( \d{4})?",
                  sub, text)

    def sub(match):
        delta = timedelta((days.index(match.group("day")) - ref.weekday()) % 7)
        l.append((ref + delta, match.span()))
        return "#" * (match.end() - match.start())

    text = re.sub(r"(?P<day>" + "|".join(days) + ")", sub, text)

    def sub(match):
        delta = timedelta(1)
        l.append((ref + delta, match.span()))
        return "#" * (match.end() - match.start())

    text = re.sub(r"tomorrow", sub, text)

    l = [d for d in l if d[0] >= ref]

    if not l:
        l.append((ref, (0, 0)))

    return text, l


def create_time(hours, mins, hd):
    if not hd:
        if 8 <= hours <= 11:
            hd = "am"
        elif 1 <= hours < 8:
            hd = "pm"
        elif hours == 12:
            hd = "pm"
        elif hours > 12:
            hours -= 12
            hd = "pm"
    hours = hours + (hd == "pm" and hours < 12) * 12
    try:
        return time(hours, mins)
    except ValueError:
        return None


def parse_times(text):
    l = []

    def sub(match):
        groups = match.groupdict()
        groups["min"] = int(groups["min"]) if groups["min"] else 0
        t1 = create_time(int(groups["hour"]), groups["min"], groups["hd"])
        groups["min2"] = int(groups["min2"]) if groups["min2"] else 0
        t2 = create_time(int(groups["hour2"]), groups["min2"], groups["hd2"])
        if t1:
            l.append((t1, match.span()))
        if t2:
            l.append((t2, match.span()))
        return "#" * (match.end() - match.start())

    text = re.sub(r"\b(?P<hour>\d{1,2})(:(?P<min>\d{2}))? ?(?P<hd>pm|am)? ?"
                  "-{1,2} ?(?P<hour2>\d{1,2})(:(?P<min2>\d{2}))? ?"
                  "(?P<hd2>pm|am)?\b", sub, text)

    def sub(match):
        if not match.end() - match.start() >= 3:
            return text[match.start():match.end()]
        groups = match.groupdict()
        groups["min"] = int(groups["min"]) if groups["min"] else 0
        t = create_time(int(groups["hour"]), groups["min"], groups["hd"])
        if t:
            l.append((t, match.span()))
        return "#" * (match.end() - match.start() - 2)

    text = re.sub(r"\b(?P<hour>\d{1,2})(:(?P<min>\d{2}))?( ?(?P<hd>pm|am))?\b",
                  sub, text)
    return text, l


def align(dates, times):
    r = []
    matched = []

    def k(d):
        if t[1][1] < d[1][0]:
            return d[1][0] - t[1][1]
        else:
            return t[1][0] - d[1][1]

    for t in times:
        d = min(dates, key=k)
        matched.append(d)
        r.append((datetime.combine(d[0], t[0]), t[1]))

    unmatched = [d for d in dates if d not in matched]
    return r, unmatched


def parse_email(fp):
    mail = email.message_from_file(fp)
    values = parsedate(mail["date"])
    subject = mail["subject"]
    date = datetime(*values[:6]).date()
    text = clean(mail.get_payload())
    text, dates = parse_dates(text, date)
    text, times = parse_times(text)
    m, u = align(dates, times)
    m.sort(key=lambda d: d[1][0])
    if len(m) >= 2:
        return subject, m[0][0], m[1][0]
    elif len(m) == 1:
        return subject, m[0][0], m[0][0] + timedelta(hours=1)
    else:
        return subject, date, date + timedelta(hours=1)


def edit(subject, begin, end):
    d = {"Summary": subject, "Start": begin.isoformat(),
         "End": end.isoformat()}
    fd, fname = mkstemp()
    with open(fname, "w") as fo:
        fo.write("\n".join(": ".join(e) for e in d.iteritems()))
    editor = os.getenv("EDITOR") or "gvim"
    check_call([editor, "-f", fname])
    return fname


def gen_icalendar(file_name):
    d = {key.strip(): value.strip() for key, value in
         (line.split(": ", 1) for line in open(file_name))}
    cal = Calendar()
    event = Event()
    event.add("summary", d["Summary"])
    event.add("dtstart", datetime.strptime(d["Start"], "%Y-%m-%dT%H:%M:%S"))
    event.add("dtend", datetime.strptime(d["End"], "%Y-%m-%dT%H:%M:%S"))
    cal.add_component(event)
    open(file_name, "w").write(cal.to_ical())
    print file_name

if __name__ == "__main__":
    gen_icalendar(edit(*parse_email(sys.stdin)))
    a = raw_input()
