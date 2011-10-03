#!/usr/bin/env python
#
# gmailboxpopd.py -- POP3 server for GMail-retrieved mbox files
#
# $Revision: 0.9 $ ($Date: 2006/05/21 18:30:00 $)
#
# Author: Adrien Joly <adrien.joly@gmail.com>
#
# Website:
# http://roly.blogsome.com/2006/05/21/gmailbox-mbox-retriever-pop3-server/
#
# License: Dual GPL 2.0 and PSF (This file only.)
#
# Based on smtpd.py by Barry Warsaw <barry@python.org> (Thanks Barry!)
#
## Applied the Debian patch bug report #277310 --SZ--

import sys
import os
import time
import socket
import asyncore
import asynchat

program = sys.argv[0]
__version__ = 'Gmailbox POP3 server version 0.9'

EMPTYSTRING = ''

my_user = ""
snapshot = None # Account snapshot...

class GmailboxSnapshot:
    """
    """

    def __init__(self, user):
        """
        """
        
        mailbox = user + ".mbox"
        print "opening mailbox '%s'..." % mailbox
        f = file(mailbox, "r")
        
        self.unreadMsgs = []
        currentMsg = ""
        
        # ignore the first fake "from" line
        line = f.readline()

        while 1:
            line = f.readline()
            if line == "":
                break
                
            line = line.replace("\r\n", "\n")
            line = line.replace("\n", "\r\n")
                
            if line[:18] == "X-Gmail-Received: ":
                if currentMsg != "":
                    print "parsed message #%i" % len(self.unreadMsgs)
                    self.unreadMsgs.append(currentMsg)
                currentMsg = ""
            currentMsg = currentMsg + line
                
        if currentMsg != "":
            print "parsed message #%i" % len(self.unreadMsgs)
            self.unreadMsgs.append(currentMsg)
            
        print "finished reading mailbox."

    def retrieveMessage(self, msgNumber, bodyLines = None):
        """
        Returns an array of lines...  
        """
        # TODO: Check request is in range...
        msgContent = self.unreadMsgs[msgNumber]

        msgLines = msgContent.split("\r\n")

        if bodyLines is not None:
            blankIndex = msgLines.index("") # Blank line between header & body.
            msgLines = msgLines[:blankIndex + 1 + bodyLines]

        return msgLines       
        
    def getMessageId(self, msgNumber):
        """
        """
        lines = snapshot.retrieveMessage(msgNumber, 1)
        id = lines[0].replace("X-Gmail-Received: ","")
        return id
        

                
