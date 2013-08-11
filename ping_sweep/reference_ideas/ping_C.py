#!/usr/bin/env python

"""
A pure python ping implementation using raw socket.

Note that ICMP messages can only be sent from processes running as root.

Derived from ping.c distributed in Linux's netkit. That code is
copyright (c) 1989 by The Regents of the University of California.
That code is in turn derived from code written by Mike Muuss of the
US Army Ballistic Research Laboratory in December, 1983 and
placed in the public domain. They have my thanks.

Bugs are naturally mine. I'd be glad to hear about them. There are
certainly word - size dependenceies here.

Copyright (c) Matthew Dixon Cowles, <http://www.visi.com/~mdc/>.
Distributable under the terms of the GNU General Public License
version 2. Provided with no warranties of any sort.

Original Version from Matthew Dixon Cowles:
-> ftp://ftp.visi.com/users/mdc/ping.py

Rewrite by Jens Diemer:
-> http://www.python-forum.de/post-69122.html#69122

Rewrite by George Notaras:
-> http://www.g-loaded.eu/2009/10/30/python-ping/

Revision history
~~~~~~~~~~~~~~~~

December 18, 2009
-----------------
awolfson@amperion.com
amperion.com
Alex Wolfson:

Added tracking of duplicate ICMPs
Added sending multiple pings from a thread scheduled with defined interval.
Added printing histogram
Added command line options

November 8, 2009
----------------
Improved compatibility with GNU/Linux systems.

Fixes by:
* George Notaras -- http://www.g-loaded.eu
Reported by:
* Chris Hallman -- http://cdhallman.blogspot.com

Changes in this release:
- Re-use time.time() instead of time.clock(). The 2007 implementation
worked only under Microsoft Windows. Failed on GNU/Linux.
time.clock() behaves differently under the two OSes[1].

[1] http://docs.python.org/library/time.html#time.clock

May 30, 2007
------------
little rewrite by Jens Diemer:
- change socket asterisk import to a normal import
- replace time.time() with time.clock()
- delete "return None" (or change to "return" only)
- in checksum() rename "str" to "source_string"

November 22, 1997
-----------------
Initial hack. Doesn't do much, but rather than try to guess
what features I (or others) will want in the future, I've only
put in what I need now.

December 16, 1997
-----------------
For some reason, the checksum bytes are in the wrong order when
this is run under Solaris 2.X for SPARC but it works right under
Linux x86. Since I don't know just what's wrong, I'll swap the
bytes always and then do an htons().

December 4, 2000
----------------
Changed the struct.pack() calls to pack the checksum and ID as
unsigned. My thanks to Jerome Poincheval for the fix.

Last commit info:
~~~~~~~~~~~~~~~~~
$LastChangedDate: $
$Rev: $
$Author: $

IP Header

bit offset 0-3 4-7 8-15 16-18 19-31
0 Version Header length Differentiated Services Total Length
32 Identification Flags Fragment Offset
64 Time to Live Protocol Header Checksum
96 Source Address
128 Destination Address
160 Options/Data

RFC792, echo/reply message:

0 1 2 3
0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Type | Code | Checksum |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Identifier | Sequence Number |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Data ...
+-+-+-+-+-

"""

import os, sys, socket, struct, select, time, threading, traceback
import collections

from optparse import OptionParser
#import pprint
#pp = pprint.PrettyPrinter(indent=4)

#from multiprocessing import Process
# From /usr/include/linux/icmp.h; your milage may vary.
ICMP_ECHO_REQUEST = 8 # Seems to be the same on Solaris.

'''
sentPings -> sequence:time
records are created during the send and delited during the receive
printStat() deletes records that are timed out
'''
sentPings = {}
statLock = threading.Lock()
class pingStatistics:
def reset(self):
self.starttime = time.time()
self.transmitted = 0
self.received = 0
self.duplicated = 0
self.missed = 0
self.pending = 0
self.min = 10000.0
self.max = 0.0
self.totaltime = 0.0
self.exceedmaxtime = 0
self.lastPrinttime = time.time()
if hasattr(self, 'hist'):
self.hist = [0 for h in self.hist]
def __init__(self, dest_addr, points):
self.reset()
self.dest_addr = dest_addr
self.points = points
self.hist = [0] * (len(self.points)+1)
# self.printafter = 10
def updateStat(self, val):
'''
update a histogram with val
points is a sorted list
@return: new histogram
'''
# statLock.acquire()
valms = val * 1000
i = 0
for p in self.points:
if valms >= p:
i += 1
else:
break
self.hist[i] += 1
self.totaltime += val
self.received += 1
if self.min > val:
self.min = val
if self.max < val:
self.max = val
# statLock.release()
def printHist(self):
for h in self.hist:
print "%10d" % (h),
print "\n" + " "*7,
for p in self.points:
print "%10.3f" % (p),
print "\n"
def printStat(self):
print "---- " + self.dest_addr + " ping statistics ----"
statLock.acquire()
currentTime = time.time()
pending = 0
# print sentPings
pings = sentPings.keys()
for seq in pings:
tm = sentPings[seq]
if (currentTime - tm > options.timeout) and tm > self.starttime:
# print 'before print del %d'%seq
del sentPings[seq]
# print 'after print del %d'%seq
self.missed += 1
else:
pending += 1
# print 'after for loop'
statLock.release()
print "time = %f sec, %d transmitted, %d received, %d duplicated, %d missed, %d pending, %f min, %f max %d exceed %f ms, " \
% (time.time() - self.starttime, self.transmitted, self.received, self.duplicated, self.missed, pending, self.min * 1000.0, self.max * 1000.0, self.exceedmaxtime , options.maxtime * 1000),
if self.received != 0:
print "%f average" % (self.totaltime / self.received * 1000.0)
else:
print ""

