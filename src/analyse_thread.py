
import argparse
import sys
from pathlib import Path
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor

from analyse_seq import analyser, rapport
from analyse_par import (
    BlocJournal,
    traiter_bloc,
    fusionner,
    entier_positif,
    ecrire_sans_ecraser
)


def analyser_threads(chemin, workers, filtre_date=None):
    debut_mesure = perf_counter()
    taille = chemin.stat().st_size
    total = analyser(BlocJournal(chemin, 0, 0), filtre_date)

    taches = [
        (chemin, taille * i // workers,
         taille * (i + 1) // workers, filtre_date)
        for i in range(workers)
    ]

    with ThreadPoolExecutor(max_workers=workers) as executant:
        for partiel in executant.map(traiter_bloc, taches):
            fusionner(total, partiel)

    total['duree'] = perf_counter() - debut_mesure
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('journal', type=Path)
    parser.add_argument('N', type=entier_positif)
    parser.add_argument('--date')
    parser.add_argument('-o', '--sortie', type=Path,
                        default=Path('resultats/JOURNAL_thread.txt'))
    args = parser.parse_args()

    if not args.journal.is_file():
        parser.error('Le fichier journal est absent ou invalide.')

    try:
        stats = analyser_threads(args.journal, args.N, args.date)
        texte = rapport(stats, args.date)
        sortie = ecrire_sans_ecraser(args.sortie, texte)
    except (OSError, ValueError) as erreur:
        print(f'Erreur : {erreur}', file=sys.stderr)
        return 1

    print(f'Rapport enregistré dans : {sortie}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
