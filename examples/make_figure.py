"""Make a figure the way the skill expects: PNG, Agg backend, dpi 150, labelled axes.

    python3 examples/make_figure.py            # writes ./figures/throughput.png
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

threads = [8, 12, 16, 20]
ns_per_day = [256.9, 267.8, 271.0, 272.5]

pathlib.Path("figures").mkdir(exist_ok=True)
fig, ax = plt.subplots(figsize=(6, 3.4), dpi=150)
ax.plot(threads, ns_per_day, marker="o")
ax.set_xlabel("OpenMP threads")
ax.set_ylabel("Throughput (ns/day)")
ax.set_xticks(threads)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("figures/throughput.png")
print("figures/throughput.png")
