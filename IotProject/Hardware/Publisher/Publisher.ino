#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"

//SSID and PASSWORD of your MQTT's network
const char* ssid = "iotvanier";
const char* password = "14730078";

//MQTT SERVER IP
const char* mqtt_server = "192.168.0.106";

//SET THE VIRTUAL PINS FOR THE DHT11 SENSORS
#define DHTPIN1 4
#define DHTPIN2 17
#define DHTTYPE DHT11

//Initialization
DHT dhtFrig1(DHTPIN1, DHTTYPE);
DHT dhtFrig2(DHTPIN2, DHTTYPE);

//Setup the client
WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
char msg[50];
int value = 0;



void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  //activate the sensors
  dhtFrig1.begin();
  dhtFrig2.begin();
}


void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  //wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  //connection has been set
  Serial.println("\nWiFi connected");
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    String clientId = "ESP32Client"
    clientId += String(random(oxffff), HEX); //EXPLAIN THIS LINE
    if (client.connect(clientId.cstr())) {
      Serial.println("connected");
      // Subscribe
      //client.subscribe("esp32/output");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  long now = millis();
  if(now - lastMsg > 2000){
    lastMsg = now;
  }
  float humidity1 = dhtFrig1.readHumidity();
  float temperature1 = dhtFrig1.readTemperature();
  float humidity2 = dhtFrig2.readHumidity();
  float temperature2 = dhtFrig2.readTemperature();
  if(!isnan(temperature1) && !isnan(humidity1)){
    String sensorData1 = "{\"temperature\": " + String(temperature1) + ", \"humidity\": " + String(humidity1) + "}";
    client.publish("Frig1", sensorData1.c_str());
      Serial.print("Frig1 Data Published: ");
      delay(2000);
      Serial.println(sensorData1);
    } else {
      Serial.println("Error: Could not read Sensor 1");
  }
  if(!isnan(temperature2) && !isnan(humidity2)){
    String sensorData2 = "{\"temperature\": " + String(temperature2) + ", \"humidity\": " + String(humidity2) + "}";
    client.publish("Frig2", sensorData2.c_str());
      Serial.print("Frig2 Data Published: ");
      delay(2000);
      Serial.println(sensorData2);
    } else {
      Serial.println("Error: Could not read Sensor 1");
  }
}