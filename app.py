from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import hvsrpy
import numpy as np
import pandas as pd
import ollama
import chromadb
import uuid
from geopy.geocoders import Nominatim
from flask import send_from_directory
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

UPLOAD_FOLDER = 'uploads'
PLOTS_FOLDER = 'plots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PLOTS_FOLDER, exist_ok=True)

# ChromaDB Setup
DB_PATH = "./chroma_db"
# Ensure the client is persistent
client = chromadb.PersistentClient(path=DB_PATH)
try:
    collection = client.get_collection(name="geodata")
except Exception as e:
    # Handle case where collection might not exist yet (though user implied it does)
    print(f"Warning: Could not get collection 'geodata': {e}")
    collection = None

#================= SETUP DATA GEOLOGI =================
try:
    file_path = os.path.join(os.path.dirname(__file__), "geologihex.csv")
    df_geologi = pd.read_csv(file_path)
    df_geologi.columns = ["x", "y", "hex"]
    df_geologi["hex"] = df_geologi["hex"].str.upper()

    hex_dict = {
        "#E5B8B2": """LAVA DAN LAHAR GUNUNG PATUHA : lava dan lahar andesit proksin yang pejal dan berongga dari Gunung Patuha. Pelembaran atau pengekaran melapis terdapat secara lokal di daerah danau patenggang, fenokris plagioklas yang panjangnya 1cm bisa terlihat. Breksi lahar biasanya termampat baik, tapi kurang terpilah. Komponen bergaris ke tengah antara beberapa cm sampai 3m; matriks tuf pasiran berwarna abu-abu""",

        "#A7A1A3": """LAHAR DAN LAVA GUNUNG KENDENG: Aliran lava berselingan dengan endapan lahar berupa breksi andesit dan breksi tuf. Komponen menydut sampai sebesar 40 cm garis tengahnya""",

        "#E3DDCD": """TALUS DAN ENDAPAN LONGSORAN: Endapan-endapan longsoran dan Talus umum ditemukan, terutama di sepanjang gawir-gawir di Formasi Bentang, dan Menindih tak selaras formasi Bentang""",

        "#B4C49D": """ANGGOTA BATU GAMPING, FORMASI BENTANG: batugamping melensa, berpori; dan mengandung fosil foraminifera. umur miosen akhir.""",

        "#D2DCD3": """FORMASI BENTANG : Runtunan turbidit berupa batupasir tuf berlapis baik, kurang mampat; tuf kristal, dan tuf batuapungan dengan sisipan lempung globigerina, batulanau, batulempung napalan, dan breksi andesit, konglomerat, tuf lapili dan breksi tuf. Di lapisan atas, batulempung dan batulanau menguasai. Breksi batuapung tersusun dari kepingan batuan bergaris tengah 5 cm. Batupasir hitam merupakan lapisan tipis yang terdapat di bagian selatan lembar peta. Struktur perlapisan dan pembebanan. Moluska dan foraminifera kecil terdapat di banyak tempat, dan Balanus tampaknya setempat. Brachiopoda berumur Neogen ditemukan di Sungai Cigoyeh, anak sungai dari Sungai Cisadea 3 km barat-baratdaya Koleberes. Lapisan batubara setebal 20 cm tersingkap di utara Kadupandak.

        Lensa batugamping yang berpori, dan lapisan berfosil terdapat pada atau dekat kontak dengan Formasi Koleberes. Fosil yang dikumpulkan sepanjang Kali Ciburial dilaporkan oleh Sutedi (1972) sebagai berikut: Lepidocyclina gigantea (MARTIN), Cycloclypeus guembelianus (BRADY), C. (Katacycloclypeus) sp., Globigerina trilobus (REUSS), G. bulloides, Orbulina universa D’ORBIGNY, O. bilobata (D’ORBIGNY) dan menunjukkan umur Miosen Akhir dengan lingkungan pengendapan laut dangkal-dalam terbuka. Tebal satuan 300 m. Formasi ini menindih selaras Formasi Cimandiri.""",

        "#F4E4B3": """FORMASI KOLEBERES : Batupasir tuf berlapis baik, kurang mampat, dan tuf kristal; dengan sisipan tuf, breksi tuf batuapungan dan breksi bersusunan andesit. Batupasir kelabu kecoklatan, terutama terdiri dari batuan andesitan dengan sejumlah batuapung. Batupasir hitam terdapat di dekat G. Gebeg dan di sebelah timur Citalahab. Bongkah-bongkah magnetit yang pejal terdapat di dua tempat dekat Koleberes. Sisa tumbuhan dan lapisan batubara setebal 1 m terutama ditemukan di G. Gebeg. Butir-butir damar ditemukan di sebelah timur Pagelaran, di lembah sungai Cilumut. Moluska, gastropoda, echinoida, koral dan foraminifera ditemukan terutama di lapisan-lapisan bagian atas satuan ini. Fauna moluska dari Cigugur meliputi 44,3 persen dari bentuk-bentuk Resen (van Regteren Altena dan Beets, 1945).

        Kumpulan fosil dari dekat lembah Cilumut yang terdiri dari Globigerina nepenthes (TODD), Globigerinoides trilobus (REUSS), G. immaturus LEROY, G. obliquus BOLLI, G. sacculifer (BRADY), G. conglobatus (BRADY), Orbulina universa D’ORBIGNY, Hastigerina aequilateralis (BRADY), Pulleniatina primalis BANNER and BLOW, Globorotalia abesa BOLLI, G. menardii (D’ORBIGNY), G. tumida (BRADY) menunjukkan umur Akhir Miosen sampai Pliosen (D. Kadar, 1971); sedangkan fosil dari dekat Pasir Pari, yang menunjukkan umur akhir Miosen, terdiri dari Globigerinoides extremus BOLLI & BERMUDEZ, G. obliquus BOLLI, G. immaturus LEROY, G. trilobus (REUSS), Globquadrina sp., G. altispira (CUSHMAN & JARVIS), Globorotalia menardii (D’ORBIGNY), Pulleniatina primalis BANNER and BLOW, Sphaeroidinella seminulina (SCHWAGER) (D. Kadar, 1972).

        Lingkungan pengendapan laut terbuka. Tebal formasi kira-kira 350 m. Satuan ini menindih selaras Formasi Bentang, dan ditindih takselaras oleh satuan Lahar dan Lava G. Kende.""",

        "#E7ADAC": """Lava andesitan andesitan-basalan Gunung Huyung""",

        "#F1D9BF": """ENDAPAN ENDAPAN PIROKLASTIKA YANG TERPISAH-KAN: Breksi andesit, breksi tuf dan tuf lapili. Di sisi timur Gunung Parang Dijumpai batuan prioklastika yang melebar, dan ignimbrit (Koesmono, 1975). Kayu terkersikkan dan yaspis terdapat dalam breksi tersebut."""
    }
