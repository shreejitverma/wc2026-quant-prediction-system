from wc2026.simulator.bracket_rules import map_third_place_teams


def test_map_third_place_perf(benchmark):
    """Benchmark the greedy matching of 3rd place teams for the knockout phase."""
    # Setup test data
    groups = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    team_to_group = {f"Team{i}": groups[i % 12] for i in range(48)}
    
    group_winners = [f"Team{i}" for i in range(8)]
    # Pick 8 third place teams that are in different groups
    third_placed_teams = [f"Team{i+24}" for i in range(8)]
    
    # Run benchmark
    benchmark(map_third_place_teams, group_winners, third_placed_teams, team_to_group)
