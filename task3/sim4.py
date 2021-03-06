#!/usr/bin/python

import sys
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor
import time

#TODO make sure more ip addresses can be used
ns.core.RngSeedManager.SetSeed(int(time.time() * 1000 % (2**31-1)))
def parse_commands():
    cmd = ns.core.CommandLine()

    cmd.d_min = 1               # minimum number of downloading clients
    cmd.d_max = 5               # maximum number of downloading clients
    cmd.u_min = 1               # minimum number of uploading clients
    cmd.u_max = 1              # maximum number of uploading clients
    cmd.queue_length = 5        # queue length
    cmd.d_data_rate = 5000000     # downloaders data rate in bytes
    cmd.u_data_rate = 5000000    # uploaders data rate in bytes
    cmd.s_data_rate = 5000000     # servers data rate in bytes
    cmd.d_start_time = 2.0      # downloding clients start time in seconds
    cmd.u_start_time = 2.0      # uploading clients start time in seconds
    cmd.d_stop_time = 40.0      # downloading clients stop time in seconds
    cmd.u_stop_time = 40.0      # uploading clients stop time in seconds
    cmd.d_latency = 1           # downloading clients latency in ms
    cmd.u_latency = 1           # uploading clients latency in ms
    cmd.s_latency = 1           # servers latency in ms
    cmd.d_on_off = 1000       # downloading clients on off rate
    cmd.u_on_off = 1000       # uploading clients on off rate
    cmd.s_on_off = 1000       # servers on off rate
    cmd.sim_run_time = 50.0     # the total time the simulation should run
    cmd.error_rate = 0.02        # error rate of packets

    cmd.Parse(sys.argv)
    return cmd

def create_nodes(no_of_downloaders, no_of_uploaders):
    s_node = ns.network.NodeContainer()
    s_node.Create(2)
    d_nodes = ns.network.NodeContainer()
    d_nodes.Create(no_of_downloaders)
    u_nodes = ns.network.NodeContainer()
    u_nodes.Create(no_of_uploaders)
    return s_node, d_nodes, u_nodes

def link_nodes(s_node, d_nodes, u_nodes, queue_length):
    ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(queue_length))
    s_link = ns.network.NodeContainer()
    s_link.Add(s_node.Get(0))
    s_link.Add(s_node.Get(1))
    d_links = list()
    for i in range(0, d_nodes.GetN()):
        link = ns.network.NodeContainer()
        link.Add(s_node.Get(1))
        link.Add(d_nodes.Get(i))
        d_links.append(link)
    u_links = list()
    for i in range(0, u_nodes.GetN()):
        link = ns.network.NodeContainer()
        link.Add(s_node.Get(1))
        link.Add(u_nodes.Get(i))
        u_links.append(link)
    return s_link, d_links, u_links

def install_network_devices(s_link, s_rate, s_latency, d_links, d_rate, d_latency, u_links, u_rate, u_latency):
    point_to_point = ns.point_to_point.PointToPointHelper()
    point_to_point.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))   #maximum transmission unit allowed on internet is 1500 bytes
    point_to_point.SetDeviceAttribute("DataRate", ns.network.DataRateValue(ns.network.DataRate(d_rate)))
    point_to_point.SetChannelAttribute("Delay", ns.core.TimeValue(ns.core.MilliSeconds(d_latency)))
    d_devices = list()
    for link in d_links:
        d_devices.append(point_to_point.Install(link))

    point_to_point.SetDeviceAttribute("DataRate", ns.network.DataRateValue(ns.network.DataRate(u_rate)))
    point_to_point.SetChannelAttribute("Delay", ns.core.TimeValue(ns.core.MilliSeconds(u_latency)))
    u_devices = list()
    for link in u_links:
        u_devices.append(point_to_point.Install(link))

    point_to_point.SetDeviceAttribute("DataRate", ns.network.DataRateValue(ns.network.DataRate(s_rate)))
    point_to_point.SetChannelAttribute("Delay", ns.core.TimeValue(ns.core.MilliSeconds(s_latency)))
    s_device = point_to_point.Install(s_link)

    #Enable Pcap here
    point_to_point.EnablePcap("sim4", s_device.Get(0), True)

    return s_device, d_devices, u_devices

