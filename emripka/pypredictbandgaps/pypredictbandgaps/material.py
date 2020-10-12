import pandas as pd
import numpy as np
from . import stoichiometry as stoichiometry 

class Material:
    def __init__(self,formula,spacegroup=None,formation_energy=None,E_above_hull=None,
                    volume=None,Nsites=None,density=None,crystal_system=None):
        self.formula = formula
        self.params = { 
            "spacegroup": spacegroup,
            "formation_energy__eV": formation_energy, 
            "E_above_hull__eV": E_above_hull,
            "volume": volume, 
            "Nsites": Nsites,
            "density__gm_per_cc": density,
            "crystal_system": crystal_system, 
        } 
        self.training_params = [ param for (param,value) in self.params.items() if value is not None ]

class MaterialPredictionData:
    """
    - the user creates an object of this type to use the package
    - takes in a MaterialsDatset type object which contains materials and their params to use for prediction
    - houses array of data to run through the model to predict the bandgap
    - also houses information needed to create the correct training data based on the user input
    """
    def __init__(self, material, symbols, periodic_table):
        self.symbols = symbols
        self.molecular_weight = stoichiometry.get_molecular_weight(material.formula, periodic_table)
        self.material_stoichiometry = stoichiometry.get_norm_stoichiomertry(material.formula)  
        self.prediction_data = [ value for (param, value) in material.params.items() if value is not None ]
        self.material_elements = list(self.material_stoichiometry.keys())   
        self.prediction_data.append(self.molecular_weight)
        for symbol in self.symbols:
            value = self.material_stoichiometry[symbol] if symbol in self.material_elements else 0
            self.prediction_data.append(value)