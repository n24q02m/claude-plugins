"""Private advisory file-locking primitive shared by Agent Chat stores."""

from __future__ import annotations

import errno
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path


class AdvisoryLockTimeout(TimeoutError):
    pass


@dataclass
class AdvisoryFileLock:
    path: Path
    fd: int
    released: bool = False

    def release(self) -> None:
        if self.released:
            return
        try:
            try:
                os.lseek(self.fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self.fd, fcntl.LOCK_UN)
            except OSError:
                pass
        finally:
            self.released = True
            try:
                os.close(self.fd)
            except OSError:
                pass


def acquire_advisory_file_lock(
    path: Path, *, timeout: float
) -> AdvisoryFileLock:
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "advisory lock is not a regular file")
        if os.name == "nt" and os.fstat(fd).st_size == 0:
            os.write(fd, b"\0")
        started = time.monotonic()
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return AdvisoryFileLock(path=path, fd=fd)
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise
                if time.monotonic() - started > timeout:
                    raise AdvisoryLockTimeout(str(path)) from error
                time.sleep(0.01)
    except BaseException:
        os.close(fd)
        raise
