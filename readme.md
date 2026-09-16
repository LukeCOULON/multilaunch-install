# MultiLaunch

**MultiLaunch** est un launcher de jeux pour Linux, conçu pour centraliser et lancer des jeux natifs Linux ainsi que des jeux utilisant **Wine** ou **Proton**.

Il peut détecter des jeux présents dans plusieurs environnements Linux, notamment Steam, Lutris, Heroic, Bottles et Wine, puis les ajouter à une bibliothèque locale.

---

## ✨ Fonctionnalités

* 🎮 Bibliothèque locale de jeux
* 🔎 Détection automatique des jeux installés
* 🖥️ Interface graphique avec Tkinter
* 🎮 Support des jeux Linux
* 🍷 Support Wine
* ⚙️ Support Proton
* 📦 Détection des installations Steam
* 🦸 Détection des installations Heroic
* 🎮 Détection Lutris
* 🍾 Détection Bottles
* 🔍 Recherche approfondie dans des dossiers sélectionnés
* ▶️ Lancement direct des jeux
* ⚙️ Arguments personnalisés
* 🌎 Variables d'environnement personnalisées
* 🍷 Gestion des préfixes Wine
* 📁 Répertoire de travail personnalisé
* 📋 Logs de lancement et diagnostics
* 🔄 Vérification des mises à jour GitHub
* 🖥️ Raccourci dans le menu des applications Linux
* 💾 Sauvegarde de la bibliothèque locale

---

# 📋 Prérequis

MultiLaunch fonctionne actuellement sur **Linux**.

Il est recommandé d'utiliser une distribution récente.

### Python

Python **3.10 ou supérieur** est recommandé.

Vérifiez votre version :

```bash
python3 --version
```

Exemple :

```text
Python 3.13.x
```

### Tkinter

L'interface graphique utilise **Tkinter**.

Sur les distributions basées sur Arch Linux, comme CachyOS :

```bash
sudo pacman -S python-tk
```

Sur Ubuntu / Debian :

```bash
sudo apt install python3-tk
```

### Wine

Wine n'est nécessaire que pour lancer des jeux Windows avec Wine.

Sur Arch Linux / CachyOS :

```bash
sudo pacman -S wine
```

### Proton

Pour les jeux Steam utilisant Proton, installez Steam et configurez Proton depuis Steam.

---

# 🚀 Installation rapide

La méthode recommandée consiste à cloner le dépôt GitHub puis à lancer `install.py`.

## 1. Installer Git

Si Git n'est pas installé :

```bash
sudo pacman -S git
```

Sur Ubuntu / Debian :

```bash
sudo apt install git
```

---

## 2. Télécharger MultiLaunch

Clonez le dépôt :

```bash
git clone https://github.com/LukeCOULON/multilaunch.git
```

Entrez dans le dossier :

```bash
cd multilaunch
```

---

## 3. Lancer l'installation

Exécutez :

```bash
python3 install.py
```

L'installation se fait dans le dossier personnel de l'utilisateur.

Aucune commande `sudo` n'est nécessaire pour installer MultiLaunch.

---

# ⚡ Installation en une seule commande

Vous pouvez effectuer le téléchargement et l'installation avec :

```bash
git clone https://github.com/LukeCOULON/multilaunch.git && cd multilaunch && python3 install.py
```

---

# ▶️ Lancer MultiLaunch

Après l'installation, MultiLaunch crée la commande :

```bash
~/.local/bin/multilaunch
```

Pour démarrer l'interface graphique :

```bash
~/.local/bin/multilaunch gui
```

Si `~/.local/bin` est présent dans votre `PATH`, vous pouvez simplement utiliser :

```bash
multilaunch gui
```

L'installation crée également un raccourci dans le menu des applications Linux.

---

# 🎮 Utilisation

## Ajouter un jeu manuellement

Depuis l'interface graphique :

1. Cliquez sur **« + Ajouter un jeu »**
2. Sélectionnez le fichier exécutable du jeu
3. Configurez les paramètres nécessaires
4. Ajoutez le jeu à la bibliothèque

Selon le jeu, vous pouvez configurer :

* l'exécutable ;
* la plateforme ;
* Wine ou Proton ;
* le préfixe Wine ;
* les arguments ;
* les variables d'environnement ;
* le répertoire de travail.

---

## 🔎 Détecter les jeux automatiquement

Cliquez sur :

**Détecter**

MultiLaunch recherche les installations connues sur votre système.

Les emplacements pris en charge comprennent notamment :

* Steam
* Steam Play / Proton
* Lutris
* Heroic Games Launcher
* Bottles
* Wine
* dossiers `Games`
* dossiers `games`
* Bureau
* Téléchargements
* certains supports montés

Les résultats détectés peuvent ensuite être importés dans votre bibliothèque.

---

## 📁 Rechercher dans un dossier

Le bouton :

**Chercher dans un dossier**

permet de sélectionner manuellement un dossier dans lequel MultiLaunch recherchera des jeux et exécutables.

Cette méthode est particulièrement utile pour :

* les jeux installés manuellement ;
* les jeux provenant d'autres launchers ;
* les jeux installés sur un autre disque ;
* les installations Wine personnalisées.

---

# 🍷 Jeux Windows avec Wine

MultiLaunch peut lancer des exécutables Windows via Wine.

Un jeu peut être configuré avec :

* un exécutable `.exe` ;
* un préfixe Wine ;
* des arguments ;
* des variables d'environnement ;
* un dossier de travail personnalisé.

Exemple de préfixe :

```text
/home/utilisateur/Games/mon-jeu
```

Le préfixe peut être différent pour chaque jeu.

---

# 🎮 Steam / Proton

