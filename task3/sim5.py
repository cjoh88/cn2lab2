#!/usr/bin/python

import sys
import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.flow_monitor
import time
import random
import matplotlib.pyplot as plt

def seed_rng():
    #ns.core.RngSeedManager.SetSeed(int(time.time() * 1000 % (2**31-1)))
    ns.core.RngSeedManager.SetSeed(random.randint(0, sys.maxint))
    #print(str(int(time.time() * 1000 % (2**31-1))))
    #print(str(random.randint(0, sys.maxint)))
    #sys.exit()

def command_line():
    cmd = ns.core.CommandLine()

    # Default values
    cmd.queue_length = 1
    cmd.d_max = 1
    cmd.u_min = 0
    cmd.u_step = 100
    cmd.u_max = 1000
    cmd.latency = 100
    cmd.rate = 500000
    cmd.error_rate = 0.2
    cmd.attempts = 20

    cmd.on_off_rate = 300000 #300000
    cmd.AddValue ("rate", "P2P data rate in bps")
    cmd.AddValue ("latency", "P2P link Latency in miliseconds")
    cmd.AddValue ("on_off_rate", "OnOffApplication data sending rate")
    cmd.Parse(sys.argv)
    return cmd

def create_nodes(no_of_downloaders, no_of_uploaders):
    nodes = ns.network.NodeContainer()
    nodes.Create(3 + no_of_downloaders + no_of_uploaders)
    return nodes

def connect_nodes(nodes, queue_length):
    ns.core.Config.SetDefault("ns3::DropTailQueue::MaxPackets", ns.core.UintegerValue(queue_length))
    links = dict()

    links["n0n1"] = ns.network.NodeContainer()
    links["n0n1"].Add(nodes.Get(0))
    links["n0n1"].Add(nodes.Get(1))

    links["n1n2"] = ns.network.NodeContainer()
    links["n1n2"].Add(nodes.Get(1))
    links["n1n2"].Add(nodes.Get(2))

    for i in range(3, nodes.GetN()):
        s = "n2n" + str(i)
        links[s] = ns.network.NodeContainer()
        links[s].Add(nodes.Get(2))
        links[s].Add(nodes.Get(i))
    return links

def install_devices(links, data_rate, latency):
    # create point-to-point helper with common attributes
    pointToPoint = ns.point_to_point.PointToPointHelper()
    pointToPoint.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1500))
    pointToPoint.SetDeviceAttribute("DataRate",
                                ns.network.DataRateValue(ns.network.DataRate(data_rate)))
    pointToPoint.SetChannelAttribute("Delay",
                                ns.core.TimeValue(ns.core.MilliSeconds(latency)))
    devices = dict()

    #devices["d0d1"] = pointToPoint.Install(links["n0n1"])
    #devices["d1d2"] = pointToPoint.Install(links["n1n2"])
    for k, v in links.items():
        s = k.replace("n", "d")
        devices[s] = pointToPoint.Install(v)
    pointToPoint.EnablePcap("pcap/sim5-uploaders-" + str(len(links) - 3), devices["d2d3"].Get(1), True)
    return devices

def set_error_model(devices, rate):
    em = ns.network.RateErrorModel()
    em.SetAttribute("ErrorUnit", ns.core.StringValue("ERROR_UNIT_PACKET"))
    em.SetAttribute("ErrorRate", ns.core.DoubleValue(rate))
    devices["d1d2"].Get(1).SetReceiveErrorModel(em)

def configure_tcp():
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

def create_protocol_stack(nodes):
    stack = ns.internet.InternetStackHelper()
    stack.Install(nodes)

def assign_ip(devices):
    helper = ns.internet.Ipv4AddressHelper()
    address = dict()
    i = 0
    for k, v in devices.items():
        s = k.replace("d", "if")
        ip = "x.x.x.0"
        x1 = 16711680
        x2 = 65280
        x3 = 255
        ip = ip.replace("x", str((i & x1) >> 16), 1)
        ip = ip.replace("x", str((i & x2) >> 8), 1)
        ip = ip.replace("x", str((i & x3)), 1)
        #print(ip)
        helper.SetBase(ns.network.Ipv4Address(ip), ns.network.Ipv4Mask("255.255.255.0"))
        address[s] = helper.Assign(v)
        i += 1
    ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()
    return address

