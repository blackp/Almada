#!/usr/bin/env python
#
# Analyze the results of an experiment, for one or many particular configurations.
#
# Philip Blackwell October 2009

import os, sys
import logging
import pickle
from optparse import OptionParser

import pylab
import numpy

from Almada.config import Config
from Almada.experiment.experiment_db import load_experiment
from RTLS.PyFrontend.rtls_interface import RTLS
     
def count_walls_between(rtls_interface, experiment, arena_id=1):
    "Return a dictionary of dictionarys ground_truth_id[anchor_id] -> num_walls, assume this experiment is in arena 1."
    
    result = {}
    
    # Get a map image from the rtls interface
        
    maps = rtls_interface.get_maps(arena_id)
    for map_id, map_image in maps.items():
        if "walls" in map_image.picturePath.lower():
            wall_map = map_image
        else:
            floorplan = map_image
                
    # Count the number of walls between anchor and tag for each ground truth entry
    
    for ground_truth_id in experiment.ground_truth_ids():
        
        label, start_x, start_y, end_x, end_y, start_time, end_time = experiment.ground_truth_details(ground_truth_id)
        tag_location = start_x, start_y

        # Skip any "dynamic" ground truth entries
        if end_x or end_y:
            continue
        
        result[ground_truth_id] = {}
        for anchor_id, location in experiment.anchors.items():
            walls = map_image.findWallsBetween(location, tag_location)
                                                
            result[ground_truth_id][anchor_id] = len(walls)
            
    return result
    
def reception_over_time(experiment, time_slice=1.0):
        
    pass
    
def dump_error_histogram(experiment, histogram_filename="error_histogram.pickle"):
    
    distance, ground_truth_distance = distance_versus_ground_truth(experiment)
    d = numpy.array(distance)
    g = numpy.array(ground_truth_distance)
    e = d - g
    p, bins = numpy.histogram(e, bins=20, normed=True)
    pickle.dump((p, bins), open(histogram_filename, "w"))
    
def distance_versus_ground_truth(experiment, tag_id=None, anchor_id=None, ground_truth_id=None):
    
    sql = "SELECT distance, ground_truth_distance FROM distance_reading WHERE ground_truth_id IS NOT NULL"
    if tag_id:
        sql += " AND tag_id = %d" % tag_id
    if anchor_id:
        sql += " AND anchor_id = %d" % anchor_id
    if ground_truth_id:
        sql += " AND ground_truth_id = %d" % ground_truth_id
    sql += " ORDER BY ground_truth_distance"
    
    distance_readings = experiment.query(sql).fetchall() 
    
    # Arrays for distance and ground_truth
    d, g = [], []
    
    for distance_reading in distance_readings:
        distance, ground_truth_distance = distance_reading
        d.append(distance)
        g.append(ground_truth_distance)
            
    return d, g
    
def analyze_distance_readings(experiment):
    "Much of the analysis is independent of any location algorithm: how did the raw distance reading compare with expected?"
    
    sql = "SELECT MIN(timestamp), MAX(timestamp) FROM distance_reading;"
    experiment_start_time, experiment_end_time = experiment.query(sql).fetchone()
    
    # For each ground truth entry
    ground_truth = {}
    sql = "SELECT id, label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y FROM ground_truth;"
    for row in experiment.query(sql):
        ground_truth_id, label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y = row
        if not start_time:
            start_time = experiment_start_time
        if not end_time:
            end_time = experiment_end_time
        duration = end_time - start_time
        
        sql = "SELECT DISTINCT(timestamp) FROM distance_reading WHERE ground_truth_id = %d ORDER BY timestamp" % ground_truth_id
        updates = experiment.query(sql).fetchall()
        
        print "Ground truth %3d: %7s: %3d distance readings in %4.1f seconds" % (ground_truth_id, label, len(updates), duration)        
    
    sql = "SELECT distance, ground_truth_distance FROM distance_reading WHERE ground_truth_id IS NOT NULL ORDER BY ground_truth_distance"
    distance_readings = experiment.query(sql).fetchall()
    
    # Arrays for distance and ground_truth
    d, g = [], []
    
    for distance_reading in distance_readings:
        distance, ground_truth_distance = distance_reading
        d.append(distance)
        g.append(ground_truth_distance)
            
    return d, g

