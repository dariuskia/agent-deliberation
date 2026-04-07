"""Sweep: centralized vs clustered vs delegates across population sizes and questions.

Generates comparison graphs, a markdown report, and logs everything to W&B.
"""

import asyncio
import json
import os
import random
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import wandb
import yaml
from dotenv import load_dotenv

from deliberation.llm import LLMClient
from deliberation.modes import run_centralized, run_clustered, run_delegates
from deliberation.models import Principal
from questions import QUESTION_BANK, short_label

BASE_DIR = Path(__file__).resolve().parent
RUNS_DIR = BASE_DIR / "runs"

load_dotenv(BASE_DIR / ".env")

# ── Sweep grid ──────────────────────────────────────────────
MODES = ["centralized", "clustered", "delegates"]
POPULATION_SIZES = [4, 10, 50]
QUESTIONS = QUESTION_BANK[:1]
NUM_TRIALS = 1
NUM_ROUNDS = 3
N_CLUSTERS = 3
SEED = 42

MODE_COLORS = {"centralized": "#e74c3c", "clustered": "#3498db", "delegates": "#2ecc71"}
MODE_MARKERS = {"centralized": "s", "clustered": "D", "delegates": "o"}

MODE_RUNNERS = {
    "centralized": lambda llm, principals, question: run_centralized(
        llm, principals, question, num_rounds=NUM_ROUNDS,
    ),
    "clustered": lambda llm, principals, question: run_clustered(
        llm, principals, question, n_clusters=min(N_CLUSTERS, len(principals)),
        num_rounds=NUM_ROUNDS,
    ),
    "delegates": lambda llm, principals, question: run_delegates(
        llm, principals, question, num_rounds=NUM_ROUNDS,
    ),
}


