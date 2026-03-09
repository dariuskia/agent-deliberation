import asyncio
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import wandb
import yaml
from dotenv import load_dotenv

from deliberation.deliberation import run_deliberation
from deliberation.llm import LLMClient
from deliberation.models import ExperimentResult, Principal

BASE_DIR = Path(__file__).resolve().parent
RUNS_DIR = BASE_DIR / "runs"

load_dotenv(BASE_DIR / ".env")


def compute_regret(
    delegate_scores: dict[str, dict],
    principal_scores: dict[str, dict],
) -> dict:
    """Compute delegation regret: principal_satisfaction - delegate_satisfaction."""
    per_principal = {}
    for pid in delegate_scores:
        d_score = delegate_scores[pid]["score"]
        p_score = principal_scores[pid]["score"]
        regret = p_score - d_score
        per_principal[pid] = {
            "delegate_satisfaction": d_score,
            "principal_satisfaction": p_score,
            "regret": regret,
        }

    regrets = [v["regret"] for v in per_principal.values()]
    d_scores = [v["delegate_satisfaction"] for v in per_principal.values()]
    p_scores = [v["principal_satisfaction"] for v in per_principal.values()]

    return {
        "per_principal": per_principal,
        "avg_regret": sum(regrets) / len(regrets),
        "max_regret": max(regrets),
        "min_regret": min(regrets),
        "avg_delegate_satisfaction": sum(d_scores) / len(d_scores),
        "avg_principal_satisfaction": sum(p_scores) / len(p_scores),
    }


async def run_experiment(config: dict, principals: list[Principal], llm: LLMClient):
    question = config["question"]
    num_rounds = config["deliberation"]["num_rounds"]

    # Run delegate deliberation (no hidden values)
    print("=" * 60)
    print("DELEGATE DELIBERATION (no hidden values)")
    print("=" * 60)
    delegate_result = await run_deliberation(
        llm=llm,
        principals=principals,
        question=question,
        num_rounds=num_rounds,
        include_hidden_values=False,
        label="delegate",
    )

    # Run principal deliberation (with hidden values)
    print()
    print("=" * 60)
    print("PRINCIPAL DELIBERATION (with hidden values)")
    print("=" * 60)
    principal_result = await run_deliberation(
        llm=llm,
        principals=principals,
        question=question,
        num_rounds=num_rounds,
        include_hidden_values=True,
        label="principal",
    )

    # Compute delegation regret
    regret = compute_regret(
        delegate_result.satisfaction_scores,
        principal_result.satisfaction_scores,
    )

    return ExperimentResult(
        config=config,
        delegate_result=delegate_result,
        principal_result=principal_result,
        delegation_regret=regret,
    )


async def main():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    principals_path = Path(__file__).parent / config["principals_file"]
    with open(principals_path) as f:
        principals_data = yaml.safe_load(f)

    all_principals = [Principal(**p) for p in principals_data]

    selected_ids = config["deliberation"].get("principal_ids")
    if selected_ids:
        principals = [p for p in all_principals if p.id in selected_ids]
    else:
        principals = all_principals

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        return

    llm = LLMClient(
        api_key=api_key,
        model=config["llm"]["model"],
        base_url=config["llm"]["base_url"],
    )

    exp_config = config.get("experiment", {})
    num_trials = exp_config.get("num_trials", 1)
    wandb_project = exp_config.get("wandb_project", "deliberation")
    exp_name = exp_config.get("name", "experiment")

    for trial in range(num_trials):
        run_name = f"{exp_name}_trial{trial}" if num_trials > 1 else exp_name

        # Init W&B
        wandb.init(
            project=wandb_project,
            name=run_name,
            config={
                "question": config["question"],
                "model": config["llm"]["model"],
                "num_rounds": config["deliberation"]["num_rounds"],
                "topology": config["deliberation"].get("topology", "flat"),
                "num_principals": len(principals),
                "principal_ids": [p.id for p in principals],
                "trial": trial,
            },
        )

        print(f"\n{'#' * 60}")
        print(f"TRIAL {trial + 1}/{num_trials}: {run_name}")
        print(f"Question: {config['question']}")
        print(f"Principals: {len(principals)}, Rounds: {config['deliberation']['num_rounds']}")
        print(f"{'#' * 60}\n")

        result = await run_experiment(config, principals, llm)

        # Log metrics to W&B
        regret = result.delegation_regret
        wandb.log({
            "delegate/avg_satisfaction": regret["avg_delegate_satisfaction"],
            "principal/avg_satisfaction": regret["avg_principal_satisfaction"],
            "regret/avg": regret["avg_regret"],
            "regret/max": regret["max_regret"],
            "regret/min": regret["min_regret"],
        })

        # Log per-principal metrics
        for pid, data in regret["per_principal"].items():
            principal = next(p for p in principals if p.id == pid)
            wandb.log({
                f"per_principal/{principal.name}/delegate_satisfaction": data["delegate_satisfaction"],
                f"per_principal/{principal.name}/principal_satisfaction": data["principal_satisfaction"],
                f"per_principal/{principal.name}/regret": data["regret"],
            })

        # Save full result as artifact
        runs_dir = Path(__file__).parent / "runs"
        runs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = runs_dir / f"{timestamp}_experiment.json"
        with open(output_path, "w") as f:
            json.dump(asdict(result), f, indent=2)

        artifact = wandb.Artifact(f"experiment_{timestamp}", type="result")
        artifact.add_file(str(output_path))
        wandb.log_artifact(artifact)

        # Print summary
        print()
        print("=" * 60)
        print("EXPERIMENT COMPLETE")
        print("=" * 60)
        print(f"Delegate consensus: {result.delegate_result.winner.text}")
        print(f"Principal consensus: {result.principal_result.winner.text}")
        print()
        print(f"Avg delegate satisfaction: {regret['avg_delegate_satisfaction']:.1f}/10")
        print(f"Avg principal satisfaction: {regret['avg_principal_satisfaction']:.1f}/10")
        print(f"Avg delegation regret: {regret['avg_regret']:.2f}")
        print(f"Max regret: {regret['max_regret']:.1f}, Min regret: {regret['min_regret']:.1f}")
        print()
        print("Per-principal regret:")
        for pid, data in regret["per_principal"].items():
            principal = next(p for p in principals if p.id == pid)
            print(f"  {principal.name}: delegate={data['delegate_satisfaction']}/10, "
                  f"principal={data['principal_satisfaction']}/10, "
                  f"regret={data['regret']:+.1f}")
        print()
        print(f"Full results saved to {output_path}")

        wandb.finish()


if __name__ == "__main__":
    asyncio.run(main())
