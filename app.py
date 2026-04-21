from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'krenova2026_agrolink'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Otomatis buat folder upload jika belum ada agar tidak error
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='agro_link'
    )
    return connection

# ================= ROUTE AUTENTIKASI =================
# 1. Rute Baru untuk Landing Page
@app.route('/')
def index():
    return render_template('index.html')

# 2. Rute Login yang sudah digeser ke /login
@app.route('/login', methods=['GET', 'POST'])
def login():
    pesan_error = ''
    if request.method == 'POST':

        nik_input = request.form['nik']
        password_input = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE nik = %s AND password = %s", (nik_input, password_input))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['loggedin'] = True
            session['id_user'] = user['id_user']
            session['nama'] = user['nama_lengkap']
            session['role'] = user['role']
            
            if user['role'] == 'petani':
                return redirect(url_for('dashboard_petani'))
            else:
                return redirect(url_for('dashboard_pedagang'))
        else:
            pesan_error = 'NIK atau Password salah. Silakan coba lagi.'

    return render_template('login.html', pesan=pesan_error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama_lengkap']
        password = request.form['password']
        role = request.form['role']
        no_hp = request.form['no_hp']
        kecamatan = request.form['kecamatan']

        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO users (nik, nama_lengkap, password, role, no_hp, kecamatan) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (nik, nama, password, role, no_hp, kecamatan)
        
        try:
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error: {e}")
            return "Terjadi kesalahan saat mendaftar. NIK mungkin sudah ada."

    return render_template('register.html')

# ================= ROUTE PEDAGANG =================
@app.route('/dashboard_pedagang')
def dashboard_pedagang():
    if 'loggedin' in session and session['role'] == 'pedagang':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT p.*, u.nama_lengkap, u.kecamatan FROM produk p JOIN users u ON p.id_petani = u.id_user ORDER BY p.id_produk DESC"
        cursor.execute(query)
        semua_produk = cursor.fetchall()
        
        query_pesanan_saya = """
            SELECT ps.*, pr.nama_produk, u.nama_lengkap AS nama_petani, u.no_hp
            FROM pesanan ps
            JOIN produk pr ON ps.id_produk = pr.id_produk
            JOIN users u ON pr.id_petani = u.id_user
            WHERE ps.id_pedagang = %s
            ORDER BY ps.tanggal_pesan DESC
        """
        cursor.execute(query_pesanan_saya, (session['id_user'],))
        pesanan_saya = cursor.fetchall()

        cursor.execute("SELECT SUM(total_harga) AS total_pengeluaran FROM pesanan WHERE id_pedagang = %s", (session['id_user'],))
        hasil_pengeluaran = cursor.fetchone()
        total_pengeluaran = hasil_pengeluaran['total_pengeluaran'] if hasil_pengeluaran['total_pengeluaran'] else 0
        
        cursor.close()
        conn.close()
        return render_template('dashboard_pedagang.html', nama=session['nama'], produk=semua_produk, pesanan=pesanan_saya, total_pengeluaran=total_pengeluaran)
    return redirect(url_for('login'))

@app.route('/beli/<int:id_produk>')
def beli(id_produk):
    if 'loggedin' in session and session['role'] == 'pedagang':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT p.*, u.nama_lengkap FROM produk p JOIN users u ON p.id_petani = u.id_user WHERE p.id_produk = %s", (id_produk,))
        produk_dipilih = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('beli.html', produk=produk_dipilih)
    return redirect(url_for('login'))

@app.route('/proses_beli', methods=['POST'])
def proses_beli():
    if 'loggedin' in session and session['role'] == 'pedagang':
        id_produk = request.form['id_produk']
        jumlah_beli = int(request.form['jumlah_beli'])
        harga_per_kg = int(request.form['harga_per_kg'])
        total_harga = jumlah_beli * harga_per_kg
        id_pedagang = session['id_user']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT stok_kg FROM produk WHERE id_produk = %s", (id_produk,))
        stok_sekarang = cursor.fetchone()['stok_kg']

        if jumlah_beli <= stok_sekarang:
            stok_baru = stok_sekarang - jumlah_beli
            cursor.execute("UPDATE produk SET stok_kg = %s WHERE id_produk = %s", (stok_baru, id_produk))
            cursor.execute("INSERT INTO pesanan (id_pedagang, id_produk, jumlah_kg, total_harga) VALUES (%s, %s, %s, %s)", (id_pedagang, id_produk, jumlah_beli, total_harga))
            conn.commit()
        
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard_pedagang'))
    return redirect(url_for('login'))

@app.route('/nego/<int:id_produk>')
def nego(id_produk):
    if 'loggedin' in session and session['role'] == 'pedagang':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT p.*, u.nama_lengkap FROM produk p JOIN users u ON p.id_petani = u.id_user WHERE p.id_produk = %s", (id_produk,))
        produk_dipilih = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('nego.html', produk=produk_dipilih)
    return redirect(url_for('login'))

@app.route('/proses_nego', methods=['POST'])
def proses_nego():
    if 'loggedin' in session and session['role'] == 'pedagang':
        id_produk = request.form['id_produk']
        jumlah_kebutuhan = request.form['jumlah_kebutuhan']
        harga_tawaran = request.form['harga_tawaran']
        id_pedagang = session['id_user']

        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO nego_harga (id_pedagang, id_produk, jumlah_kebutuhan_kg, harga_tawaran) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (id_pedagang, id_produk, jumlah_kebutuhan, harga_tawaran))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard_pedagang'))
    return redirect(url_for('login'))

