
#!/bin/bash

for JOURNAL in data/echantillon_access.log data/access.log; do
    echo "Test de $JOURNAL"

    python3 src/analyse_seq.py "$JOURNAL" > seq.txt || exit 1

    for N in 1 2 4 8; do
        python3 src/analyse_par.py "$JOURNAL" "$N" > par.txt || exit 1

        if diff -q <(grep -v "Temps d'analyse" seq.txt) <(grep -v "Temps d'analyse" par.txt); then
            echo "$N workers : OK"
        else
            echo "$N workers : ERREUR"
            exit 1
        fi
    done
done

rm seq.txt par.txt
echo "Tous les tests sont réussis !"
