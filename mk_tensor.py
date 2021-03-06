from os import walk, path
import matplotlib.pyplot as plt
import numpy as np
import json


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


def test_module(p, directory, pre_i, post_i, pre_j, post_j):
    '''

    Check the image
    This script is equal to make_tensor function.
    '''
    pre_i = path.join(p, directory, directory + '_pre_disaster.png')
    post_i = path.join(p, directory, directory + '_post_disaster.png')
    pre_j = path.join(p, directory, directory + '_pre_disaster.json')
    post_j = path.join(p, directory, directory + '_post_disaster.json')

    originals = []  # pre images
    orii = []  # post images
    types = []  # damage types
    total = []  # pre - post images
    idx = 0  # total images number

    pre = plt.imread(pre_i)
    with open(pre_j) as labels:  #
        b = json.load(labels)

    for content in b['features']['xy']:

        # print(content)


        Dots = content['wkt'].split('((')[1].split('))')[0].split(',')  # 이건... 노가다의 결과


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

        b = post[min_y:max_y]
        b = np.transpose(b, (1, 0, 2))
        b = b[min_x:max_x]
        b = np.transpose(b, (1, 0, 2))

        if total[idx].shape != b.shape:
            total[idx] = calcurate_pre_post(total[idx], b)
        else:
            total[idx] = abs(total[idx] - b)
        orii += [b]
        idx += 1

    for to, ors, oi, ty in zip(total, originals, orii, types):
        fig = plt.figure(figsize=(4, 10))
        fig.suptitle(ty)
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)

        ax1.title.set_text('pre-post image')
        ax2.title.set_text('pre-image')
        ax3.title.set_text('post-image')

        ax1.imshow(to)
        ax2.imshow(ors)
        ax3.imshow(oi)

        plt.show()


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


