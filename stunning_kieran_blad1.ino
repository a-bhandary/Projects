/*
 * Project: Automated Light Sensor and Calibration System
 * Description: Smart room light sensor that reads ambient brightness using a photoresistor.
 * Features an automatic mode (turns LED on below threshold) and a manual override toggle.
 * 
 * HARDWARE NOTE: Pushbutton on Pin 7 is wired directly to GND. 
 * This code uses INPUT_PULLUP to activate the Arduino's internal resistor.
 */

#include <LiquidCrystal.h>

// --- Pin Definitions ---
const int rs = 12, en = 11, d4 = 5, d5 = 4, d6 = 3, d7 = 2;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);

const int ldrPin = A0;       // Photoresistor connected to Analog Pin 0
const int ledPin = 8;        // Red LED connected to Digital Pin 8
const int buttonPin = 7;     // Push button connected to Digital Pin 7

// --- System Variables ---
int lightLevel = 0;          // Stores the analog reading from the LDR
const int threshold = 900;   // The light limit to trigger the LED

// --- State Tracking for Button Toggle ---
bool isAutoMode = true;      // Defaults to Auto Mode on startup

// Default button states are HIGH because INPUT_PULLUP holds the pin at 5V until pressed
int lastButtonState = HIGH;
int currentButtonState = HIGH;

void setup() {
  // Initialize component modes
  pinMode(ldrPin, INPUT);
  pinMode(ledPin, OUTPUT);
  
  // Activate the Arduino's internal pull-up resistor for the button
  pinMode(buttonPin, INPUT_PULLUP); 
  
  // Initialize the 16x2 LCD display
  lcd.begin(16, 2);
}

void loop() {
  // 1. Read current state of sensors
  lightLevel = analogRead(ldrPin);
  currentButtonState = digitalRead(buttonPin);

  // 2. Button Toggle Logic (Edge Detection)
  // Check if the button was just pressed (went from HIGH to LOW because it connects to GND)
  if (currentButtonState == LOW && lastButtonState == HIGH) {
    isAutoMode = !isAutoMode; // Flip between true (Auto) and false (Override)
    delay(50);                // Quick debounce delay to prevent rapid flickering
  }
  lastButtonState = currentButtonState; // Save state for the next loop

  // 3. Update the Top Row of the LCD
  lcd.setCursor(0, 0);
  lcd.print("Light:");
  lcd.print(lightLevel);
  lcd.print("    "); // Extra spaces clear out leftover digits if the number drops

  // 4. Mode Logic and Bottom Row Display
  if (isAutoMode) {
    // --- AUTO MODE ---
    lcd.setCursor(0, 1);
    lcd.print("Mode: AUTO      ");
    
    // Check threshold
    if (lightLevel < threshold) {
      digitalWrite(ledPin, HIGH); // Too dark -> Turn LED ON
    } else {
      digitalWrite(ledPin, LOW);  // Bright enough -> Turn LED OFF
    }
    
  } else {
    // --- MANUAL OVERRIDE MODE ---
    lcd.setCursor(0, 1);
    lcd.print("Override: ON    ");
    digitalWrite(ledPin, HIGH);   // Keep LED ON regardless of light level
  }
  
  // Slight delay for system stability
  delay(100); 
}