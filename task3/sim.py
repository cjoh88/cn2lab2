#!/usr/bin/python

import sys
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor

################################################################################
# COMMAND LINE PARSING

cmd = ns.core.CommandLine()

# Default values
cmd.latency = 1
cmd.rate = 500000
cmd.on_off_rate = 300000
cmd.downloading_clients = 10
cmd.uploading_clients = 10
cmd.AddValue ("rate", "P2P data rate in bps")
cmd.AddValue ("latency", "P2P link Latency in miliseconds")
cmd.AddValue ("on_off_rate", "OnOffApplication data sending rate")
cmd.AddValue ("downloading_clients", "Number of downloading clients")
cmd.AddValue ("uploading_clients", "Number of uploading clients")


cmd.Parse(sys.argv)

#######################################################################################
# CREATE NODES

nodes = ns.network.NodeContainer()
nodes.Create(2)

downloading_nodes = ns.network.NodeContainer()
downloading_nodes.Create(cmd.downloading_clients)

uploading_nodes = ns.network.NodeContainer()
uploading_nodes.Create(cmd.uploading_clients)

################################################################################
# CONNECT NODES WITH POINT-TO-POINT CHANNEL

# set default queue length to 5 packets (used by NetDevices)
ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(5))

nSnB = ns.network.NodeContainer()
nSnB.Add(nodes.Get(0))
nSnB.Add(nodes.Get(1))

nDnB = list()
for i in range(0, cmd.downloading_clients):
    link = ns.network.NodeContainer()
    link.Add(downloading_nodes.Get(i))
    link.Add(nodes.Get(1))
    nDnB.append(link)

nUnB = list()
for i in range(0, cmd.uploading_clients):
    link = ns.network.NodeContainer()
    link.Add(uploading_nodes.Get(i))
    link.Add(nodes.Get(1))
    nUnB.append(link)
