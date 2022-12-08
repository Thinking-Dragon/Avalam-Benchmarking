#!/usr/bin/python3

import sys
import time
import subprocess
import pickle
import re

def load_benchmarks_cache():
    try:
        file = open('benchmarks.cache', 'rb')
        benchmarks = pickle.load(file)
        file.close()
        return benchmarks
    except FileNotFoundError:
        return dict()

def save_benchmarks_cache(cache):
    file = open('benchmarks.cache', 'wb')
    pickle.dump(cache, file)
    file.close()

def print_benchmark_results(agent1_name, agent1_win_ratio, agent2_name, agent2_win_ratio):
    print('Result:')
    print('-----------------------------------------------------------------------')
    print(agent1_name, ' win ratio: ', agent1_win_ratio * 100, '%')
    print(agent2_name, ' win ratio: ', agent2_win_ratio * 100, '%')
    print('=======================================================================\n')

class BenchmarkResult:
    def __init__(self, agent1_name: str, agent1_win_ratio: int, agent2_name: str, agent2_win_ratio: int, iterations: int) -> None:
        self.agent1_name = agent1_name
        self.agent1_win_ratio = agent1_win_ratio
        self.agent2_name = agent2_name
        self.agent2_win_ratio = agent2_win_ratio
        self.iterations = iterations

class GameEvent:
    NONE = 0
    END_OF_STREAM = 1
    GAME_ENDED = 2

def start_agent(name: str, port: str):
    return subprocess.Popen(
        [
            'python3', './' + name,
            '-b', 'localhost',
            '-p', port
        ],
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def start_game(port1: str, port2: str):
    return subprocess.Popen(
        [
            'python3', './game.py',
            'http://localhost:' + port1,
            'http://localhost:' + port2,
            '--time', '900',
            '--no-gui',
            '--verbose'
        ],
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

def process_game_log(process):
    log_line = process.stdout.readline()
    if process.poll() is not None:
        return GameEvent.END_OF_STREAM, None
    if log_line:
        line = log_line.strip().decode('utf-8')

        if re.search('Player [0-9] has won!', line):
            winner_id = int(line.split(' ')[1])
            return GameEvent.GAME_ENDED, winner_id

    return GameEvent.NONE, None

def play_match(agent1_name: str, agent2_name: str):
    print('\tRunning match: ', agent1_name, ' vs ', agent2_name)

    agent1_port, agent2_port = '8080', '8000'
    agent1_process = start_agent(agent1_name, agent1_port)
    agent2_process = start_agent(agent2_name, agent2_port)

    time.sleep(1)
    game_process = start_game(agent1_port, agent2_port)

    winner_id = -1
    game_finished = False
    while not game_finished:
        game_event, event_payload = process_game_log(game_process)

        if game_event == GameEvent.END_OF_STREAM:
            print('\t> Game has ceased unexpectedly\n')
            game_finished = True

        if game_event == GameEvent.GAME_ENDED:
            winner_id = event_payload
            winner_name = agent1_name if winner_id == 1 else agent2_name
            print('\t> Game was won by ', winner_name, '\n')
            game_finished = True

    game_process.kill()
    agent1_process.kill()
    agent2_process.kill()

    return winner_id

def execute_benchmark(agent1_name: str, agent2_name: str, iterations: int):
    print('=======================================================================')
    print('Running ', iterations, ' matches between ', agent1_name, ' and ', agent2_name)
    print('=======================================================================')
    agent1_wins = 0
    agent2_wins = 0

    for i in range(iterations):
        winner_id = play_match(agent1_name, agent2_name)
        if winner_id == 1:
            agent1_wins += 1
        if winner_id == 2:
            agent2_wins += 1
    
    agent1_win_ratio = agent1_wins / iterations
    agent2_win_ratio = agent2_wins / iterations

    print_benchmark_results(
        agent1_name, agent1_win_ratio,
        agent2_name, agent2_win_ratio
    )

    return agent1_win_ratio, agent2_win_ratio

def benchmark_agents(cache, agent1_name, agent2_name, iterations, should_ignore_cache):
    key = (agent1_name, agent2_name)
    if key in cache.keys() and not should_ignore_cache:
        cached_benchmark = cache[key]
        print('=======================================================================')
        print('Already ran ', cached_benchmark.iterations, ' matches between ', cached_benchmark.agent1_name, ' and ', cached_benchmark.agent2_name)
        print_benchmark_results(
            cached_benchmark.agent1_name, cached_benchmark.agent1_win_ratio,
            cached_benchmark.agent2_name, cached_benchmark.agent2_win_ratio
        )
    else:
        agent1_win_ratio, agent2_win_ratio = execute_benchmark(agent1_name, agent2_name, iterations)
        cache[key] = BenchmarkResult(agent1_name, agent1_win_ratio, agent2_name, agent2_win_ratio, iterations)

def start_benchmark(iterations: int, agent_names: list, should_ignore_cache: bool = False):
    benchmarks = load_benchmarks_cache()

    for i in range(len(agent_names)):
        for j in range(i + 1, len(agent_names)):
            agent1_name = agent_names[i]
            agent2_name = agent_names[j]
            benchmark_agents(benchmarks, agent1_name, agent2_name, iterations, should_ignore_cache)
            benchmark_agents(benchmarks, agent2_name, agent1_name, iterations, should_ignore_cache)

    save_benchmarks_cache(benchmarks)

if __name__ == '__main__':
    iterations = int(sys.argv[1])
    agent_names = sys.argv[2].split(',')
    should_ignore_cache = len(sys.argv) >= 4 and sys.argv[3] == '--ignore-cache'

    start_benchmark(iterations, agent_names, should_ignore_cache)