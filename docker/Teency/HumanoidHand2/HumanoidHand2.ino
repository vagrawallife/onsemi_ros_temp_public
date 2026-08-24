#include <Adafruit_NeoPixel.h>

#define LED_PIN 14 // Data pin connected to NeoPixels
#define LED_PIN1 15 // Data pin connected to NeoPixels
#define LED_PIN2 16 // Data pin connected to NeoPixels
#define LED_PIN3 17 // Data pin connected to NeoPixels
#define LED_COUNT 2 // Number of LEDs in the strip/ring

#define DELAYVAL 500 // milliseconds



Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip1(LED_COUNT, LED_PIN1, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2(LED_COUNT, LED_PIN2, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip3(LED_COUNT, LED_PIN3, NEO_GRB + NEO_KHZ800);


// COLOR DECLARATION
const uint16_t white = strip.Color(255, 255, 255);
const uint16_t orange = strip.Color(255, 50, 0);
const uint16_t blue = strip.Color(0, 0, 255);
const uint16_t green = strip.Color(0, 255, 0);
const uint16_t red = strip.Color(255, 0, 0);
const uint16_t purple = strip.Color (160, 32, 240);  
const uint16_t cayn = strip.Color (0, 255, 255);  
const uint16_t yellow = strip.Color ( 255, 255, 0); 

void setup() {
strip.begin(); // Initialize NeoPixel object
strip1.begin(); // Initialize NeoPixel object
strip2.begin(); // Initialize NeoPixel object
strip3.begin(); // Initialize NeoPixel object
strip.show(); // Turn off all pixels initially
strip1.show(); // Turn off all pixels initially
strip2.show(); // Turn off all pixels initially
strip3.show(); // Turn off all pixels initially
}



// ====== HELPER FUNCTION ======
void setStripColor(Adafruit_NeoPixel &strip, uint8_t r, uint8_t g, uint8_t b) {
  for (uint16_t i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, strip.Color(r, g, b));
  }
  strip.show(); // Send data to the strip
}

void loop() {
  setStripColor(strip, 160, 32, 240); // Purple
  setStripColor(strip1, 0, 0, 255);   // Blue
  setStripColor(strip2, 0, 255, 0);   // Green
  setStripColor(strip3, 255, 50, 0);  // Orange
  delay(1000);
}
