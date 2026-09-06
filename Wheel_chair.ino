#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// Create Hotspot
const char* ssid = "WHEELCHAIR_CTRL";
const char* password = "12345678";

// Home ESP IP (fixed)
const char* homeESP = "192.168.4.2";

WebServer server(80);

// Motor Pins
#define IN1 14
#define IN2 27
#define IN3 26
#define IN4 25
#define ENA 13
#define ENB 12

// Safety Sensor Pins (2 HC-SR04 Sensors)
#define US_FRONT_TRIG 4
#define US_FRONT_ECHO 16
#define US_BACK_TRIG 17
#define US_BACK_ECHO 5

#define BUZZER_PIN 22

// LDR & Face Light Pins
#define LDR_PIN 34
#define FACE_LED_PIN 32

// Parameters
int speedValue = 120;
unsigned long lastCmdTime = 0;
const unsigned long WATCHDOG_TIMEOUT = 1500; // 1.5 seconds safety stop

enum MovementState { STATE_STOP, STATE_FORWARD, STATE_BACKWARD, STATE_LEFT, STATE_RIGHT };
MovementState currentState = STATE_STOP;

// Sensor States
float distFront = 100.0;
float distBack = 100.0;
bool edgeDetected = false;
bool fireAlarm = false;

// Send to Home ESP
void sendToHome(String path) {
  HTTPClient http;
  String url = "http://" + String(homeESP) + path;
  http.begin(url);
  http.GET();
  http.end();
}

// Read HC-SR04 distance in cm
float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000); // 30ms timeout
  if (duration == 0) return 400.0; // Out of range
  return duration * 0.0343 / 2.0;
}

// Motor driving functions with safety watchdog logging
void forward(){
  if (distFront < 30.0 || edgeDetected || fireAlarm) {
    stopCar();
    return;
  }
  currentState = STATE_FORWARD;
  lastCmdTime = millis();
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}

void backward(){
  if (distBack < 30.0 || fireAlarm) {
    stopCar();
    return;
  }
  currentState = STATE_BACKWARD;
  lastCmdTime = millis();
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}

void left(){
  if (fireAlarm) {
    stopCar();
    return;
  }
  currentState = STATE_LEFT;
  lastCmdTime = millis();
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}

void right(){
  if (fireAlarm) {
    stopCar();
    return;
  }
  currentState = STATE_RIGHT;
  lastCmdTime = millis();
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}

void stopCar(){
  currentState = STATE_STOP;
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}

// ===== UI =====
const char webpage[] PROGMEM = R"====(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Wheelchair</title>

