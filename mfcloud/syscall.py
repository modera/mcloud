#!/usr/bin/env python
"""syscall: wrappers around many linux syscalls"""
from ctypes import c_char_p, c_int
import logging
import platform
import ctypes
import errno
import os

logger = logging.getLogger("asylum.syscall")
logger.addHandler(logging.NullHandler())

# Try and avoid find_lib here as its slow (70ms per lookup on an atom)
# not the best way to do it, but hey, it saves a whole bunch of startup
# time
#_libsched = ctypes.CDLL(find_library("sched"))
#_libc = ctypes.CDLL(find_library("c"))
_libsched = ctypes.CDLL(None)
_libc = ctypes.CDLL('libc.so.6')

arch = platform.architecture()
## syscall op for some syscalls differs depending on arch on x86, select the correct call
if arch in ("64bit",):
    # 64 bit /usr/include/x86_64-linux-gnu/asm/unistd_64.h
    PIVOT_ROOT = 155
    SYSCLONE = 56
    GETPID = 39
    SET_NS = 308
else:
    # 32 bit /usr/include/i386-linux-gnu/asm/unistd_32.h
    PIVOT_ROOT = 217
    SYSCLONE = 120
    GETPID = 20
    SET_NS = 346

# # Syscall
def syscall(syscall_op, argtypes, errcheck=None):
    """Create a function that calls a specific syscall
    
    This function operates as a Closure to build a custom function for the required
    syscall
    
    Args:
    -----
    syscall_op:    The number of the syscall to create the wrapper for
    argtypes:    The signature of the function
    errcheck:   The error checking function to use when a syscall raises an error
    
    Returns:
    --------
    syscall:    A custom function that when called maps safely onto the syscall
    """
    logger.debug("Creating syscall %d: %s", syscall_op, argtypes)
    syscall = _libc.syscall
    syscall.restype = ctypes.c_int
    syscall.argtypes = (ctypes.c_int,) + argtypes
    if errcheck:
        logger.debug("syscall %d error checking = %r", syscall_op, errcheck)
        syscall.errcheck = errcheck
    def wrapped_syscall(*args):
        """Make a direct syscall to syscall {0}""".format(syscall_op)
        logger.debug("Calling syscall %d: %r", syscall_op, args)
        return syscall(syscall_op, *args)

    return wrapped_syscall

class PathError(Exception):
    """Oldpath does not lie inside newpath"""
    pass

class CapabilityError(object):
    """You do not have the required capabilities (CAP_SYS_ADMIN) to use this syscall"""
    pass

def _pivot_root_error(val, func, args):
    if val < 0:
        val = abs(val)
        if val == errno.EBUSY:
            if os.path.ismount(args[1]):
                raise ValueError("old_root already has a filesystem mounted: {0}".format(args[1]))
            else:
                raise ValueError("new_root is not on a seperate mount to /")
        elif val == errno.EINVAL:
            raise PathError()
        elif val == errno.ENOTDIR:
            raise ValueError("new_root or old_path is not a directory")
        elif val == errno.EPERM:
            ## Linux seems to have overloaded this err num, may actually be a EBUSY
            # ie, no mount at new_rool or old_root already has a mount
            if os.path.ismount(args[1]):
                raise ValueError("old_root already has a filesystem mounted: {0}".format(args[1]))
            else:
                raise CapabilityError("You do not have sufficent privliges (CAP_SYS_ADMIN) to use pivot_root")
        else:
            raise ValueError("Unknown Error: {0}".format(val))
    return val

_pivot_root = syscall(PIVOT_ROOT, (c_char_p, c_char_p), _pivot_root_error)

def contains(x, y):
    """Check that the folder y is inside x"""
    x = os.path.abspath(x)
    y = os.path.abspath(y)

    # ensure x is not the rootfs
    if x == "/":
        return False

    # ensure that the same path was not specified for both fields
    if x == y:
        return False

    # ensure y is inside x
    if x == os.path.commonprefix([x,y]):
        if y[len(x)] == os.path.sep:
            return True
    return False

def pivot_root(new_root, old_path):
    """Make new_root the root filesystem and mount the old one at old_root

    Args:
    -----
    new_root (str):    The new filesystem root
    old_path (str): Where to mount the old root inside the new one
    
    Exceptions:
    -----------
    PathError: the old_path is not inside new_root and would not be visible if a pivot was
                performed
                
    Notes:
    ------
    * some of the more obscure uses of pivot_root may quickly lead to insanity
    """
    logger.debug("Pivioting root: old=%s new=%s", new_root, old_path)
    # subtract old from new and check the first char is "/"
    # this ensures that old_path is inside new_root
    if contains(new_root, old_path):
        _pivot_root(new_root, old_path)
        # we do this for security, linux makes no garenties about updating "/"
        # for any processes for pivot_root
        os.chdir("/")
    else:
        raise PathError("old_path does not lie inside new_path(old={0}, new={1})".format(old_path, new_root))


