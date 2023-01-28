#!/usr/bin/env python3

import argparse
import datetime
import functools
import html
import json
import locale
import logging
import shutil
import sys
import zipfile
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, TextIO

from util import Group, GroupInfo, SomePath, SummaryData, User


def make_summary_data(
    search_path: SomePath,
    group_filter_strict: bool,
    group_filter: set[str],
    sender_filter: set[str],
) -> SummaryData:
    groups = list[Group]()
    usercounts = defaultdict[str, int](int)
    groups_path = search_path / "Groups"
    if not (groups_path.exists() and groups_path.is_dir()):
        raise Exception(
            f"Expected 'Groups' dir in {search_path}; found {list(search_path.iterdir())}"
        )

    for gd in groups_path.iterdir():
        info_path = gd / "group_info.json"
        if not (info_path.exists() and info_path.is_file()):
            raise Exception(
                f"Expected 'group_info.json' in {gd}; found {list(gd.iterdir())}"
            )
        with info_path.open("r", encoding="utf-8") as info_file:
            json_group: GroupInfo = json.load(info_file)

        group = Group(json_group, gd.name)

        # Apply group and sender filters to the group
        if group_filter:
            if not group_filter.intersection(group.members.keys()):
                continue
            if group_filter_strict and set(group.members.keys()).difference(
                group_filter
            ):
                continue
        if sender_filter:
            if not sender_filter.intersection(group.members.keys()):
                continue

        groups.append(group)

        # Scan messages
        msgs = group.load_messages(search_path)
        for msg in msgs:
            em = msg.creator.email.lower()

            # Apply sender filter here
            if sender_filter:
                if em not in sender_filter:
                    continue

            if em not in group.members:
                # This seems to happen ... maybe this person has left the group?
                group.members[em] = msg.creator
                group.usercounts[em] = 0
            group.usercounts[em] += 1
            group.count += 1
            usercounts[em] += 1

    return SummaryData(groups, usercounts)


def write_summary(data: SummaryData, outfile: TextIO) -> None:
    groups, usercounts = data

    print("Summary:", file=outfile)
    print("====== CHATS ======", file=outfile)
    for group in groups:
        print(
            f" - {group.name} ({', '.join(group.members.keys())})",
            file=outfile,
        )
        print(f"   {group.count} total messages", file=outfile)
        if group.first_msg_time:
            print(
                f"   from '{group.first_msg_time}' to '{group.last_msg_time}'",
                file=outfile,
            )
        for member in group.members.values():
            print(
                f"   - {member.email} ({member.name}): {group.usercounts[member.email.lower()]} messages",
                file=outfile,
            )
        print(file=outfile)

    print("====== USERS ======", file=outfile)
    for em in usercounts:
        print(f" - {em}: {usercounts[em]} total messages", file=outfile)


@contextmanager
def htmlfile(path: Path) -> Generator[TextIO, None, None]:
    f = path.open("w", encoding="utf-8")
    try:
        print("<!DOCTYPE html>", file=f)
        print('<html lang="en">', file=f)
        print("  <head>", file=f)
        print('    <meta charset="utf-8">', file=f)
        print('    <link rel="stylesheet" href="styles.css">', file=f)
        print("  </head>", file=f)
        print("  <body>", file=f)
        print(file=f)
        yield f
    finally:
        print(file=f)
        print("  </body>", file=f)
        print("</html>", file=f)
        f.close()


def username_html(u: User, g: Group) -> str:
    return (
        f'<span class="user{g.user_idxs.get(u.email, 0)%10}">'
        + html.escape(u.email)
        + "</span>"
    )


