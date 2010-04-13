
import logging

class GroundTruthAction(object):
    "GroundTruthAction"
    
    arrived_code = "Arrived"
    passed_code = "Passed"
    abandoned_code = "Abandoned"
    heading_code = "Heading"
    
class PartialGroundTruth(object):
    """Simple class for holding on to the information """

    def __init__(self, experiment, tag_id, location, label, code):
        super(PartialGroundTruth, self).__init__()
        self.tag_id = tag_id
        self.label = label
        self.location = location
        self.code = code
        self.experiment = experiment

        #Start the ground truth in the database
        self.ground_truth_id = self.experiment.start_ground_truth(tag_id, label, location)
        
    def finalise(self, label, code, location):
        "End or cancel the ground truth in the database depending on what's appropriate."

        logging.info("Finalising ground truth for tag %d: %s > %s" % (self.tag_id, self.label, label))

        if code in [GroundTruthAction.abandoned_code, GroundTruthAction.heading_code] and self.code == GroundTruthAction.arrived_code:
            # Static ground truth
            if label == self.label:
                self.experiment.end_ground_truth(self.ground_truth_id)
                return
                
        elif code in [GroundTruthAction.passed_code, GroundTruthAction.arrived_code] and self.code in [GroundTruthAction.heading_code, GroundTruthAction.passed_code]:
            # Moving ground truth
            if label != self.label:
                self.experiment.end_ground_truth(self.ground_truth_id, location, "%s>%s" % (self.label, label))
                return
            
        logging.warning("Canceling ground truth %d (%s - %s)" % (self.ground_truth_id, self.label, label))
        self.experiment.cancel_ground_truth(self.ground_truth_id)
