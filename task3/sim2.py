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

################################################################################
# CREATE NODES
nodes = ns.network.NodeContainer()
nodes.Create(cmd.downloading_clients + cmd.uploading_clients + 2)

################################################################################
# CONNECT NODES WITH POINT-TO-POINT CHANNEL

# set default queue length to 5 packets (used by NetDevices)
ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(5))

server_bottleneck = ns.network.NodeContainer()
server_bottleneck.Add(nodes.Get(0))
server_bottleneck.Add(nodes.Get(1))

links = list()
for i in range(2, cmd.uploading_clients + cmd.downloading_clients + 2):
    link = ns.network.NodeContainer()
    link.Add(nodes.Get(1))
    link.Add(nodes.Get(i))
    links.append(link)

# create point-to-point helper with common attributes
pointToPoint = ns.point_to_point.PointToPointHelper()
pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
pointToPoint.SetDeviceAttribute("DataRate",
                            ns.network.DataRateValue(ns.network.DataRate(int(cmd.rate))))
pointToPoint.SetChannelAttribute("Delay",
                            ns.core.TimeValue(ns.core.MilliSeconds(int(cmd.latency))))

devices = list()
devices.append(pointToPoint.Install(server_bottleneck));
for l in links:
    devices.append(pointToPoint.Install(l))

# Here we can introduce an error model on the bottle-neck link (from node 4 to 5)
#em = ns.network.RateErrorModel()
#em.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
#em.SetAttribute("ErrorRate", ns.core.DoubleValue(0.02))
#d4d5.Get(1).SetReceiveErrorModel(em)

################################################################################
# CONFIGURE TCP

ns.core.Config.SetDefault("ns3::TcpSocket::SegmentSize", ns.core.UintegerValue(1448))

################################################################################
# CREATE A PROTOCOL STACK

stack = ns.internet.InternetStackHelper()
stack.Install(nodes)

################################################################################
# ASSIGN IP ADDRESSES FOR NET DEVICES
address = ns.internet.Ipv4AddressHelper()

addresses = list()

address.SetBase(ns.network.Ipv4Address("10.1.1.0"), ns.network.Ipv4Mask("255.255.255.0"))
for i, device in enumerate(devices):
    ip = "10.1." + str(i) + ".0"
    address.SetBase(ns.network.Ipv4Address(ip), ns.network.Ipv4Mask("255.255.255.0"))
    addresses.append(address.Assign(device))

ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

#######################################################################################
# CREATE TCP APPLICATION AND CONNECTION

def SetupTcpConnection(srcNode, dstNode, dstAddr, startTime, stopTime):
      # Create TCP connection from srcNode to dstNode
      on_off_tcp_helper = ns.applications.OnOffHelper("ns3::TcpSocketFactory",
                              ns.network.Address(ns.network.InetSocketAddress(dstAddr, 8080)))
      on_off_tcp_helper.SetAttribute("DataRate",
                          ns.network.DataRateValue(ns.network.DataRate(int(cmd.on_off_rate))))
      on_off_tcp_helper.SetAttribute("PacketSize", ns.core.UintegerValue(1500))
      on_off_tcp_helper.SetAttribute("OnTime",
                          ns.core.StringValue("ns3::ConstantRandomVariable[Constant=2]"))
      on_off_tcp_helper.SetAttribute("OffTime",
                            ns.core.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
      #                      ns.core.StringValue("ns3::UniformRandomVariable[Min=1,Max=2]"))
      #                      ns.core.StringValue("ns3::ExponentialRandomVariable[Mean=2]"))

      # Install the client on node srcNode
      client_apps = on_off_tcp_helper.Install(srcNode)
      client_apps.Start(startTime)
      client_apps.Stop(stopTime)

SetupTcpConnection(nodes.Get(0), nodes.Get(1), addresses[0].GetAddress(0), ns.core.Seconds(2.0), ns.core.Seconds(40.0))

print("Uploading: " + str(cmd.uploading_clients) + "\nDownloading: " + str(cmd.downloading_clients))
