import numpy as np
import sys
sys.path.append('../HOTS')
from Tools import tic,toc, get_loader, fit_data, predict_data, classification_results, netparam
import pickle

#_________NETWORK_PARAMETERS______________________
#______________________________________________
name = 'homhots'
sigma = None
pooling = False
homeinv = False
jitonic = [None,None] #[temporal, spatial]
jitter = False
tau = 5
R = 2
nblay = 3
nbclust = [4, 8, 16]
filt = 2

#______________________________________________

#_______________NB_OF_DIGITS___________________
dataset = 'nmnist'
nb_test = 10000
nb_train = 60000
ds = 1
nb_test = nb_test//ds
nb_train = nb_train//ds
print(f'training set size: {nb_train} - testing set: {nb_test}')
#______________________________________________
#_______________LR_PARAMETERS__________________
learning_rate = 0.005
beta1, beta2 = 0.9, 0.999
betas = (beta1, beta2)
num_epochs = 2 ** 5 + 1
#num_epochs = 2 ** 9 + 1
print(f'number of epochs: {num_epochs}')
#______________________________________________

timestr = '2021-03-29'
record_path = '../Records/EXP_03_NMNIST/models/'

results = []

for name in ['hots','homhots']:
    print(f'get training set for {name}...')
    learn_set, nb_pola, name_net = get_loader(name, record_path, nb_train, True, filt, tau, nbclust, sigma, homeinv, jitter, timestr, dataset, R)
    print(f'LR fit for {name}...')
    model, loss = fit_data(name_net, learn_set, nb_train, nb_pola, learning_rate, num_epochs, betas, verbose=True)
    print(f'get testing set for {name}...')
    test_set, nb_pola, name_net = get_loader(name, record_path, nb_test, False, filt, tau, nbclust, sigma, homeinv, jitter, timestr, dataset, R)
    print(f'prediction for {name}...')
    pred_target, true_target = predict_data(test_set, model, nb_test)
    mean_acc, online_acc = classification_results(pred_target, true_target, nb_test)
    print(f'Classification performance for {name}: {mean_acc}')
    results.append([pred_target, true_target, mean_acc, online_acc])

hotshom, homeotest = netparam(name, filt, tau, nbclust, sigma, homeinv, jitter, timestr, dataset, R)
path = '../Records/EXP_03_NMNIST/'
f_name = f'{path}{hotshom.get_fname()}_LR_results_{nb_train}_{nb_test}.pkl'

with open(f_name, 'wb') as file:
    pickle.dump([results], file, pickle.HIGHEST_PROTOCOL)