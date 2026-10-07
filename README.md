# PyPSA LAEP results

Explore Guildford's local energy planning results in three notebooks:

1. [2025 baseline](01-2025-baseline.ipynb)
2. [2035 without district heating](02-2035-without-DH.ipynb)
3. [2035 with district heating](03-2035-with-DH.ipynb)

Charts cover demand and supply, dispatch, heating, retrofit, storage, costs, emissions and network capacity. Maps use OpenStreetMap. Change `AREA` and `DAY` in the first cell to explore.

```bash
pip install -r requirements.txt
jupyter lab
```

Run from this repository's root. Saved chart outputs are viewable on GitHub; run the notebooks for interactive maps. No optimiser or original model checkout is required.

## Results basis

Five primary areas, 28,876 homes. The compact `data/` exports come from the saved study results on 7 October 2026; they include derived substation aggregates, not raw building records. The optimisation used 12 representative days per area. Reconstructed annual profiles repeat those days and are not a chronological replay. Dispatch units are MW; storage MWh; annual flows GWh.

Costs retain mixed monetary bases. Existing assets are treated as paid for in 2025; 2035 costs include annualised investment. The year-to-year gap includes changed prices and grid emissions. DH routes and sites are candidate screening geometry, not final pipe selections. See [data provenance](data/provenance.json).

Basemaps © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL. The source tile mosaic is bundled for offline chart previews; interactive maps request OSM tiles.

The previous code remains recoverable in Git history. This repository now presents results only.
