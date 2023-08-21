import argparse
import os
import sys
from typing import Set
from omglib.repo import GitRepository, repo_find, repo_create
from omglib.obj import GitCommit, GitTree, GitTreeLeaf, object_find, object_hash, object_read


def cmd_init(args: argparse.Namespace) -> None:
    repo_create(args.path)


def cmd_cat_file(args: argparse.Namespace) -> None:
    repo = repo_find()
    sha = object_find(repo, args.object, args.type)
    obj = object_read(repo, sha)
    sys.stdout.buffer.write(obj.serialize())


def cmd_hash_object(args: argparse.Namespace) -> None:
    if args.write:
        repo = repo_find()
    else:
        repo = None

    with open(args.path, "rb") as f:
        sha = object_hash(f.read(), args.type, repo)
        print(sha)


def cmd_log(args: argparse.Namespace) -> None:
    repo = repo_find()

    print("digraph omglog{")
    print(" node[shape=rect]")
    log_graphviz(repo, object_find(repo, args.commit, "commit"), set())
    print("}")


# recursive function
def log_graphviz(repo: GitRepository, sha: str, seen: Set[str]) -> None:
    if sha in seen:
        return

    seen.add(sha)

    commit: GitCommit = object_read(repo, sha)
    short_hash = sha[0:8]
    message = commit.kvlm[None].decode(
        "utf-8").strip().replace("\\", "\\\\").replace("\"", "\\\"")

    if "\n" in message:
        # only show the first line
        message = message[:message.index("\n")]

    print(" c_{0} [label=\"{1} : {2}\"]".format(sha, short_hash, message))
    assert commit.fmt == b'commit'

    if not b'parent' in commit.kvlm.keys():
        # init commit
        return

    # sha
    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print(" c_{0} -> c_{1}".format(sha, p))
        # process the parent
        log_graphviz(repo, p, seen)


def cmd_ls_tree(args: argparse.Namespace) -> None:
    repo = repo_find()
    ls_tree(repo, args.tree, args.recursive)


def ls_tree(repo: GitRepository, ref: str, recursive: bool = False, prefix: str = "") -> None:
    sha = object_find(repo, ref, "tree")
    obj: GitTree = object_read(repo, sha)

    for item in obj.items:
        if len(item.mode) == 5:
            tp = item.mode[0:1]
        else:
            tp = item.mode[0:2]

        if tp == b'04':
            # directory
            tp = "tree"
        elif tp == b'10':
            # a regular file
            tp = "blob"
        elif tp == b'12':
            # a symlink, blob contents is link target.
            tp = "blob"
        elif tp == b'16':
            # a sub module
            tp = "commit"
        else:
            raise Exception("Unknown type {}".format(tp))

        if not (recursive and type == 'tree'):
            # a leaf node
            print("{0}{1} {2} {3}\t{4}".format(
                "0" * (6 - len(item.mode)) + item.mode.decode("utf-8"),
                tp, item.sha, os.path.join(prefix, item.path.decode("utf-8"))
            ))
        else:
            ls_tree(repo, item.sha, recursive, os.path.join(
                prefix, item.path.decode("utf-8")))


def cmd_checkout(args:argparse.Namespace)->None:
    repo = repo_find()

    obj = object_read(repo, object_find(repo, args.commit))

    if obj.fmt == b'commit':
        obj = object_read(repo, obj.kvlm[b'tree'].decode("utf-8"))
    

    if os.patj.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception(f"Not a directory {args.path}")
        if os.listdir(args.path):
            raise Exception(f"Not Empty {args.path}")
    else:
        # create a new empty directory 
        os.mkdirdirs(args.path)

    tree_checkout(repo, obj, args.path)


def tree_checkout(repo:GitRepository, tree:GitTree, path:str)->None:
    for item in tree.items:
        obj = object_read(item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            with open(dest, 'wb', encoding='utf-8') as f:
                f.write(obj.blobdata)
            