def setup_tcp_connection(src_node, dst_node, dst_addr, start_time, stop_time, on_off_rate):
    packet_sink_helper = ns.applications.PacketSinkHelper(
        "ns3::TcpSocketFactory",
        ns.network.InetSocketAddress(
            ns.network.Ipv4Address.GetAny(),
            8080
        )
    )

    sink_apps = packet_sink_helper.Install(dst_node)
    sink_apps.Start(ns.core.Seconds(2.0))
    sink_apps.Stop(ns.core.Seconds(50.0))

    on_off_tcp_helper = ns.applications.OnOffHelper(
        "ns3::TcpSocketFactory",
        ns.network.Address(
            ns.network.InetSocketAddress(dst_addr, 8080)
        )
    )
    on_off_tcp_helper.SetAttribute(
        "DataRate",
        ns.network.DataRateValue(
            ns.network.DataRate(on_off_rate)
        )
    )
    on_off_tcp_helper.SetAttribute(
        "PacketSize",
        ns.core.UintegerValue(1500)
    )
    on_off_tcp_helper.SetAttribute(
        "OnTime",
        #ns.core.StringValue("ns3::ConstantRandomVariable[Constant=2]")
        ns.core.StringValue("ns3::ExponentialRandomVariable[Mean=2]")
    )
    on_off_tcp_helper.SetAttribute(
        "OffTime",
        #ns.core.StringValue("ns3::ConstantRandomVariable[Constant=1]")
        #ns.core.StringValue("ns3::UniformRandomVariable[Min=1,Max=2]")
        ns.core.StringValue("ns3::ExponentialRandomVariable[Mean=1]")
        )


    client_apps = on_off_tcp_helper.Install(src_node)
    client_apps.Start(start_time)
    client_apps.Stop(stop_time)

def setup_tcp(nodes, address, no_of_downloaders, no_of_uploaders, on_off_rate):
    for i in range(3, 3 + no_of_downloaders):
        ip = "if2if" + str(i)
        setup_tcp_connection(
            nodes.Get(0),
            nodes.Get(i),
            address[ip].GetAddress(1),
            ns.core.Seconds(2.0),
            ns.core.Seconds(40.0),
            on_off_rate
        )
    for i in range(3 + no_of_downloaders, 3 + no_of_downloaders + no_of_uploaders):
        ip = "if0if1"
        setup_tcp_connection(
            nodes.Get(i),
            nodes.Get(0),
            address[ip].GetAddress(0),
            ns.core.Seconds(2.0),
            ns.core.Seconds(40.0),
            on_off_rate
        )



def create_flow_monitor():
    helper = ns.flow_monitor.FlowMonitorHelper()
    monitor = helper.InstallAll()
    return monitor, helper

def run(seconds):
    ns.core.Simulator.Stop(ns.core.Seconds(seconds))
    ns.core.Simulator.Run()

def get_throughput(flow_stats):
    return (flow_stats.rxBytes *
                                       8.0 /
                                       (flow_stats.timeLastRxPacket.GetSeconds()
                                         - flow_stats.timeFirstTxPacket.GetSeconds())/
                                       1024/
                                       1024)

def analyse(monitor, flowmon_helper):
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

def analyse_downloader(monitor, flowmon_helper, address):
    monitor.CheckForLostPackets()
    classifier = flowmon_helper.GetClassifier()
    data = dict()
    ack = dict()

    for flow_id, flow_stats in monitor.GetFlowStats():
        t = classifier.FindFlow(flow_id)
        #print(address["if2if3"].GetAddress(1))
        downloader = get_downloader_addr(address)
        if downloader == t.sourceAddress:   #acks
            ack["throughput"] = get_throughput(flow_stats)
            ack["packet_loss"] = flow_stats.lostPackets

        elif get_downloader_addr(address) == t.destinationAddress:  #data
            data["throughput"] = get_throughput(flow_stats)
            data["packet_loss"] = flow_stats.lostPackets
        #print(t.sourceAddress)
    return data, ack


def get_downloader_addr(address):
    return address["if2if3"].GetAddress(1)

def get_server_addr(address):
    return address["if0if1"].GetAddress(0)

def get_uploader_addr(address, no_of_downloaders):
    key = "if2if" + str(3 + no_of_downloaders)
    return address[key].GetAddress(1)

def destroy():
    ns.core.Simulator.Destroy()

def print_result(result):
    print("Throughput:  %f Mbps" % result["throughput"])
    print("Packet loss: %i" % result["packet_loss"])

