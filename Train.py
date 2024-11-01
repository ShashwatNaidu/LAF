import torch
from torch import optim
import torch.nn.functional as F
import random
import os
import numpy as np
from torch.utils.data import DataLoader
from torch.utils.data import Dataset
from torch.utils.data import Subset
import torch.nn as nn
from torch.nn.modules.sparse import Embedding
import torchsummary
import torchvision.transforms as T
from sklearn.metrics import confusion_matrix, classification_report
import time
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from matplotlib import pyplot
import seaborn as sns 
import pandas as pd
from torch.nn.functional import softmax
from sklearn.model_selection import train_test_split
from sklearn import linear_model, model_selection    
from sklearn.metrics import accuracy_score, precision_score, recall_score
import xgboost as xgb
from xgboost import XGBClassifier
import copy

def train(model, train_loader, test_loader, epochs, lr, weight_decay, best_model = True):
    
    model.cuda()
    model.train()
    best_loss = float('inf')
    best_model = None
    optimizer = optim.Adam(model.parameters(), lr = lr, weight_decay=weight_decay) 
    loss_func = nn.CrossEntropyLoss()  
    for epoch in range(epochs):
        epoch_loss = 0.0
        for i, (data, targets) in enumerate(train_loader):
            
            data = data.cuda() 
            targets = targets.type(torch.LongTensor)  
            targets = targets.cuda()   
            output = model(data)[0]   
            
            loss = loss_func(output, targets)
            optimizer.zero_grad()           
            
            loss.backward()    
            optimizer.step() 
            
            epoch_loss += loss.item()  # Accumulate batch loss
                    
        avg_loss = epoch_loss / len(train_loader)  # Average loss for the epoch
        print('Epoch [{}/{}], Average Loss: {:.4f}'.format(epoch + 1, epochs, avg_loss))
        if(avg_loss <= best_loss):
            print("Next Best Model found on Epoch {}".format(epoch + 1))
            best_loss = avg_loss
            best_model = copy.deepcopy(model)

    return best_model

         
def test(trained_model, test_loader, output_label = None):
    trained_model = trained_model.cuda()
    trained_model.eval()
    all_preds = torch.tensor([])
    targets = torch.tensor([])
    original_targets = torch.tensor([])
    total = 0
    correct = 0
    with torch.no_grad():

        for i, (x,y) in enumerate(test_loader):
            
            original_targets = torch.cat((original_targets, y.cpu()),dim=0)
                            
            x = x.cuda()
            y = y.type(torch.LongTensor)
            y = y.cuda()
            y_out, _ = trained_model(x)
            
            _, predicted = torch.max(y_out.data, dim=1)
            all_preds = torch.cat((all_preds, y_out.cpu()),dim=0)
            targets = torch.cat((targets, y.cpu()),dim=0)
            
            total += y.size(0)
            correct += (predicted == y).sum().item()   

        preds = all_preds.argmax(dim=1)
        targets = np.array(targets)
        acc = 100.0 * correct / total
        #print('The accuracy of the all classes is: ', acc)
        if output_label is None:
            #print('Confusion matrix and classification report of all classes are: ')
            #print(confusion_matrix(targets, preds))
            #print(classification_report(targets, preds))
            selected_acc = acc
        else:
            selected_preds = []
            selected_targets = []
            selected_total = 0
            for i in range(len(preds)):
                if original_targets[i] in output_label:
                    selected_preds.append(preds[i])
                    selected_targets.append(targets[i])
                    selected_total += 1  
            # if len(output_label) == 1:        
            #     print(selected_preds) 
                        
            selected_correct = (np.array(selected_preds) == np.array(selected_targets)).sum().item()                  
            selected_acc = 100.0 * selected_correct / selected_total
            #print('The accuracy of the selected classes ', output_label, 'is: ', selected_acc)

    return selected_acc

'''
x_out is the output image data, and x is the original image data
'''
def vae_loss_function(x_out, x, mu, sigma):
    #print(x_out.shape)
    BCE = F.mse_loss(x_out, x, reduction='sum')/x.shape[0]
    #print(BCE)
    KLD = -0.5 * torch.sum(torch.log(sigma.pow(2) + 1e-8) + 1 - mu.pow(2) - sigma.pow(2))/x.shape[0]
    #print(KLD)
    return BCE + KLD * 0.025

