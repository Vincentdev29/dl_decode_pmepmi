dl_decode_pmepmi : Décoder les trames des compteurs PME/PMI, rendre accessible les valeurs via API WEB

# Installation :
```bash
# en tant que root :
apt-get install python-serial python-flask  [...]
cd /opt/
git clone https://github.com/Liberasys/dl_decode_pmepmi.git
cd dl_decode_pmepmi/
chmod 755 api_pmepmi.py
./chmod 755 api_pmepmi.py
```

# Configuration :
Voir fichier de référence : api_pmepmi.conf

# Utilisation :
obtenir une donnée unitaire (remplacer TARIF et ETIQUETTE) : http://127.0.0.1:5000/get_donnee?tarif=TARIF&etiquette=ETIQUETTE
obtenir l'interpretation complete des trames : http://127.0.0.1:5000/get_interpretation

# Lancement automatique par systemd :
cat << 'EOF' > /etc/systemd/system/apipmepmi.service
[Unit]
Description=API pour compteur PME/PMI
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/opt/dl_decode_pmepmi
ExecStart=/usr/bin/python ./api_pmepmi.py

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable apipmepmi
systemctl start apipmepmi