def compute_metrics(satisfaction_scores: dict[str, dict]) -> dict:
    scores = sorted(v["score"] for v in satisfaction_scores.values())
    n = len(scores)
    avg = sum(scores) / n
    min_sat = scores[0]
    max_sat = scores[-1]
    variance = sum((s - avg) ** 2 for s in scores) / n

    # Bottom quartile (minority satisfaction)
    q1_count = max(1, n // 4)
    bottom_quartile = sum(scores[:q1_count]) / q1_count

    return {
        "avg_satisfaction": avg,
        "min_satisfaction": min_sat,
        "max_satisfaction": max_sat,
        "bottom_quartile_satisfaction": bottom_quartile,
        "satisfaction_variance": variance,
    }


async def run_cell(
    all_principals: list[Principal],
    llm: LLMClient,
    mode: str,
    n: int,
    question: str,
    trial: int,
) -> dict:
    rng = random.Random(SEED + trial)
    principals = rng.sample(all_principals, min(n, len(all_principals)))

    runner = MODE_RUNNERS[mode]
    result = await runner(llm, principals, question)

    metrics = compute_metrics(result.satisfaction_scores)

    # Per-principal scores for detailed graphs
    per_principal = {}
    for p in principals:
        score_data = result.satisfaction_scores.get(p.id, {})
        per_principal[p.id] = {
            "name": p.name,
            "score": score_data.get("score", 0),
            "reasoning": score_data.get("reasoning", ""),
        }

    # Serialize full deliberation transcript
    rounds_serialized = [
        [{"round_num": m.round_num, "delegate_id": m.delegate_id, "content": m.content}
         for m in round_msgs]
        for round_msgs in result.rounds
    ]
    candidates_serialized = [
        {"id": c.id, "delegate_id": c.delegate_id, "text": c.text}
        for c in result.candidate_statements
    ]
    ballots_serialized = [
        {"delegate_id": b.delegate_id, "ranking": b.ranking}
        for b in result.ballots
    ]
    principals_serialized = [
        {"id": p.id, "name": p.name, "profile": p.profile, "values": p.values, "hidden_values": p.hidden_values}
        for p in principals
    ]

    return {
        "mode": mode,
        "n": n,
        "question": question,
        "trial": trial,
        **metrics,
        "per_principal": per_principal,
        "winner_text": result.winner.text,
        "principal_ids": [p.id for p in principals],
        "principals": principals_serialized,
        "rounds": rounds_serialized,
        "candidate_statements": candidates_serialized,
        "ballots": ballots_serialized,
    }


# ── Graph generation ────────────────────────────────────────

def generate_graphs(results: list[dict], output_dir: Path) -> list[Path]:
    """Generate and save comparison graphs. Returns list of saved file paths."""
    output_dir.mkdir(exist_ok=True, parents=True)
    paths = []

    valid = [r for r in results if "error" not in r]
    if not valid:
        return paths

    # ── 1. Aggregate bar chart: metrics by mode (averaged across all questions & sizes) ──
    metric_labels = {
        "avg_satisfaction": "Average",
        "min_satisfaction": "Minimum\n(Worst-Case)",
        "bottom_quartile_satisfaction": "Bottom Quartile\n(Minority)",
    }
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(metric_labels))
    width = 0.25

    for i, mode in enumerate(MODES):
        mode_results = [r for r in valid if r["mode"] == mode]
        if not mode_results:
            continue
        vals = []
        for key in metric_labels:
            trial_vals = [r[key] for r in mode_results]
            vals.append(sum(trial_vals) / len(trial_vals))

        bars = ax.bar(x + i * width, vals, width, label=mode,
                      color=MODE_COLORS[mode], edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_ylabel("Satisfaction (1-10)", fontsize=12)
    ax.set_title("Satisfaction Metrics by Mode (all questions & sizes)", fontsize=14)
    ax.set_xticks(x + width)
    ax.set_xticklabels(metric_labels.values(), fontsize=10)
    ax.legend(fontsize=11)
    ax.set_ylim(0, 11)
    ax.grid(True, alpha=0.2, axis="y")
    fig.tight_layout()

    path = output_dir / "metrics_comparison.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    paths.append(path)

    # ── 2. Scaling curves: satisfaction vs N per mode ──────────
    sizes = sorted(set(r["n"] for r in valid))
    if len(sizes) > 1:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        metric_keys = ["avg_satisfaction", "min_satisfaction", "bottom_quartile_satisfaction"]
        metric_titles = ["Average Satisfaction", "Minimum Satisfaction", "Bottom Quartile Satisfaction"]

        for ax, key, title in zip(axes, metric_keys, metric_titles):
            for mode in MODES:
                means = []
                stds = []
                for n in sizes:
                    vals = [r[key] for r in valid if r["mode"] == mode and r["n"] == n]
                    if vals:
                        means.append(sum(vals) / len(vals))
                        if len(vals) > 1:
                            m = means[-1]
                            stds.append((sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5)
                        else:
                            stds.append(0)
                    else:
                        means.append(None)
                        stds.append(0)

                valid_idx = [i for i, m in enumerate(means) if m is not None]
                x_vals = [sizes[i] for i in valid_idx]
                y_vals = [means[i] for i in valid_idx]
                y_std = [stds[i] for i in valid_idx]

                ax.plot(x_vals, y_vals, marker=MODE_MARKERS[mode], color=MODE_COLORS[mode],
                        label=mode, linewidth=2, markersize=8)
                if any(s > 0 for s in y_std):
                    y_lo = [y - s for y, s in zip(y_vals, y_std)]
                    y_hi = [y + s for y, s in zip(y_vals, y_std)]
                    ax.fill_between(x_vals, y_lo, y_hi, color=MODE_COLORS[mode], alpha=0.15)

            ax.set_xlabel("Population Size (N)", fontsize=12)
            ax.set_ylabel("Score (1-10)", fontsize=12)
            ax.set_title(title, fontsize=13)
            ax.set_ylim(0, 11)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.2)

        fig.tight_layout()
        path = output_dir / "scaling_curves.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)

    # ── 3. Score distribution (box/strip plot) ────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    positions = []
    data_for_box = []
    colors_for_box = []

    for i, mode in enumerate(MODES):
        mode_results = [r for r in valid if r["mode"] == mode]
        all_scores = []
        for r in mode_results:
            all_scores.extend(d["score"] for d in r["per_principal"].values())
        if all_scores:
            data_for_box.append(all_scores)
            positions.append(i)
            colors_for_box.append(MODE_COLORS[mode])

    if data_for_box:
        bp = ax.boxplot(data_for_box, positions=positions, widths=0.5, patch_artist=True,
                        showmeans=True, meanprops=dict(marker="D", markerfacecolor="white", markersize=6))
        for patch, color in zip(bp["boxes"], colors_for_box):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        # Overlay individual points
        for pos, scores, color in zip(positions, data_for_box, colors_for_box):
            jitter = np.random.default_rng(42).uniform(-0.15, 0.15, len(scores))
            ax.scatter([pos + j for j in jitter], scores, color=color,
                       edgecolor="black", linewidth=0.5, s=30, zorder=5, alpha=0.6)

    ax.set_xticks(positions)
    ax.set_xticklabels(MODES, fontsize=12)
    ax.set_ylabel("Satisfaction Score (1-10)", fontsize=12)
    ax.set_title("Satisfaction Distribution by Mode (all cells)", fontsize=14)
    ax.set_ylim(0, 11)
    ax.grid(True, alpha=0.2, axis="y")
    fig.tight_layout()

    path = output_dir / "satisfaction_distribution.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    paths.append(path)

    # ── 4. Inequality scaling: variance vs N per mode ─────────
    if len(sizes) > 1:
        fig, ax = plt.subplots(figsize=(8, 5))
        for mode in MODES:
            means = []
            for n in sizes:
                vals = [r["satisfaction_variance"] for r in valid if r["mode"] == mode and r["n"] == n]
                means.append(sum(vals) / len(vals) if vals else None)

            valid_idx = [i for i, m in enumerate(means) if m is not None]
            x_vals = [sizes[i] for i in valid_idx]
            y_vals = [means[i] for i in valid_idx]

            ax.plot(x_vals, y_vals, marker=MODE_MARKERS[mode], color=MODE_COLORS[mode],
                    label=mode, linewidth=2, markersize=8)

        ax.set_xlabel("Population Size (N)", fontsize=12)
        ax.set_ylabel("Satisfaction Variance", fontsize=12)
        ax.set_title("Inequality Scaling (lower = more equitable)", fontsize=14)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.2)
        fig.tight_layout()

        path = output_dir / "inequality_scaling.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)

    # ── 5. Per-question comparison ────────────────────────────
    questions = sorted(set(r["question"] for r in valid))
    if len(questions) > 1:
        fig, axes = plt.subplots(1, len(questions), figsize=(6 * len(questions), 5), sharey=True)
        if len(questions) == 1:
            axes = [axes]

        for ax, q in zip(axes, questions):
            q_results = [r for r in valid if r["question"] == q]
            for i, mode in enumerate(MODES):
                mode_q = [r for r in q_results if r["mode"] == mode]
                if not mode_q:
                    continue
                avg = sum(r["avg_satisfaction"] for r in mode_q) / len(mode_q)
                bot_q = sum(r["bottom_quartile_satisfaction"] for r in mode_q) / len(mode_q)

                x_pos = np.array([0, 1]) + i * 0.25
                ax.bar(x_pos, [avg, bot_q], 0.22, label=mode if ax == axes[0] else "",
                       color=MODE_COLORS[mode], edgecolor="white", linewidth=0.5)

            ax.set_xticks([0.25, 1.25])
            ax.set_xticklabels(["Avg Sat", "Bot. Quartile"], fontsize=10)
            ax.set_title(short_label(q, 50), fontsize=10)
            ax.set_ylim(0, 11)
            ax.grid(True, alpha=0.2, axis="y")

        axes[0].set_ylabel("Satisfaction (1-10)", fontsize=12)
        axes[0].legend(fontsize=10)
        fig.suptitle("Per-Question Comparison", fontsize=14)
        fig.tight_layout()

        path = output_dir / "per_question_comparison.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)

    return paths


