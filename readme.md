
Ping Sweep
==========

What and Why
------------

I wrote this application to help diagnose some odd network connectivity problems on my home
network.  The basic idea is to ping to a remote host with increasingly larger packets.  As
of right now, the packet sizes start at 32 bytes and increase by factors of two.  Summary
results are generated for various percentiles of the ping times and number of packets lost.
Packets are considered lost for two reasons: socket timeout or corrupted payload on the echo
packet.

This application relies upon the dpkt python package (http://code.google.com/p/dpkt/).  It is
included here as a subfolder.  Finally, this module relies upon the use of raw sockets.  You will
need to run with elevated administrator permissions on Windows.  On Linux simply run this tool
using 'sudo'.

Initial inspiration for this tool came from various sources:
- http://www.doughellmann.com/PyMOTW/asyncore/
- http://www.commercialventvac.com/dpkt.html
- http://jon.oberheide.org/blog/2008/08/25/dpkt-tutorial-1-icmp-echo/
- http://www.python-forum.de/viewtopic.php?p=183720
- http://code.activestate.com/recipes/576662/

In the end I implemented my very own framework instead of copying one of those above.  It was fun
to learn something new about working with sockets.


Examples
--------

Here is an example of the text output when I target my PC upstairs where I suspected problems
with my ethernet cables in the closet:

     C:\Projects\ping_sweep> .\ping_sweep.py 192.168.1.29

     Ping Sweep
     ==========
     target name: 192.168.1.29
     ping count:  100
     timeout:     1000 ms
     pause time:  5 ms

      Size (bytes)  |       Ping Times (ms)         | Lost Packets
     Payload Packet |  min    avg    [std]     max  | All  T   C
     ------------------------------------------------------------
        32     40   | 80.59  98.94 [ 20.64]  162.95 |  1   1   0
        64     72   | 80.70  98.54 [ 23.29]  166.97 |  0   0   0
       128    136   | 81.16  91.79 [ 17.75]  170.88 |  0   0   0
       256    264   | 81.98  86.49 [  5.74]  121.32 |  0   0   0
       512    520   | 82.21  95.20 [ 28.57]  252.61 |  0   0   0
      1024   1032   | 84.19 101.15 [ 24.22]  173.09 |  1   1   0
      1472   1480   | 87.31  97.93 [  5.54]  120.48 |  0   0   0


Next below is a nice result where I target my WiFi router to which I am directly connected
now on my laptop.  There are still the occasional delayed packets, but not as many as above,
and all packets made the round trip just fine.

     C:\Projects\ping_sweep> .\ping_sweep.py 192.168.1.254

     Ping Sweep
     ==========
     target name: 192.168.1.254
     ping count:  100
     timeout:     1000 ms
     pause time:  5 ms

     Payload Packet |  min    avg    [std]     max  | All  T   C
      Size (bytes)  |       Ping Times (ms)         | Lost Packets
     ------------------------------------------------------------
        32     40   |  0.38   0.53 [  1.09]   11.35 |  0   0   0
        64     72   |  0.38   0.57 [  1.48]   15.29 |  0   0   0
       128    136   |  0.39   0.43 [  0.07]    0.85 |  0   0   0
       256    264   |  0.40   0.60 [  1.49]   15.43 |  0   0   0
       512    520   |  0.40   0.74 [  2.68]   27.44 |  0   0   0
      1024   1032   |  0.49   0.72 [  1.65]   17.12 |  0   0   0
      1472   1480   |  0.52   0.72 [  1.57]   16.31 |  0   0   0
