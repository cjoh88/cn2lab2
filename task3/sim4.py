#!/usr/bin/python

import sys
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor

def parse_commands():
    cmd = ns.core.CommandLine()

    cmd.d_min = 1
    cmd.d_max = 100
    cmd.u_min = 1
    cmd.u_max = 100
    cmd.d_queue_length = 5
    cmd.u_queue_length = 5
    cmd.d_data_rate = 50000
    cmd.u_data_rate = 50000
    cmd.d_start_time = 2.0
    cmd.u_start_time = 2.0
    cmd.d_stop_time = 40.0
    cmd.u_stop_time = 40.0
    cmd.d_latency = 1
    cmd.u_latency = 1
    cmd.d_on_off = 300000
    cmd.u_on_off = 300000
    cmd.sim_run_time = 50.0

    cmd.Parse(sys.argv)
    return cmd

def create_nodes(no_of_downloaders, no_of_uploaders):
    s_node = ns.network.NodeContainer()
    s_node.Create(1)
    d_nodes = ns.network.NodeContainer()
    d_nodes.Create(no_of_downloaders)
    u_nodes = ns.network.NodeContainer()
    u_nodes.Create(no_of_uploaders)
    return s_node, d_nodes, u_nodes

def link_nodes(s_node, nodes, queue_length):
    ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(queue_length))
    links = list()
    for i in range(0, nodes.GetN()):
        link = ns.network.NodeContainer()
        link.Add(s_node.Get(0))
        link.Add(nodes.Get(i))
        links.append(link)
    return links

def install_network_devices(links, data_rate, latency):
    point_to_point = ns.point_to_point.PointToPointHelper()
    point_to_point.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))   #maximum transmission unit allowed on internet is 1500 bytes
    point_to_point.SetDeviceAttribute("DataRate", ns.network.DataRateValue(ns.network.DataRate(data_rate)))
    point_to_point.SetChannelAttribute("Delay", ns.core.TimeValue(ns.core.MilliSeconds(latency)))
    devices = list()
    for link in links:
        devices.append(point_to_point.Install(link))
    return devices

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

def assign_ip(devices, ip, net_mask):
    address = ns.internet.Ipv4AddressHelper()
    addresses = list()
    for i, d in enumerate(devices):
        address.SetBase(ns.network.Ipv4Address(ip.replace("x", str(i))), ns.network.Ipv4Mask(net_mask))
        addresses.append(address.Assign(d))
    return addresses

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
    #                      ns.core.StringValue("ns3::UniformRandomVariable[Min=1,Max=2]"))
    #                      ns.core.StringValue("ns3::ExponentialRandomVariable[Mean=2]"))

    client_apps = on_off_tcp_helper.Install(src_node)
    client_apps.Start(start_time)
    client_apps.Stop(stop_time)

def setup_downloaders(s_node, d_nodes, d_ips, start_time, stop_time, on_off_rate):
    for i in range(0, d_nodes.GetN()):
        node = d_nodes.Get(i)
        server = s_node.Get(0)
        setup_tcp_connection(server, node, d_ips[i].GetAddress(1), ns.core.Seconds(start_time), ns.core.Seconds(stop_time), on_off_rate)

def setup_uploaders(s_node, u_nodes, u_ips, start_time, stop_time, on_off_rate):
    for i in range(0, u_nodes.GetN()):
        node = u_nodes.Get(i)
        server = s_node.Get(0)
        setup_tcp_connection(node, server, u_ips[i].GetAddress(0), ns.core.Seconds(start_time), ns.core.Seconds(stop_time), on_off_rate)

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

            print ("  Tx Bytes: %i" % flow_stats.txBytes)
            print ("  Rx Bytes: %i" % flow_stats.rxBytes)
            print ("  Lost Pkt: %i" % flow_stats.lostPackets)
            print ("  Flow active: %fs - %fs" % (flow_stats.timeFirstTxPacket.GetSeconds(),
                                                flow_stats.timeLastRxPacket.GetSeconds()))

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

def sim(downloaders,
        uploaders,
        cmd):
    s_node, d_nodes, u_nodes = create_nodes(downloaders, uploaders) #create 10 downloaders and 10 uploaders
    d_links = link_nodes(s_node, d_nodes, int(cmd.d_queue_length))
    u_links = link_nodes(s_node, u_nodes, int(cmd.u_queue_length))
    d_devices = install_network_devices(d_links, int(cmd.d_data_rate), int(cmd.d_latency)) # data rate of 50000 bps and 1 ms latency
    u_devices = install_network_devices(u_links, int(cmd.u_data_rate), int(cmd.u_latency)) # data rate of 50000 bps and 1 ms latency
    configure_tcp()
    stack = create_protocol_stack(s_node, d_nodes, u_nodes)
    d_ips = assign_ip(d_devices, "10.1.x.0", "255.255.255.0")
    u_ips = assign_ip(u_devices, "10.2.x.0", "255.255.255.0")
    setup_downloaders(s_node, d_nodes, d_ips, float(cmd.d_start_time), float(cmd.d_stop_time), int(cmd.d_on_off))    # start time 2 and stop time 40 and on off rate 300000
    setup_uploaders(s_node, u_nodes, u_ips, float(cmd.u_start_time), float(cmd.u_stop_time), int(cmd.u_on_off))    # start time 2 and stop time 40 and on off rate 300000
    monitor, helper = create_flowmon()
    ns.core.Simulator.Stop(ns.core.Seconds(float(cmd.sim_run_time)))
    ns.core.Simulator.Run()
    flowmon_analysis(monitor, helper)
    ns.core.Simulator.Destroy()


def main():
    cmd = parse_commands()
    sim(int(cmd.d_max), int(cmd.u_max), cmd)

main()
