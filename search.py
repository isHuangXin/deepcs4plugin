import os
import sys
import traceback
import numpy as np
import argparse
import threading
import codecs
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

import torch

from utils import normalize, similarity, sent2indexes
from data_loader import load_dict, load_vecs
import models, configs
  
codevecs, codebase = [], []

##### Data Set #####   
def load_codebase(code_path, chunk_size=2000000):
    """load codebase
      codefile: h5 file that stores raw code
    """
    logger.info(f'Loading codebase (chunk size={chunk_size})..')
    codebase= []
    codes = codecs.open(code_path, encoding='latin-1').readlines() # use codecs to read in case of encoding problem
    for i in range(0, len(codes), chunk_size):
        codebase.append(codes[i: i+chunk_size]) 
    '''
    import subprocess
    n_lines = int(subprocess.check_output(["wc", "-l", code_path], universal_newlines=True).split()[0])
    for i in range(1, n_lines+1, chunk_size):
        codecs = subprocess.check_output(["sed",'-n',f'{i},{i+chunk_size}p', code_path]).split()
        codebase.append(codecs)
   '''
    return codebase

### Results Data ###
def load_codevecs(vec_path, chunk_size=2000000):
    logger.debug(f'Loading code vectors (chunk size={chunk_size})..')       
    """read vectors (2D numpy array) from a hdf5 file"""
    codevecs=[]
    chunk_id = 0
    chunk_path = f"{vec_path[:-3]}_part{chunk_id}.h5"
    while os.path.exists(chunk_path):
        reprs = load_vecs(chunk_path)
        codevecs.append(reprs)
        chunk_id+=1
        chunk_path = f"{vec_path[:-3]}_part{chunk_id}.h5"
    return codevecs

def search(config, model, vocab, query, n_results=10):
    model.eval()
    device = next(model.parameters()).device
    desc, desc_len =sent2indexes(query, vocab_desc, config['desc_len'])#convert query into word indices
    desc = torch.from_numpy(desc).unsqueeze(0).to(device)
    desc_len = torch.from_numpy(desc_len).clamp(max=config['desc_len']).to(device)
    with torch.no_grad():
        desc_repr = model.desc_encoding(desc, desc_len).data.cpu().numpy().astype(np.float32) # [1 x dim]
    if config['sim_measure']=='cos': # normalizing vector for fast cosine computation
        desc_repr = normalize(desc_repr) # [1 x dim]
    results =[]
    threads = []
    for i, codevecs_chunk in enumerate(codevecs):
        t = threading.Thread(target=search_thread, args = (results, desc_repr, codevecs_chunk, i, n_results, config['sim_measure']))
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:#wait until all sub-threads have completed
        t.join()
    return results

def search_thread(results, desc_repr, codevecs, i, n_results, sim_measure):        
#1. compute code similarities
    if sim_measure=='cos':
        chunk_sims = np.dot(codevecs, desc_repr.T)[:,0] # [pool_size]
    else:
        chunk_sims = similarity(codevecs, desc_repr, sim_measure) # [pool_size]
    
#2. select the top K results
    negsims = np.negative(chunk_sims)
    maxinds = np.argpartition(negsims, kth=n_results-1)
    maxinds = maxinds[:n_results]  
    chunk_codes = [codebase[i][k] for k in maxinds]
    chunk_sims = chunk_sims[maxinds]
    results.extend(zip(chunk_codes, chunk_sims))
    
def postproc(codes_sims):
    codes_, sims_ = zip(*codes_sims)
    codes = [code for code in codes_]
    sims = [sim for sim in sims_]
    final_codes = []
    final_sims = []
    n = len(codes_sims)        
    for i in range(n):
        is_dup=False
        for j in range(i):
            if codes[i][:80]==codes[j][:80] and abs(sims[i]-sims[j])<0.01:
                is_dup=True
        if not is_dup:
            final_codes.append(codes[i])
            final_sims.append(sims[i])
    return zip(final_codes,final_sims)
    
def parse_args():
    parser = argparse.ArgumentParser("Train and Test Code Search(Embedding) Model")
    parser.add_argument('--data_path', type=str, default='./data/', help='location of the data corpus')
    parser.add_argument('--model', type=str, default='JointEmbeder', help='model name')
    parser.add_argument('-d', '--dataset', type=str, default='example', help='name of dataset.java, python')
    parser.add_argument('-t', '--timestamp', type=str, help='time stamp')
    parser.add_argument('--reload_from', type=int, default=4000000, help='step to reload from')
    parser.add_argument('--chunk_size', type=int, default=2000000, help='codebase and code vector are stored in many chunks. '\
                         'Note: should be consistent with the same argument in the repr_code.py')
    parser.add_argument('-g', '--gpu_id', type=int, default=0, help='GPU ID')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    device = torch.device(f"cuda:{args.gpu_id}" if torch.cuda.is_available() else "cpu")
    config = getattr(configs, 'config_'+args.model)()
    
    ##### Define model ######
    logger.info('Constructing Model..')
    model = getattr(models, args.model)(config)#initialize the model
    ckpt = f"./trained_model/step{args.reload_from}.h5"
    model.load_state_dict(torch.load(ckpt, map_location=device))
    model.eval()
    data_path = args.data_path+args.dataset+'/'
    
    vocab_desc = load_dict(data_path+config['vocab_desc'])
    codebase = load_codebase(data_path+config['use_codebase'], args.chunk_size)
    codevecs = load_codevecs(data_path+config['use_codevecs'], args.chunk_size)
    assert len(codebase)==len(codevecs), \
         "inconsistent number of chunks, check whether the specified files for codebase and code vectors are correct!"    
    
    while True:
        try:
            # query = input('Input Query: ')
            # n_results = int(input('How many results? '))
            query = "determine whether the specified name has been used as a key in this table or any of its parents"
            n_results = 10
        except Exception:
            print("Exception while parsing your input:")
            traceback.print_exc()
            break
        query = query.lower().replace('how to ', '').replace('how do i ', '').replace('how can i ', '').replace('?', '').strip()
        results = search(config, model, vocab_desc, query, n_results)
        results = sorted(results, reverse=True, key=lambda x:x[1])
        results = postproc(results)
        results = list(results)[:n_results]
        results = '\n\n'.join(map(str,results)) #combine the result into a returning string
        print(results)

