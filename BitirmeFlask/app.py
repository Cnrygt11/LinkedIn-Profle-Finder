from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import os
import threading
import time
from queue import Queue
import uuid
import numpy as np


from Absolute import (
    google_search_advanced, linkedin_login, extract_profile_sections,
    generate_summary_with_gemini, calculate_relevance_score, BASE_DIR
)

app = Flask(__name__)
CORS(app)  # Frontend ile iletişim için CORS'u etkinleştir

# Aktif arama işlemlerini takip etmek için
active_searches = {}
search_results = {}


class SearchTask:
    def __init__(self, search_id, search_params):
        self.search_id = search_id
        self.search_params = search_params
        self.status = "starting"
        self.progress = 0
        self.results = []
        self.error = None
        self.total_profiles = 0
        self.processed_profiles = 0


def make_json_serializable(obj):
    """NumPy tiplerini JSON serializable tiplere çevirir"""
    if isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    else:
        return obj

def background_search(search_task):
    """Arka planda profil arama ve analiz işlemi"""
    try:
        search_task.status = "searching"
        search_task.progress = 10

        # Google Search
        profiles = google_search_advanced(
            search_task.search_params['name'],
            search_task.search_params.get('city'),
            search_task.search_params.get('job'),
            search_task.search_params.get('university'),
            num=20
        )

        if not profiles:
            search_task.status = "completed"
            search_task.error = "Uygun profil bulunamadı"
            return

        # 0.85 üzeri skorlu profilleri filtrele
        filtered_profiles = [p for p in profiles if p[0] > 0.85]
        if not filtered_profiles:
            search_task.status = "completed"
            search_task.error = "0.85 üzeri profil bulunamadı"
            return

        search_task.total_profiles = len(filtered_profiles)
        search_task.status = "analyzing"
        search_task.progress = 20

        # LinkedIn'e giriş yap
        driver = linkedin_login()
        if not driver:
            search_task.status = "error"
            search_task.error = "LinkedIn giriş hatası"
            return

        try:
            # Anahtar kelimeler
            required_keywords = []
            if search_task.search_params.get('job'):
                required_keywords.append(search_task.search_params['job'])
            if search_task.search_params.get('city'):
                required_keywords.append(search_task.search_params['city'])

            analyzed_profiles = []

            for idx, (score, profile_url, title, _) in enumerate(filtered_profiles):
                try:
                    # Profil analizi
                    ham_text, bilgiler = extract_profile_sections(
                        driver, profile_url, required_keywords
                    )

                    if not ham_text.strip() or bilgiler is None:
                        continue

                    # Profil metnini düz yazıya çevir
                    flat_text = ""
                    for section in bilgiler:
                        flat_text += f"\n\n## {section['label'].capitalize()}\n{section['text']}"

                    # Özet oluştur
                    summary = generate_summary_with_gemini(flat_text)

                    if summary:
                        # Kategori skoru hesapla
                        kategori_skoru = calculate_relevance_score(
                            summary, search_task.search_params['category']
                        )

                        analyzed_profiles.append({
                            "title": title.strip(),
                            "url": profile_url,
                            "summary": summary,
                            "score": kategori_skoru,
                            "sections": bilgiler
                        })

                    # Progress güncelle
                    search_task.processed_profiles = idx + 1
                    search_task.progress = 20 + (70 * (idx + 1) / len(filtered_profiles))

                    time.sleep(8 + idx % 3)  # Rate limiting

                except Exception as e:
                    print(f"Profil analiz hatası: {e}")
                    continue

            # Sonuçları skoruna göre sırala
            analyzed_profiles.sort(key=lambda x: x["score"], reverse=True)
            search_task.results = analyzed_profiles[:10]  # En iyi 10 profil
            search_task.status = "completed"
            search_task.progress = 100

        finally:
            driver.quit()

    except Exception as e:
        search_task.status = "error"
        search_task.error = str(e)
        print(f"Arama hatası: {e}")


