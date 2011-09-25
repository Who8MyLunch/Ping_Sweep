# Work in progess implementation of non-blocking file IO that blocks
# but only on Stackless channels rather than blocking the whole
# interpreter.. etc
#
# * TODO
#
# Incorrectly implemented:
# - Exceptions.  Should be IOErrors where applicable rather than
#   Windows errors.
# - The Python API calls should always raise Python related errors and
#   not Windows errors.
# - Look into "cannot block last runnable tasklet".  I seem to recall
#   that there as this error which if people are not doing file operations
#   in other tasklets but on the main one, I will want to look into and
#   handle better.
#
# Features:
# - File writing (untested but partially written).
# - Replacement socket object based on IOCP.
# - Reusing a buffer, or a pool of them.  When the reading is only a
#   small amount, there is no reason I can't reuse the same buffer.
#   Might have to clear it though.
#
# * NOTES
#
# - The initial value I had for INVALID_HANDLE_VALUE was -1, but this was
#   not matching what was being returned from CreateFile in event of error.
#   That was 4294967295L or 0xFFFFFFF, which I had to change it to.
#

import stackless
from ctypes import windll, pythonapi
from ctypes import c_int, c_long, c_ulong, c_void_p, byref, c_char_p, Structure, Union, py_object, POINTER, pointer
from ctypes.wintypes import HANDLE, ULONG, DWORD, BOOL, LPCSTR, LPCWSTR, WinError
import os

uthreadLibPath = r"C:\Richard\SVN\stackless\sandbox\libraries\uthread-ccp"

import sys
if uthreadLibPath not in sys.path:
    sys.path.append(uthreadLibPath)

import uthread

# Check os.name is "nt" ?
# ----------------------------------------------------------------------------

class _US(Structure):
    _fields_ = [
        ("Offset",          DWORD),
        ("OffsetHigh",      DWORD),
    ]

class _U(Union):
    _fields_ = [
        ("s",               _US),
        ("Pointer",         c_void_p),
    ]

    _anonymous_ = ("s",)

class OVERLAPPED(Structure):
    _fields_ = [
        ("Internal",        POINTER(ULONG)),
        ("InternalHigh",    POINTER(ULONG)),

        ("u",               _U),

        ("hEvent",          HANDLE),

        # Custom fields.
        ("channel",         py_object),
    ]

    _anonymous_ = ("u",)

# ----------------------------------------------------------------------------

# Windows kernel32 API

CreateIoCompletionPort = windll.kernel32.CreateIoCompletionPort
CreateIoCompletionPort.argtypes = (HANDLE, HANDLE, POINTER(c_ulong), DWORD)
CreateIoCompletionPort.restype = HANDLE

GetQueuedCompletionStatus = windll.kernel32.GetQueuedCompletionStatus
GetQueuedCompletionStatus.argtypes = (HANDLE, POINTER(DWORD), POINTER(c_ulong), POINTER(POINTER(OVERLAPPED)), DWORD)
GetQueuedCompletionStatus.restype = BOOL

ReadFile = windll.kernel32.ReadFile
ReadFile.argtypes = (HANDLE, c_void_p, DWORD, POINTER(DWORD), POINTER(OVERLAPPED))
ReadFile.restype = BOOL

WriteFile = windll.kernel32.WriteFile
WriteFile.argtypes = (HANDLE, c_void_p, DWORD, POINTER(DWORD), POINTER(OVERLAPPED))
WriteFile.restype = BOOL

CreateFileA = windll.kernel32.CreateFileA
CreateFileA.argtypes = (LPCSTR, DWORD, DWORD, c_void_p, DWORD, DWORD, HANDLE)
CreateFileA.restype = HANDLE

CreateFileW = windll.kernel32.CreateFileW
CreateFileW.argtypes = (LPCWSTR, DWORD, DWORD, c_void_p, DWORD, DWORD, HANDLE)
CreateFileW.restype = HANDLE

CloseHandle = windll.kernel32.CloseHandle
CloseHandle.argtypes = (HANDLE,)
CloseHandle.restype = BOOL

# Python API

pythonapi.PyBuffer_New.argtypes = (c_ulong,)
pythonapi.PyBuffer_New.restype = py_object

pythonapi.PyErr_SetFromErrno.argtypes = (py_object,)
pythonapi.PyErr_SetFromErrno.restype = py_object

# ----------------------------------------------------------------------------

INVALID_HANDLE_VALUE = 0xFFFFFFFF
NULL = c_ulong()

WAIT_TIMEOUT = 0x102
ERROR_IO_PENDING = 997


