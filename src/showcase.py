"""Small, inspectable plotting helpers. No optimisation or hidden modelling."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FormatStrFormatter
from matplotlib.colors import LinearSegmentedColormap

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
TEAL='#259d98'; BLUE='#378bb9'; GOLD='#db9144'; PURPLE='#9470b6'; INK='#233f4b'; GREY='#9aabb3'
COLORS=[TEAL,BLUE,GOLD,PURPLE,GREY]
CMAP=LinearSegmentedColormap.from_list('laep',['#e5f3f0',TEAL,'#06495e'])
def style():
    plt.rcParams.update({'figure.figsize':(11,4.8),'figure.dpi':120,'savefig.dpi':160,
        'font.family':'DejaVu Sans','font.size':11,'text.color':INK,'axes.labelcolor':INK,
        'xtick.color':INK,'ytick.color':INK,'axes.spines.top':False,'axes.spines.right':False,
        'axes.edgecolor':'#c9d7dc','axes.titleweight':'bold','axes.titlepad':16,
        'axes.prop_cycle':plt.cycler(color=COLORS),'figure.facecolor':'white',
        'axes.facecolor':'white','grid.color':'#e8edef','axes.axisbelow':True})
def read(path,**kwargs): return pd.read_csv(DATA/path,**kwargs)
def js(path): return json.loads((DATA/path).read_text(encoding='utf-8'))
def summary(path): return read(path+'/summary.csv',index_col=0)['economic']
def finish(fig,name):
    fig.tight_layout(pad=1.8)
    (ROOT/'assets').mkdir(exist_ok=True)
    fig.savefig(ROOT/'assets'/f'{name}.png',bbox_inches='tight')
    plt.show()
def labelbars(ax,fmt='{:,.0f}',suffix=''):
    for container in ax.containers:
        ax.bar_label(container,labels=[fmt.format(v)+suffix for v in container.datavalues],padding=4,fontsize=10)
def mapzones(ax,z,value,title,label):
    scatter=ax.scatter(z.lon,z.lat,c=value,s=35+z.dwellings/2,cmap=CMAP,
                       edgecolor='white',linewidth=.7,vmin=0,vmax=100)
    ax.set(title=title,xlabel='Longitude',ylabel='Latitude')
    ax.set_aspect(1/np.cos(np.deg2rad(z.lat.mean())))
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.grid(alpha=.5)
    plt.colorbar(scatter,ax=ax,shrink=.75,label=label)
    return scatter
