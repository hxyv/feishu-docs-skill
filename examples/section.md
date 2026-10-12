GROMACS throughput was measured at 8, 12, 16 and 20 OpenMP threads on one node. Going from 8
to 12 threads gains about 4 %, and each further step adds less than 1.5 %.

![Figure 1. GROMACS throughput versus thread count](@./figures/throughput.png)

| Threads | ns/day | vs 8 threads |
|---|---|---|
| 8 | 256.9 | 100 % |
| 12 | 267.8 | 104 % |
| 16 | 271.0 | 105 % |
| 20 | 272.5 | 106 % |
