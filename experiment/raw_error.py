"""
Compare

"""

import os, sys
import glob
import numpy
import experiment.experiment_db as db
import experiment.analyze_experiment as analyze

from Almada.config import Config

def load_experiment(path):
    return db.load_experiment(path)
    
base_dir = "/Users/philip/Documents/Projects/FieldTrials/"
experiment_dirs = [#"DeakinWalk", 
                   "DeakinWalk2"]
experiment_files = []
for experiment_dir in experiment_dirs:
    glob_pattern = base_dir + experiment_dir + "/*.db"
    files = glob.glob(glob_pattern)
    experiment_files.extend(files)

print experiment_files

for experiment_file in experiment_files:
    
    experiment_dir, filename = os.path.split(experiment_file)
    base_dir, sub_dir = os.path.split(experiment_dir)
    
    experiment_name = os.path.join(sub_dir, filename)
    experiment = load_experiment(experiment_file)

    d, g = analyze.distance_versus_ground_truth(experiment)
    distance = numpy.array(d)
    ground_truth = numpy.array(g)
    error = distance - ground_truth

    #pylab.hist(error, 20, normed=1)
    
    pylab.hist(error, 20, normed=1, histtype="step", label=experiment_name)
    
pylab.legend()