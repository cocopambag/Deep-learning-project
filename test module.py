from os import walk, path, makedirs
import json
import cv2
import torch.nn as nn
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision.transforms import transforms
import torchvision.models as models
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import copy
import os
from mk_tensor import make_tensor


def calcurate_pre_post(pre, post):
    '''
    adjust post-image shape to pre-image shape in padding or crop.
    :param pre: pre-image numpy
    :param post: post-image numpy
    :return: adjust post-image shape to pre-image shape. Absolutely, adjust pre-image shape.
    '''
    # pre/post image height/width
    pre_h, pre_w = pre.shape[0], pre.shape[1]
    post_h, post_w = post.shape[0], post.shape[1]

    post = np.transpose(post, (2, 0, 1))

    # adjust pre-image height and width to post-image
    new_post = np.zeros((3, pre_h, pre_w))
    for i in range(3):
        # compare height
        if pre_h > post_h:
            new_post[i, :post_h, :post_w] = post[i, :, :pre_w]
        elif pre_h < post_h:
            new_post[i, :, :post_w] = post[i, :-(post_h - pre_h), :pre_w]

        # compare width
        if pre_w > post_w:
            new_post[i, :post_h, :post_w] = post[i, : pre_h, :]
        elif pre_w < post_w:
            new_post[i, :post_h, :] = post[i, :pre_h, :-(post_w - pre_w)]

    new_post = np.transpose(new_post, (1, 2, 0))
    return abs(pre - new_post)


def check_scale(scale):
    '''
    the degree of damage is string type. So, this script change string to int.
    no-damage : 0
    minor-damage : 1
    major-damage : 2
    destroyed : 3
    :param scale: According to the degree of damage(string)
    :return: According to the degree of damgage(int)
    '''
    chk = 0
    if scale == 'no-damage':
        chk = 0
    elif scale == 'minor-damage':
        chk = 1
    elif scale == 'major-damage':
        chk = 2
    else:
        chk = 3

    return chk


class CustomDataset(Dataset):
    def __init__(self, x, y, x_transform):
        self.x = x
        self.y = y
        self.x_transform = x_transform

    def __len__(self):
        return len(self.x)

    def __getitem__(self, item):
        # https://stackoverflow.com/questions/60138697/typeerror-cannot-handle-this-data-type-1-1-3-f4
        # https://discuss.pytorch.org/t/typeerror-pic-should-be-pil-image-or-ndarray-got-class-numpy-ndarray/20134
        # Refer above URL
        x = Image.fromarray((self.x[item] * 255).astype(np.uint8))
        x = self.x_transform(x)

        # https://discuss.pytorch.org/t/runtimeerror-expected-object-of-scalar-type-long-but-got-scalar-type-float-when-using-crossentropyloss/30542
        # Error is 'No INT'
        y = self.y[item]

        return x, y


def deprocess(img):
    transform = transforms.Compose([
        transforms.Normalize(mean=(0, 0, 0), std=(1 / 0.2023, 1 / 0.1994, 1 / 0.2010)),
        transforms.Normalize(mean=(-0.4914, -0.4822, -0.4465), std=(1, 1, 1)),
        transforms.ToPILImage(),
    ])
    return transform(img)


