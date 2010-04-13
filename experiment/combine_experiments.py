#!/usr/bin/env python
#
# Combine the distance readings from several experiments into one.
#
# Philip Blackwell October 2009

import os, sys
import logging
from optparse import OptionParser

from Almada.experiment.experiment_db import new_experiment, load_experiment
from Almada.util.geometry import distance_2d
                
def combine(combined, existing):
    """
    Combine the list of 'existing' databases into 'new'
    """
    
    # First we need to confirm that the anchors were in the same posisions.
    anchors = {}
    for database in existing:
        for anchor_id, location in database.anchors.items():
            if not anchors.has_key(anchor_id):
                anchors[anchor_id] = location
            elif distance_2d(location, anchors[anchor_id]) > 0.01:
                raise Exception, "Anchor locations don't match for anchor %d: (%s) != (%s)" % (anchor_id, str(location), str(anchors[anchor_id]))

    for anchor_id, location in anchors.items():
        combined.add_anchor(anchor_id, location)

    # Add all the distance readings in each database.
    # The corresponding ground truth entries will need to be migrated too.
    for i, database in enumerate(existing):
        print "Processing database %d" % i
        sql = "SELECT id, label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y FROM ground_truth"
        cursor = database.connection.cursor()   
        cursor.execute(sql)
        
        ground_truth_mapping = {}
        for existing_ground_truth_id, label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y in cursor.fetchall():
            combined_ground_truth_id = combined.add_ground_truth(label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y)
            ground_truth_mapping[existing_ground_truth_id] = combined_ground_truth_id
            
        select_readings_sql = "SELECT anchor_id, tag_id, distance, ground_truth_distance, ground_truth_error, timestamp FROM distance_reading WHERE ground_truth_id = ?"
            
        for ground_truth_id, new_ground_truth_id in ground_truth_mapping.items():
            cursor.execute(select_readings_sql, (ground_truth_id,))
            for anchor_id, tag_id, distance, ground_truth_distance, ground_truth_error, timestamp in cursor.fetchall():
                combined.add_full_reading(anchor_id, tag_id, distance, new_ground_truth_id, ground_truth_distance, ground_truth_error, timestamp)
        

if __name__ == "__main__":
    
    ##############################
    # Command line options.
    ##############################
   
    usage = "usage: %prog [options] database1 database2..."
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--combined", dest="combined", default="combined.db",
                      help="The sqlite database file for the combined database.", metavar="FILE")

    options, args = parser.parse_args()

    try:
        combined = new_experiment(options.combined)
    except Exception, e:
        sys.exit("Error loading combined database: %s" % str(e))
    
    existing = []
    for filename in args:
        database = load_experiment(filename)
        if database:
            existing.append(database)
        else:
            logging.error("Error loading database: %s" % filename)
            
    
    combine(combined, existing)
