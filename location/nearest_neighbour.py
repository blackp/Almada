"""
nearest_neighbour.py

We have a large database of observations with known ground truth.

Within this database, we try to find the nearest neighbours of the current observation.

Philip Blackwell February 2010
"""

import os
import sqlite3
import math

class ObservationDatabase(object):
    """
    An sqlite implementation of the observation database defined above
    """
    
    last_rowid_sql = "SELECT last_insert_rowid()"

    create_observation_sql = """
    -- The Main table of observations.

    CREATE TABLE observation (id INTEGER PRIMARY KEY,
                              x REAL,
                              y REAL);
    """

    create_neighbour_sql = """
    -- The table which describes which observations are close to each other.
    -- Closeness is real world measure of how hard it would be to move from one location to another.

    CREATE TABLE neighbour (this INTEGER,
                            that INTEGER,
                            closeness REAL,
                            PRIMARY KEY (this, that));
    """

    create_distance_sql = """
    -- Observed distances (to each of the anchors) for each observation

    CREATE TABLE distance (observation_id INTEGER,
                           anchor_id INTEGER,
                           distance real,
                           PRIMARY KEY (observation_id, anchor_id));
    """

    create_anchors_sql = """
    -- The locations of the anchors
    
    CREATE TABLE anchor (id INTEGER PRIMARY KEY,
                         x REAL,
                         y REAL);
    
    """


    def __init__(self, filename):
        "The database is entirely contained in an sqlite3 file. Create it if it doesn't exist."
        super(ObservationDatabase, self).__init__()
        self.filename = filename

        if os.path.exists(filename):
            self.connection = sqlite3.connect(filename)
        else:
            self.connection = sqlite3.connect(filename)
            self.initialise()
        
    def initialise(self):
        "Create the tables."

        cursor = self.connection.cursor()
        for sql in [self.create_observation_sql, self.create_distance_sql, self.create_neighbour_sql, self.create_anchors_sql]:
            print sql
            cursor.execute(sql)
        cursor.close()
        self.connection.commit()

    def query(self, *args):
        "Execute a query statement (args as for cursor.execute). Return the result as a list of rows."
        
        cursor = self.connection.cursor()
        cursor.execute(*args)
        return cursor.fetchall()
        
    def insert(self, *args):
        "Execute an insert statement (args as for cursor.execute), and commit. Return the inserted row ID."

        cursor = self.connection.cursor()
        cursor.execute(*args)
        cursor.close()
        self.connection.commit()

        return cursor.lastrowid

    def new_observation(self, x, y):
        "Insert a new observation, return the new ID" 

        cursor = connection.cursor()

        sql = "INSERT INTO observation (x, y) VALUES (?, ?)"
        cursor.execute(sql, (x, y))

        cursor.execute(self.last_rowid_sql)
        return cursor.fetchone()[0]
            
    def add_distance(self, observation_id, anchor_id, distance):
        "Add a distance observation for an anchor."
        
        sql = "INSERT INTO distance (observation_id, anchor_id, distance) VALUES (?, ?, ?)"
        self.insert(sql, (observation_id, anchor_id, distance))

    def add_anchor(self, anchor_id, x, y):
        "Specify the x, y coordinates for an anchor."
        
        sql = "INSERT INTO anchor VALUES (?, ?, ?)"
        self.insert(sql, (anchor_id, x, y))
    
    def nearby(self, x, y, grid_size):
        "A dictionary of observation IDs near x, y (id -> (x, y))"

        sql = "SELECT id, x, y FROM observation WHERE ? <= x and x <= ? and ? <= y and y <= ?"

        l = x - grid_size
        r = x + grid_size
        t = y + grid_size
        b = y - grid_size

        result = {}
        for observation_id, x, y in self.query(sql, (l, r, b, t)):
            result[observation_id] = x, y

        return result
    
    def observation_ids(self):
        "All the IDs of all observations in the database."

        sql = "SELECT id FROM observation"
        return [row[0] for row in self.query(sql)]

    def observation_ids_with_anchor(self, anchor_id):
        "All the IDs of all observations by the given anchor."

        sql = "SELECT distinct(observation_id) FROM distance WHERE anchor_id = ?"
        return [row[0] for row in self.query(sql, (anchor_id,))]
        
    def observation_location(self, observation_id):
        "The x, y location of the given observation"
        
        sql = "SELECT x, y FROM observation WHERE id = ?"
        
        rows = self.query(sql, (observation_id,))
        
        if len(rows) == 1:
            x, y = rows[0]
            return x, y
        
    def distances(self, observation_id):
        "A dictionary of distances (by anchor_id) for an observation within the database."

        sql = "SELECT distance, anchor_id FROM distance WHERE observation_id = ?"        
        result = {}
        for distance, anchor_id in self.query(sql, (observation_id)):
            result[anchor_id] = distance
            
        return result
    
    def anchors(self):
        "A dictionary of anchors (anchor_id -> (x, y))."
        
        anchors_sql = "SELECT id, x, y FROM anchor"
    
        result = {}
        for anchor_id, x, y in self.query(anchors_sql):
            result[anchor_id] = x, y
            
        return result
        
    def anchor_ids(self):
        "A list of all anchor IDs."
        
        return self.anchors().keys()

    def score(self, observation, observation_id):
        """
        Compare a given observation against one in the database.
        
        observation - dictionary of anchor_id -> distance
        observation_id - the ID of the observation within the database to compare to
        min_readings - the minimum number of readings counted in the total.
        """
        
        total = 0.0
        n = 0
        
        distances = self.distances(observation_id)
        for anchor_id in observation:
            if anchor_id in distances:
                d = abs(distances[anchor_id] - observation[anchor_id])
                total += d
                n += 1
            
        if n < self.min_readings:
            return None
        
        return total / n
     
    def nearest(self, observation):
        "ID of the nearest observation in the database. Brute force search."
        
        best_score = 10e6
        best_observation = None
        
        for observation_id in self.observation_ids():
            score = self.score(observation, observation_id)
        
            if score < best_score:
                best_score = score
                best_observation = observation_id
                
        return best_observation


