// Number of ultrasonic sensors
const int NUM_SENSORS = 8;

// Define the TRIG and ECHO pins for each sensor
const int trigPins[NUM_SENSORS] = {2, 4, 6, 8, 10, 14, 16, 18};
const int echoPins[NUM_SENSORS] = {3, 5, 7, 9, 11, 15, 17, 19};

// Array to store distances in centimeters
long distances[NUM_SENSORS];

void setup() {
  Serial.begin(9600);

  // Initialize each TRIG pin as OUTPUT and ECHO as INPUT
  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
  }
}

void loop() {
  for (int i = 0; i < NUM_SENSORS; i++) {
    distances[i] = measureDistance(trigPins[i], echoPins[i]);
    //distances[0] = measureDistance(trigPins[5], echoPins[5]);
  }

  // Print all distances to Serial Monitor
  for (int i = 0; i < NUM_SENSORS; i++) {
    Serial.print("Sensor ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(distances[i]);
    Serial.println(" cm");
  }

  Serial.println("--------------------");
  delay(500); // Wait half a second before next round
}

// Function to measure distance for one sensor
long measureDistance(int trigPin, int echoPin) {
  // Ensure TRIG is LOW before starting
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  // Send a 10µs HIGH pulse to TRIG
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Measure the duration of ECHO HIGH pulse
  long duration = pulseIn(echoPin, HIGH, 30000); // Timeout after 30ms to prevent hanging

  // Convert duration to distance in cm: distance = duration / 58
  long distance = duration / 58;

  // Handle out-of-range or failed readings
  if (duration == 0) {
    return -1; // Return -1 for failed reading
  }

  return distance;
}
