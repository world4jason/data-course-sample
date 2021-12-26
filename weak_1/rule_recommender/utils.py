import pandas as pd
import subprocess
from tqdm import tqdm 
from typing import Union
import pathlib


class DatasetLoader:
    def __init__(self, 
                 data_file_name:str="All_Beauty.csv",
                 meta_data_file_name:str="meta_All_Beauty.json.gz",
                 base_file_folder:str="data",
                 make_dir:bool=False,
                ):
        self.data      = None
        self.meta_data = None
        
        self._data_url      = "http://deepyeti.ucsd.edu/jianmo/amazon/categoryFilesSmall/All_Beauty.csv"
        self._meta_data_url = "http://deepyeti.ucsd.edu/jianmo/amazon/metaFiles2/meta_All_Beauty.json.gz"
        
        self._data_file_name      = data_file_name
        self._meta_data_file_name = meta_data_file_name
        
        self.base_file_folder = base_file_folder
        
        pathlib.Path(self.base_file_folder).mkdir(parents=True, exist_ok=True) 
                        
    def download_dataset(self) -> bool :
        data_retcode = subprocess.call("wget {url} -O {file_path}/{file_name}".format(url=self._data_url,
                                                                                      file_path=self.base_file_folder, 
                                                                                      file_name=self._data_file_name),
                                        shell=True,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.STDOUT)
        meta_data_retcode = subprocess.call("wget {url} -O {file_path}/{file_name}".format(url=self._meta_data_url, 
                                                                                           file_path=self.base_file_folder, 
                                                                                           file_name=self._meta_data_file_name),
                                            shell=True,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.STDOUT)
        
        
        return not meta_data_retcode and not data_retcode
    
    def prepare_data(self) -> None:
        data_file_path      = pathlib.Path("{file_path}/{file_name}".format(file_path=self.base_file_folder, file_name=self._data_file_name))
        meta_data_file_path = pathlib.Path("{file_path}/{file_name}".format(file_path=self.base_file_folder, file_name=self._meta_data_file_name))
        
        if not data_file_path.exists():
            raise AssertionError("data path : {path} is not exist.".format(path=data_file_path))
            
        if not meta_data_file_path.exists():
            raise AssertionError("meta data path : {path} is not exist.".format(path=data_file_path))
            
        self.meta_data = self.read_json(data_file_path=meta_data_file_path, lines=True, compression='gzip')
        self.data      = self.read_csv(data_file_path=data_file_path, names=['asin', 'reviewerID', 'overall', 'unixReviewTime'], header=None)
        
    def read_json(self, data_file_path:str, **kwargs):
        return pd.read_json(path_or_buf=data_file_path, **kwargs)
    
    def read_csv(self, data_file_path:str, **kwargs) -> pd.DataFrame:
        return pd.read_csv(data_file_path, **kwargs)
    
    
class Dataset:
    def __init__(self, 
                 dataset_loader:DatasetLoader):
        
        self.ratings_trainings = None
        self.ratings_testings  = None
        
        self.ratings_testings_by_user=None
        
        self.ratings = dataset_loader.data
        self.meta_data = dataset_loader.meta_data
        
        
    def get_train_test(self, force_rearm=False):
        
        data_exist_condition = self.ratings_trainings is not None and self.ratings_testings is not None 
        
        if not data_exist_condition or force_rearm:
            self._train_test_split()
            self._generate_evaluation()
        
        return self.ratings_trainings, self.ratings_testings
    
    def get_evaluation_data(self):
        if self.ratings_testings_by_user is None:
            self._train_test_split()
            self._generate_evaluation()
        return self.ratings_testings_by_user
    
    def _train_test_split(self):
        ratings = self.ratings
        ratings['DATE'] = pd.to_datetime(ratings['unixReviewTime'], unit='s')
        
        ratings_trainings = ratings[
            (ratings['DATE'] < '2018-09-01')
        ]
        ratings_testings = ratings[
            (ratings['DATE'] >= '2018-09-01') & 
            (ratings['DATE'] <= '2018-09-30')
        ]
        
        #users = list(ratings_testings_by_user.keys())
        self.ratings_trainings = ratings_trainings
        self.ratings_testings  = ratings_testings
        
        
        return ratings_trainings, ratings_testings
    
        
    def _generate_evaluation(self):
        ratings = self.ratings
        ratings_testings = self.ratings_testings
        ratings_testings_by_user = ratings_testings.groupby('reviewerID').agg(list).reset_index()[['reviewerID', 'asin']].to_dict('records')
        ratings_testings_by_user = { rating['reviewerID']: rating['asin'] for rating in ratings_testings_by_user }
        self.ratings_testings_by_user=ratings_testings_by_user
        return ratings_testings_by_user
    
    