except Exception as e:
    print(f"Gagal memuat data geologi: {e}")
    df_geologi = None
    hex_dict = {}

def get_geologi_info(lon, lat):
    if df_geologi is None or df_geologi.empty:
        return "Data geologi tidak tersedia."
    
    try:
        user_x = float(lon)
        user_y = float(lat)
        
        # hitung jarak
        df_geo_copy = df_geologi.copy()
        df_geo_copy["distance"] = np.sqrt((df_geo_copy["x"] - user_x)**2 + (df_geo_copy["y"] - user_y)**2)
        
        # ambil titik terdekat
        nearest_point = df_geo_copy.nsmallest(1, "distance")
        
        # ambil litologi
        hex_code = nearest_point.iloc[0]["hex"]
        description = hex_dict.get(hex_code, "Tidak diketahui")
        return description
    except Exception as e:
        print(f"Error dalam mengambil data geologi: {e}")
        return "Gagal mendapatkan data geologi."
#======================================================

def klasifikasi_f0(f0):
    if 6.667 <= f0 <= 20:
        return "Batuan tersier atau lebih tua, sedimen sangat tipis, didominasi batuan keras"
    elif 4 <= f0 < 6.667:
        return "Batuan alluvial (~5 m), sedimen permukaan kategori menengah (5–10 meter)"
    elif 2.5 <= f0 < 4:
        return "Batuan alluvial (>5 m), sedimen permukaan tebal (±10–30 meter)"
    elif f0 < 2.5:
        return "Sedimen lunak (delta/top soil/lumpur), sedimen sangat tebal (>30 meter)"
    else:
        return "Tidak terklasifikasi"

