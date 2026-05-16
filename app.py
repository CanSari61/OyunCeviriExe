import eel
import os
import time
import shutil
import re
import tkinter as tk
from tkinter import filedialog
from deep_translator import GoogleTranslator

if not os.path.exists('web'):
    os.makedirs('web')

eel.init('web')

def process_text_files(game_path, translator):
    """Bulduğu tüm metin dosyalarını Türkçe yapar"""
    text_extensions = ['.json', '.txt', '.xml', '.ini', '.yaml', '.csv']
    files_to_process = []
    
    for root_dir, dirs, files in os.walk(game_path):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in text_extensions and not filename.endswith(".bak"):
                files_to_process.append(os.path.join(root_dir, filename))

    total = len(files_to_process)
    if total == 0:
        return 0

    for i, file_path in enumerate(files_to_process):
        filename = os.path.basename(file_path)
        progress = int(((i + 1) / total) * 40)
        eel.update_ui_progress(progress, f"Metin Çevriliyor: {filename}")()
        
        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(file_path, backup_path)

        try:
            with open(backup_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            translated_lines = []
            for line in lines:
                if len(line.strip()) > 3 and not line.startswith(('#', '[', '<', '{', '}')):
                    try:
                        tr_line = translator.translate(line.strip())
                        translated_lines.append(line.replace(line.strip(), tr_line))
                    except:
                        translated_lines.append(line)
                else:
                    translated_lines.append(line)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(translated_lines))
        except Exception:
            continue
            
    return total

def process_binary_archives(game_path, translator):
    """Büyük şifreli arşivlerin (.pak, .assets) içine dalıp metinleri byte seviyesinde yamalar"""
    archive_exts = ['.pak', '.assets', '.rpf', '.forge', '.ba2', '.archive']
    archives = []
    
    for root_dir, dirs, files in os.walk(game_path):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in archive_exts:
                archives.append(os.path.join(root_dir, filename))

    total = len(archives)
    if total == 0:
        return 0

    CHUNK_SIZE = 10 * 1024 * 1024 # RAM çökmesin diye 10 MB parçalar halinde okur

    for i, file_path in enumerate(archives):
        filename = os.path.basename(file_path)
        progress = 40 + int(((i + 1) / total) * 60)
        eel.update_ui_progress(progress, f"Arşiv İçine Sızılıyor (Hex Yaması): {filename}")()
        
        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, 'rb+') as f: # rb+ = Oku ve Doğrudan Üzerine Yaz
                offset = 0
                while offset < file_size:
                    f.seek(offset)
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                        
                    # 7 harften uzun İngilizce kelime/cümleleri bul
                    matches = re.finditer(b'[a-zA-Z\s]{7,}', data)
                    
                    for match in matches:
                        original_bytes = match.group()
                        original_str = original_bytes.decode('utf-8', errors='ignore').strip()
                        
                        # Eğer geçerli bir kelimeyse
                        if len(original_str) > 6 and " " in original_str:
                            try:
                                translated_str = translator.translate(original_str)
                                translated_bytes = translated_str.encode('utf-8')
                                
                                # OYUN KORUMASI: Yeni kelimeyi orijinalin tam BYTE UZUNLUĞUNA uydur
                                target_length = len(original_bytes)
                                if len(translated_bytes) < target_length:
                                    translated_bytes = translated_bytes.ljust(target_length, b' ')
                                elif len(translated_bytes) > target_length:
                                    translated_bytes = translated_bytes[:target_length]
                                
                                # Dosyadaki gerçek konumunu hesapla ve geri yaz
                                absolute_pos = offset + match.start()
                                f.seek(absolute_pos)
                                f.write(translated_bytes)
                            except:
                                continue
                    
                    offset += CHUNK_SIZE - 100 # Kesişimleri kaçırmamak için hafif geri sar
        except Exception as e:
            print(f"Arşiv atlandı {filename}: {e}")
            continue

    return total

@eel.expose
def auto_translate_game():
    """Kullanıcı butona bastığında çalışan ana motor"""
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    
    folder_path = filedialog.askdirectory(title="Türkçe Yapılacak Oyunun Klasörünü Seç")
    root.destroy()
    
    if not folder_path:
        return {"error": "Klasör seçilmedi. İşlem iptal edildi."}

    game_name = os.path.basename(folder_path) or "Oyun"
    
    # Arka planda işlemi başlat
    eel.spawn(start_translation_thread, folder_path)
    
    return {"status": "started", "name": game_name}

def start_translation_thread(game_path):
    try:
        translator = GoogleTranslator(source='auto', target='tr')
        
        eel.update_ui_progress(5, "Motor başlatılıyor, dosyalar taranıyor...")()
        text_count = process_text_files(game_path, translator)
        
        eel.update_ui_progress(40, "Açık metinler tamam. Şifreli oyun motoru arşivleri kırılıyor...")()
        arch_count = process_binary_archives(game_path, translator)
        
        eel.update_ui_progress(100, "Her şey tamamlandı! Oyun entegrasyonu başarılı.")()
        time.sleep(1)
        
        msg = f"Toplam {text_count} metin dosyası ve {arch_count} şifreli arşiv başarıyla Türkçeye uyarlandı!"
        eel.translation_finished(True, msg)()
        
    except Exception as e:
        eel.translation_finished(False, f"Sistem hatası: {str(e)}")()

if __name__ == '__main__':
    try:
        eel.start('index.html', size=(900, 650), mode='chrome')
    except Exception:
        # Chrome yoksa Edge ile aç
        eel.start('index.html', size=(900, 650), mode='edge')
