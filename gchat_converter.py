#!/usr/bin/env python3

import argparse
import json
import locale
import logging
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import TextIO

from util import Group, GroupInfo, Message, MessageFile, SomePath, SummaryData


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
        with info_path.open("r") as info_file:
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
        msgs_path = gd / "messages.json"
        if msgs_path.exists() and msgs_path.is_file():
            with msgs_path.open("r") as msgs_file:
                msg_file: MessageFile = json.load(msgs_file)

            msgs = [Message(m) for m in msg_file["messages"]]

            if msgs:
                group.first_msg_time = msgs[0].created_date
                group.last_msg_time = msgs[-1].created_date

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
        raise Exception("not yet implemented")
    elif args.format == "summarize":
        if args.output:
            outfile: TextIO = open(args.output, "w")
        else:
            outfile = sys.stdout

        summary_data = make_summary_data(
            search_path, args.chat_filter_exclusive, group_filter, sender_filter
        )
        write_summary(summary_data, outfile)