self.printHist()
self.lastPrinttime=currentTime

#global statistics, movingstat, continue_receive, statLock

continue_receive = True

# From http://code.activestate.com/recipes/142812/
FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])
def dump2(src, length=8):
result=[]
for i in xrange(0, len(src), length):
s = src[i:i+length]
hexa = ' '.join(["%02X"%ord(x) for x in s])
printable = s.translate(FILTER)
result.append("%04X %-*s %s\n" % (i, length*3, hexa, printable))
return ''.join(result)

def checksum(source_string):
"""
I'm not too confident that this is right but testing seems
to suggest that it gives the same answers as in_cksum in ping.c
"""
sum = 0
countTo = (len(source_string)/2)*2
count = 0
while count<countTo:
thisVal = ord(source_string[count + 1])*256 + ord(source_string[count])
sum = sum + thisVal
sum = sum & 0xffffffff # Necessary?
count = count + 2

if countTo<len(source_string):
sum = sum + ord(source_string[len(source_string) - 1])
sum = sum & 0xffffffff # Necessary?

sum = (sum >> 16) + (sum & 0xffff)
sum = sum + (sum >> 16)
answer = ~sum
answer = answer & 0xffff

# Swap bytes. Bugger me if I know why.
answer = answer >> 8 | (answer << 8 & 0xff00)

return answer
def send_one_ping(my_socket, dest_addr, ID, size):
"""
Send one ping to the given >dest_addr<.
"""
dest_addr = socket.gethostbyname(dest_addr)

# Header is type (8), code (8), checksum (16), id (16), sequence (16)
my_checksum = 0
seqH = statistics.transmitted & 0xffff # sequence has signed short format
# Make a dummy header with a 0 checksum.
header = struct.pack("!bbHHH", ICMP_ECHO_REQUEST, 0, my_checksum, ID, seqH)
bytesInDouble = struct.calcsize("d")
data = (size - bytesInDouble) * "Q"
timeSent = time.time()
data = struct.pack("d", timeSent) + data

# Calculate the checksum on the data and the dummy header.
my_checksum = checksum(header + data)

# Now that we have the right checksum, we put that in. It's just easier
# to make up a new header than to stuff it into the dummy.
header = struct.pack(
"!bbHHH", ICMP_ECHO_REQUEST, 0, my_checksum, ID, seqH
)
packet = header + data
sentPings[seqH] = timeSent
my_socket.sendto(packet, (dest_addr, 1)) # 1 is a port number
statistics.transmitted += 1
movingstat.transmitted += 1
#DEBUG
#if options.verbose > 1:
# print "at %f sent seq=%u" % (timeSent, seqH)

def verbose_receive_one_ping(my_socket, ID, timeout):
"""
receive the ping from the socket.
update statistics
"""
global statLock
timeLeft = timeout
while True:
startedSelect = time.time()
whatReady = select.select([my_socket], [], [], timeLeft)
howLongInSelect = (time.time() - startedSelect)
if whatReady[0] == []: # Timeout
return
timeReceived = time.time()
recPacket, addr = my_socket.recvfrom(2048) #TODO: find a better way to specify size.
icmpHeader = recPacket[20:28]
type, code, checksum, packetID, sequence = struct.unpack(
"!bbHHH", icmpHeader
)
if options.verbose > 2:
print 'recPacket (len = %d)\n' % (len(recPacket)), dump2(recPacket)
if packetID == ID:
if type != 0: #not a reply msg
print "Got not a 'reply' msg: type %d, code %d\n" % (type, code)
continue
bytesInDouble = struct.calcsize("d")
timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
# TODO:update statistic
rtt = timeReceived - timeSent
if options.verbose > 1:
print "at %f received %d bytes from %s: time=%.3f, seq=%u, rtt=%.3f ms" % (timeReceived, len(recPacket),
addr, timeSent - statistics.starttime, sequence, rtt*1000),
statLock.acquire()
if sequence in sentPings:
#print 'receive del'
del sentPings[sequence]
statistics.updateStat(rtt)
movingstat.updateStat(rtt)
if rtt > options.maxtime:
statistics.exceedmaxtime += 1
movingstat.exceedmaxtime += 1
if options.verbose > 1:
print ""
statLock.release()
return rtt
else: # Duplicate ICMP
if options.verbose > 1:
print " (DUP)"
statistics.duplicated += 1
movingstat.duplicated += 1
statLock.release()
return -1
statLock.release()
timeLeft = timeLeft - howLongInSelect
if timeLeft <= 0:
if options.verbose > 1:
print "nothing received in %f sec\n" % (timeout)
# statistics.missed += 1
return

