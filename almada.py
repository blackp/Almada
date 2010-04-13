#!/usr/bin/env python
#
# This is the main executable of the LAT Frontend.
# All relevant modules are loaded, then the server starts.
#
# Philip Blackwell September 2009

import sys, os
import logging
import select

from Almada.location_server import LocationServer
from Almada.lat_backend import LatServer
from Almada.config import Config, ConfigError, DEFAULT_RTLS_URL
from Almada.infield_device_server import InfieldDeviceServer
try:
    from Almada.location.locmod import new_locmod
except:
    logging.critical("Error importing locmod!")
    
class AlmadaServer(object):
    """
    Interface between Nanotron Location Server, LAT Backend, and Infield Devices.
    """
    
    def __init__(self, locmod, location_server, experiment=None, lat_server=None, infield_device_server=None):
        """
        locmod - LocMod
        location_server - Interface to the location server
        experiment - Experiment database to record to, if any.
        lat_server - Interface to the LAT backend
        infield_device_server - Interface to the infield devices
        """

        super(AlmadaServer, self).__init__()
        
        self.location_server = location_server
        self.experiment = experiment
        self.infield_device_server = infield_device_server
        self.lat_server = lat_server
        self.locmod = locmod
                 
    def most_recent(self, readings):
        """
        Take a list of readings from the location server, and return only the most recent from each pair.
        
        We would prefer to drop a few measurements than to get further and further behind real time.
        """
        
        if not readings:
            return []
            
        # Readings come in order of tag ID then anchor ID.
        # We expect to see decreasing tag IDs as we read back from the end.
        # As soon as we see the tag ID increase (or the anchor ID increase, in the case of a single tag), we know it is an older set of measurements.
        # Keep only the most recent.
        
        i = len(readings) - 1
        tag_id = readings[i].tag_id
        anchor_id = readings[i].anchor_id
        tag_ids = set([tag_id])
        while i > 0:
            reading = readings[i - 1]
            if reading.tag_id > tag_id:
                break
            elif reading.tag_id == tag_id and reading.anchor_id > anchor_id:
                break
                
            tag_id = reading.tag_id
            tag_ids.add(tag_id)
            anchor_id = reading.anchor_id
            i -= 1
        
        if i > 0:
            logging.warning("Discarding %d old readings from location server (keeping %d)" % (i, len(readings) - i))
            logging.info("Keeping measurements from tag_ids: %s" % str(tag_ids))
        else:
            logging.info("Keeping all readings from location_server: tag_ids: %s" % str(tag_ids))
        
        return readings[i:]
                        
    def finish(self):
        "Finalise everything before termination"
        
        self.experiment.append_ground_truth_distances()
                        
    def loop(self):
        """
        Service loop. Runs forever.
        
        Take in readings from the location server.
        Push tag locations to the LAT backend.
        Service infield device clients.
        """
        
        sockets = [self.location_server.socket]
        if self.infield_device_server:
            sockets.append(self.infield_device_server.socket)
        self.clients = []
        
        while True:
            
            (readers, writers, exceptors) = select.select(sockets + self.infield_device_server.clients, [], [], 0.1)
            
            for reader in readers:
                            
                if reader == self.infield_device_server.socket:
                    self.infield_device_server.accept_client()
                    
                elif reader == self.location_server.socket:
                    
                    readings = self.location_server.new_readings()
                    readings = self.most_recent(readings)
                    for reading in readings:
                        if locmod:
                            self.locmod.add_reading(reading.anchor_id, reading.tag_id, reading.distance)
                        if self.experiment:
                            self.experiment.add_reading(reading.anchor_id, reading.tag_id, reading.distance)
                    
                    if self.locmod:
                        tag_locations = self.locmod.update_locations()

                        if self.lat_server:
                            self.lat_server.send_tag_updates(tag_locations)
                                        
                        if self.experiment:
                            for tag_id, location in tag_locations.iteritems():
                                x, y = location
                                self.experiment.add_estimate(tag_id, x, y)
                              
                else:
                    self.infield_device_server.service_client(reader)
            
            