def True_image_check(p):
    '''
    Function for inference.
    :param p: test directory path.
    :return: nothing.
    '''
    d = next(walk(p))[1]

    for directory in d:
        print(directory)

        pre_i = path.join(p, directory, directory + '_pre_disaster.png')
        post_i = path.join(p, directory, directory + '_post_disaster.png')
        pre_j = path.join(p, directory, directory + '_pre_disaster.json')
        post_j = path.join(p, directory, directory + '_post_disaster.json')

        originals = []  # pre images
        orii = []  # post images
        types = []  # damage types
        total = []  # pre - post images
        idx = 0  # total images number

        pre_store_dots = []
        post_store_dots = []

        # Get the pre-image
        pre = plt.imread(pre_i)
        with open(pre_j) as labels:
            b = json.load(labels)

        # Get the x, y axis from json file.
        for content in b['features']['xy']:
            # print(content)

            Dots = content['wkt'].split('((')[1].split('))')[0].split(',')

            # Search min/max dot
            min_x = 2000
            max_x = -1
            min_y = 2000
            max_y = -1
            for dot in Dots:
                dot = dot.strip().split(' ')
                x = int(float(dot[0]))
                y = int(float(dot[1]))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
            pre_store_dots += [[min_x, min_y, max_x, max_y]]

            # print(min_x, min_y, max_x, max_y)

            b = pre[min_y:max_y]
            b = np.transpose(b, (1, 0, 2))
            b = b[min_x:max_x]
            b = np.transpose(b, (1, 0, 2))

            total += [b]
            originals += [b]

            # plt.imshow(b)
            # plt.show()

        if total == []:
            print("This area don't have house.")
            return

        post = plt.imread(post_i)
        with open(post_j) as labels:
            c = json.load(labels)

        for content in c['features']['xy']:
            scale = content['properties']['subtype']

            # Except to un-classified
            if scale == 'un-classified':
                del total[idx]
                del originals[idx]
                del pre_store_dots[idx]
                continue
            types += [scale]

            Dots = content['wkt'].split('((')[1].split('))')[0].split(',')
            min_x = 2000
            max_x = -1
            min_y = 2000
            max_y = -1
            for dot in Dots:
                dot = dot.strip().split(' ')
                x = int(float(dot[0]))
                y = int(float(dot[1]))
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

            post_store_dots += [[min_x, min_y, max_x, max_y]]

            # Make the min/max dot
            b = post[min_y:max_y]
            b = np.transpose(b, (1, 0, 2))
            b = b[min_x:max_x]
            b = np.transpose(b, (1, 0, 2))

            # Subtract pre-image and post-image
            if total[idx].shape != b.shape:  # if shape is different.
                total[idx] = calcurate_pre_post(total[idx], b)
            else:
                total[idx] = abs(total[idx] - b)
            orii += [b]  # 제거
            idx += 1

        pre_image = cv2.imread(pre_i)
        post_image = cv2.imread(post_i)

        # Print total image.
        # It is to draw the square into house of image.
        for pre_dot, post_dot, type in zip(pre_store_dots, post_store_dots, types):
            # https://stackoverflow.com/questions/32673359/systemerror-new-style-getargs-format-but-argument-is-not-a-tuple
            # Abolutely, make the tuple type.
            pre_min = (pre_dot[0], pre_dot[1])
            pre_max = (pre_dot[2], pre_dot[3])
            pre_image = cv2.rectangle(pre_image, pre_min, pre_max, (0, 255, 0), 2)

            post_min = (post_dot[0], post_dot[1])
            post_max = (post_dot[2], post_dot[3])
            scale_dot = (post_dot[0] + 10, post_dot[1] + 10)
            post_image = cv2.rectangle(post_image, post_min, post_max, (255, 0, 0), 2)
            post_image = cv2.putText(post_image, str(check_scale(type)), scale_dot, cv2.FONT_HERSHEY_SIMPLEX, 1,
                                     (255, 255, 255), 3)

        fig = plt.figure(figsize=(10, 10))
        fig.suptitle(f"{directory}\n0: No-damaged  1: minor-damaged  2: major-damaged  3: destroyed")
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax1.title.set_text('pre image')
        ax2.title.set_text('post image')
        ax1.imshow(pre_image)
        ax2.imshow(post_image)
        plt.show()

        scales = []
        for s in types:
            scales += [check_scale(s)]

        Resolution = 36
        Batch_size = len(total)

        te_transform = transforms.Compose([transforms.Resize((Resolution, Resolution)),
                                           transforms.ToTensor(),
                                           transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))])

        te_data = CustomDataset(total, scales, te_transform)
        te_loader = DataLoader(te_data, batch_size=Batch_size, shuffle=False)

        criterion = nn.CrossEntropyLoss()

        model = torch.load(p + '/model.pt')
        model.eval()

        # print each house
        idx = 0
        for to, ors, oi, ty in zip(total, originals, orii, types):
            # saliency map
            img, sample_label = te_data.__getitem__(idx)
            sample_img = torch.unsqueeze(img, dim=0).cuda()

            # 1) forward pass through the model to get the scores
            model.eval()
            sample_img.requires_grad_()
            scores = model(sample_img)

            # 2) Get the index corresponding to the maximum score and the maximum score itself.
            score_max_index = torch.argmax(scores)
            score_max = scores[0, score_max_index]

            # 3) backward function on score_max performs the backward pass in the computation graph and calculates the gradient of
            # score_max with respect to nodes in the computation graph
            score_max.backward()

            # 4) Saliency would be the gradient with respect to the input image now. But note that the input image has 3 channels,
            # R, G and B. To derive a single class saliency value for each pixel (i, j),  we take the maximum magnitude
            # across all colour channels.
            saliency_map, _ = torch.max(sample_img.grad.data.abs(), dim=1)

            # 5) Visualized the saliency map
            o = deprocess(img)
            o = np.asarray(o)

            # Check the image.
            fig = plt.figure(figsize=(10, 10))
            fig.suptitle(ty)
            ax1 = fig.add_subplot(531)
            ax2 = fig.add_subplot(532)
            ax3 = fig.add_subplot(533)
            ax4 = fig.add_subplot(537)
            ax5 = fig.add_subplot(538)
            ax1.title.set_text('pre image')
            ax2.title.set_text('post image')
            ax3.title.set_text('pre-post image(Ground Truth)')
            ax4.title.set_text('Resizing Ground Truth')
            ax5.title.set_text('Saliency map')
            ax1.imshow(ors)
            ax2.imshow(oi)
            ax3.imshow(to)
            ax4.imshow(o)
            ax5.imshow(saliency_map[0].cpu(), cmap=plt.cm.hot)
            plt.show()
            idx += 1

        # Start testing
        test_loss = 0
        correct = 0
        total = 0

        result = []
        with torch.no_grad():
            for batch_idx, (inputs, targets) in enumerate(te_loader):
                inputs = inputs.cuda()
                targets = targets.cuda()
                outputs = model(inputs)

                result = torch.argmax(outputs, axis=1)

                loss = criterion(outputs, targets)

                test_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()

        loss = test_loss / len(te_loader)
        acc = 100 * correct / total

        print('Evaluation - Loss : %.2f, Accuracy : %.2f' % (loss, acc))

        prediction_image = cv2.imread(post_i)

        result = result.cpu().numpy()
        for post_dot, type in zip(post_store_dots, result):
            post_min = (post_dot[0], post_dot[1])
            post_max = (post_dot[2], post_dot[3])
            scale_dot = (post_dot[0] + 20, post_dot[1] + 20)
            prediction_image = cv2.rectangle(prediction_image, post_min, post_max, (255, 0, 0), 2)
            prediction_image = cv2.putText(prediction_image, str(type), scale_dot, cv2.FONT_HERSHEY_SIMPLEX, 1,
                                           (255, 0, 255), 3)

        fig = plt.figure(figsize=(10, 10))
        fig.suptitle("Ground Truth vs Prediction\n0: No-damage  1: minor-damage  2: major-damage  3: destroyed")
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax1.title.set_text('Ground Truth')
        ax2.title.set_text('Prediction')
        ax1.imshow(post_image)
        ax2.imshow(prediction_image)
        plt.show()


