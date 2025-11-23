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

