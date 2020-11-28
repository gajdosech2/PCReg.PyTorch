import h5py
import numpy as np
import open3d as o3d
import os
import torch

from torch.utils.data import Dataset
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOR_DIR = os.path.dirname(BASE_DIR)
sys.path.append(ROOR_DIR)
from utils import pc_normalize, random_select_points, shift_point_cloud, \
    jitter_point_cloud, generate_random_rotation_matrix, \
    generate_random_tranlation_vector, transform


class ModelNet40(Dataset):
    def __init__(self, root, npts, train=True, normal=False):
        super(ModelNet40, self).__init__()
        self.npts = npts
        self.train = train
        self.normal = normal
        files = [os.path.join(root, 'ply_data_train{}.h5'.format(i))
                 for i in range(5)]
        if not train:
            files = [os.path.join(root, 'ply_data_test{}.h5'.format(i))
                     for i in range(2)]
        self.data, self.labels = self.decode_h5(files)
        l = len(self.data)
        self.Rs = [generate_random_rotation_matrix() for _ in range(l)]
        self.ts = [generate_random_tranlation_vector() for _ in range(l)]
    
    def decode_h5(self, files):
        points, normal, label = [], [], []
        for file in files:
            f = h5py.File(file, 'r')
            cur_points = f['data'][:].astype(np.float32)
            cur_normal = f['normal'][:].astype(np.float32)
            cur_label = f['label'][:].astype(np.float32)
            points.append(cur_points)
            normal.append(cur_normal)
            label.append(cur_label)
        points = np.concatenate(points, axis=0)
        normal = np.concatenate(normal, axis=0)
        data = np.concatenate([points, normal], axis=-1).astype(np.float32)
        label = np.concatenate(label, axis=0)
        return data, label

    def __getitem__(self, item):
        ref_cloud = self.data[item, ...]
        R, t = self.Rs[item], self.ts[item]
        ref_cloud = random_select_points(ref_cloud, m=self.npts)
        src_cloud_points = transform(ref_cloud[:, :3], R, t)
        src_cloud_normal = transform(ref_cloud[:, 3:], R)
        src_cloud = np.concatenate([src_cloud_points, src_cloud_normal], axis=-1)
        if self.train:
            ref_cloud[:, :3] = jitter_point_cloud(ref_cloud[:, :3])
            src_cloud[:, :3] = jitter_point_cloud(src_cloud[:, :3])
        if not self.normal:
            ref_cloud, src_cloud = ref_cloud[:, :3], src_cloud[:, :3]
        return ref_cloud, src_cloud, R, t

    def __len__(self):
        return len(self.data)


if __name__ == '__main__':
    seed = 1234
    torch.backends.cudnn.deterministic = True
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    from torch.utils.data import DataLoader
    root = '/root/data/modelnet40_ply_hdf5_2048'
    #modelnet = ModelNet40(root, npts=1024)
    train_set = ModelNet40(root, 1024)
    test_set = ModelNet40(root, 1024, False)
    train_loader = DataLoader(train_set, batch_size=20,
                            shuffle=True, num_workers=4)
    test_loader = DataLoader(test_set, batch_size=20, shuffle=False,
                            num_workers=4)
    #loader = DataLoader(modelnet, batch_size=20, shuffle=True, num_workers=4)
    for epoch in range(2):
        for i, (a, b, c, d) in enumerate(train_loader):
            print('epoch: ', epoch)
            if i > 2:
                break
