# 🎮 MultiLaunch

**MultiLaunch** est un launcher de jeux pour Linux permettant de regrouper, détecter et lancer facilement ses jeux depuis une interface graphique.

Il est conçu pour fonctionner avec différentes installations de jeux et différents environnements, notamment **Steam, Proton, Wine, Lutris, Heroic Games Launcher et Bottles**.

---

## ✨ Fonctionnalités

* 🎮 Bibliothèque de jeux
* 🔎 Détection automatique des jeux installés
* 📁 Recherche de jeux dans des dossiers personnalisés
* 🖥️ Interface graphique
* ▶️ Lancement des jeux depuis MultiLaunch
* 🍷 Support de Wine
* 🎮 Support de Proton
* 🚂 Détection des jeux Steam
* 🎮 Détection des jeux Lutris
* 🦸 Détection des jeux Heroic
* 🍾 Détection des installations Bottles
* ⚙️ Arguments personnalisés
* 🌎 Variables d'environnement personnalisées
* 📂 Répertoire de travail personnalisé
* 📝 Système de logs
* 🔄 Vérification des mises à jour
* 🖥️ Création d'un raccourci dans le menu des applications
* 💾 Sauvegarde de la bibliothèque

---

# 💻 Prérequis

MultiLaunch est principalement destiné à **Linux**.

### Python

Python 3 est nécessaire.

Vérifiez votre version avec :

```bash
python3 --version
```

Si Python n'est pas installé sur **CachyOS / Arch Linux** :

```bash
sudo pacman -S python
```

### Git

Git est nécessaire pour télécharger le dépôt.

Sur CachyOS / Arch Linux :

```bash
sudo pacman -S git
```

### Tkinter

L'interface graphique utilise Tkinter.

Sur CachyOS / Arch Linux :

```bash
sudo pacman -S tk
```

Sur certaines distributions, le paquet peut être fourni séparément avec Python.

---

# 🚀 Installation

## Méthode recommandée

Téléchargez le dépôt officiel :

```bash
git clone https://github.com/LukeCOULON/multilaunch-install.git
```

Entrez dans le dossier :

```bash
cd multilaunch-install
```

Puis lancez le programme d'installation :

```bash
python3 install.py
```

---

## ⚡ Installation en une seule commande

Vous pouvez effectuer toutes les étapes avec une seule commande :

```bash
git clone https://github.com/LukeCOULON/multilaunch-install.git && cd multilaunch-install && python3 install.py
```

---

# 📦 Que fait `install.py` ?

Le fichier `install.py` automatise l'installation de MultiLaunch.

Il permet notamment de :

1. préparer les fichiers nécessaires ;
2. installer MultiLaunch dans le dossier prévu ;
3. créer les fichiers nécessaires au lancement ;
4. configurer le raccourci de l'application ;
5. préparer le lancement depuis le système.

Cela évite d'avoir à copier manuellement les fichiers ou créer les raccourcis.

### Lancer manuellement l'installateur

Depuis le dépôt :

```bash
python3 install.py
```

---

# ▶️ Lancer MultiLaunch

Une fois l'installation terminée, MultiLaunch peut être lancé depuis le raccourci créé dans le menu des applications.

Vous pouvez également utiliser le lanceur installé si celui-ci est disponible dans votre `PATH`.

---

# 🎮 Utilisation

## 🔎 Détection automatique

MultiLaunch peut rechercher les jeux présents sur votre système.

La détection peut notamment rechercher les installations provenant de :

* Steam
* Proton
* Wine
* Lutris
* Heroic Games Launcher
* Bottles

La détection permet d'éviter d'ajouter manuellement chaque jeu.

---

## 📁 Recherche dans un dossier

Si un jeu n'est pas automatiquement détecté, vous pouvez effectuer une recherche dans un dossier spécifique.

Cette fonction est utile pour les jeux :

* installés manuellement ;
* installés sur un autre disque ;
* utilisant un préfixe Wine personnalisé ;
* provenant d'un launcher non détecté automatiquement.

---

# 🍷 Jeux Windows avec Wine

MultiLaunch peut être utilisé pour lancer des jeux Windows avec Wine.

