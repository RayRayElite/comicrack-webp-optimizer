# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""CPython performance primitives: measured process resources and bounded cache.

No ComicRack objects or replacement operations belong here. I/O counters are
logical process activity, not physical disk/NAS traffic. Working sets include
shared pages, so their sampled sum is explicitly an estimate.
"""
import ctypes
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid

WORKERS = (1, 2, 4, 6, 8, 10, 12)
TRACKER = None


class _IO(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in ('ro', 'wo', 'oo', 'read', 'write', 'other')]


class _MEM(ctypes.Structure):
    _fields_ = [('cb', w.DWORD), ('faults', w.DWORD)] + [(name, ctypes.c_size_t) for name in ('peak', 'working', 'poolpeak', 'pool', 'nonpeak', 'non', 'pagefile', 'pagepeak', 'private')]


class ResourceTracker:
    """Sample only this helper and explicitly registered children; no PID search."""
    def __init__(self):
        self.enabled = os.name == 'nt'
        self.lock = threading.RLock()
        self.handles = {}
        self.retired = [0., 0., 0.]
        self.stop = threading.Event()
        self.peak_ram = self.peak_commit = self.peak_cpu = 0.
        self.started = self.last_time = time.perf_counter()
        self.last_cpu = 0.
        if self.enabled:
            self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
            self.kernel.OpenProcess.restype = w.HANDLE
            self.kernel.CloseHandle.argtypes = [w.HANDLE]
            self.kernel.GetProcessTimes.argtypes = [w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4
            self.kernel.GetProcessIoCounters.argtypes = [w.HANDLE, ctypes.POINTER(_IO)]
            self.psapi = ctypes.WinDLL('psapi', use_last_error=True)
            self.psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(_MEM), w.DWORD]
            self.add(os.getpid())
            self.baseline = self._totals()[0:3]
            self.last_cpu = self.baseline[0]
            self.thread = threading.Thread(target=self._sample_loop, daemon=True)
            self.thread.start()

    def _read(self, handle):
        times = [w.FILETIME() for _ in range(4)]
        io, mem = _IO(), _MEM()
        mem.cb = ctypes.sizeof(mem)
        self.kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times))
        self.kernel.GetProcessIoCounters(handle, ctypes.byref(io))
        self.psapi.GetProcessMemoryInfo(handle, ctypes.byref(mem), mem.cb)
        cpu = sum((t.dwHighDateTime << 32) + t.dwLowDateTime for t in times[2:]) / 1e7
        return cpu, io.read, io.write, mem.working, mem.private

    def add(self, pid):
        if self.enabled:
            with self.lock:
                handle = self.kernel.OpenProcess(0x0410, False, pid)
                if handle:
                    self.handles[pid] = handle

    def retire(self, pid):
        if self.enabled:
            with self.lock:
                handle = self.handles.pop(pid, None)
                if handle:
                    values = self._read(handle)
                    self.retired = [a + b for a, b in zip(self.retired, values[:3])]
                    self.kernel.CloseHandle(handle)

    def _totals(self):
        values = [self._read(handle) for handle in self.handles.values()]
        return [sum(row[i] for row in values) + (self.retired[i] if i < 3 else 0) for i in range(5)]

    def _sample_loop(self):
        while not self.stop.wait(.25):
            self.sample()

    def sample(self):
        with self.lock:
            totals, now = self._totals(), time.perf_counter()
            cpu = max(0, totals[0] - self.last_cpu) / max(.001, now - self.last_time) / (os.cpu_count() or 1) * 100
            self.peak_cpu = max(self.peak_cpu, cpu)
            self.peak_ram, self.peak_commit = max(self.peak_ram, totals[3]), max(self.peak_commit, totals[4])
            self.last_cpu, self.last_time = totals[0], now

    def finish(self):
        if not self.enabled:
            return {'RESOURCE_NOTE': 'Process measurements unavailable on this platform'}
        self.stop.set()
        self.thread.join()
        self.sample()
        with self.lock:
            totals = self._totals()
            duration = max(.001, time.perf_counter() - self.started)
            values = dict(RESOURCE_CPU_AVG_PERCENT=max(0, totals[0] - self.baseline[0]) / duration / (os.cpu_count() or 1) * 100,
                          RESOURCE_CPU_PEAK_PERCENT=self.peak_cpu, RESOURCE_RAM_PEAK_MB=self.peak_ram / 1048576,
                          RESOURCE_COMMIT_PEAK_MB=self.peak_commit / 1048576,
                          RESOURCE_READ_MBPS=max(0, totals[1] - self.baseline[1]) / 1048576 / duration,
                          RESOURCE_WRITE_MBPS=max(0, totals[2] - self.baseline[2]) / 1048576 / duration)
            for handle in self.handles.values():
                self.kernel.CloseHandle(handle)
            self.handles.clear()
        return {key: '%.3f' % value for key, value in values.items()}


def run_tool(*args, **kwargs):
    """subprocess.run contract with child lifetime accounting, including short jobs."""
    if TRACKER is None:
        return subprocess.run(*args, **kwargs)
    capture, timeout, check, data = kwargs.pop('capture_output', False), kwargs.pop('timeout', None), kwargs.pop('check', False), kwargs.pop('input', None)
    if capture:
        kwargs['stdout'] = kwargs['stderr'] = subprocess.PIPE
    if data is not None:
        kwargs['stdin'] = subprocess.PIPE
    with subprocess.Popen(*args, **kwargs) as process:
        TRACKER.add(process.pid)
        try:
            try:
                output, error = process.communicate(data, timeout=timeout)
            except BaseException:
                process.kill()
                process.communicate()
                raise
        finally:
            TRACKER.retire(process.pid)
        if check and process.returncode:
            raise subprocess.CalledProcessError(process.returncode, process.args, output, error)
        return subprocess.CompletedProcess(process.args, process.returncode, output, error)


def set_priority(profile):
    if os.name == 'nt' and profile == 'Background':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = w.HANDLE
        kernel.SetPriorityClass.argtypes = [w.HANDLE, w.DWORD]
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000):
            raise OSError('Could not enable below-normal background priority')


def local_storage(path):
    """Mapped SMB drives also count as remote, even without a UNC spelling."""
    if os.name != 'nt':
        return True
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDriveTypeW.argtypes = [w.LPCWSTR]
    return kernel.GetDriveTypeW(str(Path(path).resolve().anchor)) == 3


def signature(path):
    info = os.stat(path)
    return [info.st_size, info.st_mtime_ns]


def file_hash(path):
    result = hashlib.sha256()
    with open(path, 'rb') as incoming:
        for block in iter(lambda: incoming.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def cleanup_cache(record, work_root):
    """Delete exactly a generated cache's known files; reject redirects/unknowns."""
    folder = _cache_folder(record, work_root)
    if not folder.exists():
        return
    for path in folder.iterdir():
        if path.name not in ('archive.bin', 'manifest.json') or not path.is_file() or _redirected(path):
            raise RuntimeError('Unexpected prefetch cache content')
    for path in folder.iterdir():
        path.unlink()
    folder.rmdir()


