#!/usr/bin/env python
#
# Update the anchors from a new configuration file. Update ground truth distances accordingly
#
# Philip Blackwell March 2010

import os, sys
import logging
import pickle
from optparse import OptionParser

import pylab
import numpy

from Almada.config import Config
from Almada.experiment.experiment_db import load_experiment
from RTLS.PyFrontend.rtls_interface import RTLS
     

if __name__ == "__main__":
    
    ##############################
    # Command line options.
    ##############################

    option_parser = OptionParser()
    option_parser.add_option("-e", "--experiment", dest="experiment", default="experiment.db",
                             help="The experiment database to record to")
    option_parser.add_option("-c", "--config", dest="config", default="almada.cfg",
                             help="The configuration file.")
    option_parser.add_option("-l", "--log_level", dest="log_level", type="int",
                             help="The log level.", default=0)
    option_parser.add_option("-o", "--log_file", dest="log_file",
                             help="The log file (default stderr).")

    options, args = option_parser.parse_args()

    # Start logging.
    logging.basicConfig(filename=options.log_file, level=options.log_level,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filemode='w')

    experiment = load_experiment(options.experiment)
    
    config = Config()
    config.load_file(options.config)
    
    for anchor_id, location in config.anchors.items():
        experiment.update_anchor(anchor_id, location)
    
    experiment.append_ground_truth_distances()