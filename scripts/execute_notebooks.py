"""Execute every notebook with this Python, then export self-contained HTML."""
from pathlib import Path
import json, sys, tempfile
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
ROOT=Path(__file__).resolve().parents[1]
def main():
    (ROOT/'reports').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='laep-kernel-') as temp:
        kernels=Path(temp)/'kernels';spec=kernels/'python3';spec.mkdir(parents=True)
        (spec/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Python 3','language':'python'}))
        for p in sorted((ROOT/'notebooks').glob('*.ipynb')):
            print('Executing',p.name,flush=True)
            nb=nbformat.read(p,as_version=4)
            km=KernelManager(kernel_name='python3',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]))
            client=NotebookClient(nb,km=km,timeout=180,resources={'metadata':{'path':str(ROOT)}})
            try:
                client.execute()
            finally:
                if km.has_kernel: km.shutdown_kernel(now=True)
            nbformat.write(nb,p)
            html,_=HTMLExporter(embed_images=True,exclude_input=True,exclude_input_prompt=True,exclude_output_prompt=True).from_notebook_node(nb,resources={'metadata':{'name':p.stem}})
            (ROOT/'reports'/f'{p.stem}.html').write_text(html,encoding='utf-8')
            print('Saved outputs and HTML:',p.stem,flush=True)
if __name__=='__main__':main()
