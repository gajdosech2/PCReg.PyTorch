import os
import sys

  
def process(root):
  datasets = os.listdir(root)
  for dataset in datasets:
    if os.path.isdir(root + '/' + dataset):
      files = os.listdir(root + '/' + dataset + '/')
      for file in files:
        if ".cogs" in file:  
          name = file.split('.')[0]
          print("processing: " + name)
          if os.name == 'nt':
            os.system('"WCC.exe"' + 
                      ' --pcd ' + 
                      root + '/' + dataset + '/' + file + ' ' + 
                      root + '/' + dataset + '/' )
        else:
          pass
  

if __name__ == "__main__":
  process("dataset/CustomData/")
