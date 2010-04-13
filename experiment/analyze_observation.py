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
    option_parser.add_option("-o", "--observation_database", dest="observation_database", default="observations.db",
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
    backend_api = config.load_rtls()
    arena_id = 1
    
    observations = CanonicalObservationDatabase(options.observation_database)
    
    distances_by_anchor_observation = {}
    
    # Keep some arrays, in arbitrary (but identical) order
    d  = [] # ground truth distance
    m  = [] # median observed distance
    D  = [] # distance arrays
    er = [] # errors (m - d)
    a  = [] # anchor IDs
    l  = [] # observation locations
    
    images = {}
    
    anchors = observations.anchors()
    for anchor_id, (ax, ay) in anchors.items():
        image = backend_api.get_default_map(arena_id)
        images[anchor_id] = image
        for observation_id in observations.observation_ids_with_anchor(anchor_id):
            ox, oy = observations.observation_location(observation_id)
            distance = math.hypot(ax - ox, ay - oy)
            distances = observations.distances(observation_id, anchor_id)
            distances.sort()
            median = distances[len(distances)/2]
            error = median - distance
            distances_by_anchor_observation[(anchor_id, observation_id)] = distance, distances
            
            m.append(median)
            d.append(distance)
            D.append(distances)
            er.append(error)
            l.append((ox, oy))
            a.append(anchor_id)
            
            #image.drawCircleWorld(ox, oy, error, colour="Red")
            
            print "%d %d %d %5.2f %5.2f" % (anchor_id, observation_id, len(distances), distances[0] - distance, distances[-1] - distance)
        #image.save("Anchor%d.png" % anchor_id)
        
    # Draw a grey line from the each anchor to each observation point (in the relevant image)
    for i in range(len(d)):
        anchor_id = a[i]
        ax, ay = anchors[anchor_id]
        x, y = l[i]
        images[anchor_id].drawLineWorld((ax, ay), (x, y), colour=(200,200,200))

    # Draw a median error circle at each observation point
    for i in range(len(d)):
        anchor_id = a[i]
        x, y = l[i]        
        error = er[i]
        images[anchor_id].drawCircleWorld(x, y, error, colour="Red")

    # Save each image
    for anchor_id in anchors:
        images[anchor_id].save("Anchor%d.png" % anchor_id)