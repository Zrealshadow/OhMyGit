

import configparser
import os
from typing import Optional


class GitRepository(object):
    """A git repository"""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("Not a Git repository {}".format(path))

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0 and not force:
                raise Exception(
                    "Unsupported repositoryformatversion {}".format(vers)
                )


def repo_path(repo: GitRepository, *path: str) -> str:
    """Compute path under repo's gitdir"""
    return os.path.join(repo.gitdir, *path)


def repo_file(repo: GitRepository, *path: str, mkdir: bool = False) -> Optional[str]:
    """Same as repo_path, but create dirname(*path) if absent. For
    example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
    .git/refs/remotes/origin."""

    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(repo: GitRepository, *path: str, mkdir: bool = False) -> Optional[str]:
    """Same as repo_path, but mkdir *path if absent if mkdir."""
    path = repo_path(repo, *path)

    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception("Not a directory {}".format(path))

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_create(path: str) -> GitRepository:
    """Create a new repository at path."""

    # force = True, create a new repository or reset a exist reporitory
    repo = GitRepository(path, True)

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception("{} is not a directory!".format(path))
        if os.listdir(repo.worktree):
            raise Exception("{} is not empty!".format(path))
    else:
        os.makedirs(repo.worktree)

    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    # .git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write(
            "Unnamed repository; edit this file 'description' to name the repository.\n")

    # .git/HEAD

    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo


def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    # the versionn of the gitdir format.
    # 0 means the initial format, 1 the same with extensions.
    # currently, only 0 is supported.

    ret.set("core", "filemode", "false")
    # disable tracking of file mode changes

    ret.set("core", "bare", "false")
    # indicates this repository has a worktree.
    # Git support optional worktree key which inndicates the location of worktree.
    # currently it is not supported.

    return ret


# find the git repository directory recursively
# from the current directory to the root of the filesystem
def repo_find(path: str = ".", required=True):
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    parent = os.path.realpath(os.path.join(path, ".."))

    if parent == path:
        # we are at the root of the filesystem
        if required:
            raise Exception("No git directory.")
        else:
            return None

    return repo_find(parent, required)
