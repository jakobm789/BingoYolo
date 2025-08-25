import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import os
import pickle
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
from ultralytics import YOLO

class BingoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bingo Spiel")

        self.state = "initial"
        self.drawn_numbers = set()
        self.bingo_cards = {}
        self.loaded_cards = {}
        self.current_card_number = None
        self.card_window = None
        self.card_canvas = None

        # GUI-Elemente initialisieren
        self.create_initial_widgets()

    def create_initial_widgets(self):
        # Frame für Eingabefelder
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(pady=10, padx=10, fill="x")

        # Eingabefelder und deren Labels
        input_frame = tk.Frame(self.main_frame)
        input_frame.grid(row=0, column=0, sticky="nw")

        header = tk.Label(input_frame, text="BINGO", font=("Arial", 24))
        header.pack(pady=10)

        self.date_label = tk.Label(input_frame, text="Datum des Spiels (TT.MM.JJJJ):")
        self.date_label.pack()
        self.date_entry = tk.Entry(input_frame)
        self.date_entry.pack()

        self.time_label = tk.Label(input_frame, text="Uhrzeit des Spiels (HH:MM):")
        self.time_label.pack()
        self.time_entry = tk.Entry(input_frame)
        self.time_entry.pack()

        self.card_count_label = tk.Label(input_frame, text="Anzahl der Bingo-Karten:")
        self.card_count_label.pack()
        self.card_count_entry = tk.Entry(input_frame)
        self.card_count_entry.pack()

        self.generate_button = tk.Button(input_frame, text="Bingo-Karten generieren", command=self.generate_cards)
        self.generate_button.pack(pady=10)

        self.load_button = tk.Button(input_frame, text="Generierte Karten laden", command=self.load_cards)
        self.load_button.pack(pady=10)

        self.start_game_button = tk.Button(input_frame, text="Spiel starten", command=self.start_game)
        self.start_game_button.pack(pady=10)

    def clear_widgets(self):
        # Entfernt alle Widgets im Root-Fenster
        for widget in self.root.winfo_children():
            widget.destroy()

    def start_game(self):
        if not self.loaded_cards:
            messagebox.showerror("Fehler", "Bitte laden Sie zuerst die generierten Bingo-Karten.")
            return
        # In den Spiel-Zustand wechseln
        self.state = "playing"
        self.clear_widgets()
        self.create_game_widgets()
        
        # Initialisiere die Anzeige der Bingo-Anzahl
        self.update_bingo_counts()

    def create_game_widgets(self):
        # Haupt-Frame für Eingabefelder und Bingo-Status nebeneinander
        game_frame = tk.Frame(self.root)
        game_frame.pack(pady=10, padx=10, fill="x")

        # Zentrierte Überschrift im Haupt-Frame
        self.header = tk.Label(game_frame, text="BINGO Spiel", font=("Arial", 24))
        self.header.pack(pady=10)

        # Eingabe-Frame links
        input_frame = tk.Frame(game_frame)
        input_frame.pack(side="left", anchor="nw", padx=10, pady=10)

        self.ball_label = tk.Label(input_frame, text="Gezogene Zahl:")
        self.ball_label.pack()

        self.ball_entry = tk.Entry(input_frame)
        self.ball_entry.pack()
        self.ball_entry.bind("<Return>", lambda event: self.add_ball())
        self.ball_entry.bind("<KP_Enter>", lambda event: self.add_ball())

        self.add_ball_button = tk.Button(input_frame, text="Zahl bestätigen", command=self.add_ball)
        self.add_ball_button.pack(pady=10)

        self.card_number_label = tk.Label(input_frame, text="Kartennummer zur Überprüfung:")
        self.card_number_label.pack()
        self.card_number_entry = tk.Entry(input_frame)
        self.card_number_entry.pack()
        self.card_number_entry.bind("<Return>", lambda event: self.check_card())
        self.card_number_entry.bind("<KP_Enter>", lambda event: self.check_card())

        self.check_card_button = tk.Button(input_frame, text="Karte prüfen", command=self.check_card)
        self.check_card_button.pack(pady=10)

        # Schaltfläche zum Starten der Kameraerkennung
        self.camera_button = tk.Button(input_frame, text="Kamera starten", command=self.start_camera_detection)
        self.camera_button.pack(pady=10)

        # Status-Frame für den Bingo-Status rechts daneben
        status_frame = tk.Frame(game_frame)
        status_frame.pack(side="right", anchor="n", padx=20, fill="y", expand=True)

        # Platzhalter oben, um Bingo-Status vertikal zu zentrieren
        spacer_top = tk.Frame(status_frame)
        spacer_top.pack(side="top", expand=True)

        self.bingo_status_label = tk.Label(status_frame, text="Bingo-Status:", font=("Arial", 12, "bold"))
        self.bingo_status_label.pack(pady=5)

        self.bingo_counts = [tk.Label(status_frame, text=f"Karten mit {i} Bingo(s): 0") for i in range(6)]
        for label in self.bingo_counts:
            label.pack(anchor="w")

        # Platzhalter unten für Zentrierung
        spacer_bottom = tk.Frame(status_frame)
        spacer_bottom.pack(side="bottom", expand=True)

        # Übersicht über gezogene und nicht gezogene Zahlen
        self.numbers_status = {i: False for i in range(1, 76)}
        self.number_items = {}
        self.display_drawn_numbers()

    def display_drawn_numbers(self):
        # Canvas für die Anzeige der Zahlen als Kreise, Höhe auf 700 erhöht
        self.numbers_canvas = tk.Canvas(self.root, width=500, height=700)
        self.numbers_canvas.pack(pady=20)

        columns = ["B", "I", "N", "G", "O"]
        col_width = 80
        radius = 20
        total_width = len(columns) * col_width
        x_start = (500 - total_width) / 2

        for i, col in enumerate(columns):
            x = x_start + i * col_width + col_width / 2
            y = 20
            self.numbers_canvas.create_text(x, y, text=col, font=("Arial", 16, "bold"))

        for i in range(5):  # Spalten
            for j in range(15):  # Zeilen
                number = i * 15 + j + 1
                x = x_start + i * col_width + col_width / 2
                y = j * (2 * radius + 5) + 50
                circle = self.numbers_canvas.create_oval(
                    x - radius, y - radius, x + radius, y + radius,
                    fill="white", outline="black")
                text = self.numbers_canvas.create_text(x, y, text=str(number), font=("Arial", 12))

                # Event-Bindings für Klicks
                self.numbers_canvas.tag_bind(circle, "<Button-1>", lambda event, num=number: self.on_number_click(num))
                self.numbers_canvas.tag_bind(text, "<Button-1>", lambda event, num=number: self.on_number_click(num))

                self.number_items[number] = (circle, text)

    def add_ball(self):
        try:
            ball = int(self.ball_entry.get())
            if 1 <= ball <= 75 and ball not in self.drawn_numbers:
                self.drawn_numbers.add(ball)
                self.update_number_label(ball)
                self.ball_entry.delete(0, tk.END)
                self.update_displayed_card()
                self.update_bingo_counts()
            else:
                messagebox.showerror("Fehler", "Bitte eine gültige, noch nicht gezogene Zahl zwischen 1 und 75 eingeben.")
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gültige Zahl eingeben.")

    def update_number_label(self, number):
        circle, text = self.number_items[number]
        self.numbers_canvas.itemconfig(circle, fill="lightgreen")

    def reset_number_label(self, number):
        circle, text = self.number_items[number]
        self.numbers_canvas.itemconfig(circle, fill="white")

    def update_bingo_counts(self):
        bingo_counts = [0] * 6  # Zählt Karten mit 0 bis 5 Bingos

        for card_number, card in self.loaded_cards.items():
            bingos = self.is_bingo(card)
            if bingos <= 5:
                bingo_counts[bingos] += 1

        for i in range(6):
            self.bingo_counts[i].config(text=f"Karten mit {i} Bingo(s): {bingo_counts[i]}")

    def is_bingo(self, card):
        bingos = 0
        for row in range(5):
            if all(card[col][row] in self.drawn_numbers for col in range(5)):
                bingos += 1

        for col in range(5):
            if all(card[col][row] in self.drawn_numbers for row in range(5)):
                bingos += 1

        if all(card[i][i] in self.drawn_numbers for i in range(5)):
            bingos += 1
        if all(card[4 - i][i] in self.drawn_numbers for i in range(5)):
            bingos += 1

        return bingos

    def on_number_click(self, number):
        if number in self.drawn_numbers:
            # Bestätigungsdialog anzeigen
            if messagebox.askyesno("Zahl zurücksetzen", f"Möchten Sie die Zahl {number} wirklich als ungezogen markieren?"):
                self.drawn_numbers.remove(number)
                self.numbers_status[number] = False
                self.reset_number_label(number)
                # Aktualisiere die Kartenvorschau, wenn eine Karte ausgewählt ist
                if self.current_card_number:
                    self.update_displayed_card()
        else:
            # Zahl als gezogen markieren
            if messagebox.askyesno("Zahl markieren", f"Möchten Sie die Zahl {number} als gezogen markieren?"):
                self.drawn_numbers.add(number)
                self.numbers_status[number] = True
                self.update_number_label(number)
                # Aktualisiere die Kartenvorschau, wenn eine Karte ausgewählt ist
                if self.current_card_number:
                    self.update_displayed_card()
        
        # Aktualisiere die Bingo-Anzeige nach dem Klick
        self.update_bingo_counts()

    def generate_cards(self):
        try:
            count = int(self.card_count_entry.get())
            if count <= 0:
                messagebox.showerror("Fehler", "Bitte eine Anzahl größer als 0 eingeben.")
                return

            # Datum und Uhrzeit einlesen
            date_str = self.date_entry.get()
            time_str = self.time_entry.get()
            try:
                date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            except ValueError:
                messagebox.showerror("Fehler", "Bitte ein gültiges Datum im Format TT.MM.JJJJ eingeben.")
                return
            try:
                time_obj = datetime.strptime(time_str, "%H:%M")
            except ValueError:
                messagebox.showerror("Fehler", "Bitte eine gültige Uhrzeit im Format HH:MM eingeben.")
                return

            datetime_str = f"{date_str} {time_str}"
            filename = f"Bingo_Karten_{date_str}_{time_str.replace(':', '-')}.pdf"

            # Ordner erstellen, falls er nicht existiert
            output_folder = "Bingo_Karten"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # PDF-Erstellung
            cards_per_page = 6
            total_pages = (count + cards_per_page - 1) // cards_per_page
            c = canvas.Canvas(os.path.join(output_folder, filename), pagesize=A4)
            card_width = A4[0] / 2 - 20 * mm
            card_height = (A4[1] - 50 * mm) / 3

            card_num = 1
            for page in range(total_pages):
                for i in range(cards_per_page):
                    if card_num > count:
                        break
                    card_numbers = self.generate_bingo_card_numbers()
                    # Speichern der Karte für die spätere Auswertung
                    self.bingo_cards[card_num] = card_numbers

                    x_offset = 10 * mm if i % 2 == 0 else A4[0] / 2 + 10 * mm
                    row = i // 2
                    y_offset = A4[1] - ((row + 1) * card_height) - 20 * mm

                    # Verschieben der 2. und 3. Reihe um 5 mm nach unten
                    if row == 0:
                        y_offset += 5 * mm
                    if row == 2:
                        y_offset -= 5 * mm

                    self.draw_bingo_card(c, card_numbers, card_num, datetime_str, x_offset, y_offset, card_width, card_height)
                    card_num += 1
                c.showPage()
            c.save()

            # Speichern der Kartendaten in einer Datei
            with open(os.path.join(output_folder, f"Bingo_Karten_{date_str}_{time_str.replace(':', '-')}.pkl"), 'wb') as f:
                pickle.dump(self.bingo_cards, f)

            messagebox.showinfo("Erfolg", f"Bingo-Karten wurden erfolgreich als {filename} gespeichert.")
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gültige Anzahl eingeben.")

    def load_cards(self):
        # Dialog zum Auswählen der Kartendatei
        file_path = filedialog.askopenfilename(title="Bingo-Karten laden", filetypes=[("Pickle Dateien", "*.pkl")], initialdir="Bingo_Karten")
        if file_path:
            with open(file_path, 'rb') as f:
                self.loaded_cards = pickle.load(f)
            messagebox.showinfo("Erfolg", "Bingo-Karten wurden erfolgreich geladen.")

    def generate_bingo_card_numbers(self):
        card = []
        ranges = [(1,15), (16,30), (31,45), (46,60), (61,75)]
        for r in ranges:
            numbers = random.sample(range(r[0], r[1]+1), 5)
            card.append(numbers)
        return card

    def draw_bingo_card(self, c, card_numbers, card_number, datetime_str, x_offset, y_offset, card_width, card_height):
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(x_offset + card_width / 2, y_offset + card_height - 20, "BINGO")

        date_str, time_str = datetime_str.split()
        c.setFont("Helvetica", 8)
        c.drawString(x_offset + 5, y_offset + card_height - 35, f"Datum: {date_str}")
        c.drawString(x_offset + 5, y_offset + card_height - 45, f"Uhrzeit: {time_str}")

        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(x_offset + card_width - 5, y_offset + card_height - 30, f"Nr. {card_number}")

        cell_size = min(card_width / 5, (card_height - 70) / 5)
        table_top = y_offset + card_height - 70
        x_start = x_offset + (card_width - (cell_size * 5)) / 2
        y = table_top

        c.setFont("Helvetica-Bold", 12)
        columns = ["B", "I", "N", "G", "O"]
        for i, col in enumerate(columns):
            x = x_start + i * cell_size
            c.drawCentredString(x + cell_size / 2, y + cell_size - 30, col)

        c.setFont("Helvetica", 12)
        for row in range(5):
            for col in range(5):
                x = x_start + col * cell_size
                y_pos = y - ((row + 1.25) * cell_size)
                c.rect(x, y_pos, cell_size, cell_size)
                number = card_numbers[col][row]
                c.drawCentredString(x + cell_size / 2, y_pos + cell_size / 2 - 1 * mm, str(number))

    def check_card(self):
        try:
            card_number = int(self.card_number_entry.get())
            if card_number not in self.loaded_cards:
                messagebox.showerror("Fehler", "Die eingegebene Kartennummer ist ungültig.")
                return

            self.current_card_number = card_number  # Speichert die ausgewählte Kartennummer
            self.display_card(card_number)
            
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gültige Kartennummer eingeben.")
        
        self.card_number_entry.delete(0, tk.END)

    def display_card(self, card_number):
        card = self.loaded_cards[card_number]
        bingos = self.is_bingo(card)
        
        # Schließe das vorhandene Fenster, falls es existiert
        if self.card_window and self.card_window.winfo_exists():
            self.card_window.destroy()

        # Neues Fenster zur Anzeige der Karte erstellen
        self.card_window = tk.Toplevel(self.root)
        self.card_window.title(f"Bingo Karte Nr. {card_number}")

        # Canvas zum Zeichnen der Karte
        canvas_width = 300
        canvas_height = 400
        self.card_canvas = tk.Canvas(self.card_window, width=canvas_width, height=canvas_height)
        self.card_canvas.pack()

        # Karte zeichnen
        self.draw_card_on_canvas(card, bingos)

    def update_displayed_card(self):
        if self.card_window and self.card_window.winfo_exists():
            card = self.loaded_cards[self.current_card_number]
            bingos = self.is_bingo(card)
            self.draw_card_on_canvas(card, bingos)

    def draw_card_on_canvas(self, card, bingos):
        """Zeichnet die Karte auf dem Canvas unter Berücksichtigung der gezogenen Zahlen."""
        self.card_canvas.delete("all")  # Lösche vorherige Inhalte auf dem Canvas

        cell_size = 50
        x_start = (300 - cell_size * 5) / 2
        y_start = 50

        # Spaltenüberschriften
        columns = ["B", "I", "N", "G", "O"]
        for i, col in enumerate(columns):
            x = x_start + i * cell_size + cell_size / 2
            y = y_start - 30
            self.card_canvas.create_text(x, y, text=col, font=("Arial", 16, "bold"))

        # Zahlen als Kreise zeichnen
        radius = cell_size / 2 - 5
        for row in range(5):
            for col in range(5):
                x_center = x_start + col * cell_size + cell_size / 2
                y_center = y_start + row * cell_size + cell_size / 2
                number = card[col][row]

                # Überprüfen, ob die Zahl gezogen wurde
                fill_color = "lightgreen" if number in self.drawn_numbers else "white"

                # Kreis zeichnen
                self.card_canvas.create_oval(
                    x_center - radius, y_center - radius,
                    x_center + radius, y_center + radius,
                    fill=fill_color, outline="black"
                )

                # Zahl im Kreis anzeigen
                self.card_canvas.create_text(x_center, y_center, text=str(number), font=("Arial", 12))

        # Anzeige der Anzahl der Bingos
        bingos_text = f"Anzahl der Bingos: {bingos}"
        self.card_canvas.create_text(300 / 2, 400 - 20, text=bingos_text, font=("Arial", 14, "bold"))

    def is_bingo(self, card):
        # Überprüft, wie viele Bingos die Karte hat
        bingos = 0
        # Reihen prüfen
        for row in range(5):
            if all(card[col][row] in self.drawn_numbers for col in range(5)):
                bingos += 1

        # Spalten prüfen
        for col in range(5):
            if all(card[col][row] in self.drawn_numbers for row in range(5)):
                bingos += 1

        # Diagonalen prüfen
        if all(card[i][i] in self.drawn_numbers for i in range(5)):
            bingos += 1
        if all(card[4 - i][i] in self.drawn_numbers for i in range(5)):
            bingos += 1

        return bingos

    def start_camera_detection(self):
        # Neues Fenster für die Kameraerkennung erstellen
        self.camera_window = tk.Toplevel(self.root)
        self.camera_window.title("Kameraerkennung")

        # Fixiere die Größe des Kamera-Fensters
        self.camera_window.geometry("1700x720")
        self.camera_window.resizable(False, False)

        # Hauptframe für das gesamte Fenster
        main_frame = tk.Frame(self.camera_window)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame für die Anzeige
        display_frame = tk.Frame(main_frame)
        display_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Label zum Anzeigen des Videostreams
        self.camera_label = tk.Label(display_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)

        # Frame für die Legende und Informationen
        info_frame = tk.Frame(main_frame, width=420)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y)
        info_frame.pack_propagate(False)  # Verhindert Größenänderung basierend auf Inhalt

        # Legende erstellen
        legend_label = tk.Label(info_frame, text="Legende", font=("Arial", 12, "bold"))
        legend_label.pack(pady=5)

        # Canvas für die Legende (wird in `camera_loop` aktualisiert)
        self.legend_canvas = tk.Canvas(info_frame, width=400, bg="white")
        self.legend_canvas.pack()

        # Label zum Anzeigen der erkannten Informationen
        self.detected_info_label = tk.Label(info_frame, text="", font=("Arial", 14), width=40, wraplength=400, justify="left")
        self.detected_info_label.pack(pady=10)

        # Variable zum Stoppen des Kamera-Threads
        self.stop_camera = False

        # Event zum Schließen des Fensters
        self.camera_window.protocol("WM_DELETE_WINDOW", self.on_camera_window_close)

        # Starten des Kamera-Threads
        self.camera_thread = threading.Thread(target=self.camera_loop)
        self.camera_thread.start()

    def update_legend(self, class_names, color_dict):
        # Entferne vorherige Inhalte der Legende
        self.legend_canvas.delete("all")

        # Zeige alle Klassen an, mit einer speziellen Kategorie für Zahlen
        y = 10  # Startposition für die erste Eintragung
        legend_item_height = 30
        shown_classes = set()
        num_legend_items = 0  # Zähler für die Anzahl der Elemente

        for class_id in sorted(class_names.keys()):
            class_name = class_names[class_id]
            if class_name.isdigit():
                continue  # Überspringe einzelne Ziffern, werden später hinzugefügt
            if class_name not in shown_classes:
                color_rgb = color_dict[class_id]
                color_hex = '#%02x%02x%02x' % color_rgb
                self.legend_canvas.create_rectangle(10, y - 10, 30, y + 10, fill=color_hex, outline='')
                self.legend_canvas.create_text(40, y, text=class_name, anchor='w')
                y += legend_item_height  # Abstand für den nächsten Eintrag
                num_legend_items += 1
                shown_classes.add(class_name)

        # Hinzufügen der Kategorie "Zahlen"
        number_color_hex = '#%02x%02x%02x' % (0, 255, 0)  # Grün
        self.legend_canvas.create_rectangle(10, y - 10, 30, y + 10, fill=number_color_hex, outline='')
        self.legend_canvas.create_text(40, y, text="Zahlen", anchor='w')
        num_legend_items += 1

        # Anpassung der Canvas-Höhe entsprechend der Anzahl der Elemente
        total_height = num_legend_items * legend_item_height + 10
        self.legend_canvas.config(height=total_height)

    def on_camera_window_close(self):
        self.stop_camera = True
        self.camera_window.destroy()

    def camera_loop(self):
        model_path = './model/m.pt'  # Ersetzen Sie diesen Pfad durch den Pfad zu Ihrem Modell
        model = YOLO(model_path)

        confidence_threshold = 0.0  # 50%

        # Klassen aus dem Modell laden
        class_names = model.names  # Dictionary {class_id: class_name}
        sorted_class_ids = sorted(class_names.keys())

        # Farben für die Klassen definieren
        color_list = [
            (255, 0, 0),    # Rot
            (0, 255, 0),    # Grün
            (0, 0, 255),    # Blau
            (255, 255, 0),  # Gelb
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (128, 0, 128),  # Violett
            (255, 165, 0),  # Orange
            (0, 128, 0),    # Dunkelgrün
            (0, 0, 128),    # Dunkelblau
        ]

        # Sicherstellen, dass genügend Farben für alle Klassen vorhanden sind
        num_classes = len(sorted_class_ids)
        if num_classes > len(color_list):
            # Generiere zusätzliche zufällige Farben
            for _ in range(num_classes - len(color_list)):
                color_list.append(
                    (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                )

        # Mappe Klassen-IDs zu Farben, mit einer festen Farbe für Zahlen
        color_dict = {}
        number_color = (0, 255, 0)  # Einheitliche Farbe für alle Zahlen (Grün)
        for idx, class_id in enumerate(sorted_class_ids):
            class_name = class_names[class_id]
            if class_name.isdigit():  # Setze eine feste Farbe für Zahlen
                color_dict[class_id] = number_color
            else:
                color_dict[class_id] = color_list[idx % len(color_list)]

        # Legende aktualisieren
        self.update_legend(class_names, color_dict)

        # Zugriff auf die Webcam (Standardkamera)
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        if not cap.isOpened():
            print("Fehler beim Zugriff auf die Webcam.")
            return  # Beende die Funktion, wenn die Kamera nicht geöffnet werden kann

        while not self.stop_camera:
            ret, frame = cap.read()
            if not ret:
                print("Fehler beim Lesen des Frames.")
                break

            # Objekterkennung auf dem aktuellen Frame
            results = model(frame)

            # Listen für erkannte Objekte
            card_number_digits = []
            bingos_detected = 0
            nr_detected = False

            # Durchlaufe die Erkennungsergebnisse und zeichne Bounding Boxes
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    confidence = box.conf[0]
                    class_id = int(box.cls[0])
                    class_name = class_names[class_id]
                    color_rgb = color_dict[class_id]
                    color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])  # RGB zu BGR für OpenCV

                    if confidence > confidence_threshold:
                        if class_name == 'Diagonal1':  # Diagonale von links oben nach rechts unten
                            # Linie von (x1, y1) nach (x2, y2) zeichnen
                            cv2.line(frame, (x1, y1), (x2, y2), color_bgr, 2)
                            bingos_detected += 1
                        elif class_name == 'Diagonal2':  # Diagonale von rechts oben nach links unten
                            # Linie von (x2, y1) nach (x1, y2) zeichnen
                            cv2.line(frame, (x2, y1), (x1, y2), color_bgr, 2)
                            bingos_detected += 1
                        else:
                            # Zeichne Bounding Box ohne Label
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color_bgr, 2)

                        # Verarbeitung der Erkennungen
                        if class_name == 'Nr.':
                            nr_detected = True
                        elif class_name.isdigit():
                            # Speichere die Ziffern mit ihrer x-Position
                            x_center = (x1 + x2) / 2
                            card_number_digits.append((x_center, class_name))
                        elif class_name == 'Bingo':
                            bingos_detected += 1
                        # Falls Sie weitere spezielle Klassen haben, können Sie hier entsprechende Aktionen hinzufügen


            # Wenn 'Nr.' erkannt wurde, die Kartennummer bestimmen
            color = "black"
            if nr_detected:
                # Sortiere die Ziffern basierend auf ihrer x-Position
                card_number_digits.sort(key=lambda tup: tup[0])
                card_number = ''.join([digit for x, digit in card_number_digits])

                # Überprüfen, ob die Kartennummer gültig ist
                if card_number.isdigit():
                    card_num_int = int(card_number)
                    if card_num_int in self.loaded_cards:
                        card = self.loaded_cards[card_num_int]
                        actual_bingos = self.is_bingo(card)
                        info_text = f"Nr.: {card_number}\nEingetragene Bingos: {bingos_detected}\n"
                        if actual_bingos >= bingos_detected:
                            info_text += "\nAnzahl passt."
                            color = "green"
                        else:
                            info_text += "\nKarte hat weniger Bingos."
                            color = "red"
                    else:
                        info_text = f"Kartennummer {card_number} nicht gefunden."
                else:
                    info_text = "Kartennummer konnte nicht erkannt werden."
            else:
                info_text = "Bitte halten Sie die Kartennummer ins Bild."

            # Aktualisieren der Anzeige
            self.detected_info_label.config(text=info_text, fg=color)

            # Resize Frame für die Anzeige auf 720p
            display_frame = cv2.resize(frame, (1280, 720))

            # Frame in RGB konvertieren und im Tkinter-Fenster anzeigen
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.configure(image=imgtk)

            # Kurze Pause, um GUI-Updates zuzulassen
            self.camera_window.update()

        cap.release()

if __name__ == "__main__":
    root = tk.Tk()
    app = BingoGUI(root)
    root.mainloop()