# Ana sayfa route'u ekle
@app.route('/')
def index():
    """Ana sayfa"""
    try:
        # HTML dosyasını oku
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dosya Bulunamadı</title>
        </head>
        <body>
            <h1>Hata: index.html dosyası bulunamadı</h1>
            <p>Lütfen index.html dosyasının app.py ile aynı dizinde olduğundan emin olun.</p>
        </body>
        </html>
        """, 404


@app.route('/api/search', methods=['POST'])
def start_search():
    """Yeni bir profil arama işlemi başlatır"""
    try:
        data = request.get_json()

        # Gerekli alanları kontrol et
        required_fields = ['name', 'category']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'{field} alanı gereklidir'
                }), 400

        # Benzersiz arama ID'si oluştur
        search_id = str(uuid.uuid4())

        # Arama görevini oluştur
        search_task = SearchTask(search_id, data)
        active_searches[search_id] = search_task

        # Arka planda arama işlemini başlat
        thread = threading.Thread(target=background_search, args=(search_task,))
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'search_id': search_id,
            'message': 'Arama başlatıldı'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search/<search_id>/status', methods=['GET'])
def get_search_status(search_id):
    """Arama işleminin durumunu döndürür"""
    if search_id not in active_searches:
        return jsonify({
            'success': False,
            'error': 'Arama bulunamadı'
        }), 404

    search_task = active_searches[search_id]

    response_data = {
        'success': True,
        'search_id': search_id,
        'status': search_task.status,
        'progress': float(search_task.progress),  # Açık float çevirimi
        'total_profiles': int(search_task.total_profiles),
        'processed_profiles': int(search_task.processed_profiles)
    }

    if search_task.error:
        response_data['error'] = search_task.error

    if search_task.status == 'completed' and search_task.results:
        # Sonuçları JSON serializable yap
        response_data['results'] = make_json_serializable(search_task.results)

    return jsonify(response_data)


@app.route('/api/search/<search_id>/results', methods=['GET'])
def get_search_results(search_id):
    """Arama sonuçlarını döndürür"""
    if search_id not in active_searches:
        return jsonify({
            'success': False,
            'error': 'Arama bulunamadı'
        }), 404

    search_task = active_searches[search_id]

    if search_task.status != 'completed':
        return jsonify({
            'success': False,
            'error': 'Arama henüz tamamlanmadı'
        }), 400

    return jsonify({
        'success': True,
        'search_id': search_id,
        'results': search_task.results,
        'total_found': len(search_task.results)
    })


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Mevcut kategorileri döndürür"""
    from Absolute import KATEGORI_KELIMELERI

    categories = []
    for kategori, keywords in KATEGORI_KELIMELERI.items():
        categories.append({
            'id': kategori,
            'name': kategori.title(),
            'keywords_count': len(keywords.split(','))
        })

    return jsonify({
        'success': True,
        'categories': categories
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """API durumunu kontrol eder"""
    return jsonify({
        'success': True,
        'message': 'API çalışıyor',
        'timestamp': time.time()
    })


@app.route('/api/search/<search_id>', methods=['DELETE'])
def cancel_search(search_id):
    """Arama işlemini iptal eder"""
    if search_id in active_searches:
        del active_searches[search_id]
        return jsonify({
            'success': True,
            'message': 'Arama iptal edildi'
        })

    return jsonify({
        'success': False,
        'error': 'Arama bulunamadı'
    }), 404


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint bulunamadı'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Sunucu hatası'
    }), 500


if __name__ == '__main__':
    # Gerekli klasörü oluştur
    os.makedirs(BASE_DIR, exist_ok=True)

    print("Server başlatılıyor...")
    print("Ana sayfa: http://localhost:5000")
    print("API Health Check: http://localhost:5000/api/health")

    # Flask uygulamasını başlat
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)