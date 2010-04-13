"""
The connection to the LAT Backend.

For now, only sends tag positions (x, y).
Should also be able to get config.

FIXME: Updates should be done as frequently as possible, then filtered appropriately in the backend. 
       (As it is, updates are simply limited to 1Hz.)
"""

import logging
import socket

from Almada.clock import shared_clock as clock

class LatServer(object):
    """docstring for LatServer"""
    
    def __init__(self, hostname, port):
        ""
        
        super(LatServer, self).__init__()
        self.hostname = hostname
        self.port = port    
        self.tags = {}
        self.update_period = 1.0
        self.last_update_time = 0.0
            
    def connect(self):
        ""
        
        logging.info("Connecting to LAT backend server at %s:%d" % (self.hostname, self.port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1.0)
        self.socket.connect((self.hostname, self.port))
        logging.info("Connected to LAT backend server")
            
                        
    def send_tag_updates(self, tags):
        "Send location information given in the dictionary 'tags' (tag_id -> location)"

        # FIXME: Uses plain text interface. Should use proper LAT XML interface.

        result = {}

        # Add these tag updates to our history
        for tag_id, location in tags.iteritems():
            if not self.tags.has_key(tag_id):
                self.tags[tag_id] = []
            self.tags[tag_id].append(location)
            
        now = clock.get_time()
        if now - self.last_update_time > self.update_period:
            
            for tag_id, locations in self.tags.iteritems():
                x, y = locations[-1]
                result[tag_id] = x, y
                logging.info("Sending tag update: %d (%.2f, %.2f)" % (tag_id, x, y))
                if self.socket:
                    self.socket.send("%d %.2f %.2f\r\n" % (tag_id, x, y))
            
            # Reset for next time.
            self.tags = {}
            self.last_update_time = clock.get_time()
            
        return result
