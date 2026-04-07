"""Generate diverse principal profiles using the LLM.

Keeps existing P0-P9 from principals.yaml and generates P10-P49.
Saves combined set to profiles/principals_50.yaml.
"""

import asyncio
import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from deliberation.llm import LLMClient, extract_json

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TARGET_COUNT = 50

# Diversity dimensions to ensure coverage
DIVERSITY_SPECS = [
    # (age_range, race/ethnicity, region, occupation_type, political_lean)
    ("20s", "White", "Midwest", "farmer/agricultural worker", "conservative"),
    ("30s", "Black", "South", "nurse", "moderate Democrat"),
    ("40s", "Hispanic/Latino", "Southwest", "construction foreman", "independent"),
    ("50s", "White", "Appalachia", "coal miner turned solar installer", "populist"),
    ("60s", "Asian-American", "West Coast", "retired restaurant owner", "moderate Republican"),
    ("20s", "Native American", "Plains states", "tribal government employee", "progressive"),
    ("30s", "White", "Northeast", "social worker", "progressive"),
    ("40s", "Black", "Midwest", "police officer", "moderate"),
    ("50s", "South Asian", "Texas", "gas station franchise owner", "libertarian"),
    ("60s", "White", "Pacific Northwest", "retired teacher", "liberal"),
    ("20s", "Mixed race", "Southeast", "gig economy driver", "disengaged/apolitical"),
    ("30s", "Hispanic/Latino", "California", "tech support worker", "progressive"),
    ("40s", "White", "Rural South", "evangelical pastor", "social conservative"),
    ("50s", "Black", "Mid-Atlantic", "postal worker", "union Democrat"),
    ("60s", "Vietnamese-American", "Gulf Coast", "shrimp boat operator", "conservative Democrat"),
    ("20s", "White", "Mountain West", "ski instructor / seasonal worker", "libertarian"),
    ("30s", "Middle Eastern", "Michigan", "auto industry engineer", "moderate"),
    ("40s", "White", "Suburban Midwest", "stay-at-home parent / PTA president", "moderate Republican"),
    ("50s", "Black", "Deep South", "Baptist minister", "progressive on economics, conservative on social"),
    ("60s", "Italian-American", "New Jersey", "retired firefighter", "blue-collar Democrat"),
    ("20s", "Korean-American", "New York", "graduate student in public policy", "progressive"),
    ("30s", "White", "Alaska", "commercial fisherman", "independent/libertarian"),
    ("40s", "Mexican-American", "Border town Texas", "school principal", "moderate Democrat"),
    ("50s", "White", "New England", "small-town pharmacist", "fiscally conservative, socially moderate"),
    ("60s", "Filipino-American", "Hawaii", "retired Navy veteran", "moderate Republican"),
    ("20s", "Black", "Atlanta", "aspiring rapper / retail worker", "progressive"),
    ("30s", "White", "Silicon Valley", "startup founder (failed)", "techno-libertarian"),
    ("40s", "Puerto Rican", "Florida", "insurance agent", "swing voter"),
    ("50s", "White", "Great Plains", "cattle rancher", "conservative Republican"),
    ("60s", "Chinese-American", "San Francisco", "retired accountant", "moderate Democrat"),
    ("20s", "Somali-American", "Minnesota", "community college student", "progressive"),
    ("30s", "White", "Rust Belt", "unemployed factory worker", "populist right"),
    ("40s", "Indian-American", "Research Triangle NC", "biotech researcher", "moderate"),
    ("50s", "White", "Suburban Atlanta", "real estate agent", "conservative"),
    ("60s", "Jewish-American", "South Florida", "retired lawyer", "liberal Democrat"),
    ("20s", "Hispanic/Latina", "Colorado", "wildland firefighter", "independent"),
    ("30s", "White", "Montana", "park ranger", "centrist environmentalist"),
    ("40s", "Haitian-American", "Boston", "home health aide", "moderate Democrat"),
    ("50s", "White", "Oklahoma", "oil field supervisor", "conservative Republican"),
    ("60s", "Japanese-American", "Portland", "retired social studies teacher", "progressive"),
]

