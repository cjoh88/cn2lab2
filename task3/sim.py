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
downloading_nodes.Create(int(cmd.downloading_clients))

uploading_nodes = ns.network.NodeContainer()
uploading_nodes.Create(int(cmd.uploading_clients))

################################################################################
# CONNECT NODES WITH POINT-TO-POINT CHANNEL

# set default queue length to 5 packets (used by NetDevices)
ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(5))

nSnB = ns.network.NodeContainer()
nSnB.Add(nodes.Get(0))
nSnB.Add(nodes.Get(1))

nDnB = list()
for i in range(0, int(cmd.downloading_clients)):
    link = ns.network.NodeContainer()
    link.Add(downloading_nodes.Get(i))
    link.Add(nodes.Get(1))
    nDnB.append(link)

nUnB = list()
for i in range(0, int(cmd.uploading_clients)):
    link = ns.network.NodeContainer()
    link.Add(uploading_nodes.Get(i))
    link.Add(nodes.Get(1))
    nUnB.append(link)

################################################################################
# INSTALL NETWORK DEVICES

# create point-to-point helper with common attributes
pointToPoint = ns.point_to_point.PointToPointHelper()
pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
pointToPoint.SetDeviceAttribute("DataRate",
                            ns.network.DataRateValue(ns.network.DataRate(int(cmd.rate))))
pointToPoint.SetChannelAttribute("Delay",
                            ns.core.TimeValue(ns.core.MilliSeconds(int(cmd.latency))))

dSdB = pointToPoint.Install(nSnB)
dDdB = list()
for n in nDnB:
    dDdB.append(pointToPoint.Install(n))
dUdB = list()
for n in nUnB:
    dUdB.append(pointToPoint.Install(n))

# Here we can introduce an error model on the bottle-neck link (from node 4 to 5)
#em = ns.network.RateErrorModel()
#em.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
#em.SetAttribute("ErrorRate", ns.core.DoubleValue(0.02))
#d4d5.Get(1).SetReceiveErrorModel(em)

################################################################################
# CONFIGURE TCP
#
# Choose a TCP version and set some attributes.

# Set a TCP segment size (this should be inline with the channel MTU)
ns.core.Config.SetDefault("ns3::TcpSocket::SegmentSize", ns.core.UintegerValue(1448))

# If you want, you may set a default TCP version here. It will affect all TCP
# connections created in the simulator. If you want to simulate different TCP versions
# at the same time, see below for how to do that.
#ns.core.Config.SetDefault("ns3::TcpL4Protocol::SocketType",
#                          ns.core.StringValue("ns3::TcpTahoe"))
#                          ns.core.StringValue("ns3::TcpReno"))
#                          ns.core.StringValue("ns3::TcpNewReno"))
#                          ns.core.StringValue("ns3::TcpWestwood"))

# Some examples of attributes for some of the TCP versions.
ns.core.Config.SetDefault("ns3::TcpNewReno::ReTxThreshold", ns.core.UintegerValue(4))
ns.core.Config.SetDefault("ns3::TcpWestwood::ProtocolType",
                          ns.core.StringValue("WestwoodPlus"))


################################################################################
# CREATE A PROTOCOL STACK

stack = ns.internet.InternetStackHelper()
stack.Install(nodes)
stack.Install(downloading_nodes)
stack.Install(uploading_nodes)

################################################################################
# ASSIGN IP ADDRESSES FOR NET DEVICES

address = ns.internet.Ipv4AddressHelper()

address.SetBase(ns.network.Ipv4Address("10.0.0.0"), ns.network.Ipv4Mask("255.255.255.0"))
ifSifB = address.Assign(dSdB)
ifDifB = list()
for i, d in enumerate(dDdB):
    address.SetBase(ns.network.Ipv4Address("10.1." + str(i) + ".0"), ns.network.Ipv4Mask("255.255.255.0"))
    ifDifB.append(address.Assign(d))