def make_tensor(p):
    '''
    According to directory, make a image tensor.
    (the number of images, Height, Width, Channel)
    :param p: directory path
    :return: (total, total_scale) -> (total image, total degree of damage)
    '''
    # Load all directory below 'p'
    a = next(walk(p))[1]

    # The number of house
    i = 0

    # List of all images
    total = []

    # List of all damaged scales
    total_scale = []

    # number of testing
    test_number = 2000

    # Index number of total value
    idx = 0

    # max/min height and width
    min_h = 1000
    min_w = 1000
    max_h = -1
    max_w = -1

    # Average height and width
    mean_h = 0
    mean_w = 0

    # start by directory
    '''
        directory shape
        p ---- guatemala-volcano_00000 ---  이름_post_disaster.json
            |                           |
            |                           --  이름_post_disaster.png
            |                           |
            |                           --  이름_pre_disaster.json
            |                           |
            |                           --  이름_pre_disaster.png
            |
            -- guatemala-vocano_00001 --- ...
            |
            ...
    '''
    for directory in a:
        # Separate each pre/post image and json file
        pre_i = path.join(p, directory, directory + '_pre_disaster.png')
        post_i = path.join(p, directory, directory + '_post_disaster.png')
        pre_j = path.join(p, directory, directory + '_pre_disaster.json')
        post_j = path.join(p, directory, directory + '_post_disaster.json')

        # Get the pre-image
        pre = plt.imread(pre_i)

        # Open json file
        with open(pre_j) as labels:
            pre_contents = json.load(labels)

        # Get x, y axis from json file
        for content in pre_contents['features']['xy']:
            # Below script is 'json-file content'
            # print(content)

            # Pull dots. Because This dataset is annotated in polygon for houses.
            Dots = content['wkt'].split('((')[1].split('))')[0].split(',')  # The result of hard work....

            # Search min/max dot and make a square shape for houses.
            pre_min_x = 2000
            pre_max_x = -1
            pre_min_y = 2000
            pre_max_y = -1
            for dot in Dots:
                dot = dot.strip().split(' ')
                x = int(float(dot[0])) if float(dot[0]) >= 0 else 0
                y = int(float(dot[1])) if float(dot[1]) >= 0 else 0
                pre_min_x = min(pre_min_x, x)
                pre_max_x = max(pre_max_x, x)
                pre_min_y = min(pre_min_y, y)
                pre_max_y = max(pre_max_y, y)

            # Below script is 'min/max dot'.
            # print(min_x, min_y, max_x, max_y)

            # The reason used np.transpose is easily to divide pre-image.
            c = pre[pre_min_y:pre_max_y]  # (h, w, c)
            c = np.transpose(c, (1, 0, 2))  # (h, w, c) -> (w, h, c)
            c = c[pre_min_x:pre_max_x]  # (w, h, c)
            c = np.transpose(c, (1, 0, 2))  # (w, h, c) -> (h, w, c)

            # Store result annotated house to total value. -> Subsequently, it  is subtracted from the below script.
            total += [c]

            # Check the annotated house.
            # plt.imshow(c)
            # plt.show()

        # current pre-image don't have houses ->  e.g first image don't have houses.
        if total == []:
            i += 1
            continue

        # Check the index and pre-image being processing.
        # print(i, pre_i)

        # Get the post-image. it is equal to above pre-image.
        # But, when total value is stored, compare to pre-image.
        post = plt.imread(post_i)
        with open(post_j) as labels:
            post_contents = json.load(labels)

        for content in post_contents['features']['xy']:
            # scale의 경우 해당 집이 어떤 피해를 입은지 알려준다.
            scale = content['properties']['subtype']

            # Except to no-annotation
            # https://wikidocs.net/16040
            if scale == 'un-classified':
                del total[idx]
                continue
            total_scale += [check_scale(scale)]

            # Extract dots and search min/max dot
            post_Dots = content['wkt'].split('((')[1].split('))')[0].split(',')
            min_x = 2000
            max_x = -1
            min_y = 2000
            max_y = -1
            for dot in post_Dots:
                dot = dot.strip().split(' ')
                x = int(float(dot[0])) if float(dot[0]) >= 0 else 0
                y = int(float(dot[1])) if float(dot[1]) >= 0 else 0
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

            mean_h += max_y - min_y
            mean_w += max_x - min_x

            # Make min/max dot
            b = post[min_y:max_y]
            b = np.transpose(b, (1, 0, 2))
            b = b[min_x:max_x]
            b = np.transpose(b, (1, 0, 2))

            # Check the post-image
            # plt.imshow(b)
            # plt.show()

            # subtract pre and post (to check difference between pre and post)
            if total[idx].shape != b.shape:  # 모양이 다른 경우
                total[idx] = calcurate_pre_post(total[idx], b)
            else:
                total[idx] = abs(total[idx] - b)
            idx += 1

        # Check the pre/post image and json file
        # print(pre_i, post_i, pre_j, post_j)

        # Test module
        if i == test_number:
            test_module(p, directory, pre_i, post_i, pre_j, post_j)

        min_h = min(min_h, total[idx - 1].shape[0])
        min_w = min(min_w, total[idx - 1].shape[1])
        max_h = max(max_h, total[idx - 1].shape[0])
        max_w = max(max_w, total[idx - 1].shape[1])
        i += 1

        # Check if the height or width is '0'
        if total[idx - 1].shape[0] <= 0 or total[idx - 1].shape[1] <= 0:
            print(pre_i)
            print(total[idx - 1].shape[0])
            print(total[idx - 1].shape[1])
            print('pre', pre_min_y, pre_max_y, pre_min_x, pre_max_x)
            print('post', min_y, max_y, min_x, max_x)
            print(post_Dots)
            plt.imshow(c)
            plt.show()
            plt.imshow(b)
            plt.show()

    print('Data Processing Success!')
    print(f'max_h = {max_h}\tmax_w = {max_w}\tmin_h = {min_h}\tmin_w = {min_w}')
    print(f'mean_h = {mean_h / len(total)}\tmean_w = {mean_w / len(total)}')
    print(len(total))
    return total, total_scale


if __name__ == '__main__':
    make_tensor('data/pre_train')
