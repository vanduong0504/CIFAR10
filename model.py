import os
import time
import glob
import torch
from utils import *
import torch.nn as nn
from models import vgg,resnet
from tqdm import tqdm
from data import CIFAR
import torch.optim as optim


class model:
    def __init__(self,args):
        self.model = args.model
        self.phase = args.phase
        self.dataset = args.dataset
        self.channels = args.c
        self.classes = args.classes

        self.epochs = args.epochs
        self.batch_size = args.batch_size
        self.lr = args.lr

        self.device = args.device
        self.result_dir = args.result_dir
        self.save_freq  = args.save_freq 
        self.save_path  = args.save_path 
        self.save_type = args.save_type
        self.stop = args.stop

        print()
        print("##### Information #####")
        print("# model : ", self.model)
        print("# dataset : ", self.dataset)
        print("# channels : ", self.channels)
        print("# classes : ", self.classes)
        print("# epoch : ", self.epochs)
        print("# batch_size : ", self.batch_size)
        print("# save_freq  : ", self.save_freq )
        print()

    def build_model(self):
        "Dataset"
        data = CIFAR()
        traindata = data.train
        testdata = data.test
        self.trainloader = data.loader(traindata, batch_sizes=self.batch_size)
        self.testloader = data.loader(testdata, batch_sizes=self.batch_size)

        "Define model"
        if self.model == "VGG16": 
            self.net = vgg.VGG16(self.channels, self.classes).to(self.device)
        elif self.model == "VGG19":
            self.net = vgg.VGG19(self.channels, self.classes).to(self.device)
        elif self.model == "RESNET18":
            self.net = resnet.RESNET18(self.channels, self.classes).to(self.device)
        elif self.model == "RESNET34":
            self.net = resnet.RESNET34(self.channels, self.classes).to(self.device)
        elif self.model == "RESNET50":
            self.net = resnet.RESNET50(self.channels, self.classes).to(self.device)
        elif self.model == "RESNET152":
            self.net = resnet.RESNET152(self.channels, self.classes).to(self.device)

        "weight initialization"
        print("Weight Initialization")
        init_weight(self.net)
        print()
    def load(self, epoch=None):
        "epoch you want to load, --self.save_freq "
        path = f"{self.save_path }/{self.model}/"
        if epoch is None:   
            "load lastest epoch"
            files = glob.glob(path+"*.pth")
            path = max(files, key=os.path.getctime)
            print(path)
        else:
            path = path+f"{self.model}_{epoch}.pth"
        self.net.load_state_dict(torch.load(path))

    def save(self, epoch, save_type):
        path = f"{self.save_path }/{self.model}/"
        if save_type == 'N_epochs':
            torch.save(self.net.state_dict(), check_folder(path)+f"{self.model}_{epoch+1}.pth")
        elif save_type == 'best_epoch':
            torch.save(self.net.state_dict(), check_folder(path)+f"{self.model}_best.pth")

    def train(self):
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.net.parameters(), lr=self.lr, weight_decay=5e-4)
        early_stop = early_stopping(self.stop)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer=optimizer, patience=5, verbose=True)
        
        self.net.train()
        
        for epoch in range(self.epochs):
            losses = []
            acc = []
            loop = tqdm(enumerate(self.trainloader), total=len(self.trainloader), leave=False)
            for batch_idx, (inputs, labels) in loop:
                "Train"
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                optimizer.zero_grad()
                outputs = self.net(inputs)
                loss = criterion(outputs, labels)
                losses.append(loss.item())
                loss.backward()
                optimizer.step()

                "Accuracy"
                correct = 0
                _, predicted = torch.max(outputs, dim=1)
                correct = (predicted==labels).sum().item()
                accurary = correct/labels.size(0)
                acc.append(accurary)
                

                loop.set_description(f"Epoch [{epoch+1}/{self.epochs}]")
                loop.set_postfix(loss=loss.item(), acc_train=accurary*100)
                time.sleep(0.1)

            mean_loss = sum(losses)/len(losses)
            mean_acc = sum(acc)/len(acc)
            scheduler.step(mean_loss)
            print(f"Epoch [{epoch+1}/{self.epochs}] Loss: {mean_loss}")
            
            "Early stopping"
            early_stop(mean_loss)
            if early_stop.stop:
                "save best epoch"
                self.save(epoch-self.stop)
                break

            "Save epoch"
            if (self.save_type == "N_epochs") and (epoch%self.save_freq  == self.save_freq -1):
                self.save(epoch, save_type=self.save_type)
            elif (self.save_type == "best_epoch") and (mean_loss <= early_stop.best_loss):
                self.save(epoch, save_type=self.save_type)


    def test(self):
        "Load model"
        self.load()
        self.net.eval()

        correct = 0
        total = 0
        with torch.no_grad():
            for (inputs,labels) in self.testloader:
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                outputs = self.net(inputs)

                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted==labels).sum().item()

            print('Accuracy of the network on the 10000 test images: %d %%' % (100*correct/total))

            
    
