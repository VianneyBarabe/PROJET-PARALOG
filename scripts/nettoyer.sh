#!/usr/bin/env bash
# nettoyer.sh — ParaLog (A7)
# Usage : bash scripts/nettoyer.sh N [-y]
#   N  : âge en jours ; les rapports de resultats/ de plus de N jours sont supprimés
#   -y : supprime sans demander de confirmation
# Supprime aussi les fichiers temporaires (__pycache__, *.tmp, *~).
#
# Sécurité : seuls src/, scripts/ et resultats/ sont parcourus.
# data/ et archives/ ne sont JAMAIS touchés.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"

usage() { echo "Usage : bash scripts/nettoyer.sh N [-y]" >&2; }

# 1. Vérification des arguments
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
    exit 1
fi
N="$1"
OPTION="${2:-}"

if ! [[ "$N" =~ ^[0-9]+$ ]]; then
    echo "Erreur : N doit être un nombre de jours, entier positif ou nul (reçu : $N)" >&2
    exit 1
fi
if [ -n "$OPTION" ] && [ "$OPTION" != "-y" ]; then
    echo "Erreur : option inconnue : $OPTION" >&2
    usage
    exit 1
fi

cd "$RACINE" || exit 1

# 2. Liste des fichiers à supprimer (sort -zu : chaque fichier une seule fois)
mapfile -d '' FICHIERS < <(
    {
        # rapports de plus de N jours (N x 1440 minutes)
        find resultats -type f -mmin +$((N * 1440)) -print0
        # fichiers temporaires, quel que soit leur âge
        find src scripts resultats -type f \
            \( -name '*.tmp' -o -name '*~' -o -path '*/__pycache__/*' \) -print0
    } 2>/dev/null | sort -zu
)

if [ "${#FICHIERS[@]}" -eq 0 ]; then
    echo "Rien à nettoyer."
    exit 0
fi

echo "Fichiers à supprimer (${#FICHIERS[@]}) :"
printf '  %s\n' "${FICHIERS[@]}"

# 3. Confirmation, sauf avec -y
if [ "$OPTION" != "-y" ]; then
    read -r -p "Confirmer la suppression ? [o/N] " reponse
    case "$reponse" in
        o|O|oui|OUI) ;;
        *) echo "Annulé, rien n'a été supprimé."; exit 0 ;;
    esac
fi

# 4. Suppression, puis retrait des dossiers devenus vides
rm -f -- "${FICHIERS[@]}"
find resultats -mindepth 1 -type d -empty -delete 2>/dev/null
find src scripts -type d -name __pycache__ -empty -delete 2>/dev/null

echo "Nettoyage terminé : ${#FICHIERS[@]} fichier(s) supprimé(s)."
