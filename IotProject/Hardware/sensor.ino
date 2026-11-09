#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
// 1. UPDATE THESE WITH YOUR ACTUAL NETWORK DETAILS
const char* ssid = "HomeHelix";
const char* password = "12345678";

// 2. UPDATE THIS WITH YOUR RASPBERRY PI'S IP ADDRESS (e.g., 192.168.1.50)
const char* mqtt_server = "10.0.0.148";

// 3. DEFINE PINS FOR BOTH SENSORS
#define DHTPIN1 4     // Data wire for Fridge 1 sensor
#define DHTPIN2 17     // Data wire for Fridge 2 sensor
#define DHTTYPE DHT11 // Or DHT22 depending on your hardware

// Initialize both sensors
DHT dht1(DHTPIN1, DHTTYPE);
DHT dht2(DHTPIN2, DHTTYPE);

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32DualClient-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  
  // Start both sensors
  dht1.begin();
  dht2.begin();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  long now = millis();
  
  // Fire every 2 seconds
  if (now - lastMsg > 2000) { 
    lastMsg = now;

    // Read Sensor 1
    float t1 = dht1.readTemperature();
    float h1 = dht1.readHumidity();

    // Read Sensor 2
    float t2 = dht2.readTemperature();
    float h2 = dht2.readHumidity();

    // Process and Publish Fridge 1
    if (!isnan(t1) && !isnan(h1)) {
      String payload1 = "{\"temperature\": " + String(t1) + ", \"humidity\": " + String(h1) + "}";
      client.publish("Frig1", payload1.c_str());
      Serial.print("Frig1 Published: ");
      Serial.println(payload1);
    } else {
      Serial.println("Error: Could not read Sensor 1");
    }

    // Process and Publish Fridge 2
    if (!isnan(t2) && !isnan(h2)) {
      String payload2 = "{\"temperature\": " + String(t2) + ", \"humidity\": " + String(h2) + "}";
      client.publish("Frig2", payload2.c_str());
      Serial.print("Frig2 Published: ");
      Serial.println(payload2);
    } else {
      Serial.println("Error: Could not read Sensor 2");
    }
  }
}