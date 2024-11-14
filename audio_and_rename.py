import os
import librosa
import numpy as np
import soundfile as sf
import tkinter as tk
from tkinter import filedialog, ttk, simpledialog, Toplevel, Radiobutton
import re

# Функции для аудио обработки
def add_padding(y, sr, pad_start=0.10, pad_end=0.20):
    start_pad = np.zeros(int(sr * pad_start))
    end_pad = np.zeros(int(sr * pad_end))
    return np.concatenate((start_pad, y, end_pad))

def process_audio(file_path, output_sr, output_folder, progress_text, progress_bar):
    y, sr = librosa.load(file_path, sr=None)

    # Удаляем обработку шума и тишины
    y_padded = add_padding(y, sr)  # Добавление паддинга без предварительной обрезки

    y_resampled = librosa.resample(y_padded, orig_sr=sr, target_sr=output_sr)
    output_path = os.path.join(output_folder, os.path.basename(file_path))
    sf.write(output_path, y_resampled, output_sr, subtype='PCM_16')
    progress_text.insert(tk.END, f"Обработан файл: {os.path.basename(file_path)} -> {output_sr} Гц\n")
    progress_bar.step()

def process_directory(input_dir, output_dir, progress_text, progress_bar):
    dir_22k = os.path.join(output_dir, '22k')
    dir_8k = os.path.join(output_dir, '8k')
    os.makedirs(dir_22k, exist_ok=True)
    os.makedirs(dir_8k, exist_ok=True)

    files = [f for f in os.listdir(input_dir) if f.endswith('.wav')]
    progress_bar["maximum"] = len(files) * 2

    for filename in files:
        file_path = os.path.join(input_dir, filename)
        process_audio(file_path, 22050, dir_22k, progress_text, progress_bar)
        process_audio(file_path, 8000, dir_8k, progress_text, progress_bar)

# Функция для выбора и применения суффиксов
def rename_files_with_suffix_choice(progress_text, progress_bar):
    suffix_choice = tk.StringVar(value="alternate")
    skip_names_input = None

    def apply_suffix_choice():
        skip_names = skip_names_input.get("1.0", tk.END).strip().splitlines()
        rename_files(progress_text, progress_bar, suffix_choice.get(), skip_names)
        suffix_window.destroy()

    # Создание окна для выбора суффикса
    suffix_window = Toplevel()
    suffix_window.title("Выбор суффикса")

    tk.Label(suffix_window, text="Выберите режим суффикса:").pack(anchor="w", padx=10, pady=5)
    Radiobutton(suffix_window, text="Чередовать R и K", variable=suffix_choice, value="alternate").pack(anchor="w", padx=10)
    Radiobutton(suffix_window, text="Только R", variable=suffix_choice, value="R").pack(anchor="w", padx=10)
    Radiobutton(suffix_window, text="Только K", variable=suffix_choice, value="K").pack(anchor="w", padx=10)

    # Текстовое поле для пропуска файлов
    tk.Label(suffix_window, text="Введите имена файлов для пропуска (по одному в строке):").pack(anchor="w", padx=10, pady=5)
    skip_names_input = tk.Text(suffix_window, height=6, width=40)
    skip_names_input.pack(padx=10, pady=10)

    apply_button = tk.Button(suffix_window, text="Применить", command=apply_suffix_choice)
    apply_button.pack(pady=10)

