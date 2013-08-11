
from __future__ import division, print_function #, unicode_literals

import os
import argparse
import subprocess

import win32api
import win32com.shell.shell




def work(value):
    print('The value is "%s"' % value)

    permission = win32com.shell.shell.IsUserAnAdmin()
    
    print('permission: %s' % permission)

    
    # Done.


def main():

    # Parse command line arguments.
    parser = argparse.ArgumentParser()

    parser.add_argument('value', action='store', help='something')

    args = parser.parse_args()

    # This only runs with admin privileges.
    if win32com.shell.shell.IsUserAnAdmin():
        # Ok good.  Run the application.
        work(args.value)
    else:
        raise Exception('This application requires admin privileges.')

    # Done.


if __name__ == '__main__':
    main()
