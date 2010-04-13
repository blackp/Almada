#!/usr/bin/env python

import os, sys
import logging
import pickle
import math
from optparse import OptionParser


from Almada.config import Config
from Almada.experiment.experiment_db import load_experiment
from RTLS.PyFrontend.rtls_interface import RTLS
from Almada.location.nearest_neighbour import CanonicalObservationDatabase


if __name__ == "__main__":
    
    ##############################
    # Command line options.
    ##############################

    option_parser = OptionParser()
    option_parser.add_option("-e", "--experiment", dest="experiment", default="experiment.db",
                             help="The source experiment database")
    option_parser.add_option("-c", "--config", dest="config", default="almada.cfg",
                             help="The configuration file.")
    option_parser.add_option("-o", "--observation_database", dest="observation_database",
                             help="The output observation database")
    option_parser.add_option("-l", "--log_level", dest="log_level", type="int",
                             help="The log level.", default=30)
    option_parser.add_option("-O", "--log_file", dest="log_file",
                             help="The log file (default stderr).")

    options, args = option_parser.parse_args()
        
    # Start logging.
    if options.log_file:
        log_file = os.path.join(working_dir, options.log_file)
    else:
        log_file = None
    logging.basicConfig(filename=log_file, level=options.log_level,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filemode='w')

    config = Config()
    if os.path.exists(options.config):
        config.load_file(options.config)

    experiment = load_experiment(options.experiment)
    grid_size = 0.25

    if os.path.exists(options.observation_database):
        sys.exit("Observation database (%s) already exists" % options.observation_database)
    observations = CanonicalObservationDatabase(options.observation_database)
    observations.populate_observation_grid(config.min_x, config.max_x, config.min_y, config.max_y, grid_size)

    
    for anchor_id, (x, y) in config.anchors.items():
        observations.add_anchor(anchor_id, x, y)
          
    count = 0
    sql = "SELECT anchor_id, tag_id, distance, timestamp FROM distance_reading ORDER BY timestamp"
    for anchor_id, tag_id, distance, timestamp in experiment.query(sql):
        
        # Find a nearby observation (there should be exactly one, or four equidistant)
        try:
            x, y = experiment.ground_truth(tag_id, timestamp)
        except:
            logging.debug("Skipping observation without ground truth.")
            continue
        nearby = observations.nearby(x, y, grid_size/2.0)
                
        if len(nearby) == 1:
            observation_id = nearby.keys()[0]    
        elif nearby:
            logging.warning("Multiple (%d) observations nearby (%.2f, %.2f)" % (len(nearby), x, y))
        else:
            logging.warning("No observation nearby (%.2f, %.2f)" % (x, y))
            continue
            
        obs_x, obs_y = nearby[observation_id]
        observations.add_distance(observation_id, anchor_id, distance)
        count += 1
        if count % 1000 == 0:
            print count
            
    observations.trim()
