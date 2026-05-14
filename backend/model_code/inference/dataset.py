import copy
import numpy as np
import torch
from torch.utils.data import Dataset

from data.dataset import FeatureDataset


class FeatureInfDataset(FeatureDataset):
    """
    Dataset for inferring feature models.
    Heavily inherits from FeatureDataset.

    Args:
        df (DataFrame): DataFrame containing the dataset information.
        exp_folders (list): List of experimental folders.
        crop_fts (dict): Dictionary of cropped features.
        csv_fts (dict, optional): Dictionary of features from CSV files. Defaults to None.
        save_folder (str, optional): Path to save the output. Defaults to "../output/tmp".
    """
    def __init__(self, df, exp_folders, crop_fts, csv_fts=None, save_folder="../output/tmp"):
        self.df = df
        self.exp_folders = exp_folders

        self.targets = np.zeros((len(df), 1))

        self.series_dict = self.get_series_dict(df)

        self.dummies = {
            "scs_crop": np.zeros(3),
            "nfn_crop": np.zeros(3),
            "crop": np.zeros((5, 3)),
            "crop_2": np.zeros((5, 3)),
            "dh": np.zeros((25, 3)),
            "dh_2": np.zeros((25, 3)),
            "ch": np.zeros((25, 3)),
        }

        self.fts = crop_fts

        if csv_fts is not None:
            self.fts.update(csv_fts)


class SafeDataset(Dataset):
    """
    Wrapper to avoid dataset errors and fallback to another index.

    Args:
        dataset (Dataset): The dataset to wrap.
    """
    def __init__(self, dataset):
        self.dataset = dataset
        self.ref_output = None

        for idx in range(len(dataset)):
            try:
                self.ref_output = copy.deepcopy(list(self.dataset[idx]))
                break
            except Exception as e:
                print(f'Error initializing SafeDataset at idx {idx}: {e}')
                continue

        if self.ref_output is None:
            # Absolute fallback if dataset is empty or entirely broken
            print("SafeDataset: No valid sample found for initialization. Using dummy fallback.")
            # Check if we should return a dict or tensor based on the dataset type
            if "Feature" in str(type(dataset)):
                self.ref_output = ({}, torch.zeros(1), 0)
            else:
                self.ref_output = (torch.zeros((1, 3, 224, 224)), torch.zeros(1), 0)
        else:
            if isinstance(self.ref_output[0], dict):
                for k in self.ref_output[0]:
                    self.ref_output[0][k] *= 0
            elif isinstance(self.ref_output[0], torch.Tensor):
                self.ref_output[0] *= 0
            
            # Wrap as tuple
            self.ref_output = tuple(self.ref_output)

    def __len__(self):
        """
        Get the length of the dataset.

        Returns:
            int: Length of the dataset.
        """
        return len(self.dataset)

    def __getitem__(self, idx):
        """
        Get an item from the dataset.

        Args:
            idx (int): Index of the item to retrieve.

        Returns:
            tuple: Retrieved item from the dataset or fallback output in case of error.
        """
        try:
            return self.dataset[idx]
        except Exception:
            print(f"Error at idx {idx}")
            return self.ref_output
