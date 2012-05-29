
I wrote this application to help diagnose some odd network connectivity problems on my home network.
The basic idea is to ping to a remote host with increasingly larger packets.  As of right now, the 
packet sizes start at 16 bytes and increase by factors of two up 32 bytes.

Note: This module relies upon the use of raw sockets.  You will need to run with elevated administrator
permissions on Windows.  I'm not sure about Linux.
 
Summary results are generated for various percentiles of the ping times and number of packets lost.
Packets are considered lost for two reasons: socket timeout or corrupted payload on the echo packet.

This application relies upon the dpkt python package (http://code.google.com/p/dpkt/).
It is included here as a subfolder.

Initial inspiration came from various sources:
http://www.doughellmann.com/PyMOTW/asyncore/
http://www.commercialventvac.com/dpkt.html
http://jon.oberheide.org/blog/2008/08/25/dpkt-tutorial-1-icmp-echo/
http://www.python-forum.de/viewtopic.php?p=183720
http://code.activestate.com/recipes/576662/

In the end I implemented this framework on my own to meet the needs of my particular problems while
diagnosing my home network LAN.


Here is an example of the text output when I target my PC upstairs where I suspect problems with my
ethernet cables in the closet:

C:\Projects\ping_sweep> .\ping_sweep.py shrike

 Ping Sweep
 ==========
 target name: shrike
 ping count:  25
 timeout:     1000 ms
 pause time:  5 ms

 Payload |  Min. | Percentile Delta (ms) | Lost
 (bytes) |  (ms) |  0.25   0.50   1.00   | All  T   C
 -----------------------------------------------------
     8   |  0.95 |  0.12   0.16   4.42   |  0   0   0
    16   |  0.99 |  0.02   0.06   1.84   |  0   0   0
    32   |  1.01 |  0.05   0.08   2.09   |  0   0   0
    64   |  1.03 |  0.06   0.07  10.05   |  0   0   0
   128   |  1.09 |  0.05   0.09   2.85   |  0   0   0
   256   |  1.19 |  0.04   0.09   5.47   |  0   0   0
   512   |  1.39 |  0.09   0.14   2.80   |  1   1   0
  1024   |  1.80 |  0.09   0.15   2.68   |  1   1   0
  2048   |  2.48 |  0.22   0.36   2.36   |  1   1   0
  4096   |  3.51 |  0.25   0.46   4.98   |  0   0   0
  8192   |  6.38 |  0.25   0.73   3.42   | 10  10   0
 16384   | 10.59 |  1.08   1.82  10.66   | 15  15   0
 32768   | 19.52 |  0.68   2.14   4.26   | 17  17   0

 
 
Next here below is a nice result where I target my WiFi router to which I am directly connected
now on my laptop.  There are still the occasional delayed packets, but not as many as above,
and all packets made the round trip just fine.
 
C:\Projects\ping_sweep> .\ping_sweep.py 192.168.1.254

 Ping Sweep
 ==========
 target name: 192.168.1.254
 ping count:  25
 timeout:     1000 ms
 pause time:  5 ms

 Payload |  Min. | Percentile Delta (ms) | Lost
 (bytes) |  (ms) |  0.25   0.50   1.00   | All  T   C
 -----------------------------------------------------
     8   |  0.93 |  0.09   0.19   2.00   |  0   0   0
    16   |  0.95 |  0.08   0.36   1.34   |  0   0   0
    32   |  0.95 |  0.06   0.22   1.85   |  0   0   0
    64   |  0.98 |  0.11   0.28  10.84   |  0   0   0
   128   |  0.99 |  0.07   0.12   1.87   |  0   0   0
   256   |  1.04 |  0.09   0.20   2.26   |  0   0   0
   512   |  1.11 |  0.14   0.28   2.34   |  0   0   0
  1024   |  1.17 |  0.20   0.25   1.45   |  0   0   0
  2048   |  1.92 |  0.42   0.55   1.58   |  0   0   0
  4096   |  2.99 |  0.24   0.55   1.76   |  0   0   0
  8192   |  5.34 |  0.54   1.13   4.07   |  0   0   0
 16384   | 10.38 |  0.72   2.30  16.43   |  0   0   0
 32768   | 20.63 |  1.44   2.35   6.51   |  0   0   0

 
 