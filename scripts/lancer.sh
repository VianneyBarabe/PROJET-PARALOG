#!/usr/bin/env bash
# lancer.sh — ParaLog (A4)
# Usage : bash scripts/lancer.sh JOURNAL [N]
#   JOURNAL : fichier de journaux à analyser
#   N       : nombre de workers (par défaut : nombre de cœurs, donné par nproc)
# Écrit un rapport horodaté dans resultats/.
#
# Codes de retour :
#   0 succès   1 mauvais usage   2 journal absent ou illisible
#   3 N invalide   4 programme introuvable   5 échec de l'analyse

umask 007   # rapports créés en 660, conformes au tableau des droits

# Racine du projet = dossier parent de scripts/ (pas de chemin absolu)
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
PROGRAMME="$RACINE/src/analyse_par.py"   # à adapter au nom choisi par l'équipe P

usage() { echo "Usage : bash scripts/lancer.sh JOURNAL [N]" >&2; }

# 1. Vérification des arguments
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Erreur : nombre d'arguments incorrect." >&2
    usage
    exit 1
fi

JOURNAL="$1"
N="${2:-$(nproc)}"   # N absent : nombre de cœurs de la machine

if [ ! -f "$JOURNAL" ]; then
    echo "Erreur : journal introuvable : $JOURNAL" >&2
    exit 2
fi
if [ ! -r "$JOURNAL" ]; then
    echo "Erreur : journal illisible (droits insuffisants) : $JOURNAL" >&2
    exit 2
fi
if ! [[ "$N" =~ ^[1-9][0-9]*$ ]]; then
    echo "Erreur : N doit être un entier supérieur ou égal à 1 (reçu : $N)" >&2
    exit 3
fi
if [ ! -f "$PROGRAMME" ]; then
    echo "Erreur : programme d'analyse introuvable : $PROGRAMME" >&2
    exit 4
fi

# 2. Lancement de l'analyse, rapport horodaté dans resultats/
mkdir -p "$RACINE/resultats"
RAPPORT="$RACINE/resultats/rapport_$(date +%Y-%m-%d_%Hh%Mm%S)_${N}w.txt"

# Le programme écrit lui-même le rapport dans le fichier donné par -o
# (et l'affiche aussi à l'écran).
if python3 "$PROGRAMME" "$JOURNAL" "$N" -o "$RAPPORT"; then
    echo "lancer.sh : rapport horodaté dans resultats/$(basename "$RAPPORT")"
else
    rm -f "$RAPPORT"   # pas de rapport incomplet
    echo "Erreur : l'analyse a échoué, aucun rapport écrit." >&2
    exit 5
fi
