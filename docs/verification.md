# Release verification · 27 September 2026

* All three notebooks executed from fresh kernels, with saved outputs and no cell errors.
* Execution repeated successfully from a separate copied directory, using only packaged data.
* Nine automated tests pass: release/population, hourly/annual reconciliation, adoption,
  committed pipe cost, explicit replay failure, town-wide headroom, executed outputs,
  absence of raw dwelling identifiers/workstation paths, and source-manifest coverage.
* Fifteen figures inspected visually; crowded map tick labels and inconsistent map colours corrected.
* HTML reports and a local reader index exported; images are embedded in the notebook reports.
* 53 source records hashed and checked against the source files after packaging.

These checks validate the **showcase packaging and internal accounting**, not the
underlying model's scientific validity or engineering feasibility. Known incomplete
model checks remain explicit in the notebooks and scope document.
