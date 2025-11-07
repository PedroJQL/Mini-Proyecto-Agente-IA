# 🔊 Sistema de Monitoreo Inteligente de Ruido

Sistema IoT para monitoreo y detección de ruido en tiempo real que combina hardware embebido (ESP32) con un backend inteligente (FastAPI) que aprende adaptativamente de los patrones de sonido y envía alertas automáticas a través de Telegram.

## 📋 Descripción

Este proyecto implementa un sistema completo de monitoreo acústico que:

- **Monitorea niveles de sonido** en tiempo real mediante un sensor conectado a ESP32
- **Detecta eventos de ruido** que superen umbrales adaptativos configurados por bandas horarias
- **Aprende automáticamente** de los patrones de ruido usando algoritmos de aprendizaje incremental (EMA)
- **Envía alertas** automáticas a través de Telegram cuando se detectan niveles anormales
- **Se adapta dinámicamente** a diferentes contextos horarios con umbrales personalizados

## ✨ Características Principales

- 🎯 **Detección Inteligente**: Sistema adaptativo que aprende de los patrones de ruido
- ⏰ **Bandas Horarias**: Diferentes umbrales según la hora del día
- 📱 **Alertas en Tiempo Real**: Notificaciones instantáneas vía Telegram
- 🔄 **Aprendizaje Continuo**: Algoritmo EMA para adaptación automática
- 🛡️ **Autenticación**: Protección mediante Bearer Token
- 📊 **Métricas de Rendimiento**: Seguimiento de falsos positivos/negativos
- 🔧 **API REST**: Endpoints para configuración y monitoreo

## 🏗️ Arquitectura

El sistema está compuesto por tres componentes principales:

1. **Hardware (ESP32)**: Captura de señales acústicas, cálculo de RMS/Pico y transmisión HTTP
2. **Backend (FastAPI)**: Procesamiento inteligente, detección de eventos y gestión de alertas
3. **Notificaciones (Telegram)**: Comunicación con el usuario final

## 📦 Requisitos

### Hardware
- ESP32 (cualquier variante con WiFi)
- Sensor de sonido analógico (micrófono con salida analógica)
- Conexión WiFi

### Software
- Python 3.8 o superior
- Arduino IDE o PlatformIO (para el firmware del ESP32)
- Librerías Arduino: WiFi, HTTPClient, ArduinoJson

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd AGENTE_IA
```

### 2. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 3. Configurar el Backend

Edita el archivo `settings.json` o configura las variables de entorno:

```json
{
  "auth_token": "tu_token_seguro",
  "telegram_token": "tu_token_de_telegram",
  "telegram_chat_id": 123456789
}
```

**O mediante variables de entorno:**
```bash
export AGENT_AUTH_TOKEN="tu_token_seguro"
export TELEGRAM_BOT_TOKEN="tu_token_telegram"
export TELEGRAM_CHAT_ID="tu_chat_id"
```

### 4. Configurar Telegram Bot

1. Crea un bot en Telegram hablando con [@BotFather](https://t.me/BotFather)
2. Obtén el token del bot
3. Obtén tu Chat ID (puedes usar [@userinfobot](https://t.me/userinfobot))
4. Agrega estos valores en `settings.json` o variables de entorno

### 5. Configurar el ESP32

1. Abre `sensor.ino` en Arduino IDE
2. Configura las credenciales WiFi:
   ```cpp
   #define WIFI_SSID "tu_red_wifi"
   #define WIFI_PASS "tu_password"
   ```
3. Configura la URL del servidor:
   ```cpp
   const char* SERVER = "http://IP_SERVIDOR:8000/ingest";
   const char* AUTH = "tu_token_seguro";
   ```
4. Sube el código al ESP32

## 🎯 Uso

### Iniciar el servidor Backend

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

El servidor estará disponible en `http://localhost:8000`

### Documentación de la API

Una vez iniciado el servidor, accede a:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📡 Endpoints de la API

### `GET /status`
Obtiene el estado actual del sistema.

**Headers:**
```
Authorization: Bearer tu_token
```

