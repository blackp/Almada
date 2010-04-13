#!/usr/bin/env python

""""
Interface with the Location Server.

For now, the location server is provided by Nanotron.
It is somewhat poorly named: it only provides distance information. Determining the location is up to us.

Philip Blackwell August 2009
"""

import logging
import select
import socket
import time

from Almada.clock import shared_clock as clock

class Reading(object):
    """
    Representation of a tag-anchor distance reading from the nanotron location server.
    
    Break a line into its parts. (distance, tag_id, anchor_id, error_code).
    eg: #0006.58:017:001:000
    """
    
    def __init__(self, line=None, distance=None, tag_id=None, anchor_id=None, error_code=None, timestamp=None):
        
        super(Reading, self).__init__()
        
        if line != None:        
            line = line.strip()[1:] # Get rid of any leading or trailing whitespace, and the leading hash.
            parts = line.split(":")

            # We expect four parts
            if len(parts) != 4:
                raise

            # The first four parts are the same regardless.    
            self.distance = float(parts[0])
            self.tag_id = int(parts[1])
            self.anchor_id = int(parts[2])
            self.error_code = int(parts[3])

        else:
            self.distance = distance
            self.tag_id = tag_id
            self.anchor_id = anchor_id
            self.error_code = error_code

        self.timestamp = timestamp
    
    def __repr__(self):
        "How is this reading represented by the Location Server."
        return "#%07.2f:%03d:%03d:%03d" % (self.distance, self.tag_id, self.anchor_id, self.error_code)
    
DEFAULT_LOCATION_SERVER_PORT = 6868

class LocationServer(object):
    """
    The interface (over TCP/IP) to a Nanotron LocationServer
    
    Parses the output into readings.
    Ignores readings with non-zero error codes.
    Provides readings For tags and anchors that are being tracked.
    Optionally, logs the output directly from the Location Server (including readings with error codes). 
    
    Must be driven by calling 'new_readings' whenever new data is available on the socket.
    """
    
    line_separator = "\r\n"
    receive_size = 4096
    
    def __init__(self, anchor_ids, hostname="", port=6868, logfile=None, log_all=False):
        """
        If a logfile is given, all data reveived from the location server will be logged.
        log_all - Whether to log everything, or just readings from tracked ids.
        """
        super(LocationServer, self).__init__()
        self.hostname = hostname
        self.port = port
        self.anchor_ids = anchor_ids
        self.logfile = logfile
        self.log_all = log_all
        self.tracked_ids = set()

    def should_record(self, tag_id, anchor_id=None):
        "Whether we are tracking these IDs (or logging all)."
        
        if self.log_all:
            return True
            
        if not tag_id in self.tracked_ids:
            return False
                        
        return (anchor_id == None) or (anchor_id in self.tracked_ids)
        
    def start_tracking(self, device_id):
        "Start (or continue) tracking the given device (distance estimates will be logged.)"
        
        if not device_id in self.tracked_ids:
            logging.info("Readings for %d will now be recorded." % device_id)
            self.tracked_ids.add(device_id)
    
    def stop_tracking(self, device_id):
        "Stop tracking the given device (distance estimates will not be logged.)"
        
        logging.info("Readings for %d will no longer be recorded." % device_id)
        if device_id in self.tracked_ids:
            self.tracked_ids.remove(device_id)
    
    def connect(self):
        """
        Connect to location server and initiate continuous mode.
        """        
        
        logging.info("Connecting to location server at %s:%d" % (self.hostname, self.port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.hostname, self.port))
        self.recv_buffer = ""

        # Set the commands to initiate the location server.
        init_command = "INIT %d" % (len(self.anchor_ids))
        for anchor_id in self.anchor_ids:
            init_command += " %d" % anchor_id
        start_command = "START"
        continuous_mode_command = "MODE 0"
        
        # Send the commands
        self.socket.send(init_command + self.line_separator)
        self.socket.send(start_command + self.line_separator)
        self.socket.send(continuous_mode_command + self.line_separator)
        
    def log_line(self, line):
        "Log a line, and separator, if we are logging."
        if self.logfile:
            self.logfile.write(line + self.line_separator)
            self.logfile.flush()
        
    def log_lines(self, lines):
        "Log several lines with separators, if we are logging."
        for line in lines:
            self.log_line(line)
        
    def log_timestamp(self):
        "Log the current time."
        timestamp = "%%:%.3f" % time.time()
        self.log_line(timestamp)
        
    def new_readings(self):
        "A list of complete lines received from the server in the order they arrived, if there are any."

        new_data = self.receive_size * "a"
        while len(new_data) == self.receive_size:
            new_data = self.socket.recv(self.receive_size)
            logging.debug("LocationServer: received %d bytes" % len(new_data))
            self.recv_buffer += new_data
        
        lines = self.recv_buffer.split(self.line_separator)
        complete_lines = lines[:-1]
        self.recv_buffer = lines[-1]
            
        # Process the lines.
        readings = []
        for line in complete_lines:
            if not line.strip():
                continue
            try:
                reading = Reading(line)     
                if reading.error_code:
                   logging.info("Ignoring reading with error (%d)" % reading.error_code)
                else:
                   readings.append(reading)
                    
            except Exception, e:
                logging.error("Error reading line from location server: %s" % line)

        # Log the lines we are about to process.
        self.log_timestamp()
        for line in complete_lines:
            self.log_line(line)

        return readings
        
