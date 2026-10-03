import os


class InstanceLock:
    """One running process for one data directory, even with another port."""

    def __init__(self, path):
        self.path = path
        self.handle = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.path, 'a+b')
        if f.seek(0, 2) == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            raise RuntimeError('此项目的工作台已在运行，请使用已有窗口。')
        self.handle = f

    def release(self):
        if self.handle:
            self.handle.close()
            self.handle = None