def write_html(
    search_path: SomePath,
    sender_filter: set[str],
    outpath: Path,
    summary: SummaryData,
) -> None:
    outpath.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__).parent / "styles.css", outpath)

    # First let's write each of the chats...
    for i in range(len(summary.groups)):
        group = summary.groups[i]
        # Load up all the messages for the group
        msgs = group.load_messages(search_path)

        with htmlfile(outpath / f"g{i}.html") as ghtml:
            gout = functools.partial(print, file=ghtml)

            gout(f'<h1 id="top">Chat: {html.escape(group.name)}</h1>')
            if group.first_msg_time:
                gout(
                    f"<p>From {html.escape(str(group.first_msg_time))} to {html.escape(str(group.last_msg_time))}"
                )
            gout("<h2>Members</h2>")

            # Print members list
            gout("<ul>")
            for m in group.members.values():
                gout("<li>")
                gout(username_html(m, group))
                gout(
                    f"({html.escape(m.name)}): {group.usercounts[m.email.lower()]} messages"
                )
            gout("</ul>")

            # Find all months present
            months = set((m.created_date.year, m.created_date.month) for m in msgs if m.created_date)
            gout('<h2>Month Index</h2>')
            gout('<p>')
            for month in months:
                gout(f'<a href="#{month[0]}-{month[1]}">')
                gout(f'{month[0]}-{month[1]}')
                gout('</a> ')


            # Print basic read-out of the chat
            # TODO: date links
            gout("<h1>Messages</h1>")
            prev_date: Optional[datetime.date] = None
            prev_month: Optional[tuple[int, int]] = None
            for msg in msgs:
                # Update date stuff
                if msg.created_date:
                    cur_date = msg.created_date.date()
                    cur_month = (cur_date.year, cur_date.month)
                    if not prev_date or cur_date != prev_date:
                        if not prev_month or cur_month != prev_month:
                            gout(f'<h3 id="{cur_month[0]}-{cur_month[1]}">')
                            gout('<a href="#top">&uarr;</a>')
                            gout(f'{cur_month[0]}-{cur_month[1]}')
                            gout('</h3>')
                        gout(f'<h4 id="{html.escape(str(cur_date), quote=True)}">')
                        gout(html.escape(str(cur_date)))
                        gout('</h4>')
                    prev_date = cur_date
                    prev_month = cur_month

                gout("<p>")
                gout(username_html(msg.creator, group))
                gout(": " + html.escape(msg.text))
                gout('<br>')
                gout('<span class="details">')
                if msg.created_date:
                    gout(html.escape(msg.created_date.isoformat()))
                if msg.has_annotations:
                    gout(' (message included images or other non-text data)')
                gout('</span>')


def get_search_path(in_path: Path) -> SomePath:
    search_path: SomePath
    if in_path.is_dir():
        logging.info("Found directory at %s", in_path)
        search_path = in_path
    elif zipfile.is_zipfile(in_path):
        logging.info("Found zipfile at %s", in_path)
        search_path = zipfile.Path(in_path)
    else:
        raise Exception(f"Not sure what to do with {in_path}")

    # Descend into outer levels of the directory structure
    if (in_path / "Takeout").exists():
        search_path = search_path / "Takeout"
    if (search_path / "Google Chat").exists():
        search_path = search_path / "Google Chat"

    return search_path


if __name__ == "__main__":
    # We read in dates in US-ian locale
    locale.setlocale(locale.LC_TIME, "en_US")

    argparser = argparse.ArgumentParser(
        prog="gchat_converter",
        description="Converts gchat messages to more readable formats",
    )
    argparser.add_argument(
        "--input", action="store", help="path to input", required=True
    )
    argparser.add_argument("--output", action="store", help="path to output")
    argparser.add_argument(
        "--format",
        action="store",
        help="output format",
        default="html",
        choices=["html", "summarize"],
    )
    argparser.add_argument(
        "--only-chats-with",
        help="If set, only includes messages in chats including these email addresses",
        action="store",
        nargs="*",
        default=[],
    )
    argparser.add_argument(
        "--chat-filter-exclusive", action="store_true", default=False
    )
    argparser.add_argument(
        "--only-senders",
        help="If set, only includes messages sent by these email addresses",
        action="store",
        nargs="*",
        default=[],
    )

    args = argparser.parse_args()

    search_path = get_search_path(Path(args.input))
    assert search_path

    logging.info("Searching %s", search_path)

    # Normalize group / sender filters
    group_filter = set(g.lower() for g in args.only_chats_with)
    sender_filter = set(s.lower() for s in args.only_senders)

    if args.format == "html":
        if not args.output:
            print("--output required for --format html", sys.stderr)
            sys.exit(1)
        outpath = Path(args.output)
        if outpath.exists():
            if outpath.is_dir() and not outpath.is_symlink():
                s = input(f"{outpath} exists, are you sure? (y or die)")
                if s.strip().lower() != "y":
                    sys.exit(1)
                shutil.rmtree(outpath)
            else:
                print(
                    f"{outpath} exists, not a directory; aborting.",
                    file=sys.stderr,
                )
                sys.exit(1)

        summary_data = make_summary_data(
            search_path, args.chat_filter_exclusive, group_filter, sender_filter
        )
        write_html(search_path, sender_filter, outpath, summary_data)

    elif args.format == "summarize":
        if args.output:
            outfile: TextIO = open(args.output, "w", encoding="utf-8")
        else:
            outfile = sys.stdout

        summary_data = make_summary_data(
            search_path, args.chat_filter_exclusive, group_filter, sender_filter
        )
        write_summary(summary_data, outfile)