# bits/sched.h linux/sched.h
CLONE_CSIGNAL = 0x000000FF
CLONE_VM      = 0x00000100
CLONE_FS      = 0x00000200
CLONE_FILES   = 0x00000400
CLONE_SIGHAND = 0x00000800
CLONE_NEWNS   = 0x00020000
CLONE_STOPPED = 0x02000000
CLONE_NEWUTS  = 0x04000000
CLONE_NEWIPC  = 0x08000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWPID  = 0x20000000
CLONE_NEWNET  = 0x40000000


CLONE_ALL = CLONE_NEWIPC  | \
            CLONE_NEWNET  | \
            CLONE_NEWNS   | \
            CLONE_NEWUTS  | \
            CLONE_NEWUSER | \
            CLONE_NEWPID

def clone_flags_from_list(*args, **kwargs):
    """Given a list of 'tags' work out the bitmask for the clone() syscall
    
    Comes in 2 forms:
    clone_flags_from_list(["UTS", "UID"]) or
    clone_flags_from_list(UTS=True, UID=True)

    Args:
    -----
    Form 1:
    arg1 (list of strings):    a list of strings that match the diffrent namespaces
    
    Form 2:
    UTS (bool):    unshare the UTS (hostname) namespace
    UID (bool):    unshare the UID namespace
    PID (bool):    unshare the PID namespace
    NET (bool):    unshare the NET namespace
    IPC (bool):    unshare the IPC namesapce
    MOUNT (bool):    unshare the MOUNT namespace

    Returns:
    --------
    flags (int):    the bitmask of all the requested flags

    Examples:
    ---------
    >>> CLONE_ALL == clone_flags_from_list(["UTS", "UID", "PID", "NET", "MOUNT", "IPC"])
    True

    >>> CLONE_ALL == clone_flags_from_list(["ALL"])
    True

    >>> CLONE_ALL == clone_flags_from_list(UTS=True, UID=True, PID=True, NET=True, MOUNT=True, IPC=True)
    True

    >>> CLONE_ALL == clone_flags_from_list(ALL=True)
    True
    """
    namespace = []
    if len(args) == 1:
        namespace = args[0]
    else:
        if "UTS" in kwargs:
            if kwargs['UTS']:
                namespace.append("UTS")
        if "UID" in kwargs:
            if kwargs['UID']:
                namespace.append("UID")
        if "PID" in kwargs:
            if kwargs['PID']:
                namespace.append("PID")
        if "NET" in kwargs:
            if kwargs['NET']:
                namespace.append("NET")
        if "MOUNT" in kwargs:
            if kwargs['MOUNT']:
                namespace.append("MOUNT")
        if "IPC" in kwargs:
            if kwargs['IPC']:
                namespace.append("IPC")
        if "ALL" in kwargs:
            if kwargs['ALL']:
                namespace.append("ALL")

    flags = 0
    if "UTS" in namespace:
        flags |= CLONE_NEWUTS
    if "UID" in namespace:
        flags |= CLONE_NEWUSER
    if "PID" in namespace:
        flags |= CLONE_NEWPID
    if "NET" in namespace:
        flags |= CLONE_NEWNET
    if "MOUNT" in namespace:
        flags |= CLONE_NEWNS
    if "IPC" in namespace:
        flags |= CLONE_NEWIPC
    if "ALL" in namespace:
        flags |= CLONE_ALL

    return flags

# wait4, waitpid flags (not provided by python)
# this is a bad hack to work around C stupidity
# flags is a signed int but WCLONE is specified 
# as 0x80000000
WCLONE = -2 ** 31
WALL = 0x40000000

#### UnShare ####
# bits/sched.h
# int unshare(int flags)
# int clone(int (*fn)(void *), void *child_stack, int flags, void *args,
#            /*pid_t *ptid, struct user_desc *tls, pid_t, *cls */)
def _unshare_error(val, func, args):
    """Check the unshare() funciton call for a error return code"""
    if val < 0:
        val = abs(val)
        if val == errno.EINVAL:
            raise ValueError("Invalid Flag specified")
        elif val == errno.ENOMEM:
            raise MEMError("Cannot allocate memory to unshare resources")
        elif val == errno.EPERM:
            raise CapabilityError("You do not have sufficent privliges (CAP_SYS_ADMIN) to use CLONE_NEWNS or namespaces are not compiled into the kernel")
        else:
            raise ValueError("Unknown Error: {0}".format(val))
    return val

