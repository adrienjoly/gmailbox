#!/usr/bin/env python
#
# gmailretr.py -- Gmail inbox retrieval to a mailbox file
#
# $Revision: 0.9 $ ($Date: 2006/05/21 18:30:00 $)
#
# Author: Adrien Joly <adrien.joly@gmail.com>
#
# Website:
# http://roly.blogsome.com/2006/05/21/gmailbox-mbox-retriever-pop3-server/
#
# License: GPL 2.0
#
# Based on archive.py by <follower@myrealbox.com>
#
##

import sys
import os
import logging

__version__ = 'Gmail Inbox Retrieval version 0.9'

# Allow us to run using installed `libgmail` or the one in parent directory.
try:
    import libgmail
except ImportError:
    sys.path.insert(1,
                    os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                  os.path.pardir)))
    import libgmail

from libgmail import U_INBOX_SEARCH
from libgmail import U_AS_SUBSET_UNREAD

# Retrieval function

def retrieve(ga, label, filename):

    if label in libgmail.STANDARD_FOLDERS:
        threads = ga.getMessagesByFolder(label, True)
    else:
        threads = ga.getMessagesByLabel(label, True)

    t = 0;
    mbox = []
    
    print 'Number of threads to retrieve: %i' % len(threads)

    for thread in threads:
        t = t + 1
        print 'Thread %i (%i messages)...' % (t, len(thread))
        m = 0
        for msg in thread:
            m = m + 1
            source = msg.source.replace("\r","").lstrip()
            print ' - Message %i (%i bytes) DONE.' % (m, len(source))
            mbox.append("From - Thu Jan 22 22:03:29 1998\n")
            mbox.append(source)
            mbox.append("\n\n")
    
    open(filename, "w+b").writelines(mbox)

# Main program

if __name__ == '__main__':

    print __version__
    print
    print 'usage: gmailretr.py [<account> [<label> [<password>]]]'
    print

    import sys
    from getpass import getpass

    try:
        user = sys.argv[1]
    except IndexError:
        user = raw_input("Gmail account name: ")
        
    try:
        password = sys.argv[3]
    except IndexError:
        password = getpass("Password: ")

    print "Connecting to %s@gmail.com..." % user
    
    ga = libgmail.GmailAccount(user, password)

    try:
        ga.login()
    except libgmail.GmailLoginFailure:
        print 'Unable to login as %s on GMail' % user
    else:
        print 'Successfully connected to GMail'
        
        try:
            label = sys.argv[2]
        except IndexError:
            print 'List of folders/labels:'
            labels = libgmail.STANDARD_FOLDERS + ga.getLabelNames()
            
            for optionId, optionName in enumerate(labels):
                print "  %d. %s" % (optionId, optionName)

            label = labels[int(raw_input("Choice: "))]

        print 'Retrieving messages from "%s" ...' % label
        filename = "%s-%s.mbox" % (user, label)
        retrieve(ga, label, filename)
        print "The mailbox has been saved in %s" % filename