def rename_files(progress_text, progress_bar, suffix_mode, skip_names):
    # Убедимся, что skip_names — это строка, а не список
    if isinstance(skip_names, list):
        skip_names = "\n".join(skip_names)  # Преобразуем список в строку, разделяя строками

    # Преобразуем строку в множество имен, убирая расширение '.wav' для пропущенных файлов
    skip_names_set = set(name.strip().replace('.wav', '') for name in skip_names.splitlines())  # Убираем .wav

    # Для отладки: распечатаем skip_names_set
    print("Список пропущенных имен:", skip_names_set)

    def get_user_input(prompt):
        return simpledialog.askstring("Ввод данных", prompt)

    folder_path = filedialog.askdirectory(title="Выберите папку с подкаталогами 22k и 8k")
    folder_22k = os.path.join(folder_path, "22k")
    folder_8k = os.path.join(folder_path, "8k")

    files_22k = [f for f in os.listdir(folder_22k) if f.endswith('.wav')]
    files_8k = [f for f in os.listdir(folder_8k) if f.endswith('.wav')]

    if len(files_22k) != len(files_8k):
        progress_text.insert(tk.END, "Количество файлов в папках 22k и 8k отличается!\n")
        return

    template = get_user_input("Введите шаблонное название (например, 1_TEST_A_R):")
    match = re.match(r"(\d+)_(.*)_([A-Z])$", template)
    if not match:
        progress_text.insert(tk.END, "Неверный формат шаблона. Используйте формат, например: 1_TEST_A_R\n")
        return

    start_index = int(match.group(1))
    base_name = match.group(2)
    first_suffix = match.group(3)
    second_suffix = "K" if first_suffix == "R" else "R"

    files_22k.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))
    files_8k.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))

    new_names = []
    index = start_index
    while len(new_names) < len(files_22k):
        if suffix_mode == "alternate":
            for suffix in [first_suffix, second_suffix]:
                new_name = f"{index}_{base_name}_{suffix}.wav"
                # Печатаем, чтобы отследить что происходит
                print(f"Проверка на пропуск: {new_name}")
                if new_name.replace('.wav', '') not in skip_names_set:  # Пропускаем имена без расширения
                    new_names.append(new_name)
                    if len(new_names) >= len(files_22k):
                        break
        else:
            new_name = f"{index}_{base_name}_{suffix_mode}.wav"
            # Печатаем, чтобы отследить что происходит
            print(f"Проверка на пропуск: {new_name}")
            if new_name.replace('.wav', '') not in skip_names_set:  # Пропускаем имена без расширения
                new_names.append(new_name)
        index += 1

    progress_bar["maximum"] = len(files_22k) * 2

    for i in range(len(files_22k)):
        current_file_22k = files_22k[i]
        current_file_8k = files_8k[i]
        new_name = new_names.pop(0)

        # Переименование 22k файлов, если не в списке пропущенных
        if current_file_22k.replace('.wav', '') not in skip_names_set:
            os.rename(os.path.join(folder_22k, current_file_22k), os.path.join(folder_22k, new_name))
            progress_text.insert(tk.END, f"Переименован: {current_file_22k} -> {new_name}\n")
            progress_bar.step()
        else:
            progress_text.insert(tk.END, f"Пропущен: {current_file_22k}\n")

        # Переименование 8k файлов, если не в списке пропущенных
        if current_file_8k.replace('.wav', '') not in skip_names_set:
            os.rename(os.path.join(folder_8k, current_file_8k), os.path.join(folder_8k, new_name))
            progress_text.insert(tk.END, f"Переименован: {current_file_8k} -> {new_name}\n")
            progress_bar.step()
        else:
            progress_text.insert(tk.END, f"Пропущен: {current_file_8k}\n")

    progress_text.insert(tk.END, "Файлы переименованы успешно.\n")


# Основной интерфейс
def audio_processing(progress_text, progress_bar):
    input_directory = filedialog.askdirectory(title="Выберите папку с аудиофразами")
    if not input_directory:
        progress_text.insert(tk.END, "Выбор папки отменен.\n")
        return

    output_directory = filedialog.askdirectory(title="Выберите папку для сохранения обработанных аудио")
    if not output_directory:
        progress_text.insert(tk.END, "Выбор папки для сохранения отменен.\n")
        return

    process_directory(input_directory, output_directory, progress_text, progress_bar)

def main():
    root = tk.Tk()
    root.title("Audio Processor")
    root.geometry("400x400")
    root.configure(bg='#f0f0f0')

    style = ttk.Style()
    style.configure("TButton", font=("Arial", 12), padding=10)
    style.map("TButton", background=[('active', '#45a049')])

    frame = ttk.Frame(root, padding=10, relief="solid")
    frame.pack(fill="both", expand=True)

    progress_text = tk.Text(frame, wrap="word", height=10, font=("Arial", 10))
    progress_text.pack(pady=10, fill="both", expand=True)

    progress_bar = ttk.Progressbar(frame, mode="determinate")
    progress_bar.pack(fill="x", pady=10)

    audio_button = ttk.Button(frame, text="Audio", command=lambda: audio_processing(progress_text, progress_bar))
    audio_button.pack(pady=5, fill="x")

    rename_button = ttk.Button(frame, text="Rename", command=lambda: rename_files_with_suffix_choice(progress_text, progress_bar))
    rename_button.pack(pady=5, fill="x")

    root.mainloop()

if __name__ == "__main__":
    main()