def vae_train(trained_model, vae, loader):
    trained_model = trained_model.cuda()
    trained_model.eval()
    vae = vae.cuda()
    optimizer = torch.optim.Adam(vae.parameters(), lr = 0.001)
    # list to record loss, mu, and sigma in the training process
    for epoch in range(10):
        all_loss = 0
        count = 0
        vae.train()

        for x, y in loader:
            
            x = x.cuda()
            y = y.type(torch.LongTensor)
            y = y.cuda()
            
            #print(y.shape)
            _, e = trained_model(x)
            #print(e.shape)
            y = y.unsqueeze(1)
            #e = torch.cat([e, y], dim=1)
            optimizer.zero_grad()
            e_out, z, mu, sigma = vae(e)
            loss = vae_loss_function(e_out, e, mu, sigma)
            loss.backward()
            all_loss += loss.cpu().item()
            count += 1
            optimizer.step()
        
        epoch_loss = all_loss/count
        print('VAE Training Epoch: ', epoch, ' Loss: ', epoch_loss)   
    return vae


def train_attack_model(trained_model, train_loader, test_loader):

    
    trained_model.cuda()        
    trained_model.eval()
    N_unlearn_sample = 5000
    train_data = torch.zeros([1,10])
    train_data = train_data.cuda()
    with torch.no_grad():
           
        for batch_idx, (data, target) in enumerate(train_loader):
            data = data.cuda()
            out, _ = trained_model(data)
            train_data = torch.cat([train_data, out])
            if(train_data.shape[0] > N_unlearn_sample):
                break
                
                
    train_data = train_data[1:,:]
    train_data = softmax(train_data,dim = 1)
    train_data = train_data.cpu()
    train_data = train_data.detach().numpy()
    
    N_unlearn_sample = 5000
    test_data = torch.zeros([1,10])
    test_data = test_data.cuda()
    with torch.no_grad():
        for batch, (data, target) in enumerate(test_loader):
            data = data.cuda()
            out, _ = trained_model(data)
            test_data = torch.cat([test_data, out])
            
            if(test_data.shape[0] > N_unlearn_sample):
                break
            
    test_data = test_data[1:,:]
    test_data = softmax(test_data,dim = 1)
    test_data = test_data.cpu()
    test_data = test_data.detach().numpy()
    
    print(len(train_data))
    print(len(test_data))
    att_y = np.hstack((np.ones(train_data.shape[0]), np.zeros(test_data.shape[0])))
    att_y = att_y.astype(np.int16)
    
    att_X = np.vstack((train_data, test_data))
    att_X.sort(axis=1)
    
    
    X_train, X_test, y_train, y_test = train_test_split(att_X, att_y, test_size = 0.01, shuffle=True)
    
    attacker = XGBClassifier(n_estimators = 100,
                              n_jobs = -1,
                              objective = 'binary:logistic',
                              booster="gbtree",
                              )
    
    attacker.fit(X_train, y_train)
    
    pred_Y = attacker.predict(X_train)
    acc = accuracy_score(y_train, pred_Y)
    
    print("MIA attacker training accuracy = {:.4f}".format(acc))
    
    return attacker   


