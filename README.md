# Auto-Mikro: Analisis Mikrotremor HVSR & Interpretasi AI

Auto-Mikro adalah aplikasi berbasis web untuk mengolah data mikrotremor menggunakan metode **Horizontal-to-Vertical Spectral Ratio (HVSR)**. Aplikasi ini mengintegrasikan pemrosesan sinyal geofisika dengan Kecerdasan Buatan (AI) untuk memberikan interpretasi otomatis mengenai kondisi geologi dan potensi bahaya gempa.

---

## Persiapan Sistem

### 1. Prasyarat Software
- **Python 3.10+**
- **Ollama** (untuk fitur AI/LLM):
  - Download di [ollama.com](https://ollama.com).
  - Jalankan perintah berikut untuk mengunduh model yang diperlukan:
    ```bash
    ollama pull mistral
    ollama pull nomic-embed-text
    ```

### 2. Instalasi Dependensi
Jalankan perintah berikut di terminal/command prompt:
```bash
pip install flask flask-cors hvsrpy numpy pandas ollama chromadb geopy matplotlib scipy mseedlib
```

---

## Cara Menjalankan Aplikasi

1.  Pastikan aplikasi **Ollama** sedang berjalan.
2.  Buka terminal di folder ini dan jalankan:
    ```bash
    python app.py
    ```
3.  Buka browser dan akses: `http://localhost:5000`

---

## Panduan Penggunaan

### 1. Menentukan Lokasi Pengukuran
- Anda dapat mengklik langsung pada peta interaktif untuk mengisi koordinat secara otomatis.
- Atau masukkan nilai **Latitude** dan **Longitude** secara manual pada kolom yang tersedia.

### 2. Keterangan Lokasi (Opsional)
- Tambahkan informasi tambahan mengenai kondisi sekitar lokasi pengukuran pada kolom teks untuk membantu AI memberikan interpretasi yang lebih akurat.

### 3. Memilih Mode Upload
Aplikasi memiliki dua mode pemrosesan:
- **File Seismik**: Upload langsung file format `.mseed`, `.saf`, `.sac`, `.gcf`, atau `.peer`.
- **Seismophile**: Upload pasangan file `.bin` dan `.json`. Aplikasi akan mengonversinya ke format `.mseed` secara otomatis sebelum diolah.

### 4. Mengolah Data
- Klik tombol **Olah Data**.
- Sistem akan memproses data menggunakan `hvsrpy` untuk menghasilkan grafik HVSR dan parameter geofisika.
- AI akan melakukan pencarian pada database (RAG) dan menghasilkan penjelasan dalam 3 paragraf mengenai kondisi geologi, parameter HVSR, dan potensi bahaya gempa.

---

## Parameter yang Dihasilkan
- **f0 (Hz)**: Frekuensi dominan (menunjukkan ketebalan sedimen).
- **A0**: Faktor amplifikasi.
- **Kg**: Indeks kerentanan seismik.
- **Grafik HVSR**: Visualisasi kurva perbandingan komponen horizontal dan vertikal.

---

## Struktur File Penting
- `app.py`: Backend Flask utama.
- `index.html`, `style.css`, `script.js`: Frontend aplikasi.
- `geologihex.csv`: Database pemetaan geologi lokal.
- `chroma_db/`: Penyimpanan vektor untuk data referensi AI (RAG).
- `seismophile.py`: Modul konversi data seismik mentah.

---
*Dibuat untuk penelitian analisis mikrotremor otomatis.*