if __name__ == "__main__":
    
    from experiment.experiment_db import new_experiment
    
    ##############################
    # Command line options.
    ##############################

    from optparse import OptionParser

    option_parser = OptionParser()
    option_parser.add_option("-p", "--port", dest="port", type="int",
                             help="The TCP port to make connections available.")
    option_parser.add_option("-c", "--config", dest="config", default="almada.cfg",
                             help="The configuration file.")
    option_parser.add_option("-C", "--locmod_config", dest="locmod_config", default="locmod.lcfg",
                             help="The locmod configuration file.")
    option_parser.add_option("-u", "--rtls_url", dest="rtls_url", default=DEFAULT_RTLS_URL,
                             help="The upstream RTLS server to get config from (default=%default).")
    option_parser.add_option("-a", "--rtls_arena", dest="rtls_arena", type="int",
                              help="The arena ID to use for RTLS server config.")
    option_parser.add_option("-e", "--experiment", dest="experiment", default="experiment.db",
                             help="The experiment database to record t.")
    option_parser.add_option("-L", "--location_log", dest="location_log",
                             help="The file to log location_server output to.")
    option_parser.add_option("-l", "--log_level", dest="log_level", type="int",
                             help="The log level.", default=0)
    option_parser.add_option("-o", "--log_file", dest="log_file",
                             help="The log file (default stderr).")
    option_parser.add_option("-d", "--working_dir", dest="working_dir",
                             help="The working directory for the above files")

    options, args = option_parser.parse_args()

    # Get the right working dir, ensure it's a valid directory.
    if options.working_dir:
        working_dir = options.working_dir
        if not os.path.exists(working_dir):
            os.mkdir(working_dir)
        if not os.path.isdir(options.working_dir):
            sys.exit("Working directory (%s) exists, but is not a directory!" % working_dir)
    else:
        working_dir = "."
        
    # Start logging.
    if options.log_file:
        log_file = os.path.join(working_dir, options.log_file)
    else:
        log_file = None
    logging.basicConfig(filename=log_file, level=options.log_level,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filemode='w')

    # Start by loading default configuration.
    config = Config()
    # Then customise based on the config files.
    try:
        config.load_file(options.config, working_dir)
        config.load_locmod_file(options.locmod_config, working_dir)
        config.load_rtls(options.rtls_url, options.rtls_arena)
    except ConfigError, e:
        print "Configuration error:", e.msg
        sys.exit()
    # Finally, customise based on command line arguments
    
    if options.port:
        config.port = options.port

    anchor_ids = config.anchors.keys()
    anchor_ids.sort()

    # Only have the location server output logged if a working directory was specified.
    if options.working_dir and options.location_log:
        filename = os.path.join(working_dir, options.location_log)
        location_server_log = open(filename, "w")
    else:
        location_server_log = None
        
    # Load the location server. There's little point continuing if this fails.
    # But we will for if we just want to test the infield devices.
    try:
        location_server = LocationServer(anchor_ids, 
                                         hostname=config.location_server_hostname, 
                                         port=config.location_server_port, 
                                         logfile=location_server_log)
        location_server.connect()
    except Exception, e:
        logging.critical("Error connecting to location server: %s" % str(e))
        location_server = None
        
    # Try to load the LAT backend server. Non-essential.
    try:
        lat_server = LatServer(config.lat_server_hostname, config.lat_server_port)
        lat_server.connect()
    except:
        logging.critical("Error connecting to LAT backend server at %s:%d" % (lat_server.hostname, lat_server.port))
        lat_server = None
    
    # Load the LocMod. Not necessary for just collecting measurements.
    try:
        locmod = new_locmod(config)
    except Exception, e:
        logging.critical("Error loading location module: %s" % str(e))
        locmod = None
        
    # Only create the experiment database if a working directory was specified.
    if options.working_dir:
        experiment_filename = os.path.join(working_dir, options.experiment)
        if os.path.exists(experiment_filename):
            sys.exit("Experiment file (%s) already exists" % (experiment_filename))
        experiment = new_experiment(experiment_filename)
    
        for anchor_id, location in config.anchors.items():
            experiment.add_anchor(anchor_id, location)
    
        # Specify a limited subset of reference points to give out in order in a file called "reference_points.txt"
        # FIXME: Make reference point sequences configurable, and/or less of a hack.
        
        sequence_path = os.path.join(options.working_dir, "reference_points.txt")
        if os.path.exists(sequence_path):
            sequence_points = [line.strip() for line in open(sequence_path)]
        else:
            sequence_points = []
    
        if locmod:
            experiment.register_configuration(config.filename, config.text, config.locmod_filename, config.locmod_text)

        # Try to load the infield device server. There should be no problem here.
        try:
            infield_device_server = InfieldDeviceServer(experiment, config.anchors, config.tag_ids, config.reference_points, sequence_points, config.infield_device_port)
            infield_device_server.connect()
        except Exception, e:
            logging.critical("Error loading Infield Device Server: %s" % str(e))
            infield_device_server = None
            
    else:
        experiment = None
        infield_device_server = None

    logging.info("Starting Almada Server")
    almada_server = AlmadaServer(locmod, location_server, experiment, lat_server, infield_device_server)

    try:
        almada_server.loop()
    except KeyboardInterrupt:
        print "Quitting momentarily, just need to clean up a bit."
        experiment.append_ground_truth_distances()
        sys.exit()
