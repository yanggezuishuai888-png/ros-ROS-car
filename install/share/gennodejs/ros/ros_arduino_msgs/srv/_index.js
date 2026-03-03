
"use strict";

let ServoRead = require('./ServoRead.js')
let AnalogRead = require('./AnalogRead.js')
let DigitalWrite = require('./DigitalWrite.js')
let ServoWrite = require('./ServoWrite.js')
let AnalogWrite = require('./AnalogWrite.js')
let DigitalSetDirection = require('./DigitalSetDirection.js')
let DigitalRead = require('./DigitalRead.js')

module.exports = {
  ServoRead: ServoRead,
  AnalogRead: AnalogRead,
  DigitalWrite: DigitalWrite,
  ServoWrite: ServoWrite,
  AnalogWrite: AnalogWrite,
  DigitalSetDirection: DigitalSetDirection,
  DigitalRead: DigitalRead,
};
