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

from __future__ import division, print_function #, unicode_literals

import sys
import time
import socket
import random

import dpkt
import pvlib # used only for the percentile function imported from Scipy.

# TODO: factor out dependenciies on pvlib.


# Helper functions.
def percentile(data, P):

    return pvlib.stats.percentile(data, P)


def now():
    """
    Return current time, platform dependent.
    """
    if os.sys.platform == 'win32':
        return time.clock()  # best for windows?  seems to give finer temporal resolution.
    else:
        return time.time()  # best for Unix, others???



def create_packet(id, seq, data_size):
    """
    Create a data packet represented as a string.
    """

    # Random sequence of characters.
    payload = ''
    for k in range(data_size):
        payload += chr(random.randint(65, 65+25))

    # Create ICMP echo packet.
    echo = dpkt.icmp.ICMP.Echo()
    echo.id = id
    echo.seq = seq
    echo.data = payload

    icmp = dpkt.icmp.ICMP()
    icmp.type = dpkt.icmp.ICMP_ECHO
    icmp.data = echo

    # Return data packet as string representation.
    packet = str(icmp)

    # Done.
    return (payload, packet)



def create_socket(host_name, timeout=None):
    """
    Make the socket and connect to remote host.
    timeout: seconds
    """
    if timeout is None:
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



def ping_once(sock, data_size=32, id=1):
    """
    One ping, just one ping.
    """

    seq = 1999 # not really used here, but the TV show Space 1999! was pretty awesome when I was a kid.

    payload, packet = create_packet(id, seq, data_size)

    try:
        # Send it, record the time.
        sock.sendall(packet)
        time_send = now()

        # Receive response, record time.
        msg_recv = sock.recv(0xffff)
        time_recv = now()

        # Extract packet data.
        ip = dpkt.ip.IP(msg_recv)

        # Process results.
        is_same_data = (payload == ip.icmp.echo.data)
        time_ping = (time_recv - time_send)
        echo_id = ip.icmp.echo.id

    except socket.timeout:
        is_same_data = False
        time_ping = None
        echo_id = None

    # Done.
    result = {'time_ping':time_ping,
              'data_size':data_size,
              'is_same_data':is_same_data,
              'id':id,
              'echo_id':echo_id}

    return result



def ping_repeat(host_name, data_size=64, time_pause=25., count_send=10, timeout=None):
    """
    Ping remote host.  Repeat for better statistics.

    data_size: size of payload in bytes.
    count_send: number of ping repetitions.
    time_pause: milliseconds between repetitions.
    timeout: socket timeout period, seconds.
    """

    # Make a socket, send a sequence of pings.
    sock = create_socket(host_name, timeout=timeout)
    time_sweep_start = now()
    time_sleeping = 0.
    results = []
    for k in range(count_send):
        if k > 0:
            # Little pause between sending packets.  Try to be a little nice.
            time_mark = now()
            time.sleep(time_pause / 1000.)  # sleep in seconds, not milliseconds.
            time_sleeping += (now() - time_mark)

        res = ping_once(sock, data_size=data_size)
        results.append(res)

    time_sweep_end = now()

    # Process results.
    count_timeout = 0
    count_corrupt = 0

    times = []
    for res in results:
        if res['is_same_data']:
            times.append(res['time_ping'])
        else:
            if res['time_ping'] is None:
                # Packet was lost because of timeout.  Most likely cause.
                count_timeout += 1
            else:
                # Packet is considered lost since returned payload did match original.
                count_corrupt += 1



    count_lost = count_timeout + count_corrupt
    count_recv = count_send - count_lost

    # num_packets = len(times)
    data_size = results[0]['data_size']

    # debugging.
    print(data_size)

    rate = count_recv * data_size / (time_sweep_end - time_sweep_start - time_sleeping) / 1024.

    P = [0.00, 0.25, 0.50, 0.75, 1.00]
    P_times = percentile(times, P)

    stats = {'host_name':host_name,
             'data_size':data_size,
             'rate':rate,
             'times':times,
             'P':P,
             'P_times':P_times,
             'count_send':count_send,
             'count_timeout':count_timeout,
             'count_corrupt':count_corrupt,
             'count_lost':count_lost}

    # Done.
    return stats



def ping_sweep(host_name, size_sweep=None, time_pause=25, count_send=10):
    """
    Perform a sequence of pings over a range of payload sizes.
    """
    if size_sweep is None:
        # size_sweep = [32, 64, 128] # basic
        size_sweep = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
        # size_sweep = [2048, 4090, 4093, 4096, 4099, 4102]
        # size_sweep = [16, 32, 64, 128, 256, 512, 1024, 2048, 8192, 16384, 32768]

    stats_sweep = []
    for s in size_sweep:
        stats = ping_repeat(host_name, data_size=s, time_pause=time_pause, count_send=count_send)
        stats_sweep.append(stats)

    # Done.
    return stats_sweep



def pretty_results(stats_sweep):
    """
    Nice results display.
    """

    # Print.
    print('\n\n Ping sweep target: %s' % stats_sweep[0]['host_name'])
    print(' count_send=%d\n' % stats_sweep[0]['count_send'])

    # Percentiles.
    P = stats_sweep[0]['P']

    # Header.
    head = '  size '
    for p in P:
        head += '   %4.2f' % p
    head += '   Lost TO  Crpt  Rate'

    print(head)
    div = ' ' + '-' * (len(head)-1)
    print(div)

    # Line output.
    template = ' %5d '
    for p in P:
        template += ' %6.2f'

    template += '   %3d %3d %3d   %5.1f'

    for stats in stats_sweep:
        num_bytes = stats['data_size']

        P_times = stats['P_times']
        val = [num_bytes]
        for p in P_times:
            val.append(p*1000.)

        val.append(stats['count_lost'])
        val.append(stats['count_timeout'])
        val.append(stats['count_corrupt'])
        val.append(stats['rate'])
        val = tuple(val)

        print(template % val)




if __name__ == '__main__':
    # Example useage.

    if len(sys.argv) > 1:
        host_name = sys.argv[1]
    else:
        # host_name = 'www.google.com'
        host_name = '192.168.1.254'
        # host_name = 'shrike'
        # host_name = 'vulture'
        # host_name = 'purple-martin'


    #
    # Sequence of pings over range of packet sizes.
    #
    stats_sweep = ping_sweep(host_name, count_send=25, time_pause=5.)


    pretty_results(stats_sweep)