def plot_moving_estimates(experiment, configuration_id, ground_truth_id):
    "A local line plot of all estimates (in order) for a particular ground truth."
    
    label, start_x, start_y, end_x, end_y, start_time, end_time = experiment.ground_truth_details(ground_truth_id)
    
    # Establish whether this is a static or dynamic entry.
    moving = ">" in label
    
    # If it's dynamic, draw a line between the start and end points
    if moving:
        bx = (start_x + end_x) / 2.0
        by = (start_y + end_y) / 2.0
        pylab.plot([start_x - bx, end_x - bx], [start_y - by, end_y - by], "--")
    else:
        bx = start_x
        by = start_y

    est_x = []
    est_y = []
    
    sql = "SELECT x, y FROM estimate WHERE configuration_id = ? AND ground_truth_id = ? ORDER BY timestamp ASC"
    for x, y in experiment.query(sql, (configuration_id, ground_truth_id)).fetchall():
        est_x.append(x - bx)
        est_y.append(y - by)
    
    pylab.plot(est_x, est_y)
    

def plot_error_scatter(experiment, configuration_id, ground_truth_id, size=5.0):
    "A scatter plot of all errors for a particular ground truth."            
    
    pylab.cla()
    estimates, timestamps, errors, error_sizes = experiment.ground_truth_estimate_info(configuration_id, ground_truth_id)
    
    errors_x = [e[0] for e in errors]
    errors_y = [e[1] for e in errors]

    #pylab.figure(figsize=(6,6))    
    #
    pylab.plot(errors_x, errors_y, ".")
    pylab.grid()
    pylab.axis([-size, size, -size, size])
    pylab.axis("equal")


def dump_anchor_reception(experiment, ground_truth_id=None):
    "A string with anchor reception stats"

    # How long was the tag at the given ground truth location.
    sql = "SELECT MIN(timestamp), MAX(timestamp) FROM distance_reading WHERE ground_truth_id = ?"
    start, end = experiment.query(sql, (ground_truth_id,)).fetchone()
    duration = end - start
    
    anchor_reading_counts = {}
    sql = "SELECT COUNT(*) FROM distance_reading WHERE ground_truth_id = ? AND anchor_id = ?"
    for anchor_id in experiment.anchors:
        anchor_reading_counts[anchor_id] = experiment.query(sql, (ground_truth_id, anchor_id)).fetchone()[0]
    
    max_readings = max(anchor_reading_counts.values())
    total_readings = sum(anchor_reading_counts.values())
    heading = "Total readings: %4d in %.2f seconds\n Reception by anchor:" % (total_readings, duration)
    percent = ""
    update_rate = ""
    anchor_ids = ""
    for anchor_id in experiment.anchors:
        anchor_percent = 100 * float(anchor_reading_counts[anchor_id])/max_readings
        anchor_update_rate = anchor_reading_counts[anchor_id] / duration
        anchor_ids += "%5d " % anchor_id
        percent += "%4.0f%% " % (anchor_percent)
        update_rate += "%3.1fHz " % (anchor_update_rate)
    
    return "%s\n%s\n%s\n%s" % (heading, anchor_ids, update_rate, percent)

def draw_estimates(experiment, configuration_id, image):

    for ground_truth_id in experiment.ground_truth_ids():
        label, start_x, start_y, end_x, end_y, start_time, end_time = experiment.ground_truth_details(ground_truth_id)
        
        # Skip any "dynamic ground truth entries."
        if ">" in label:
            image.drawLineWorld((start_x, start_y), (end_x, end_y), colour="Blue")
        else:
            image.drawCircleWorld(start_x, start_y, 4, colour="Red")

        estimates, timestamps, errors, error_sizes = experiment.ground_truth_estimate_info(configuration_id, ground_truth_id)
        
        image.drawPoints(estimates, colour="Grey")
    
def draw_global_skew(experiment, configuration_id, image):
    
    for ground_truth_id in experiment.ground_truth_ids():
        label, start_x, start_y, end_x, end_y, start_time, end_time = experiment.ground_truth_details(ground_truth_id)
        
        # Skip any "dynamic ground truth entries."
        if ">" in label:
            continue
        estimates, timestamps, errors, error_sizes = experiment.ground_truth_estimate_info(configuration_id, ground_truth_id)
        
        ex = [e[0] for e in estimates]
        ey = [e[1] for e in estimates]
        
        x = numpy.median(ex)
        y = numpy.median(ey)

        image.drawLineWorld((start_x, start_y), (x, y), colour=(200,200,200))
        image.drawCircleWorld(start_x, start_y, 4, colour="Red")
        image.drawPoints(estimates, colour="Grey")