def _redirected(path):
    info = os.lstat(path)
    return Path(path).is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _cache_folder(record, work_root):
    record = Path(os.path.abspath(record))
    folder = record.parent
    if folder.parent != Path(work_root).resolve() or not folder.name.startswith('webp_prefetch_') or len(folder.name) != 46:
        raise RuntimeError('Unsafe prefetch cache path')
    if any(c not in '0123456789abcdef' for c in folder.name[14:]) or record.name != 'manifest.json':
        raise RuntimeError('Invalid prefetch cache identity')
    if folder.exists() and _redirected(folder):
        raise RuntimeError('Redirected prefetch cache refused')
    return folder


def cached_input(record, source, work_root):
    folder = _cache_folder(record, work_root)
    if _redirected(record):
        raise RuntimeError('Redirected prefetch manifest refused')
    data = json.loads(Path(record).read_text(encoding='utf-8'))
    archive = folder / 'archive.bin'
    if os.path.normcase(data['source']) != os.path.normcase(os.path.abspath(source)) or data['signature'] != signature(source):
        return source, False
    if _redirected(archive) or file_hash(archive) != data['sha256'] or signature(source) != data['signature']:
        raise RuntimeError('Prefetched archive checksum mismatch')
    return str(archive), True


class Prefetch:
    """At most one compressed archive; never extract or modify the next source."""
    def __init__(self, source, work_root, budget_mb):
        self.source, self.work_root = os.path.abspath(source), Path(work_root).resolve()
        self.budget = budget_mb * 1048576
        self.cancel = threading.Event()
        self.record, self.warning = '', ''
        self.folder = None
        self.thread = threading.Thread(target=self._copy, daemon=True)
        self.thread.start()

    def _copy(self):
        try:
            before = signature(self.source)
            if before[0] > self.budget or shutil.disk_usage(self.work_root).free < before[0] + 128 * 1048576:
                self.warning = 'Next archive exceeds prefetch budget/free-space reserve; normal processing will be used'
                return
            self.folder = self.work_root / ('webp_prefetch_' + uuid.uuid4().hex)
            self.folder.mkdir()
            digest = hashlib.sha256()
            copied = 0
            with open(self.source, 'rb') as incoming, (self.folder / 'archive.bin').open('xb') as outgoing:
                while not self.cancel.is_set():
                    block = incoming.read(1048576)
                    if not block:
                        break
                    copied += len(block)
                    if copied > self.budget or copied > before[0]:
                        raise RuntimeError('Next archive grew beyond its reserved cache budget')
                    outgoing.write(block)
                    digest.update(block)
            if self.cancel.is_set() or signature(self.source) != before:
                return
            record = self.folder / 'manifest.json'
            record.write_text(json.dumps(dict(source=self.source, signature=before, sha256=digest.hexdigest())), encoding='utf-8')
            self.record = str(record)
        except Exception as error:
            self.warning = 'Prefetch unavailable: ' + str(error)

    def finish(self, keep):
        if self.thread.is_alive():
            self.cancel.set()
        self.thread.join()  # Finish an active read before any cache cleanup.
        if self.folder and (not keep or not self.record):
            cleanup_cache(str(self.folder / 'manifest.json'), self.work_root)
            self.record = ''
        return self.record
