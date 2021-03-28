import numpy as np
import os
import torch
from torch.utils.data import Dataset

from utils import readpcd
from utils import pc_normalize, random_select_points, shift_point_cloud, \
    jitter_point_cloud, generate_random_rotation_matrix, \
    generate_random_tranlation_vector, transform


class CustomData(Dataset):
    def __init__(self, root, npts, train=True):
        super(CustomData, self).__init__()
        dirname = 'train_data' if train else 'val_data'
        path = os.path.join(root, dirname)
        self.train = train
        self.files = [os.path.join(path, item) for item in sorted(os.listdir(path)) if ".pcd" in item]
        self.npts = npts
        
    def read_transform(self, transform_file):
        params = []
        with open(transform_file) as read_file:
            params = read_file.readline().strip().split(" ")
    
        R = np.eye(3, dtype=np.float32)
        
        R[0, 0] = float(params[0])
        R[1, 0] = float(params[1])
        R[2, 0] = float(params[2])
        
        R[0, 1] = float(params[4])
        R[1, 1] = float(params[5])
        R[2, 1] = float(params[6])
        
        R[0, 2] = float(params[8])
        R[1, 2] = float(params[9])
        R[2, 2] = float(params[10])
        
        t = np.array([float(params[12]), float(params[13]), float(params[14])]).astype(np.float32)
        return R, t

    def __getitem__(self, item):
        file = self.files[item]
        R, t = self.read_transform(file[:-4] + "_bin_transform.txt")
        
        ref_cloud = readpcd(file, rtype='npy')
        ref_cloud = random_select_points(ref_cloud, m=self.npts)

        src_cloud = readpcd("dataset/bin.pcd", rtype='npy')
        src_cloud = random_select_points(src_cloud, m=8192)
        return ref_cloud, src_cloud, R, t

    def __len__(self):
        return len(self.files)