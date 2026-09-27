"""Readable notebook sources. Execute with execute_notebooks.py after building."""
from pathlib import Path
import textwrap
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
def md(s): return nbf.v4.new_markdown_cell(textwrap.dedent(s).strip())
def code(s): return nbf.v4.new_code_cell(textwrap.dedent(s).strip())
SETUP=code('''
from pathlib import Path
import sys
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'src/showcase.py').exists())
sys.path.insert(0, str(ROOT/'src'))
from showcase import *
from IPython.display import display
style()
pd.set_option('display.precision', 3)
''')
def save(name,cells):
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11'}})
    (ROOT/'notebooks').mkdir(exist_ok=True)
    nbf.write(nb,ROOT/'notebooks'/f'{name}.ipynb')

save('01_enermap_latest_handoff',[
md('''
# EnerMap → PyPSA-LAEP
### The latest residential demand handoff · completed 23 September 2026

The starting point is simple: before deciding how to heat a place, we need to understand
its buildings. This notebook opens the latest completed EnerMap export and shows what
it can pass to the optimisation model: **where demand is, when it occurs, and how it
changes under alternative retrofit packages**.

This is the **57,300-dwelling Guildford-area stock**, not just the smaller town or
Westborough optimisation area. It is an uncalibrated, median-archetype release.
The optimisation notebooks alongside this one use an **earlier handoff**; they have
not yet been rerun with these data. Snapshot packaged 27 September 2026.
'''),SETUP,
code('''
clusters = read('enermap/cluster_summary.csv')
annual = read('enermap/cluster_annual_totals.csv')
hourly = read('enermap/hourly_totals.csv', parse_dates=['timestamp_utc'])
zones = read('enermap/zone_centroids.csv')
completion = js('enermap/completion.json')
display(pd.Series({'Dwellings':int(clusters.dwelling_count.sum()),
                   'Building records':int(clusters.building_count.sum()),
                   'Demand clusters':len(clusters), 'Electricity zones':len(zones),
                   'Hourly steps per package':hourly.groupby('package_id').size().min()},name='Coverage').to_frame())
print('Completed:', completion['completed_utc'])
print('Case:', read('enermap/cases.csv').iloc[0].to_dict())
'''),md('''
## 1 · Put the stock on the map

Each point is a **dwelling-weighted zone centroid**, not an individual building or an
electrical connection. The distinction between inferred substation zones and assumed
LSOA zones is important: neither is a substitute for a DNO connectivity model.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,5))
for color,(method,g) in zip([PURPLE,TEAL],zones.groupby('network_assignment_method')):
    ax[0].scatter(g.lon,g.lat,s=15+g.dwellings/8,alpha=.75,color=color,label=method.replace('_',' '))
ax[0].set(xlabel='Longitude',ylabel='Latitude',title='Demand geography | 320 zones')
ax[0].set_aspect(1/np.cos(np.deg2rad(zones.lat.mean())))
ax[0].legend(fontsize=8,loc='upper left')
stock=clusters.groupby('network_assignment_method').dwelling_count.sum()
ax[1].bar(['LSOA assumption' if 'lsoa' in x else 'Nearest substation' for x in stock.index],stock.values,color=[PURPLE,TEAL])
ax[1].set(ylabel='Dwellings',title='How the electricity zones were assigned')
labelbars(ax[1]);ax[1].margins(y=.2)
finish(fig,'enermap_coverage')
'''),md('''
## 2 · Three fabric states, one population

R0 is the baseline; R1 and R2 are alternative fabric packages. These bars ask what the
modelled stock would demand under each package envelope. **They are not an optimised
rollout**: the optimiser must still respect eligibility, quantities, costs and shares.
The space-heat profiles are simulated; the savings are not a fixed percentage imposed
afterwards. Hot-water and non-heating electricity must remain separate.
'''),code('''
totals=annual.groupby('package_id')[['space_heat_kWh','hot_water_kWh','non_heating_elec_kWh']].sum()/1e6
fig,ax=plt.subplots(1,2,figsize=(12,4.6))
totals.rename(columns={'space_heat_kWh':'Useful space heat','hot_water_kWh':'Useful hot water','non_heating_elec_kWh':'Non-heating electricity'}).plot.bar(ax=ax[0],color=[TEAL,GOLD,BLUE],rot=0,width=.8)
ax[0].set(title='Annual demand | same stock, different fabric',ylabel='GWh/year',xlabel='')
ax[0].legend(fontsize=8)
savings=(1-totals.space_heat_kWh/totals.loc['R0','space_heat_kWh'])*100
ax[1].bar(savings.index,savings.values,color=[GREY,TEAL,PURPLE]);labelbars(ax[1],'{:.1f}','%')
ax[1].set(title='Space-heat reduction relative to R0',ylabel='Reduction (%)');ax[1].margins(y=.2)
finish(fig,'enermap_packages')
display(totals.rename_axis('Alternative package').round(2))
'''),md('''
## 3 · Timing is part of the handoff

The annual totals hide winter peaks and day-to-day variation. These profiles sum the
**actual exported cluster demand**, not a rescaled illustrative curve. The UTC label
is a fixed 8,760-hour model clock for local TMY weather; it should not be shifted for DST.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,4.5))
for color,(package,g) in zip([GREY,TEAL,PURPLE],hourly.groupby('package_id')):
    series=g.set_index('timestamp_utc').space_heat_kw/1000
    series.resample('D').mean().plot(ax=ax[0],label=package,color=color,lw=1.4)
    series.iloc[:168].plot(ax=ax[1],label=package,color=color,lw=1.5)
ax[0].set(title='Seasonal pattern | daily mean',ylabel='Useful space heat (MW)',xlabel='')
ax[1].set(title='First winter week | hourly',ylabel='Useful space heat (MW)',xlabel='')
for a in ax:a.legend();a.grid(axis='y')
finish(fig,'enermap_hourly')
'''),md('''
## 4 · Heat demand is not heat-pump electricity

Retrofitting changes the thermal demand. The chosen heating system then converts that
demand to fuel or electricity. EnerMap supplies hourly ASHP COPs for space heat and DHW;
the model should not divide every hour by a single assumed seasonal COP. The exported
non-heating electricity vector excludes heating electricity, avoiding double counting.
These curves omit defrost, backup and cycling corrections.
'''),code('''
cop=read('enermap/heat_pump_cop_hourly.csv',parse_dates=['timestamp_utc']).set_index('timestamp_utc')
fig,ax=plt.subplots(1,2,figsize=(12,4.3))
cop[['COP_space_heat','COP_dhw']].resample('D').mean().rename(columns={'COP_space_heat':'Space heat','COP_dhw':'Hot water'}).plot(ax=ax[0],color=[TEAL,GOLD])
ax[0].set(title='Daily mean conversion efficiency',ylabel='COP (heat / electricity)',xlabel='')
ax[1].scatter(cop.T_out_C,cop.COP_space_heat,s=4,alpha=.2,color=TEAL,label='Space heat')
ax[1].scatter(cop.T_out_C,cop.COP_dhw,s=4,alpha=.2,color=GOLD,label='Hot water')
ax[1].set(title='The weather–efficiency relationship',xlabel='Outdoor temperature (°C)',ylabel='Hourly COP');ax[1].legend()
finish(fig,'enermap_cop')
'''),md('''
## 5 · What has actually been checked?

The run records **16 physics tests, 120 accounting tests and a passed interface import**.
The current baseline uses 34 construction groups × three median size representatives;
306 stochastic cases feed the stock estimate, with 102 deterministic reference cases.
R1 and R2 each have 306 paired simulations. No annual meter calibration was applied.

The annual gas/electricity comparisons are useful diagnostics, but were inspected during
development: they are not an untouched holdout test. The modelled electricity peak is
not validated against hourly measurements. Three stochastic draws and roof-exposure
variation remain limitations.
'''),code('''
print('Completion record:')
display(pd.Series({k:completion[k] for k in ['calibration','representation_method','baseline_simulations','retrofit_simulations','interface_import_passed','physics_tests','accounting_tests']}).to_frame('Recorded value'))
baseline=js('enermap/baseline_summary.json')
display(pd.Series(baseline.get('metrics',{})).to_frame('Baseline diagnostic'))
# Sum of hourly-average kW over one-hour intervals gives kWh.
by_hour=hourly.groupby('package_id')[['space_heat_kw','hot_water_heat_kw','non_heating_electricity_kw']].sum()
by_year=annual.groupby('package_id')[['space_heat_kWh','hot_water_kWh','non_heating_elec_kWh']].sum()
relative_error=np.abs(by_hour.to_numpy()-by_year.to_numpy())/by_year.to_numpy()
assert relative_error.max()<1e-5
assert (hourly.groupby('package_id').size()==8760).all()
assert clusters.dwelling_count.sum()==57300
print(f'Packaged hourly/annual reconciliation: maximum relative error {relative_error.max():.2e}')
'''),md('''
## What this makes possible next

The optimiser can choose a share of each **fabric × heating-system** option in each
cluster. For a cluster, those shares must sum to one. Demand follows the selected
package profile; costs follow eligible physical quantities and heating capacity.
Electricity, fuel and heat remain distinct but coupled balances.

The next modelling milestone is to rerun PyPSA-LAEP on this release and then replay the
selected design hourly. The import check alone does not establish an optimised solution.
See [scope and units](../docs/scope.md) and the [source manifest](../docs/source_manifest.json).
''')])

