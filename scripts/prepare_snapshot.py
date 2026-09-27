"""Package saved research outputs; never run or modify the optimisation models.

Usage: python scripts/prepare_snapshot.py --enermap <outputs/current> --model <PyPSA-LAEP>
The two inputs are intentionally separate releases. See docs/scope.md.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = []
def digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def record(p, root, family, transform, output):
    MANIFEST.append(dict(source=family+'/'+p.relative_to(root).as_posix(), sha256=digest(p),
                         transform=transform, output=output))
def export(df, rel):
    p=ROOT/rel; p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,float_format='%.10g')
def copy(p, root, family, rel):
    dest=ROOT/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    record(p,root,family,'Unmodified source snapshot',rel)
def clean(obj):
    if isinstance(obj,dict): return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,list): return [clean(v) for v in obj]
    if isinstance(obj,str) and re.match(r'^[A-Za-z]:[/\\]',obj): return '[local source path omitted]/'+obj.replace('\\','/').split('/')[-1]
    return obj
def main(en, model):
    interface=en/'pypsa_interface'; main=model/'pypsa-laep'; dev=model/'pypsa-laep-dev'
    for filename in ['cluster_summary.csv','cluster_annual_totals.csv','heat_pump_cop_hourly.csv','checks.json','pypsa_import_check.json','README_pypsa_interface.md','cases.csv']:
        copy(interface/filename,en,'enermap-current','data/enermap/'+filename)
    copy(en/'completion.json',en,'enermap-current','data/enermap/completion.json')
    copy(en/'baseline/summary.json',en,'enermap-current','data/enermap/baseline_summary.json')
    # Aggregate the actual handoff, not a reconstruction from a different profile library.
    p=interface/'demand_profiles.parquet'; chunks=[]
    vectors=['space_heat_kw','hot_water_heat_kw','non_heating_electricity_kw']
    for batch in pq.ParquetFile(p).iter_batches(batch_size=500000,columns=['timestamp_utc','package_id']+vectors):
        d=batch.to_pandas()
        d[vectors]=d[vectors].astype('float64')
        chunks.append(d.groupby(['package_id','timestamp_utc'])[vectors].sum())
    hourly=pd.concat(chunks).groupby(level=[0,1]).sum().reset_index()
    export(hourly,'data/enermap/hourly_totals.csv')
    record(p,en,'enermap-current','Sum across clusters for each package and timestamp; float64 accumulation; original kW units','data/enermap/hourly_totals.csv')
    cs=pd.read_csv(interface/'cluster_summary.csv')
    bm=pd.read_csv(interface/'building_cluster_map.csv',usecols=['electricity_zone_id','dwelling_count','lon','lat'])
    bm['weighted_lon']=bm.lon*bm.dwelling_count;bm['weighted_lat']=bm.lat*bm.dwelling_count
    zones=bm.groupby('electricity_zone_id').agg(dwellings=('dwelling_count','sum'),x=('weighted_lon','sum'),y=('weighted_lat','sum'))
    zones['lon']=zones.x/zones.dwellings;zones['lat']=zones.y/zones.dwellings
    zones=zones.drop(columns=['x','y']).reset_index().merge(cs[['electricity_zone_id','network_assignment_method']].drop_duplicates(),on='electricity_zone_id',validate='one_to_one')
    export(zones,'data/enermap/zone_centroids.csv')
    record(interface/'building_cluster_map.csv',en,'enermap-current','Dwelling-weighted zone centroids. Individual building IDs and locations excluded','data/enermap/zone_centroids.csv')
    for case,group,base in [('westborough_2035_adder60_td','residential/westborough',main),('exp_clean100_retrofit_fixed_td','residential/clean100_fixed',main),('exp_clean100_td','residential/clean100_retrofit',main),('guildford_td','residential/guildford',main),('dh4_A_individual_td','dh/A',dev),('dh4_B_dh_hp_td','dh/B',dev),('dh4_C_dh_hp_chp_td','dh/C',dev)]:
        folder=base/'results'/case
        for name in ['summary.csv','replay_report.csv','replay_zone_table.csv','zone_table.csv']:
            if (folder/name).exists(): copy(folder/name,model,'pypsa-saved','data/'+group+'/'+name)
        p=folder/'provenance.json'
        if p.exists():
            raw=json.loads(p.read_text()); out={k:clean(raw[k]) for k in ['scenario','generated','model_version','config_hash','config'] if k in raw}
            dest='data/'+group+'/assumptions.json'; (ROOT/dest).write_text(json.dumps(out,indent=2),encoding='utf-8')
            record(p,model,'pypsa-saved','Selected provenance fields; local absolute paths redacted',dest)
        if case in ['westborough_2035_adder60_td','dh4_C_dh_hp_chp_td']:
            p=folder/'option_uptake.csv'; d=pd.read_csv(p)
            agg=d.groupby(['zone','package','system'],as_index=False).dwellings.sum()
            export(agg,'data/'+group+'/uptake.csv');record(p,model,'pypsa-saved','Dwelling-equivalent adoption summed by zone, package and system','data/'+group+'/uptake.csv')
        if case=='dh4_C_dh_hp_chp_td':
            p=folder/'replay_schedules.parquet';d=pd.read_parquet(p);out=pd.DataFrame(index=d.index)
            for system in ['dh_connection','ashp','resistive','gas_boiler_existing']:
                cols=[c for c in d.columns if f'::{system}::' in c and c.endswith('::heat_delivered_mw')]
                if cols: out[system+'_heat_delivered_mw']=d[cols].sum(axis=1)
            out.index.name='timestamp';export(out.reset_index(),'data/dh/C/hourly_heat.csv')
            record(p,model,'pypsa-saved','Sum option heat-delivery schedules by system, same full-year replay','data/dh/C/hourly_heat.csv')
    for name in ['ward_kpis.csv','borough_import_hourly.csv']:
        copy(main/'results/guildford_td'/name,model,'pypsa-saved','data/residential/guildford/'+name)
    for name in ['zone_4_curve.csv','zones_summary.csv','zone_members_check.csv']:
        copy(main/'data/dh/zones'/name,model,'pypsa-saved','data/dh/'+name)
    p=main/'data/dh/guildford_dh_screening.csv'; d=pd.read_csv(p)
    export(d[['length','lhd','built','wkt']],'data/dh/screening_routes.csv')
    record(p,model,'pypsa-saved','Selected screening network columns only; source EPSG:27700; not final construction routes','data/dh/screening_routes.csv')
    copy(dev/'resources/dh4_C_dh_hp_chp_td/dh_candidates.csv',model,'pypsa-saved','data/dh/candidate.csv')
    (ROOT/'docs').mkdir(exist_ok=True)
    manifest={'packaged_on':'2026-09-27','notice':'Latest EnerMap and earlier PyPSA results are separate releases, not a rerun.','sources':MANIFEST}
    (ROOT/'docs/source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Packaged',len(MANIFEST),'source records',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--enermap',type=Path,required=True);ap.add_argument('--model',type=Path,required=True)
    args=ap.parse_args();main(args.enermap,args.model)