def attack(trained_model, attack_model, target_loaders, test_loader):
  
    
    trained_model.cuda()
        
    trained_model.eval()
    
    #The predictive output of forgotten user data after passing through the target model.
    unlearn_X = torch.zeros([1,10])
    unlearn_X = unlearn_X.cuda()
    with torch.no_grad():
        for batch_idx, (data, target) in enumerate(target_loaders):
            data = data.cuda()
            out, _ = trained_model(data)
            unlearn_X = torch.cat([unlearn_X, out])
                    
    unlearn_X = unlearn_X[1:,:]
    unlearn_X = softmax(unlearn_X,dim = 1)
    unlearn_X = unlearn_X.cpu().detach().numpy()
    
    #unlearn_X.sort(axis=1)
    unlearn_y = np.ones(unlearn_X.shape[0])
    unlearn_y = unlearn_y.astype(np.int16)   
    
    N_unlearn_sample = unlearn_X.shape[0]
    
    test_X = torch.zeros([1,10])
    test_X = test_X.cuda()
    
    test_X0 = torch.zeros([1,10])
    test_X0 = test_X.cuda()
    
    with torch.no_grad():
        for batch_idx, (data, target) in enumerate(test_loader):
            if(test_X0.shape[0] < 5000):
                data = data.cuda()
                out, _ = trained_model(data)
                test_X0  = torch.cat([test_X0 , out])
            else:
                data = data.cuda()
                out, _ = trained_model(data)
                test_X  = torch.cat([test_X , out])
            
                if(test_X.shape[0] > N_unlearn_sample):
                    break
                    
    test_X = test_X[1:,:]
    test_X = softmax(test_X,dim = 1)
    test_X = test_X.cpu().detach().numpy()
    
    #test_X.sort(axis=1)
    test_y = np.zeros(test_X.shape[0])
    test_y = test_y.astype(np.int16) 
    
    y = np.hstack((unlearn_y, test_y))
    y = y.astype(np.int16)
    
    X = np.vstack((unlearn_X, test_X))
    X.sort(axis=1)                
    
    pred_Y = attack_model.predict(X)
    acc = accuracy_score(y, pred_Y)
    
    print("MIA Attacker accuracy = {:.4f}".format(acc))
    
    return acc     

def testHypothesis(trained_model, retrained_model, test_loader, output_label = None, test_label = 0, labelAgnostic=True):
    print("Shashwat")
    trained_model = trained_model.cuda()
    retrained_model = retrained_model.cuda()
    trained_model.eval()
    retrained_model.eval()
    all_preds = torch.tensor([])
    targets = torch.tensor([])
    original_targets = torch.tensor([])
    matchLength = torch.tensor([])
    total = 0
    correct = 0
    with torch.no_grad():

        for i, (x,y) in enumerate(test_loader):
            
            original_targets = torch.cat((original_targets, y.cpu()),dim=0)
                            
            x = x.cuda()
            y = y.type(torch.LongTensor)
            y = y.cuda()
            y_out, _ = trained_model(x)
            y_out_retrained, _ = retrained_model(x)

            predicted_set_original = torch.from_numpy(np.argsort(-y_out.cpu().numpy())[:, ::-1].copy())
            predicted_set_retrained = torch.from_numpy(np.argsort(-y_out_retrained.cpu().numpy())[:, ::-1].copy())
            for k in range(len(predicted_set_original)):
                if(labelAgnostic):
                    if predicted_set_original[k][0] == test_label :
                        shifted_set = torch.cat((predicted_set_original[k][1:], predicted_set_original[k][0].unsqueeze(0)))
                        newPredictedSet = shifted_set
                    else:
                        newPredictedSet = predicted_set_original[k]
                    newRetrainedSet = predicted_set_retrained[k]
                    # ind = int(torch.where(predicted_set_retrained[k] == predicted_set_original[k][0])[0].cpu().numpy()[0])
                    # newRetrainedSet = torch.cat((predicted_set_retrained[k][:ind], predicted_set_retrained[k][ind+1:]))
                else:
                    indOrg = int(torch.where(predicted_set_retrained[k] == test_label)[0].cpu().numpy()[0])
                    newPredictedSet = torch.cat((predicted_set_original[k][:indOrg], predicted_set_original[k][indOrg+1:]))
                    indRet = int(torch.where(predicted_set_retrained[k] == test_label)[0].cpu().numpy()[0])
                    newRetrainedSet = torch.cat((predicted_set_retrained[k][:indRet], predicted_set_retrained[k][indRet+1:]))
    
                newPredictedSet = newPredictedSet.cpu().numpy()
                newRetrainedset = newRetrainedSet.cpu().numpy()
                i = 0
                while i < len(newPredictedSet):
                    if(newPredictedSet[i] != newRetrainedSet[i] and (((i+1) < len(newPredictedSet)) and (newPredictedSet[i+1] != newRetrainedSet[i]))):
                        y1 = torch.tensor([i])
                        matchLength = torch.cat((matchLength, y1.cpu()),dim=0)
                        break
                    i += 1
                if(i == len(newPredictedSet)):
                    y1 = torch.tensor([len(newPredictedSet)])
                    matchLength = torch.cat((matchLength, y1.cpu()),dim=0)
                
            _, predicted = torch.max(y_out.data, dim=1)
            all_preds = torch.cat((all_preds, y_out.cpu()),dim=0)
            targets = torch.cat((targets, y.cpu()),dim=0)
            
            total += y.size(0)
            correct += (predicted == y).sum().item()   

        preds = all_preds.argmax(dim=1)
        targets = np.array(targets)
        acc = 100.0 * correct / total
        #print('The accuracy of the all classes is: ', acc)
        if output_label is None:
            #print('Confusion matrix and classification report of all classes are: ')
            #print(confusion_matrix(targets, preds))
            #print(classification_report(targets, preds))
            selected_acc = acc
        else:
            selected_preds = []
            selected_targets = []
            selected_total = 0
            for i in range(len(preds)):
                if original_targets[i] in output_label:
                    selected_preds.append(preds[i])
                    selected_targets.append(targets[i])
                    selected_total += 1  
            # if len(output_label) == 1:        
            #     print(selected_preds) 
                        
            selected_correct = (np.array(selected_preds) == np.array(selected_targets)).sum().item()                  
            selected_acc = 100.0 * selected_correct / selected_total
            #print('The accuracy of the selected classes ', output_label, 'is: ', selected_acc)

    return selected_acc, matchLength

