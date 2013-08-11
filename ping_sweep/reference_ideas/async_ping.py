#!/usr/bin/env python

"""
A pure Python ping implementation using raw socket.
Note that ICMP messages can only be sent from processes running as root.
"""

from __future__ import division, print_function #, unicode_literals

import dpkt
import time
import socket
import asyncore
import sys


class AsyncPing(asyncore.dispatcher):
    def __init__(self, host_name, id=None, seq=None, data_size=None, timeout=None):
        """
        Derived class from "asyncore.dispatcher" for sending and receiving an ICMP
        echo request/reply.  This class is generally used in conjunction with method
        asyncore.loop().  Once the loop is over, retrieve results with the "get_result" method.

        host_name: target name or IP address.
        id: 2-byte integer.  Must be unique across a work session.
        """
        asyncore.dispatcher.__init__(self)

        if id is None:
            id = 1999

        if seq is None:
            seq = 1

        if data_size is None:
            data_size = 32

        if timeout is None:
            timeout = 1.0

        self.ping_sent = False
        self.timeout = timeout
        self.buffer_read = ''
        self.data_echo_send = None
        self.time_connect = None
        self.time_close = None
        self.data_size = data_size
        
        # Create socket.
        self.create_socket(socket.AF_INET, socket.SOCK_RAW, dpkt.ip.IP_PROTO_ICMP)

        # Connect to remote host.
        host_addr = socket.gethostbyname(host_name)
        port = 1  # dummy value
        self.connect( (host_addr, port) )

        # Create outgoing data packet, store in string buffer.
        self.buffer_write = self.create_packet(id, seq, data_size)


    def create_packet(self, id, seq, data_size):
        """
        Create a data packet represented as a string.
        """

        # Create ICMP echo packet.
        echo = dpkt.icmp.ICMP.Echo()
        echo.id = id
        echo.seq = seq

        self.data_echo_send = 'V'*data_size   # payload is a repeated character sequence.
        echo.data = self.data_echo_send

        icmp = dpkt.icmp.ICMP()
        icmp.type = dpkt.icmp.ICMP_ECHO
        icmp.data = echo

        # Convert to string representation.
        data = str(icmp)

        # Done.
        return data


    def create_socket(self, family, type, proto):
        """
        Overwride the original since it does not support "proto" argument.
        """

        sock = socket.socket(family, type, proto)
        sock.setblocking(0)
        sock.settimeout(self.timeout)

        self.set_socket(sock)

        # Part of the original but is not used. (at least at python 2.7)
        # Copied for possible compatiblity reasons.
        self.family_and_type = family, type  # PVV --> ?


    # def handle_connect(self):
        # pass


    def handle_close(self):
        self.close()
        self.time_close = self.now()

        self.post_process()
        

    def writable(self):
        """
        Writeable so long as there is data to be sent.
        """
        is_writable = (len(self.buffer_write) > 0)
        # print('writable %s' % is_writable)

        return is_writable


    def readable(self):
        """
        Readable only after ping has been sent, at least until timeout.
        """
        is_readable = False

        if self.ping_sent:
            if self.now() - self.time_connect <= self.timeout:
                # Ok.
                is_readable = True
            else:
                # Sorry, timeout.
                is_readable = False
                self.handle_close()

        # print('readable %s' % is_readable)
        return is_readable


    def handle_write(self):
        # Send some data, update outgoing buffer accordingly.
        if self.time_connect is None:
            self.time_connect = self.now()
            self.ping_sent = True

        sent = self.send(self.buffer_write)
        self.buffer_write = self.buffer_write[sent:]

        # print('handle_write: %s' % sent)


    def handle_read(self):
        # Append new data to string buffer.
        msg = self.recv(0xffff)

        self.buffer_read = msg

        # Only one read necesary for this application (ping).  Close connection.
        self.handle_close()

        # print('handle_read: %s' % len(msg))


    def now(self):
        """
        Return current time.  This method should be platform dependent.
        Current implmentation is ideal for Windows.
        """
        return time.clock()  # best for windows
        # # return time.time()  # best for Unix


    def post_process(self):
        """
        Process results.
        """
        time_ping = (self.time_close - self.time_connect) * 1000.

        # Unpack packet data.
        if len(self.buffer_read) > 0:
            ip = dpkt.ip.IP(self.buffer_read)

            # Store results.
            self.is_same_data = (self.data_echo_send == ip.icmp.echo.data)
            self.time_ping = time_ping
            self.id = ip.icmp.echo.id
            self.seq = ip.icmp.echo.seq
            self.icmp = ip.icmp
        else:
            self.is_same_data = False
            self.time_ping = None
            self.id = None
            self.seq = None
            self.icmp = None
            

def ping_single(host_name, data_size=None, verbosity=1):
    """
    Ping example to a single remote host.
    """

    sock = AsyncPing(host_name, data_size=data_size)

    timeout = 0.1  # I think this number should be small: 10 - 50 ms???
    asyncore.loop(timeout)

    result = sock.extract()

    if result is not None:
        time_ping, is_same_data, id, seq, ip = result
    else:
        time_ping = None
        is_same_data = False

    if verbosity:
        print()
        print('Host: %s, time: %.1f ms' % (host_name, time_ping))
        
    # Done.
    return time_ping
    
    

def ping_multi(host_name, verbosity=1):
    """
    Ping example to a single remote host.
    """

    timeout = 0.01  # seconds.  default = 30
    # I think this number should be small: 10 - 50 ms???

    # Setup the sockets.
    powers = range(8)
    # powers = [6]*5

    socks = []
    id = 0
    for p in powers:
        id += 1
        size = 2**p
        
        s = AsyncPing(host_name, id=id, data_size=size)
        socks.append(s)
        
    # Start the event loop.
    asyncore.loop(timeout)

    # Extract results.
    for s in socks:
        print(s.data_size, s.time_ping)





if __name__ == '__main__':
    # Example useage.

    if len(sys.argv) > 1:
        host_name = sys.argv[1]
    else:
        # host_name = 'www.google.com'
        host_name = '192.168.1.254'
        
    
    # size = 1024
    # time = ping_single(host_name, data_size=size, verbosity=True)

    ping_multi(host_name)
    