Vous pouvez notamment configurer :

* l'exécutable `.exe` ;
* le préfixe Wine ;
* les arguments ;
* les variables d'environnement ;
* le dossier de travail.

Exemple de préfixe Wine :

```text
/home/utilisateur/Games/mon-jeu
```

---

# 🎮 Jeux Steam et Proton

Les jeux Steam installés avec Proton peuvent être détectés automatiquement.

Les installations Steam utilisent généralement une structure similaire à :

```text
steamapps/
├── common/
└── compatdata/
```

MultiLaunch peut utiliser ces informations pour identifier les installations de jeux.

---

# ⚙️ Configuration d'un jeu

Pour chaque jeu, il est possible de configurer différents paramètres selon l'installation.

### Exécutable

Chemin vers le programme à lancer.

Exemple :

```text
/home/user/Games/MyGame/game.exe
```

### Arguments

Arguments supplémentaires transmis au programme.

Exemple :

```text
-windowed -novsync
```

### Variables d'environnement

Permet de définir des variables utilisées lors du lancement.

Exemple :

```text
PROTON_LOG=1
```

### Répertoire de travail

Permet de définir le dossier depuis lequel le jeu doit être lancé.

---

# 📝 Logs

MultiLaunch dispose d'un système de logs permettant de suivre les opérations effectuées par le programme.

Les logs peuvent être utiles pour diagnostiquer :

* un jeu qui ne démarre pas ;
* un exécutable introuvable ;
* un problème Wine/Proton ;
* une erreur de configuration ;
* un problème lors de la détection.

---

# 🔄 Mises à jour

Le projet est disponible sur GitHub :

[Dépôt GitHub — MultiLaunch Install](https://github.com/LukeCOULON/multilaunch-install/tree/main?utm_source=chatgpt.com)

Pour récupérer la dernière version du dépôt :

```bash
cd multilaunch-install
git pull
```

Puis relancez l'installation :

```bash
python3 install.py
```

Vous pouvez donc utiliser :

```bash
cd multilaunch-install && git pull && python3 install.py
```

---

# 🐛 Dépannage

## Python n'est pas trouvé

Si vous obtenez :

```text
python3: command not found
```

Installez Python.

### CachyOS / Arch

```bash
sudo pacman -S python
```

Puis vérifiez :

```bash
python3 --version
```

---

## Git n'est pas trouvé

Si vous obtenez :

```text
git: command not found
```

Installez Git :

```bash
sudo pacman -S git
```

---

## Tkinter ne fonctionne pas

Sur CachyOS / Arch :

```bash
sudo pacman -S tk
```

Puis relancez :

```bash
python3 install.py
```

---

## Le jeu n'est pas détecté

Utilisez la fonction de recherche dans un dossier et sélectionnez directement le dossier dans lequel le jeu est installé.

Vérifiez également que l'exécutable du jeu existe réellement.

---

## Le jeu ne se lance pas

Vérifiez :

1. le chemin de l'exécutable ;
2. les permissions du fichier ;
3. la configuration Wine/Proton ;
4. le préfixe utilisé ;
5. les arguments personnalisés ;
6. les logs de MultiLaunch.

Pour rendre un script Linux exécutable :

```bash
chmod +x fichier
```

---

# 📂 Structure du dépôt

```text
multilaunch-install/
│
├── install.py
├── README.md
└── ...
```

Le dépôt **`multilaunch-install`** contient principalement le système permettant d'installer MultiLaunch.

---

# 🧑‍💻 Développement

Le projet est développé par **Luke Coulon**.

GitHub :

[Luke Coulon sur GitHub](https://github.com/LukeCOULON?utm_source=chatgpt.com)

Dépôt :

[LukeCOULON/multilaunch-install](https://github.com/LukeCOULON/multilaunch-install?utm_source=chatgpt.com)

---

# 📜 Licence

Consultez les fichiers du dépôt pour connaître les conditions de licence et de redistribution applicables au projet.

---

# ⭐ MultiLaunch

Un launcher Linux pour **centraliser, détecter et lancer vos jeux** depuis une seule application.

**Steam • Proton • Wine • Lutris • Heroic • Bottles**
