import os
from os import walk, path, makedirs
from shutil import copy2 as cp
import argparse
'''
    This script Change from original folder to New folder.
    <original folder shape>
    original ----- images ----- 1_pre.jpg 1_post.jpg 2_pre.jpg 2_post.jpg ...
            |
            |
             ----- labels ----- 1_pre.json 1_post.json 2_pre.json 2_post.json ...
             
    <New folder shape>
    New  ----- ex1 ----- ex1_pre.jpg ex1_pre.json ex1_post.jpg ex1_post.json 
        |
        |
         ----- ex2 ----- ex2_pre.jpg ex2_pre.json ex2_post.jpg ex2_post.json
        |
        |
         ----- ex3 ----- ex3_pre.jpg ex3_pre.json ex3_post.jpg ex3_post.json
         .
         .
         .
        All dataset           
    
'''

# Get file name
def get_files(base_dir):
    '''

    :param base_dir: directory location. ex) train, test
    :return: files name. ex) name000_number_pre_disaster.png
    '''
    # Minmizing (halfing) list to just pre image files
    base_dir = base_dir + '/images'

    files = [f for f in next(walk(base_dir))[2] if "pre" in f]

    return files

# change from pre image name to post image name
def pre_to_post(file):
    '''
    This script change file name from pre image name to post image name
    :param file: file name(pre)
    :return:  file name(post)
    '''
    file = file.split('_')
    file[2] = 'post'
    file = '_'.join(file)

    return file

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='make sum folder')

    parser.add_argument('--original', type=str, help='Input your train/test directory path. ex) "data/test/"', required=True)
    parser.add_argument('--new', type=str, help='Input your new directory path. ex) "data/pre_test"', required=True)

    args = parser.parse_args()

    original = args.original
    new = args.new

    # Reference to below URL.
    # https://cinema4dr12.tistory.com/1296
    try:
        if not(os.path.isdir(new)):
            os.makedirs(os.path.join(new))
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("Failed to cerate directory!!!!!")
            raise

    # get the file names
    files = get_files(original)
    i = 0

    for file in files:
        '''
            pre: pre image file name
            post: post image file name
            pre_json: pre json file name
            post_json: post json file name
        '''
        pre = file
        post = pre_to_post(pre)
        pre_json = pre.split('.')[0] + '.json'
        post_json = post.split('.')[0] + '.json'
        name = post.split('_post')[0]

        # make directory
        makedirs(path.join(new, name))

        # copy from original to new.
        cp(path.join(original, 'images', pre), path.join(new, name))
        cp(path.join(original, 'images', post), path.join(new, name))
        cp(path.join(original, 'labels', pre_json), path.join(new, name))
        cp(path.join(original, 'labels', post_json), path.join(new, name))

        # Print every 1000th file name to see the progress.
        if i % 1000 == 0:
            print(pre, post, name)
        i += 1
