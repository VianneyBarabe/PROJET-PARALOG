import argparse
import re
import sys
from collections import Counter
from datetime import date
from functools import lru_cache
from ipaddress import ip_address
from pathlib import Path
from time import perf_counter


CHAINE = r'((?:[^"\\\r\n]|\\.)*)'
FORMAT_LOG = re.compile(
    r'^(\S+) (\S+) (\S+) \['
    r'(\d{2}/[A-Za-z]{3}/\d{4}):(\d{2}):(\d{2}):(\d{2}) '
    r'([+-]\d{4})\] "' + CHAINE + r'" ([1-5]\d{2}) (\d+|-) "'
    + CHAINE + r'" "' + CHAINE + r'"\s*$'
)
MOIS = {m: n for n, m in enumerate(
    ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'), 1
)}

def entier_positif(texte):
    try:
        nombre = int(texte)
    except ValueError:
        raise argparse.ArgumentTypeError("Il faut un entier positif.")

    if nombre < 1:
        raise argparse.ArgumentTypeError("Le nombre doit être supérieur à 0.")

    return nombre

@lru_cache(maxsize=512)
def date_iso(texte):
    """Valider la date sans dépendre de la langue du système."""
    jour, mois, annee = texte.split('/')
    return date(int(annee), MOIS[mois], int(jour)).isoformat()


@lru_cache(maxsize=65536)
def verifier_ip(texte):
    ip_address(texte)


def extraire(ligne):
    """Valider une ligne entière avant de modifier les compteurs."""
    correspondance = FORMAT_LOG.fullmatch(ligne)
    if correspondance is None:
        raise ValueError('format Apache combined invalide')
    (ip, identite, utilisateur, jour, h, minute, seconde, fuseau,
     requete, code, taille, referent, agent) = correspondance.groups()

    verifier_ip(ip)
    jour = date_iso(jour)
    heure = int(h)
    if heure > 23 or int(minute) > 59 or int(seconde) > 59:
        raise ValueError('heure invalide')
    if int(fuseau[1:3]) > 23 or int(fuseau[3:]) > 59:
        raise ValueError('fuseau invalide')

    morceaux = requete.split()
    if len(morceaux) != 3:
        raise ValueError('requête incomplète')
    methode, page, protocole = morceaux
    if not re.fullmatch(r'[A-Z]+', methode):
        raise ValueError('méthode invalide')
    if not re.fullmatch(r'HTTP/\d+(?:\.\d+)?', protocole):
        raise ValueError('protocole invalide')

    return (ip, jour, heure, h + ':' + minute + ':' + seconde, fuseau,
            methode, page, protocole, int(code),
            None if taille == '-' else int(taille), referent, agent)


def top(compteur, limite=10):
    """Ordre stable en cas d'égalité : clé alphabétique croissante."""
    return sorted(compteur.items(), key=lambda couple: (-couple[1], couple[0]))[:limite]


def analyser(chemin, filtre_date=None):
    stats = {nom: Counter() for nom in (
        'codes', 'ips', 'pages', 'heures', 'produits', 'methodes',
        'protocoles', 'referents', 'agents', 'erreurs_pages', 'jours',
        'jours_heures', 'fuseaux'
    )}
    stats.update(lues=0, valides=0, ignorees=0, hors_date=0,
                 retenues=0, octets=0, tailles_inconnues=0,
                 premier=None, dernier=None)
    debut = perf_counter()
    with chemin.open('r', encoding='utf-8', errors='surrogateescape') as fichier:
        for ligne in fichier:
            stats['lues'] += 1
            try:
                if re.search(r'[\udc80-\udcff]', ligne):
                    raise ValueError('encodage UTF-8 invalide')
                donnees = extraire(ligne)
            except (ValueError, KeyError, OverflowError):
                stats['ignorees'] += 1
                continue

            stats['valides'] += 1
            (ip, jour, heure, horloge, fuseau, methode, page,
             protocole, code, taille, referent, agent) = donnees
            if filtre_date and jour != filtre_date:
                stats['hors_date'] += 1
                continue

            stats['retenues'] += 1
            for nom, valeur in (
                ('codes', code), ('ips', ip), ('pages', page),
                ('heures', heure), ('methodes', methode),
                ('protocoles', protocole), ('referents', referent),
                ('agents', agent), ('jours', jour),
                ('jours_heures', (jour, heure)), ('fuseaux', fuseau)
            ):
                stats[nom][valeur] += 1

            if page.split('?', 1)[0].startswith('/produits/'):
                stats['produits'][page] += 1
            if code >= 400:
                stats['erreurs_pages'][page] += 1
            if taille is None:
                stats['tailles_inconnues'] += 1
            else:
                stats['octets'] += taille

            instant_local = jour + ' ' + horloge
            if stats['premier'] is None or instant_local < stats['premier']:
                stats['premier'] = instant_local
            if stats['dernier'] is None or instant_local > stats['dernier']:
                stats['dernier'] = instant_local

    stats['duree'] = perf_counter() - debut
    return stats


