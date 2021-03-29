import os
import sys
from shutil import copyfile

  
def process(root):
    datasets = os.listdir(root)
    for dataset in datasets:
        files = os.listdir(root + '/' + dataset + '/')
      
        for scan in files:
            if '.cogs' in scan and 'p.cogs' not in scan:  
                name = scan.split('.')[0]
                print('processing: ' + name)
                bin = name + 'p.cogs'
              
                export_path = 'dataset/custom/train_data/'
                if not os.path.exists(export_path):
                    os.makedirs(export_path)
                
                copyfile(root + '/' + dataset + '/' + name + '_remaining_transform.txt', 
                       export_path + name + '_remaining_transform.txt')
                
                if os.name == 'nt':
                    os.system('WCC.exe' + 
                              ' --pcd ' + 
                              root + '/' + dataset + '/' + scan + ' ' + 
                              export_path )
                    os.system('WCC.exe' + 
                              ' --pcd ' + 
                              root + '/' + dataset + '/' + bin + ' ' + 
                              export_path )
                      
            
if __name__ == '__main__':
  process('dataset/raw/')
