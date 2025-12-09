# MLflow Experiment Tracking Repository

Bu repo, makine öğrenmesi projelerinde **deney takibi**, **model versiyonlama**, **artifakt yönetimi** ve **tekrarlanabilir MLOps süreçleri** oluşturmak için yapılandırılmış bir MLflow altyapısı içerir. Kod tabanı, sade bir proje yapısı üzerinde MLflow’un yerel (local) kullanımına odaklanır.

---

## 🚀 Amaç

Bu proje, model geliştirme sürecindeki tüm deneyleri merkezi bir yapıda takip etmeyi sağlar:

- Deney parametreleri ve metriklerin kaydı  
- Modellerin otomatik versiyonlanması  
- Yerel MLflow UI ile takip  
- Kolay test, geliştirme ve demo ortamı  

MLflow’u “tek dosyalık minimal bir tracking server” olarak kullanmak isteyenler için idealdir.

---

## 📁 Proje Yapısı

```
mlflow/
│
├── mlflow.db           # SQLite backend-store (MLflow meta)
├── mlruns/             # MLflow artifact store
├── .env                # Ortam değişkenleri (opsiyonel)
├── train.py            # Deneme amaçlı MLflow log script'i
└── README.md           # Bu dosya
```

---

## 🔧 Kurulum

### 1) Gerekli paketleri kur

```bash
pip install -r requirements.txt
```

veya

```bash
pip install mlflow
```

---

## 🏁 MLflow Tracking Server Başlatma

Repo kök dizininde şu komutu çalıştır:

```bash
mlflow server   --backend-store-uri sqlite:///mlflow.db   --default-artifact-root ./mlruns   --host 127.0.0.1   --port 5000
```

Arayüz adresi:  
👉 http://127.0.0.1:5000

---

## 🧪 Örnek Eğitim Scripti

Bu repo içinde basit bir MLflow test script’i bulunuyor: `train.py`

Çalıştırmak için:

```bash
python train.py
```

Script, MLflow üzerinde aşağıdakileri otomatik loglar:

- Parametreler  
- Metrikler  
- Model (pickle formatında)  
- Çıktılar  

---

## 🔍 Deney Kayıtlarını Görüntüleme

Çalışan MLflow server üzerinden:

- Run ID
- Parametreler
- Metrikler
- Artifact’ler (model dosyası vs.)

hepsini UI’dan inceleyebilirsin.

---

## 📦 Model Yükleme (Prediction)

Kaydedilmiş bir modeli yüklemek için:

```python
import mlflow.pyfunc

model = mlflow.pyfunc.load_model("runs:/<RUN_ID>/model")
pred = model.predict(input_data)
```

---

## 🧠 Teknoloji Stack

- **Python 3.11+**
- **MLflow**
- **SQLite backend store**
- **Local artifact storage (mlruns/)**

---

## 👤 Geliştirici

**Seyit Kaan Güneş**  
AI / ML Developer  
GitHub: https://github.com/SeyitKaanGunes

---

Bu repo, “minir MLflow altyapısı isteyenler imal ama etkili” biçin hazırlanmıştır.
Daha gelişmiş bir pipeline (DVC, Docker, model registry, CI/CD) eklemek istersen yapı buna uygun şekilde genişletilebilir.

## 🔐 Adalet, Güvenlik, Governance ve SBOM

- Fairlearn: Grup bazlı adalet ve parite farkları için `python assurance_suite.py --skip-giskard --skip-credo --skip-sbom` komutunu çalıştır; çıktılar `artifacts/assurance/fairlearn/` altında.
- Giskard (güvenlik/sağlamlık): Python 3.10/3.11 ortamında `pip install giskard` sonrası `python assurance_suite.py --skip-fairlearn --skip-credo --skip-sbom` komutuyla çıktılar `artifacts/assurance/giskard/` altında oluşur. 3.13 için GISKARD_SKIPPED.txt notunu kontrol et.
- Credo AI (yönetim/uyum): `python assurance_suite.py` governance taslağını `artifacts/assurance/governance/` klasörüne yazar. Tam Lens deneyimi için Python 3.10/3.11 + `pip install credoai-lens` kullan.
- CycloneDX SBOM: `python assurance_suite.py --skip-fairlearn --skip-giskard --skip-credo` veya doğrudan `cyclonedx-bom --format json -o artifacts/assurance/sbom/sbom.json` komutu ile tedarik zinciri listesi yarat.
- Hepsi bir arada: `python assurance_suite.py` komutu adalet, güvenlik (kuruluysa), governance taslağı ve SBOM çıktısı üretir; özet `artifacts/assurance/assurance_summary.json` dosyasında.
