
from __future__ import division, print_function #, unicode_literals

import os
import argparse


try:
    import win32api
    import win32com.shell.shell
except ImportError:
    pass




def is_admin():
    """
    Return True if the current user has elevated admin privileges.
    Should work on Windows and Linux.

    """

    if os.name == 'nt':
        import ctypes
        # WARNING: requires Windows XP SP2 or higher!
        try:
            # Warning: This call fails unless you have Windows XP SP2 or
            # higher.

            value = ctypes.windll.shell32.IsUserAnAdmin()

        except:
            # traceback.print_exc()
            # print "Admin check failed, assuming not an admin."
            value = False

    elif os.name == 'posix':
        # Check for root on Posix
        value = os.getuid() == 0

    else:
        raise RuntimeError('Unsupported operating system for this module: %s' % (os.name,))

    # Done.
    return value



def work(value):
    print('The value is "%s"' % value)

    permission = win32com.shell.shell.IsUserAnAdmin()

    print('permission: %s' % permission)


    # Done.




if __name__ == '__main__':
    """
    Try running this script as a regular user and again as admin.
    """

    value = is_admin()

    print('\nYou have admin privileges: {:}\n'.format(value))