class CanonicalObservationDatabase(ObservationDatabase):
    """
    An observation database where 'canonical' observations are spread out evenly across a grid.
    
    There may be many distance observations from any one anchor associated with a particular 'canonical' observation.
    """

    create_distance_sql = """
    -- Observed distances (to each of the anchors) for each observation

    CREATE TABLE distance (observation_id INTEGER,
                           anchor_id INTEGER,
                           distance real);
    """

    create_settings_sql = """
    -- Miscellaneous settings for the database.

    CREATE TABLE settings (grid_size REAL);
    """


    def __init__(self, filename):
        
        ObservationDatabase.__init__(self, filename)
        self._grid_size = None
        
    def grid_size(self):
        "The distance between the 'canonical' observations (in both x and y)"
        
        if self._grid_size:
            return self._grid_size
        
        rows = self.query("SELECT grid_size FROM settings")
        if rows:
            self._grid_size = rows[0][0]
            return self._grid_size
            
        else:
            return None
        
    def initialise(self):
        "Create the tables."

        ObservationDatabase.initialise(self)

        cursor = self.connection.cursor()
        cursor.execute(self.create_settings_sql)
        cursor.close()
        self.connection.commit()

    def distances(self, observation_id, anchor_id):
        "A list of distances observations for a canonical observation by a given anchor"

        sql = "SELECT distance FROM distance WHERE observation_id = ? AND anchor_id = ?"
        
        rows = self.query(sql, (observation_id, anchor_id))
        return [row[0] for row in rows]

    def populate_observation_grid(self, min_x, max_x, min_y, max_y, grid_size):
        "Make a grid of canonical observations."

        if self.grid_size():
            raise Exception("Grid size already set.")
            
        self.insert("INSERT INTO settings (grid_size) VALUES (?)", (grid_size,))
        
        print self.grid_size(), grid_size
        
        cursor = self.connection.cursor()
        
        sql = "INSERT INTO observation (x, y) VALUES (?, ?)"
            
        n_x = int((max_x - min_x) / grid_size)
        n_y = int((max_y - min_y) / grid_size)
        
        for i in range(n_x):
            x = min_x + i * grid_size
            for j in range(n_y):
                y = min_y + j * grid_size
                
                cursor.execute(sql, (x, y))

        self.connection.commit()

    def trim(self, max_gap=0.10):
        "Remove redundant observation (no point keeping two observations closer than max_gap)"

        distances_sql = "SELECT rowid, distance FROM distance WHERE observation_id = ? AND anchor_id = ? ORDER BY distance ASC"
        delete_sql = "DELETE FROM distance WHERE rowid = ?"

        cursor = self.connection.cursor()

        for observation_id in self.observation_ids():
            for anchor_id in self.anchor_ids():
        
                rows = self.query(distances_sql, (observation_id, anchor_id))
        
                last_distance = -1.0
                for rowid, distance in rows:
                    if distance - last_distance < max_gap:
                        cursor.execute(delete_sql, (rowid,))
                    else:
                        last_distance = distance

        self.connection.commit()

    def observations_matching(self, anchor_id, distance, error):
        "A list of observation IDs with observations matching the given distance (+/- the given error)"
        
        sql = "SELECT DISTINCT observation_id FROM distance WHERE anchor_id = ? and ? <= distance and distance <= ?"
        
        rows = self.query(sql, (anchor_id, distance - error, distance + error))
        
        return [row[0] for row in rows]
        
    def best_matches(self, distances, error):
        "The observation IDs that best match the given dictionary of distances (anchor_id -> distance)"
        
        observation_scores = {} # The number of matching anchors, by observation_id
        
        for anchor_id, distance in distances.items():
            for observation_id in self.observations_matching(anchor_id, distance, error):
                if observation_id in observation_scores:
                    observation_scores[observation_id] += 1
                else:
                    observation_scores[observation_id] = 1
            
        # Make a list of the observation IDs with the best score.
        best_score = 0
        result = []
        for observation_id, score in observation_scores.items():
            if score > best_score:
                best_score = score
                result = []
            if score == best_score:
                result.append(observation_id)
                
        return result
                
    def possible_locations(self, distances, error):
        "Cloud of observation locations with example readings within the specified error given dictionary of distances"
        
        result = []
        
        for observation_id in self.best_matches(distances, error):
            result.append(self.observation_location(observation_id))
            
        return result
        
        
if __name__ == "__main__":
    
    from optparse import OptionParser

    usage = "usage: %prog [options] database1 database2..."
    option_parser = OptionParser(usage=usage)
    option_parser.add_option("-t", "--trim", dest="trim", default=False, action="store_true",
                             help="Trim the given (canonical) database(s) default %default.")

    options, args = option_parser.parse_args()
    
    if options.trim:
        for database_filename in args:
            print "Trimming database %s" % database_filename