#!/usr/bin/env python
#
# Run a particular configuration against an experiment database.
# This allows us to try an alternative locmod (or setup - modified bases, for example).
#
# Philip Blackwell September 2009

import sys, os
import math
import logging
import glob
from optparse import OptionParser

from Almada.clock import shared_clock as clock
from Almada.config import Config, ConfigError
from Almada.location.locmod import new_locmod
from Almada.experiment.experiment_db import load_experiment
        
def run_locmod(experiment, locmod, config):
    "Run the locmod for a particular configuration against the distance readings to generate a new set of estimates."

    last_anchor_id = 0

    logging.info("Running location module: %s" % (config.locmod_filename))

    experiment.register_configuration(config.filename, config.text, config.locmod_filename, config.locmod_text)


    sql = "SELECT anchor_id, tag_id, distance, timestamp FROM distance_reading ORDER BY timestamp"
    for anchor_id, tag_id, distance, timestamp in experiment.query(sql):

        # Skip if the reading is not relavent to this configuration
        if not anchor_id in config.anchors:
            logging.debug("Ignoring reading from unknown anchor: %d" % anchor_id)
            continue
        if not tag_id in config.tag_ids:
            logging.debug("Ignoring reading from unknown tag: %d" % tag_id)
            continue

        # Anchor IDs come in order, so if we roll back to an earlier one it means we have all the reading for this update, and it's time to do the location update.
        if anchor_id < last_anchor_id:
            update = locmod.update_locations([tag_id])
            if update.has_key(tag_id):
                location = update[tag_id]
                x, y = location
                ground_truth = experiment.ground_truth(tag_id)
                if ground_truth:
                    gx, gy = ground_truth
                    error = math.hypot(x - gx, y - gy)
                    ground_truth_id = experiment.ground_truth_id(tag_id)
                    sql = "INSERT INTO estimate(tag_id, x, y, timestamp, ground_truth_id, error, configuration_id) VALUES (?, ?, ?, ?, ?, ?, ?)"
                    experiment.cursor.execute(sql, (tag_id, x, y, clock.get_time(), ground_truth_id, error, experiment.configuration_id))
                    logging.debug("Inserted estimate: (%06.2f, %06.2f) error %05.2fm from (%06.2f, %06.2f)" % (x, y, error, gx, gy))
                else:
                    logging.debug("Not adding estimate, location not known.")

        clock.set_time(timestamp)
        locmod.add_reading(anchor_id, tag_id, distance)

        last_anchor_id = anchor_id

    experiment.connection.commit()
        
            
if __name__ == "__main__":
    
    ##############################
    # Command line options.
    ##############################


    option_parser = OptionParser()
    option_parser.add_option("-e", "--experiment", dest="experiment", default="experiment.db",
                             help="The experiment database to record t.")
    option_parser.add_option("-c", "--config", dest="config",
                             help="The configuration file.")
    option_parser.add_option("-C", "--locmod_config", dest="locmod_config",
                             help="The locmod configuration file.")
    option_parser.add_option("-a", "--all",
                             action="store_true", dest="all", default=False,
                             help="Run all posible configs unless c or C are provided")
    option_parser.add_option("-d", "--working_dir", dest="working_dir",
                             help="The working directory for the above files")
    option_parser.add_option("-l", "--log_level", dest="log_level", type="int",
                             help="The log level.", default=30)
    option_parser.add_option("-o", "--log_file", dest="log_file",
                             help="The log file (default stderr).")

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

    experiment_filename = os.path.join(working_dir, options.experiment)
    experiment = load_experiment(experiment_filename)

    if options.all:
        config_names = [os.path.split(path)[1] for path in glob.glob("%s/*.cfg" % working_dir)]
        locmod_config_names = [os.path.split(path)[1] for path in glob.glob("%s/*.lcfg" % working_dir)]
        if options.config:
            config_names = [options.config]
        if options.locmod_config:
            locmod_config_names = [options.locmod_config]
            
        print "L:", locmod_config_names
        print "C:", config_names
        
    else:
        if options.config:
            config_names = [options.config]
        else:
            config_names = ["almada.cfg"]
        if options.locmod_config:
            locmod_config_names = [options.locmod_config]
        else:
            locmod_config_names = ["locmod.lcfg"]
            
    for config_name in config_names:
        for locmod_config_name in locmod_config_names:

            # Start by loading default configuration.
            config = Config()

            # Then customise based on the config files.
            try:
                config.load_file(config_name, working_dir)
                config.load_locmod_file(locmod_config_name, working_dir)
            except ConfigError, e:
                print "Configuration error:", e.msg
                sys.exit()
            # Finally, customise based on command line arguments
    
            anchor_ids = config.anchors.keys()
            anchor_ids.sort()

            locmod = new_locmod(config)

            run_locmod(experiment, locmod, config)
