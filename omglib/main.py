import argparse
import collections
import configparser
import grp
import pwd
import os
import re
import sys
import zlib
import hashlib
from fnmatch import fnmatch
from datetime import datetime
from math import ceil
from omglib import cmd


argparser = argparse.ArgumentParser(
    description="The oh-my-git library"
)

argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

argsp = argsubparsers.add_parser(
    "init", help="Initialize a new, empty repository.")

argsp.add_argument("path",
                   metavar="directory",
                   nargs="?",
                   default=".",
                   help="Where to create the repository.")


argsp = argsubparsers.add_parser(
    "cat-file", help="Provide content of repository objects")

argsp.add_argument("type",
                   metavar="type",
                   choices=["blob", "commit", "tag", "tree"],
                   help="Specify the type")

argsp.add_argument("object",
                   metavar="object",
                   help="The object to display")


argsp = argsubparsers.add_parser(
    "hash-object",
    help="Compute object ID and optionally creates a blob from a file")

argsp.add_argument("-t",
                   metavar="type",
                   dest="type",
                   choices=["blob", "commit", "tag", "tree"],
                   default="blob",
                   help="Specify the type")

argsp.add_argument("-w",
                   dest="write",
                   action="store_true",
                   help="Actually write the object into the database")

argsp.add_argument("path",
                   help="Read object from <file>")


argsp = argsubparsers.add_parser(
    "log", help="Display history of a given commit.")

argsp.add_argument("commit",
                   default="HEAD",
                   nargs="?",
                   help="Commit to start at.")


argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")

argsp.add_argument("-r",
                   dest="recursive",
                   action="store_true",
                   help="Recurse into sub-trees")

argsp.add_argument("tree",
                   help="A tree-ish object")


argsp = argsubparsers.add_parser("checkout",
                    help="Checkout a commit inside of a directory")

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    if args.command == "add":
        pass
    elif args.command == "cat-file":
        cmd.cmd_cat_file(args)
    elif args.command == "check-ignore":
        pass
    elif args.command == "checkout":
        pass
    elif args.command == "commit":
        pass
    elif args.command == "hash-object":
        pass
    elif args.command == "init":
        cmd.cmd_init(args)
    elif args.command == "log":
        pass
    elif args.command == "ls-file":
        pass
    elif args.command == "ls-tree":
        cmd.cmd_ls_tree(args)
    elif args.command == "merge":
        pass
    elif args.command == "rebase":
        pass
    elif args.command == "rev-parse":
        pass
    elif args.command == "rm":
        pass
    elif args.command == "show-ref":
        pass
    elif args.command == "status":
        pass
    elif args.command == "tag":
        pass
    else:
        print("Unknown command: {}".format(args.command), file=sys.stderr)
