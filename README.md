dl_decode_pmepmi : Décoder les trames des compteurs PME/PMI, rendre accessible les valeurs via API WEB

# Installation :
```bash
# en tant que root :
apt-get install python-serial python-flask  [...]
mkdir /opt/api_pmepmi/
cd /opt/api_pmepmi
git clone https://github.com/Liberasys/dl_decode_pmepmi.git
cd dl_decode_pmepmi/
chmod 755 api_pmepmi.py
./chmod 755 api_pmepmi.py
```
# Utilisation :
obtenir une donnée unitaire (remplacer TARIF et ETIQUETTE) : http://127.0.0.1:5000/get_donnee?tarif=TARIF&etiquette=ETIQUETTE
obtenir l'interpretation complete des trames : http://127.0.0.1:5000/get_interpretation
