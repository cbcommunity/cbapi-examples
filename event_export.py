import requests
import argparse
import json
import traceback
import csv
import sys
import threading
import time
import os

API_TIMEOUT_DEFAULT = 15


#
# Prerequisites:
#
# Create a virtual environment
# python3 -m venv venv
#
# Activate virtual environment
# source venv/bin/activate
#
# Install dependencies
# pip3 install requests
#
# Usage: python3 event_export.py --defense-api-url=https://api-prod05.conferdeploy.net --connector-id=<connector_id> --api-key=<api-key>
#
# Description:
# Script will run for a specified number of minutes specified by --minutes. Default is 1 minute.
# After the script runs it will output a csv file by default named event_export.csv.  History on events is kept
# between runs in files event_ids.json and events.json.  Keep these files so we don't export duplicates.
#
# Note: Eventually event_ids.json and events.json will get too large.  Delete them once the script start lagging behind.
#
# Example Run:
# $ python3 event_export.py --defense-api-url=https://api-prod05.conferdeploy.net --connector-id=<connector_id> --api-key=<api_key> --minutes=1
# [+] Starting event export script
# [+] Running this script for 1 minute(s)
# New events count:12907
# [+] Exporting events to event_export.csv
# [+] Done
#

class EventThread(threading.Thread):
    def __init__(self, args):
        super().__init__()
        self.running = True
        self.args = args

    def stop(self):
        self.running = False

    def run(self):
        new_events = 0
        total_events_grabbed = 0

        while (self.running):
            try:
                event_ids = import_event_ids()
            except Exception as e:
                event_ids = []

            try:
                response = request_events(args.defense_api_url, args.connector_id, args.api_key)

                for event in response.get('results', []):
                    total_events_grabbed += 1
                    event_id = event.get('eventId', None)
                    if event_id is None:
                        continue
                    elif event_id in event_ids:
                        continue
                    else:
                        new_events += 1
                        event_ids.append(event_id)
                        dump_event(json.dumps(event) + "\n")
                        dump_event_id(str(event_id) + "\n")

                sys.stdout.write("\rNew events count:{}".format(new_events))
                sys.stdout.flush()
                # print("\rTotal events received:{}".format(total_events_grabbed))
                # print("New events count:{}".format(new_events))
                # print("Total events saved in history:{}".format(total_event_count()))
                # print("Total event ids saved in history:{}".format(total_event_id_count()))
            except Exception as e:
                traceback.print_exc()

            time.sleep(5)


def request_events(api_url_root, connector_id, api_key):
    headers = {'X-Auth-Token': "{0}/{1}".format(api_key, connector_id)}

    try:
        response = requests.get(
            "{0}/integrationServices/v3/event?searchWindow=3h&rows=5000&eventType=NETWORK".format(api_url_root),
            headers=headers,
            timeout=API_TIMEOUT_DEFAULT)
    except Exception as e:
        print("Exception {0} when retrieving events".format(str(e)))
        return None

    return response.json()


def dump_event(data):
    with open('events.json', 'a') as fp:
        fp.write(data)


def import_event_ids():
    event_ids = []
    with open('event_ids.json', 'r') as fp:
        for line in fp.readlines():
            event_ids.append(line.strip())
    return event_ids


def dump_event_id(data):
    with open('event_ids.json', 'a') as fp:
        fp.write(data)


def total_event_count():
    try:
        with open('events.json', 'r') as fp:
            return len(fp.readlines())
    except Exception as e:
        print(str(e))
        return 0


def total_event_id_count():
    try:
        with open('event_ids.json', 'r') as fp:
            return len(fp.readlines())
    except Exception as e:
        print(str(e))
        return 0


def export_to_csv():
    with open('event_export.csv', 'w') as csvfile:
        with open('events.json', 'r') as fp:
            fieldnames = ['eventId', 'sourceAddress', 'destAddress', 'threatIndicators', 'deviceName',
                          'parentName', 'name', 'appName', 'targetAppName', 'parentAppName']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for line in fp.readlines():
                threatIndicators = json.loads(line).get('threatIndicators', [])
                if not threatIndicators:
                    threatIndicators = []
                writer.writerow({'eventId': json.loads(line).get('eventId', ''),
                                 'sourceAddress': json.loads(line).get('netFlow', {}).get('sourceAddress', ''),
                                 'destAddress': json.loads(line).get('netFlow', {}).get('destAddress', ''),
                                 'threatIndicators': threatIndicators,
                                 'deviceName': json.loads(line).get('deviceDetails', {}).get('deviceName', ''),
                                 'parentName': json.loads(line).get('processDetails', {}).get('parentName', ''),
                                 'name': json.loads(line).get('processDetails', {}).get('name', ''),
                                 'appName': json.loads(line).get('selectedApp', {}).get('applicationName', ''),
                                 'targetAppName': json.loads(line).get('targetApp', {}).get('applicationName', ''),
                                 'parentAppName': json.loads(line).get('parentApp', {}).get('applicationName', '')})


def main(args):
    print('[+] Starting event export script')
    print('[+] Running this script for {} minute(s)'.format(args.minutes))

    try:
        if args.reset:
            os.remove("events.json")
            os.remove("event_ids.json")
    except Exception as e:
        print(str(e))

    try:
        event_thread = EventThread(args)
        event_thread.start()

        time.sleep(args.minutes * 60)
        event_thread.stop()
        event_thread.join()
        print('\n[+] Exporting events to event_export.csv')
        export_to_csv()
        print('[+] Done')
    except:
        print("[-] Error")
        print(traceback.format_exc())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='event export example script')

    parser.add_argument('--defense-api-url',
                        required=True,
                        help='api url for your Cb Defense environment')

    parser.add_argument('--connector-id',
                        required=True,
                        help='Connector ID for API connector')

    parser.add_argument('--api-key',
                        required=True,
                        help='API Key for API connector')

    parser.add_argument('--output_file',
                        default="events_export.csv",
                        help="output csv file")

    parser.add_argument('--reset',
                        type=bool,
                        default=False,
                        help="delete event history")

    parser.add_argument('--minutes',
                        type=int,
                        default=1,
                        help="number of minutes to run")

    args = parser.parse_args()
    main(args)
