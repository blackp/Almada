#!/usr/bin/env python

"""
The schema for the experiment database.

Philip Blackwell September 2009
"""

create_table_distance_reading_comment = """
# distance_reading Table:
# Each Tag-Anchor Distance reading as reported by the Base (with error code 0)
# If available, include the id of the relevant ground truth entry, along with the actual distance and error.
"""

create_table_distance_reading_sql = """
CREATE TABLE distance_reading (id INTEGER PRIMARY KEY,
                               anchor_id INTEGER(4),
                               tag_id INTEGER(4),
                               distance REAL,
                               ground_truth_id INTEGER,
                               ground_truth_distance REAL,
                               ground_truth_error REAL,
                               timestamp REAL);"""

create_table_anchor_comment = """
# anchor Table:
# x and y position (in meters) of each anchor.
"""
create_table_anchor_sql = """
CREATE TABLE anchor (id INTEGER PRIMARY KEY,
                     x REAL,
                     y REAL);"""

create_table_ground_truth_comment = """
# ground_truth Table:
# A ground truth entry describes a tags position over a period of time.
# The tags position is either static at a particular reference point (label is just the name of the reference point)
# Or moving from one reference point to another (label, contains the two reference points joined by a '>')
# The start position must be provided.
# The end position is only provided if the tag was moving from one reference point to another.
"""

create_table_ground_truth_sql = """
CREATE TABLE ground_truth (id INTEGER PRIMARY KEY,
                           label TEXT,
                           tag_id INTEGER,
                           start_time REAL,
                           end_time REAL,
                           start_x REAL,
                           start_y REAL,
                           end_x REAL,
                           end_y REAL);"""

create_table_configuration_comment = """
# configuration Table:
# Describe the configuration used for a particular run of the experiment
"""

create_table_configuration_sql = """
CREATE TABLE configuration(id INTEGER PRIMARY KEY,
                           configuration_name TEXT,
                           configuration_text TEXT,
                           locmod_name TEXT,
                           locmod_text TEXT);"""

create_table_estimate_comment = """
# estimate Table
# Each run of the experiment will generate a list of estimates.
"""

create_table_estimate_sql = """
CREATE TABLE estimate (id INTEGER PRIMARY KEY,
                       tag_id INTEGER,
                       x REAL,
                       y REAL,
                       timestamp REAL,
                       ground_truth_id INTEGER,
                       error REAL,
                       configuration_id);"""

create_database_sql = [create_table_distance_reading_sql, 
                       create_table_anchor_sql, 
                       create_table_ground_truth_sql,
                       create_table_configuration_sql,
                       create_table_estimate_sql]

def create_database(cursor):
    "Execute the sql to create the database."
    for statement in create_database_sql:
        cursor.execute(statement)
    
def dump_sql(f):
    "Dump the sql to create the database to the given file 'f'."

    for statement in create_database_sql:
        f.write ("%s\n" % statement)

if __name__ == "__main__":
    
    import sys
    dump_sql(sys.stdout)
    
