# 🔍 LinkedIn Profile Finder & Analyzer

AI destekli bu proje, isim, şehir, meslek ve üniversite bilgilerini kullanarak LinkedIn profillerini bulur, içeriklerini analiz eder ve özetler.  
Google Custom Search API, Selenium, Gemini API ve NLP tabanlı embedding modelleriyle en alakalı profilleri listeler.  

---

## 🚀 Özellikler

- 🌐 **Google Custom Search API** ile LinkedIn profillerini bulur.  
- 🤖 **Gemini API** ile doğal, sohbet tarzı özetler üretir.  
- 🧠 **Sentence Transformers (MiniLM)** ile profil-kategori uyumunu ölçer.  
- 🔑 **Kategori Bazlı Skorlama** (teknoloji, mühendislik, sağlık, hukuk, iş dünyası, tasarım, danışmanlık).  
- 📊 **Alaka Skoru Hesaplama** → %60 keyword eşleşmesi + %40 vektör benzerliği.  
- 💻 **Flask REST API** ve modern bir **Frontend (HTML/JS/CSS)** arayüz.  
- 🔒 **LinkedIn login & profil scraping** (Selenium üzerinden).  
- 📝 JSON ve TXT formatında profil çıktıları.

---

## 📂 Proje Yapısı

```text
BitirmeFlask/
├── Absolute.py        # Çekirdek fonksiyonlar: arama, login, scraping, NLP, özetleme
├── app.py             # Flask API (backend)
├── index.html         # Frontend arayüz
├── requirements.txt   # Python bağımlılıkları
└── outputs/           # Kaydedilen JSON ve TXT özet dosyaları (BASE_DIR)
```

---

## ⚙️ Kurulum

### 1️⃣ Ortam Hazırlığı
```bash
git clone https://github.com/Cnrygt11/LinkedIn-Profle-Finder.git
cd LinkedIn-Profle-Finder/BitirmeFlask
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2️⃣ Bağımlılıkları Kur
```bash
pip install -r requirements.txt
```

### 3️⃣ Gerekli API ve Giriş Bilgilerini Tanımla
`Absolute.py` içinde kendi bilgilerini gir:
```python
API_KEY = "YOUR_GOOGLE_API_KEY"
CSE_ID = "YOUR_CSE_ID"
LINKEDIN_EMAIL = "YOUR_EMAIL"
LINKEDIN_PASSWORD = "YOUR_PASSWORD"
genai.configure(api_key="YOUR_GEMINI_API_KEY")
```

> ⚠️ **Uyarı**: LinkedIn scraping işlemleri için gerçek kullanıcı hesabı gereklidir. Deneme/özel hesap kullanmanız tavsiye edilir.

---

## ▶️ Çalıştırma

### Backend (Flask API)
```bash
python app.py
```
Çalıştırıldığında:
- API Health: [http://localhost:5000/api/health](http://localhost:5000/api/health)  
- Ana sayfa: [http://localhost:5000](http://localhost:5000)  

### Frontend
`index.html` doğrudan tarayıcıda açılabilir. Flask API’ye bağlanır.

---

## 📡 API Endpointleri

### 1. Yeni Arama Başlat
```http
POST /api/search
```
Body:
```json
{
  "name": "Ahmet Yılmaz",
  "category": "teknoloji",
  "city": "İstanbul",
  "job": "Yazılım Geliştirici",
  "university": "Boğaziçi Üniversitesi"
}
```

### 2. Durum Kontrol
```http
GET /api/search/<search_id>/status
```

### 3. Sonuçlar
```http
GET /api/search/<search_id>/results
```

### 4. Aramayı İptal Et
```http
DELETE /api/search/<search_id>
```

### 5. Kategoriler
```http
GET /api/categories
```

---

## 🎨 Arayüz

- Sol panel: arama formu (isim, kategori, şehir, meslek, üniversite).  
- Sağ panel: sonuç kartları → profil linki, AI özeti ve alaka skoru.  
- İlerleme çubuğu ve iptal butonu mevcut.  

---

## 🛠️ Kullanılan Teknolojiler

- **Backend**: Flask, Python  
- **AI/NLP**: Gemini API, SentenceTransformers, Scikit-learn  
- **Web Scraping**: Selenium  
- **Frontend**: HTML, CSS, JavaScript (fetch API)  
- **Destekleyici**: Google Custom Search API, Levenshtein, Jellyfish  

---

## 📑 Örnek Çalışma

1. “Ahmet Yılmaz” ismiyle *teknoloji* kategorisinde İstanbul filtresi eklenerek arama yapılır.  
2. Google CSE’den profiller çekilir.  
3. LinkedIn login sonrası içerikler ayrıştırılır.  
4. Gemini API ile kısa bir özet üretilir.  
5. Teknoloji kategorisine göre skorlanır.  
6. En ilgili ilk 10 profil arayüzde listelenir.  

---

## ⚠️ Uyarılar

- LinkedIn scraping, LinkedIn kullanım koşullarına aykırı olabilir. Sorumluluk kullanıcıya aittir.  
- API anahtarları gizli tutulmalıdır.  
