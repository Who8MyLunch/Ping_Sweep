
I wrote this application to help diagnose some odd network connectivity problems on my home network.
The basic idea is to ping to a remote host with increasingly larger packets.  As of right now, the 
packet sizes start at 16 bytes and increase by factors of two up 32 bytes.
 
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

C:\Projects\ping_sweep> python .\ping_sweep.py shrike

 Ping Sweep
 ==========
 target name:  shrike
 ping count:   25
 sock timeout: 1000 ms
 pause time:   5 ms

  Packet   Percentile Times (ms)               Lost Packets
   Size    0.00   0.25   0.50   0.75   1.00    All [ T / C ]
 -----------------------------------------------------------
     8     0.93   0.98   1.01   1.14   2.67     2    2   0
    16     0.96   1.07   1.14   1.29   2.59     1    1   0
    32     0.90   1.06   1.14   1.49  12.62     1    1   0
    64     0.99   1.07   1.28   1.45   2.07     1    1   0
   128     1.01   1.14   1.31   1.57   9.44     0    0   0
   256     1.18   1.27   1.46   1.84   8.43     2    2   0
   512     1.29   1.39   1.47   1.94   2.69     1    1   0
  1024     1.75   1.81   1.89   2.01   3.94     3    3   0
  2048     2.32   2.49   2.72   2.94   4.11     3    3   0
  4096     3.36   3.73   4.21   5.41   8.10     9    9   0
  8192     6.14   6.51   6.87   7.77  28.51    10   10   0
 16384    10.39  11.94  12.51  14.48  14.96    19   19   0
 32768    21.57  21.57  21.57  21.57  21.57    24   24   0


 
 
Next here below is a nice result where I target my WiFi router to which I am directly connected
now on my laptop.  There are still the occasional delayed packets, but not as many as above,
and all packets made the round trip just fine.
 
C:\Projects\ping_sweep> python .\ping_sweep.py 192.168.1.254

 Ping Sweep
 ==========
 target name:  192.168.1.254
 ping count:   25
 sock timeout: 1000 ms
 pause time:   5 ms

  Packet   Percentile Times (ms)               Lost Packets
   Size    0.00   0.25   0.50   0.75   1.00    All [ T / C ]
 -----------------------------------------------------------
     8     0.90   0.98   1.06   1.13   1.65     0    0   0
    16     0.97   1.02   1.04   1.10   2.09     0    0   0
    32     0.94   1.05   1.10   1.39   8.55     0    0   0
    64     0.95   1.06   1.11   1.27   5.21     0    0   0
   128     1.00   1.07   1.12   1.18   1.79     0    0   0
   256     1.05   1.11   1.18   1.22   1.43     0    0   0
   512     1.13   1.18   1.24   1.54   3.33     0    0   0
  1024     1.27   1.33   1.44   1.71   4.11     0    0   0
  2048     2.02   2.23   2.55   2.85  10.97     0    0   0
  4096     3.04   3.33   3.60   4.50   7.95     0    0   0
  8192     5.54   5.97   6.42   7.16   9.86     0    0   0
 16384    10.11  11.28  11.75  13.10  27.41     0    0   0
 32768    19.60  21.34  22.26  23.56  27.09     0    0   0

 
 