def testUnlearn(retrained_model, unlearn_model, test_loader, output_label = None):
    retrained_model = retrained_model.cuda()
    unlearn_model = unlearn_model.cuda()
    retrained_model.eval()
    unlearn_model.eval()
    all_preds_retrain = torch.tensor([])
    targets_retrain = torch.tensor([])
    all_preds_unlearn = torch.tensor([])
    targets_unlearn = torch.tensor([])
    original_targets = torch.tensor([])
    total = 0
    correct = 0
    with torch.no_grad():

        for i, (x,y) in enumerate(test_loader):
            
            original_targets = torch.cat((original_targets, y.cpu()),dim=0)
                            
            x = x.cuda()
            y = y.type(torch.LongTensor)
            y = y.cuda()
            y_out_retrain, _ = retrained_model(x)
            y_out_unlearn, _ = unlearn_model(x)
            
            _, predicted_retrain = torch.max(y_out_retrain.data, dim=1)
            all_preds_retrain = torch.cat((all_preds_retrain, y_out_retrain.cpu()),dim=0)
            targets_retrain = torch.cat((targets_retrain, y.cpu()),dim=0)

            _, predicted_unlearn = torch.max(y_out_unlearn.data, dim=1)
            all_preds_unlearn = torch.cat((all_preds_unlearn, y_out_unlearn.cpu()),dim=0)
            targets_unlearn = torch.cat((targets_unlearn, y.cpu()),dim=0)
            
            total += y.size(0)
            correct += (predicted_retrain == predicted_unlearn).sum().item()   

        preds_retrain = all_preds_retrain.argmax(dim=1)
        preds_unlearn = all_preds_unlearn.argmax(dim=1)
        targets_retrain = np.array(targets_retrain)
        acc = 100.0 * correct / total
        #print('The accuracy of the all classes is: ', acc)
        if output_label is None:
            #print('Confusion matrix and classification report of all classes are: ')
            #print(confusion_matrix(targets, preds))
            #print(classification_report(targets, preds))
            selected_acc = acc
        else:
            selected_preds_retrain = []
            selected_preds_unlearn = []
            selected_total = 0
            for i in range(len(preds_retrain)):
                if original_targets[i] in output_label:
                    selected_preds_retrain.append(preds_retrain[i])
                    selected_preds_unlearn.append(preds_unlearn[i])
                    selected_total += 1  
            # if len(output_label) == 1:        
            #     print(selected_preds) 
                        
            selected_correct = (np.array(selected_preds_retrain) == np.array(selected_preds_unlearn)).sum().item()                  
            selected_acc = 100.0 * selected_correct / selected_total
            #print('The accuracy of the selected classes ', output_label, 'is: ', selected_acc)

    return selected_acc
