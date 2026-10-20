from multiprocessing import Process, Value, Lock

def compter(total, verrou):
    for _ in range(100_000):
        with verrou:                 # section critique
            total.value += 1         # lire, ajouter, écrire

if __name__ == "__main__":
    total = Value("i", 0, lock=False)  # entier partagé
    verrou = Lock()
    workers = [Process(target=compter,
                       args=(total, verrou))
               for _ in range(4)]

    for w in workers:
        w.start()                     # lancer
    for w in workers:
        w.join()                      # attendre la fin

    print(total.value)                # 400000