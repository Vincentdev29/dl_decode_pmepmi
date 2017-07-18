#!/usr/bin/python
# Droits d'auteur : HUSSON CONSULTING SAS - Liberasys
# 2016/09
# Donne en licence selon les termes de l EUPL V.1.1 (EUPL : European Union Public Licence)
# Voir EUPL V1.1 ici : http://ec.europa.eu/idabc/eupl.html

import serial
import threading
import string
import syslog
import sys
import copy
import signal
import atexit
from pid import PidFile

import urllib
from flask import Flask, request, jsonify, url_for, redirect, escape

from decode_pmepmi import LecturePortSerie
from decode_pmepmi import LectureFichier
from decode_pmepmi import DecodeCompteurPmePmi
from decode_pmepmi import InterpretationTramesPmePmi
from decode_pmepmi import SortieFichier
from pickler import PicklesMyData




########################################################################
# MAIN
########################################################################

chemin_sauvegarde_interpretation = "/opt/api_pmepmi/sauvegarde_etat.pkl"
periode_sauvegarde = 600 # nbr de secondes entre deux sauvegardes

# parametrage sortie syslog
syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

# chemin du fichier contenant le PID
chemin_fichier_pid = "/run/api_pmepmi.pid"

# activer la sortie fichier ou non
sortie_fichier_active = True

# mode de fonctionnement : simulateur ou compteur
mode_fonctionnement = "compteur"

decode_pmepmi = DecodeCompteurPmePmi()
pickles_etat = PicklesMyData(chemin_sauvegarde_interpretation, periode_sauvegarde)
interpreteur_trames = InterpretationTramesPmePmi()
app = Flask(__name__)


