#!/usr/bin/env bash
# controle.sh — ParaLog (A5)
# Usage : bash scripts/controle.sh JOURNAL
# Recalcule les indicateurs 1 et 2 avec les seules commandes du cours,
# reliées par des tubes, pour vérifier les nombres du programme Python.

umask 007          # fichier créé en 660, conforme au tableau des droits
export LC_ALL=C    # tri plus rapide et identique sur toutes les machines

RACINE="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Vérification de l'argument
if [ $# -ne 1 ]; then
    echo "Usage : bash scripts/controle.sh JOURNAL" >&2
    exit 1
fi
JOURNAL="$1"
if [ ! -r "$JOURNAL" ]; then
    echo "Erreur : journal introuvable ou illisible : $JOURNAL" >&2
    exit 2
fi

# 2. Calcul, résultats enregistrés par redirection (> crée, >> ajoute)
mkdir -p "$RACINE/resultats"
SORTIE="$RACINE/resultats/controle_$(date +%Y-%m-%d_%Hh%Mm%S).txt"

echo "=== Nombre de lignes du journal ===" > "$SORTIE"
wc -l < "$JOURNAL" >> "$SORTIE"

echo "=== 1. Requêtes par code HTTP (9e champ) ===" >> "$SORTIE"
cut -d' ' -f9 "$JOURNAL" | sort | uniq -c >> "$SORTIE"

echo "=== 2. Top 10 des adresses IP (1er champ) ===" >> "$SORTIE"
cut -d' ' -f1 "$JOURNAL" | sort | uniq -c | sort -rn | head -10 >> "$SORTIE"

# 3. Affichage
cat "$SORTIE"
echo "Contrôle enregistré dans resultats/$(basename "$SORTIE")"
