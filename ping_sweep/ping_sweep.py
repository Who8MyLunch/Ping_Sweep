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



def create_socket(host_name, timeout=None):
    """
    Make the socket and connect to remote host.
    timeout: seconds
    """
    if not timeout:
        timeout = 1.0

    # Make the socket.
    s_family = socket.AF_INET
    s_type = socket.SOCK_RAW
    s_proto = dpkt.ip.IP_PROTO_ICMP

    sock = socket.socket(s_family, s_type, s_proto)
    sock.settimeout(timeout)

    # Connect to remote host.
    host_addr = socket.gethostbyname(host_name)
    port = 1  # dummy value

    sock.connect( (host_addr, port) )

    # Done.
    return sock



def ping_once(sock, data_size=None, pid=None):
    """
    One ping, just one ping.
    """

    if not data_size:
        data_size = 64

    if not pid:
        pid = 1

    seq = 1999 # not really used here, but the TV show "Space 1999!"" was pretty awesome when I was a kid.

    payload, packet = create_packet(pid, seq, data_size)

    try:
        # Send it, record the time.
        sock.sendall(packet)
        time_send = now()

        # Wait and receive response, record the time.
        msg_recv = sock.recv(0xffff)
        time_recv = now()

        # Extract packet data.
        ip = dpkt.ip.IP(msg_recv)

        # Process results.
        is_same_data = (payload == ip.icmp.echo.data)
        time_ping = time_recv - time_send
        echo_id = ip.icmp.echo.id

    except socket.timeout:
        is_same_data = False
        time_ping = None
        echo_id = None


    # Finish.
    result = {'time_ping': time_ping,
              'data_size': data_size,
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


    # Make a socket, send a sequence of pings.
    sock = create_socket(host_name, timeout=timeout/1000.)   # note: timeout in seconds, not milliseconds.
    time_sweep_start = now()
    time_sleeping = 0.

    # Main loop over pings.
    results = []
    for k in range(count_send):
        if k > 0:
            # Little pause between sending packets.  Try to be a little nice.
            time.sleep(time_pause / 1000.)   # sleep in seconds, not milliseconds.

        res = ping_once(sock, data_size=data_size)
        results.append(res)


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

    data_size = results[0]['data_size']

    # Compute some statistics about the recorded times.
    # P = [0.00, 0.25, 0.50, 1.00]
    # P_times = percentile(times, P)

    # Subtract minimum time from later values.
    # for k in range(1, len(P_times)):
    #     P_times[k] -= P_times[0]

    stats = {'host_name': host_name,
             'data_size': data_size,
             'times': times,
             'timeout': res['timeout'],
             'time_pause': time_pause,
             # 'P': P,
             # 'P_times': P_times,
             'count_send': count_send,
             'count_timeout': count_timeout,
             'count_corrupt': count_corrupt,
             'count_lost': count_lost}

    # Done.
    return stats



def ping_sweep(host_name, timeout=None, size_sweep=None, time_pause=None, count_send=None, verbosity=False):
    """
    Perform a sequence of pings over a range of payload sizes.
    """
    if not size_sweep:
        size_sweep = [32, 128, 512, 2048]

    stats_sweep = []
    for s in size_sweep:
        stats = ping_repeat(host_name, data_size=s,
                            timeout=timeout,
                            time_pause=time_pause,
                            count_send=count_send)
        stats_sweep.append(stats)

        if verbosity:
            if len(stats_sweep) == 1:
                display_results_header(stats)
            display_results_line(stats)

    # Done.
    return stats_sweep

#################################################


def display_results_header(stats):
    """
    Nice results display.
    """

    # Print.
    print()
    print(' Ping Sweep')
    print(' ==========')
    print(' target name: %s' % stats['host_name'])
    print(' ping count:  %d' % stats['count_send'])
    print(' timeout:     %d ms' % stats['timeout'])
    print(' pause time:  %d ms' % stats['time_pause'])
    print()

    # Percentiles.
    P = stats['P']

    # Header strings.
    head_top = ' Payload |  Min. | Percentile Delta (ms) | Lost'
    head_bot = ' (bytes) |  (ms) |  %4.2f   %4.2f   %4.2f   | All  T   C '
    head_bot = head_bot % tuple(P[1:])

    print(head_top)
    print(head_bot)

    div = ' ' + '-' * (len(head_bot)-1)
    print(div)

    # Done.


def display_results_line(stats):
    """
    Generate line of text for current set of results.
    """
    # Line output.
    template = ' %5d   |%6.2f |%6.2f %6.2f %6.2f   |%3d %3d %3d'

    num_bytes = stats['data_size']

    P_times = stats['P_times']
    val = [num_bytes]
    for p in P_times:
        val.append(p*1000.)

    val.append(stats['count_lost'])
    val.append(stats['count_timeout'])
    val.append(stats['count_corrupt'])
    val = tuple(val)

    print(template % val)

    # Done.

#################################################


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

    args = parser.parse_args()

    # Should this argument also be handled by argparse??
    size_sweep = [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
    # # size_sweep = [2048, 4090, 4093, 4096, 4099, 4102]
    # # size_sweep = [16, 32, 64, 128, 256, 512, 1024, 2048, 8192, 16384, 32768]

    # This only runs with elevated privileges.
    if is_admin():
        # Ok good.  Run the application: sequence of pings over a range of packet sizes.
        stats_sweep = ping_sweep(args.host_name,
                                 size_sweep=size_sweep,
                                 count_send=args.count,
                                 time_pause=args.pause,
                                 timeout=args.timeout,
                                 verbosity=True)
    else:
        raise Exception('This application requires admin privileges.')

    # Done.



if __name__ == '__main__':
    main()
