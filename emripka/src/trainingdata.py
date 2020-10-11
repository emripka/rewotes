import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import json
from os import listdir
from os.path import isfile, join
import sys
sys.path.insert(1, "../src/")
from converters import csv_to_json
from stoichiometry import get_norm_stoichiomertry
from converters import create_non_numeric_map

def create_id():
    # to-do: need to make this a unique value wrt all user data made and stored
    return "user-%05d" % np.random.randint(0,99999)  

class TrainingData:
    """
    User input training data class.
    """
    def __init__(self,formula,spacegroup="",formation_energy=0.0,E_above_hull=0.0,band_gap=0.0,has_bandstructure=False,
                    volume=0.0,Nsites=0,theoretical=False,count=0.0,density=0.0,crystal_system=""):
        self.ID = create_id() 
        self.formula = formula
        self.spacegroup = spacegroup 
        self.formation_energy = formation_energy 
        self.E_above_hull = E_above_hull 
        self.band_gap = band_gap 
        self.has_bandstructure = has_bandstructure 
        self.volume = volume 
        self.Nsites = Nsites 
        self.theoretical = theoretical 
        self.count = count 
        self.density = density 
        self.crystal_system = crystal_system 
        self.data_dict = dict() 

    def make_data_dict(self):
        data_dict = {
            self.ID: {
                "formula": self.formula,
                "spacegroup": self.spacegroup,
                "formation_energy__eV": self.formation_energy,
                "E_above_hull__eV": self.E_above_hull,
                "band_gap__eV": self.band_gap,
                "has_bandstructure": self.has_bandstructure,
                "volume": self.volume,
                "Nsites": self.Nsites,
                "theoretical": self.theoretical,
                "count": self.count,
                "density__gm_per_cc": self.density,
                "crystal_system": self.crystal_system 
            }
        }
        self.data_dict = data_dict

    def show_data(self):
        self.make_data_dict()
        print(self.data_dict)

    def store_data(self):
        """ This method will store the user training data to the data directory."""
        self.make_data_dict()

        json_path = "../data/training/materialsproject_json/"

        # open the existing user_data.json file
        with open(f"{json_path}/user_data.json","r") as fname:
            try:
                user_data = dict(json.load(fname))
            except:
                user_data = dict() 
        fname.close()

        user_data[self.ID] = self.data_dict[self.ID]
        with open(f"{json_path}/user_data.json","w") as fname:
            json.dump(user_data,fname,indent=4)
        fname.close()

class BandGapDataset:
    def __init__(self,csv_path,json_path):
        self.csv_path = csv_path
        self.json_path = json_path
        self.data_dict = dict()
        self.data_IDs = list() 
        self.bad_formulas_IDs = list()
        self.convert_stored_csvs() 
        self.get_stored_data()
        self.set_stoichiometry()

    def convert_stored_csvs(self):
        csv_files = [f for f in listdir(self.csv_path) if isfile(join(self.csv_path, f))]
        json_files = [f for f in listdir(self.json_path) if isfile(join(self.json_path, f))]

        csv_files_stripped = [f.split(".csv")[0] for f in csv_files]
        json_files_stripped = [f.split(".json")[0] for f in json_files]

        for csv_file in csv_files_stripped:
            if csv_file not in json_files_stripped:
                csv_to_json(self.csv_path,self.json_path,fname=csv_file)
                print(f"created {csv_file}.json")

    def get_stored_data(self):
        json_files = [f for f in listdir(self.json_path) if isfile(join(self.json_path, f))]
        training_compounds = [f.split(".json")[0] for f in json_files]

        for training_compound in training_compounds:
            with open(f"{self.json_path}/{training_compound}.json") as fname:
                training_compound_results = dict(json.load(fname))
                for ID, training_compound_result in training_compound_results.items():
                    self.data_dict[ID] = training_compound_result

        self.data_IDs = list(self.data_dict.keys())

    def set_stoichiometry(self):
        for ID, result in self.data_dict.items():
            formula = result["formula"]
            if "(" not in formula:
                norm_stoichiometry = get_norm_stoichiomertry(formula)
                self.data_dict[ID]["stoichiometry"] = norm_stoichiometry
            else:
                self.bad_formulas_IDs.append(ID)

        for ID in self.bad_formulas_IDs:
            del self.data_dict[ID]

class BandGapDataFrame:
    def __init__(self, data_dict, symbols,material_training_params):
        self.data_dict = data_dict
        self.symbols = symbols
        self.crystal_system_map = dict()
        self.spacegroup_map = dict()
        # create new dictionary
        self.data_dict_clean = {
            "ID": [ ID for (ID, result) in self.data_dict.items() ],
        }
        self.non_element_keys = ["band_gap__eV",]
        for param in material_training_params:
            self.non_element_keys.append(param)
        self.populate_data_dict_clean()

        # create dataframe from data_dict_clean 
        self.dataframe = pd.DataFrame(self.data_dict_clean) 
        # dropping rows which have a bandgap of zero
        # not sure if I want to do this...
        self.dataframe = self.dataframe[self.dataframe['band_gap__eV'] != 0]

    def populate_data_dict_clean(self):
        for non_element_key in self.non_element_keys:
            self.data_dict_clean[non_element_key] = [result[non_element_key] for (ID, result) in self.data_dict.items() ] 

        for symbol in self.symbols:
            self.data_dict_clean[symbol] = list() 

        self.populate_stoichiometry()

        if "crystal_system" in self.non_element_keys: 
            self.crystal_system_map = create_non_numeric_map(self.data_dict_clean, "crystal_system")
            self.data_dict_clean["crystal_system"] = [self.crystal_system_map[value] for value in self.data_dict_clean["crystal_system"] ] 

        if "spacegroup" in self.non_element_keys: 
            self.spacegroup_map = create_non_numeric_map(self.data_dict_clean, "spacegroup")
            self.data_dict_clean["spacegroup"] = [self.spacegroup_map[value] for value in self.data_dict_clean["spacegroup"] ] 
    
    def populate_stoichiometry(self):
        # populate the dictionary with keys of all symbols of elements
        for ID, result in self.data_dict.items():
            elements = list(result["stoichiometry"].keys())   
            for symbol in self.symbols:
                value = result["stoichiometry"][symbol] if symbol in elements else 0
                self.data_dict_clean[symbol].append(value)

    def get_train_test_splits(self):
        X_keys = list(self.dataframe.keys())[2:]

        X = np.asarray(self.dataframe[X_keys])
        y = np.asarray(self.dataframe['band_gap__eV'])
                
        return train_test_split(X, y, test_size=0.33, shuffle= True) 