def test(p, Resolution):
    '''
    Trained model is tested to dataset(Test)
    :param p: Path of trained model
    :param Resolution: Resolution of trained model
    :return:
    '''
    test_path = 'data/pre_test'
    test_file = 'data/test.npy'

    Batch_size = 1024

    if os.path.isfile(test_file):
        load = np.load(test_file, allow_pickle=True)
        te_x, te_y = load[0], load[1]
    else:
        te_x, te_y = make_tensor(test_path)
        np.save(test_file, np.array([te_x, te_y]))

    te_transform = transforms.Compose([transforms.Resize((Resolution, Resolution)),
                                       transforms.ToTensor(),
                                       transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))])

    te_data = CustomDataset(te_x, te_y, te_transform)
    te_loader = DataLoader(te_data, batch_size=Batch_size, shuffle=False)

    criterion = nn.CrossEntropyLoss()

    model = torch.load(p + '/model.pt')
    model.eval()
    model.eval()

    test_loss = 0
    correct = 0
    total = 0

    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(te_loader):
            inputs = inputs.cuda()
            targets = targets.cuda()

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

    loss = test_loss / len(te_loader)
    acc = 100 * correct / total

    print('Evaluation - Loss : %.2f, Accuracy : %.2f' % (loss, acc))


if __name__ == '__main__':
    True_image_check('test')
    test('save/resnet_18_32x32', 32)