def klasifikasi_a0(a0):
    if a0 < 3:
        return "Tanah memiliki potensi kecil untuk mengalami kerusakan saat terjadi gempa (Rendah)"
    elif 3 <= a0 < 6:
        return "Tanah memiliki potensi untuk mengalami kerusakan saat terjadi gempa (Menengah)"
    elif 6 <= a0 <= 9:
        return "Tanah memiliki potensi cukup besar untuk mengalami kerusakan saat terjadi gempa (Tinggi)"
    elif a0 > 9:
        return "Tanah memiliki potensi sangat besar untuk mengalami kerusakan besar saat terjadi gempa (Sangat Tinggi)"
    else:
        return "Tidak terklasifikasi"

def klasifikasi_kg(kg):
    if kg <= 3:
        return "Kerentanan seimik Rendah"
    elif 3 < kg <= 5:
        return "Kerentanan seimik Sedang"
    elif 5 < kg < 10:
        return "Kerentanan seimik Tinggi"
    elif kg >= 10:
        return "Kerentanan seimik Sangat Tinggi"
    else:
        return "Tidak terklasifikasi"

def hasilinterpretasimikrotremor(f0, a0, kg):
    nilaifo = klasifikasi_f0(f0)
    nilaia0 = klasifikasi_a0(a0)
    nilaikg = klasifikasi_kg(kg)


def get_location_name(lat, lon):
    """Reverse geocode koordinat menjadi nama daerah (kecamatan, kabupaten, provinsi)."""
    try:
        geolocator = Nominatim(user_agent="geo_locator_indonesia")
        location = geolocator.reverse((float(lat), float(lon)), language="id")
        if location and location.raw.get('address'):
            address = location.raw['address']
            kecamatan = address.get('district') or address.get('suburb') or address.get('village') or ""
            kabupaten = address.get('county') or address.get('city') or address.get('municipality') or ""
            provinsi = address.get('state') or ""
            daerah = f"{kecamatan}, {kabupaten}, {provinsi}"
            return daerah.strip(", ")
        return "Lokasi tidak ditemukan"
    except Exception as e:
        print(f"Error dalam reverse geocoding: {e}")
        return "Gagal mendapatkan nama lokasi"

def process_microtremor(file_path, plot_filename):
    # Setup HvsrPy
    # hvsrpy expects a list of lists of filenames
    fnames = [[file_path]]

    preprocessing_settings = hvsrpy.settings.HvsrPreProcessingSettings()
    preprocessing_settings.detrend = "linear"
    preprocessing_settings.window_length_in_seconds = 20
    preprocessing_settings.orient_to_degrees_from_north = 0.0
    preprocessing_settings.filter_corner_frequencies_in_hz = (0.1, 20)
    preprocessing_settings.ignore_dissimilar_time_step_warning = False

    processing_settings = hvsrpy.settings.HvsrTraditionalProcessingSettings()
    processing_settings.window_type_and_width = ("tukey", 0.2)
    processing_settings.smoothing=dict(operator="konno_and_ohmachi",
                                       bandwidth=40,
                                       center_frequencies_in_hz=np.geomspace(0.1, 20, 200))
    processing_settings.method_to_combine_horizontals = "geometric_mean"
    processing_settings.handle_dissimilar_time_steps_by = "frequency_domain_resampling"

    try:
        srecords = hvsrpy.read(fnames)
        srecords = hvsrpy.preprocess(srecords, preprocessing_settings)
        hvsr = hvsrpy.process(srecords, processing_settings)

        # Mendapatkan nilai f0 dan A0 dari lognormal puncak rata rata
        f0, a0 = hvsr.mean_curve_peak(distribution="lognormal")

        # Buat plot HVSR
        plot_path = os.path.join(PLOTS_FOLDER, plot_filename)
        _generate_hvsr_plot(hvsr, f0, a0, plot_path)

        return f0, a0, plot_filename
    except Exception as e:
        print(f"Error in HVSR processing: {e}")
        raise e


