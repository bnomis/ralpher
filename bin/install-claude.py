#!/usr/bin/env python
"""
install-claude: symlinks files in to ~/.claude/
"""

import argparse

# auditme: accept[stdlib-logging] runs under the system Python before the project environment, and loguru, exist
import logging
import pathlib
import sys
from typing import NoReturn


def symlink_file(options, src: pathlib.Path, dst: pathlib.Path) -> None:
    """link a file from source to target, renaming existing file if necessary"""
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink():
            dst.unlink()
        else:
            existing = dst
            rn = existing.with_suffix(dst.suffix + '.orig')
            i = 2
            while rn.exists():
                rn = rn.with_name(rn.stem + f'.{i}' + rn.suffix)
                i += 1
            existing.rename(rn)

    dst_parent = dst.parent
    src_parent = src.parent
    relative_parent = src_parent.relative_to(dst_parent, walk_up=True)
    print(f'Linking {src} to {dst} via {relative_parent / src.name}')
    dst.symlink_to(relative_parent / src.name)


def symlink_dir(options, src: pathlib.Path, dst: pathlib.Path) -> None:
    """links files in a directory from src to dst"""
    print(f'Linking directory {src} to {dst}')
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        srcf = f
        dstf = dst / f.name
        symlink_file(options, srcf, dstf)


def this_dir() -> pathlib.Path:
    """returns the directory of this script"""
    return pathlib.Path(__file__).parent.resolve()


def src_claude_dir() -> pathlib.Path:
    """returns the directory of the claude files"""
    return this_dir().parent / 'claude'


def dest_claude_dir() -> pathlib.Path:
    """returns the directory of the claude files"""
    return pathlib.Path.home() / '.claude'


def find_dangling_symlinks(options, dir: pathlib.Path, max_depth: int = 2) -> None:
    root_depth = len(dir.parts)
    dangle = []
    for dirpath, dirnames, filenames in dir.walk(top_down=True):
        depth = len(dirpath.parts) - root_depth
        if depth >= max_depth - 1:
            dirnames.clear()

        for f in filenames:
            p = pathlib.Path(dirpath) / f
            if p.is_symlink() and not p.exists():
                dangle.append(p)

    if dangle:
        print('Dangling symlinks found:')
        for p in dangle:
            print(f'  {p}')
        print('Remove with:')
        print(f'rm {" ".join(str(p) for p in dangle)}')


def install_claude(options) -> None:
    """link files from source to target"""
    fdir = src_claude_dir()
    tdir = dest_claude_dir()

    for f in fdir.iterdir():
        if f.name[0] == '.':
            continue

        src = f
        dest = tdir / f.name
        if src.is_dir():
            symlink_dir(options, src, dest)
        else:
            symlink_file(options, src, dest)

    find_dangling_symlinks(options, tdir)


def parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='install-claude',
        description='symlinks files into ~/.claude',
    )
    return parser.parse_args(argv)


def main(argv) -> NoReturn:
    options = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG)
    options.logger = logging.getLogger('install-claude')
    m = 0
    try:
        install_claude(options)
    except Exception as e:
        # auditme: accept[except-interpolation] the message is the exit message, which shows no traceback
        m = f'Exception: {e}'
        options.logger.exception(m)
    sys.exit(m)


if __name__ == '__main__':
    main(sys.argv[1:])