# ================= ROUTE PETANI =================
@app.route('/dashboard_petani')
def dashboard_petani():
    if 'loggedin' in session and session['role'] == 'petani':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM produk WHERE id_petani = %s", (session['id_user'],))
        data_produk = cursor.fetchall()

        query_pesanan = """
            SELECT ps.*, pr.nama_produk, u.nama_lengkap AS nama_pedagang, u.no_hp
            FROM pesanan ps
            JOIN produk pr ON ps.id_produk = pr.id_produk
            JOIN users u ON ps.id_pedagang = u.id_user
            WHERE pr.id_petani = %s
            ORDER BY ps.tanggal_pesan DESC
        """
        cursor.execute(query_pesanan, (session['id_user'],))
        data_pesanan = cursor.fetchall()

        query_nego = """
            SELECT n.*, p.nama_produk, u.nama_lengkap AS nama_pedagang 
            FROM nego_harga n
            JOIN produk p ON n.id_produk = p.id_produk
            JOIN users u ON n.id_pedagang = u.id_user
            WHERE p.id_petani = %s AND n.status_nego = 'Menunggu'
            ORDER BY n.tanggal_nego DESC
        """
        cursor.execute(query_nego, (session['id_user'],))
        data_nego = cursor.fetchall()

        query_pendapatan = "SELECT SUM(ps.total_harga) AS total_pendapatan FROM pesanan ps JOIN produk pr ON ps.id_produk = pr.id_produk WHERE pr.id_petani = %s"
        cursor.execute(query_pendapatan, (session['id_user'],))
        hasil_pendapatan = cursor.fetchone()
        total_pendapatan = hasil_pendapatan['total_pendapatan'] if hasil_pendapatan['total_pendapatan'] else 0
        
        # --- TAMBAHAN BARU: AMBIL DATA PENGELUARAN MODAL ---
        cursor.execute("SELECT * FROM pengeluaran_tani WHERE id_petani = %s ORDER BY tanggal DESC", (session['id_user'],))
        data_pengeluaran = cursor.fetchall()

        cursor.execute("SELECT SUM(nominal) AS total_modal FROM pengeluaran_tani WHERE id_petani = %s", (session['id_user'],))
        hasil_modal = cursor.fetchone()
        total_modal = hasil_modal['total_modal'] if hasil_modal['total_modal'] else 0
        # ---------------------------------------------------

        cursor.close()
        conn.close()
        # Tambahkan pengeluaran=data_pengeluaran dan modal=total_modal di ujungnya
        return render_template('dashboard_petani.html', nama=session['nama'], produk=data_produk, pesanan=data_pesanan, nego=data_nego, total_pendapatan=total_pendapatan, pengeluaran=data_pengeluaran, modal=total_modal)
    return redirect(url_for('login'))


