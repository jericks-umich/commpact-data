#!/usr/bin/env python3

import sys
import os.path
import numpy

# constants
USAGE = """%s <server data filename> <client data filename>
Redirect stderr to file to print out corrected first hop data
""" % sys.argv[0]
CORRECTION_SAMPLE_SIZE = 50
LOST_PACKET_THRESHOLD = 0.010  # any packet taking longer than X (default 10ms) is considered lost
DEBUG = False

# globals
SERVER_FILENAME = ""
CLIENT_FILENAME = ""
SERVER_DATA = []
CLIENT_DATA = []
RETURN_DATA = None  # becomes a list
CORRECTION_FACTOR = 0  # half the amount that the first hop is greater than the second hop, on average
CORRECTED_FIRST_HOP = None  # becomes a list
CORRECTED_SECOND_HOP = None  # becomes a list


# input: server data filename, client data filename
def main():
    # read in data from client and server filenames
    parseArgs()
    readData()
    # calculate 2nd hop data by subtracting server data from client data
    makeReturnData()
    # sort latencies by client (rtt) data
    sorted_client_data = makeSortedClientData()
    # take lowest N data points and calculate clock correction factor
    calculateCorrectionFactor(sorted_client_data)
    # apply correction factor to each hop data
    applyCorrectionFactor()
    # filter packet latencies above X, considered lost packets
    applyLostPacketFilter()
    # calculate average latency, packet loss rate, other stats on latency data for first hop -- ignore 2nd hop
    printPacketLoss()
    printAverageLatency()
    printPercentiles()
    # dump first hop data to stderr, if redirected
    dumpDataToStderr()


def parseArgs():
    global SERVER_FILENAME
    global CLIENT_FILENAME
    if len(sys.argv) != 3:
        print(USAGE)
        sys.exit(1)
    if not os.path.isfile(sys.argv[1]):
        print("Server filename invalid")
        print(USAGE)
        sys.exit(1)
    if not os.path.isfile(sys.argv[2]):
        print("Client filename invalid")
        print(USAGE)
        sys.exit(1)
    SERVER_FILENAME = os.path.abspath(sys.argv[1])
    CLIENT_FILENAME = os.path.abspath(sys.argv[2])


def readData():
    with open(SERVER_FILENAME, "r") as f:
        server_data = f.readlines()
    with open(CLIENT_FILENAME, "r") as f:
        client_data = f.readlines()
    try:
        for l in server_data:
            SERVER_DATA.append(float(l))
        for l in client_data:
            CLIENT_DATA.append(float(l))
    except:
        print("Invalid data in source file. Must be floats.")
        sys.exit(1)
    if len(SERVER_DATA) != len(CLIENT_DATA):
        print("Server data length doesn't match client data length.")
        sys.exit(1)


def makeReturnData():
    global RETURN_DATA
    RETURN_DATA = list(map(lambda x, y: x - y, CLIENT_DATA, SERVER_DATA))


def makeSortedClientData():
    client_data = []
    for i, t in enumerate(CLIENT_DATA):
        client_data.append((t, i))
    return sorted(client_data)


def calculateCorrectionFactor(sorted_client_data):
    global CORRECTION_FACTOR
    # ignore any lost packets (-1's) at the start of the list
    while len(sorted_client_data) > 0 and sorted_client_data[0][0] == -1:
        sorted_client_data.pop(0)
    # calculate correction factor
    first_hop_vs_second_hop_list = []
    for idx in map(lambda x: x[1],
                   sorted_client_data[:CORRECTION_SAMPLE_SIZE]):
        first_hop_vs_second_hop_list.append(
            SERVER_DATA[idx] - RETURN_DATA[idx])
    if DEBUG:
        print(first_hop_vs_second_hop_list)
    CORRECTION_FACTOR = (
        sum(first_hop_vs_second_hop_list) / CORRECTION_SAMPLE_SIZE) / 2


def applyCorrectionFactor():
    global CORRECTED_FIRST_HOP
    global CORRECTED_SECOND_HOP
    CORRECTED_FIRST_HOP = list(
        map(lambda x: x - CORRECTION_FACTOR if x != -1 else -1, SERVER_DATA))
    CORRECTED_SECOND_HOP = list(
        map(lambda x: x + CORRECTION_FACTOR if x != -1 else -1, RETURN_DATA))


def applyLostPacketFilter():
    global CORRECTED_FIRST_HOP
    global CORRECTED_SECOND_HOP
    CORRECTED_FIRST_HOP = list(
        map(lambda x: x if x < LOST_PACKET_THRESHOLD else -1,
            CORRECTED_FIRST_HOP))
    CORRECTED_SECOND_HOP = list(
        map(lambda x: x if x < LOST_PACKET_THRESHOLD else -1,
            CORRECTED_SECOND_HOP))


def printPacketLoss():
    packets_lost = len(list(filter(lambda x: x == -1, CORRECTED_FIRST_HOP)))
    packet_loss = packets_lost / len(CORRECTED_FIRST_HOP)
    print("Packet loss: %g%%" % (packet_loss * 100))


def printAverageLatency():
    non_lost_packet_latencies = list(
        filter(lambda x: x != -1, CORRECTED_FIRST_HOP))
    average_latency = sum(non_lost_packet_latencies) / len(
        non_lost_packet_latencies)
    print("Average latency: %g ms" % (average_latency * 1000))


def printPercentiles():
    non_lost_packet_latencies = list(
        filter(lambda x: x != -1, CORRECTED_FIRST_HOP))
    data = numpy.array(non_lost_packet_latencies)
    print(" 2%%: %g ms" % (numpy.percentile(data, 2) * 1000))
    print("25%%: %g ms" % (numpy.percentile(data, 25) * 1000))
    print("50%%: %g ms" % (numpy.percentile(data, 50) * 1000))
    print("75%%: %g ms" % (numpy.percentile(data, 75) * 1000))
    print("98%%: %g ms" % (numpy.percentile(data, 98) * 1000))


def dumpDataToStderr():
    if not os.isatty(2):
        for dat in CORRECTED_FIRST_HOP:
            if dat == -1:
                print("%d" % dat, file=sys.stderr)
            else:
                print("%.6f" % dat, file=sys.stderr)


if __name__ == "__main__":
    main()
