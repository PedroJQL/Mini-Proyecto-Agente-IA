/*#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ======= WiFi =======
#define WIFI_SSID "TIGO-32F9_plus"
#define WIFI_PASS "2NB112104406"

// ======= ADC / Sensibilidad =======
#define ADC_PIN    36          // ADC1_CH0 (estable con WiFi)
#define N_SAMPLES  256         // ↑ ventana para RMS estable
#define GAIN       2.5f        // ↑ ganancia por software (pruebas: 1.5–3.0)
#define SAMPLE_US  200         // 200 µs ≈ 5 kHz (antes 250 µs)

// ======= Backend =======
const char* SERVER = "http://192.168.0.2:8000/ingest";
const char* AUTH   = "tokenarduino";
const char* DEVICE = "esp32-a1";

// ----------------------
// Conexión WiFi
// ----------------------
void wifiConnect() {
  Serial.println("\n[WiFi] Conectando...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (millis() - t0 > 15000) {
      Serial.println("\n[WiFi] Reintentando...");
      WiFi.disconnect(true);
      delay(1000);
      WiFi.begin(WIFI_SSID, WIFI_PASS);
      t0 = millis();
    }
  }
  Serial.println("\n[WiFi] Conectado ✅");
  Serial.print("[WiFi] IP: ");   Serial.println(WiFi.localIP());
  Serial.print("[WiFi] RSSI: "); Serial.println(WiFi.RSSI());
}

// ----------------------
// Medición base en silencio (1s) para referencia
// ----------------------
float baseline_rms = 0.0f;

float measureRMSOnce(uint16_t nsamp, uint16_t us_delay) {
  // media de la ventana para quitar DC real
  uint32_t sum = 0;
  for (int i=0;i<nsamp;i++){ sum += analogRead(ADC_PIN); delayMicroseconds(us_delay); }
  float mean = (float)sum / nsamp;

  unsigned long sumSq = 0;
  for (int i=0;i<nsamp;i++){
    int x = analogRead(ADC_PIN);
    float d = (x - mean) * GAIN;            // << ganancia por software
    sumSq += (unsigned long)(d * d);
    delayMicroseconds(us_delay);
  }
  return sqrt((float)sumSq / nsamp);
}

void autoCalibrate(uint32_t ms=1000){
  uint32_t t0 = millis();
  uint32_t cnt = 0;
  double acc = 0.0;
  while (millis() - t0 < ms) {
    acc += measureRMSOnce(64, SAMPLE_US);
    cnt++;
  }
  baseline_rms = (float)(acc / max<uint32_t>(1,cnt));
  Serial.printf("[CAL] baseline_rms=%.2f (1s)\n", baseline_rms);
}

// ----------------------
// RMS/Pico por ventana (sin DC, con ganancia)
// ----------------------
float readRMSPeak(float &peak) {
  // media por ventana
  uint32_t sum = 0;
  for (int i=0;i<N_SAMPLES;i++){ sum += analogRead(ADC_PIN); delayMicroseconds(SAMPLE_US); }
  float mean = (float)sum / N_SAMPLES;

  unsigned long sumSq = 0;
  int pk = 0;
  for (int i=0;i<N_SAMPLES;i++){
    int x = analogRead(ADC_PIN);
    int d = (int)((x - mean) * GAIN);       // << ganancia por software
    int a = d >= 0 ? d : -d;
    if (a > pk) pk = a;
    sumSq += (unsigned long)(d * d);
    delayMicroseconds(SAMPLE_US);
  }
  peak = (float)pk;
  return sqrt((float)sumSq / N_SAMPLES);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  // Ajustes recomendados del ADC del ESP32
  analogSetWidth(12);
  analogSetPinAttenuation(ADC_PIN, ADC_11db);  // 0–~3.6 V

  wifiConnect();
  autoCalibrate(1000); // mide ruido de fondo 1s (solo informativo)
}

void loop() {
  float peak = 0;
  float rms  = readRMSPeak(peak);

  // Debug
  Serial.printf("[ADC] rms=%.1f  peak=%d  (base=%.1f)\n", rms, (int)peak, baseline_rms);

  // ---- Payload JSON ----
  StaticJsonDocument<256> doc;
  doc["device_id"] = DEVICE;
  doc["ts"]  = (uint32_t)(millis()/1000);
  doc["rms"] = rms;
  doc["peak"] = (int)peak;
  doc["v"] = 1;

  char buf[256];
  size_t n = serializeJson(doc, buf);

  // ---- POST HTTP ----
  HTTPClient http;
  http.begin(SERVER);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + AUTH);
  http.setTimeout(4000);

  int code = http.POST((uint8_t*)buf, n);
  if (code > 0) {
    String resp = http.getString();
    Serial.printf("POST %d: %s\n", code, resp.c_str());
  } else {
    Serial.printf("HTTP error: %d\n", code);
  }
  http.end();

  delay(100); // ~10 Hz
}
*/