def rapport(stats, filtre_date=None):
    lignes = ['JOURNAL — RAPPORT D’ANALYSE WEB', '=' * 60]

    def section(titre):
        lignes.extend(['', titre, '-' * len(titre)])

    def tableau(compteur, limite=10, trier_cle=False):
        valeurs = sorted(compteur.items()) if trier_cle else top(compteur, limite)
        if not valeurs:
            lignes.append('Aucune donnée.')
        for cle, nombre in valeurs:
            lignes.append('{} : {}'.format(cle, nombre))

    n = stats['retenues']
    section('SYNTHÈSE')
    lignes.extend([
        'Date sélectionnée : ' + (filtre_date or 'toutes les dates du fichier'),
        'Lignes lues : {}'.format(stats['lues']),
        'Lignes valides analysées : {}'.format(stats['valides']),
        'Lignes ignorées car mal formées : {}'.format(stats['ignorees']),
        'Lignes valides hors date sélectionnée : {}'.format(stats['hors_date']),
        'Requêtes retenues pour les statistiques : {}'.format(n),
        'IP distinctes (pas un nombre de visiteurs) : {}'.format(len(stats['ips'])),
        'Pages/cibles distinctes : {}'.format(len(stats['pages'])),
        'Première date/heure locale observée : {}'.format(stats['premier'] or '-'),
        'Dernière date/heure locale observée : {}'.format(stats['dernier'] or '-'),
        'Fuseaux présents : ' + (', '.join(sorted(stats['fuseaux'])) or '-'),
        'Les heures sont celles inscrites dans les logs, sans conversion.',
        'Une absence de requêtes ne prouve pas que la collecte couvre 24 h.',
    ])
    section('1. REQUÊTES PAR CODE HTTP')
    tableau(stats['codes'], trier_cle=True)
    section('2. LES 10 ADRESSES IP LES PLUS ACTIVES')
    tableau(stats['ips'])
    section('3. LES 10 PAGES LES PLUS DEMANDÉES')
    tableau(stats['pages'])
    section('4. REQUÊTES PAR HEURE (24 TRANCHES)')
    if len(stats['jours']) > 1:
        lignes.append('Cumul de toutes les dates retenues ; détail par jour plus bas.')
    for heure in range(24):
        lignes.append('{:02d}h : {}'.format(heure, stats['heures'][heure]))

    section('PRODUITS LES PLUS DEMANDÉS (TOP 10)')
    tableau(stats['produits'])
    section('MÉTHODES HTTP')
    tableau(stats['methodes'], trier_cle=True)
    section('PROTOCOLES HTTP')
    tableau(stats['protocoles'], trier_cle=True)
    section('ERREURS HTTP')
    erreurs_client = sum(nb for code, nb in stats['codes'].items() if 400 <= code < 500)
    erreurs_serveur = sum(nb for code, nb in stats['codes'].items() if 500 <= code < 600)
    taux = 100 * (erreurs_client + erreurs_serveur) / n if n else 0
    lignes.extend([
        'Réponses 4xx : {}'.format(erreurs_client),
        'Réponses 5xx : {}'.format(erreurs_serveur),
        'Part des réponses 4xx/5xx : {:.2f} %'.format(taux),
        'Pages/cibles avec le plus de réponses 4xx/5xx :',
    ])
    tableau(stats['erreurs_pages'])
    section('VOLUME DES RÉPONSES')
    lignes.extend([
        'Octets déclarés connus : {}'.format(stats['octets']),
        'Volume connu en Mio : {:.2f}'.format(stats['octets'] / 1024**2),
        'Tailles non renseignées (-) : {}'.format(stats['tailles_inconnues']),
        'Le champ taille ne mesure pas tout le trafic réseau (en-têtes exclus).',
    ])
    section('RÉFÉRENTS DÉCLARÉS (TOP 10 ; - = NON RENSEIGNÉ)')
    tableau(stats['referents'])
    section('USER-AGENTS DÉCLARÉS (TOP 10)')
    tableau(stats['agents'])
    lignes.append('Ces chaînes sont déclaratives : elles ne prouvent pas une identité.')
    section('RÉPARTITION PAR DATE')
    tableau(stats['jours'], trier_cle=True)
    if len(stats['jours']) > 1:
        for jour in sorted(stats['jours']):
            section('HEURES DU ' + jour)
            for heure in range(24):
                lignes.append('{:02d}h : {}'.format(heure, stats['jours_heures'][(jour, heure)]))
    section('TEMPS')
    lignes.append("Temps d'analyse : {:.6f} secondes".format(stats['duree']))
    lignes.append('Mesure : lecture, validation et comptage ; écriture du rapport exclue.')
    return '\n'.join(lignes) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('journal', type=Path, help='Fichier de logs Apache combined')
    parser.add_argument('-o', '--sortie', type=Path, default=Path('resultats/JOURNAL.txt'),
                        help='Rapport à créer (défaut : resultats/JOURNAL.txt)')
    parser.add_argument('--date', help='Date locale à retenir, format AAAA-MM-JJ')
    args = parser.parse_args()
    if args.date:
        try:
            if date.fromisoformat(args.date).isoformat() != args.date:
                raise ValueError()
        except ValueError:
            parser.error('--date doit être une date valide au format AAAA-MM-JJ')
    try:
        if args.journal.resolve() == args.sortie.resolve():
            parser.error('Le rapport doit être différent du fichier de logs.')
        if args.sortie.exists() and args.journal.samefile(args.sortie):
            parser.error('Le rapport et les logs désignent le même fichier.')
        stats = analyser(args.journal, args.date)
        texte = rapport(stats, args.date)
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(texte, encoding='utf-8')
    except OSError as erreur:
        print('Erreur de lecture/écriture : {}'.format(erreur), file=sys.stderr)
        return 1
    print('\nRapport enregistré dans : {}'.format(args.sortie), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
