import asyncio
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import yaml

from deliberation.deliberation import run_deliberation
from deliberation.llm import LLMClient
from deliberation.models import Principal


async def main():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    principals_path = Path(__file__).parent / config["principals_file"]
    with open(principals_path) as f:
        principals_data = yaml.safe_load(f)

    all_principals = [Principal(**p) for p in principals_data]

    # Filter by principal_ids if specified
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

    print(f"Starting deliberation with {len(principals)} delegates...")
    print(f"Question: {config['question']}")
    print(f"Rounds: {config['deliberation']['num_rounds']}")
    print()

    result = await run_deliberation(
        llm=llm,
        principals=principals,
        question=config["question"],
        num_rounds=config["deliberation"]["num_rounds"],
    )

    # Save results
    runs_dir = Path(__file__).parent / "runs"
    runs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = runs_dir / f"{timestamp}_result.json"

    with open(output_path, "w") as f:
        json.dump(asdict(result), f, indent=2)

    # Print summary
    print()
    print("=" * 60)
    print("DELIBERATION COMPLETE")
    print("=" * 60)
    print()
    print(f"QUESTION: {result.question}")
    print()
    print("CANDIDATE STATEMENTS:")
    for cs in result.candidate_statements:
        print(f"  [{cs.id}] ({cs.delegate_id}): {cs.text[:100]}...")
    print()
    print(f"WINNER: [{result.winner.id}]")
    print(f"  {result.winner.text}")
    print()
    print("SATISFACTION SCORES:")
    scores = []
    for pid, info in result.satisfaction_scores.items():
        principal = next(p for p in result.principals if p.id == pid)
        score = info["score"]
        scores.append(score)
        print(f"  {principal.name} ({pid}): {score}/10 — {info['reasoning']}")
    print()
    avg = sum(scores) / len(scores)
    print(f"Average satisfaction: {avg:.1f}/10")
    print(f"Min: {min(scores)}/10  Max: {max(scores)}/10")
    print()
    print(f"Full results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
