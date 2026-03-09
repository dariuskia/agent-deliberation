from collections import Counter, defaultdict

from .models import Ballot, CandidateStatement


def instant_runoff(
    ballots: list[Ballot], candidates: list[CandidateStatement]
) -> CandidateStatement:
    active_ids = {c.id for c in candidates}
    candidate_map = {c.id: c for c in candidates}
    rankings = [b.ranking for b in ballots]

    while len(active_ids) > 1:
        # Count first-choice votes among active candidates
        counts = {i: 0 for i in active_ids}
        for ranking in rankings:
            for cid in ranking:
                if cid in active_ids:
                    counts[cid] += 1
                    break

        total = len(candidates)

        # Check for majority
        max_cid = max(counts, key=counts.get)
        if counts[max_cid] > total / 2:
            return candidate_map[max_cid]

        # Eliminate candidate with fewest first-choice votes
        min_cid = min(counts, key=counts.get)
        active_ids.discard(min_cid)

    return candidate_map[active_ids.pop()]