**Respuesta:**
```json
{
  "ok": true,
  "now": "2024-01-01T12:00:00",
  "kb": {...},
  "settings": {...}
}
```

### `POST /ingest`
Recibe datos del sensor ESP32.

**Headers:**
```
Authorization: Bearer tu_token
Content-Type: application/json
```

**Body:**
```json
{
  "device_id": "esp32-a1",
  "ts": 1704110400,
  "rms": 95.5,
  "peak": 180,
  "v": 1
}
```

### `POST /setband`
Configura o crea una banda horaria.

**Body:**
```json
{
  "name": "band1",
  "start": "08:00",
  "end": "12:00"
}
```

### `POST /setk`
Ajusta el multiplicador de sensibilidad (k) de una banda.

**Body:**
```json
{
  "name": "band1",
  "k": 3.0
}
```

### `POST /fp`
Marca un falso positivo (aumenta el umbral).

### `POST /fn`
Marca un falso negativo (disminuye el umbral).

## 🔧 Configuración de Bandas Horarias

El sistema permite configurar diferentes umbrales según la hora del día:

- **Band1**: Día (08:00 - 12:00) - Umbral medio
- **Band2**: Tarde (14:00 - 20:00) - Umbral alto
- **Band3**: Noche (21:00 - 05:00) - Umbral bajo

Cada banda tiene:
- `mu_rms`: Media RMS adaptativa
- `sigma_rms`: Desviación estándar adaptativa
- `k`: Multiplicador de umbral (2.0 - 4.0)
- `samples`: Contador de muestras procesadas

## 🧠 Algoritmo de Aprendizaje

El sistema utiliza **Exponential Moving Average (EMA)** para adaptarse automáticamente:

```
μ_new = (1 - α) × μ_old + α × rms_new
σ_new = (1 - α) × σ_old + α × |rms_new - μ_new|
```

Donde:
- `α = 0.1` (factor de aprendizaje)
- `μ`: Media RMS de la banda
- `σ`: Desviación estándar de la banda

## 📁 Estructura del Proyecto

```
AGENTE_IA/
│
├── app.py                 # Servidor FastAPI principal
├── sensor.ino             # Código firmware para ESP32
├── requirements.txt       # Dependencias de Python
├── settings.json          # Configuración (tokens, IDs)
├── kb_noise.json          # Base de conocimiento (bandas, estadísticas)
└── README.md              # Este archivo
```

## 🔐 Seguridad

- **Cambia el token de autenticación** por defecto en producción
- Usa **HTTPS** en producción (requiere configuración adicional)
- No compartas tus tokens de Telegram públicamente
- Considera usar variables de entorno para valores sensibles

## 🐛 Solución de Problemas

### El ESP32 no se conecta al WiFi
- Verifica las credenciales WiFi en `sensor.ino`
- Asegúrate de que la red WiFi esté disponible
- Verifica la señal WiFi (RSSI)

### No se reciben alertas en Telegram
- Verifica que el token de Telegram sea correcto
- Verifica que el Chat ID sea el correcto
- Revisa los logs del servidor para errores

### El sistema no detecta eventos
- Verifica que el warmup esté completado (300 muestras)
- Ajusta el multiplicador `k` según sea necesario
- Revisa los umbrales en `kb_noise.json`

## 📊 Ejemplo de Uso con cURL

### Ver estado del sistema
```bash
curl -X GET http://localhost:8000/status \
  -H "Authorization: Bearer tokenarduino"
```

### Configurar banda horaria
```bash
curl -X POST http://localhost:8000/setband \
  -H "Authorization: Bearer tokenarduino" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "band1",
    "start": "08:00",
    "end": "12:00"
  }'
```

### Ajustar sensibilidad
```bash
curl -X POST http://localhost:8000/setk \
  -H "Authorization: Bearer tokenarduino" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "band1",
    "k": 2.5
  }'
```

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👨‍💻 Autor

Proyecto desarrollado para monitoreo inteligente de ruido ambiental.

## 📞 Soporte

Para preguntas o soporte, abre un issue en el repositorio del proyecto.

---

**Versión**: 1.1  
**Última actualización**: 2024