unshare = _libsched.unshare
unshare.__doc__ = """Unshare resources with the current namespace

Args:
-----
flags (int):    The bitmask of flags to unshare, only CLONE_IPC, CLONE_NET or CLONE_NS
                is valid

Notes:
------
* Currently unshare as of 2.6.37 only allows unsharing of CLONE_NET
  CLONE_IPC and CLONE_NS. attempting to unshare other resources fails
  to unshare all namespaces try using clone()
"""
unshare.argtypes = (ctypes.c_int, )
unshare.restype = ctypes.c_int
unshare.errcheck = _unshare_error

#### Clone ####
def _clone_error(val, func, args):
    """Check the clone() funciton call for a error return code"""
    if val < 0:
        val = abs(val)
        if val == errno.EAGAIN:
            raise ProcessLimitError("Running process limit hit")
        elif val == errno.EINVAL:
            raise ValueError("Invalid Flag specified")
        elif val == errno.ENOMEM:
            raise MEMError("Cannot allocate memory to unshare resources")
        elif val == errno.EPERM:
            raise CapabilityError("You do not have sufficent privliges (CAP_SYS_ADMIN) to use CLONE_NEWNS or namespaces are not compiled into the kernel")
        else:
            raise ValueError("Unknown Error: {0}".format(val))
    return val


_sysclone = syscall(SYSCLONE, (ctypes.c_int, ctypes.c_int), _clone_error)
def clone(flags, child_stack=0):
    """Fork and unshare resources in one step
    
    currently works with all types of namespaces, however unlike
    unshare() this acts like a fork and creates a process in the 
    new namespace.
    
    Args:
    -----
    flags (int):    A bit mask of flags to pass to clone, valid flags
                    start with CLONE_*
    child_stack (int): the base address of the stack allocated to the 
                        child process as the child may be operating in
                        the same memory space as the parent (eg threads)
                        if specified as 0 automatically select a valid
                        address, CLONE_VM should not be specified
                        if this is non zero (default=0)                    
    Returns:
    --------
    child_pid (int): the child pid if the current process is the parent
                     otherwise 0

    Notes:
    ------
    * note that using CLONE_NEWPID will create the new process in the new
      namespace with PID = 1, however calls to os.getpid() will return
      the same pid as the parent. this is due to a caching bug in libc
      to get the real PID, use the getpid supplied in this module
    """
    logger.debug("Clone called: flags=0x%x, stack=0x%x", flags, child_stack)
    return _sysclone(flags, child_stack)

#### PRCTL ####
# linux/prctl.h
# Set process name, name can be 16 bytes long max, null terminated
# arg2 = (char *) to the name buffer
PR_SET_NAME = 15
PR_GET_NAME = 16

# Used for setting the seccomp_enabled flag
# arg2 must be 1 for SET
# A get returns 0 if not active, SIGKILL if active
PR_GET_SECCOMP = 21
PR_SET_SECCOMP = 22

def _prctl_error(val, func, args):
    """Check the prctl() funciton call for a error return code"""
    if val < 0:
        val = abs(val)
        if val == errno.EINVAL:
            raise ConfigError('Kernel not compiled with "CONFIG_SECCOMP"')
        elif val == errno.EFAULT:
            raise ValueError("arg2 is an invalid address")
        elif val == errno.EPERM:
            raise ValueError("You do not have the required Capabilites to use this call")
        else:
            raise ValueError("Unknown Error: {0}".format(val))
    return val

# int, prctl(int, arg2=ulong, arg3=ulong, arg4=ulong, arg5=ulong)
prctl = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, 
                         ctypes.c_ulong, ctypes.c_ulong)
_param_flags = ((0, "option"), (0, "arg2", 0), (0, "arg3", 0), (0, "arg4", 0), (0, "arg5", 0))
prctl = prctl(("prctl", _libsched), _param_flags)
prctl.restype = ctypes.c_int
prctl.errcheck = _prctl_error
del _param_flags

#### getpid ####
# non caching getpid
# !!!! Use with caution !!!!
getpid = syscall(GETPID, tuple())
getpid.__doc__ = """Non caching version of getpid

!!!! Use with caution, has higher overhead than os.getpid !!!!
see clone for more info of this workaround

Returns:
--------
pid (int): the pid of the current process
"""

