/*
  CitizenTech — estação de demonstração no Wokwi (ESP32)

  Sensores:
    - HC-SR04 (ultrassônico) instalado acima do rio: nível = altura do sensor - distância até a água
    - Potenciômetro fazendo papel de pluviômetro: chuva (mm) nos últimos 10 minutos
    - Sensor de presença (PIR) na porta do abrigo: +1 pessoa a cada entrada
    - Botão "saída": -1 pessoa
    PIR e botão são lidos por interrupção: um toque rápido no botão, ou uma entrada enquanto
    a placa publica ou reconecta ao broker, não se perde.
  Atuador:
    - LED vermelho acende quando o nível passa da cota de alerta (funciona mesmo sem internet)

  Publica no broker MQTT público (o Wokwi gratuito não alcança o computador local).
  A ponte (docker compose --profile wokwi) confere a assinatura e repassa ao broker local.
  Formato da mensagem: contratos/leitura.v1.schema.json + campo "assinatura" (HMAC-SHA256).
*/
#include <WiFi.h>
#include <PubSubClient.h>
#include <time.h>
#include "mbedtls/md.h"

// ---- iguais ao .env (WOKWI_PREFIXO e WOKWI_CHAVE). Chave de DEMONSTRAÇÃO: o projeto é público.
const char* PREFIXO = "gs20262-citizentech-421c5520aa65";
const char* CHAVE = "6c4dbe1fe811caa16936fbe757849afc";
const char* BROKER = "broker.hivemq.com";

// ---- estação de demonstração (cotas iguais às de demo-wokwi em estacoes.csv)
const float ALTURA_SENSOR_M = 4.0;  // sensor a 4 m do fundo do rio
const float COTA_ALERTA_M = 1.2;
const float CHUVA_MAX_MM = 30.0;    // potenciômetro no máximo = 30 mm em 10 min
const unsigned long INTERVALO_MS = 5000;  // a ponte aceita no máximo 1 mensagem/s por sensor

// ---- pinos
const int PINO_TRIG = 5;
const int PINO_ECHO = 18;
const int PINO_CHUVA = 34;
const int PINO_PIR = 27;
const int PINO_SAIDA = 26;
const int PINO_LED = 2;

WiFiClient wifi;
PubSubClient mqtt(wifi);
int ocupacao = 0;
unsigned long ultimoEnvio = 0;
float ultimoNivel = 0;

// Contadores preenchidos pelas interrupções e esvaziados no loop()
const unsigned long DEBOUNCE_MS = 200;  // ignora o "repique" mecânico do botão
volatile int entradasPendentes = 0;
volatile int saidasPendentes = 0;
volatile unsigned long ultimaSaidaMs = 0;
portMUX_TYPE trava = portMUX_INITIALIZER_UNLOCKED;  // protege os contadores entre interrupção e loop()

void IRAM_ATTR aoEntrar() {  // borda de subida do PIR = alguém entrou
  portENTER_CRITICAL_ISR(&trava);
  entradasPendentes++;
  portEXIT_CRITICAL_ISR(&trava);
}

void IRAM_ATTR aoSair() {  // botão pressionado (vai para LOW) = alguém saiu
  unsigned long agora = millis();
  portENTER_CRITICAL_ISR(&trava);
  if (agora - ultimaSaidaMs >= DEBOUNCE_MS) {
    saidasPendentes++;
    ultimaSaidaMs = agora;
  }
  portEXIT_CRITICAL_ISR(&trava);
}

String hmacHex(const String& texto) {
  byte saida[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char*)CHAVE, strlen(CHAVE));
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)texto.c_str(), texto.length());
  mbedtls_md_hmac_finish(&ctx, saida);
  mbedtls_md_free(&ctx);
  String hex;
  for (int i = 0; i < 32; i++) {
    if (saida[i] < 16) hex += "0";
    hex += String(saida[i], HEX);
  }
  return hex;
}

String horarioUtc() {
  time_t agora = time(nullptr);
  struct tm utc;
  gmtime_r(&agora, &utc);
  char texto[25];
  strftime(texto, sizeof(texto), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return String(texto);
}

// seq = milissegundos desde 1970: sempre cresce, mesmo se a placa reiniciar
unsigned long long seqAgora() {
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  return (unsigned long long)tv.tv_sec * 1000ULL + tv.tv_usec / 1000;
}

void publicar(const char* sensorId, float valor, const char* unidade) {
  String medidoEm = horarioUtc();
  char seqTexto[21];
  snprintf(seqTexto, sizeof(seqTexto), "%llu", seqAgora());
  String seq(seqTexto);
  String valorTexto = String(valor, 2);  // 2 casas: é o mesmo texto que a ponte confere na assinatura
  String assinatura = hmacHex(String(sensorId) + "|" + seq + "|" + medidoEm + "|" + valorTexto);
  String json = String("{\"v\":1,\"sensor_id\":\"") + sensorId + "\",\"valor\":" + valorTexto +
                ",\"unidade\":\"" + unidade + "\",\"medido_em\":\"" + medidoEm + "\",\"seq\":" + seq +
                ",\"assinatura\":\"" + assinatura + "\"}";
  String topico = String(PREFIXO) + "/" + sensorId;
  bool ok = mqtt.publish(topico.c_str(), json.c_str());
  Serial.printf("%s %s\n", ok ? "enviado" : "FALHOU", json.c_str());
}

float medirNivel() {
  digitalWrite(PINO_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);
  long duracao = pulseIn(PINO_ECHO, HIGH, 30000);
  if (duracao == 0) return ultimoNivel;  // sem eco: mantém a última leitura
  float distanciaM = duracao * 0.0343 / 2.0 / 100.0;
  float nivel = ALTURA_SENSOR_M - distanciaM;
  return nivel < 0 ? 0 : nivel;
}

void conectarWifi() {
  WiFi.begin("Wokwi-GUEST", "", 6);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
    Serial.print(".");
  }
  Serial.println(" conectado");
  configTime(0, 0, "pool.ntp.org");  // horário UTC
  while (time(nullptr) < 1700000000) delay(200);
  Serial.println("Relógio sincronizado: " + horarioUtc());
}

void conectarMqtt() {
  while (!mqtt.connected()) {
    String id = "esp32-citizentech-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    if (mqtt.connect(id.c_str())) {
      Serial.println("MQTT conectado em " + String(BROKER));
    } else {
      delay(1000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PINO_TRIG, OUTPUT);
  pinMode(PINO_ECHO, INPUT);
  pinMode(PINO_PIR, INPUT);
  pinMode(PINO_SAIDA, INPUT_PULLUP);
  pinMode(PINO_LED, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(PINO_PIR), aoEntrar, RISING);
  attachInterrupt(digitalPinToInterrupt(PINO_SAIDA), aoSair, FALLING);
  conectarWifi();
  mqtt.setServer(BROKER, 1883);
  conectarMqtt();
}

void loop() {
  if (!mqtt.connected()) conectarMqtt();
  mqtt.loop();

  // Contagem de pessoas no abrigo: soma o que as interrupções registraram desde a última volta
  portENTER_CRITICAL(&trava);
  int entradas = entradasPendentes;
  int saidas = saidasPendentes;
  entradasPendentes = 0;
  saidasPendentes = 0;
  portEXIT_CRITICAL(&trava);
  ocupacao = max(0, ocupacao + entradas - saidas);

  // Alerta local: funciona mesmo sem internet
  ultimoNivel = medirNivel();
  digitalWrite(PINO_LED, ultimoNivel >= COTA_ALERTA_M ? HIGH : LOW);

  if (millis() - ultimoEnvio >= INTERVALO_MS) {
    ultimoEnvio = millis();
    float chuva = analogRead(PINO_CHUVA) * CHUVA_MAX_MM / 4095.0;
    publicar("wok-nivel", ultimoNivel, "m");
    publicar("wok-chuva", chuva, "mm");
    publicar("wok-ocup", ocupacao, "pessoas");
  }
  delay(50);
}