<style>
body { font-family: Arial; text-align: center; background:#1e3c72; color:white; }

.box {
  margin:20px;
  padding:20px;
  background:rgba(255,255,255,0.1);
  border-radius:15px;
}

.button {
  width:80px; height:80px;
  margin:5px;
  border:none;
  border-radius:10px;
  background:#444;
  color:white;
}

.button.active { background:#00c6ff; }
</style>

<script>
let interval;

function startCmd(btn,cmd){
  btn.classList.add("active");
  interval=setInterval(()=>fetch("/"+cmd),100);
}

function stopCmd(btn){
  btn.classList.remove("active");
  clearInterval(interval);
  fetch("/S");
}

function sendHome(cmd){
  fetch("/home/"+cmd);
}
</script>

</head>

<body>

<h2>SMART WHEELCHAIR</h2>

<div class="box">
<h3>Movement</h3>

<button class="button" onmouseenter="startCmd(this,'F')" onmouseleave="stopCmd(this)">FWD</button><br>

<button class="button" onmouseenter="startCmd(this,'L')" onmouseleave="stopCmd(this)">LEFT</button>
<button class="button" onmouseenter="startCmd(this,'S')" onmouseleave="stopCmd(this)">STOP</button>
<button class="button" onmouseenter="startCmd(this,'R')" onmouseleave="stopCmd(this)">RIGHT</button><br>

<button class="button" onmouseenter="startCmd(this,'B')" onmouseleave="stopCmd(this)">REV</button>
</div>

<div class="box">
<h3>Home Control</h3>

<button class="button" onclick="sendHome('light_on')">Light ON</button>
<button class="button" onclick="sendHome('light_off')">Light OFF</button><br><br>

<button class="button" onclick="sendHome('fan_on')">Fan ON</button>
<button class="button" onclick="sendHome('fan_off')">Fan OFF</button>

</div>

</body>
</html>
)====";

void setup(){
  Serial.begin(115200);

  pinMode(IN1,OUTPUT);
  pinMode(IN2,OUTPUT);
  pinMode(IN3,OUTPUT);
  pinMode(IN4,OUTPUT);

  // Safety sensors setup
  pinMode(US_FRONT_TRIG, OUTPUT);
  pinMode(US_FRONT_ECHO, INPUT);
  pinMode(US_BACK_TRIG, OUTPUT);
  pinMode(US_BACK_ECHO, INPUT);

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // LDR & Face Light setup
  pinMode(LDR_PIN, INPUT);
  pinMode(FACE_LED_PIN, OUTPUT);
  digitalWrite(FACE_LED_PIN, LOW);

  ledcSetup(0,1000,8);
  ledcAttachPin(ENA,0);
  ledcWrite(0,speedValue);

  ledcSetup(1,1000,8);
  ledcAttachPin(ENB,1);
  ledcWrite(1,speedValue);

  // Start Hotspot
  WiFi.softAP(ssid,password);

  Serial.println(WiFi.softAPIP()); // 192.168.4.1

  server.on("/", [](){ server.send(200,"text/html",webpage); });

  // Car locomotion requests
  server.on("/F", [](){ forward(); server.send(200,"OK"); });
  server.on("/B", [](){ backward(); server.send(200,"OK"); });
  server.on("/L", [](){ left(); server.send(200,"OK"); });
  server.on("/R", [](){ right(); server.send(200,"OK"); });
  server.on("/S", [](){ stopCar(); server.send(200,"OK"); });

  // Safety status endpoint (for Python client feedback)
  server.on("/status", [](){
    String json = "{";
    json += "\"distFront\":" + String(distFront) + ",";
    json += "\"distBack\":" + String(distBack) + ",";
    json += "\"edgeDetected\":" + String(edgeDetected ? 1 : 0) + ",";
    json += "\"fireAlarm\":" + String(fireAlarm ? 1 : 0);
    json += "}";
    server.send(200, "application/json", json);
  });

  // Home control routes
  server.on("/home/light_on", [](){ sendToHome("/light/on"); server.send(200,"OK"); });
  server.on("/home/light_off", [](){ sendToHome("/light/off"); server.send(200,"OK"); });
  server.on("/home/fan_on", [](){ sendToHome("/fan/on"); server.send(200,"OK"); });
  server.on("/home/fan_off", [](){ sendToHome("/fan/off"); server.send(200,"OK"); });

  server.begin();
  lastCmdTime = millis();
}

void loop(){
  server.handleClient();

  // 1. Safety Watchdog (If active locomotion without client heartbeat, stop)
  if (currentState != STATE_STOP && (millis() - lastCmdTime > WATCHDOG_TIMEOUT)) {
    stopCar();
    Serial.println("Watchdog safety stop triggered.");
  }

  // 2. Poll Sensors (2 HC-SR04 Sensors: Front and Back)
  distFront = getDistance(US_FRONT_TRIG, US_FRONT_ECHO);
  distBack = getDistance(US_BACK_TRIG, US_BACK_ECHO);

  // Auto Face Light Control based on LDR (dim threshold ~1200 on 4095 scale)
  int ldrVal = analogRead(LDR_PIN);
  if (ldrVal < 1200) {
    digitalWrite(FACE_LED_PIN, HIGH);
  } else {
    digitalWrite(FACE_LED_PIN, LOW);
  }

  // 3. Safety Action and Audible Buzzer indicators (Obstacle Avoidance via Front/Back sensor depending on movement direction)
  if (currentState == STATE_FORWARD && distFront < 30.0) {
    stopCar();
    // Warn override chirp
    digitalWrite(BUZZER_PIN, HIGH); delay(300);
    digitalWrite(BUZZER_PIN, LOW);
  } 
  else if (currentState == STATE_BACKWARD && distBack < 30.0) {
    stopCar();
    // Warn override chirp
    digitalWrite(BUZZER_PIN, HIGH); delay(300);
    digitalWrite(BUZZER_PIN, LOW);
  }
  else if ((currentState == STATE_FORWARD && distFront < 60.0) || (currentState == STATE_BACKWARD && distBack < 60.0)) {
    // Early warning chirp
    digitalWrite(BUZZER_PIN, HIGH); delay(50);
    digitalWrite(BUZZER_PIN, LOW);
  }
  else {
    digitalWrite(BUZZER_PIN, LOW);
  }

  // Maintain equal speed (no wall-following bias needed for front/back configuration)
  ledcWrite(0, speedValue);
  ledcWrite(1, speedValue);

  delay(50);
}