import cv2
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import time
import threading

# Variabili di controllo
is_paused = False
stop_processing = False
MAX_IMAGES_PER_SCENE = 5  # Limite di immagini per scena
MIN_TIME_BETWEEN_FRAMES = 30  # Numero minimo di fotogrammi tra il salvataggio di immagini
MIN_CONTOUR_AREA = 1500  # Dimensione minima del contorno per essere considerato "umano"

# Sottrattore dello sfondo
fgbg = cv2.createBackgroundSubtractorMOG2()

# Variabile globale per l'ultima immagine salvata
last_saved_image = None

# Funzione per rilevare oggetti in movimento e identificare possibili figure umane
def detect_humans(frame):
    fgmask = fgbg.apply(frame)
    contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    human_contours = []
    
    for contour in contours:
        # Filtra per area minima del contorno
        if cv2.contourArea(contour) > MIN_CONTOUR_AREA:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h)
            
            # Filtra ulteriormente per il rapporto larghezza/altezza (ad es. tra 0.3 e 0.9 potrebbe indicare una figura umana)
            if 0.3 < aspect_ratio < 0.9:
                human_contours.append(contour)
    
    return human_contours

# Funzione per processare il video
def process_video(video_path, output_dir):
    global is_paused, stop_processing, last_saved_image

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    frame_count = 0
    saved_frames = 0
    last_frame_time = 0  # Per tenere traccia dell'ultimo frame salvato
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    start_time = time.time()
    
    while cap.isOpened():
        if stop_processing:
            break
        
        if is_paused:
            time.sleep(0.1)  # Attesa quando in pausa
            continue
        
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        human_contours = detect_humans(frame)
        
        if human_contours:
            if frame_count - last_frame_time >= MIN_TIME_BETWEEN_FRAMES:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                frame_filename = os.path.join(output_dir, f'frame_{frame_count:04d}_{timestamp}.jpg')
                
                # Disegna una cornice verde acido sui contorni rilevati
                for contour in human_contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Cornice verde acido
                
                cv2.imwrite(frame_filename, frame)
                last_saved_image = frame_filename  # Salva il percorso dell'ultima immagine
                update_preview()  # Aggiorna l'anteprima immediatamente
                saved_frames += 1
                last_frame_time = frame_count  # Aggiorniamo il tempo dell'ultimo frame salvato
        
        progress = (frame_count / total_frames) * 100
        progress_bar['value'] = progress
        
        current_time = frame_count / fps
        time_elapsed = time.time() - start_time
        frames_remaining = total_frames - frame_count
        estimated_time_remaining = (time_elapsed / frame_count) * frames_remaining if frame_count > 0 else 0
        
        current_time_label.config(text=f"Tempo corrente: {int(current_time)} s")
        remaining_time_label.config(text=f"Tempo stimato rimanente: {int(estimated_time_remaining)} s")
        
        root.update_idletasks()
    
    cap.release()
    if not stop_processing:
        messagebox.showinfo("Elaborazione completata", f"{saved_frames} fotogrammi salvati nella cartella {output_dir}")
    else:
        messagebox.showinfo("Elaborazione interrotta", "L'elaborazione è stata interrotta dall'utente.")
    
    update_preview()  # Aggiorna l'anteprima alla fine dell'elaborazione

# Funzione per aggiornare l'anteprima
def update_preview():
    global last_saved_image
    if last_saved_image:
        img = Image.open(last_saved_image)
        img.thumbnail((300, 300), Image.LANCZOS)  # Usa LANCZOS per ridimensionare
        img = ImageTk.PhotoImage(img)
        preview_label.config(image=img)
        preview_label.image = img
    else:
        # Mostra l'immagine predefinita (lente di ingrandimento)
        img = Image.new("RGB", (300, 300), "#e0e0e0")  # Sfondo grigio chiaro
        draw = ImageDraw.Draw(img)
        draw.ellipse((100, 100, 200, 200), outline="black", width=5)  # Lente di ingrandimento
        draw.line((150, 150, 250, 250), fill="black", width=5)  # Manico della lente
        img = ImageTk.PhotoImage(img)
        preview_label.config(image=img)
        preview_label.image = img

# Funzioni per la GUI
def select_input_file():
    video_path = filedialog.askopenfilename(
        title="Seleziona il file video",
        filetypes=[("Video Files", "*.mp4 *.h265 *.avi *.mkv *.mov")]
    )
    input_entry.delete(0, tk.END)
    input_entry.insert(0, video_path)

def select_output_folder():
    output_dir = filedialog.askdirectory(title="Seleziona la cartella di destinazione")
    output_entry.delete(0, tk.END)
    output_entry.insert(0, output_dir)

def start_processing():
    global is_paused, stop_processing
    is_paused = False
    stop_processing = False

    video_path = input_entry.get()
    output_dir = output_entry.get()
    
    if not video_path or not output_dir:
        messagebox.showwarning("Errore", "Seleziona sia il file video che la cartella di destinazione.")
        return
    
    processing_thread = threading.Thread(target=process_video, args=(video_path, output_dir))
    processing_thread.start()

def pause_processing():
    global is_paused
    is_paused = not is_paused
    pause_button.config(text="▶️ Riprendi" if is_paused else "⏸️ Pausa")

