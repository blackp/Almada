"""
Maths for modelling the distance estimates.
"""

import sys, os
import pickle
import logging

import numpy
import scipy.interpolate

def load_histogram(errors_filename="errors.pickle", histogram_filename="error_histogram.pickle"):
    
    if os.path.exists(histogram_filename):
        logging.info("Loading histogram from pickle: %s" % histogram_filename)
        p, bins = pickle.load(open(histogram_filename))
    elif os.path.exists(errors_filename):
        logging.info("Loading errors from pickle: %s" % errors_filename)
        errors = pickle.load(open(errors_filename))
        p, bins = numpy.histogram(errors, bins=20, normed=True)
        logging.info("Dumping histogram to pickle: %s" % histogram_filename)
        pickle.dump((p, bins), open(histogram_filename, "w"))
    else:
        return None
    
    return p, bins
                
histogram = load_histogram()

class DistanceModel(object):
    """DistanceModel"""
    def __init__(self, error_histogram=None):
        super(DistanceModel, self).__init__()
        if error_histogram == None:
            error_histogram = histogram
        p, bins = error_histogram
        x = [(bins[i] + bins[i+1]) / 2 for i in range(len(p))]
        self.pdf = scipy.interpolate.interp1d(x, p)
        self.min_x = min(self.pdf.x)
        self.max_x = max(self.pdf.x)

    def error_probability(self, error):
        ""

        if self.min_x <= error <= self.max_x:
            return self.pdf(error) 

        return 0.0
                
    def distance_probability(self, distance, estimated_distance):
        "What is the probability that a given distance gave rise to a particular estimate"

        error = estimated_distance - distance
        return self.error_probability(error)
                
class UniformDistanceModel(object):
    """docstring for UniformDistanceModel"""
    def __init__(self):
        super(UniformDistanceModel, self).__init__()
    
    def error_probability(self, error):
        if error > 0:
            return 1.0
        else:
            return 0.0
        
    def distance_probability(self, distance, estimated_distance):
        error = estimated_distance - distance
        return self.error_probability(error)

if __name__ == "__main__":

    if histogram == None:
        sys.exit("Error loading distance error histogram")
    
    distance_model = DistanceModel(histogram)
