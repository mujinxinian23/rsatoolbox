#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Definition of RSA Dataset class and subclasses
@author: baihan, jdiedrichsen, bpeters
"""


import numpy as np
import pickle
from pyrsa.util.data_utils import get_unique_unsorted
from pyrsa.util.descriptor_utils import check_descriptor_length_error
from pyrsa.util.descriptor_utils import subset_descriptor
from pyrsa.util.descriptor_utils import bool_index
from pyrsa.util.descriptor_utils import format_descriptor
from pyrsa.util.descriptor_utils import parse_input_descriptor
from pyrsa.util.file_io import write_dict_hdf5
from pyrsa.util.file_io import write_dict_pkl
from pyrsa.util.file_io import read_dict_hdf5
from pyrsa.util.file_io import read_dict_pkl


class DatasetBase:
    """
    Abstract dataset class.
    Defines members that every class needs to have, but does not
    implement any interesting behavior. Inherit from this class
    to define specific dataset types

    Args:
        measurements (numpy.ndarray): n_obs x n_channel 2d-array,
        descriptors (dict):           descriptors (metadata)
        obs_descriptors (dict):       observation descriptors (all
            are array-like with shape = (n_obs,...))
        channel_descriptors (dict):   channel descriptors (all are
            array-like with shape = (n_channel,...))

    Returns:
        dataset object
    """
    def __init__(self, measurements, descriptors=None,
                 obs_descriptors=None, channel_descriptors=None):
        if measurements.ndim != 2:
            raise AttributeError(
                "measurements must be in dimension n_obs x n_channel")
        self.measurements = measurements
        self.n_obs, self.n_channel = self.measurements.shape
        check_descriptor_length_error(obs_descriptors,
                                      "obs_descriptors",
                                      self.n_obs
                                      )
        check_descriptor_length_error(channel_descriptors,
                                      "channel_descriptors",
                                      self.n_channel
                                      )
        self.descriptors = parse_input_descriptor(descriptors)
        self.obs_descriptors = parse_input_descriptor(obs_descriptors)
        self.channel_descriptors = parse_input_descriptor(channel_descriptors)

    def __repr__(self):
        """
        defines string which is printed for the object
        """
        return (f'pyrsa.data.{self.__class__.__name__}(\n'
                f'measurements = \n{self.measurements}\n'
                f'descriptors = \n{self.descriptors}\n'
                f'obs_descriptors = \n{self.obs_descriptors}\n'
                f'channel_descriptors = \n{self.channel_descriptors}\n'
                )

    def __str__(self):
        """
        defines the output of print
        """
        string_desc = format_descriptor(self.descriptors)
        string_obs_desc = format_descriptor(self.obs_descriptors)
        string_channel_desc = format_descriptor(self.channel_descriptors)
        if self.measurements.shape[0] > 5:
            measurements = self.measurements[:5, :]
        else:
            measurements = self.measurements
        return (f'pyrsa.data.{self.__class__.__name__}\n'
                f'measurements = \n{measurements}\n...\n\n'
                f'descriptors: \n{string_desc}\n\n'
                f'obs_descriptors: \n{string_obs_desc}\n\n'
                f'channel_descriptors: \n{string_channel_desc}\n'
                )

    def split_obs(self, by):
        """ Returns a list Datasets split by obs

        Args:
            by(String): the descriptor by which the splitting is made

        Returns:
            list of Datasets, splitted by the selected obs_descriptor

        """
        raise NotImplementedError(
            "split_obs function not implemented in used Dataset class!")

    def split_channel(self, by):
        """ Returns a list Datasets split by channels

        Args:
            by(String): the descriptor by which the splitting is made

        Returns:
            list of Datasets,  splitted by the selected channel_descriptor

        """
        raise NotImplementedError(
            "split_channel function not implemented in used Dataset class!")

    def subset_obs(self, by, value):
        """ Returns a subsetted Dataset defined by certain obs value

        Args:
            by(String): the descriptor by which the subset selection is made
                from obs dimension
            value:      the value by which the subset selection is made
                from obs dimension

        Returns:
            Dataset, with subset defined by the selected obs_descriptor

        """
        raise NotImplementedError(
            "subset_obs function not implemented in used Dataset class!")

    def subset_channel(self, by, value):
        """ Returns a subsetted Dataset defined by certain channel value

        Args:
            by(String): the descriptor by which the subset selection is made
                from channel dimension
            value:      the value by which the subset selection is made
                from channel dimension

        Returns:
            Dataset, with subset defined by the selected channel_descriptor

        """
        raise NotImplementedError(
            "subset_channel function not implemented in used Dataset class!")

    def save(self, filename, file_type='hdf5'):
        """ Saves the dataset object to a file

        Args:
            filename(String): path to the file
                [or opened file]
            file_type(String): Type of file to create:
                hdf5: hdf5 file
                pkl: pickle file

        """
        data_dict = self.to_dict()
        if file_type == 'hdf5':
            write_dict_hdf5(filename, data_dict)
        elif file_type == 'pkl':
            write_dict_pkl(filename, data_dict)

    def to_dict(self):
        """ Generates a dictionary which contains the information to
        recreate the dataset object. Used for saving to disc

        Returns:
            data_dict(dict): dictionary with dataset information

        """
        data_dict = {}
        data_dict['measurements'] = self.measurements
        data_dict['descriptors'] = self.descriptors
        data_dict['obs_descriptors'] = self.obs_descriptors
        data_dict['channel_descriptors'] = self.channel_descriptors
        data_dict['type'] = type(self).__name__
        return data_dict


class Dataset(DatasetBase):
    """
    Dataset class is a standard version of DatasetBase.
    It contains one data set - or multiple data sets with the same structure
    """

    def split_obs(self, by):
        """ Returns a list Datasets splited by obs

        Args:
            by(String): the descriptor by which the splitting is made

        Returns:
            list of Datasets, splitted by the selected obs_descriptor
        """
        unique_values = get_unique_unsorted(self.obs_descriptors[by])
        dataset_list = []
        for v in unique_values:
            selection = (self.obs_descriptors[by] == v)
            measurements = self.measurements[selection, :]
            descriptors = self.descriptors
            obs_descriptors = subset_descriptor(
                self.obs_descriptors, selection)
            channel_descriptors = self.channel_descriptors
            dataset = Dataset(measurements=measurements,
                              descriptors=descriptors,
                              obs_descriptors=obs_descriptors,
                              channel_descriptors=channel_descriptors)
            dataset_list.append(dataset)
        return dataset_list

    def split_channel(self, by):
        """ Returns a list Datasets splited by channels

        Args:
            by(String): the descriptor by which the splitting is made

        Returns:
            list of Datasets,  splitted by the selected channel_descriptor
        """
        unique_values = get_unique_unsorted(self.channel_descriptors[by])
        dataset_list = []
        for v in unique_values:
            selection = (self.channel_descriptors[by] == v)
            measurements = self.measurements[:, selection]
            descriptors = self.descriptors
            descriptors[by] = v
            obs_descriptors = self.obs_descriptors
            channel_descriptors = subset_descriptor(
                self.channel_descriptors, selection)
            dataset = Dataset(measurements=measurements,
                              descriptors=descriptors,
                              obs_descriptors=obs_descriptors,
                              channel_descriptors=channel_descriptors)
            dataset_list.append(dataset)
        return dataset_list

    def subset_obs(self, by, value):
        """ Returns a subsetted Dataset defined by certain obs value

        Args:
            by(String): the descriptor by which the subset selection
                is made from obs dimension
            value:      the value by which the subset selection is made
                from obs dimension

        Returns:
            Dataset, with subset defined by the selected obs_descriptor

        """
        selection = bool_index(self.obs_descriptors[by], value)
        measurements = self.measurements[selection, :]
        descriptors = self.descriptors
        obs_descriptors = subset_descriptor(
            self.obs_descriptors, selection)
        channel_descriptors = self.channel_descriptors
        dataset = Dataset(measurements=measurements,
                          descriptors=descriptors,
                          obs_descriptors=obs_descriptors,
                          channel_descriptors=channel_descriptors)
        return dataset

    def subset_channel(self, by, value):
        """ Returns a subsetted Dataset defined by certain channel value

        Args:
            by(String): the descriptor by which the subset selection is
                made from channel dimension
            value:      the value by which the subset selection is made
                from channel dimension

        Returns:
            Dataset, with subset defined by the selected channel_descriptor

        """
        selection = bool_index(self.channel_descriptors[by], value)
        measurements = self.measurements[:, selection]
        descriptors = self.descriptors
        obs_descriptors = self.obs_descriptors
        channel_descriptors = subset_descriptor(
            self.channel_descriptors, selection)
        dataset = Dataset(measurements=measurements,
                          descriptors=descriptors,
                          obs_descriptors=obs_descriptors,
                          channel_descriptors=channel_descriptors)
        return dataset

    def sort_by(self, by):
        """ sorts the dataset by a given observation descriptor

        Args:
            by(String): the descriptor by which the dataset shall be sorted

        Returns:
            ---

        """
        desc = self.obs_descriptors[by]
        order = np.argsort(desc)
        self.measurements = self.measurements[order]
        self.obs_descriptors = subset_descriptor(self.obs_descriptors, order)
        

class TemporalDataset(Dataset):
    """
    TemporalDataset for spatio-temporal datasets
    

    Args:
        measurements (numpy.ndarray): n_obs x n_channel x time 3d-array,
        descriptors (dict):           descriptors (metadata)
        obs_descriptors (dict):       observation descriptors (all
            are array-like with shape = (n_obs,...))
        channel_descriptors (dict):   channel descriptors (all are
            array-like with shape = (n_channel,...))
        time_descriptors (dict):      time descriptors (alls are 
            array-like with shape= (n_time,...))
        
            time_descriptors needs to contain one key 'time' that 
            specifies the time-coordinate. if None is provided, 'time' is
            set as (0, 1, ..., n_time-1)

    Returns:
        dataset object
    """
    def __init__(self, measurements, descriptors=None,
                 obs_descriptors=None, channel_descriptors=None,
                 time_descriptors=None):
        
        if measurements.ndim != 3:
            raise AttributeError(
                "measurements must be in dimension n_obs x n_channel x time")
        
        self.measurements = measurements
        self.n_obs, self.n_channel, self.n_time = self.measurements.shape
        
                
        if time_descriptors is None:
            time_descriptors = {'time': np.arange(self.n_time)}
        elif 'time' not in time_descriptors:
            time_descriptors['time'] = np.arange(self.n_time)
            raise Warning(
                "there was no 'time' provided in dictionary time_descriptors\n"\
                "'time' will be set to (0, 1, ..., n_time-1)")
                    
        check_descriptor_length_error(obs_descriptors,
                                      "obs_descriptors",
                                      self.n_obs
                                      )
        check_descriptor_length_error(channel_descriptors,
                                      "channel_descriptors",
                                      self.n_channel
                                      )
        check_descriptor_length_error(time_descriptors,
                                      "time_descriptors",
                                      self.n_time
                                      )        
        self.descriptors = parse_input_descriptor(descriptors)
        self.obs_descriptors = parse_input_descriptor(obs_descriptors)
        self.channel_descriptors = parse_input_descriptor(channel_descriptors)
        self.time_descriptors = parse_input_descriptor(time_descriptors)

    def __str__(self):
        """
        defines the output of print
        """
        string_desc = format_descriptor(self.descriptors)
        string_obs_desc = format_descriptor(self.obs_descriptors)
        string_channel_desc = format_descriptor(self.channel_descriptors)
        string_time_desc = format_descriptor(self.time_descriptors)
        if self.measurements.shape[0] > 5:
            measurements = self.measurements[:5, :, :]
        else:
            measurements = self.measurements
        return (f'pyrsa.data.{self.__class__.__name__}\n'
                f'measurements = \n{measurements}\n...\n\n'
                f'descriptors: \n{string_desc}\n\n'
                f'obs_descriptors: \n{string_obs_desc}\n\n'
                f'channel_descriptors: \n{string_channel_desc}\n'
                f'time_descriptors: \n{string_time_desc}\n'
                )

    def split_obs(self, by):
        """ Returns a list TemporalDataset splited by obs

        Args:
            by(String): the descriptor by which the splitting is made

        Returns:
            list of TemporalDataset, splitted by the selected obs_descriptor
        """
        unique_values = get_unique_unsorted(self.obs_descriptors[by])
        dataset_list = []
        for v in unique_values:
            selection = (self.obs_descriptors[by] == v)
            measurements = self.measurements[selection, :, :]
            descriptors = self.descriptors
            obs_descriptors = subset_descriptor(
                self.obs_descriptors, selection)
            channel_descriptors = self.channel_descriptors
            time_descriptors = self.time_descriptors
            dataset = TemporalDataset(measurements=measurements,
                                  descriptors=descriptors,
                                  obs_descriptors=obs_descriptors,
                                  channel_descriptors=channel_descriptors,
                                  time_descriptors=time_descriptors)
            dataset_list.append(dataset)
        return dataset_list
        
    def split_channel(self, by):
        """ Returns a list TemporalDataset splited by channels

        Args:
            by(String): the descriptor by which the splitting is made

        Returns:
            list of TemporalDataset,  splitted by the selected channel_descriptor
        """
        unique_values = get_unique_unsorted(self.channel_descriptors[by])
        dataset_list = []
        for v in unique_values:
            selection = (self.channel_descriptors[by] == v)
            measurements = self.measurements[:, selection, :]
            descriptors = self.descriptors.copy()
            descriptors[by] = v
            obs_descriptors = self.obs_descriptors
            channel_descriptors = subset_descriptor(
                self.channel_descriptors, selection)
            time_descriptors = self.time_descriptors
            dataset = TemporalDataset(measurements=measurements,
                                  descriptors=descriptors,
                                  obs_descriptors=obs_descriptors,
                                  channel_descriptors=channel_descriptors,
                                  time_descriptors=time_descriptors)
            dataset_list.append(dataset)
        return dataset_list    
    
    def split_time(self, by):
        """ Returns a list TemporalDataset splited by time

        Args:
            by(String): the descriptor by which the splitting is made

        Returns:
            list of TemporalDataset,  splitted by the selected time_descriptor
        """
        
        time = get_unique_unsorted(self.time_descriptors[by])
        dataset_list = []
        for v in time:
            selection = (self.time_descriptors[by] == v)
            measurements = self.measurements[:, :, selection]
            descriptors = self.descriptors
            obs_descriptors = self.obs_descriptors
            channel_descriptors = self.channel_descriptors
            time_descriptors = subset_descriptor(
                self.time_descriptors, selection)
            dataset = TemporalDataset(measurements=measurements,
                                  descriptors=descriptors,
                                  obs_descriptors=obs_descriptors,
                                  channel_descriptors=channel_descriptors,
                                  time_descriptors=time_descriptors)
            dataset_list.append(dataset)
        return dataset_list

    def bin_time(self, by, bins):
        """ Returns an object TemporalDataset with time-binned data. 

        Args:
            bins(array-like): list of bins, with bins[i] containing the vector
                of time-points for the i-th bin

        Returns:
            a single TemporalDataset object
                Data is averaged within time-bins.
                'time' descriptor is set to the average of the 
                binned time-points.            
        """
        
        time = self.time_descriptors[by]
        n_bins = len(bins)
        
        binned_measurements = np.zeros((self.n_obs, self.n_channel, n_bins))
        binned_time = np.zeros(n_bins)
        
        for t in range(n_bins):
            t_idx = np.isin(time, bins[t])
            binned_measurements[:,:,t] = np.mean(self.measurements[:,:,t_idx],axis=2)
            binned_time[t] = np.mean(time[t_idx])
        
        time_descriptors = self.time_descriptors.copy()
        time_descriptors[by] = binned_time
        
        # adding the bins as an additional descriptor currently 
        # does not work because of check_descriptor_length which transforms 
        # it into a numpy.array.
        #time_descriptors['bins'] = [x for x in bins]
        time_descriptors['bins'] = [np.array2string(x, precision=2, separator=',') for x in bins]
        
        dataset = TemporalDataset(measurements=binned_measurements,
                              descriptors=self.descriptors,
                              obs_descriptors=self.obs_descriptors,
                              channel_descriptors=self.channel_descriptors,
                              time_descriptors=time_descriptors)        
        
        return dataset
        
    def subset_obs(self, by, value):
        """ Returns a subsetted TemporalDataset defined by certain obs value

        Args:
            by(String): the descriptor by which the subset selection
                is made from obs dimension
            value:      the value by which the subset selection is made
                from obs dimension

        Returns:
            TemporalDataset, with subset defined by the selected obs_descriptor

        """
        selection = bool_index(self.obs_descriptors[by], value)
        measurements = self.measurements[selection, :, :]
        descriptors = self.descriptors
        obs_descriptors = subset_descriptor(
            self.obs_descriptors, selection)
        channel_descriptors = self.channel_descriptors
        time_descriptors = self.time_descriptors
        dataset = TemporalDataset(measurements=measurements,
                              descriptors=descriptors,
                              obs_descriptors=obs_descriptors,
                              channel_descriptors=channel_descriptors,
                              time_descriptors=time_descriptors)
        return dataset

    def subset_channel(self, by, value):
        """ Returns a subsetted TemporalDataset defined by certain channel value

        Args:
            by(String): the descriptor by which the subset selection is
                made from channel dimension
            value:      the value by which the subset selection is made
                from channel dimension

        Returns:
            TemporalDataset, with subset defined by the selected channel_descriptor

        """
        selection = bool_index(self.channel_descriptors[by], value)
        measurements = self.measurements[:, selection]
        descriptors = self.descriptors
        obs_descriptors = self.obs_descriptors
        channel_descriptors = subset_descriptor(
            self.channel_descriptors, selection)
        time_descriptors = self.time_descriptors
        dataset = TemporalDataset(measurements=measurements,
                              descriptors=descriptors,
                              obs_descriptors=obs_descriptors,
                              channel_descriptors=channel_descriptors,
                              time_descriptors=time_descriptors)
        return dataset
    
    def subset_time(self, by, t_from, t_to):
        """ Returns a subsetted TemporalDataset with time between t_from to t_to

        Args:
            by(String): the descriptor by which the subset selection is
                made from channel dimension
            t_from: time-point from which onwards data should be subsetted
            t_to: time-point until which data should be subsetted
                
        Returns:
            TemporalDataset, with subset defined by the selected time_descriptor
        """
        
        time = get_unique_unsorted(self.time_descriptors[by])
        sel_time = [t for t in time if t <= t_to and t>=t_from]      
        
        selection = bool_index(self.time_descriptors[by], sel_time)        
        measurements = self.measurements[:, :, selection]
        descriptors = self.descriptors
        obs_descriptors = self.obs_descriptors
        channel_descriptors = self.channel_descriptors
        time_descriptors = subset_descriptor(
            self.time_descriptors, selection)
        dataset = TemporalDataset(measurements=measurements,
                              descriptors=descriptors,
                              obs_descriptors=obs_descriptors,
                              channel_descriptors=channel_descriptors,
                              time_descriptors=time_descriptors)
        return dataset        
        
    
    def sort_by(self, by):
        """ sorts the dataset by a given observation descriptor

        Args:
            by(String): the descriptor by which the dataset shall be sorted

        Returns:
            ---

        """
        desc = self.obs_descriptors[by]
        order = np.argsort(desc)
        self.measurements = self.measurements[order]
        self.obs_descriptors = subset_descriptor(self.obs_descriptors, order)
        
    def convert_to_dataset(self, by):
        """ converts to Dataset long format. 
            time dimension is absorbed into observation dimension

        Args:
            by(String): the descriptor which indicates the time dimension in
                the time_descriptor

        Returns:
            Dataset

        """        
        time = get_unique_unsorted(self.time_descriptors[by])
         
        descriptors = self.descriptors
        channel_descriptors = self.channel_descriptors.copy()
        
        measurements = np.empty([0, self.n_channel])
        obs_descriptors = dict.fromkeys(self.obs_descriptors, [])
        
        for key in self.time_descriptors:
            obs_descriptors[key] = np.array([])        
        
        for v in time:
            selection = (self.time_descriptors[by] == v)
            
            measurements = np.concatenate((measurements, 
                                           self.measurements[:, :, selection].squeeze()), 
                                          axis=0)
            
            for key in self.obs_descriptors:
                obs_descriptors[key] = np.concatenate((obs_descriptors[key],
                                          self.obs_descriptors[key].copy()),
                                          axis=0)
            
            for key in self.time_descriptors:
                obs_descriptors[key] = np.concatenate((obs_descriptors[key],
                                          np.repeat(self.time_descriptors[key][selection],
                                                    self.n_obs)), axis=0)

        dataset = Dataset(measurements=measurements,
                          descriptors=descriptors,
                          obs_descriptors=obs_descriptors,
                          channel_descriptors=channel_descriptors)
        return dataset
        
        


def load_dataset(filename, file_type=None):
    """ loads a Dataset object from disc

    Args:
        filename(String): path to file to load

    """
    if file_type is None:
        if isinstance(filename, str):
            if filename[-4:] == '.pkl':
                file_type = 'pkl'
            elif filename[-3:] == '.h5' or filename[-4:] == 'hdf5':
                file_type = 'hdf5'
    if file_type == 'hdf5':
        data_dict = read_dict_hdf5(filename)
    elif file_type == 'pkl':
        data_dict = read_dict_pkl(filename)
    else:
        raise ValueError('filetype not understood')
    return dataset_from_dict(data_dict)


def dataset_from_dict(data_dict):
    """ regenerates a Dataset object from the dictionary representation

    Currently this function works for Dataset, DatasetBase, and TemporalDataset objects

    Args:
        data_dict(dict): the dictionary representation

    Returns:
        data(Dataset): the regenerated Dataset

    """
    if data_dict['type'] == 'Dataset':
        data = Dataset(
            data_dict['measurements'],
            descriptors=data_dict['descriptors'],
            obs_descriptors=data_dict['obs_descriptors'],
            channel_descriptors=data_dict['channel_descriptors'])
    elif data_dict['type'] == 'DatasetBase':
        data = DatasetBase(
            data_dict['measurements'],
            descriptors=data_dict['descriptors'],
            obs_descriptors=data_dict['obs_descriptors'],
            channel_descriptors=data_dict['channel_descriptors'])
    elif data_dict['type'] == 'TemporalDataset':
        data = TemporalDataset(
            data_dict['measurements'],
            descriptors=data_dict['descriptors'],
            obs_descriptors=data_dict['obs_descriptors'],
            channel_descriptors=data_dict['channel_descriptors'],
            time_descriptors=data_dict['time_descriptors'])        
    else:
        raise ValueError('type of Dataset not recognized')
    return data
