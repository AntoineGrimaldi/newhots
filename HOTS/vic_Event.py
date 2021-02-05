__author__ = "(c) Victor Boutin & Laurent Perrinet INT - CNRS (2017-) Antoine Grimaldi (2020-)"

import scipy.io
import numpy as np
from os import listdir
from vic_Tools import LoadObject
import vic_Tool_libUnpackAtis as ua
import pickle

#from HOTS.conv2eve import conv2eve
class conv2eve(object):
	""" Transform a matrix into event type:
                .t -> time
                .x and .y -> spatial position
                .p -> polarity"""

	def __init__(self, t, x, y, p):
		self.t = t
		self.x = x
		self.y = y
		self.p = p

class Event(object):
    '''
    Class representing an event with all its attributes
    ATTRIBUTE
        + polarity : np.array of shape [nb_event] with the polarity number of each event
        + address : np array of shape [nb_event, 2] with the x and y of each event
        + time : np.array of shape [nb_event] with the time stamp of each event
        + ImageSize : (tuple) representing the maximum window where an event could appear
        + ListPolarities : (list) list of the polarity we want to keep
        + ChangeIdx : (list) list composed by the last index of event of each event
        + OutOnePolarity : (bool), transform all polarities into 1 polarity
    '''

    def __init__(self, ImageSize, ListPolarities=None, OutOnePolarity=False):
        self.polarity = np.zeros(1)
        self.address = np.zeros(1)
        self.time = np.zeros(1)
        self.ImageSize = ImageSize
        #self.event_nb = np.zeros(1)
        self.ListPolarities = ListPolarities
        self.ChangeIdx = list()
        self.type = 'event'
        self.OutOnePolarity = OutOnePolarity
        # Idée, faire un mécanisme pour vérifier qu'il n'y a pas d'adresse en dehors de l'image

    def LoadFromMat(self, path, image_number, verbose=0):
        '''
        Load Events from a .mat file. Only the events contained in ListPolarities are kept:
        INPUT
            + path : a string which is the path of the .mat file (ex : './data_cache/alphabet_ExtractedStabilized.mat')
            + image_number : list with all the numbers of image to load
        '''
        obj = scipy.io.loadmat(path)
        ROI = obj['ROI'][0]

        if type(image_number) is int:
            image_number = [image_number]
        elif type(image_number) is not list:
            raise TypeError(
                'the type of argument image_number should be int or list')
        if verbose > 0:
            print("loading images {0}".format(image_number))
        Total_size = 0
        for idx, each_image in enumerate(image_number):
            image = ROI[each_image][0, 0]
            Total_size += image[1].shape[1]

        self.address = np.zeros((Total_size, 2)).astype(int)
        self.time = np.zeros((Total_size))
        self.polarity = np.zeros((Total_size))
        first_idx = 0

        for idx, each_image in enumerate(image_number):
            image = ROI[each_image][0, 0]
            last_idx = first_idx + image[0].shape[1]
            self.address[first_idx:last_idx, 0] = (image[1] - 1).astype(int)
            self.address[first_idx:last_idx, 1] = (image[0] - 1).astype(int)
            self.time[first_idx:last_idx] = (image[3] * 1e-6)
            self.polarity[first_idx:last_idx] = image[2].astype(int)
            first_idx = last_idx

        self.polarity[self.polarity.T == -1] = 0
        self.polarity = self.polarity.astype(int)
        # Filter only the wanted polarity
        self.ListPolarities = np.unique(self.polarity)
        filt = np.in1d(self.polarity, np.array(self.ListPolarities))
        self.filter(filt, mode='itself')
        if self.OutOnePolarity == True:
            self.polarity = np.zeros_like(self.polarity)
            self.ListPolarities = [0]

    def LoadFromBin(self, PathList, verbose=0):
        '''
        Load Events from a .bin file. Only the events contained in ListPolarities are kept:
        INPUT
            + PathList : a list of string representing the path each of the .bin file
        '''
        if type(PathList) is str:
            PathList = [PathList]
        elif type(PathList) not in [list, np.ndarray]:
            raise TypeError(
                'the type of argument image_number should be int or list')

        Total_size = 0
        for idx_path, path in enumerate(PathList):
            with open(path, 'rb') as f:
                a = np.fromfile(f, dtype=np.uint8)
            raw_data = np.uint32(a)
            x = raw_data[0::5]
            Total_size += x.shape[0]

        self.address = np.zeros((Total_size, 2)).astype(int)
        self.time = np.zeros((Total_size))
        self.polarity = np.zeros((Total_size))
        first_idx = 0
        for idx_path, path in enumerate(PathList):
            with open(path, 'rb') as f:
                a = np.fromfile(f, dtype=np.uint8)
            raw_data = np.uint32(a)
            x, y = raw_data[0::5], raw_data[1::5]
            p = (raw_data[2::5] & 128) >> 7
            t = ((raw_data[2::5] & 127) << 16) + \
                ((raw_data[3::5]) << 8) + raw_data[4::5]
            #each_address = np.vstack((y,x)).astype(int).T
            #each_time = (t * 1e-6).T
            each_polarity = p.copy().astype(int)
            each_polarity[each_polarity == 0] = -1
            each_polarity.T
            last_idx = first_idx + x.shape[0]
            self.address[first_idx:last_idx, 0] = y.astype(int).T
            self.address[first_idx:last_idx, 1] = x.astype(int).T
            self.time[first_idx:last_idx] = (t * 1e-6).T
            self.polarity[first_idx:last_idx] = each_polarity.T

            first_idx = last_idx

        # Filter only the wanted polarity

        filt = np.in1d(self.polarity, np.array(self.ListPolarities))
        self.filter(filt, mode='itself')

        if self.OutOnePolarity == True:
            self.polarity = np.zeros_like(self.polarity)
            self.ListPolarities = [0]

    def SeparateEachImage(self):
        '''
        find the separation event index if more than one image is represented, and store it into
        self.ChangeIDX

        '''

        add2 = self.time[1:]
        add1 = self.time[:-1]
        comp = add1 > add2
        self.ChangeIdx = np.zeros(np.sum(comp)+1).astype(int)
        self.ChangeIdx[:-1] = np.arange(0, comp.shape[0])[comp]
        self.ChangeIdx[-1] = comp.shape[0]

    def copy(self):
        '''
        copy the address, polarity, timing, and event_nb to another event
        OUTPUT :
            + event_output = event object which is the copy of self
        '''
        event_output = Event(self.ImageSize, self.ListPolarities)
        event_output.address = self.address.copy()
        event_output.polarity = self.polarity.copy()
        event_output.time = self.time.copy()
        event_output.ChangeIdx = self.ChangeIdx
        event_output.type = self.type
        event_output.OutOnePolarity = self.OutOnePolarity

        return event_output

    def filter(self, filt, mode=None):
        '''
        filters the event if mode is 'itself', or else outputs another event
        INPUT :
            + filt : np.array of boolean having the same dimension than self.polarity
        OUTPUT :
            + event_output : return an event, which is the filter version of self, only if mode
                is not 'itself'
        '''
        if mode == 'itself':
            self.address = self.address[filt]
            self.time = self.time[filt]
            self.polarity = self.polarity[filt]
            self.SeparateEachImage()
        else:
            event_output = self.copy()
            event_output.address = self.address[filt]
            event_output.time = self.time[filt]
            event_output.polarity = self.polarity[filt]
            event_output.SeparateEachImage()
            return event_output


