

import collections
import hashlib
import os
from typing import Dict, List, Optional
import zlib
from omglib.repo import GitRepository, repo_file


class GitObject(object):

    def __init__(self, data: bytes = None) -> None:
        if data is not None:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self, repo: GitRepository):
        """ This function MUST be implemented by subclasses.
        It must read the object's contents from self.data, a byte string, and do
        whatever it takes to convert it into a meaningful representation. 
        What exactly that means depend on each subclass.
        """
        raise NotImplementedError()

    def deserialize(self, data: bytes):
        raise NotImplementedError()

    def init(self):
        pass


def object_read(repo: GitRepository, sha: str):
    """Read object object_id from Git repository repo. Return a GitObject whose
    exact type depends on the object."""

    # path to e673d1b7eaa0aa01b5bc2442d570a765bdaae751
    # -> .git/objects/e6/73d1b7eaa0aa01b5bc2442d570a765bdaae751

    path = repo_file(repo, "objects", sha[0:2], sha[2:])
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type  b' ' -> 0x20
        x = raw.find(b' ')
        fmt = raw[0:x]

        # Read and validate object size， 0x00 -> b'\x00', null
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))

        if size != len(raw)-y-1:
            raise Exception("Malformed object {0}: bad length".format(sha))

        # Pick constructor
        if fmt == b'commit':
            c = GitCommit
        elif fmt == b'tree':
            c = GitTree
        elif fmt == b'tag':
            c = GitTag
        elif fmt == b'blob':
            c = GitBlob
        else:
            raise Exception("Unknown type {} for object {}".format(
                fmt.decode("ascii"), sha))

        # Call constructor and return object
        return c(raw[y+1:])


def object_find(repo: GitRepository, name: str, fmt: str = None, follow: bool = True) -> str:
    return name


def object_write(obj: GitObject, repo: GitRepository = None):
    # serialize object data
    data = obj.serialize()
    # add header and following format
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    # compute hash
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        # Compute path and create file
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir=True)

        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(zlib.compress(result))

    return sha


def object_hash(data: bytes, fmt: str, repo: GitRepository = None):
    """Compute hash of object data read from fd"""
    if fmt == b'commit':
        obj = GitCommit(data)
    elif fmt == b'tree':
        obj = GitTree(data)
    elif fmt == b'tag':
        obj = GitTag(data)
    elif fmt == b'blob':
        obj = GitBlob(data)
    else:
        raise Exception("Unknown type {}".format(fmt))

    return object_write(obj, repo)

# GitObject subclasses, just show the raw binary file


class GitBlob(GitObject):
    fmt = b'blob'

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


class GitCommit(GitObject):
    fmt = b'commit'

    def deserialize(self, data: bytes):
        self.kvlm = kvlm_parse(data)

    def serialize(self, repo: GitRepository):
        return kvlm_serialize(self.kvlm)

    def init(self):
        self.kvlm = collections.OrderedDict()


class GitTree(GitObject):
    fmt = b'tree'

    def deserialize(self, data: bytes):
        self.items:List[GitTreeLeaf] = tree_parse(data)

    def serialize(self, repo: GitRepository):
        return tree_serialize(self)

    def init(self):
        self.items:List[GitTreeLeaf] = []


class GitTag(GitObject):
    fmt = b'tag'


# Key-Value List with Message Parser
# this function is recursive; it reads a key/value pair, and then calls itself
# to read the next pair in a new postion, until it reaches the end of the message.
# Thus frist need to know where we are: at a keyword, or already in the messageQ.
def kvlm_parse(raw: bytes, start: int = 0, dct: Optional[dict] = None):

    if not dct:
        dct = collections.OrderedDict()

    # Find the next space or newline
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # if space appears before newline, have a keywords.
    # otherwise, it's the final message, just read to end of the file

    # Base case
    # ==========
    # we consider two cases:
    # 1. spc < 0, there's no space at all, in which find return -1.
    # 2. newline appears before space, means a blank line.
    # a blankline means the remainder of the data is the message, store it in the dict.
    # None as the key of message, and return.
    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = raw[start+1:]
        return dct

    # recursive case
    # ============
    key = raw[start:spc]

    # find the end of the value. '\n'+space will replace '\n' in value message
    # Continuation line begin with a space.
    # can loops until finding a "\n" not followed by a space
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '):
            break

    value = raw[spc + 1:end].replace(b'\n ', b'\n')

    if key in dct:
        if (type(dct[key]) is list):
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value

    return kvlm_parse(raw, start=end+1, dct=dct)


# Key-Value List with Message Serializer
def kvlm_serialize(kvlm: Dict):
    ret = b''

    # output fields
    for k in kvlm.keys():
        if k == None:
            continue
        val = kvlm[k]
        # Normalize to a list
        if type(val) != list:
            val = [val]

        for v in val:
            ret += k + b' ' + v.replace(b'\n', b'\n ') + b'\n'

    # add message
    ret += b'\n' + kvlm[None] + b'\n'
    return ret


class GitTreeLeaf(object):

    def __init__(self, mode: str, path: str, sha: str):
        self.mode = mode
        self.path = path
        self.sha = sha

    def serialize(self) -> bytes:
        return self.mode.encode('utf-8') + b' ' + self.path.encode('utf-8') + b'\x00' + bytes.fromhex(self.sha)

# mode + ' ' + path + '\x00' + sha


def tree_parse_one(raw: bytes, start: int = 0):

    # Find the space terminator of the mode
    x = raw.find(b' ', start)
    assert x - start == 5 or x - start == 6

    mode = raw[start:x]
    if len(mode) == 5:
        mode = b" " + mode

    # Find the null terminator of the path
    y = raw.find(b'\x00', x)
    path = raw[x + 1: y]

    sha = format(int.from_bytes(raw[y + 1: y + 21], 'big'), "040x")
    return y + 21, GitTreeLeaf(mode, path, sha)


def tree_parse(raw: bytes):
    pos = 0
    tree = []

    while pos < len(raw):
        pos, leaf = tree_parse_one(raw, pos)
        tree.append(leaf)

    return tree


def tree_leaf_sort_key(leaf: GitTreeLeaf):
    if leaf.mode.startswith(b"10"):
        # file type
        return leaf.path
    else:
        # directory type
        return leaf.path + "/"


def tree_serialize(obj: GitTree):
    # Sort tree entries by name
    obj.items.sort(key=tree_leaf_sort_key)

    # Recursively serialize tree entries
    return b''.join([x.serialize() for x in obj.items])