def set_error_model(s_device, error_rate):
    em = ns.network.RateErrorModel()
    em.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
    em.SetAttribute("ErrorRate", ns.core.DoubleValue(error_rate))
    s_device.Get(0).SetReceiveErrorModel(em)

def configure_tcp():
    ns.core.Config.SetDefault("ns3::TcpSocket::SegmentSize", ns.core.UintegerValue(1448))
    ns.core.Config.SetDefault("ns3::TcpNewReno::ReTxThreshold", ns.core.UintegerValue(4))
    ns.core.Config.SetDefault("ns3::TcpWestwood::ProtocolType",
                              ns.core.StringValue("WestwoodPlus"))

def create_protocol_stack(s_node, d_nodes, u_nodes):
    stack = ns.internet.InternetStackHelper()
    stack.Install(s_node)
    stack.Install(d_nodes)
    stack.Install(u_nodes)
    return stack

def assign_ip(s_devices, s_ip, s_mask, d_devices, d_ip, d_mask, u_devices, u_ip, u_mask):
    address = ns.internet.Ipv4AddressHelper()
    #ip = s_ip.replace("x", str((i & 65280) >> 8), 1)
    #ip = ip.replace("x", str(i & 255), 1)
    address.SetBase(ns.network.Ipv4Address(s_ip.replace("x", str(0))), ns.network.Ipv4Mask(s_mask))
    #address.SetBase(ns.network.Ipv4Address(ip), ns.network.Ipv4Mask(s_mask))
    s_addr = address.Assign(s_devices)
    d_addr = list()
    for i, d in enumerate(d_devices):
        ip = d_ip.replace("x", str((i & 65280) >> 8), 1)
        ip = ip.replace("x", str(i & 255), 1)
        #print(ip)
        #address.SetBase(ns.network.Ipv4Address(d_ip.replace("x", str(i))), ns.network.Ipv4Mask(d_mask))
        address.SetBase(ns.network.Ipv4Address(ip), ns.network.Ipv4Mask(d_mask))
        d_addr.append(address.Assign(d))
    u_addr = list()
    for i, d in enumerate(u_devices):
        ip = u_ip.replace("x", str((i & 65280) >> 8), 1)
        ip = ip.replace("x", str(i & 255), 1)
        #address.SetBase(ns.network.Ipv4Address(u_ip.replace("x", str(i))), ns.network.Ipv4Mask(u_mask))
        address.SetBase(ns.network.Ipv4Address(ip), ns.network.Ipv4Mask(u_mask))
        u_addr.append(address.Assign(d))
    return s_addr, d_addr, u_addr

