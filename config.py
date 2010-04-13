"""
Configuration for Almada

For now, all configuration is contained in two files
1) Main configuration (should accurately reflect the setup when run): Bases, Server Addresses, References points
2) LocMod configuration (settings for the location algorithms): Engine type, filter parameters, etc.

It would make sense to re-run an experiment with several different LocMod configurations to see which performs best.
It makes less sense to re-run an experiment with modified Main configuration.

The Main configuration file is nescessary, otherwise the location of the bases is unknown (without which, the location algorithm will fail).
The LocMod configuration is optional: default settings are provided.
"""

import os
import logging

from RTLS.PyFrontend.rtls_interface import RTLS

DEFAULT_IFD_PORT = 9393
DEFAULT_RTLS_URL = "http://localhost:8080/api"

class ConfigError(Exception):
    """Exception for configuration errors"""
    def __init__(self, msg):
        super(ConfigError, self).__init__()
        self.msg = msg

    def __repr__(self):
        
        return self.msg

    def __str__(self):
        
        return self.msg

class Config(object):
    
    """Configuration for Almada"""
    
    def __init__(self):
        super(Config, self).__init__()
        
        self.location_server_hostname = ""
        self.location_server_port = 6868
        
        self.lat_server_hostname = ""
        self.lat_server_port = 9292
        
        self.infield_device_port = DEFAULT_IFD_PORT
        
        self.anchors = {}
        self.tag_ids = []
        
        self.reference_points = {}
        
        self.location_engine_type = ""

        # Dictionaries of arguments for instantiation
        self.distance_filter = {}
        self.position_filter = {}
        self.location_engine = {}
        self.particle_filter = {}
                        
        # The filename, and contents of the configuration files used
        self.filename = ""
        self.text = ""
        self.locmod_filename = ""
        self.locmod_text = ""
             
    def load_rtls(self, api_url=DEFAULT_RTLS_URL, arena_id=1):
        "Load the configuration from an RTLS server with API at given url"
                        
        backend_api = RTLS(api_url)
        arena_id_names = backend_api.get_arenas()
        if arena_id_names:        
            if arena_id == None:
                if len(arena_id_names) == 1:
                    arena_id, arena_name = arena_id_names[0]
                else:
                    arenas = [("%d: %s" % (arena_id, arena_name)) for arena_id, arena_name in arena_id_names]
                    logging.error("Arena ID not given. Choose from... %s" % (", ".join(arenas)))
                    return
            
            
            self.anchors = backend_api.get_anchors(arena_id)                 
            self.min_x, self.max_x, self.min_y, self.max_y = backend_api.get_arena_bounds(arena_id)
            
            self.backend_api = backend_api
            return backend_api
                                                                  
    def load_file(self, filename, working_dir="."):
        "Load the configuration from a file"

        path = os.path.join(working_dir, filename)
        self.filename = filename
        self.text = open(path).read()
        
        for linenum, line in enumerate(open(path).readlines()):
            meat = line.strip()
            if meat.find("#") >= 0:
                meat = meat[:meat.find("#")].strip()
            
            if not meat:
                continue
            
            try:
                label, config = meat.split(":")
            
                if label.lower() == "anchor":
                    anchor_id, location = config.split(";")
                    anchor_id = int(anchor_id)
                    location = map(float, location.split(","))
                    self.anchors[anchor_id] = location
                
                elif label.lower() == "tag":
                    tag_id = int(config)
                    if not tag_id in self.tag_ids:
                        self.tag_ids.append(tag_id)
                    
                elif label.lower() == "reference":
                    name, location = config.split(";")
                    name = name.strip()
                    location = map(float, location.split(","))
                    self.reference_points[name] = location
                
                elif label.lower() == "locationserver":
                    hostname, port = config.split(",")
                    self.location_server_hostname = hostname.strip()
                    self.location_server_port = int(port)

                elif label.lower() == "latserver":
                    hostname, port = config.split(",")
                    self.lat_server_hostname = hostname.strip()
                    self.lat_server_port = int(port)
                    
                elif label.lower() in ["min_x", "max_x", "min_y", "max_y"]:
                    value = float(config)
                    self.__setattr__(label.lower(), value)

                else:
                    logging.error("Unrecognised configuration label on line %d: %s" % (linenum + 1, label))
                    
            except ConfigError, config_error:
                raise config_error
                    
            except Exception, e:
                logging.error("%s" % str(e))
                raise ConfigError("Error in configuration file (%s) on line %d: %s" % (path, linenum + 1, line.strip()))

    def load_locmod_file(self, filename, working_dir="."):
        """
        Load the locmod configuration for a particular
        
        Valid entries for a LocMod configuration file:
        Name: <the name>
        EngineType: <LocationEnginePDF|LEDLL|LocationEngineMatch>
        
        Or any of
        ParticleFilter:
        DistanceFilter:
        LocationEngine:
        PositionFilter:
        Each followed by any parameters accepted by the relevant modules.
        """
        
        path = os.path.join(working_dir, filename)
        self.locmod_filename = filename
        self.locmod_text = open(path).read()
                
        dictionaries = {"particlefilter": self.particle_filter, 
                        "distancefilter": self.distance_filter, 
                        "positionfilter": self.position_filter,
                        "locationengine": self.location_engine}
        
        current_dict = None
        
        for linenum, line in enumerate(open(path).readlines()):
            
            meat = line.strip()
            if meat.find("#") >= 0:
                meat = meat[:meat.find("#")].strip()
            
            if not meat:
                continue
                
            try:
                label, config = meat.split(":")
                label = label.strip().lower()
                config = config.strip()

                if label in dictionaries:
                    current_dict = label

                elif label == "enginetype":
                    self.location_engine_type = config
                    current_dict = None
                                        
                else:
                    if current_dict:
                        dictionaries[current_dict][label] = config
                    else:
                        raise ConfigError("Setting for unrecognized label (%s: %s) outside dictionary" % (label, config))
                        
            except Exception, e:
                raise ConfigError("Error in LocMod configuration file (%s) on line %d: %s\nError: %s" % (filename, linenum + 1, line.strip(), str(e)))
                
        


if __name__ == "__main__":
    
    config = Config()
    try:
        config.load_file("almada.cfg")
    except ConfigError, e:
        print e.msg
        print str(e)
    
