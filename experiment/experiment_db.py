#!/usr/bin/env python
"""
Keep track of all the core information related to an experiment.

Data is stored in SQLite tables.

Core Data captured live are the tag-anchor distance estimates, the anchor informatino, and the tag ground truth info.

Other information relates to particular location estimates made. This can be re-generated later.

Philip Blackwell 2009-09-18
"""

import os
import sqlite3
import math
import logging

from Almada.clock import shared_clock as clock
from Almada.experiment.schema import create_database
from Almada.experiment.ground_truth import PartialGroundTruth, GroundTruthAction
    
class Experiment(object):
    """An interface to the SQLite database underlying an experiment."""
    
    def __init__(self, connection):
        super(Experiment, self).__init__()
        self.connection = connection
        self.cursor = connection.cursor()
        self.connection.row_factory = sqlite3.Row
        self.configuration_id = None
        self.anchors = {}
        self.load_anchors()
        self.partial_ground_truths = {}
      
    def query(self, *args):
        "A cursor with the select statement performed."
        cursor = self.connection.cursor()
        cursor.execute(*args)
        return cursor
      
    def load_anchors(self):
        "Load the anchors described in the database into a dictionary, for easy access."
        anchors = self.query("SELECT * FROM anchor")
        for anchor in anchors:
            self.anchors[anchor["id"]] = anchor["x"], anchor["y"]
      
    last_rowid_sql = "SELECT last_insert_rowid()"
    def last_rowid(self):
        return self.cursor.execute(self.last_rowid_sql).fetchone()[0]
        
    def insert(self, *args):
        "Insert and commit according to the statement, return the row ID."
                                
        self.cursor.execute(*args)
        result = self.last_rowid()
        self.connection.commit()
        return result

    tag_ids_sql = "SELECT DISTINCT tag_id FROM distance_reading"
    def tag_ids(self):
        "A list of all the tag IDs"
        
        rows = self.query(self.tag_ids_sql)
        
        return [row[0] for row in rows]
        
    add_reading_sql = "INSERT INTO distance_reading (anchor_id, tag_id, distance, ground_truth_id, timestamp) VALUES (?, ?, ?, ?, ?)"
    def add_reading(self, anchor_id, tag_id, distance, ground_truth=None):
        "Add a reading, now. Don't worry about comparing to the ground truth distance."
        
        self.cursor.execute(self.add_reading_sql, (anchor_id, tag_id, distance, ground_truth, clock.get_time()))
        self.connection.commit()

    def add_readings(self, tag_id, distances, ground_truth_id=None):
        "Like add reading for many readings, but all with an identical timestamp."
        timestamp = clock.get_time()
        for anchor_id, distance in distances:
            self.cursor.execute(self.add_reading_sql, (anchor_id, tag_id, distance, ground_truth, timestamp))

    add_full_reading_sql = "INSERT INTO distance_reading (anchor_id, tag_id, distance, ground_truth_id, ground_truth_distance, ground_truth_error, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)"
    def add_full_reading(self, anchor_id, tag_id, distance, ground_truth_id, ground_truth_distance, ground_truth_error, timestamp):
        "Add the full details of a reading."

        self.cursor.execute(self.add_full_reading_sql, (anchor_id, tag_id, distance, ground_truth_id, ground_truth_distance, ground_truth_error, timestamp))
        self.connection.commit()

    add_anchor_sql = "INSERT INTO anchor (id, x, y) VALUES (?, ?, ?)"
    def add_anchor(self, anchor_id, location):
        
        self.anchors[anchor_id] = location
        x, y = location
        self.cursor.execute(self.add_anchor_sql, (anchor_id, x, y))
        self.connection.commit()
    
    clear_ground_truth_distance_anchor_sql = "UPDATE distance_reading SET ground_truth_distance = NULL WHERE anchor_id = ?"
    update_anchor_sql = "UPDATE anchor SET x = ?, y = ? WHERE id = ?"
    def update_anchor(self, anchor_id, location):
        
        if not anchor_id in self.anchors:
            self.add_anchor(anchor_id, location)
            return

        old_x, old_y = self.anchors[anchor_id]
        self.anchors[anchor_id] = location
        x, y = location
        
        logging.warning("Updating location for anchor %d: %.2f,%.2f (Was %.2f,%.2f)" % (anchor_id, x, y, old_x, old_y))
        self.cursor.execute(self.update_anchor_sql, (x, y, anchor_id))
        logging.warning("Clearing ground truth distances for anchor %d" % anchor_id)
        self.cursor.execute(self.clear_ground_truth_distance_anchor_sql, (anchor_id,))
        
        self.connection.commit()
        
    
    add_ground_truth_sql = "INSERT INTO ground_truth (label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    def add_ground_truth(self, label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y):
        self.cursor.execute(self.add_ground_truth_sql, (label, tag_id, start_time, end_time, start_x, start_y, end_x, end_y))
        ground_truth_id = self.last_rowid()
        self.connection.commit()
        
        return ground_truth_id
        
    start_ground_truth_sql = "INSERT INTO ground_truth (label, tag_id, start_time, start_x, start_y) VALUES (?, ?, ?, ?, ?)"
    def start_ground_truth(self, tag_id, label, location):
        
        x, y = location
        self.cursor.execute(self.start_ground_truth_sql, (label, tag_id, clock.get_time(), x, y))
        ground_truth_id = self.last_rowid()
        self.connection.commit()
        
        return ground_truth_id
        
    end_ground_truth_sql = "UPDATE ground_truth set end_time = ?, end_x = ?, end_y = ? WHERE id = ?"
    update_ground_truth_label_sql = "UPDATE ground_truth set label = ? WHERE id = ?"
    def end_ground_truth(self, ground_truth_id, location=None, label=None):
        if location == None:
            x, y = None, None
        else:
            x, y = location
        self.cursor.execute(self.end_ground_truth_sql, (clock.get_time(), x, y, ground_truth_id))
        if label != None:
            self.cursor.execute(self.update_ground_truth_label_sql, (label, ground_truth_id))
        
        self.connection.commit()
        
    cancel_ground_truth_sql = ["DELETE FROM ground_truth WHERE id = ?;",
                              "UPDATE distance_reading set ground_truth_id = NULL WHERE ground_truth_id = ?;",
                              "UPDATE estimate set ground_truth_id = NULL WHERE ground_truth_id = ?;"]
    def cancel_ground_truth(self, ground_truth_id):
        for statement in self.cancel_ground_truth_sql:
            self.cursor.execute(statement, (ground_truth_id,))
        self.connection.commit()
       
    distance_readings_sql = "SELECT * FROM distance_reading ORDER BY timestamp"
    def distance_readings(self):
        "An iterator over the readings."
        
        cursor = self.connection.cursor()
        cursor.execute(self.distance_readings_sql)
        
        return cursor
        
    observations_sql = "SELECT anchor_id, tag_id, distance, timestamp FROM distance_reading ORDER BY timestamp"
    def observations(self, tag_ids=None, anchor_ids=None):
        "An iterator of four tuples; tag_id, dictionary of distance reading by anchor_id, ground truth (x, y), and timestamp."
        
        if anchor_ids == None:
            anchor_ids = self.anchors.keys()
            
        if tag_ids == None:
            tag_ids = self.tag_ids()
        
        cursor = self.connection.cursor()
        distance_readings = cursor.execute(self.observations_sql)
        
        timestamps = {} # The last timestamp we have, by tag
        observations = {} # Dictionaries of anchor_id -> distance by tag_id
        for tag_id in tag_ids:
            observations[tag_id] = {}
        
        last_anchor_id = 0
                
        while distance_readings:
            
            try:
                anchor_id, tag_id, distance, timestamp = distance_readings.fetchone()
            except:
                break

            if not anchor_id in anchor_ids:
                logging.debug("Ignoring reading from unknown anchor: %d" % anchor_id)
                continue
            if not tag_id in tag_ids:
                logging.debug("Ignoring reading from unknown tag: %d" % tag_id)
                continue

            anchor_readings = observations[tag_id]

            if anchor_readings and anchor_id <= min(anchor_readings):
                # This means it's a fresh reading. Prepare the last entry for yield.
                
                location = self.ground_truth(tag_id, timestamps[tag_id])
                result = tag_id, anchor_readings, location, timestamps[tag_id]
                
                observations[tag_id] = {anchor_id: distance}
                timestamps[tag_id] = timestamp
                
                if location:
                    yield result
                else:
                    logging.debug("Ignoring observation of %d at %.2f; no ground truth" % (tag_id, timestamp))
            else:
                anchor_readings[anchor_id] = distance
                if timestamps.has_key(tag_id):
                    delta = timestamp - timestamps[tag_id]
                    if abs(delta > 0.1):
                        logging.debug("Timestamps for observation differ by %.2f" % delta)
                timestamps[tag_id] = timestamp
        
    
    ground_truth_details_sql = "SELECT label, start_x, start_y, end_x, end_y, start_time, end_time "\
                               "FROM ground_truth WHERE id = ?"
    def ground_truth_details(self, ground_truth_id):
    
        rows = self.query(self.ground_truth_details_sql, (ground_truth_id,)).fetchall()
        
        if not rows:
            return None
        
        if len(rows) > 1:
            raise Exception("More than one ground truth entry with ID %d" % ground_truth_id)
        
        return rows[0]

    ground_truth_ids_sql = "SELECT id FROM ground_truth"
    def ground_truth_ids(self):
        rows = self.query(self.ground_truth_ids_sql).fetchall()
        
        return [row[0] for row in rows]


    def ground_truth_id(self, tag_id, timestamp=None):
        
        if timestamp == None:
            timestamp = clock.get_time()
        
        sql = "SELECT id FROM ground_truth WHERE tag_id = ? AND start_time <= ? AND end_time > ?"
        rows = self.query(sql, (tag_id, timestamp, timestamp)).fetchall()
        
        if not rows:
            return None
            
        if len(rows) > 1:
            raise Exception("Tag %d at %.2f matches more than one ground truth (%d)" % (tag_id, timestamp, len(rows)))
            
        return rows[0][0]

    ground_truth_sql = "SELECT start_x, start_y, end_x, end_y, start_time, end_time FROM ground_truth "\
                       "WHERE tag_id = ? and start_time <= ? and end_time > ?"
    def ground_truth(self, tag_id, timestamp=None):
        
        if timestamp == None:
            timestamp = clock.get_time()
        
        cursor = self.connection.cursor()
        
        cursor.execute(self.ground_truth_sql, (tag_id, timestamp, timestamp))
        rows = cursor.fetchall()
        
        if not rows:
            return None
        
        if len(rows) > 1:
            print rows
            raise Exception("Tag %d at %.2f matches more than one ground truth (%d)" % (tag_id, timestamp, len(rows)))
            
        start_x, start_y, end_x, end_y, start_time, end_time = rows[0]
        
        # Static point
        if end_x == None and end_y == None:
            return start_x, start_y
        
        # Linear interpolation between the start and end points.
        alpha = (timestamp - start_time) / (end_time - start_time)
        dx = alpha * (end_x - start_x)
        dy = alpha * (end_y - start_y)
        x = start_x + dx
        y = start_y + dy
        
        return x, y
    
    tag_id_for_ground_truth_sql = "SELECT DISTINCT(tag_id) FROM ground_truth WHERE id = ?"
    def tag_id_for_ground_truth(self, ground_truth_id):
        
        rows = self.query(self.tag_id_for_ground_truth_sql, (ground_truth_id,)).fetchall()
        
        assert len(rows) == 1
        
        return rows[0][0]
        
    
    append_ground_truth_distance_sql = "UPDATE distance_reading set ground_truth_id = ?, ground_truth_distance = ?, ground_truth_error = ? WHERE id = ?"
    def append_ground_truth_distances(self):
        "Go through each distance reading, where ground truth is known add the ground truth distance and error."
    
        distance_readings = self.connection.cursor()
        distance_readings.execute("SELECT id, anchor_id, tag_id, distance, timestamp FROM distance_reading ORDER BY timestamp")
    
        for distance_reading in distance_readings:
            
            timestamp = distance_reading["timestamp"]
            tag_id = distance_reading["tag_id"]
            ground_truth_id = self.ground_truth_id(tag_id, timestamp)
            ground_truth = self.ground_truth(tag_id, timestamp)
            if ground_truth:
                gx, gy = ground_truth
                ax, ay = self.anchors[distance_reading["anchor_id"]]
                distance = math.hypot(gx - ax, gy - ay)
                error = distance_reading["distance"] - distance
                self.cursor.execute(self.append_ground_truth_distance_sql, (ground_truth_id, distance, error, distance_reading["id"]))
               
        self.connection.commit()
            
    def configuration_ids(self):
        
        sql = "SELECT id FROM configuration"
        return [row["id"] for row in self.query(sql)]
        
    def register_configuration(self, configuration_name="", configuration_text="", locmod_name="", locmod_text=""):        
        "Register a new configuration, which new estimates will be associated with."
        
        sql = "INSERT INTO configuration (configuration_name, configuration_text, locmod_name, locmod_text) VALUES (?, ?, ?, ?)"
        self.configuration_id = self.insert(sql, (configuration_name, configuration_text, locmod_name, locmod_text))

       
    def add_estimate(self, tag_id, x, y):
        "Add an estimate by the current location module."
        
        if self.configuration_id:
            sql = "INSERT INTO estimate(tag_id, x, y, timestamp, configuration_id) VALUES (?, ?, ?, ?, ?)"
            self.insert(sql, (tag_id, x, y, clock.get_time(), self.configuration_id))
        else:
            logging.warning("Ignored distance estimate because current configuration ID is not set.")
        
    
    def estimates(self, configuration_id):
        
        sql = "SELECT tag_id, x, y, timestamp FROM estimate WHERE configuration_id = ? ORDER BY timestamp"
        return self.query(sql, (configuration_id,))
        

    def ground_truth_estimate_info(self, configuration_id, ground_truth_id):
        "Four lists: estimates (x, y), timestamps, errors (dx, dy), error_sizes sqrt(dx^2 + dy^2)"
        
        tag_id = self.tag_id_for_ground_truth(ground_truth_id)
        
        estimates = []
        timestamps = []
        errors = []
        error_sizes = []
        
        sql = "SELECT x, y, timestamp FROM estimate WHERE configuration_id = ? AND ground_truth_id = ? ORDER BY timestamp ASC"
        for x, y, timestamp in self.query(sql, (configuration_id, ground_truth_id)).fetchall():
            gx, gy = self.ground_truth(tag_id, timestamp)
            ex = x - gx
            ey = y - gy
            e = math.hypot(ex, ey)
            
            estimates.append((x, y))
            timestamps.append(timestamp)
            errors.append((ex, ey))
            error_sizes.append(e)

        return estimates, timestamps, errors, error_sizes

    def clear_generated_data(self, configuration_id=None):
        """Clear all estimate data (leave distance_reading, anchor and ground truth tables.)"""
        
        delete_estimates_sql = "DELETE FROM estimate;"
        delete_configurations_sql = "DELETE FROM configuration";
        
        if configuration_id:
            delete_estimates_sql += " WHERE configuration_id = %d" % configuration_id
            delete_configurations_sql += " WHERE id = %d" % configuration_id
            
        logging.warning(delete_estimates_sql)
        logging.warning(delete_configurations_sql)
        self.cursor.execute(delete_estimates_sql)
        self.cursor.execute(delete_configurations_sql)
        self.cursor.execute("VACUUM;")
        self.connection.commit()
        
    def apply_ground_truth_info(self, tag_id, location, action, reference_name):
        """Take note of new ground truth info
        
        tag_id - ID of the given tag.
        location - Location (x, y) of the given tag
        action - The GroundTruthAction code (arrive, leave, pass, abandon)
        reference_name - The text name of the relavent reference point
        
         For example, tag A arrived at reference point B (x, y)
        """
        
        if tag_id in self.partial_ground_truths:
            partial_ground_truths = self.partial_ground_truths[tag_id]
            partial_ground_truths.finalise(reference_name, action, location)
            del self.partial_ground_truths[tag_id]
            
        if not action == GroundTruthAction.abandoned_code:
            self.partial_ground_truths[tag_id] = PartialGroundTruth(self, tag_id, location, reference_name, action)