class IOCPManager:
    port = None

    def __init__(self, numThreads=NULL):
        handle = CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, NULL, numThreads)
        if handle == 0:
            raise WinError()
        self.handle = handle
        self.numThreads = numThreads
        self.overlappedByID = {}

        # If the interpreter is exiting, we will have None in place of pretty
        # much every global variable.  So we need to store references for these
        # in case we no longer have them and are unable to import ctypes because
        # the interpreter is garbage collecting this instance when it is exiting.
        self.delReferences = GetQueuedCompletionStatus, CloseHandle, DWORD, c_ulong, POINTER, OVERLAPPED, byref

    def __del__(self):
        if self.handle is None:
            return

        # Cater for interpreter exit problems described above.
        global GetQueuedCompletionStatus
        if GetQueuedCompletionStatus is None:
            GetQueuedCompletionStatus, CloseHandle, DWORD, c_ulong, POINTER, OVERLAPPED, byref = self.delReferences

        numBytes = DWORD()
        completionKey = c_ulong()
        ovp = POINTER(OVERLAPPED)()

        while True:
            ret = GetQueuedCompletionStatus(self.handle, byref(numBytes), byref(completionKey), byref(ovp), 0)
            if ovp:
                self.UnregisterChannelObject(ovp.contents)
            elif ret == 0:
                break

        #for channelID, (f, c) in self.overlappedByID.iteritems():
        #    c.send_exception
        self.overlappedByID.clear()

        CloseHandle(self.handle)

    def poll(self, timeout=100):
        while True:
            numBytes = DWORD()
            completionKey = c_ulong()
            ovp = POINTER(OVERLAPPED)()
            ret = GetQueuedCompletionStatus(self.handle, byref(numBytes), byref(completionKey), byref(ovp), timeout)
            timeout = 0

            if not ovp and ret == 0:
                if windll.kernel32.GetLastError() == WAIT_TIMEOUT:
                    return None
                raise WinError()

            c = ovp.contents.channel
            if not c:
                raise RuntimeError("Something went horribly wrong in IOCP land")

            self.UnregisterChannelObject(c)

            if ret == 0:
                c.send_exception(WinError, e.errno, e.strerror)
            else:
                c.send(None)

    def RegisterChannelObject(self, ob, c):
        self.overlappedByID[id(c)] = ob, c

    def UnregisterChannelObject(self, c):
        k = id(c)
        if self.overlappedByID.has_key(k):
            del self.overlappedByID[k]


# ----------------------------------------------------------------------------

# Windows definitions:

FILE_FLAG_RANDOM_ACCESS = 0x10000000
FILE_FLAG_OVERLAPPED    = 0x40000000

GENERIC_READ            = 0x80000000
GENERIC_WRITE           = 0x40000000

FILE_SHARE_READ         = 0x00000001
FILE_SHARE_WRITE        = 0x00000002

OPEN_EXISTING           = 3
OPEN_ALWAYS             = 4

class BaseFileObject:
    closed = True

    def __init__(self, filename, mode="r", buffering=-1):
        if not self.closed:
            self.close()

        self.binary = 'b' in mode

        self.handle_open(filename, mode, buffering)

        self.name = filename
        self.mode = mode
        self.offset = 0
        self.closed = False

    def __del__(self):
        self.close()

    def __repr__(self):
        return "<%s file '%s', mode '%s' at 0x%08X>" % ([ "open", "closed" ][self.closed], self.name, self.mode, id(self))

    def check_still_open(self):
        if self.closed:
            raise ValueError("I/O operation on closed file")

    def close(self):
        if not self.closed:
            self.flush()

            self.handle_close()

            # We keep the file name, mode and other state from the last
            # file opened so we can display it in the __repr__ result as
            # the builtin file object does when it is closed.
            del self.closed

    @uthread.with_instance_locking
    def seek(self, offset, whence=os.SEEK_SET):
        self.handle_flush()
        if whence == os.SEEK_SET:
            self.offset = offset
        elif whence == os.SEEK_CUR:
            self.offset += offset
        elif whence == os.SEEK_END:
            raise RuntimeError("SEEK_END unimplemented")

    @uthread.with_instance_locking
    def tell(self):
        return self.offset

    @uthread.with_instance_locking
    def read(self, size=None):
        self.check_still_open()
        return self.handle_read(size)

    @uthread.with_instance_locking
    def write(self, s):
        self.check_still_open()
        return self.handle_write(s)

    @uthread.with_instance_locking
    def flush(self):
        self.handle_flush()

    def fileno(self):
        self.check_still_open()
        raise RuntimeError("fileno unimplemented")

    def isatty(self):
        self.check_still_open()
        return False

# For now this is instanced so the module will just work.
iocpMgr = IOCPManager()