def stop_processing_function():
    global stop_processing
    stop_processing = True

def update_sensitivity(val):
    global MIN_CONTOUR_AREA
    MIN_CONTOUR_AREA = int(val)

# Configura la GUI
root = tk.Tk()
root.title("Rilevamento di figure umane nei video")
root.geometry("800x500")  # Altezza aumentata per includere gli indicatori e la barra di progresso
root.configure(bg="#f0f0f5")  # Colore di sfondo leggero

# Layout principale
main_frame = tk.Frame(root, bg="#f0f0f5")
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Riquadro di anteprima a sinistra
preview_frame = tk.Frame(main_frame, bg="#ffffff", bd=2, relief=tk.SOLID)
preview_frame.grid(row=0, column=0, rowspan=4, padx=(0, 10), pady=(0, 10), sticky="ns")
preview_label = tk.Label(preview_frame, bg="#ffffff")
preview_label.pack(padx=5, pady=5)

# Etichetta e campo per selezionare il file di input
input_label = tk.Label(main_frame, text="Seleziona il file video:", font=("Helvetica Neue", 12), bg="#f0f0f5")
input_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
input_frame = tk.Frame(main_frame, bg="#f0f0f5")
input_frame.grid(row=1, column=1, padx=5, pady=5, sticky="w")
input_entry = tk.Entry(input_frame, width=40, font=("Helvetica Neue", 12))
input_entry.pack(side=tk.LEFT, padx=(0, 10))
input_button = tk.Button(input_frame, text="Sfoglia", command=select_input_file, font=("Helvetica Neue", 12), bg="#007bff", fg="white", relief="flat", padx=10, pady=5)
input_button.pack(side=tk.LEFT)

# Etichetta e campo per selezionare la cartella di output
output_label = tk.Label(main_frame, text="Seleziona la cartella di destinazione:", font=("Helvetica Neue", 12), bg="#f0f0f5")
output_label.grid(row=2, column=1, padx=5, pady=5, sticky="w")
output_frame = tk.Frame(main_frame, bg="#f0f0f5")
output_frame.grid(row=3, column=1, padx=5, pady=5, sticky="w")
output_entry = tk.Entry(output_frame, width=40, font=("Helvetica Neue", 12))
output_entry.pack(side=tk.LEFT, padx=(0, 10))
output_button = tk.Button(output_frame, text="Sfoglia", command=select_output_folder, font=("Helvetica Neue", 12), bg="#007bff", fg="white", relief="flat", padx=10, pady=5)
output_button.pack(side=tk.LEFT)

# Cursore per regolare la sensibilità
sensitivity_label = tk.Label(main_frame, text="Sensibilità del rilevamento:", font=("Helvetica Neue", 12), bg="#f0f0f5")
sensitivity_label.grid(row=4, column=1, padx=5, pady=5, sticky="w")
sensitivity_scale = tk.Scale(main_frame, from_=1500, to=10000, orient=tk.HORIZONTAL, length=400, command=update_sensitivity, bg="#f0f0f5", font=("Helvetica Neue", 12))
sensitivity_scale.grid(row=5, column=1, padx=5, pady=5, sticky="w")
sensitivity_scale.set(MIN_CONTOUR_AREA)

# Pulsanti di controllo (Avvia, Pausa, Interrompi)
buttons_frame = tk.Frame(main_frame, bg="#f0f0f5")
buttons_frame.grid(row=6, column=1, padx=5, pady=5, sticky="w")
start_button = tk.Button(buttons_frame, text="▶️ Avvia", command=start_processing, font=("Helvetica Neue", 12), bg="#28a745", fg="white", relief="flat", padx=10, pady=5)
start_button.pack(side=tk.LEFT, padx=5)
pause_button = tk.Button(buttons_frame, text="⏸️ Pausa", command=pause_processing, font=("Helvetica Neue", 12), bg="#ffc107", fg="white", relief="flat", padx=10, pady=5)
pause_button.pack(side=tk.LEFT, padx=5)
stop_button = tk.Button(buttons_frame, text="⏹️ Interrompi", command=stop_processing_function, font=("Helvetica Neue", 12), bg="#dc3545", fg="white", relief="flat", padx=10, pady=5)
stop_button.pack(side=tk.LEFT, padx=5)

# Barra di progresso
progress_label = tk.Label(main_frame, text="Progresso:", font=("Helvetica Neue", 12), bg="#f0f0f5")
progress_label.grid(row=7, column=1, padx=5, pady=5, sticky="w")
progress_bar = ttk.Progressbar(main_frame, length=400, mode="determinate")
progress_bar.grid(row=8, column=1, padx=5, pady=5, sticky="w")

# Etichette per tempo corrente e rimanente
current_time_label = tk.Label(main_frame, text="Tempo corrente: 0 s", font=("Helvetica Neue", 12), bg="#f0f0f5")
current_time_label.grid(row=9, column=1, padx=5, pady=5, sticky="w")
remaining_time_label = tk.Label(main_frame, text="Tempo stimato rimanente: 0 s", font=("Helvetica Neue", 12), bg="#f0f0f5")
remaining_time_label.grid(row=10, column=1, padx=5, pady=5, sticky="w")

root.mainloop()
