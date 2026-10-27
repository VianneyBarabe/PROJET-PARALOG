#!/usr/bin/env bash
# archiver.sh — ParaLog (A8)
# Usage : bash scripts/archiver.sh
# Crée dans archives/ une archive .tar.gz horodatée du dossier resultats/,
# lisible du seul propriétaire (600).
#
# Codes de retour : 0 succès   1 rien à archiver   2 échec de l'archivage

umask 077   # l'archive est créée directement en 600, jamais lisible par d'autres

# Racine du projet = dossier parent de scripts/ (pas de chemin absolu)
RACINE="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Vérifications
if [ -z "$(ls -A "$RACINE/resultats" 2>/dev/null)" ]; then
    echo "Erreur : resultats/ est vide ou absent, rien à archiver." >&2
    exit 1
fi
mkdir -p "$RACINE/archives"

# 2. Création de l'archive
ARCHIVE="$RACINE/archives/resultats_$(date +%Y-%m-%d_%Hh%Mm%S).tar.gz"

# -c créer, -z compresser (gzip), -f nom de l'archive
# -C se place dans la racine : l'archive contient "resultats/..." et non un chemin complet
if ! tar -czf "$ARCHIVE" -C "$RACINE" resultats; then
    rm -f "$ARCHIVE"
    echo "Erreur : l'archivage a échoué." >&2
    exit 2
fi

# 3. Droits et vérification
chmod 600 "$ARCHIVE"   # explicite, en plus du umask (exigence A8)

if ! tar -tzf "$ARCHIVE" > /dev/null; then   # -t : relit l'archive pour vérifier qu'elle est intacte
    echo "Erreur : l'archive créée est illisible." >&2
    exit 2
fi

NB=$(tar -tzf "$ARCHIVE" | grep -vc '/$')    # nombre de fichiers archivés (hors dossiers)
echo "Archive créée : archives/$(basename "$ARCHIVE") ($NB fichiers, $(du -h "$ARCHIVE" | cut -f1))"
