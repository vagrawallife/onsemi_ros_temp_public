// Verion 1.2 15 June 2025 02:23PM
#include <stdint.h>
#include <math.h>
#include <SoftwareSerial.h>
#include "RoboClaw.h"


// SOFTWARE SERIAL PINS (RX, TX)
// SOFTWARE SERIAL PINS (RX, TX)
//SoftwareSerial serial(10, 11);
#define serial1 Serial1
#define serial2 Serial2

// CREATE TWO ROBOCLAW OBJECTS
RoboClaw roboclaw1(&serial1, 10000);
RoboClaw roboclaw2(&serial2, 10000);

// ROBOCLAW ADDRESSES
#define ADDRESS1 0x80  // Board #1
#define ADDRESS2 0x80  // Board #2

// PID COEFFICIENTS
#define A1_M1_Kp   5.19223
#define A1_M1_Ki   0.91042
#define A1_M1_Kd   0.0
#define A1_M2_Kp   5.19223
#define A1_M2_Ki   0.91042
#define A1_M2_Kd   0.0
#define A2_M1_Kp   5.19223
#define A2_M1_Ki   0.91042
#define A2_M1_Kd   0.0
#define A2_M2_Kp   5.19223
#define A2_M2_Ki   0.91042
#define A2_M2_Kd   0.0

#define qpps 900
#define quad_pulses_per_revolution 537.6
#define quad_pulses_per_meter 673.0
#define max_seconds_uncommanded_travel 0.75

#define IDLE_INTERVAL 500;  //ms


uint8_t depth1a, depth2a, depth1b, depth2b;
int values[7] = {0, 0, 0, 0, 0, 0, 0}; // Initialize with invalid values
int32_t max_distance;
char version[80];
unsigned long previousMillis = 0; 
unsigned long currentMillis;
unsigned long idle_interval = 2000;
unsigned long encoderMillis = 0; 
unsigned long encoder_interval = 1000;

int32_t r1_enc1; 
int32_t r1_enc2 ;
int32_t r1_speed1 ;
int32_t r1_speed2 ;  
int32_t r2_enc1 ;
int32_t r2_enc2 ;
int32_t r2_speed1 ;
int32_t r2_speed2 ;
uint8_t status1, status2, status3, status4;
bool valid1, valid2, valid3, valid4;