class FileObject(BaseFileObject):
    def handle_open(self, filename, mode, buffering):
        flags = FILE_FLAG_RANDOM_ACCESS | FILE_FLAG_OVERLAPPED
        access = GENERIC_READ
        if 'w' in mode or 'r' in mode and '+' in mode:
            access |= GENERIC_WRITE
        share = FILE_SHARE_READ | FILE_SHARE_WRITE
        if 'w' in mode:
            disposition = OPEN_ALWAYS
        else:
            disposition = OPEN_EXISTING
        dummyp = c_void_p()

        if isinstance(filename, unicode):
            func = CreateFileW
        else:
            func = CreateFileA
        handle = func(filename, access, share, dummyp, disposition, flags, NULL)
        if handle == INVALID_HANDLE_VALUE:
            # I chose this because it gives an approximate error to the one I get
            # when I open a non-existant file in read only mode.  Not the same
            # message, but pretty similar.
            pythonapi.PyErr_SetExcFromWindowsErrWithFilename(py_object(IOError), 0, c_char_p(filename))

        self.handle = handle
        self.iocpLinked = False

    def handle_close(self):
        CloseHandle(self.handle)

        del self.handle
        del self.iocpLinked

    def handle_read(self, bytesToRead):
        # If no amount to read is given, read the whole file.
        # If we are asked to read a larger amount than the actual file
        # size, only read what is left of the actual file size.
        maxBytesToRead = int(os.path.getsize(self.name)) - self.offset
        if bytesToRead is None or maxBytesToRead < bytesToRead:
            bytesToRead = maxBytesToRead

        readBuffer = pythonapi.PyBuffer_New(bytesToRead)
        if readBuffer == 0:
            # This sould be a Python error.
            raise WinError()

        # Without access to the C structure associated with the buffer, we
        # have no other way of determining what address the allocated memory
        # we can use to read into starts at.
        readBufferPtr = c_void_p()
        ret = pythonapi.PyArg_ParseTuple(py_object((readBuffer,)), c_char_p("w"), byref(readBufferPtr))
        if ret == 0:
            # This sould be a Python error.
            raise WinError()

        bytesRead = DWORD()
        ov = OVERLAPPED()
        ov.Offset = self.offset
        ov.channel = stackless.channel()

        self.ensure_iocp_association()
        ret = ReadFile(self.handle, readBufferPtr, bytesToRead, byref(bytesRead), byref(ov))
        if ret == 0:
            # Error.
            if windll.kernel32.GetLastError() != ERROR_IO_PENDING:
                # This should raise.
                pythonapi.PyErr_SetExcFromWindowsErrWithFilename(py_object(IOError), 0, c_char_p(self.filename))

            # Windows is processing our IO request and will get back to us.
            iocpMgr.RegisterChannelObject(self, ov.channel)
            ov.channel.receive()

        # Set the new file offset.
        self.offset += bytesToRead

        # We either got an immediate result, or our channel had notification
        # send that our buffer had been filled successfully.
        return readBuffer[:bytesToRead]

    def handle_write(self, s):
        # UNTESTED AS OF YET.

        # Without access to the C structure associated with the buffer, we
        # have no other way of determining what the address of the given data
        # which we can use to write from is.
        writeBufferPtr = c_char_p()
        bytesToWrite = c_int()
        fmt = self.binary and "s#" or "t#"
        ret = pythonapi.PyArg_ParseTuple(py_object((s,)), c_char_p(fmt), byref(bPtr), byref(bLen))
        if ret == 0:
            # This sould be a Python error.
            raise WinError()

        bytesWritten = DWORD()
        ov = OVERLAPPED()
        ov.Offset = self.offset
        ov.channel = stackless.channel()

        self.ensure_iocp_association()
        ret = WriteFile(self.handle, writeBufferPtr, bytesToWrite, byref(bytesWritten), byref(ov))
        if ret == 0:
            # Error.
            if windll.kernel32.GetLastError() != ERROR_IO_PENDING:
                # This should raise.
                pythonapi.PyErr_SetExcFromWindowsErrWithFilename(py_object(IOError), 0, c_char_p(self.filename))

            # Windows is processing our IO request and will get back to us.
            iocpMgr.RegisterChannelObject(self, ov.channel)
            ov.channel.receive()

        if bytesToWrite != bytesWritten.value:
            # This should raise.  Same check as done in the actual file
            # object code.
            raise WinError()

    def handle_flush(self):
        pass

    def ensure_iocp_association(self):
        if not self.iocpLinked:
            CreateIoCompletionPort(self.handle, iocpMgr.handle, NULL, iocpMgr.numThreads)
            self.iocpLinked = True


def Test(s):
    s = r"C:\Richard\Programs\\"+ s
    f = FileObject(s, "rb")
    f.seek(100)
    v = f.read()
    f.close()
    print len(v)

