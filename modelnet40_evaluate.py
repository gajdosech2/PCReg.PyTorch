import argparse
import numpy as np
import open3d as o3d
import random
import time
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from data import ModelNet40
from models import Benchmark, IterativeBenchmark, icp, fgr
from metrics import anisotropic_R_error, anisotropic_t_error, isotropic_R_error, \
    isotropic_t_error
from utils import npy2pcd, pcd2npy, inv_R_t


def config_params():
    parser = argparse.ArgumentParser(description='Configuration Parameters')
    parser.add_argument('--root', required=True, help='the data path')
    parser.add_argument('--train_npts', type=int, default=2048,
                        help='the points number of each pc for training')
    parser.add_argument('--in_dim', type=int, default=3,
                        help='3 for (x, y, z) or 6 for (x, y, z, nx, ny, nz)')
    parser.add_argument('--niters', type=int, default=8,
                        help='iteration nums in one model forward')
    parser.add_argument('--checkpoint', default='',
                        help='the path to the trained checkpoint')
    parser.add_argument('--method', default='',
                        help='choice=[benchmark, icp, fgr]')
    parser.add_argument('--cuda', action='store_true',
                        help='whether to use the cuda')
    parser.add_argument('--show', action='store_true',
                        help='whether to visualize')
    args = parser.parse_args()
    return args


def evaluate_benchmark(args, test_loader):
    model = IterativeBenchmark(in_dim1=args.in_dim, niters=args.niters)
    if args.cuda:
        model = model.cuda()
        model.load_state_dict(torch.load(args.checkpoint))
    else:
        model.load_state_dict(torch.load(args.checkpoint, map_location=torch.device('cpu')))
    model.eval()

    dura = []
    r_mse, r_mae, t_mse, t_mae, r_isotropic, t_isotropic = [], [], [], [], [], []
    with torch.no_grad():
        for i, (ref_cloud, src_cloud, gtR, gtt) in tqdm(enumerate(test_loader)):
            if args.cuda:
                ref_cloud, src_cloud, gtR, gtt = ref_cloud.cuda(), src_cloud.cuda(), \
                                                 gtR.cuda(), gtt.cuda()
            tic = time.time()
            R, t, pred_ref_cloud = model(src_cloud.permute(0, 2, 1).contiguous(), 
                    ref_cloud.permute(0, 2, 1).contiguous())
            toc = time.time()
            dura.append(toc - tic)
            inv_R, inv_t = inv_R_t(gtR, gtt)
            cur_r_mse, cur_r_mae = anisotropic_R_error(R, inv_R)
            cur_t_mse, cur_t_mae = anisotropic_t_error(t, inv_t)
            cur_degree_error = isotropic_R_error(R, inv_R)
            cur_t_isotropic = isotropic_t_error(t, inv_t, inv_R)
            r_mse.append(cur_r_mse)
            r_mae.append(cur_r_mae)
            t_mse.append(cur_t_mse)
            t_mae.append(cur_t_mae)
            r_isotropic.append(cur_degree_error.cpu().detach().numpy())
            t_isotropic.append(cur_t_isotropic.cpu().detach().numpy())

            if args.show:
                print(cur_t_error.item(), cur_R_error.item(),
                      cur_degree_error.item())
                ref_cloud = torch.squeeze(ref_cloud).cpu().numpy()
                src_cloud = torch.squeeze(src_cloud).cpu().numpy()
                pred_ref_cloud = torch.squeeze(pred_ref_cloud).cpu().numpy()
                pcd1 = npy2pcd(ref_cloud, 0)
                pcd2 = npy2pcd(src_cloud, 1)
                pcd3 = npy2pcd(pred_ref_cloud, 2)
                o3d.visualization.draw_geometries([pcd1, pcd2, pcd3])
    r_mse = np.concatenate(r_mse, axis=0)
    r_mae = np.concatenate(r_mae, axis=0)
    t_mse = np.concatenate(t_mse, axis=0)
    t_mae = np.concatenate(t_mae, axis=0)
    r_isotropic = np.concatenate(r_isotropic, axis=0)
    t_isotropic = np.concatenate(t_isotropic, axis=0)

    return dura, np.sqrt(np.mean(r_mse)), np.mean(r_mae), \
           np.sqrt(np.mean(t_mse)), np.mean(t_mae), np.mean(r_isotropic), \
           np.mean(t_isotropic)


