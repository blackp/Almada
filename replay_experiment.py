#!/usr/bin/env python
#
# Replay the results of an experiment, pushing them to the LAT Backend
#
# Philip Blackwell September 2009

import sys, os
import logging
import time

from Almada.clock import shared_clock as clock
from Almada.lat_backend import LatServer
from Almada.config import Config, ConfigError
from Almada.experiment.experiment_db import load_experiment

def replay_experiment(experiment, experiment_id, lat_server, ground_truth_id_offset):

    estimates = experiment.estimates(options.experiment_id)
    
    last_timestamp = None
    for tag_id, x, y, timestamp in estimates:

        tags = {tag_id: (x, y)} # The dictionary we will send as updates.
        
        # Wait before sending, if necessary
        if last_timestamp:
            wait_time = timestamp - last_timestamp
            print "sleeping for %.2f seconds" % wait_time
            time.sleep(wait_time)
        
        clock.set_time(timestamp)
        last_timestamp = timestamp
        
        # Add the ground truth to the update, maybe.
        if ground_truth_id_offset:
            ground_truth_tag_id = tag_id + ground_truth_id_offset
            location = experiment.ground_truth(tag_id)
            if location:
                tags[ground_truth_tag_id] = location
        
        lat_server.send_tag_updates(tags)

def list_location_module_ids(experiment):
    
    print "Available Location Modules:"
    
    for locmod_id, text, distance_filter_text, location_engine_text, position_filter_text in experiment.query("SELECT * FROM location_module"):
        print "%03d\t%s\t%s\t%s\t%s" % (locmod_id, text, distance_filter_text, location_engine_text, position_filter_text)

if __name__ == "__main__":
    
    
    ##############################
    # Command line options.
    ##############################

    from optparse import OptionParser

    option_parser = OptionParser()
    option_parser.add_option("-p", "--port", dest="port", type="int",
                             help="The port number of the LAT Backend server.")
    option_parser.add_option("-H", "--hostname", dest="hostname", 
                             help="The hostname of the LAT Backend server.")
    option_parser.add_option("-c", "--config", dest="config", default="almada.cfg",
                             help="The configuration file.")
    option_parser.add_option("-e", "--experiment", dest="experiment", default="experiment.db",
                             help="The experiment database to record to.")
    option_parser.add_option("-i", "--experiment_id", dest="experiment_id", type="int",
                             help="The Location Module ID to use for estimates.")
    option_parser.add_option("-t", "--tag_offset", dest="tag_offset", type="int",
                             help="The amount to offset tag IDs with their ground truth. Default 0 for no ground truth", default=0)
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
        if not os.path.isdir(options.working_dir):
            sys.exit("No such directory: %s" % working_dir)
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

    # Then customise based on the config file.
    try:
        config.load_file(options.config, working_dir)
    except ConfigError, e:
        print "Configuration error:", e.msg
        sys.exit()

    # Finally, customise based on command line arguments
    if options.port:
        config.lat_server_port = options.port
    if options.hostname:
        config.lat_server_hostname = options.hostname
            
    # Try to load the LAT backend server.
    try:
        lat_server = LatServer(config.lat_server_hostname, config.lat_server_port)
        lat_server.connect()
    except:
        sys.exit("Error connecting to LAT backend server at %s:%d" % (config.lat_server_hostname, config.lat_server_port))

    # Load the experiment database
    experiment_filename = os.path.join(working_dir, options.experiment)
    experiment = load_experiment(experiment_filename)
    if experiment == None:
        sys.exit("Error loading experiment: %s" % experiment_filename)

    if options.experiment_id:
        replay_experiment(experiment, options.experiment_id, lat_server, options.tag_offset)
    else:
        list_location_module_ids(experiment)
