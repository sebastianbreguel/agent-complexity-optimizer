def leaders_per_round(rounds, scores):
    leaders = []
    for new_scores in rounds:
        scores.extend(new_scores)
        leaders.append(sorted(scores, reverse=True)[:3])
    return leaders
