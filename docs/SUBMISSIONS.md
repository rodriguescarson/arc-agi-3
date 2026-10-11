# Submission log

One submission per day. Public score = 55 hidden games; final ranking uses the other 55.

| date (UTC) | variant | kernel version | commit (git) | public score | notes |
|---|---|---|---|---|---|
| 2026-10-12 | v1-franzen-faithful | not yet committed | 110b447 | - | GPU quota exhausted (37/30 h); first GPU commit possible 2026-10-17 00:00 UTC |
| 2026-10-12 | v1-cpucheck (CPU, not a submission) | arc3-duck-v1-cpucheck v1-v2 | 110b447 | n/a | v1 failed: JSON `false` rendered into Python (fixed, test added); v2 running |

Reference distribution for the v1 configuration (Franzen copies, Son Pham, Oct 2):
mean 25.77, SD 3.93, median 26.19.

CPU baselines on the 25 public games (`arc3.local_eval`, 250 actions/game cap, competition cap 1.0):
explorer 0/183 levels (0.00), random 0/183 levels (0.00). Model-free search does not clear a single
level 1; everything rides on the LLM harness.