save('02_residential_whole_system',[
md('''
# PyPSA-LAEP · buildings and the local energy system
### The most developed residential reference case · Westborough complete-zone study

What changes when retrofit, heating choices, flexibility and the electricity network
are considered together? This is the central question behind PyPSA-LAEP.

The reference case contains **2,974 dwellings across 33 electrical zones**, with a 2035
national-system boundary. It is selected here for its saved investment results,
spatial outputs and targeted hourly replay—not because it is a validated town-wide plan.
Results were generated on **6 September 2026**, using the earlier EnerMap handoff.
The latest EnerMap release is presented separately in Notebook 01.
'''),SETUP,code('''
s=summary('residential/westborough')
z=read('residential/westborough/zone_table.csv')
uptake=read('residential/westborough/uptake.csv')
cfg=js('residential/westborough/assumptions.json')['config']
display(pd.Series({'Dwellings':s.dwellings,'Electrical zones':len(z),
    'Annualised system cost (£m/year)':s.objective_mgbp,
    'Space-heat reduction (%)':s.space_heat_reduction_pct,
    'Operational emissions (ktCO2/year)':s.emissions_kt}).to_frame('Saved economic solution'))
'''),md('''
## 1 · The whole-system idea, within an explicit boundary

Fabric changes demand; heating changes the carrier used to meet it; hourly operation
changes network loading. Solving these decisions together captures trade-offs that
independent technology calculations miss. Here “whole system” means the **modelled
residential, electricity and heating boundary**—not all sectors of Guildford yet.

| Decision or boundary | Representation in the saved model |
|---|---|
| Retrofit and heating choice | Continuous cluster shares over eligible package–technology options |
| Electricity and heat balances | PyPSA buses, loads and conversion links |
| Heat pumps and boilers | Links with efficiencies/COPs and capacity tied to adopted stock |
| Flexibility | Fabric and cylinder storage representations |
| Network | Zone transfer limits, transformer losses, optional reinforcement |
| National context | PyPSA-GB/FES24 HT 2035 prices/carbon mapped from solved winter/summer weeks |

The boundary is one-way: this study does not iteratively change the national system.
There is no EV or completed non-residential demand here, and DH is disabled in this case.
'''),md('''
## 2 · What did the model choose?

Fabric measures are selected widely, but low heat demand does not automatically imply
universal electrification. Existing boilers have sunk capital in this setup; fuel,
electricity and carbon assumptions influence the balance. The chart reports dwelling
**equivalents**, not identified household installations.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,4.6))
fabric=pd.Series({'R0':s.dwellings-s.retrofit_R1_dwellings-s.retrofit_R2_dwellings,
                  'R1':s.retrofit_R1_dwellings,'R2':s.retrofit_R2_dwellings})
heat=pd.Series({'Heat pumps':s.heat_pump_dwellings,'Resistance':s.resistive_dwellings,'Fossil':s.fossil_dwellings})
ax[0].bar(fabric.index,fabric.values,color=[GREY,TEAL,PURPLE]);ax[0].set(title='Fabric choice',ylabel='Dwelling equivalents')
ax[1].bar(heat.index,heat.values,color=[BLUE,GOLD,GREY]);ax[1].set(title='Heating choice',ylabel='Dwelling equivalents')
for a in ax:labelbars(a);a.margins(y=.2)
finish(fig,'residential_choices')
print(f'Retrofit uptake: {(1-fabric.R0/s.dwellings)*100:.1f}% of dwellings.')
print(f'Space-heat reduction: {s.space_heat_reduction_pct:.1f}%; clean heat: {s.clean_heat_share_pct:.1f}% of useful heat (different denominator).')
'''),md('''
## 3 · The pattern is spatial

These are the saved zone-level results. Marker size reflects dwelling count; colour
shows the share adopting each measure. Zones cover complete inferred substation groups,
so the study extends beyond the named ward boundary. This map is not a DNO-verified
connection diagram or a household-level recommendation.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,5.4))
mapzones(ax[0],z,100*z.retrofit_dwellings/z.dwellings,'Where fabric measures are selected','Retrofit share (%)')
mapzones(ax[1],z,100*z.heat_pump_dwellings/z.dwellings,'Where heat pumps are selected','HP share (%)')
finish(fig,'residential_map')
'''),md('''
## 4 · Less heat is needed; the network still needs checking

The selected fabric mix reduces useful space heat from about 25.04 to 17.89 GWh/year.
That reduction is separate from heating efficiency. The right-hand panel shows peak
loading in the **typical-day investment model**, not a full-year duration curve.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,4.7))
post_sh=s.r0_space_heat_gwh*(1-s.space_heat_reduction_pct/100)
ax[0].bar(['R0 reference','Selected fabric'],[s.r0_space_heat_gwh,post_sh],color=[GREY,TEAL])
ax[0].set(title='Useful space heat',ylabel='GWh/year');labelbars(ax[0],'{:.2f}');ax[0].margins(y=.2)
load=z.utilisation.sort_values().to_numpy()*100
ax[1].bar(np.arange(1,len(load)+1),load,color=BLUE)
ax[1].axhline(100,color=GOLD,ls='--',label='Available rating')
ax[1].set(title='33 zone peaks | typical-day solution',xlabel='Zones ranked by peak utilisation',ylabel='Peak utilisation (%)');ax[1].legend()
finish(fig,'residential_heat_network')
'''),md('''
## 5 · An hourly replay, with a limited scope

The saved replay fixes investment decisions and re-optimises operation across a full
year for **three of the 33 zones**. It finds no material unmet heat or electricity
in that subset. The grid-import change is small, but this does not establish feasibility
for every zone. The 221 hours near rating are **summed zone-hours**, not unique hours
for the area. Fabric storage also remains a comfort proxy rather than a validated
indoor-temperature simulation.
'''),code('''
r=read('residential/westborough/replay_report.csv').set_index('metric')
rz=read('residential/westborough/replay_zone_table.csv')
fig,ax=plt.subplots(1,2,figsize=(12,4.4))
energy=r.loc[['grid_import_mwh','gas_mwh'],['aggregated','replay']]/1000
energy.index=['Grid electricity','Gas'];energy.rename(columns={'aggregated':'Typical days','replay':'Full-year replay'}).plot.bar(ax=ax[0],color=[GREY,TEAL],rot=0)
ax[0].set(title='Same three-zone subset',ylabel='GWh/year',xlabel='')
rp=rz.pivot(index='zone',columns='run',values='utilisation')*100
rp.index=['Zone '+str(i+1) for i in range(len(rp))]
rp.plot.bar(ax=ax[1],rot=0,color=[GREY,TEAL]);ax[1].set(title='Subset peak utilisation',ylabel='Available capacity used (%)',xlabel='')
finish(fig,'residential_replay')
print(f"Subset import difference: {100*(r.loc['grid_import_mwh','replay']/r.loc['grid_import_mwh','aggregated']-1):.2f}%")
display(r.loc[['zones','unmet_heat_mwh','unmet_elec_mwh','hours_above_95pct'],['replay','unit']])
'''),md('''
## 6 · What sits behind the costs?

The £3.41m/year objective is an **annualised system cost**, including configured carbon
valuation—not a household bill, grant budget or an upfront investment total. The saved
case adds £60/MWh to its national electricity-price boundary, assumes gas at £26.26/MWh,
and uses £317.60/tCO2 carbon value with an £85/t embedded electricity-carbon allowance.
It has no minimum clean-heat share or carbon cap.

The tables below expose the original model inputs. **They are not newly verified market
quotes.** Price years are mixed and normalisation is disabled; compare scenarios with
shared assumptions, and treat absolute costs as preliminary. Existing-boiler capital
is sunk. Emitters and retrofit quantities add costs beyond the basic technology curve.
'''),code('''
tech=pd.DataFrame(cfg['technologies']['heating_systems']).T
cols=['enabled','capex_fixed_gbp_per_dwelling','capex_gbp_per_kw','lifetime','price_year']
display(tech[cols].rename_axis('Heating option'))
display(pd.DataFrame(cfg['retrofit']['measure_costs']).T.rename_axis('Fabric measure'))
print('Discount rate:',cfg['costs']['discount_rate'],'| Price normalisation:',cfg['costs']['normalise_price_year'])
'''),md('''
## 7 · A useful counterexample: retrofit under a clean-heat requirement

A separate controlled pair requires 100% clean heat: one holds fabric at R0, the other
allows R1/R2. With retrofit, the saved model chooses substantially more resistance
heating and fewer heat pumps. **System cost falls while electricity use rises.**
This is a technology-choice effect, not evidence that fabric insulation increases
heat demand. This pair has not completed the same hourly replay check.
'''),code('''
fixed=summary('residential/clean100_fixed'); flexible=summary('residential/clean100_retrofit')
fig,ax=plt.subplots(1,3,figsize=(12,4))
for a,key,title,unit in zip(ax,['objective_mgbp','grid_import_gwh','heat_pump_dwellings'],['Annualised cost','Grid electricity','Heat-pump uptake'],['£m/year','GWh/year','Dwelling equivalents']):
    a.bar(['R0 only','Retrofit allowed'],[fixed[key],flexible[key]],color=[GREY,TEAL]);a.set(title=title,ylabel=unit);labelbars(a,'{:.2f}' if key!='heat_pump_dwellings' else '{:,.0f}');a.margins(y=.25);a.tick_params(axis='x',labelsize=9)
finish(fig,'residential_clean_heat_comparison')
'''),md('''
## 8 · Why the wider Guildford result is still screening

The larger saved study combines ten independently solved, ward-labelled groups:
28,662 dwellings and 271 zones. It is useful for seeing spatial differences, but the
combined import peaks at about **60.36 MW**, above the assumed 40 MW upstream headroom.
The next iteration must enforce that shared limit jointly; calling the existing
aggregation a feasible town-wide optimum would be misleading.
'''),code('''
town=read('residential/guildford/borough_import_hourly.csv',index_col=0,parse_dates=True)
wk=read('residential/guildford/ward_kpis.csv')
fig,ax=plt.subplots(1,2,figsize=(12,5))
wk.sort_values('sh_reduction_pct').plot.barh(x='ward',y='sh_reduction_pct',ax=ax[0],color=TEAL,legend=False)
ax[0].set(title='Fabric savings across independent groups',xlabel='Space-heat reduction (%)',ylabel='')
duration=np.sort(town.borough_import_mw)[::-1]
ax[1].plot(np.arange(8760),duration,color=BLUE);ax[1].axhline(40,color=GOLD,ls='--',label='Assumed 40 MW headroom')
ax[1].fill_between(np.arange(8760),40,duration,where=duration>40,color=GOLD,alpha=.25)
ax[1].set(title='Combined hourly imports | screening',xlabel='Ranked modelled hours',ylabel='MW');ax[1].legend(fontsize=8)
finish(fig,'guildford_screening')
print(f'Combined peak: {duration.max():.2f} MW; modelled hours above 40 MW: {(duration>40).sum()}')
assert abs(s.dwellings-2974)<1e-5 and len(z)==33
assert np.isclose(uptake.dwellings.sum(),s.dwellings,atol=.02)
'''),md('''
## Where this leaves the framework

The completed work demonstrates integrated residential investment and operation,
with spatial and hourly checks. The next milestones are the latest EnerMap rerun,
whole-case replay, a joint upstream constraint, cost-year harmonisation and uncertainty
tests. EVs, non-residential anchors and multi-period pathways belong to subsequent
results—not the completed claims in this notebook.

See [scope and units](../docs/scope.md) and [source provenance](../docs/source_manifest.json).
''')])