def new_experiment(filename):
    "Create and return a new experiment object from the given database"
    
    if os.path.exists(filename):
        raise Exception("Database file already exists: %s" % filename)
    
    connection = sqlite3.connect(filename)
    cursor = connection.cursor()
    create_database(cursor)
    cursor.close()
    
    return Experiment(connection)

def load_experiment(filename):
    "Load an experiment object from an existing database."
    
    if os.path.exists(filename):
        connection = sqlite3.connect(filename)
        return Experiment(connection)
    
    
if __name__ == "__main__":

    import sys
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-e", "--experiment", dest="experiment",
                      help="The sqlite database file for the experiment.", metavar="FILE")
    parser.add_option("-n", "--new",
                    action="store_true", dest="new", default=False,
                    help="Create a new database in the given experiment file.")
    parser.add_option("-c", "--clear",
                      action="store_true", dest="clear", default=False,
                      help="Clear estimates from the database (For a particular configuration ID if given).")
    parser.add_option("-d", "--dump", type="int", dest="configuration_id",
                      help="Dump the results for the configuration with %metavar", metavar="CONFIG_ID")
    parser.add_option("-l", "--list", action="store_true", default=False,
                      help="List the available configurations")

    (options, args) = parser.parse_args()
    
    if not options.experiment:
        sys.exit("No experiment file. Seek help (-h).")
    
    if options.new:
        if os.path.exists(options.experiment):
            sys.exit("File exists: %s" % options.experiment)
        
        experiment = new_experiment(options.experiment)
        sys.exit()
    
    experiment = load_experiment(options.experiment)
    
    if options.clear:
        experiment.clear_generated_data()
        sys.exit()
        
    if options.list:
        configuration_ids = experiment.configuration_ids()
        for configuration_id in configuration_ids:
            sql = "SELECT configuration_name, locmod_name FROM configuration WHERE id = %d" % configuration_id
            config_name, locmod_config_name = experiment.query(sql).fetchone()
            print "%d: %s - %s" % (configuration_id, config_name, locmod_config_name)
    
    
