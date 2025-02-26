# Advanced Danger Detection System

## Project Summary

The Advanced Danger Detection System is a comprehensive application designed to enhance safety by detecting dangerous objects in real-time using computer vision techniques. It leverages YOLO (You Only Look Once) for object detection and can be configured to use various camera sources, including USB cameras and IP cameras (such as those on mobile phones). The system provides a user-friendly interface built with PyQt5, offering features such as real-time alerts, historical data analysis, and customizable settings. It is designed to be modular, extensible, and adaptable to different environments, making it suitable for both home and commercial use.

## Description du projet proposé

Ce projet propose un système avancé de détection de dangers en temps réel utilisant des techniques de vision par ordinateur. Il utilise YOLO pour la détection d'objets et peut être configuré pour utiliser diverses sources de caméra, y compris les caméras USB et IP. Le système offre une interface conviviale avec des alertes en temps réel, une analyse des données historiques et des paramètres personnalisables, adapté pour une utilisation domestique et commerciale.

## Key Features

- **Real-time Object Detection**: Utilizes YOLO for fast and accurate detection of dangerous objects.
- **Multi-Camera Support**: Supports USB cameras and IP cameras (e.g., mobile phones).
- **Customizable Alerts**: Sends alerts via Telegram and email upon detection of dangerous objects.
- **User-Friendly Interface**: PyQt5-based GUI for easy configuration and monitoring.
- **Historical Data Analysis**: Stores detection data in a SQLite database for analysis and reporting.
- **Configurable Settings**: Allows users to customize detection thresholds, alert settings, and more.
- **Cloud Synchronization**: Option to synchronize data with cloud storage services (AWS, Google Cloud).
- **AI-Based Filtering**: Implements AI-based filtering to reduce false positives.

## Keywords

- Object Detection
- Computer Vision
- PyQt5
- YOLO
- Real-time Alerts
- IP Camera
- USB Camera
- Safety System
- Home Security
- Python
- Deep Learning

## Installation

1. Assurez-vous d'avoir Python 3.8+ installé sur votre système.

2. Clonez ce dépôt ou téléchargez les fichiers.

3. Exécutez le script d'installation :
```bash
python setup.py
```

Ce script va :
- Créer les dossiers nécessaires
- Installer toutes les dépendances requises
- Télécharger les modèles YOLO pré-entraînés

## Configuration

1. Ouvrez `config.json` pour personnaliser :
   - Les seuils de détection
   - Les objets considérés comme dangereux
   - Les paramètres de notification
   - Les options d'enregistrement

2. Pour activer les notifications Telegram :
   - Créez un bot Telegram et obtenez le token
   - Trouvez votre Chat ID
   - Mettez à jour ces informations dans les paramètres de l'application

## Utilisation

1. Lancez l'application :
```bash
python GUI.py
```

2. Interface principale :
   - Onglet "Live Detection" : Surveillance en direct
   - Onglet "Alert History" : Historique des alertes
   - Onglet "Face Recognition" : Gestion des visages connus

3. Fonctions principales :
   - Utilisez le curseur de confiance pour ajuster la sensibilité
   - Activez/désactivez la détection avec le bouton ou Ctrl+D
   - Enregistrez des séquences vidéo manuellement
   - Ajoutez des visages connus dans l'onglet reconnaissance faciale

## Maintenance

- Les logs sont stockés dans le dossier `logs/`
- Les enregistrements vidéo sont dans `recordings/`
- Les visages connus sont sauvegardés dans `known_faces/`
- Les sauvegardes sont dans `backups/`

## Dépendances principales

- OpenCV pour le traitement d'image
- YOLO pour la détection d'objets
- Face Recognition pour l'identification des visages
- PyQt5 pour l'interface graphique
- SQLite pour le stockage des données