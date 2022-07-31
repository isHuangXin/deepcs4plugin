from glob import glob
import http
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

import json

from search import *
import configs

class NaccCodeSearchContext:
    def __init__(self, config, model, vocab_desc):
        self.config = config
        self.model = model
        self.vocab_desc = vocab_desc

context = NaccCodeSearchContext(None, None, None)

class NaccCodeSearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = self.headers["query"]
        n_results = int(self.headers["nresult"])
        query = query.lower().replace('how to ', '').replace('how do i ', '').replace('how can i ', '').replace('?', '').strip()
        results = search(context.config, context.model, context.vocab_desc, query, n_results)
        results = sorted(results, reverse=True, key=lambda x:x[1])
        results = postproc(results)
        results = list(results)[:n_results]
        super().send_response(http.HTTPStatus.OK)
        super().end_headers()
        self.wfile.write(json.dumps(results).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler):
    conf = configs.config_HttpSever()
    server_address = (conf['domain'], conf['port'])
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == "__main__":
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

    context = NaccCodeSearchContext(config, model, vocab_desc)
    
    run(HTTPServer, NaccCodeSearchHandler)