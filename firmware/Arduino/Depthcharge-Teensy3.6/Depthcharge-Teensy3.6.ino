// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>
//
// Top-level source file for Teensy 3.6
//  <https://www.pjrc.com/store/teensy36.html>
//
// I2C SCL: Pin 19
// I2C SDA: Pin 18
//

#include <Depthcharge.h>

Depthcharge::Companion dc;

void setup() {
    Serial.begin(Depthcharge::Companion::default_uart_baudrate);

    dc.attachHostInterface(&Serial);
    dc.attachLED(13, HIGH, LOW);
    dc.attachI2C(&Wire, 
                 Depthcharge::Companion::default_i2c_addr,
                 Depthcharge::Companion::default_i2c_speed); 

    interrupts();
}

void loop() {
    dc.processEvents();
}