def setup_tcp_connection(src_node, dst_node, dst_addr, start_time, stop_time, on_off_rate):
    packet_sink_helper = ns.applications.PacketSinkHelper("ns3::TcpSocketFactory",
        ns.network.InetSocketAddress(ns.network.Ipv4Address.GetAny(), 8080))
    sink_apps = packet_sink_helper.Install(dst_node)
    sink_apps.Start(ns.core.Seconds(2.0))
    sink_apps.Stop(ns.core.Seconds(50.0))

    on_off_tcp_helper = ns.applications.OnOffHelper("ns3::TcpSocketFactory",
        ns.network.Address(ns.network.InetSocketAddress(dst_addr, 8080)))
    on_off_tcp_helper.SetAttribute("DataRate",
        ns.network.DataRateValue(ns.network.DataRate(on_off_rate)))
    on_off_tcp_helper.SetAttribute("PacketSize",
        ns.core.UintegerValue(1500))
    on_off_tcp_helper.SetAttribute("OnTime",
        ns.core.StringValue("ns3::ConstantRandomVariable[Constant=2]"))
    on_off_tcp_helper.SetAttribute("OffTime",
        ns.core.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
    #    ns.core.StringValue("ns3::UniformRandomVariable[Min=1,Max=2]"))
    #    ns.core.StringValue("ns3::ExponentialRandomVariable[Mean=2]"))

    client_apps = on_off_tcp_helper.Install(src_node)
    client_apps.Start(start_time)
    client_apps.Stop(stop_time)

def setup_downloaders(s_node, d_nodes, d_ips, start_time, stop_time, on_off_rate):
    for i in range(0, d_nodes.GetN()):
        node = d_nodes.Get(i)
        server = s_node.Get(0)
        setup_tcp_connection(server, node, d_ips[i].GetAddress(0), ns.core.Seconds(start_time), ns.core.Seconds(stop_time), on_off_rate)

def setup_uploaders(s_node, u_nodes, s_ips, start_time, stop_time, on_off_rate):
    for i in range(0, u_nodes.GetN()):
        node = u_nodes.Get(i)
        server = s_node.Get(0)
        setup_tcp_connection(node, server, s_ips.GetAddress(1), ns.core.Seconds(start_time), ns.core.Seconds(stop_time), on_off_rate)

def create_pcap():
    pass

def create_flowmon():
    flowmon_helper = ns.flow_monitor.FlowMonitorHelper()
    monitor = flowmon_helper.InstallAll()
    return monitor, flowmon_helper

def flowmon_analysis(monitor, flowmon_helper):
    monitor.CheckForLostPackets()

    classifier = flowmon_helper.GetClassifier()

    for flow_id, flow_stats in monitor.GetFlowStats():
        #if flow_id == 1:
        if 1==1:
            t = classifier.FindFlow(flow_id)
            proto = {6: 'TCP', 17: 'UDP'} [t.protocol]
            print ("FlowID: %i (%s %s/%s --> %s/%i)" %
                    (flow_id, proto, t.sourceAddress, t.sourcePort, t.destinationAddress, t.destinationPort))

            #print ("  Tx Bytes: %i" % flow_stats.txBytes)
            #print ("  Rx Bytes: %i" % flow_stats.rxBytes)
            #print ("  Lost Pkt: %i" % flow_stats.lostPackets)
            #print ("  Flow active: %fs - %fs" % (flow_stats.timeFirstTxPacket.GetSeconds(),
            #                                    flow_stats.timeLastRxPacket.GetSeconds()))

            #print("D: " + str(dl) + "     U: " + str(ul))
            print ("  Throughput: %f Mbps" % (flow_stats.rxBytes *
                                             8.0 /
                                             (flow_stats.timeLastRxPacket.GetSeconds()
                                               - flow_stats.timeFirstTxPacket.GetSeconds())/
                                             1024/
                                             1024))
        #print("rxBytes: " + str(flow_stats.rxBytes))
        #print("timeLastRxPacket: " + str(flow_stats.timeLastRxPacket.GetSeconds()))
        #print("timeFirstTxPacket: " + str(flow_stats.timeFirstTxPacket.GetSeconds()))

def sim(downloaders, uploaders, cmd):
    s_node, d_nodes, u_nodes = create_nodes(downloaders, uploaders)
    s_link, d_links, u_links = link_nodes(
        s_node, d_nodes, u_nodes, int(cmd.queue_length)
    )
    s_devices, d_devices, u_devices = install_network_devices(
        s_link, int(cmd.s_data_rate), int(cmd.s_latency),
        d_links, int(cmd.d_data_rate), int(cmd.d_latency),
        u_links, int(cmd.u_data_rate), int(cmd.u_latency)
    )

    set_error_model(s_devices, float(cmd.error_rate))

    configure_tcp()
    stack = create_protocol_stack(s_node, d_nodes, u_nodes)
    s_ips, d_ips, u_ips = assign_ip(
        s_devices, "1.x.x.0", "255.255.255.0",
        d_devices, "2.x.x.0", "255.255.255.0",
        u_devices, "3.x.x.0", "255.255.255.0"
    )
    ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()
    setup_downloaders(s_node, d_nodes, d_ips, float(cmd.d_start_time), float(cmd.d_stop_time), int(cmd.d_on_off))    # start time 2 and stop time 40 and on off rate 300000
    setup_uploaders(s_node, u_nodes, s_ips, float(cmd.u_start_time), float(cmd.u_stop_time), int(cmd.u_on_off))    # start time 2 and stop time 40 and on off rate 300000
    monitor, helper = create_flowmon()
    ns.core.Simulator.Stop(ns.core.Seconds(float(cmd.sim_run_time)))
    ns.core.Simulator.Run()
    flowmon_analysis(monitor, helper)
    ns.core.Simulator.Destroy()


def main():
    cmd = parse_commands()
    sim(int(cmd.d_max), int(cmd.u_max), cmd)

main()
