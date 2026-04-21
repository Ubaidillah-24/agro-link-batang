import os

# Masukkan path folder tempat fotomu berada (pastikan pakai garis miring '/')
folder_path = 'D:/DICODING/Capston Project/Dataset_MultiLabel/images/Data'

# Ambil semua daftar file di dalam folder tersebut
files = os.listdir(folder_path)
files.sort() # Mengurutkan file sebelum diubah

count = 1
for filename in files:
    # Memastikan hanya memproses file gambar
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
        # Membuat format nama baru: tray_001.jpg, tray_002.jpg, dst.
        new_name = f"tray_{count:03d}.jpg" 
        
        # Alamat lengkap file lama dan baru
        old_file = os.path.join(folder_path, filename)
        new_file = os.path.join(folder_path, new_name)
        
        # Eksekusi ubah nama
        os.rename(old_file, new_file)
        count += 1

print(f"Beres! {count-1} foto berhasil di-rename.")