GENERATION_PROMPT_SYSTEM = """You are generating a realistic American citizen profile for a deliberation simulation.

OUTPUT FORMAT: Return a JSON object with these fields:
- "name": A realistic full name matching the demographic
- "profile": 4-6 sentences describing their life, background, work, family, hobbies. Make it vivid and specific. Include concrete details like specific towns, workplaces, habits.
- "values": 4-6 sentences describing their publicly expressed values and political views. Be nuanced — real people have complex, sometimes contradictory views.
- "hidden_values": 4-6 sentences describing private fears, doubts, contradictions they'd never express publicly. These should create tension with their public values. Every person has private anxieties that complicate their public persona.

IMPORTANT:
- Make the person feel real, not like a stereotype
- Hidden values should reveal genuine human complexity
- Use American cultural references and context
- Output ONLY the JSON object, nothing else"""


async def generate_principals(llm: LLMClient, existing: list[dict]) -> list[dict]:
    n_existing = len(existing)
    n_needed = TARGET_COUNT - n_existing

    if n_needed <= 0:
        print(f"Already have {n_existing} principals, no generation needed.")
        return existing

    print(f"Generating {n_needed} new principals (P{n_existing}-P{TARGET_COUNT - 1})...")

    specs = DIVERSITY_SPECS[:n_needed]
    # Pad with generic specs if we need more than the spec list
    while len(specs) < n_needed:
        specs.append(("varies", "varies", "varies", "varies", "varies"))

    requests = []
    for i, (age, race, region, occupation, politics) in enumerate(specs):
        pid = f"P{n_existing + i}"
        user_msg = f"""Generate a profile for: {pid}
- Age range: {age}
- Race/ethnicity: {race}
- Region: {region}
- Occupation type: {occupation}
- Political lean: {politics}

Return a JSON object with fields: name, profile, values, hidden_values"""
        requests.append((GENERATION_PROMPT_SYSTEM, user_msg))

    # Generate in batches to avoid overwhelming the API
    batch_size = 10
    all_new = []
    for batch_start in range(0, len(requests), batch_size):
        batch = requests[batch_start:batch_start + batch_size]
        print(f"  Batch {batch_start // batch_size + 1}/{(len(requests) + batch_size - 1) // batch_size}...")
        responses = await llm.complete_batch(batch, temperature=0.8)

        for j, resp in enumerate(responses):
            idx = batch_start + j
            pid = f"P{n_existing + idx}"
            try:
                data = extract_json(resp)
                principal = {
                    "id": pid,
                    "name": data["name"],
                    "profile": data["profile"].strip(),
                    "values": data["values"].strip(),
                    "hidden_values": data["hidden_values"].strip(),
                }
                all_new.append(principal)
                print(f"    {pid}: {data['name']}")
            except Exception as e:
                print(f"    {pid}: ERROR - {e}")
                # Create a fallback
                all_new.append({
                    "id": pid,
                    "name": f"Citizen {idx}",
                    "profile": f"A {specs[idx][0]} {specs[idx][1]} {specs[idx][3]} from {specs[idx][2]}.",
                    "values": f"Politically {specs[idx][4]}. Values hard work and fairness.",
                    "hidden_values": "Privately worried about the future and feels unheard.",
                })

    return existing + all_new


async def main():
    config_path = BASE_DIR / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Load existing principals
    principals_path = BASE_DIR / config["principals_file"]
    with open(principals_path) as f:
        existing = yaml.safe_load(f)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set.")
        return

    llm = LLMClient(
        api_key=api_key,
        model=config["llm"]["model"],
        base_url=config["llm"]["base_url"],
        max_concurrent=10,
    )

    all_principals = await generate_principals(llm, existing)

    output_path = BASE_DIR / "profiles" / "principals_50.yaml"
    with open(output_path, "w") as f:
        yaml.dump(all_principals, f, default_flow_style=False, allow_unicode=True, width=120)

    print(f"\nSaved {len(all_principals)} principals to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