// -------------------------------------------------------------------
// HELPER FUNCTION TO DISPLAY ENCODER/SPEED FOR A GIVEN ROBOCLAW/ADDRESS
// -------------------------------------------------------------------
void encoders(bool x) 
{
  r1_enc1 = roboclaw1.ReadEncM1(ADDRESS1, &status1, &valid1);delay(2);
  r1_speed1 = roboclaw1.ReadSpeedM1(ADDRESS1, &status3, &valid3);delay(2);
  r1_enc2 = roboclaw1.ReadEncM2(ADDRESS1, &status2, &valid2);delay(2);
  r1_speed2 = roboclaw1.ReadSpeedM2(ADDRESS1, &status4, &valid4);

  //delay(5);
  if(!valid1) {r1_enc1 = 0;}
  if(!valid2) {r1_enc2 = 0;}
  if(!valid3) {r1_speed1 = 0;}
  if(!valid4) {r1_speed2 = 0;}

  r2_enc1 = roboclaw2.ReadEncM1(ADDRESS2, &status1, &valid1);delay(2);
  r2_speed1 = roboclaw2.ReadSpeedM1(ADDRESS2, &status3, &valid3);delay(2);
  r2_enc2 = roboclaw2.ReadEncM2(ADDRESS2, &status2, &valid2);delay(2);
  r2_speed2 = roboclaw2.ReadSpeedM2(ADDRESS2, &status4, &valid4);
  if(!valid1) {r2_enc1 = 0;}
  if(!valid2) {r2_enc2 = 0;}
  if(!valid3) {r2_speed1 = 0;}
  if(!valid4) {r2_speed2 = 0;}
  sprintf(version,"start %5ld %3ld %5ld %3ld %5ld %3ld %5ld %3ld stop\r\n", 
          r1_enc1,r1_speed1,r1_enc2,r1_speed2,
          r2_enc1,r2_speed1,r2_enc2,r2_speed2);
  Serial.print(version);
  if (x == true){
      roboclaw1.ResetEncoders(ADDRESS1);
      roboclaw2.ResetEncoders(ADDRESS2);
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("Dual RoboClaw Test (0x80 & 0x81)");

  // START COMMUNICATION ON BOTH ROBOCLAW OBJECTS
  roboclaw1.begin(38400);
  roboclaw2.begin(38400);

  // SET PID FOR BOTH BOARDS
  roboclaw1.SetM1VelocityPID(ADDRESS1, A1_M1_Kd, A1_M1_Kp, A1_M1_Ki, qpps);
  roboclaw1.SetM2VelocityPID(ADDRESS1, A1_M2_Kd, A1_M2_Kp, A1_M2_Ki, qpps);
  roboclaw2.SetM1VelocityPID(ADDRESS2, A2_M1_Kd, A2_M1_Kp, A2_M1_Ki, qpps);
  roboclaw2.SetM2VelocityPID(ADDRESS2, A2_M2_Kd, A2_M2_Kp, A2_M2_Ki, qpps);
  max_distance = fabs(qpps*max_seconds_uncommanded_travel);
  if(roboclaw1.ReadVersion(ADDRESS1,version)){
    Serial.print("R1 ");  
    Serial.println(version);  
  }
  delay(100);
  if(roboclaw2.ReadVersion(ADDRESS2,version)){
    Serial.print("R2 ");  
    Serial.println(version);  
  }
  roboclaw1.ResetEncoders(ADDRESS1);
  roboclaw2.ResetEncoders(ADDRESS2);
  delay(100);
}

void parseValues(String content) {
  int index = 0;
  values[0] = 0;values[1] = 0;values[2] = 0;values[3] = 0;
  char *token = strtok((char*)content.c_str(), " ");
  if (strcmp(token,"r0") == 0){
    encoders(false);  //read encoders and speed and send to host
  }else if (strcmp(token,"r1") == 0){
    encoders(true);  //read encoders and speed and reset encoders
  }else
  {
    while (token != NULL && index < 4) {
      values[index] = atoi(token);
      token = strtok(NULL, " ");
      index++;
    }
    setMotors(values);
  }
}

void setMotors(int values[]){
  for(int i=0;i<4;i++)
  {
      Serial.print(" value: ");Serial.print(values[i]);
  }
  
  //roboclaw1.SpeedAccelDistanceM1(ADDRESS1, 1500, values[0], max_distance, 0);
  //roboclaw1.SpeedAccelDistanceM2(ADDRESS1, 1500, values[1], max_distance, 0);
  //roboclaw2.SpeedAccelDistanceM1(ADDRESS2, 1500, values[2], max_distance, 0);
  //roboclaw2.SpeedAccelDistanceM2(ADDRESS2, 1500, values[3], max_distance, 0);
  //if (values[0] == 0 && values[1] == 0 && values[2] == 0 && values[3] == 0){
    //roboclaw1.SpeedAccelM1(ADDRESS1, 4000, values[0]);
    //roboclaw1.SpeedAccelM2(ADDRESS1, 4000, values[1]);
    //roboclaw1.SpeedAccelM1(ADDRESS2, 4000, values[2]);
    //roboclaw1.SpeedAccelM2(ADDRESS2, 4000, values[3]);
  //}
  //else {
    //roboclaw1.SpeedAccelM1(ADDRESS1, 1500, values[0]);
    //roboclaw1.SpeedAccelM2(ADDRESS1, 1500, values[1]);
    //roboclaw1.SpeedAccelM1(ADDRESS2, 1500, values[2]);
    //roboclaw1.SpeedAccelM2(ADDRESS2, 1500, values[3]);
  //}

  roboclaw1.SpeedAccelM1(ADDRESS1, 1000, values[0]);
  roboclaw1.SpeedAccelM2(ADDRESS1, 1000, values[1]);
  roboclaw2.SpeedAccelM1(ADDRESS2, 1000, values[2]);
  roboclaw2.SpeedAccelM2(ADDRESS2, 1000, values[3]);
  encoders(false);  //read encoders and speed and send to host
}

void loop() {


  //currentMillis = millis();
  //if((currentMillis - encoderMillis) > encoder_interval) {
  //    encoderMillis = currentMillis; 
  //    encoders();  //read encoders and speed and send to host
  //}

  //if((currentMillis - previousMillis) > idle_interval) {
  //    previousMillis = currentMillis; 
  //    values[0] = 0;
  //    values[1] = 0;
  //    values[2] = 0;
  //    values[3] = 0;
      //setMotors(values);
  //}

  if (Serial.available() > 0) {
    previousMillis = currentMillis; 
    String content = Serial.readStringUntil('\n');
    //Serial.print("Received: "); Serial.println(content);
    parseValues(content);
  }
  delay(20);
}