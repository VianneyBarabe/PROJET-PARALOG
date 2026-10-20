import argparse
import multiprocessing
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from time import perf_counter

from analyse_seq import analyser, rapport


class BlocJournal:
    def __init__(self, chemin, debut, fin):
        self.chemin = chemin
        self.debut = debut
        self.fin = fin

    @contextmanager
    def open(self, mode='r', encoding='utf-8', errors='surrogateescape'):
        with self.chemin.open('rb') as fichier:
            if self.debut:
                fichier.seek(self.debut - 1)
                if fichier.read(1) != b'\n':
                    fichier.readline()
            else:
                fichier.seek(0)

            def lignes():
                while fichier.tell() < self.fin:
                    ligne = fichier.readline()
                    if not ligne:
                        break
                    yield ligne.decode(encoding, errors=errors)

            yield lignes()


def traiter_bloc(tache):
    chemin, debut, fin, filtre_date = tache
    return analyser(BlocJournal(chemin, debut, fin), filtre_date)


def fusionner(total, partiel):
    for cle, valeur in partiel.items():
        if isinstance(valeur, Counter):
            total[cle].update(valeur)
        elif cle in ('premier', 'dernier'):
            if valeur is not None:
                if total[cle] is None:
                    total[cle] = valeur
                elif cle == 'premier':
                    total[cle] = min(total[cle], valeur)
                else:
                    total[cle] = max(total[cle], valeur)
        elif cle != 'duree':
            total[cle] += valeur


def analyser_parallele(chemin, workers, filtre_date=None):
    if workers < 1:
        raise ValueError('Le nombre de workers doit être positif.')
    debut_mesure = perf_counter()
    taille = chemin.stat().st_size
    total = analyser(BlocJournal(chemin, 0, 0), filtre_date)
    taches = [
        (chemin, taille * i // workers, taille * (i + 1) // workers, filtre_date)
        for i in range(workers)
    ]

    contexte = multiprocessing.get_context('spawn')
    with ProcessPoolExecutor(max_workers=workers, mp_context=contexte) as executant:
        for partiel in executant.map(traiter_bloc, taches):
            fusionner(total, partiel)

    total['duree'] = perf_counter() - debut_mesure
    return total


def ecrire_sans_ecraser(chemin, texte):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    candidat = chemin
    numero = 1
    while True:
        try:
            with candidat.open('x', encoding='utf-8') as fichier:
                fichier.write(texte)
            return candidat
        except FileExistsError:
            candidat = chemin.with_name('{}_{}{}'.format(
                chemin.stem, numero, chemin.suffix))
            numero += 1


def entier_positif(texte):
    try:
        nombre = int(texte)
    except ValueError:
        raise argparse.ArgumentTypeError('N doit être un entier positif.')
    if nombre < 1:
        raise argparse.ArgumentTypeError('N doit être supérieur ou égal à 1.')
    return nombre


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('journal', type=Path, help='Fichier Apache combined')
    parser.add_argument('N', type=entier_positif, help='Nombre de processus workers')
    parser.add_argument('--date', help='Date locale AAAA-MM-JJ (optionnelle)')
    parser.add_argument('-o', '--sortie', type=Path,
                        default=Path('resultats/JOURNAL_par.txt'))
    args = parser.parse_args()
    if args.date:
        try:
            if date.fromisoformat(args.date).isoformat() != args.date:
                raise ValueError()
        except ValueError:
            parser.error('--date doit être une date valide au format AAAA-MM-JJ.')

    try:
        if not args.journal.is_file():
            parser.error('Le fichier journal est absent ou n’est pas un fichier ordinaire.')
        if args.journal.resolve() == args.sortie.resolve():
            parser.error('Le rapport doit être différent du fichier de logs.')
        if args.sortie.exists() and args.journal.samefile(args.sortie):
            parser.error('Le rapport et les logs désignent le même fichier.')
        print('Analyse avec {} workers...'.format(args.N), file=sys.stderr)
        stats = analyser_parallele(args.journal, args.N, args.date)
        texte = rapport(stats, args.date)
        sortie = ecrire_sans_ecraser(args.sortie, texte)
    except (OSError, ValueError) as erreur:
        print('Erreur : {}'.format(erreur), file=sys.stderr)
        return 1

    print('\nRapport enregistré dans : {}'.format(sortie), file=sys.stderr)
    return 0


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