def _generate_hvsr_plot(hvsr, f0, a0, save_path):
    """Generate and save HVSR curve plot."""
    fig, ax = plt.subplots(figsize=(8, 5))

    # mendapatkan data dari objek HVSR
    freqs = hvsr.frequency
    mean_curve = hvsr.mean_curve(distribution="lognormal")

    # Plot per window
    for curve in hvsr.amplitude:
        ax.plot(freqs, curve, color='#cbd5e1', alpha=0.4, linewidth=0.7)

    # Plot rata rata
    ax.plot(freqs, mean_curve, color='#1e293b', linewidth=2.2, label='Mean HVSR', zorder=5)

    # Tandai f0, A0 
    ax.plot(f0, a0, 'o', color='#ef4444', markersize=9, zorder=6, label=f'f0={f0:.3f} Hz, A0={a0:.3f}')
    ax.axvline(x=f0, color='#ef4444', linestyle='--', linewidth=1, alpha=0.6)

    # Styling
    ax.set_xscale('log')
    ax.set_xlabel('Frequency (Hz)', fontsize=11, fontweight='bold')
    ax.set_ylabel('H/V Amplitude', fontsize=11, fontweight='bold')
    ax.set_title('HVSR Curve', fontsize=13, fontweight='bold', pad=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.4, alpha=0.6)
    ax.legend(loc='upper right', fontsize=9, framealpha=0.9)
    ax.set_xlim([0.1, 20])
    y_max = a0 * 1.1
    ax.set_ylim([0, y_max])

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

@app.route('/plots/<path:filename>')
def serve_plot(filename):
    return send_from_directory(PLOTS_FOLDER, filename)

def generate_llm_output(nama_daerah, lat, lng, f0, a0, kg, info_geologi, context, keterangan):
    nilaif0 = klasifikasi_f0(f0)
    nilaia0 = klasifikasi_a0(a0)
    nilaikg = klasifikasi_kg(kg)

    prompt = f"""
        Berikan jawaban dalam bahasa Indonesia sebagai seorang ahli geofisika yang menjelaskan potensi bahaya gempa berdasarkan data mikrotremor HVSR.

        Lokasi: {nama_daerah}
        Koordinat: ({lat}, {lng})

        Data HVSR:
        - Frekuensi Dominan (f0): {f0:.3f} Hz yang menandakan {nilaif0}
        - Amplifikasi (A0): {a0:.3f} yang menandakan {nilaia0}
        - Indeks Kerentanan Seismik (Kg): {kg:.3f} yang menandakan {nilaikg}

        Referensi:
        {context}

        Informasi Geologi:
        {info_geologi}

        Keterangan tambahan:
        {keterangan if keterangan else "Tidak ada"}

        Tugas:
        Tuliskan tepat 3 paragraf:

        1. Jelaskan kondisi geologi lokasi berdasarkan informasi geologi.
        2. Interpretasikan nilai f0, A0, dan Kg, hubungkan dengan kondisi geologi, serta simpulkan ketebalan sedimen, kekerasan tanah, potensi resonansi, amplifikasi, dan tingkat kerentanan seismik.
        3. Jelaskan secara sederhana potensi bahaya gempa agar mudah dipahami masyarakat umum.

        Aturan:
        - Jangan mengulang instruksi.
        - Jangan menggunakan penomoran paragraf.
        - Gunakan bahasa jelas, padat, dan langsung ke inti.
        """

    try:
        response = ollama.chat(
            model="mistral",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )
        return response["message"]["content"]
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return f"Gagal menghasilkan penjelasan dari LLM. Error: {e}"

