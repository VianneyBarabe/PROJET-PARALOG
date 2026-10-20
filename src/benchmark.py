import argparse
import multiprocessing
import sys
import os
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from analyse_seq import entier_positif
from analyse_par import analyser_parallele

if hasattr(os, "sched_getaffinity"):
    nombre_coeurs = len(os.sched_getaffinity(0))
else:
    nombre_coeurs = os.cpu_count() or 1

WORKERS = tuple(sorted(
    {1, nombre_coeurs}
    | set(range(2, nombre_coeurs + 1, 2))
))

def creer_dossier(racine):
    racine.mkdir(parents=True, exist_ok=True)
    nom = 'benchmark_' + datetime.now().strftime('%Y%m%d_%H%M%S')
    numero = 0
    while True:
        dossier = racine / (nom if numero == 0 else nom + '_' + str(numero))
        try:
            dossier.mkdir()
            return dossier
        except FileExistsError:
            numero += 1


def empreinte_fichier(chemin):
    s = chemin.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)


def mesurer(chemin, essais):
    reference = None
    resultats = []
    compteur = 0
    total = essais * len(WORKERS)
    empreinte = empreinte_fichier(chemin)
    for workers in WORKERS:
        temps = []
        for essai in range(1, essais + 1):
            compteur += 1
            print(f'[{compteur}/{total}] {workers} worker(s) — essai {essai}/{essais}...', flush=True)
            if empreinte_fichier(chemin) != empreinte:
                raise ValueError('Le fichier source a changé pendant le benchmark.')
            stats = analyser_parallele(chemin, workers)
            if empreinte_fichier(chemin) != empreinte:
                raise ValueError('Le fichier source a changé pendant le benchmark.')
            duree = stats.pop('duree')
            if reference is None:
                reference = stats
            elif stats != reference:
                raise ValueError('Les statistiques diffèrent du premier essai à 1 worker.')
            temps.append(duree)
            print(f'  {duree:.3f} s', flush=True)
        resultats.append({
            'workers': workers,
            'moyenne': mean(temps),
            'ecart_type': stdev(temps) if essais > 1 else 0.0
        })
    return resultats


def tracer(resultats, destination, plt, titre):
    nombres = [r['workers'] for r in resultats]
    moyennes = [r['moyenne'] for r in resultats]
    ecarts = [r['ecart_type'] for r in resultats]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.errorbar(nombres, moyennes, yerr=ecarts, fmt='o-', capsize=5,
                color='steelblue', label='Temps moyen ± écart-type')
    for n, t in zip(nombres, moyennes):
        ax.annotate(f'{t:.2f} s', (n, t), xytext=(0, 10),
                    textcoords='offset points', ha='center', fontsize=9)
    ax.set_xticks(nombres)
    ax.set_xlabel('Nombre de workers')
    ax.set_ylabel('Temps d’analyse (secondes)')
    ax.set_title(titre)
    ax.set_ylim(bottom=0)
    ax.margins(y=0.25)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(destination, dpi=160, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='Temps d’analyse selon le nombre de workers')
    parser.add_argument('journal', type=Path)
    parser.add_argument('--essais', type=entier_positif, default=3,
                        help='Essais par configuration (défaut : 3)')
    parser.add_argument('--sortie', type=Path, default=Path('resultats'),
                        help='Dossier parent du graphique')
    args = parser.parse_args()
    if not args.journal.is_file():
        parser.error('Le fichier journal est absent ou invalide.')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        parser.error('Matplotlib manque : python -m pip install matplotlib')
    try:
        print(f'{args.essais * len(WORKERS)} analyses prévues.', flush=True)
        resultats = mesurer(args.journal, args.essais)
        dossier = creer_dossier(args.sortie)
        destination = dossier / 'performances.png'
        tracer(resultats, destination, plt,
               f'{args.journal.name} — {args.essais} essai(s) par configuration')
    except (OSError, ValueError) as erreur:
        print(f'Erreur : {erreur}', file=sys.stderr)
        return 1
    print(f'Graphique : {destination}')
    return 0


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
