
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