#### gethostname/sethostname ####
def _hostname_error(val, func, args):
    if val < 0:
        val = abs(val)
        if val == errno.EFAULT:
            raise ValueError("The specified name is not a valid address")
        elif val == errno.EINVAL or val == errno.ENAMETOOLONG:
            raise ValueError("Hostname is longer than kernel maximum")
        elif val == errno.EPERM:
            raise CapabilityError("You do not have sufficent privliges (CAP_SYS_ADMIN) to change the hostname")
        else:
            raise ValueError("Unknown Error: {0}".format(val))
    return val

_gethostname = _libc.gethostname
_gethostname.argtypes = (ctypes.POINTER(ctypes.c_char * 64), ctypes.c_int)
_gethostname.restype = ctypes.c_int
_gethostname.errcheck = _hostname_error

_sethostname = _libc.sethostname
_sethostname.argtypes = (ctypes.POINTER(ctypes.c_char * 64), ctypes.c_int)
_sethostname.restype = ctypes.c_int
_sethostname.errcheck = _hostname_error

_hostname_buffer_len = 64
_hostname_buffer = ctypes.c_char * _hostname_buffer_len
def gethostname():
    """Get the hostname of the system
    
    Returns:
    --------
    hostname (str):    the hostname of the system
    """
    logger.debug("Calling gethostname")
    buffer = _hostname_buffer()
    _gethostname(buffer, _hostname_buffer_len)
    logger.debug("gethostname returned %s", buffer.value)
    return buffer.value

def sethostname(hostname):
    """Set the hostname for the system
    
    Args:
    -----
    hostname (str): The new hostname of the system
    """
    logger.debug("Calling sethostname(%s)", hostname)
    buffer = _hostname_buffer()
    buffer.value = hostname
    _sethostname(buffer, _hostname_buffer_len)


#### set_ns ####
# Auto detect the namespace, for use with set_ns
NS_AUTO = 0
def _set_ns_error(val, func, args):
    if val < 0:
        val = abs(val)
        if val == errno.EBADF:
            raise ValueError("fd is not a valid file desciprtor for set_ns (is it pointing to the right file?)")
        elif val == errno.EINVAL:
            raise ValueError("namespace type of fd does not match the supplied namespace")
        elif val == errno.ENOMEM:
            raise MemoryError("Insufficent kernel memory avalible")
        elif val == errno.EPERM:
            # of course, this being linux, nearly all the above conditions actually only return EPERM
            raise CapabilityError("You do not have sufficent privliges (CAP_SYS_ADMIN) to use set_ns")
        else:
            raise ValueError("Unknown Error: {0}".format(val))
    return val

_set_ns = syscall(SET_NS, (c_int, c_int), _set_ns_error)

def set_ns(fd, namespace=NS_AUTO):
    """set_ns: change a processes namespace to that pointed to by the open file descriptor `fd`
    
    :param file fd: A file-like object (that provides the fileno() method) or an integer representing
                    an open file to the namespace you wish to change to
    :param int namespace: The type of namespace that `fd` points to, set to NS_AUTO to have this auto
                          detected
    :rtype: None
    
    The namespace argument can be any CLONE_NEW* Flag that can be provided to the clone() or unshare()
    syscall, valid choices are listed below. please note that not all the listed flags will work on all
    kernel versions:
    
    * CLONE_NEWIPC
    * CLONE_NEWNET
    * CLONE_NEWNS
    * CLONE_NEWUTS
    * CLONE_NEWUSER
    * CLONE_NEWPID
    """
    # auto detect files vs fds, fudge anything else
    try:
        fd = fd.fileno()
    except AttributeError:
        fd = int(fd)

    # '0' means auto detect the namespace
    _set_ns(fd, namespace)
    

class ConfigError(Exception):
    """The kernel was not compiled with the required subsystem options"""
    pass

class UnshareError(Exception):
    """An exception occured in the unshare system call"""
    pass

class CloneError(Exception):
    """An exception occured in the clone system call"""
    pass

class ProcessLimitError(CloneError):
    """Running Process limit hit"""
    pass

class MEMError(UnshareError, CloneError):
    """Not enough memory avalible to allocate resources"""
    pass

class CapabilityError(UnshareError, CloneError):
    """You do not have the required capabilities (CAP_SYS_ADMIN) to use this syscall"""
    pass

if __name__ == "__main__":
    pass