def sim(no_of_downloaders, no_of_uploaders, cmd):
    seed_rng()
    nodes = create_nodes(no_of_downloaders, no_of_uploaders)
    links = connect_nodes(nodes, int(cmd.queue_length))
    devices = install_devices(links, int(cmd.rate), int(cmd.latency))
    set_error_model(devices, float(cmd.error_rate))
    configure_tcp()
    create_protocol_stack(nodes)
    address = assign_ip(devices)
    setup_tcp(nodes, address, no_of_downloaders, no_of_uploaders, int(cmd.on_off_rate))
    monitor, flowmon_helper = create_flow_monitor()
    run(50.0)
    #analyse(monitor, flowmon_helper)
    data, ack = analyse_downloader(monitor, flowmon_helper, address)
    destroy()
    return data, ack

def plot(uploaders, througput, packet_loss):
    plt.figure("Throughput")
    plt.plot(uploaders, througput)
    plt.ylabel("Mbits")
    #plt.show()

    plt.figure("packet_loss")
    plt.plot(uploaders, packet_loss)
    plt.ylabel("Avg packets lost")
    plt.show()

def main():
    cmd = command_line()
    #data, ack = sim(int(cmd.d_max), int(cmd.u_max), cmd)
    #print_result(data)
    #sys.exit()
    #uploaders = list()
    #th = list()
    tf = open("througput.r", "a")
    pf = open("packet_loss.r", "a")
    throughput_result = list()
    packet_loss_result = list()
    uploaders_result = list()
    for no_uploaders in range(0, int(cmd.u_max), int(cmd.u_step)):
        #data, ack = sim(int(cmd.d_max), no_uploaders, cmd)
        #print_result(data)
        result_data = list()
        for i in range(0,int(cmd.attempts)):
            data, ack = sim(int(cmd.d_max), no_uploaders, cmd)
            result_data.append(data)
        throughput = 0.0
        packet_loss = 0.0
        tf.write("u_" + str(no_uploaders) + " = c(")
        pf.write("u_" + str(no_uploaders) + " = c(")
        for i in range(0, len(result_data)):
            throughput += result_data[i]["throughput"]
            tf.write(str(result_data[i]["throughput"]) + ", ")
            packet_loss += result_data[i]["packet_loss"]
            pf.write(str(result_data[i]["packet_loss"]) + ", ")
        tf.write(")\n")
        pf.write(")\n")
        tf.write("mean_" + str(no_uploaders) + " = mean(u_" + str(no_uploaders) + ")\n")
        pf.write("mean_" + str(no_uploaders) + " = mean(u_" + str(no_uploaders) + ")\n")
        tf.write("sd_" + str(no_uploaders) + " = sd(u_" + str(no_uploaders) + ")\n")
        pf.write("sd_" + str(no_uploaders) + " = sd(u_" + str(no_uploaders) + ")\n")
        attempts = int(cmd.attempts)
        #confidence level 0.95
        tf.write("ce_" + str(no_uploaders) + " = (sd_" + str(no_uploaders) + " / sqrt(" + str(attempts) + ")) * 1.96\n")
        tf.write("print(\"mean_" + str(no_uploaders) + "\")\n")
        tf.write("print(mean_" + str(no_uploaders) + ")\n")
        tf.write("print(\"ce_" + str(no_uploaders) + "\")\n")
        tf.write("print(ce_" + str(no_uploaders) + ")\n")
        tf.write("print(\"---------------------------\")\n")
        pf.write("ce_" + str(no_uploaders) + " = (sd_" + str(no_uploaders) + " / sqrt(" + str(attempts) + ")) * 1.96\n")
        pf.write("print(\"mean_" + str(no_uploaders) + "\")\n")
        pf.write("print(mean_" + str(no_uploaders) + ")\n")
        pf.write("print(\"ce_" + str(no_uploaders) + "\")\n")
        pf.write("print(ce_" + str(no_uploaders) + ")\n")
        pf.write("print(\"---------------------------\")\n")
        print("No of uploaders: " + str(no_uploaders))
        print(" Avg throughput:  " + str(throughput / len(result_data)))
        print(" Avg packet loss: " + str(packet_loss / len(result_data)))
        #result = {
        #    "uploaders": no_uploaders,
        #    "throughput": throughput / len(result_data),
        #    "packet_loss": packet_loss / len(result_data)
        #}
        throughput_result.append(throughput / len(result_data))
        packet_loss_result.append(packet_loss / len(result_data))
        uploaders_result.append(no_uploaders)
    tf.close()
    pf.close()
    plot(uploaders_result, throughput_result, packet_loss_result)

main()