@app.route('/tambah_pengeluaran', methods=['POST'])
def tambah_pengeluaran():
    if 'loggedin' in session and session['role'] == 'petani':
        kategori = request.form['kategori']
        keterangan = request.form['keterangan']
        nominal = int(request.form['nominal'].replace('.', '')) # Hilangkan titik jika ada

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pengeluaran_tani (id_petani, kategori, keterangan, nominal) VALUES (%s, %s, %s, %s)", (session['id_user'], kategori, keterangan, nominal))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard_petani'))
    return redirect(url_for('login'))

@app.route('/tambah_produk', methods=['POST'])
def tambah_produk():
    if 'loggedin' in session and session['role'] == 'petani':
        nama_produk = request.form['nama_produk']
        kategori = request.form['kategori']
        harga = request.form['harga_per_kg']
        stok = request.form['stok_kg']
        status_panen = request.form['status_panen']
        tanggal_estimasi = request.form.get('tanggal_estimasi_panen')
        
        if not tanggal_estimasi:
            tanggal_estimasi = None 

        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO produk (id_petani, nama_produk, kategori, harga_per_kg, stok_kg, status_panen, tanggal_estimasi_panen) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (session['id_user'], nama_produk, kategori, harga, stok, status_panen, tanggal_estimasi))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard_petani'))
    return redirect(url_for('login'))

@app.route('/terima_nego/<int:id_nego>')
def terima_nego(id_nego):
    if 'loggedin' in session and session['role'] == 'petani':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM nego_harga WHERE id_nego = %s", (id_nego,))
        nego = cursor.fetchone()

        if nego:
            cursor.execute("UPDATE nego_harga SET status_nego = 'Diterima' WHERE id_nego = %s", (id_nego,))
            cursor.execute("SELECT stok_kg FROM produk WHERE id_produk = %s", (nego['id_produk'],))
            stok_sekarang = cursor.fetchone()['stok_kg']
            stok_baru = stok_sekarang - nego['jumlah_kebutuhan_kg']
            cursor.execute("UPDATE produk SET stok_kg = %s WHERE id_produk = %s", (stok_baru, nego['id_produk']))
            total_harga = nego['jumlah_kebutuhan_kg'] * nego['harga_tawaran']
            cursor.execute("INSERT INTO pesanan (id_pedagang, id_produk, jumlah_kg, total_harga) VALUES (%s, %s, %s, %s)", (nego['id_pedagang'], nego['id_produk'], nego['jumlah_kebutuhan_kg'], total_harga))
            conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for('dashboard_petani'))
    return redirect(url_for('login'))

@app.route('/tolak_nego/<int:id_nego>')
def tolak_nego(id_nego):
    if 'loggedin' in session and session['role'] == 'petani':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE nego_harga SET status_nego = 'Ditolak' WHERE id_nego = %s", (id_nego,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard_petani'))
    return redirect(url_for('login'))

@app.route('/update_status/<int:id_pesanan>/<status>')
def update_status(id_pesanan, status):
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE pesanan SET status_pengiriman = %s WHERE id_pesanan = %s", (status, id_pesanan))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard_petani') if session['role'] == 'petani' else url_for('dashboard_pedagang'))
    return redirect(url_for('login'))

@app.route('/upload_bukti/<int:id_pesanan>')
def upload_bukti(id_pesanan):
    if 'loggedin' in session and session['role'] == 'pedagang':
        return render_template('upload_bukti.html', id_pesanan=id_pesanan)
    return redirect(url_for('login'))

@app.route('/proses_upload_bukti', methods=['POST'])
def proses_upload_bukti():
    if 'loggedin' in session and session['role'] == 'pedagang':
        id_pesanan = request.form['id_pesanan']
        if 'file_bukti' not in request.files:
            return redirect(url_for('dashboard_pedagang'))
        file = request.files['file_bukti']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE pesanan SET bukti_bayar = %s, status_pengiriman = 'Dibayar' WHERE id_pesanan = %s", (filename, id_pesanan))
            conn.commit()
            cursor.close()
            conn.close()
        return redirect(url_for('dashboard_pedagang'))
    return redirect(url_for('login'))

# ================= JALANKAN SERVER =================
if __name__ == '__main__':
    # debug=True agar server otomatis restart jika ada perubahan kode
    app.run(debug=True)