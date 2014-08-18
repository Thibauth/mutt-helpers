#! /usr/bin/python2
import sys
import email
import readline
from mailbox import Maildir
import os
from os.path import basename, join, expanduser
from ConfigParser import RawConfigParser, NoSectionError, NoOptionError

from notmuch import Database, Query

CONFIG_FILE = expanduser(os.getenv("NOTMUCH_CONFIG") or "~/.notmuch-config")
HIST_FILE = expanduser(os.getenv("MUTT_NM_HIST") or "~/.mutt-notmuch-history")


def make_query(query):
    parser = RawConfigParser()
    parser.read(CONFIG_FILE)
    try:
        tags = parser.get("search", "exclude_tags").split(";")
    except (NoSectionError, NoOptionError):
        tags = []
    q = Database().create_query(query)
    map(q.exclude_tag, tags)
    return q


def search(query):
    q = make_query(query)
    q.set_sort(Query.SORT.NEWEST_FIRST)
    for message in q.search_messages():
        yield message.get_filename()


def thread(id):
    q = make_query("id:" + id)
    for message in q.search_messages():
        q2 = make_query("thread:" + message.get_thread_id())
        for m in q2.search_messages():
            yield m.get_filename()


def process(gen, output):
    box = Maildir(output)
    box.clear()
    for filename in gen:
        os.symlink(filename, join(box._path, "cur", basename(filename)))


def main():
    output = sys.argv[1]
    if sys.argv[2] == "search":
        try:
            readline.read_history_file(HIST_FILE)
        except IOError:
            open(HIST_FILE, "a").close()
        query = raw_input("Query: ")
        readline.write_history_file(HIST_FILE)
        process(search(query), output)
    elif sys.argv[2] == "thread":
        message = email.message_from_file(sys.stdin)
        process(thread(message["message-id"][1:-1]), output)


if __name__ == "__main__":
    main()