save('03_guildford_district_heating',[
md('''
# Guildford · where district heating fits
### Spatial opportunity, individual alternatives and whole-system trade-offs

A promising heat-density map is only a starting point. A heat network also needs
enough connections, a viable plant, an electrical connection and a fair accounting
of its pipes. This notebook follows the most developed saved DH experiment: **candidate
zone 4 in Stoughton**, evaluated within **15 complete electricity zones / 2,534 dwellings**.

Three saved cases compare individual heating, DH with a central heat pump, and the
additional option of gas CHP. Results date from **6–7 September 2026** and use the earlier
EnerMap release. This is a snapshot investment study, not a deployment pathway or
construction-ready design. The full-year DH replay has a small residual electricity
shortfall; that caveat is part of the result.
'''),SETUP,code('''
cases=pd.DataFrame({c:summary('dh/'+c) for c in ['A','B','C']}).T
z=read('dh/C/zone_table.csv'); uptake=read('dh/C/uptake.csv')
curve=read('dh/zone_4_curve.csv'); candidate=read('dh/candidate.csv')
members=read('dh/zone_members_check.csv').set_index('zone')
display(cases[['dwellings','objective_mgbp','emissions_kt','dh_dwellings','dh_plant_hp_capacity_mw_th']].rename_axis('Case'))
'''),md('''
## 1 · Start with the streets, but do not confuse screening with design

The left panel shows the earlier Guildford street-network screening. “Selected” means
selected by that screening calculation—not installed infrastructure or the final
zone-4 layout. Geometry is in British National Grid (EPSG:27700).
The right panel shows the actual **zone-level DH uptake in case C**, as a share of all
dwellings in each electrical zone. The two panels have different scales and purposes.
'''),code('''
from matplotlib.collections import LineCollection
routes=read('dh/screening_routes.csv')
def line_coords(wkt):
    body=wkt[wkt.index('(')+1:wkt.rindex(')')]
    return np.array([[float(v) for v in pair.strip().split()[:2]] for pair in body.split(',')])/1000
fig,ax=plt.subplots(1,2,figsize=(12,6))
for flag,col,width in [(False,'#dce4e7',.65),(True,TEAL,1.3)]:
    paths=[line_coords(w) for w in routes.loc[routes.built.eq(flag),'wkt']]
    ax[0].add_collection(LineCollection(paths,colors=col,linewidths=width,label='Selected in screening' if flag else 'Other screened streets'))
ax[0].autoscale();ax[0].set_aspect('equal');ax[0].set(title='Guildford street-network opportunity',xlabel='BNG easting (km)',ylabel='BNG northing (km)');ax[0].legend(fontsize=8)
dh=uptake.loc[uptake.system.eq('dh_connection')].groupby('zone').dwellings.sum()
share=z.zone.map(dh).fillna(0)/z.dwellings*100
mapzones(ax[1],z,share,'Zone 4 study | case C uptake','DH share of zone dwellings (%)')
finish(fig,'dh_geography')
'''),md('''
## 2 · Three different populations explain the candidate

The pipe cost curve was derived on an earlier screening basis of **1,420 dwellings**.
After the building-to-route distance and EnerMap matching rules, **1,051 dwellings**
are eligible to connect. The optimisation includes **2,534 dwellings** because it
retains their complete electrical zones and individual heating alternatives.
About **831 dwelling equivalents** connect in the selected solution. These numbers
are different boundaries—not interchangeable measures of connection rate.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,4.5))
labels=['Pipe-curve basis','Eligible members','Whole electric zones','Selected connections']
vals=[members.loc[4,'curve_dwellings'],members.loc[4,'dwellings'],cases.loc['C','dwellings'],cases.loc['C','dh_dwellings']]
ax[0].barh(labels,vals,color=[GREY,PURPLE,BLUE,TEAL]);ax[0].invert_yaxis();ax[0].set(title='Know the denominator',xlabel='Dwellings / dwelling equivalents');labelbars(ax[0]);ax[0].margins(x=.25)
ax[1].plot(curve.share*100,curve.capex_pipes_eur_per_yr*.86/1000,'o-',color=TEAL)
ax[1].set(title='Candidate pipe-cost curve',xlabel='Screening layout share (%)',ylabel='Annualised pipe cost (£000/year)')
ax[1].scatter([100],[candidate.committed_pipe_cost_gbp_per_yr.iloc[0]/1000],s=130,facecolors='none',edgecolors=GOLD,linewidth=2,label='Committed layout in B/C');ax[1].legend(fontsize=8)
finish(fig,'dh_membership_cost_curve')
display(candidate.T.rename(columns={0:'Saved candidate input'}))
'''),md('''
## 3 · How the spatial work enters PyPSA

Topotherm-derived pipe cost/capacity information enters as a **fixed candidate layout**,
with a committed annual pipe cost. PyPSA then chooses connections and plant capacity
alongside individual heating. It is not jointly rerouting the streets in this solve.

| Component | Coupling in the saved DH model |
|---|---|
| Energy-centre electricity | Dedicated site bus, 5 MW import-only GSP connection |
| Central HP | Electricity-to-heat Link with hourly COP |
| Gas CHP option | Multi-output Link: gas input → electricity + heat |
| Heat distribution | Supply/delivery buses and a lossy, capacity-limited connection |
| Building connections | Eligible cluster options with connection/HIU cost |
| Individual alternatives | Available alongside DH, sharing the local electrical constraints |

The candidate has 4.31 km of trench and an 8.05 MW curve-based heat capacity.
Losses are a fixed topotherm-derived share with a ×2 derating assumption, not a full
hourly hydraulic calculation. There is no central thermal storage or electricity
export in these saved cases; CHP electricity can serve the energy centre only.
'''),md('''
## 4 · Count the pipes before comparing costs

**A:** individual heating only. **B:** add DH with a central heat pump.
**C:** also allow gas CHP. All share a 2.199 ktCO2 cap; their achieved emissions differ.

The plant/operation subtotal makes DH look cheaper, but the **committed pipe cost must
be added back**. With that included, B costs about £53,000/year more than A (+1.77%)
while emissions are about 9.17% lower. This is a cost–carbon trade-off under the saved
assumptions, not a claim that DH is universally cheaper. Mixed cost years remain a caveat.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,4.8))
x=np.arange(3)
ax[0].bar(x,cases.objective_excl_committed_dh_mgbp,color=BLUE,label='Rest of annualised system cost')
ax[0].bar(x,cases.committed_dh_pipe_cost_mgbp,bottom=cases.objective_excl_committed_dh_mgbp,color=GOLD,label='Committed pipes')
ax[0].set(xticks=x,xticklabels=['A · Individual','B · DH + HP','C · DH + HP/CHP'],ylabel='£m/year',title='Comparable cost boundary');ax[0].tick_params(axis='x',labelsize=9)
for i,v in enumerate(cases.objective_mgbp):ax[0].text(i,v+.04,f'{v:.3f}',ha='center')
ax[0].set_ylim(0,3.75);ax[0].legend(loc='upper left',fontsize=8)
ax[1].bar(cases.index,cases.emissions_kt,color=[GREY,TEAL,PURPLE]);ax[1].axhline(2.199,color=GOLD,ls='--',label='Shared carbon cap')
ax[1].set(title='Operational emissions',ylabel='ktCO2/year');labelbars(ax[1],'{:.3f}');ax[1].set_ylim(0,2.75);ax[1].legend(fontsize=8)
finish(fig,'dh_cost_carbon')
print(f"B − A annualised cost: £{(cases.loc['B','objective_mgbp']-cases.loc['A','objective_mgbp'])*1e6:,.0f}/year")
'''),md('''
## 5 · What gets built in the model?

B and C select nearly identical DH outcomes: approximately **4.96 MWth of central HP**
and **831 connections**. Allowing CHP does not mean the optimiser selects it: the saved
CHP capacity and output are numerically zero. This finding is conditional on gas/carbon
prices, HP performance and the import-only connection restriction.
The clean-heat-share field in the source excludes DH by its option flag, so it is not
used here as an A/B/C heat-decarbonisation score.
'''),code('''
fig,ax=plt.subplots(1,2,figsize=(12,4.5))
keys=['fossil_dwellings','heat_pump_dwellings','resistive_dwellings','dh_dwellings']
mix=cases[keys].rename(columns=dict(zip(keys,['Individual fossil','Individual HP','Resistance','District heat'])))
mix.plot.bar(stacked=True,ax=ax[0],color=[GREY,BLUE,GOLD,TEAL],rot=0)
ax[0].set(title='Heating choice across the same population',ylabel='Dwelling equivalents',xlabel='');ax[0].legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2)
cases[['dh_heat_from_hp_gwh','dh_heat_from_chp_gwh']].clip(lower=0).rename(columns={'dh_heat_from_hp_gwh':'Central HP','dh_heat_from_chp_gwh':'Gas CHP'}).plot.bar(ax=ax[1],color=[TEAL,PURPLE],rot=0)
ax[1].set(title='Annual central heat production',ylabel='GWh heat/year',xlabel='')
finish(fig,'dh_heating_mix')
'''),md('''
## 6 · Replay the operation across the year

Case C was replayed jointly for all 15 zones. These curves sum the saved option-level
heat-delivery schedules at the dwelling-side heating options; they are not fuel input
or electricity demand. Central HP production is higher than delivered DH because of
the modelled network loss.
'''),code('''
h=read('dh/C/hourly_heat.csv',index_col=0,parse_dates=True)
names={'dh_connection_heat_delivered_mw':'District heat','ashp_heat_delivered_mw':'Individual ASHP','resistive_heat_delivered_mw':'Resistance','gas_boiler_existing_heat_delivered_mw':'Existing gas'}
fig,ax=plt.subplots(1,2,figsize=(12,4.7))
h.rename(columns=names).resample('D').mean().plot(ax=ax[0],color=[TEAL,BLUE,GOLD,GREY],lw=1.2)
ax[0].set(title='Daily mean heat delivered | case C replay',ylabel='MW heat',xlabel='');ax[0].legend(fontsize=8)
h.iloc[:168].rename(columns=names).plot.area(ax=ax[1],stacked=True,color=[TEAL,BLUE,GOLD,GREY],alpha=.85,legend=False)
ax[1].set(title='First winter week | hourly heat delivery',ylabel='MW heat',xlabel='')
finish(fig,'dh_hourly_operation')
'''),md('''
## 7 · The unresolved check belongs on the page

The replay reports **zero unmet heat**, but **73.2 kWh of unmet electricity** over the
year. That exceeds the model's 1 kWh feasibility tolerance. It is small in annual
energy terms, but the strict feasibility check has **not passed**. The next model
iteration should identify the affected hours and bus, repair the constraint/dispatch
issue and rerun the replay before this is presented as a feasible design.

There is also a reporting boundary mismatch: the aggregated grid subtotal in the replay
report omits central DH electricity, whereas its replay total includes it. The apparent
32% difference must not be presented as a temporal-aggregation error. The original
table is retained for audit, not silently repaired.
'''),code('''
r=read('dh/C/replay_report.csv').set_index('metric')
display(r.loc[['zones','unmet_heat_mwh','unmet_elec_mwh','dh_heat_from_hp_mwh','dh_delivered_mwh','dh_pipe_peak_utilisation'],['replay','unit']])
shortfall_kwh=r.loc['unmet_elec_mwh','replay']*1000
print(f'UNRESOLVED: {shortfall_kwh:.1f} kWh unmet electricity; permitted tolerance = 1.0 kWh.')
print('Full-year heat coverage does not cancel an electrical feasibility failure.')
assert len(z)==15 and cases.loc['C','dwellings']==2534
assert np.allclose(cases.objective_mgbp,cases.objective_excl_committed_dh_mgbp+cases.committed_dh_pipe_cost_mgbp,atol=1e-8)
assert np.isclose(uptake.dwellings.sum(),2534,atol=.02)
'''),md('''
## The next useful experiments

First resolve the hourly electricity shortfall and align grid accounting. Then test
connection uptake, retrofit/DH interaction, central storage, alternative site connections,
cost-year harmonisation and the latest EnerMap demand. Non-residential anchor loads
could materially alter viability, but they are not completed results in this release.

Central HP costs (£700/kWth), connection/HIU (£4,500/dwelling), CHP assumptions and the
EUR→GBP factor (0.86) are **saved model inputs**, not procurement estimates. Full resolved
case assumptions are included beside the tables. No new cost verification or model run
was performed when preparing this showcase.

See [scope and units](../docs/scope.md) and [source provenance](../docs/source_manifest.json).
''')])
print('Built three notebooks.')