class FakeServer(object):
    """
    Emulate a location server in continuous mode based on an experiment database.

    FIXME: Implement.
    """
    def __init__(self, experiment, port=DEFAULT_LOCATION_SERVER_PORT, repeat=True):
        """
        Feed the data recorded in 'experiment'.
        """

        super(FakeServer, self).__init__()
        self.experiment = experiment
        self.port = port
        self.repeat = repeat

        self.readings = experiment.distance_readings().fetchall()

        self.next_update_time = -1.0
        self.next_reading = 0

    def connect(self):
        "Bind the TCP socket."

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', self.port))
        self.socket.listen(10) # 10 queued connections

    def loop(self):

        self.rdset = [self.socket]
        self.clients = []

        logging.info("Starting fake location server loop.")

        while True:

            # Deal with any incoming data first.
            (readers, writers, exceptors) = select.select(self.rdset + self.clients,[], [], 0.1)
            for reader in readers:
                if reader == self.socket:
                    # Accecpt a new connection from this socket.
                    conn, addr = self.socket.accept()
                    self.clients.append(conn)
                    logging.info("New client connection: %s" % (str(addr)))
                else:
                    # Service any data that has come from a client connection.
                    message = reader.recv(1024)
                    if message:
                        logging.info("Received message from client: %s" % message.strip())
                    else:
                        logging.info("Dropping client connection")
                        for i, client in enumerate(self.clients):
                            if client == reader:
                                del self.clients[i]

            # Then, see if it's time to push some data.
            if clock.get_time() > self.next_update_time:
                self.push_updates()

    def push_updates(self):
        "Send distance readings to all the clients, update self.next_update_time."
        
        now = clock.get_time()
        updates = ""

        reading = self.readings[self.next_reading]
        while reading["timestamp"] < now:
            
            distance_reading = Reading(distance=reading["distance"], tag_id=reading["tag_id"], anchor_id=reading["anchor_id"], error_code=0)
            updates += "%s%s" % (str(distance_reading), LocationServer.line_separator)
            
            self.next_reading += 1

            if self.next_reading >= len(self.readings):
                if self.loop:
                    # Set the next reading to the first, and set the time three seconds before the first reading.
                    self.next_reading = 0
                    first_timestamp = self.readings[0]["timestamp"]
                    clock.set_time(first_timestamp - 3.0)
                    self.next_update_time = first_timestamp
                break
            
            reading = self.readings[self.next_reading]

        if updates:
            logging.info("Pushing updates of length %d" % len(updates))
            logging.debug("Updates:\n%s" % updates)
            for client in self.clients:
                client.send(updates)

# The main LocationServer is intended to be used as a module in the LAT Frontend.
# However, if run as an executable, we can provide a "Fake" location server 
# (that the LAT Frontend could connect to for testing purposes).
    
if __name__ == "__main__":
    
    from experiment.experiment_db import load_experiment
    
    from optparse import OptionParser

    option_parser = OptionParser()
    option_parser.add_option("-e", "--experiment", dest="experiment", 
                             help="The experiment database to replay from.")
    option_parser.add_option("-l", "--log_level", dest="log_level", type="int",
                             help="The log level.", default=0)
    option_parser.add_option("-o", "--log_file", dest="log_file",
                             help="The log file (default stderr).")
    
    options, args = option_parser.parse_args()
    
    logging.basicConfig(filename=options.log_file, level=options.log_level,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filemode='w')
    
    experiment = load_experiment(options.experiment)
    fake_server = FakeServer(experiment)
    fake_server.connect()
    fake_server.loop()