def SimpleAlphabet(NbTrainingData, NbTestingData, Path=None, LabelPath=None, ClusteringData=None, OutOnePolarity=False, ListPolarities=None, verbose=0):
    '''
    Extracts the Data from the SimpleAlphabet DataBase :
    INPUT :
        + NbTrainingData : (int) Number of Training Data
        + NbTestingData : (int) Number of Testing Data
        + Path : (str) Path of the .mat file. If the path is None, the path is ../database/SimpleAlphabet/alphabet_ExtractedStabilized.mat
        + LabelPath : (str) Path of the .pkl label path. If the path is None, the path is  ../database/SimpleAlphabet/alphabet_label.pkl
        + ClusteringData : (list) a list of int indicating the image used to train the cluster. If None, the image used to train the
            the cluster are the trainingData
        + OutOnePolarity : (bool), transform all polarities into 1 polarity
        + ListPolarities : (list), list of the polarity we want to keep
    OUTPUT :
        + event_train : (<object event>)
        + event_test : (<object event>)
        + event_cluster : (<object event>)
        + label_train :
        + label_test :
    '''
    if Path is None:
        Path = '../database/SimpleAlphabet/alphabet_ExtractedStabilized.mat'

    if LabelPath is None:
        label_list = LoadObject(
            '../database/SimpleAlphabet/alphabet_label.pkl')
    else:
        label_list = LoadObject(LabelPath)

    if NbTrainingData+NbTestingData > 76:
        raise NameError('Overlaping between TrainingData and Testing Data')
    event_train = Event(ImageSize=(
        32, 32), ListPolarities=ListPolarities, OutOnePolarity=OutOnePolarity)
    event_test = Event(ImageSize=(
        32, 32), ListPolarities=ListPolarities, OutOnePolarity=OutOnePolarity)
    event_cluster = Event(ImageSize=(
        32, 32), ListPolarities=ListPolarities, OutOnePolarity=OutOnePolarity)
    event_train.LoadFromMat(Path, image_number=list(
        np.arange(0, NbTrainingData)), verbose=verbose)
    event_test.LoadFromMat(Path, image_number=list(
        np.arange(NbTrainingData, NbTrainingData+NbTestingData)), verbose=verbose)

    if ClusteringData is None:
        event_cluster = event_train
    else:
        event_cluster.LoadFromMat(
            Path, image_number=ClusteringData, verbose=verbose)
    
    # Generate Groud Truth Label
    for idx, img in enumerate(np.arange(0, NbTrainingData)):
        if idx != 0:
            label_train = np.vstack((label_train, label_list[img][0]))
        else:
            label_train = label_list[img][0]

    for idx, img in enumerate(np.arange(NbTrainingData, NbTrainingData+NbTestingData)):
        if idx != 0:
            label_test = np.vstack((label_test, label_list[img][0]))
        else:
            label_test = label_list[img][0]

    return event_train, event_test, event_cluster, label_train, label_test


