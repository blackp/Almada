# Convenience functions for tinkering with an experiment file, preferably under "ipython -pylab"
# Philip Blackwell, Jan 2010

import os, sys
import numpy
import experiment.experiment_db as db
import experiment.analyze_experiment as analyze

from Almada.config import Config

def load_experiment(path):
    return db.load_experiment(path)
    
field_trials_dir = "/Users/philip/Documents/Projects/FieldTrials/"
experiment_file = os.path.join(field_trials_dir, "DeakinDense/combined.db")
    
experiment = load_experiment(experiment_file)
d, g = analyze.distance_versus_ground_truth(experiment)
distance = numpy.array(d)
ground_truth = numpy.array(g)
error = distance - ground_truth
e = list(error)


config = Config()
backend_api = config.load_rtls()

walls = analyze.count_walls_between(backend_api, experiment)

errors_by_walls = {}

for ground_truth_id in walls:
    walls_by_anchor = walls[ground_truth_id]
    for anchor_id, num_walls in walls_by_anchor.items():
        if not errors_by_walls.has_key(num_walls):
            errors_by_walls[num_walls] = []
        
        distance, ground_truth = analyze.distance_versus_ground_truth(experiment, anchor_id=anchor_id, ground_truth_id=ground_truth_id)
        d = numpy.array(distance)
        g = numpy.array(ground_truth)
        error = list(d - g)
        errors_by_walls[num_walls].extend(error)
        

ew = {}
for num_walls in errors_by_walls:
    ew[num_walls] = numpy.array(errors_by_walls[num_walls])
    ew[num_walls].sort()
    
w = errors_by_walls.keys()
w.sort()
    
n = 10

percentile_error = {}

for i in range(1, n):
    percentile_error[i] = []
    for num_walls in w:
        percentile = i * len(ew[num_walls]) / n
        e = ew[num_walls][percentile]
        percentile_error[i].append(e)
        
pylab.cla()
for i in range(n - 1, 0, -1):
    label = "%.2f%%" % (float(i)/n)
    pylab.plot(percentile_error[i][:-1], label=label)
#pylab.legend()
