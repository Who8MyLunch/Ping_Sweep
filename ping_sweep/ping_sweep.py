#!/usr/bin/env python

#
# Copyright 2011 Pierre V. Villeneuve
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Perform a sequence of pings over a range of payload sizes
"""

from __future__ import division, print_function #, unicode_literals

import argparse
import os
import sys
import time
import socket
import random

import dpkt


#################################################
# Helper functions.
def mean(data):
    """
    Compute the mean value of a sequence of numbers.
    """
    if not hasattr(data, '__iter__'):
        data = [data]

    avg = float(sum(data)) / len(data)

    # Done
    return avg



def std(data):
    """
    Compute standard deviation of a seqence of numbers.
    """

    avg = mean(data)
    dm2 = [ (d - avg)**2 for d in data ]

    variance = mean(dm2)
    sigma = variance**.5

    # Done.
    return sigma



def now():
    """
    Return wall clock time, platform dependent.
    """
    if os.sys.platform == 'win32':
        return time.clock()  # best for windows?  seems to give finer temporal resolution.
    else:
        return time.time()  # best for Unix?  Please correct me if I got this wrong!

#################################################


# Define some exceptions.
class PingSweepError(Exception):
    def __init__(self, msg):
        self.msg = repr(msg)

    def __str__(self):
        return repr('Ping_Sweep Error: {:s}'.format(self.msg))


class PingSweepSocketError(PingSweepError):
    def __str__(self):
        return repr('Ping_Sweep Socket Error: {:s}'.format(self.msg))


class PingSweepNameError(PingSweepError):
    def __str__(self):
        return repr('Ping_Sweep Name Error: {:s}'.format(self.msg))


#################################################

def create_socket(host_name, timeout=None):
    """
    Make the socket and connect to remote host.

    NOTE: This function requires the user to be running as admin or root since
    we are creating a raw socket.

    timeout: seconds
    """
    if not timeout:
        timeout = 1.0  # seconds.

    # Make the socket.
    s_family = socket.AF_INET
    s_type = socket.SOCK_RAW
    s_proto = dpkt.ip.IP_PROTO_ICMP

    sock = socket.socket(s_family, s_type, s_proto)
    sock.setblocking(True)
    sock.settimeout(timeout)

    # Connect to remote host.  This will raise socket.error if can't resolve name.
    try:
        host_addr = socket.gethostbyname(host_name)
        port = 1  # dummy value
    except socket.error:
        raise PingSweepNameError('Unable to create socket with name: {:s}'.format(host_name))

    sock.connect( (host_addr, port) )

    # Done.
    return sock


def create_packet(pid, seq, data_size):
    """
    Create a data packet from scratch.  Stored as a string.
    """

    # Random sequence of characters.
    payload = ''
    for k in range(data_size):
        payload += chr(random.randint(65, 65+25))

    # Build the ICMP echo payload.
    echo = dpkt.icmp.ICMP.Echo()
    echo.id = pid
    echo.seq = seq
    echo.data = payload

    # Build the ICMP packet.
    icmp = dpkt.icmp.ICMP()
    icmp.type = dpkt.icmp.ICMP_ECHO
    icmp.data = echo

    # Return data packet as string representation.
    packet = str(icmp)

    # Done.
    return payload, packet



def send(sock, msg):
    """
    Send message over the socket.
    """
    num_sent = 0
    while num_sent < len(msg):
        sent = sock.send(msg[num_sent:])
        if not sent:
            raise RuntimeError("socket connection broken")
        num_sent = num_sent + sent

    # Done.
    return num_sent



def recv(sock, num_bytes):
    """
    Receive message over socket.
    """
    msg = ''
    while len(msg) < num_bytes:
        msg_chunk = sock.recv(8192)
        if msg_chunk == '':
            raise RuntimeError('connection ended')
        msg = msg + msg_chunk

    # Done.
    return msg



def ping_once(sock, data_size=None, pid=None):
    """
    One ping, just one ping.

    sock = socket created by caller.
    """

    # from IPython import embed
    # embed()

    if not data_size:
        data_size = 64

    if not pid:
        pid = 1

    seq = 1999 # not really used here, but the TV show "Space 1999!"" was pretty awesome when I was a kid.

    payload, packet = create_packet(pid, seq, data_size)

    try:
        # Send it, record the time.
        send(sock, packet)
        time_send = now()

        # Wait and receive response, record the time.
        # msg_recv = sock.recv(0xffff)
        # msg_recv = sock.recv(4096)
        # buf_size = 8192
        # msg_recv = sock.recv(buf_size)
        msg_recv = recv(sock, len(packet))
        time_recv = now()

        # Extract packet data.
        ip = dpkt.ip.IP(msg_recv)

        # Process results.
        is_same_data = (payload == ip.icmp.echo.data)
        time_ping = (time_recv - time_send) * 1000.    # convert from seconds to milliseconds
        echo_id = ip.icmp.echo.id

    except socket.timeout:
        is_same_data = False
        time_ping = None
        echo_id = None


    # Finish.
    result = {'time_ping': time_ping,
              'data_size': data_size,
              'packet_size': len(packet),
              'timeout': sock.gettimeout()*1000.,  # convert from seconds to milliseconds
              'is_same_data': is_same_data,
              'id': pid,
              'echo_id': echo_id}

    # Done.
    return result



def ping_repeat(host_name, data_size=None, time_pause=None, count_send=None, timeout=None):
    """
    Ping remote host.  Repeat for better statistics.

    data_size: size of payload in bytes.
    count_send: number of ping repetitions.
    time_pause: milliseconds between repetitions.
    timeout: socket timeout period, milliseconds.
    """

    if not time_pause:
        time_pause = 5.  # milliseconds

    if not count_send:
        count_send = 25  # milliseconds

    if not timeout:
        timeout = 1000.  # milliseconds

    if not data_size:
        data_size = 64   # number of bytes.

    # Make a socket, send a sequence of pings.
    sock = create_socket(host_name, timeout=timeout/1000.)   # note: timeout in seconds, not milliseconds.
    if not sock:
        return None, 0

    # Main loop over pings.
    time_sweep_start = now()
    results = []
    for k in range(count_send):
        if k > 0:
            # Little pause between sending packets.  Try to be a little nice.
            time.sleep(time_pause / 1000.)   # sleep in seconds, not milliseconds.

        res = ping_once(sock, data_size=data_size)
        if not res:
            raise Exception('Problem calling ping_once.')

        results.append(res)


    # Close the socket.
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()

    # Process the accumulated results.
    count_timeout = 0
    count_corrupt = 0

    times = []
    for res in results:
        if res['is_same_data']:
            times.append(res['time_ping'])
        else:
            if res['time_ping']:
                # Packet is corrupt, but at least it still came back.
                # Still considered lost since returned payload did not match original.
                count_corrupt += 1
            else:
                # No return time recorded, packet never came back.  Most likely a timeout.
                count_timeout += 1


    count_lost = count_timeout + count_corrupt
    count_recv = count_send - count_lost
    packet_size = res['packet_size']
    stats = {'host_name': host_name,
             'data_size': data_size,
             'packet_size': packet_size,
             'times': times,
             'timeout': timeout,
             'time_pause': time_pause,
             'count_send': count_send,
             'count_timeout': count_timeout,
             'count_corrupt': count_corrupt,
             'count_lost': count_lost}

    # Done.
    return stats, count_recv



def ping_sweep(host_name, timeout=None, size_sweep=None, time_pause=None, count_send=None, verbosity=False):
    """
    Perform a sequence of pings over a range of payload sizes.
    """
    if not size_sweep:
        size_sweep = [16, 64, 256, 1024]

    try:
        stats_sweep = []
        for s in size_sweep:
            stats, count_recv = ping_repeat(host_name, data_size=s,
                                            timeout=timeout,
                                            time_pause=time_pause,
                                            count_send=count_send)

            stats_sweep.append(stats)

            if verbosity:
                if count_recv:
                    if len(stats_sweep) == 1:
                        # Display the header first time through.
                        display_results_header(stats)

                    # Display line of results.
                    display_results_line(stats)

        print('\nDone.')

    except KeyboardInterrupt:
        print('\nUser stop!')

    # Done.
    return stats_sweep

#################################################


def display_results_header(stats):
    """
    Nice results display.
    """

    # Print.
    print('\n Ping Sweep')
    print(' ==========')
    print(' target name: %s' % stats['host_name'])
    print(' ping count:  %d' % stats['count_send'])
    print(' timeout:     %d ms' % stats['timeout'])
    print(' pause time:  %d ms' % stats['time_pause'])
    print()

    # Header strings.
    head_A = '  Size (bytes)  |       Ping Times (ms)         | Lost Packets'
    head_B = ' Payload Packet |  min    avg    [std]     max  | All  T   C '

    print(head_A)
    print(head_B)

    head_C = ' ' + '-' * (len(head_B)-1)
    print(head_C)

    # Done.



def display_results_line(stats):
    """
    Generate line of text for current set of results.
    """

    template = ' {:5d}  {:5d}   |{:6.2f} {:6.2f} [{:6.2f}] {:7.2f} |{:3d} {:3d} {:3d}'

    t_min = min(stats['times'])
    t_avg = mean(stats['times'])
    t_std = std(stats['times'])
    t_max = max(stats['times'])

    values = stats['data_size'], stats['packet_size'], t_min, t_avg, t_std, t_max, \
             stats['count_lost'], stats['count_timeout'], stats['count_corrupt']

    print(template.format(*values))

    # Done.

#################################################


def is_admin():
    """
    Return True if the current user has elevated admin privileges.
    Should work on Windows and Linux.
    """

    if os.name == 'nt':
        import ctypes
        try:
            # Warning: This call fails unless you have Windows XP SP2 or higher.
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

#################################################


def main():
    """
    Command line application.
    """

    # Parse command line arguments.
    parser = argparse.ArgumentParser()

    parser.add_argument('host_name', action='store',
                        help='Name or IP address of host to ping')

    parser.add_argument( '-c', '--count', action='store', type=int, default=25,
                        help='Number of pings at each packet payload size')

    parser.add_argument('-p', '--pause', action='store', type=float, default=5.,
                        help='Pause time between individual pings (ms)')

    parser.add_argument('-t' ,'--timeout', action='store', type=float, default=1000.,
                        help='Socket timeout (ms)')

    parser.add_argument('-L' ,'--large', action='store_true', default=False,
                        help='Use additional payloads larger than 1024 bytes.')

    args = parser.parse_args()

    # Use large packets?
    if args.large:
        size_sweep = [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
    else:
        size_sweep = [32, 64, 128, 256, 512, 1024, 1472]
        # size_sweep = [2048, 4090, 4093, 4096, 4099, 4102]

    # This tools only runs with elevated privileges because we need access to a raw socket.
    if is_admin():
        # Ok good.
        # Run the application: sequence of pings over a range of packet sizes.
        try:
            stats_sweep = ping_sweep(args.host_name,
                                     size_sweep=size_sweep,
                                     count_send=args.count,
                                     time_pause=args.pause,
                                     timeout=args.timeout,
                                     verbosity=True)
        except PingSweepNameError as e:
            print('\nOoops!  There was a problem: {:s}'.format(e.msg))

    else:
        print('\nOops!  This application requires elevated privileges.')
        print('Please try again.')

    # Done.



if __name__ == '__main__':
    main()
