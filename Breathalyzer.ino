#include <MQUnifiedsensor.h>
#include <LiquidCrystal_I2C.h>
#include <Wire.h>

/************************Hardware Related Macros************************************/
#define Board ("Arduino UNO")
#define Pin (A0)

/************************Software Related Macros************************************/
#define Type ("MQ-3")               
#define Voltage_Resolution (5)
#define ADC_Bit_Resolution (10)     
#define RatioMQ3CleanAir (60)       

/*****************************Globals***********************************************/
MQUnifiedsensor MQ3(Board, Voltage_Resolution, ADC_Bit_Resolution, Pin, Type);

LiquidCrystal_I2C lcd(0x27, 16, 2);

#define greenLedPin 7
#define redLedPin 13
#define switchPin A2

int count = 0;
bool isMeasuring = false;
bool personDetected = false;

const float legalLimit = 0.03;
float maxValue = 0.0;

void setup() {
  pinMode(greenLedPin, OUTPUT);
  pinMode(redLedPin, OUTPUT);
  pinMode(switchPin, INPUT_PULLUP);

  Serial.begin(9600);

  MQ3.setRegressionMethod(1);
  MQ3.setA(0.3934);
  MQ3.setB(-1.504);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Breathalyzer");
  lcd.setCursor(0, 1);
  lcd.print("Press to start");

  digitalWrite(greenLedPin, HIGH);
  digitalWrite(redLedPin, LOW);

  MQ3.init();

  float calcR0 = 0;
  for (int i = 1; i <= 10; i++) {
    MQ3.update();
    calcR0 += MQ3.calibrate(RatioMQ3CleanAir);
    Serial.print(".");
  }
  MQ3.setR0(calcR0 / 3.8);

  MQ3.serialDebug(true);
}

void loop() {
  if (digitalRead(switchPin) == HIGH && !isMeasuring) {
    lcd.backlight();
    int numReadings = 0;
    maxValue = 0.0;

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Measuring");


    isMeasuring = true;

    while (digitalRead(switchPin) == HIGH) {
      MQ3.update();
      count++;

      numReadings++;

      MQ3.update();
      float data = MQ3.readSensor();

      lcd.setCursor(0, 1);
      lcd.print(data, 2);

      if (data > maxValue) {
        maxValue = data;
      }

      Serial.println(data, 2);
      delay(200);
    }

    if (numReadings >= 10) {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Max Value: ");
      lcd.setCursor(0, 1);
      lcd.print(maxValue, 2);
      Serial.print("Max Value:");
      Serial.println(maxValue, 2);

      if (maxValue < legalLimit) {
        Serial.println("record");
        Serial.println("Engine Control Activate");
        delay(2000);
        lcd.setCursor(0, 0);
        lcd.print("Engine Control");
        lcd.setCursor(0, 1);
        lcd.print("Activate");
        delay(5000);
      } else {
        Serial.println("record");
        Serial.println("Engine Control Block");
        delay(2000);
        lcd.setCursor(0, 0);
        lcd.print("Engine Control");
        lcd.setCursor(0, 1);
        lcd.print("Block");
        delay(5000);
      }
    } else {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Please");
      lcd.setCursor(0, 1);
      lcd.print("re-measure");
      delay(2000);
    }

    isMeasuring = false;
    lcd.setCursor(0, 0);
    lcd.print("Breathalyzer");
    lcd.setCursor(0, 1);
    lcd.print("Press to start");
    count = 0;
  }
  if (Serial.available()) {
    char data = Serial.read();
    
    if (data == 'G') {
      digitalWrite(greenLedPin, LOW);
      digitalWrite(redLedPin, HIGH);
    }
    else if(data == 'R'){
      digitalWrite(greenLedPin, HIGH);
      digitalWrite(redLedPin, LOW);
    }

    else{
      digitalWrite(greenLedPin, LOW);
      digitalWrite(redLedPin, LOW);
    }

  }
  

}