def analyze_by_ground_truth_id(experiment, configuration_id, configuration_name):
    ""

    if not os.path.exists(configuration_name):
        os.mkdir(configuration_name)
    if not os.path.isdir(configuration_name):
        raise Exception("%s exists, but is not a directory.")

    for ground_truth_id in experiment.ground_truth_ids():
        label, start_x, start_y, end_x, end_y, start_time, end_time = experiment.ground_truth_details(ground_truth_id)

        print "\nGround truth %s:" % label

        estimates, timestamps, errors, error_sizes = experiment.ground_truth_estimate_info(configuration_id, ground_truth_id)
        
        print dump_anchor_reception(experiment, ground_truth_id)

        pylab.cla()
        plot_error_scatter(experiment, configuration_id, ground_truth_id)
        filename = "%s/ErrorScatter-%d.png" % (configuration_name, ground_truth_id)
        fig = open(filename, "w")
        pylab.savefig(fig)

        pylab.cla()
        plot_moving_estimates(experiment, configuration_id, ground_truth_id)
        filename = "%s/EstimateTrail-%d.png" % (configuration_name, ground_truth_id)
        fig = open(filename, "w")
        pylab.savefig(fig)
        

def plot_percentile_errors(experiment, configuration_id, label=""):
  
    sql = "SELECT configuration_name, locmod_name FROM configuration WHERE id = %d" % configuration_id
    config_name, locmod_config_name = experiment.query(sql).fetchone()
  
    sql = "SELECT error FROM estimate WHERE configuration_id = %d" % configuration_id
    errors = [row["error"] for row in experiment.query(sql)]
    
    print configuration_id, config_name, locmod_config_name, len(errors)
    
    errors.sort()
    percentile = [float(i)/len(errors) for i in range(len(errors))]
                
    pylab.plot(percentile, errors, label=label)

if __name__ == "__main__":
    
    ##############################
    # Command line options.
    ##############################

    option_parser = OptionParser()

    option_parser.add_option("-p", "--percentile", dest="percentile", default=False, action="store_true",
                             help="Plot the percentile error for the given experiments")
    option_parser.add_option("-r", "--report", dest="report", default=False, action="store_true",
                             help="Make up a report, by ground truth ID for each configuration.")
    
    option_parser.add_option("-c", "--configuration_ids", dest="configuration_ids",
                             help="The configuration IDs (separated by commas), experiments separated by colons (e.g 1,2,3:2,3:4)")
    
    options, args = option_parser.parse_args()
    
    configuration_ids_by_experiment = {}
    if options.configuration_ids:
        for i, configuration_ids in enumerate(options.configuration_ids.split(":")):
            configuration_ids_by_experiment[i] = map(int, configuration_ids.split(","))    
    
    if options.report:
        config = Config()
        backend_api = config.load_rtls()
    
    for i, experiment_filename in enumerate(args):
        experiment = load_experiment(experiment_filename)    
        experiment_dir, experiment_name = os.path.split(experiment_filename)
        
        configuration_ids = configuration_ids_by_experiment.get(i)
        if not configuration_ids:
            configuration_ids = experiment.configuration_ids()

        for configuration_id in configuration_ids:
            configuration_name = "%s-%d" % (experiment_name, configuration_id)
            
            if options.percentile:
                try:
                    plot_percentile_errors(experiment, configuration_id, label=configuration_name)
                except Exception, e:
                    print "Error plotting percentile error for %s" % (configuration_name)
                    print e
                    
            if options.report:
                analyze_by_ground_truth_id(experiment, configuration_id, configuration_name)

                image = backend_api.get_default_map(1)
                draw_global_skew(experiment, configuration_id, image)
                image.save("%s/Skew.png" % configuration_name)
                
                image = backend_api.get_default_map(1)
                draw_estimates(experiment, configuration_id, image)
                image.save("%s/Estimates.png" % configuration_name)
                
                
                
            
    if options.percentile:
        pylab.title("Percentile Error")
        pylab.xlabel("Percentile")
        pylab.ylabel("Error (m)")

        pylab.legend()
        pylab.show()