def receive_loop(my_socket, my_ID, timeout):
''' This is a thread routine'''
while continue_receive:
verbose_receive_one_ping(my_socket, my_ID, timeout)

def ping_with_stat(my_socket, dest_addr, my_ID, size, interval, timeout):
send_one_ping(my_socket, dest_addr, my_ID, size)
time.sleep(interval)

def do_many(dest_addr, interval = 1.0, timeout = 1.0, count = 1, size = 56):
"""
sends packets in a main loop with delays.
receive packets from the thread
This allows send packets independently of receiving
Returns either the delay (in seconds) or none on timeout.
"""
global statistics, movingstat
movingstat.reset()
statistics.reset()
icmp = socket.getprotobyname("icmp")
try:
# my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
except socket.error, (errno, msg):
if errno == 1:
# Operation not permitted
msg = msg + (
" - Note that ICMP messages can only be sent from processes"
" running as root."
)
raise socket.error(msg)
raise # raise the original error
my_ID = os.getpid() & 0xFFFF
receiveThread = threading.Thread(target = receive_loop, args = (my_socket, my_ID, timeout))
receiveThread.start()
if count == -1:
i=0
while 1:
if not receiveThread.isAlive():
break
i = i + 1
ping_with_stat(my_socket, dest_addr, my_ID, size, interval, timeout)
if time.time() - movingstat.lastPrinttime >= options.printinterval:
if options.verbose > 0:
movingstat.printStat()
movingstat.reset()
statistics.printStat()
else:
for i in xrange(1, count+1):
if not receiveThread.isAlive():
break
ping_with_stat(my_socket, dest_addr, my_ID, size, interval, timeout)
if time.time() - movingstat.lastPrinttime >= options.printinterval:
if options.verbose > 0:
movingstat.printStat()
movingstat.reset()
statistics.printStat()
continue_receive = False
time.sleep(timeout) # to be sure that all sent pings are processed
receiveThread.join(timeout)
statistics.printStat()
my_socket.close()

#=================================================================

if __name__ == '__main__':
try:
usage = "%prog [options]IP\n %prog -h for more inormation"
parser = OptionParser()
parser.usage = usage
parser.add_option("-c", "--count", dest="count", type='int', help="number of pings. -1: infinity, default=%default", default=-1)
parser.add_option("-i", "--interval", dest="interval", type='float', help="ping interval in sec, default = %default", default = 1.0)
parser.add_option("-t", "--timeout", dest="timeout", type='float', help="ping timeout in sec, default = %default", default = 1.0)
parser.add_option("-p", "--printinterval", dest="printinterval", type='float', help="statistics print interval in sec, default = %default", default = 5.0)
parser.add_option("-s", "--size", dest="size", type='int', help="payload size, default = %default", default = 56)
parser.add_option("-m", "--maxtime", dest="maxtime", type='float', help="numer of ping greater then maxtime sec, default = %default", default = 0.025)
# parser.add_option("-d", "--histdim", dest="histdim", type='int', help="payload size, default = %default", default = 56)
parser.add_option("-g", "--hist", dest="hist", type='float', nargs = 11, help="histogram points, default = %default", default = (5.0, 10.0, 15, 20.0, 30.0, 40.0, 50.0, 100, 200, 300, 500))
parser.add_option("-v", "--verbose", dest="verbose", type='int', help="0: only final stat; 1: final and intermediate stat; \n2: 1 + individual packets, default=%default; 3: 2 + receive packet dump", default=2)
(options, args) = parser.parse_args()
if args == []:
parser.error('Provide Target IP')
targetIP = args[0]
statistics = pingStatistics(targetIP, options.hist)
movingstat = pingStatistics(targetIP, options.hist)
#movingstat.printafter = int(options.printinterval / options.interval)
#if movingstat.printafter < 1: movingstat.printafter = 1
do_many(targetIP, interval = options.interval, timeout = options.timeout, count = options.count, size = options.size)
except ( KeyboardInterrupt):
print
statistics.printStat()
sys.exit(0)
except:
traceback.print_exc()
#raise
finally:
sys.exit(1)
