#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "WHEELCHAIR_CTRL";
const char* password = "12345678";

WebServer server(80);

// Relay pins
#define LIGHT_PIN 26
#define FAN_PIN 27

void setup(){
  Serial.begin(115200);

  pinMode(LIGHT_PIN,OUTPUT);
  pinMode(FAN_PIN,OUTPUT);

  digitalWrite(LIGHT_PIN,HIGH);
  digitalWrite(FAN_PIN,HIGH);

  WiFi.begin(ssid,password);

  while(WiFi.status()!=WL_CONNECTED){
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected to Wheelchair ESP!");
  Serial.println(WiFi.localIP()); // should be 192.168.4.2

  server.on("/light/on", [](){
    digitalWrite(LIGHT_PIN,LOW);
    server.send(200,"OK");
  });

  server.on("/light/off", [](){
    digitalWrite(LIGHT_PIN,HIGH);
    server.send(200,"OK");
  });

  server.on("/fan/on", [](){
    digitalWrite(FAN_PIN,LOW);
    server.send(200,"OK");
  });

  server.on("/fan/off", [](){
    digitalWrite(FAN_PIN,HIGH);
    server.send(200,"OK");
  });

  server.begin();
}

void loop(){
  server.handleClient();
}