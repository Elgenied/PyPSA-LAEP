# What this showcase does — and does not — establish

This is a results companion to the research model, not a replacement model distribution.
It reproduces figures from saved outputs without a solver. No new optimisation has been
performed for this release. Notebook execution is not model validation.

## Two releases, deliberately kept separate

The current EnerMap handoff completed on **23 September 2026**. Its case is
`GF2021_TMY_UNCAL_MEDIAN3_HOURLY_COP`: uncalibrated, median construction archetypes,
three size classes and three stochastic draws per size. Baseline: 408 simulations,
including 306 stochastic cases and 102 deterministic references. Each retrofit package
has 306 simulations. The references are not added to the stock prediction.

The saved PyPSA-LAEP optimisations were generated on **6–7 September 2026** and used
`GF2021_TMYx_CHAP_cal08`, an earlier demand handoff. Do not subtract the new EnerMap
baseline from these older optimisation totals. A rerun is needed to link the releases.

## Boundaries that matter

* EnerMap covers 57,300 dwellings across 84 LSOAs. Its 2,386 clusters use 320 electricity
  zones. Spatial nearest-substation assignment and assumed LSOA zones are not verified
  distribution-network connectivity.
* Westborough is a 2,974-dwelling, 33-zone **complete-zone** case, not an exact ward polygon.
  Twelve typical days give 288 optimisation snapshots, weighted to 8,760 hours.
  Full-year operational replay covers only three zones; no whole-case feasibility claim.
* Guildford's 28,662-dwelling town result combines ten independently solved groups.
  Their summed imports exceed the assumed 40 MW upstream limit. It is a screening
  result, not a jointly feasible town-wide optimum.
* The DH experiment covers 2,534 dwellings in 15 complete electrical zones. Zone 4
  has 1,051 eligible dwelling equivalents; the earlier pipe-curve basis has 1,420.
  The difference reflects membership and matching rules, not an increase in population.
* A/B/C share a 2.199 ktCO2 carbon cap, not equal achieved emissions. Include the
  committed pipe cost when comparing costs. The DH clean-share field excludes DH
  connections by flag; it is not a consistent indicator for the whole heat mix.
* The C replay covers all 15 zones but contains **0.0732095 MWh of unmet electricity**,
  above the model's 0.001 MWh tolerance. It is not a passed feasibility test.
  The report's aggregated grid-import subtotal omits central DH electricity; do not
  interpret its aggregate/replay ratio as temporal-aggregation error.
* Costs are saved modelling assumptions, with mixed price years and normalisation
  disabled. Objectives are annualised system costs including the configured carbon
  valuation, not household bills or current installed-price quotes.
* Adoption is continuous at cluster level. Fractional dwelling equivalents are not
  installation commitments or identified household decisions.
* Fabric flexibility assumes a 3 K window, full participation and no separate control
  cost. This proxy has not established building-level thermal comfort.
* EVs and non-residential demand are **not completed results** in this release.
  A future pathway model, endogenously changing DH routes, central thermal storage,
  detailed hydraulics and iterative national/local coupling are not claimed here.

## Units and accounting

Useful space heat and tap-level hot water are distinct from delivered fuel and electricity.
The new interface contains hourly average kW; divide by 1,000 for MW. At one-hour
resolution, sum kW to obtain kWh. R0/R1/R2 are alternatives for the same stock, not
three populations to sum. Reductions here apply to space heat, not automatically DHW.
COP is dimensionless and time-dependent; it is not a heat-reduction percentage.

## Provenance and data handling

`source_manifest.json` records source-relative names, SHA-256 hashes and transformations.
Absolute workstation paths have been removed. No raw dwelling IDs, address lists,
building geometries, solver binaries or large solved networks are distributed here.
Zone-centroid and street-screening maps are sufficient for this presentation; they
are not approved engineering designs. Keep the repository private until source-data
licensing and publication permissions have been reviewed. No blanket open licence is
assigned to research outputs or third-party-derived data.
