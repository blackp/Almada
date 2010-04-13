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
experiment_file = os.path.join(field_trials_dir, "DeakinWalk2/2.db")
    
experiment = load_experiment(experiment_file)
d, g = analyze.distance_versus_ground_truth(experiment)
distance = numpy.array(d)
ground_truth = numpy.array(g)
error = distance - ground_truth
e = list(error)

print len(e)

pylab.hist(e, 20, normed=1)