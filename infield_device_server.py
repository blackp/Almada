"""
A TCP/IP interface to any Infield Devices.

Philip Blackwell 2009-09-25
"""

import logging
import re
import socket

from Almada.experiment.ground_truth import GroundTruthAction
from Almada.experiment.sound import action_sounds
from Almada.config import DEFAULT_IFD_PORT

class InfieldDeviceServer(object):
    """
    A TCP/IP interface to any Infield Devices.
    """
    
    def __init__(self, experiment, anchors, tag_ids, reference_points, sequence=None, port=DEFAULT_IFD_PORT):
        """
        """

        super(InfieldDeviceServer, self).__init__()
        
        self.experiment = experiment
        self.anchors = anchors
        self.tag_ids = tag_ids
        self.reference_points = reference_points
        self.sequence = sequence
        self.port = port
        self.clients = []        
        
        print self.reference_points
        print self.sequence
        
    def connect(self):
        "Bind the TCP socket. Start listening for Infield Devices"
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', self.port))
        self.socket.listen(10) # 10 queued connections
        
    def service_client_request(self, request, client):
        """
        Service a request from an Infield Device.
        """
        
        logging.info("IFD: Request: %s" % request)
        
        if request.lower() == "tags":
            tag_ids = "Tag IDs:"
            for tag_id in self.tag_ids:
                tag_ids += " %d" % tag_id
            logging.info("Sending tags response: %s" % tag_ids)
            client.send("%s\r\n" % tag_ids)
        if request.lower() == "reference":
            if self.sequence:
                reference_point_labels = self.sequence
            else:
                reference_point_labels = self.reference_points.keys()
                reference_point_labels.sort()
            response = "Reference Points: " + " ".join(reference_point_labels)
            logging.info("Sending reference points response: %s" % response)
            client.send("%s\r\n" % response)

    arrived_re = re.compile("Tag ([0-9]+) Arrived at Reference (.*)")
    passed_re = re.compile("Tag ([0-9]+) Passed Reference (.*)")
    heading_re = re.compile("Tag ([0-9]+) Left Reference (.*)")
    abandoned_re = re.compile("Tag ([0-9]+) Abandoned Reference (.*)")
        
    regular_expressions = {GroundTruthAction.arrived_code: arrived_re,
                           GroundTruthAction.passed_code: passed_re,
                           GroundTruthAction.heading_code: heading_re,
                           GroundTruthAction.abandoned_code: abandoned_re}

    def service_client_command(self, command, client):
        """
        Service a command. That is a line ending in a full stop.
        """
        
        logging.info("IFD: Command: %s" % command)
        
        # Try this command against regexps for all actions, it should match exactly one.
        matches = [(regexp.match(command), action) for action, regexp in self.regular_expressions.iteritems()]
        matches = filter(lambda x: x[0], matches) # Remove any non-matches
        if len(matches) != 1:
            logging.error("IFD: Unexpected command from client (matched %d): %s" % (len(matches), command))
            logging.error("IDF: Matches: %s" % str(matches))
            return
        
        match, action = matches[0]
        action_sounds[action].play()
                
        tag_id, reference_name = match.groups()
        tag_id = int(tag_id)
        location = self.reference_points[reference_name]
        
        print tag_id, location, action, reference_name
        self.experiment.apply_ground_truth_info(tag_id, location, action, reference_name)

    def service_client(self, client):
        """Service some activity for this client."""
        
        message = client.recv(1024)
        if message:
            meat = message.strip()
            if meat.endswith("?"):
                self.service_client_request(meat[:-1], client)
            elif meat.endswith("."):
                self.service_client_command(meat[:-1], client)
            else:
                logging.error("IFD: Unexpected message: %s" % message.strip())
        else:
            logging.info("IFD: Dropping client connection")
            self.clients.remove(client)

    def accept_client(self):
        """Accept a new client on the socket."""
        conn, addr = self.socket.accept()
        self.clients.append(conn)
        logging.info("IFD: New client connection: %s" % (str(addr)))