class POPChannel(asynchat.async_chat):

    def __init__(self, server, conn, addr):
        asynchat.async_chat.__init__(self, conn)
        self.__server = server
        self.__conn = conn
        self.__addr = addr
        self.__line = []
        self.__fqdn = socket.getfqdn()
        self.__peer = conn.getpeername()
        print 'Peer:', repr(self.__peer)
        self.push('+OK %s %s' % (self.__fqdn, __version__))
        self.set_terminator('\r\n')

        self._activeDataChannel = None
        

    # Overrides base class for convenience
    def push(self, msg):
        if msg == "." or msg[:3] == "+OK" or msg[:4] == "-ERR":
          print msg
        asynchat.async_chat.push(self, msg + '\r\n')

    # Implementation of base class abstract method
    def collect_incoming_data(self, data):
        self.__line.append(data)

    # Implementation of base class abstract method
    def found_terminator(self):
        line = EMPTYSTRING.join(self.__line)
        print 'Data:', repr(line)
        self.__line = []
        if not line:
            self.push('500 Error: bad syntax')
            return
        method = None
        i = line.find(' ')
        if i < 0:
            command = line.upper()
            arg = None
        else:
            command = line[:i].upper()
            arg = line[i+1:].strip()
        method = getattr(self, 'pop_' + command, None)
        if not method:
            self.push('-ERR Error : command "%s" not implemented' % command)
            return
        method(arg)
        return


    def pop_USER(self, arg):
        if not arg:
            self.push('-ERR: Syntax: USER username')
        else:
            global my_user
            my_user = arg
            self.push('+OK Password required')


    def pop_PASS(self, arg = ''):
        """
        """
        try:
            global snapshot
            snapshot = GmailboxSnapshot(my_user)
        except:
            self.push('-ERR Failed opening mailbox')
        else:            
            self.push('+OK User logged in')


    def pop_STAT(self, arg):
        """
        """
        # We define "Mail Drop" as being unread messages.
        # TODO: Handle presenting all messages using read=deleted approach
        #       or would it be better to be read=archived?
        
        # We just use a dummy mail drop size here at present, hope it causes
        # no problems...
        # TODO: Determine actual drop size... (i.e. always download msgs)
        mailDropSize = 1
        
        self.push('+OK %d %d' % (len(snapshot.unreadMsgs), mailDropSize))


    def pop_LIST(self, arg):
        """
        """
        DUMMY_MSG_SIZE = 1 # TODO: Determine actual message size.
        msgCount = len(snapshot.unreadMsgs)
        self.push('+OK')
        if not arg:
            # TODO: Change all of this to operate on an account snapshot?
            for msgIdx in range(1, msgCount + 1):
                self.push('%d %d' % (msgIdx, DUMMY_MSG_SIZE))
        else:
            try:
                arg = int(arg)
            except:
                arg = -1
            if 0 < arg <= msgCount:
                self.push('%d %d' % (arg, DUMMY_MSG_SIZE))
            else:
                self.push("-ERR no such message, only %d messages in maildrop"
                          % msgCount)
        self.push(".")

    def pop_UIDL(self, arg):
        """
        """
        DUMMY_MSG_SIZE = 1 # TODO: Determine actual message size.
        msgCount = len(snapshot.unreadMsgs)
        self.push('+OK')
        if not arg:
            # TODO: Change all of this to operate on an account snapshot?
            for msgIdx in range(0, msgCount):
                id = snapshot.getMessageId(msgIdx)
                self.push('%d %s' % (msgIdx + 1, id))
                print '%d %s' % (msgIdx + 1, id)
        else:
            try:
                arg = int(arg)
            except:
                arg = -1
                
            if 0 < arg <= msgCount:
                id = snapshot.getMessageId(arg - 1)
                self.push('%d %s' % (arg, id))

            else:
                self.push("-ERR no such message, only %d messages in maildrop"
                          % msgCount)
        self.push(".")

    def pop_RETR(self, arg):
        """
        """
        if not arg:
            self.push('-ERR: Syntax: RETR msg')
        else:
            # TODO: Check request is in range...
            msgNumber = int(arg) - 1 # Argument is 1 based, sequence is 0 based
            
            self.push('+OK')

            for msgLine in byteStuff(snapshot.retrieveMessage(msgNumber)):
                self.push(msgLine)

            self.push('.') # TODO: Make constant...

#    def pop_DELE(self, arg):
#        """
#        """
#        if not arg:
#            self.push('-ERR: Syntax: DELE msg')
#        else:
#            # TODO: Delete the message from the mbox?
#            self.push('+OK DELE Ignored')
#            self.push('.') # TODO: Make constant...


    def pop_TOP(self, arg):
        """
        """
        if not arg:
            self.push('-ERR: Syntax: RETR msg')
        else:
            msgNumber, bodyLines = arg.split(" ")
            # TODO: Check request is in range...
            msgNumber = int(msgNumber) - 1 # Argument is 1 based, sequence is 0 based
            bodyLines = int(bodyLines)
            
            self.push('+OK')

            for msgLine in byteStuff(snapshot.retrieveMessage(msgNumber, bodyLines)):
                self.push(msgLine)

            self.push('.') # TODO: Make constant...

    
    def pop_QUIT(self, arg):
        # args is ignored
        self.push('+OK Goodbye')
        self.close_when_done()


def byteStuff(lines):
    """
    """
    for line in lines:
        if line.startswith("."):
            line = "." + line
        yield line


class POP3Proxy(asyncore.dispatcher):
    def __init__(self, localaddr):
        self._localaddr = localaddr
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        # try to re-use a server port if possible
        self.set_reuse_addr()
        self.bind(localaddr)
        self.listen(5)
        print '%s started at %s\n\tLocal addr: %s\n' % (
            self.__class__.__name__, time.ctime(time.time()),
            localaddr)

    def handle_accept(self):
        conn, addr = self.accept()
        print 'Incoming connection from %s' % repr(addr)
        channel = POPChannel(self, conn, addr)

        

if __name__ == '__main__':

    print __version__
    print
    print "usage: gmailboxpopd.py"
    print "  then connect with your POP3 client on localhost, port 110"
    print "  with the name of the mbox file as user, password will be ignored."
    print
    print "Press ctrl-c or ctrl-pause to exit."
    
    proxy = POP3Proxy(('127.0.0.1', 110))

    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass
