#!/bin/sh
# Gera o arquivo de senhas a partir das variáveis do .env (as senhas nunca ficam no git).
set -eu

: "${MQTT_INGESTOR_PASSWORD:?defina MQTT_INGESTOR_PASSWORD no .env}"
: "${MQTT_SIMULADOR_PASSWORD:?defina MQTT_SIMULADOR_PASSWORD no .env}"
: "${MQTT_PONTE_PASSWORD:?defina MQTT_PONTE_PASSWORD no .env}"

DADOS=/mosquitto/data
rm -f "$DADOS/passwd"
touch "$DADOS/passwd"
chmod 0700 "$DADOS/passwd"
mosquitto_passwd -b "$DADOS/passwd" ingestor "$MQTT_INGESTOR_PASSWORD"
mosquitto_passwd -b "$DADOS/passwd" simulador "$MQTT_SIMULADOR_PASSWORD"
mosquitto_passwd -b "$DADOS/passwd" ponte "$MQTT_PONTE_PASSWORD"

# A ACL vem do repositório (somente leitura); a cópia fica com permissão restrita.
cp /mosquitto/config/acl "$DADOS/acl"
chmod 0700 "$DADOS/acl"
chown -R mosquitto:mosquitto "$DADOS"

exec /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
