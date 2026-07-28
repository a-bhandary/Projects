/*
 * IR Remote-Controlled Cooling Fan System - BASIC VERSION
 * 
 * Features:
 * - Power On/Off control with RED button
 * - Speed UP with UP arrow (increases speed)
 * - Speed DOWN with DOWN arrow (decreases speed)
 * - Direct speed selection with buttons 1, 2, 3
 * 
 * IR Remote Button Mapping (adjust codes for your remote):
 * RED button (Power): 0xFF00BF00
 * UP arrow (Speed Up): 0xF50ABF00
 * DOWN arrow (Speed Down): 0xF708BF00
 * Button 1 (Low): 0xEF10BF00
 * Button 2 (Med): 0xEE11BF00
 * Button 3 (High): 0xED12BF00
 */

#include <IRremote.h>

// Pin Definitions
#define IR_RECEIVE_PIN 2      // IR receiver data pin
#define MOTOR_EN 8             // L293D Enable pin (PWM for speed control)
#define MOTOR_IN1 9            // L293D Input 1
#define MOTOR_IN2 7            // L293D Input 2

// IR Remote Button Codes (CHANGE THESE to match YOUR remote!)
#define BTN_POWER 0xFF00BF00      // RED button - Power On/Off
#define BTN_SPEED_UP 0xF50ABF00   // UP arrow - Increase speed
#define BTN_SPEED_DOWN 0xF708BF00 // DOWN arrow - Decrease speed
#define BTN_1 0xEF10BF00          // Button 1 - LOW
#define BTN_2 0xEE11BF00          // Button 2 - MEDIUM
#define BTN_3 0xED12BF00          // Button 3 - HIGH

// Speed PWM values (0-255) - Optimized for 3-6V motors
#define SPEED_OFF 0
#define SPEED_LOW 150      // ~60% power
#define SPEED_MED 200      // ~80% power
#define SPEED_HIGH 255     // 100% power

// Global Variables
bool fanOn = false;
int currentSpeed = 0;  // 0=off, 1=low, 2=med, 3=high

void setup() {
  Serial.begin(9600);
  
  // Initialize IR Receiver
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);
  
  // Initialize Motor Driver pins
  pinMode(MOTOR_EN, OUTPUT);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  
  // Motor off initially
  stopMotor();
  
  Serial.println("IR Fan Control System Ready!");
  Serial.println("Press remote buttons to see their codes");
}

void loop() {
  // Check for IR remote signals
  if (IrReceiver.decode()) {
    unsigned long command = IrReceiver.decodedIRData.decodedRawData;
    
  
    handleIRCommand(command);
    
    IrReceiver.resume(); // Ready for next signal
  }
  
  delay(100);
}

void handleIRCommand(unsigned long command) {
  // Ignore repeat codes (0x0) from held buttons
  if (command == 0x0 || command == 0xFFFFFFFF) {
    return; // Do nothing for repeat codes
  }
  
  switch(command) {
    case BTN_POWER:
      togglePower();
      break;
      
    case BTN_SPEED_UP:
      increaseSpeed(); // UP arrow increases speed
      break;
      
    case BTN_SPEED_DOWN:
      decreaseSpeed(); // DOWN arrow decreases speed
      break;
      
    case BTN_1:
      setSpeed(1); // Button 1 = Low speed
      break;
      
    case BTN_2:
      setSpeed(2); // Button 2 = Medium speed
      break;
      
    case BTN_3:
      setSpeed(3); // Button 3 = High speed
      break;
      
    default:
      Serial.println("Wrong button! Please use:");
      Serial.println("RED button = Power ON/OFF");
      Serial.println("UP arrow = Increase speed");
      Serial.println("DOWN arrow = Decrease speed");
      Serial.println("Button 1 = Low speed");
      Serial.println("Button 2 = Medium speed");
      Serial.println("Button 3 = High speed");
      break;
  }
}

void togglePower() {
  fanOn = !fanOn;
  
  if (fanOn) {
    Serial.println("Fan: ON ");
    setSpeed(1); // Start at low speed
  } else {
    Serial.println("Fan: OFF ");
    stopMotor();
    currentSpeed = 0;
  }
}

void setSpeed(int speed) {
  if (!fanOn) {
    fanOn = true;
    Serial.println("Fan: ON ");
  }
  
  currentSpeed = speed;
  
  int pwmValue;
  
  switch(speed) {
    case 0:
      pwmValue = SPEED_OFF;
      Serial.println("Speed: OFF ");
      break;
    case 1:
      pwmValue = SPEED_LOW;
      Serial.println("Speed: LOW ");
      break;
    case 2:
      pwmValue = SPEED_MED;
      Serial.println("Speed: MEDIUM ");
      break;
    case 3:
      pwmValue = SPEED_HIGH;
      Serial.println("Speed: HIGH ");
      break;
    default:
      pwmValue = SPEED_OFF;
      break;
  }
  
  runMotor(pwmValue);
}

void increaseSpeed() {
  if (!fanOn) {
    Serial.println("Fan is OFF! Press POWER button first.");
    return;
  }
  
  if (currentSpeed < 3) {
    currentSpeed++;
    setSpeed(currentSpeed);
  } else {
    Serial.println("Already at MAX speed!");
  }
}

void decreaseSpeed() {
  if (!fanOn) {
    Serial.println("Fan is OFF! Press POWER button first.");
    return;
  }
  
  if (currentSpeed > 1) {
    currentSpeed--;
    setSpeed(currentSpeed);
  } else {
    Serial.println("Already at MIN speed!");
  }
}

void runMotor(int speed) {
  // Set motor direction (forward)
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  
  // Set motor speed
  analogWrite(MOTOR_EN, speed);
}

void stopMotor() {
  analogWrite(MOTOR_EN, 0);
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
}