# contexte du demon et fichier de PID
with PidFile(pidname="api_pmepmi"):
    def shut_my_app_down(signum, frame):
        """ Arrete proprement l'application """
        print 'Signal handler called with signal', signum
        lecture_serie.close()
        pickles_etat.stop()
        pickles_etat.get_and_pickles_data()
        pickles_etat.close()
        #print("Application erretee, exit 0")
        sys.exit(0)

    signal.signal(signal.SIGHUP, shut_my_app_down)
    signal.signal(signal.SIGINT, shut_my_app_down)
    signal.signal(signal.SIGTERM, shut_my_app_down)

    try:
        print("Initialisation du port serie")
        syslog.syslog(syslog.LOG_INFO, "Initialisation du port serie")
        if mode_fonctionnement == "compteur":
            lien_serie = serial.Serial(port = '/dev/ttyUSB0',
                                       baudrate = 1200,
                                       bytesize=serial.SEVENBITS,
                                       parity=serial.PARITY_EVEN,
                                       stopbits=serial.STOPBITS_ONE,
                                       xonxoff=False,
                                       rtscts=False,
                                       dsrdtr=False,
                                       timeout=1)
        elif mode_fonctionnement == "simulateur":
            lien_serie = serial.Serial(port = '/dev/ttyACM0',
                                       baudrate = 115200,
                                       bytesize=serial.SEVENBITS,
                                       parity=serial.PARITY_EVEN,
                                       stopbits=serial.STOPBITS_ONE,
                                       xonxoff=False,
                                       rtscts=False,
                                       dsrdtr=False,
                                       timeout=1)
        else:
            raise Exception("Mauvais mode de fonctionnement : " + mode_fonctionnement)
        print("Port serie initialise")
        syslog.syslog(syslog.LOG_INFO, "Port serie initialise")
    except serial.SerialException, e:
        print("Probleme avec le port serie : " + str(e) + ", arret du programme")
        syslog.syslog(syslog.LOG_WARNING, "Probleme avec le port serie : " + str(e) + "arret du programme")
        exit(1)
    
    # Instanciation sortie fichier si besoin
    if sortie_fichier_active == True:
        sortie_fichier = SortieFichier()
    
    
    # Callback appele quand un octet est recu
    def cb_nouvel_octet_recu(octet_recu):
        decode_pmepmi.nouvel_octet(serial.to_bytes(octet_recu))
        if sortie_fichier_active == True:
            sortie_fichier.nouvel_octet(serial.to_bytes(octet_recu))
    
    # Callback debut interruption
    def cb_debut_interruption():
        print("INTERRUPTION DEBUT !!!!!!")
        interpreteur_trames.incrementer_compteur_interruptions()
    
    # callback fin interruption
    def cb_fin_interruption():
        dump_interruption = decode_pmepmi.get_tampon_interruption()
        print("Dump interruption : ")
        print(dump_interruption)
        syslog.syslog(syslog.LOG_NOTICE, 'Interruption :')
        syslog.syslog(syslog.LOG_NOTICE, dump_interruption)
        print("INTERRUPTION FIN")
    
    # callback mauvaise trame recue
    def cb_mauvaise_trame_recue():
        print("Trame invalide recue")
        syslog.syslog(syslog.LOG_NOTICE, "Trame invalide recue")
        interpreteur_trames.incrementer_compteur_trames_invalides()
    
    # Callback pour la sauvegarde d'etats
    def cb_sauvegarde_etat():
        return interpreteur_trames.get_dict_interpretation()
    
    # affectation des callbacks :
    decode_pmepmi.set_cb_nouvelle_trame_recue_tt_trame(interpreteur_trames.interpreter_trame)
    decode_pmepmi.set_cb_debut_interruption(cb_debut_interruption)
    decode_pmepmi.set_cb_fin_interruption(cb_fin_interruption)
    decode_pmepmi.set_cf_mauvaise_trame_recue(cb_mauvaise_trame_recue)
    pickles_etat.set_callback(cb_sauvegarde_etat)
        
    # lecture de l'etat sauvegarde et demarrage de la sauvegarde periodique :
    etat_sauve = pickles_etat.get_data()
    if etat_sauve != None :
        interpreteur_trames.charger_etat_interpretation(pickles_etat.get_data())
    pickles_etat.start()
    
    # Lecture sur port serie
    lecture_serie = LecturePortSerie(lien_serie, cb_nouvel_octet_recu)
    lecture_serie.start()
    
    # parametrage API
    @app.errorhandler(404)
    def page_not_found(error):
        texte = ""
        url = request.url + "zabbix_autoconf"
        description = "autoconfiguration Zabbix (LLD) - parametre optionnel : type (int, float, char, text, log)"
        texte = texte + "<a href=" + url + ">" + url + "</a>" + "   :: " + description + "<br/>"
        url = request.url + "get_donnee?tarif=INDEP_TARIF&etiquette=ID_COMPTEUR"
        description = "obtenir une donnee unitaire"
        texte = texte + "<a href=" + url + ">" + url + "</a>" + "   :: " + description + "<br/>"
        url = request.url + "get_interpretation"
        description = "obtenir l'interpretation complete des trames"
        texte = texte + "<a href=" + url + ">" + url + "</a>" + "   :: " + description + "<br/>"
        return texte
    
    # API autoconfiguration Zabbix (LLD)
    @app.route('/zabbix_autoconf', methods = ['GET'])
    def api_cptpmepmi__zabbix_autoconf():
        if 'type' in request.args :
            zabbix_type_donnee = request.args['type']
        else:
            zabbix_type_donnee = ""
        return jsonify(interpreteur_trames.get_autoconf_zabbix(zbx_type = zabbix_type_donnee))
    
    # API de recuperation d'une donnee
    @app.route('/get_donnee', methods = ['GET'])
    def api_cptpmepmi__get_donnee():
        retour = ()
        if 'tarif' in request.args and 'etiquette' in request.args :
            retour = interpreteur_trames.get_donnee(request.args['tarif'],request.args['etiquette'])
            if retour == (None, None):
                return ""
            else:
                return retour[0]
        else:
            return "Donner les bons parametres : tarif=, etiquette="
    
    # API d'obtention d'un dump du dictionnaire d'interpretation des trames
    @app.route('/get_interpretation', methods = ['GET'])
    def api_cptpmepmi__get_dict_interpretation_trame():
        return jsonify(interpreteur_trames.get_dict_interpretation())
    
    # lancement API
    app.run(debug=False)
    




## Configuration Zabbix pour l'API du compteur pmepmi
#UserParameter=custom.discovery.apipmepmi[*],/usr/bin/curl --silent "http://127.0.0.1:5000/zabbix_autoconf?type=$1"
#UserParameter=custom.api.datalogging.pmepmi[*],/usr/bin/curl --silent "http://127.0.0.1:5000/get_donnee?tarif=$1&etiquette=$2"

