#!/usr/bin/env bash
# tester_droits.sh — ParaLog (A3)
# Usage : bash scripts/tester_droits.sh
# Vérifie que les droits du projet respectent le tableau des droits.
# Prérequis : un utilisateur extérieur au groupe (sudo useradd -m testeur)

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1
ok=0
ko=0

# verifier "description" commande... : OK si la commande réussit
verifier() {
    local desc="$1"; shift
    if "$@" > /dev/null 2>&1; then
        echo "[OK] $desc"; ok=$((ok + 1))
    else
        echo "[KO] $desc"; ko=$((ko + 1))
    fi
}

droits()  { [ "$(stat -c '%a' "$1")" = "$2" ]; }           # droits chemin octal
groupe()  { [ "$(stat -c '%G' "$1")" = "paralog" ]; }       # groupe chemin
aucun()   { [ -z "$(find "$@" 2>/dev/null)" ]; }            # find ne renvoie rien
refuse()  { ( cd / && sudo -u testeur "$@" ) 2>&1 | grep -q "Permission denied"; }

echo "=== Droits des dossiers ==="
for d in . src scripts docs resultats; do
    verifier "$d en 2770" droits "$d" 2770
done
verifier "data en 750"     droits data 750
verifier "archives en 700" droits archives 700
for d in . data src scripts docs resultats; do
    verifier "$d appartient au groupe paralog" groupe "$d"
done

echo "=== Droits des fichiers existants ==="
verifier "data/*.log en 640"          aucun data      -type f -name '*.log'    ! -perm 640
verifier "src/*.py en 660"            aucun src       -type f -name '*.py'     ! -perm 660
verifier "scripts/*.sh en 770"        aucun scripts   -type f -name '*.sh'     ! -perm 770
verifier "docs/* en 660"              aucun docs      -type f                  ! -perm 660
verifier "archives/*.tar.gz en 600"   aucun archives  -type f -name '*.tar.gz' ! -perm 600
verifier "aucun droit 777 dans le projet" aucun . -perm 777 ! -type l   # un lien symbolique est toujours en 777 : ignoré

echo "=== Accès d'un utilisateur extérieur (testeur) ==="
if id testeur > /dev/null 2>&1; then
    verifier "testeur ne peut pas lire data/access.log" refuse cat "$RACINE/data/access.log"
    verifier "testeur ne peut pas lister data/"         refuse ls "$RACINE/data"
    verifier "testeur ne peut pas lancer les scripts"   refuse bash "$RACINE/scripts/lancer.sh"
    verifier "testeur ne peut pas lister archives/"     refuse ls "$RACINE/archives"
else
    echo "[--] utilisateur testeur absent : sudo useradd -m testeur"
fi

echo "=== Fichiers créés par un membre du groupe ==="
touch resultats/.test_droits src/.test_droits.py
verifier "un nouveau rapport hérite du groupe paralog (setgid)" groupe resultats/.test_droits
verifier "un nouveau .py hérite du groupe paralog (setgid)"     groupe src/.test_droits.py
verifier "un nouveau .py est en 660 (umask 007)"                droits src/.test_droits.py 660
rm -f resultats/.test_droits src/.test_droits.py

echo "=== Bilan : $ok OK, $ko KO ==="
[ "$ko" -eq 0 ]
