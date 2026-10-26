#!/usr/bin/env bash
# installer.sh — ParaLog (A2)
# Usage : bash scripts/installer.sh
# Crée l'arborescence, vérifie les prérequis et pose les droits.
# Relançable sans risque.

set -e

# Racine du projet = dossier parent de scripts/ (pas de chemin absolu)
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
GROUPE="paralog"

# 1. Prérequis
python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' \
    || { echo "Erreur : Python 3.8 ou plus requis" >&2; exit 1; }

for cmd in cut sort uniq head wc tar; do
    command -v "$cmd" > /dev/null || { echo "Erreur : $cmd introuvable" >&2; exit 1; }
done

# 2. Arborescence
mkdir -p "$RACINE"/{data,src,scripts,resultats,archives,docs}

# 3. Groupe de l'équipe
getent group "$GROUPE" > /dev/null || sudo groupadd "$GROUPE"
sudo usermod -aG "$GROUPE" "$USER"
sudo chgrp -R "$GROUPE" "$RACINE"

# 4. Droits
chmod 750 "$RACINE"/{data,src,scripts,resultats,docs}
chmod 700 "$RACINE/archives"

echo "Installation terminée dans $RACINE"
