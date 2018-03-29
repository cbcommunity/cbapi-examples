#!/usr/bin/env python
#
# The MIT License (MIT)
#
# Copyright (c) 2018 Carbon Black
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# -----------------------------------------------------------------------------
#
# Created 2018-03-29 by Jason Garman <jgarman@carbonblack.com>

#
# Restart Cb Response sensors when certain criteria are met.
#
#  This script will restart sensors that match *any* of the status messages contained within the
#  accompanying "restart_sensors.conf" file
#

import sys
from cbapi.example_helpers import build_cli_parser, get_cb_response_object
from cbapi.response import Sensor


def main():
    parser = build_cli_parser("Restart Cb Response sensors when certain criteria are met")
    parser.add_argument("--config", "-c", help="Configuration file path", default="restart_sensors.conf")
    parser.add_argument("--dryrun", "-d", help="Dry run - don't actually restart sensors", action="store_true")
    options = parser.parse_args()

    criteria = [c.strip() for c in open(options.config, "r").readlines()]
    criteria = [c for c in criteria if c != ""]

    print("Will restart sensors that have any of the following sensor health messages:")
    for c in criteria:
        print("  - {0}".format(c))

    cb = get_cb_response_object(options)

    num_sensors_restarted = 0

    for sensor in cb.select(Sensor):
        if sensor.sensor_health_message in criteria:
            print("Restarting sensor id {0} (hostname {1}) because its health message is {2}"
                  .format(sensor.id, sensor.hostname, sensor.sensor_health_message))
            num_sensors_restarted += 1
            if not options.dryrun:
                sensor.restart_sensor()

    print("{0} {1} sensors.".format("Would have restarted" if options.dryrun else "Restarted", num_sensors_restarted))


if __name__ == '__main__':
    sys.exit(main())