# ── Report generation ──────────────────────────────────────

def generate_report(results: list[dict], graphs_dir: Path, timestamp: str):
    """Generate or append to report.md."""
    valid = [r for r in results if "error" not in r]
    if not valid:
        return

    report_path = BASE_DIR / "report.md"
    rel_graphs = graphs_dir.relative_to(BASE_DIR)

    lines = []

    # If file doesn't exist, add header
    if not report_path.exists():
        lines.append("# Deliberation Mode Comparison — Experiment Report\n")
        lines.append("Comparing centralized, clustered, and delegates deliberation modes ")
        lines.append("across population sizes and questions.\n\n")
        lines.append("---\n\n")

    # Experiment section
    questions_used = sorted(set(r["question"] for r in valid))
    sizes_used = sorted(set(r["n"] for r in valid))
    modes_used = sorted(set(r["mode"] for r in valid))

    lines.append(f"## Experiment: {timestamp}\n\n")
    lines.append(f"**Grid:** {len(modes_used)} modes × {len(sizes_used)} sizes × {len(questions_used)} questions × {NUM_TRIALS} trial(s)\n\n")
    lines.append(f"- **Modes:** {', '.join(modes_used)}\n")
    lines.append(f"- **Population sizes:** {', '.join(str(s) for s in sizes_used)}\n")
    lines.append(f"- **Questions:**\n")
    for q in questions_used:
        lines.append(f"  - {q}\n")
    lines.append(f"- **Rounds per deliberation:** {NUM_ROUNDS}\n\n")

    # Summary table
    lines.append("### Results Summary\n\n")
    lines.append("| Mode | N | Question | Avg Sat | Min Sat | Bot. Quartile | Variance |\n")
    lines.append("|------|---|----------|---------|---------|---------------|----------|\n")
    for r in sorted(valid, key=lambda x: (x["mode"], x["n"], x["question"])):
        q_short = short_label(r["question"], 35)
        lines.append(
            f"| {r['mode']} | {r['n']} | {q_short} | "
            f"{r['avg_satisfaction']:.1f} | {r['min_satisfaction']} | "
            f"{r['bottom_quartile_satisfaction']:.1f} | {r['satisfaction_variance']:.2f} |\n"
        )
    lines.append("\n")

    # Aggregate by mode
    lines.append("### Aggregate by Mode (averaged across all questions & sizes)\n\n")
    lines.append("| Mode | Avg Sat | Min Sat | Bot. Quartile | Variance |\n")
    lines.append("|------|---------|---------|---------------|----------|\n")
    for mode in MODES:
        mr = [r for r in valid if r["mode"] == mode]
        if not mr:
            continue
        avg_s = sum(r["avg_satisfaction"] for r in mr) / len(mr)
        min_s = sum(r["min_satisfaction"] for r in mr) / len(mr)
        bot_q = sum(r["bottom_quartile_satisfaction"] for r in mr) / len(mr)
        var_s = sum(r["satisfaction_variance"] for r in mr) / len(mr)
        lines.append(f"| {mode} | {avg_s:.2f} | {min_s:.1f} | {bot_q:.2f} | {var_s:.2f} |\n")
    lines.append("\n")

    # Graphs
    lines.append("### Graphs\n\n")
    for png in sorted(graphs_dir.glob("*.png")):
        rel = png.relative_to(BASE_DIR)
        title = png.stem.replace("_", " ").title()
        lines.append(f"#### {title}\n")
        lines.append(f"![{title}]({rel})\n\n")

    # Key findings
    lines.append("### Key Findings\n\n")

    # Best mode by avg satisfaction
    mode_avgs = {}
    for mode in MODES:
        mr = [r for r in valid if r["mode"] == mode]
        if mr:
            mode_avgs[mode] = sum(r["avg_satisfaction"] for r in mr) / len(mr)
    if mode_avgs:
        best_avg = max(mode_avgs, key=mode_avgs.get)
        lines.append(f"- **Highest average satisfaction:** {best_avg} ({mode_avgs[best_avg]:.2f})\n")

    # Best mode by minority satisfaction
    mode_bots = {}
    for mode in MODES:
        mr = [r for r in valid if r["mode"] == mode]
        if mr:
            mode_bots[mode] = sum(r["bottom_quartile_satisfaction"] for r in mr) / len(mr)
    if mode_bots:
        best_bot = max(mode_bots, key=mode_bots.get)
        lines.append(f"- **Best minority satisfaction:** {best_bot} ({mode_bots[best_bot]:.2f})\n")

    # Lowest variance
    mode_vars = {}
    for mode in MODES:
        mr = [r for r in valid if r["mode"] == mode]
        if mr:
            mode_vars[mode] = sum(r["satisfaction_variance"] for r in mr) / len(mr)
    if mode_vars:
        best_var = min(mode_vars, key=mode_vars.get)
        lines.append(f"- **Most equitable (lowest variance):** {best_var} ({mode_vars[best_var]:.2f})\n")

    # Scaling trend
    if len(sizes_used) > 1:
        lines.append(f"\n**Scaling trends (N={sizes_used[0]} → N={sizes_used[-1]}):**\n")
        for mode in MODES:
            small = [r for r in valid if r["mode"] == mode and r["n"] == sizes_used[0]]
            large = [r for r in valid if r["mode"] == mode and r["n"] == sizes_used[-1]]
            if small and large:
                avg_small = sum(r["avg_satisfaction"] for r in small) / len(small)
                avg_large = sum(r["avg_satisfaction"] for r in large) / len(large)
                delta = avg_large - avg_small
                direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
                lines.append(f"- {mode}: {avg_small:.1f} → {avg_large:.1f} ({direction}{abs(delta):.1f})\n")

    lines.append("\n---\n\n")

    # Write/append
    mode = "a" if report_path.exists() else "w"
    with open(report_path, mode) as f:
        f.writelines(lines)

    print(f"Report {'appended to' if mode == 'a' else 'written to'} {report_path}")


