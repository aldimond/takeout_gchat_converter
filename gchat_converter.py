#!/usr/bin/env python3

import argparse
import json
import os
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import TypedDict


def summarize(search_path, outfile, group_filter, sender_filter):
    groups = list()
    usercounts = defaultdict(int)
    groups_path = search_path / "Groups"
    if not (groups_path.exists() and groups_path.is_dir()):
        raise Exception(f"Expected 'Groups' dir in {search_path}; found {list(search_path.iterdir())}")
    
    for gd in groups_path.iterdir():
        info_path = gd / "group_info.json"
        if not (info_path.exists() and info_path.is_file()):
            raise Exception(f"Expected 'group_info.json' in {gd}; found {list(gd.iterdir())}")
        with info_path.open("r") as info_file:
            group = json.load(info_file)

        # Add overall count
        group["count"] = 0

        # Convert members to an email-keyed dict with a count
        group["members"] = {m["email"].lower(): m for m in group["members"]}
        for member in group["members"].values():
            member["count"] = 0

        # Apply group and sender filters to the group
        if group_filter:
            if not group_filter.intersection(group["members"].keys()):
                continue
        if sender_filter:
            if not sender_filter.intersection(group["members"].keys()):
                continue

        groups.append(group)

        # Scan messages
        msgs_path = gd / "messages.json"
        if msgs_path.exists() and msgs_path.is_file():
            with msgs_path.open("r") as msgs_file:
                msgs = json.load(msgs_file)

            if msgs.get("messages"):
                group["first"] = msgs["messages"][0]["created_date"]
                group["last"] = msgs["messages"][-1]["created_date"]

            for msg in msgs["messages"]:
                em = msg["creator"]["email"].lower()

                # Apply sender filter here
                if sender_filter:
                    if em not in sender_filter:
                        continue

                if em not in group["members"]:
                    # This seems to happen ... maybe this person has left the group?
                    group["members"][em] = msg["creator"]
                    group["members"][em]["count"] = 0
                group["members"][em]["count"] += 1
                group["count"] += 1
                usercounts[em] += 1

    # Write summary
    print(f"Summary of {search_path}:", file=outfile)
    print("====== CHATS ======", file=outfile)
    for group in groups:
        print(f" - {group.get('name', 'DM')} ({', '.join(group['members'].keys())})", file=outfile)
        print(f"   {group['count']} total messages", file=outfile)
        if "first" in group:
            print(f"   from '{group['first']}' to '{group['last']}'", file=outfile)
        for member in group["members"].values():
            print(f"   - {member['email']} ({member['name']}): {member['count']} messages", file=outfile)
        print(file=outfile)

    print("====== USERS ======", file=outfile)
    for em in usercounts:
        print(f" - {em}: {usercounts[em]} total messages")




if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
            prog = "gchat_converter",
            description = "Converts gchat messages to more readable formats"
    )
    argparser.add_argument("--input", action="store", help="path to input", required=True)
    argparser.add_argument("--output", action="store", help="path to output")
    argparser.add_argument("--format", action="store", help="output format", default="html", choices=["html", "summarize"])
    argparser.add_argument("--only-chats-with", help="If set, only includes messages in chats including these email addresses", action="store", nargs="*", default=[])
    argparser.add_argument("--only-senders", help="If set, only includes messages sent by these email addresses", action="store", nargs="*", default=[])

    args = argparser.parse_args()

    in_path = Path(args.input)
    search_path = None

    if in_path.is_dir():
        print(f"Found directory at {in_path}")
        search_path = in_path

    elif zipfile.is_zipfile(in_path):
        print(f"Found zipfile at {in_path}")
        search_path = zipfile.Path(in_path)
    else:
        raise Exception(f"Not sure what to do with {in_path}")

    # Descend into outer levels of the directory structure
    if (in_path / "Takeout").exists():
        search_path = search_path / "Takeout"
    if (search_path / "Google Chat").exists():
        search_path = search_path / "Google Chat"

    # Normalize group / sender filters
    group_filter = set(g.lower() for g in args.only_chats_with)
    sender_filter = set(s.lower() for s in args.only_senders)

    if args.format == "html":
        raise Exception("not yet implemented")
    elif args.format == "summarize":
        if args.output:
            outfile = open(args.output, "w")
        else:
            outfile = sys.stdout

        summarize(search_path, outfile, group_filter, sender_filter)