Les jeux installés via Steam peuvent être détectés automatiquement.

MultiLaunch recherche notamment dans les répertoires Steam classiques et leurs variantes.

Les installations Proton sont également prises en compte, notamment les dossiers :

```text
steamapps/common/
```

et :

```text
steamapps/compatdata/
```

---

# 🦸 Heroic, Lutris et Bottles

MultiLaunch recherche également les installations provenant de plusieurs gestionnaires de jeux Linux.

### Heroic

Les installations Heroic peuvent être détectées depuis ses répertoires de configuration et de données.

### Lutris

MultiLaunch peut rechercher les jeux enregistrés dans Lutris et ses bases de données.

### Bottles

Les préfixes et installations Bottles peuvent également être analysés.

---

# 💾 Données de MultiLaunch

Les données utilisateur sont stockées dans :

```text
~/Documents/MultiLaunch/
```

La bibliothèque de jeux est enregistrée dans :

```text
~/Documents/MultiLaunch/data.json
```

Les logs sont enregistrés dans :

```text
~/Documents/MultiLaunch/logs/
```

Les informations d'état des mises à jour sont stockées dans :

```text
~/Documents/MultiLaunch/update-state.json
```

Vos données de jeux ne sont donc pas stockées directement dans le dossier du dépôt Git.

---

# 📦 Fichiers installés

Par défaut, le programme est installé dans :

```text
~/MultiLaunch/
```

Les principaux fichiers sont :

```text
launcher.py
gui.py
gamedetector.py
version.json
update.json
```

Le script d'installation crée également :

```text
~/.local/bin/multilaunch
```

et le raccourci graphique :

```text
~/.local/share/applications/multilaunch.desktop
```

---

# 🛠️ Options de install.py

Le script `install.py` possède plusieurs options.

## Installation normale

```bash
python3 install.py
```

## Choisir un dossier d'installation

```bash
python3 install.py --target ~/Applications/MultiLaunch
```

## Tester l'installation sans modifier le système

```bash
python3 install.py --dry-run
```

Cette commande affiche les opérations qui seraient effectuées sans installer les fichiers.

## Désinstaller MultiLaunch

```bash
python3 install.py --uninstall
```

La désinstallation supprime le programme et son raccourci, mais **conserve les données utilisateur**.

Les données restent dans :

```text
~/Documents/MultiLaunch/
```

---

# 🔄 Mise à jour

MultiLaunch possède un système de vérification des mises à jour depuis GitHub.

Depuis l'interface :

**Mises à jour**

Le programme peut vérifier les informations de version du dépôt.

Vous pouvez également récupérer manuellement les dernières modifications :

```bash
cd multilaunch
git pull
python3 install.py
```

---

# 🐛 Dépannage

## `python3: command not found`

Installez Python.

Sur CachyOS / Arch :

```bash
sudo pacman -S python
```

---

## Tkinter n'est pas disponible

Sur CachyOS / Arch :

```bash
sudo pacman -S python-tk
```

Puis relancez :

```bash
python3 install.py
```

---

## `multilaunch: command not found`

Essayez directement :

```bash
~/.local/bin/multilaunch gui
```

Si cela fonctionne, ajoutez `~/.local/bin` à votre `PATH`.

Pour Fish :

```fish
fish_add_path ~/.local/bin
```

Pour Bash :

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## Un jeu n'est pas détecté

Utilisez :

**Chercher dans un dossier**

et sélectionnez directement le dossier d'installation du jeu.

MultiLaunch ignore volontairement certains exécutables qui ressemblent à des installateurs, launchers, outils système ou composants Wine afin de limiter les faux résultats.

---

# 🔐 Sécurité de la détection

La détection automatique ne considère pas automatiquement chaque exécutable trouvé comme un jeu confirmé.

MultiLaunch utilise différentes informations pour identifier les installations et peut signaler certaines découvertes comme nécessitant une vérification.

Cela permet de limiter les faux positifs lors de recherches dans des dossiers contenant de nombreux exécutables.

---

# 📝 Versions

## 0.0.5

* Interface graphique responsive
* Bibliothèque locale
* Détection Steam
* Détection Lutris
* Détection Heroic
* Détection Bottles
* Détection Wine
* Recherche approfondie dans des dossiers
* Import des jeux détectés
* Gestion des préfixes Wine
* Arguments personnalisés
* Variables d'environnement
* Logs
* Diagnostics
* Vérification des mises à jour
* Installation automatique
* Raccourci dans le menu des applications

---

# 📁 Structure du projet

```text
multilaunch/
├── launcher.py
├── gui.py
├── gamedetector.py
├── install.py
├── version.json
├── update.json
└── README.md
```

### `launcher.py`

Contient le moteur principal de MultiLaunch :

* gestion de la bibliothèque ;
* lancement des jeux ;
* configuration Wine/Proton ;
* logs ;
* mises à jour ;
* gestion des données.

### `gui.py`

Contient l'interface graphique Tkinter.

### `gamedetector.py`

Contient le système de détection des jeux et des installations.

### `install.py`

Permet d'installer et désinstaller MultiLaunch.

### `version.json`

Contient les informations de version du programme.

### `update.json`

Contient les notes de version affichées dans l'application.

---

# 👨‍💻 Développeur

**Luke Coulon**

GitHub :

https://github.com/LukeCOULON

Dépôt :

https://github.com/LukeCOULON/multilaunch

---

# 📜 Licence

Le projet est actuellement distribué via son dépôt GitHub.

Consultez les fichiers du dépôt pour connaître les conditions de distribution applicables à la version utilisée.

---

## ⭐ MultiLaunch

Un launcher Linux simple pour regrouper vos jeux et installations **Linux, Wine et Proton** au même endroit.