def LoadGestureDB(filepath, OutOnePolarity=False):
    ts, c, p, removed_events = ua.readATIS_td(filepath, orig_at_zero=True,
                                              drop_negative_dt=True, verbose=False)
    event = Event(ImageSize=(304, 240))
    # print(p.shape)
    event.time = ts * 1e-6
    if OutOnePolarity == False:
        event.polarity = p
    else:
        event.polarity = np.zeros_like(p)
    event.ListPolarities = np.unique(event.polarity)
    event.address = c
    return event


def LoadNMNIST(NbTrainingData, NbTestingData, NbClusteringData, 
               Path=None, OutOnePolarity=False, ListPolarities=None, verbose=0):
    '''
    Loads the NMNIST dataset and returns the diferent event lists and labels

    The database consists of len(EVE)=10000 presentations with for each a listof events
    corresponding to that presentation.

    '''
    # loads the pickle
    if Path is None: Path = '../Data/testsetnmnist.p'
    EVE = pickle.load(open(Path, "rb" ))

    def make_events(list_digits_idx, NbData, ListPolarities=ListPolarities, OutOnePolarity=OutOnePolarity):
        # initializes event lists
        opts = dict(ImageSize=(34, 34), ListPolarities=ListPolarities, OutOnePolarity=OutOnePolarity)
        event = Event(**opts) # TRAIN

        # generate train
        #event.ChangeIdx = []
        size = 0
        for idx in list_digits_idx:
            size += len(EVE[idx].t)

        event.address = np.zeros((size, 2)).astype(int)
        event.time = np.zeros((size, ))
        event.polarity = np.zeros((size, )).astype(int)

        label = np.zeros((size, )).astype(int)

        t = 0 # absolute time
        idg = 0 # index for events
        idgl = 0 # index for digits
        for idx in list_digits_idx:
            events_digit = EVE[idx] # this digit
            N_events_digit = len(events_digit.t)
            for idev in range(N_events_digit):
                event.time[idg] = t + events_digit.t[idev]*pow(10,-6) # from micro-seconds to seconds
                event.address[idg][0] = int(events_digit.y[idev])
                event.address[idg][1] = int(events_digit.x[idev])
                event.polarity[idg] = int(events_digit.p[idev])
                label[idg] = events_digit.l
                idg += 1
            #event.ChangeIdx.append(len(events_digit.t))
            t += events_digit.t[idev]*pow(10,-6) # from micro-seconds to seconds
            idgl += 1
        
        event.ListPolarities = np.unique(event.polarity)
        return event, label
    
    # shuffle digits
    assert(NbTrainingData+NbTestingData+NbClusteringData <= len(EVE))
    list_digits_idx = np.random.permutation(len(EVE))

    list_digits_idx_train = list_digits_idx[:NbTrainingData]
    event_train, label_train = make_events(list_digits_idx_train, NbTrainingData, OutOnePolarity=OutOnePolarity)
    
    list_digits_idx_test = list_digits_idx[NbTrainingData:(NbTrainingData+NbTestingData)]
    event_test, label_test = make_events(list_digits_idx_test, NbTestingData, OutOnePolarity=OutOnePolarity)

    list_digits_idx_clust = list_digits_idx[(NbTrainingData+NbTestingData):(NbTrainingData+NbTestingData+NbClusteringData)]
    event_cluster, _ = make_events(list_digits_idx_clust, NbClusteringData, OutOnePolarity=OutOnePolarity)

    return event_train, event_test, event_cluster, label_train, label_test