@app.route('/process', methods=['POST'])
def process():
    from seismophile import dataview

    lat = request.form.get('lat')
    lng = request.form.get('lng')
    keterangan = request.form.get('keterangan', '')
    upload_mode = request.form.get('mode', 'direct')  # 'direct' atau 'convert'

    unique_id = str(uuid.uuid4())
    plot_filename = unique_id + "_hvsr.png"
    temp_files = []  # file-file sementara yang perlu dihapus

    try:
        if upload_mode == 'convert':
            # ===== MODE 2: Upload bin + json, konversi ke mseed via seismophile =====
            if 'bin_file' not in request.files or 'json_file' not in request.files:
                return jsonify({'error': 'Mode konversi membutuhkan file .bin dan .json'}), 400

            bin_file = request.files['bin_file']
            json_file = request.files['json_file']

            if bin_file.filename == '' or json_file.filename == '':
                return jsonify({'error': 'File .bin dan .json harus dipilih'}), 400

            # Simpan kedua file dengan nama dasar yang sama (syarat seismophile)
            base_name = unique_id + "_data"
            bin_path = os.path.join(UPLOAD_FOLDER, base_name + ".bin")
            json_path = os.path.join(UPLOAD_FOLDER, base_name + ".json")
            mseed_path = os.path.join(UPLOAD_FOLDER, base_name + ".mseed")

            bin_file.save(bin_path)
            json_file.save(json_path)
            temp_files.extend([bin_path, json_path, mseed_path])

            # Konversi bin -> mseed menggunakan seismophile dataview
            print(f"Mengkonversi {bin_path} ke mseed...")
            dv = dataview(bin_path, fmt='bin')
            dv.save_mseed(mseed_path)
            print(f"Konversi selesai: {mseed_path}")

            filepath = mseed_path

        else:
            # ===== MODE 1: Upload langsung file seismik =====
            if 'file' not in request.files:
                return jsonify({'error': 'Tidak ada file yang diupload'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

            filename = unique_id + "_" + file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            temp_files.append(filepath)

        # Proses Mikrotremor
        f0, a0, plot_file = process_microtremor(filepath, plot_filename)
        
        # Hitung Kg
        kg = (a0**2) / f0

        # Reverse Geocoding - dapatkan nama daerah dari koordinat
        nama_daerah = get_location_name(lat, lng)
        print(f"Lokasi terdeteksi: {nama_daerah}")
        
        # Dapatkan Info Geologi
        info_geologi = get_geologi_info(lng, lat)
        
        # RAG Logic
        if collection:
            query_text = f"Informasi daerah {nama_daerah} dengan latitude {lat} dan longitude {lng}. nilai HVSR f0 = {f0}, A0 = {a0}, Kg = {kg}"
            
            try:
                query_embedding = ollama.embeddings(
                    model="nomic-embed-text",
                    prompt=query_text
                )["embedding"]
                
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=5
                )
                
                context = "\n\n".join(results["documents"][0])
            except Exception as e:
                print(f"Error querying ChromaDB/Ollama: {e}")
                context = "Tidak ada data konteks yang ditemukan atau terjadi kesalahan pada database vector."
        else:
            context = "Database vector tidak tersedia."

        # Generate LLM Output
        explanation = generate_llm_output(nama_daerah, lat, lng, f0, a0, kg, info_geologi, context, keterangan)

        return jsonify({
            'f0': f0,
            'a0': a0,
            'kg': kg,
            'explanation': explanation,
            'plot_url': f'/plots/{plot_file}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up semua file sementara
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)
