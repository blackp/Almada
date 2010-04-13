#!/usr/bin/env python

import os, sys
import logging
import pickle
import math
from optparse import OptionParser

import pylab
import numpy

from Almada.experiment.experiment_db import load_experiment
from RTLS.PyFrontend.rtls_interface import RTLS
from Almada.location.nearest_neighbour import CanonicalObservationDatabase
    
def run_nn(experiment, observations, error_bound):
    
    errors = []
    
    for tag_id, reading, ground_truth, timestamp in experiment.observations():
        
        gx, gy = ground_truth
        
        delta_x = []
        delta_y = []
        
        possible_locations = observations.possible_locations(reading, error_bound)
        for x, y in possible_locations:
            dx = x - gx
            dy = y - gy
            delta_x.append(dx)
            delta_y.append(dy)
            
        n = len(delta_x)
        dx = sum(delta_x)/n
        dy = sum(delta_y)/n
        d = math.hypot(dx, dy)
        
        errors.append(d)
        
        print "d: %5.2f (%5.2f, %5.2f) n: %d" % (d, dx, dy, len(possible_locations))
        
    return errors
    
if __name__ == "__main__":
    
    ##############################
    # Command line options.
    ##############################

    option_parser = OptionParser()
    option_parser.add_option("-o", "--observation_database", dest="observation_database", default="observations.db",
                             help="The output observation database")
    option_parser.add_option("-e", "--experiment", dest="experiment", default="experiment.db",
                             help="The experiment database to record to")
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

    if not os.path.exists(options.experiment):
        sys.exit("Experiment file (%s) doesn't exist!" % options.experiment)
    experiment = load_experiment(options.experiment)

    if not os.path.exists(options.observation_database):
        sys.exit("Observations file (%s) doesn't exist!" % options.observation_database)
    observations = CanonicalObservationDatabase(options.observation_database)

    if True:
        errors_by_bound = {}
        for error_bound in [0.5, 1.0, 2, 3, 5]:
            errors = run_nn(experiment, observations, error_bound)
            errors_by_bound[error_bound] = errors
        
            print "B: %.2f Avg: %.2f Min: %.2f Max: %.2f" % (error_bound, sum(errors)/len(errors), min(errors), max(errors))
        