# ── Main ────────────────────────────────────────────────────

async def main():
    config_path = BASE_DIR / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Load principals — use principals_50.yaml if it exists and max N requires it
    max_n = max(POPULATION_SIZES)
    principals_50_path = BASE_DIR / "profiles" / "principals_50.yaml"
    if max_n > 10 and principals_50_path.exists():
        print(f"Loading extended principals from {principals_50_path}")
        with open(principals_50_path) as f:
            principals_data = yaml.safe_load(f)
    else:
        principals_path = BASE_DIR / config["principals_file"]
        with open(principals_path) as f:
            principals_data = yaml.safe_load(f)

    all_principals = [Principal(**p) for p in principals_data]
    print(f"Loaded {len(all_principals)} principals")

    if max_n > len(all_principals):
        print(f"WARNING: max population size ({max_n}) > available principals ({len(all_principals)}). "
              f"Will cap at {len(all_principals)}.")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        return

    llm = LLMClient(
        api_key=api_key,
        model=config["llm"]["model"],
        base_url=config["llm"]["base_url"],
    )

    wandb_project = config.get("experiment", {}).get("wandb_project", "deliberation")
    all_results = []

    total = len(MODES) * len(POPULATION_SIZES) * len(QUESTIONS) * NUM_TRIALS
    cell_num = 0
    sweep_start = time.time()
    cell_times = []

    for question in QUESTIONS:
        q_label = short_label(question, 40)
        for mode in MODES:
            for n in POPULATION_SIZES:
                for trial in range(NUM_TRIALS):
                    cell_num += 1
                    run_name = f"sweep_{mode}_n{n}_{q_label[:20].replace(' ', '_')}_t{trial}"

                    # Progress + ETA
                    elapsed = time.time() - sweep_start
                    if cell_times:
                        avg_cell = sum(cell_times) / len(cell_times)
                        remaining = avg_cell * (total - cell_num + 1)
                        eta_min = remaining / 60
                        eta_str = f"  ETA: {eta_min:.0f}min"
                    else:
                        eta_str = ""

                    print(f"\n{'='*60}")
                    print(f"[{cell_num}/{total}] {run_name}  ({elapsed/60:.1f}min elapsed{eta_str})")
                    print(f"  Q: {question}")
                    print(f"{'='*60}")

                    cell_start = time.time()

                    wandb.init(
                        project=wandb_project,
                        name=run_name,
                        group="mode_sweep_v2",
                        config={
                            "mode": mode,
                            "n": n,
                            "trial": trial,
                            "question": question,
                            "question_short": q_label,
                            "num_rounds": NUM_ROUNDS,
                            "n_clusters": N_CLUSTERS,
                            "model": config["llm"]["model"],
                        },
                    )

                    try:
                        cell_result = await run_cell(
                            all_principals, llm, mode, n, question, trial,
                        )
                        all_results.append(cell_result)

                        wandb.log({
                            "avg_satisfaction": cell_result["avg_satisfaction"],
                            "min_satisfaction": cell_result["min_satisfaction"],
                            "max_satisfaction": cell_result["max_satisfaction"],
                            "bottom_quartile_satisfaction": cell_result["bottom_quartile_satisfaction"],
                            "satisfaction_variance": cell_result["satisfaction_variance"],
                        })

                        # Log per-principal scores
                        for pid, data in cell_result["per_principal"].items():
                            wandb.log({
                                f"principal/{data['name']}/satisfaction": data["score"],
                            })

                        cell_elapsed = time.time() - cell_start
                        cell_times.append(cell_elapsed)
                        print(f"  avg={cell_result['avg_satisfaction']:.2f}  "
                              f"min={cell_result['min_satisfaction']}  "
                              f"bottom_q={cell_result['bottom_quartile_satisfaction']:.1f}  "
                              f"({cell_elapsed:.0f}s)")
                    except Exception as e:
                        print(f"  ERROR: {e}")
                        import traceback
                        traceback.print_exc()
                        all_results.append({
                            "mode": mode, "n": n, "question": question,
                            "trial": trial, "error": str(e),
                        })
                    finally:
                        wandb.finish()

    # Save results JSON
    RUNS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RUNS_DIR / f"{timestamp}_sweep.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)

    # Generate and save graphs
    graphs_dir = RUNS_DIR / f"{timestamp}_graphs"
    graph_paths = generate_graphs(all_results, graphs_dir)
    print(f"\nGraphs saved to {graphs_dir}/")

    # Generate report
    generate_report(all_results, graphs_dir, timestamp)

    # Log graphs to W&B as a summary run
    wandb.init(
        project=wandb_project,
        name=f"sweep_summary_{timestamp}",
        group="mode_sweep_v2",
        job_type="summary",
        config={
            "modes": MODES,
            "population_sizes": POPULATION_SIZES,
            "questions": QUESTIONS,
            "num_trials": NUM_TRIALS,
            "num_rounds": NUM_ROUNDS,
        },
    )
    for path in graph_paths:
        wandb.log({path.stem: wandb.Image(str(path))})

    artifact = wandb.Artifact(f"sweep_{timestamp}", type="results")
    artifact.add_file(str(output_path))
    artifact.add_dir(str(graphs_dir), name="graphs")
    wandb.log_artifact(artifact)
    wandb.finish()

    # Print summary table
    print(f"\n{'='*80}")
    print("SWEEP COMPLETE")
    print(f"{'='*80}")
    print(f"{'Mode':<15} {'N':<5} {'Question':<40} {'Avg':>6} {'Min':>5} {'BotQ':>6} {'Var':>6}")
    print("-" * 85)
    for r in all_results:
        if "error" in r:
            print(f"{r['mode']:<15} {r['n']:<5} {short_label(r['question'], 38):<40} {'ERROR':>6}")
        else:
            print(f"{r['mode']:<15} {r['n']:<5} "
                  f"{short_label(r['question'], 38):<40} "
                  f"{r['avg_satisfaction']:>6.1f} "
                  f"{r['min_satisfaction']:>5.0f} "
                  f"{r['bottom_quartile_satisfaction']:>6.1f} "
                  f"{r['satisfaction_variance']:>6.2f}")

    print(f"\nResults saved to {output_path}")
    print(f"Graphs saved to {graphs_dir}/")
    print(f"Report at {BASE_DIR / 'report.md'}")


if __name__ == "__main__":
    asyncio.run(main())
