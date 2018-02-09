# -*- coding: utf-8 -*-

import argparse
import os
import random
import torch
from torch.autograd import Variable

from utils.tools import str2bool
from dataLoader.dataLoader import getDataLoader
import models

class Solver(object):
    def __init__(self, config, trainLoader, testLoader):
        self.trainLoader = trainLoader
        self.testLoader = testLoader
        self.use_cuda = config.use_cuda
        if config.dataset == 'MNIST':
            self.LeNet = getattr(models, 'LeNet')(1, 10, config.use_ReLU)
        else:
            self.LeNet = getattr(models, 'LeNet')(3, 10, config.use_ReLU)
        if config.model_name != '':
            print('use pretrained model: ', config.model_name)
            self.LeNet.load(config.model_name)
        self.optimizer = torch.optim.SGD(self.LeNet.parameters(), lr=config.lr, weight_decay=config.weight_decay)
        self.criterion = torch.nn.CrossEntropyLoss()
        if self.use_cuda:
            self.LeNet = self.LeNet.cuda()
            self.criterion = self.criterion.cuda()

        self.n_epochs = config.n_epochs
        self.log_step = config.log_step
        self.out_path = config.out_path

    def val(self):
        LeNet = self.LeNet
        testLoader = self.testLoader
        LeNet.eval()  # 验证模式
        class_correct = list(0. for i in range(10))
        class_total = list(0. for i in range(10))
        accuracy = list(0. for i in range(10 + 1))
        loss = 0.0
        for ii, (datas, labels) in enumerate(testLoader):
            val_inputs = Variable(datas, volatile=True)
            target = Variable(labels)
            if self.use_cuda:
                val_inputs = val_inputs.cuda()
                target = target.cuda()
            outputs = LeNet(val_inputs)
            loss += self.criterion(outputs, target)
            _, predicted = torch.max(outputs.data, 1)
            c = (predicted.cpu() == labels).squeeze()
            for jj in range(labels.size()[0]):
                label = labels[jj]
                class_correct[label] += c[jj]
                class_total[label] += 1

        correct = 0
        total = 0
        for ii in range(10):
            if class_total[ii] == 0:
                accuracy[ii] = 0
            else:
                correct = correct + class_correct[ii]
                total = total + class_total[ii]
                accuracy[ii] = class_correct[ii] / class_total[ii]
        accuracy[10] = correct / total

        LeNet.train()  # 训练模式
        return accuracy, loss.cpu().data.numpy()

    def train(self):
        val_accuracy, val_loss = self.val()
        print('begin with accuracy: ', val_accuracy[10])

        LeNet = self.LeNet
        for epoch in range(self.n_epochs):
            for ii, (data, label) in enumerate(self.trainLoader):
                input = Variable(data)
                target = Variable(label)
                if self.use_cuda:
                    input = input.cuda()
                    target = target.cuda()
                self.optimizer.zero_grad()
                score = LeNet(input)
                loss = self.criterion(score, target)
                loss.backward()
                self.optimizer.step()

                if (ii + 1) % self.log_step == 0:
                    print('epoch: ', epoch, 'train_num: ', ii + 1, loss.cpu().data.numpy()[0])

            val_accuracy, val_loss = self.val()
            print('val accuracy: ', val_accuracy[10])
            print('val loss:     ', val_loss[0])

        LeNet.save(root=self.out_path, name='LeNet_cifar10.pth')
        return

    def test(self):
        accuracy, loss = self.val()

        for jj in range(10):
            print('accuracy_', jj, ': ', accuracy[jj])
        print('accuracy total: ', accuracy[10])
        return


def main(config):
    # cuda
    if config.use_cuda:
        from torch.backends import cudnn
        cudnn.benchmark = True
    elif torch.cuda.is_available():
        print("WARNING: You have a CUDA device, so you should probably run with --cuda")

    # seed
    if config.seed == 0:
        config.seed = random.randint(1, 10000)  # fix seed
    print("Random Seed: ", config.seed)
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    if config.use_cuda:
        torch.cuda.manual_seed_all(config.seed)

    # create directories if not exist
    if not os.path.exists(config.out_path):
        os.makedirs(config.out_path)

    trainLoader, testLoader = getDataLoader(config)
    print('train samples num: ', len(trainLoader), '  test samples num: ', len(testLoader))

    solver = Solver(config, trainLoader, testLoader)
    print(solver.LeNet)

    if config.mode == 'train':
        solver.train()
    elif config.mode == 'test':
        solver.test()
    else:
        print('error mode!')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--image-size', type=int, default=32)
    parser.add_argument('--n-epochs', type=int, default=30)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--n-workers', type=int, default=4)
    parser.add_argument('--lr', type=float, default=0.01)
    parser.add_argument('--weight-decay', type=float, default=1e-4, help='')
    parser.add_argument('--out-path', type=str, default='./output')
    parser.add_argument('--use-ReLU', type=str2bool, default=False, help='use ReLU or not')
    parser.add_argument('--seed', type=int, default=0, help='random seed for all')

    parser.add_argument('--log-step', type=int, default=100)
    parser.add_argument('--use-cuda', type=str2bool, default=True, help='enables cuda')

    parser.add_argument('--data-path', type=str, default='./data/mnist')
    parser.add_argument('--dataset', type=str, default='MNIST', help='CIFAR10 or MNIST')
    parser.add_argument('--mode', type=str, default='test', help='train, test')
    parser.add_argument('--model-name', type=str, default='./pretrained_models/LeNet_sigmoid_mnist.pth', help='model for test or retrain')

    config = parser.parse_args()
    if config.use_cuda and not torch.cuda.is_available():
        config.use_cuda = False
        print("WARNING: You have no CUDA device")

    args = vars(config)
    print('------------ Options -------------')
    for key, value in sorted(args.items()):
        print('%16.16s: %16.16s' % (str(key), str(value)))
    print('-------------- End ----------------')

    main(config)
    print('End!!')
