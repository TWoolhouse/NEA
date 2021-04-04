import game
from games.g_dino.main import main

if __name__ == "__main__":
    import json
    import time
    import neural
    import pickle
    from path import PATH

    GAME_PATH = f"{PATH}games/g_dino/net/"

    # AI Train
    LOG_FILE = f"{GAME_PATH}data.log"
    with open(LOG_FILE, "r") as file:
        log_data: list[float] = json.load(file)
    FILE = f"{GAME_PATH}ai.net"
    try:
        with open(FILE, "rb") as file:
            network = pickle.load(file)
    except (IOError, EOFError):
        open(FILE, "wb").close()
        network = main.AI

    start_time = time.time()
    prev_time = start_time
    algo = neural.algorithm.Genetic(network, 12, 0.8, 0.2)
    try:
        while True:
            current_time = time.time()
            print(round(current_time - prev_time), round(current_time - start_time))
            prev_time = current_time
            print("Generation:", len(log_data))
            score = game.run_train(
                main,
                algo,
                3, timeout=150,
            )
            if score is not None:
                log_data.append(score)
                print("Score:", round(score))
            else:
                print("Timeout")
            with open(FILE, "wb") as file:
                pickle.dump(algo.network, file)
            with open(LOG_FILE, "w") as file:
                json.dump(log_data, file)
    finally:
        with open(LOG_FILE, "w") as file:
            json.dump(log_data, file)