def evaluate_icp(args, test_loader):
    dura = []
    t_errors, R_errors, degree_errors = [], [], []

    for i, (ref_cloud, src_cloud, gtR, gtt) in tqdm(enumerate(test_loader)):
        if args.cuda:
            ref_cloud, src_cloud, gtR, gtt = ref_cloud.cuda(), src_cloud.cuda(), \
                                             gtR.cuda(), gtt.cuda()

        ref_cloud = torch.squeeze(ref_cloud).cpu().numpy()
        src_cloud = torch.squeeze(src_cloud).cpu().numpy()

        tic = time.time()
        R, t, pred_ref_cloud = icp(npy2pcd(src_cloud), npy2pcd(ref_cloud))
        toc = time.time()
        R = torch.from_numpy(np.expand_dims(R, 0)).to(gtR)
        t = torch.from_numpy(np.expand_dims(t, 0)).to(gtt)
        dura.append(toc - tic)
        cur_t_error = translation_error(t, -gtt[..., None])
        cur_R_error = rotation_error(R, gtR.permute(0, 2, 1).contiguous())
        cur_degree_error = degree_error(R, gtR.permute(0, 2, 1).contiguous())
        t_errors.append(cur_t_error.item())
        R_errors.append(cur_R_error.item())
        degree_errors.append(cur_degree_error.item())

        if args.show:
            print(cur_t_error.item(), cur_R_error.item(),
                  cur_degree_error.item())
            pcd1 = npy2pcd(ref_cloud, 0)
            pcd2 = npy2pcd(src_cloud, 1)
            pcd3 = pred_ref_cloud
            o3d.visualization.draw_geometries([pcd1, pcd2, pcd3])
    return dura, np.mean(t_errors), np.mean(R_errors), np.mean(degree_errors)


# Not complete
def evaluate_fgr(args, test_loader):
    pass


if __name__ == '__main__':
    seed = 222
    random.seed(seed)
    np.random.seed(seed)

    args = config_params()

    test_set = ModelNet40(args.root, args.train_npts, False)
    test_loader = DataLoader(test_set, batch_size=16, shuffle=False)

    if args.method == 'benchmark':
        dura, R_mse, R_mae,t_mse, t_mae, degree_error,t_isotropic = \
            evaluate_benchmark(args, test_loader)
        print('time: {:.2f} s, mean: {:.5f} s'.format(np.sum(dura), np.mean(dura)))
        print('mean mse Euler degree error: {:.2f}'.format(R_mse))
        print('mean mae Euler degree error: {:.2f}'.format(R_mae))
        print('mean mse translation error: {:.2f}'.format(t_mse))
        print('mean mae translation error: {:.2f}'.format(t_mae))
        print('mean degree error: {:.2f}'.format(degree_error))
        print('mean isotropic translation error: {:.2f}'.format(t_isotropic))
    elif args.method == 'icp':
        dura, t_error, R_error, degree_error = evaluate_icp(args, test_loader)
        print('time: {:.2f} s, mean: {:.2f} s'.format(np.sum(dura), np.mean(dura)))
        print('mean tranlation error: {:.2f}'.format(t_error))
        print('mean rotation error: {:.2f}'.format(R_error))
        print('mean degree error: {:.2f}'.format(degree_error))
    elif args.method == 'fgr':
        raise NotImplementedError
    else:
        b_dura, b_t_error, b_R_error, b_mse_R_error = evaluate_benchmark(args,
                                                                 test_loader)
        i_dura, i_t_error, i_R_error, i_mse_R_error = evaluate_icp(args, test_loader)
        raise NotImplementedError
