python modelnet40_train.py --root dataset/modelnet40_ply_hdf5_2048
python custom_train.py --root dataset/custom --train_npts 8192 --num_workers 1 --batchsize 1 --epoches 200 --lr 0.01
python custom_train.py --root dataset/custom --train_npts 8192 --batchsize 5 --epoches 100