ifUifB = list()
for i, d in enumerate(dUdB):
    address.SetBase(ns.network.Ipv4Address("10.2." + str(i) + ".0"), ns.network.Ipv4Mask("255.255.255.0"))
    ifUifB.append(address.Assign(d))

# Turn on global static routing so we can actually be routed across the network.
ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

#print(ifSifB.GetAddress(0))


################################################################################
# CREATE TCP APPLICATION AND CONNECTION

def SetupTcpConnection(srcNode, dstNode, dstAddr, startTime, stopTime):
  # Create a TCP sink at dstNode
  packet_sink_helper = ns.applications.PacketSinkHelper("ns3::TcpSocketFactory",
                          ns.network.InetSocketAddress(ns.network.Ipv4Address.GetAny(),
                                                       8080))
  sink_apps = packet_sink_helper.Install(dstNode)
  sink_apps.Start(ns.core.Seconds(2.0))
  sink_apps.Stop(ns.core.Seconds(50.0))

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

for i in range(0, int(cmd.downloading_clients)):
    n = downloading_nodes.Get(i)
    SetupTcpConnection(nodes.Get(0), n, ifDifB[i].GetAddress(0), ns.core.Seconds(2.0), ns.core.Seconds(40.0))
for i in range(0, int(cmd.uploading_clients)):
    n = uploading_nodes.Get(i)
    SetupTcpConnection(n, nodes.Get(0), ifSifB.GetAddress(0), ns.core.Seconds(2.0), ns.core.Seconds(40.0))

#######################################################################################
# CREATE A PCAP PACKET TRACE FILE
#
# This line creates two trace files based on the pcap file format. It is a packet
# trace dump in a binary file format. You can use Wireshark to open these files and
# inspect every transmitted packets. Wireshark can also draw simple graphs based on
# these files.
#
# You will get two files, one for node 0 and one for node 1

#pointToPoint.EnablePcap("sim-tcp", d0d4.Get(0), True)
#pointToPoint.EnablePcap("sim-tcp", d1d4.Get(0), True)

#######################################################################################
# FLOW MONITOR
#
# Here is a better way of extracting information from the simulation. It is based on
# a class called FlowMonitor. This piece of code will enable monitoring all the flows
# created in the simulator. There are four flows in our example, one from the client to
# server and one from the server to the client for both TCP connections.

flowmon_helper = ns.flow_monitor.FlowMonitorHelper()
monitor = flowmon_helper.InstallAll()

#######################################################################################
# RUN THE SIMULATION
#
# We have to set stop time, otherwise the flowmonitor causes simulation to run forever

ns.core.Simulator.Stop(ns.core.Seconds(50.0))
ns.core.Simulator.Run()

#######################################################################################
# FLOW MONITOR ANALYSIS
#
# Simulation is finished. Let's extract the useful information from the FlowMonitor and
# print it on the screen.

# check for lost packets
monitor.CheckForLostPackets()

classifier = flowmon_helper.GetClassifier()

for flow_id, flow_stats in monitor.GetFlowStats():
    t = classifier.FindFlow(flow_id)
    proto = {6: 'TCP', 17: 'UDP'} [t.protocol]
    print ("FlowID: %i (%s %s/%s --> %s/%i)" %
          (flow_id, proto, t.sourceAddress, t.sourcePort, t.destinationAddress, t.destinationPort))

    print ("  Tx Bytes: %i" % flow_stats.txBytes)
    print ("  Rx Bytes: %i" % flow_stats.rxBytes)
    print ("  Lost Pkt: %i" % flow_stats.lostPackets)
    print ("  Flow active: %fs - %fs" % (flow_stats.timeFirstTxPacket.GetSeconds(),
                                       flow_stats.timeLastRxPacket.GetSeconds()))
    print ("  Throughput: %f Mbps" % (flow_stats.rxBytes *
                                     8.0 /
                                     (flow_stats.timeLastRxPacket.GetSeconds()
                                       - flow_stats.timeFirstTxPacket.GetSeconds())/
                                     1024/
                                     1024))


# This is what we want to do last
ns.core.Simulator.Destroy()
