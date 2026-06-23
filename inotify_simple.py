#!/usr/bin/env python3
"""
inotify_simple.py — Minimal inotify wrapper via ctypes (zero dependencies)
替代pyinotify, 兼容Python 3.12+ (asyncore已移除)

系统调用: inotify_init1, inotify_add_watch, inotify_rm_watch, read
常量: IN_ACCESS, IN_MODIFY, IN_CREATE, IN_DELETE, IN_MOVED_FROM, IN_MOVED_TO
"""

import ctypes
import ctypes.util
import os
import struct

# ═══ 常量 ═══
IN_ACCESS = 0x00000001
IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CLOSE_WRITE = 0x00000008
IN_CLOSE_NOWRITE = 0x00000010
IN_OPEN = 0x00000020
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_DELETE_SELF = 0x00000400
IN_MOVE_SELF = 0x00000800

IN_CLOSE = IN_CLOSE_WRITE | IN_CLOSE_NOWRITE
IN_MOVE = IN_MOVED_FROM | IN_MOVED_TO

IN_ONLYDIR = 0x01000000
IN_DONT_FOLLOW = 0x02000000
IN_EXCL_UNLINK = 0x04000000
IN_MASK_ADD = 0x20000000
IN_ISDIR = 0x40000000
IN_ONESHOT = 0x80000000

IN_NONBLOCK = 0x00000800  # O_NONBLOCK

# 事件结构体 (从inotify.h)
# struct inotify_event {
#     int      wd;           /* watch descriptor */
#     uint32_t mask;         /* mask of events */
#     uint32_t cookie;       /* unique cookie for related events */
#     uint32_t len;          /* size of name field */
#     char     name[];       /* optional null-terminated name */
# };
EVENT_SIZE = 16  # sizeof(struct inotify_event) without name

# 加载libc
_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

_inotify_init1 = _libc.inotify_init1
_inotify_init1.argtypes = [ctypes.c_int]
_inotify_init1.restype = ctypes.c_int

_inotify_add_watch = _libc.inotify_add_watch
_inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
_inotify_add_watch.restype = ctypes.c_int

_inotify_rm_watch = _libc.inotify_rm_watch
_inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
_inotify_rm_watch.restype = ctypes.c_int


class InotifyEvent:
    """一个inotify事件"""
    __slots__ = ('wd', 'mask', 'cookie', 'name')
    def __init__(self, wd, mask, cookie, name):
        self.wd = wd
        self.mask = mask
        self.cookie = cookie
        self.name = name

    def __repr__(self):
        return f"InotifyEvent(wd={self.wd}, mask={self.mask:#x}, name='{self.name}')"


class Inotify:
    """inotify实例"""
    def __init__(self, nonblocking=False):
        flags = IN_NONBLOCK if nonblocking else 0
        self._fd = _inotify_init1(flags)
        if self._fd < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"inotify_init1 failed: {os.strerror(errno)}")
        self._watches = {}  # path -> wd
        self._wd_to_path = {}  # wd -> path

    def add_watch(self, path, mask):
        """添加监控路径, 返回watch descriptor"""
        path_bytes = os.fsencode(str(path))
        wd = _inotify_add_watch(self._fd, path_bytes, mask)
        if wd < 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"inotify_add_watch('{path}') failed: {os.strerror(errno)}")
        self._watches[str(path)] = wd
        self._wd_to_path[wd] = str(path)
        return wd

    def add_watch_recursive(self, path, mask):
        """递归添加监控路径及其子目录"""
        path = str(path)
        wds = []
        for root, dirs, files in os.walk(path):
            try:
                wd = self.add_watch(root, mask)
                wds.append(wd)
            except OSError:
                pass
        return wds

    def rm_watch(self, wd):
        """移除监控"""
        _inotify_rm_watch(self._fd, wd)
        # 清理映射
        for p, w in list(self._watches.items()):
            if w == wd:
                del self._watches[p]
        self._wd_to_path.pop(wd, None)

    def read(self, timeout_ms=None):
        """读取事件, 返回 InotifyEvent 列表

        如果 nonblocking=True, 立刻返回(可能为空)
        如果 timeout_ms 设置, 阻塞最多timeout_ms毫秒
        """
        if timeout_ms is not None and timeout_ms > 0:
            # 用select做超时
            import select
            r, _, _ = select.select([self._fd], [], [], timeout_ms / 1000)
            if not r:
                return []

        buf_size = 4096
        raw = os.read(self._fd, buf_size)
        if not raw:
            return []

        events = []
        offset = 0
        while offset < len(raw):
            # 解析固定头: wd(4) mask(4) cookie(4) len(4) = 16 bytes
            hdr = raw[offset:offset + EVENT_SIZE]
            wd, mask, cookie, name_len = struct.unpack("iIII", hdr)
            offset += EVENT_SIZE
            # 读取name
            name = b""
            if name_len > 0:
                name = raw[offset:offset + name_len].rstrip(b'\x00')
                offset += name_len
            events.append(InotifyEvent(wd, mask, cookie, os.fsdecode(name) if name else ""))
            # 对齐到4字节边界
            while offset % 4:
                offset += 1

        return events

    def close(self):
        """关闭inotify fd"""
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1

    def fileno(self):
        return self._fd

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
