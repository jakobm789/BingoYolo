import os
import random
import shutil

# Verzeichnisse für Bilder und Labels
image_dir = './datasets/dataset2/images'
label_dir = './datasets/dataset2/labels'

# Verzeichnisse für die Ausgabe
train_image_dir = './datasets/dataset2/train/images'
train_label_dir = './datasets/dataset2/train/labels'
val_image_dir = './datasets/dataset2/val/images'
val_label_dir = './datasets/dataset2/val/labels'

# Erstelle die Zielverzeichnisse falls sie nicht existieren
os.makedirs(train_image_dir, exist_ok=True)
os.makedirs(train_label_dir, exist_ok=True)
os.makedirs(val_image_dir, exist_ok=True)
os.makedirs(val_label_dir, exist_ok=True)

# Hole alle Bilddateinamen und mische sie zufällig
image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]
random.shuffle(image_files)

# Definiere Split-Ratio für Training und Validierung
split_ratio = 0.8
split_index = int(len(image_files) * split_ratio)

# Splitte in Trainings- und Validierungssets
train_files = image_files[:split_index]
val_files = image_files[split_index:]

# Funktion zum Verschieben von Dateien in die Zielordner
def move_files(file_list, target_image_dir, target_label_dir):
    for image_file in file_list:
        label_file = image_file.replace('.jpg', '.txt')
        # Überprüfe, ob das Label existiert
        if os.path.exists(os.path.join(label_dir, label_file)):
            # Verschiebe Bild und Label in das Zielverzeichnis
            shutil.move(os.path.join(image_dir, image_file), os.path.join(target_image_dir, image_file))
            shutil.move(os.path.join(label_dir, label_file), os.path.join(target_label_dir, label_file))
        else:
            print(f"Label für {image_file} nicht gefunden, Datei wird übersprungen.")

# Verschiebe die Dateien
move_files(train_files, train_image_dir, train_label_dir)
move_files(val_files, val_image_dir, val_label_dir)

print("Datensätze wurden erfolgreich aufgeteilt in Training und Validierung.")
