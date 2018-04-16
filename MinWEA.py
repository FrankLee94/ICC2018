#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for DWBA in hybrid-PON
# objective: bandwidth utilization and packet delay fairness
# JialongLi 2017/08/14
# if there are no specific instructions, the unit of time is μs
# the minimum time unit is μs


import random
import math
import pickle
import copy
import time

ONU_NUM = 4
WAVELENGTH_NUM = 8
UPSTREAM_RATE = 1e10    # 10G/s
PERIOD = 1e7            # 1e7 μs, 10s
RTT = 100.0             # 100μs, single trip, 0.1ms
T_GUARD = 5.0           # 5μs

# relative traffic in two areas, period = 2 hours
residence = [0.20, 0.10, 0.05, 0.10, 0.20, 0.20, 0.30, 0.20, 0.40, 0.80, 1.00, 0.90]
business  = [0.05, 0.05, 0.05, 0.40, 0.80, 1.00, 0.90, 1.00, 0.80, 0.20, 0.10, 0.05]

class Optical_Network_Unit:
	def __init__(self, grant, start_packet, end_packet, trans_time, guard_time, total_packet, total_delay, current_burden):
		self.grant = grant
		self.start_packet = start_packet
		self.end_packet = end_packet
		self.trans_time = trans_time
		self.guard_time = guard_time
		self.total_packet = total_packet
		self.total_delay = total_delay
		self.current_burden = current_burden

# ONU initialization
def ONU_initialization():
	grant = 0
	start_packet = -1
	end_packet = -1
	trans_time = 0
	guard_time = 0
	total_packet = 0
	total_delay = 0
	current_burden = 0

	ONU = []
	for i in range(ONU_NUM):
		ONU_object = Optical_Network_Unit(grant, start_packet, end_packet, 
		trans_time, guard_time, total_packet, total_delay, current_burden)
		ONU.append(ONU_object)
	return ONU

def set_arrive_rate(period_num, area):
	ONU_arrive_rate = [0 for i in range(ONU_NUM)]
	ONU_bandwidth = [0 for i in range(ONU_NUM)]   # Gbps
	for i in range(ONU_NUM - 1):
		ONU_bandwidth[i] = area[period_num]
	ONU_bandwidth[ONU_NUM - 1] = area[period_num] * 5
	for i in range(ONU_NUM):
		arrive_rate = int(ONU_bandwidth[i] * 100000 / 0.6328)
		ONU_arrive_rate[i] = arrive_rate
	return ONU_arrive_rate

# generate packets for a ONU in a PERIOD
def packet_generation_one_ONU(arrive_rate):
	onu_packet = []
	time_stamp = []  # record the generation time of each packet
	time_index = 0
	while time_index < PERIOD:
		Probability_Poisson = random.random()
		if Probability_Poisson == 0.0 or Probability_Poisson == 1.0:
			Probability_Poisson = 0.5
		interval = -(1e6 / arrive_rate) * math.log(1 - Probability_Poisson)   # generate a packet
		interval = int(round(interval))
		Probability_Uniform = random.random()
		packet_size = 1 * (64 + int (1454 * Probability_Uniform))  # byte
		time_index += interval       # generation time
		onu_packet.append(packet_size)
		time_stamp.append(time_index)
	return onu_packet, time_stamp

# generate packets for all ONU in a PERIOD
def packet_generation_all_ONU(ONU_arrive_rate):
	packet = [0 for i in range(ONU_NUM)]
	stamp = [0 for i in range(ONU_NUM)]
	for i in range(ONU_NUM):
		onu_packet, time_stamp = packet_generation_one_ONU(ONU_arrive_rate[i])
		packet[i] = copy.deepcopy(onu_packet)
		stamp[i] = copy.deepcopy(time_stamp)
	return packet, stamp

# determine the transmission packet
# make sure that the time stamp of end packet can not be larger than absolute_clock
def grant_determine(ONU_object, onu_packet, time_stamp, absolute_clock):
	start_packet = ONU_object.start_packet
	end_packet = ONU_object.end_packet
	grant = 0
	if len(onu_packet) == 0 or len(onu_packet) - 1 == end_packet:
		start_packet = -1
		end_packet = -1
	else:
		while time_stamp[end_packet + 1] < absolute_clock:
			trans_packet_size = 8 * onu_packet[end_packet + 1]  # unit of oun_packet is byte
			grant += trans_packet_size
			end_packet += 1
			if len(onu_packet) - 1 == end_packet:
				break
		start_packet = ONU_object.end_packet + 1
	ONU_object.start_packet = start_packet
	ONU_object.end_packet = end_packet
	ONU_object.grant = grant


# report grant for the first time, absolute_clock = RTT
# grant does not surpass MAX_GRANT, in bit
def polling_init(ONU, packet, stamp, absolute_clock):
	for i in range(ONU_NUM):
		grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)

# packet transmission
def packet_transmission(ONU_object):
	transmission_time = float(ONU_object.grant) * 1e6 / float(UPSTREAM_RATE)  # bit, μs
	transmission_time = round(transmission_time, 4)    # μs
	return transmission_time

# packet delay: from packet arrive to transmission starts
def delay_calculation(ONU_object, time_stamp, absolute_clock):
	if ONU_object.start_packet > ONU_object.end_packet:  # no packet
		return
	else:
		for i in range(ONU_object.end_packet - ONU_object.start_packet + 1):
			ONU_object.total_delay += absolute_clock - time_stamp[ONU_object.start_packet + i]

# after each period (10s here), ONU needs to be reset. make sure that packet_delay...can not be reset
def reset(ONU):
	for i in range(ONU_NUM):
		ONU[i].grant = 0
		ONU[i].start_packet = -1
		ONU[i].end_packet = -1

# polling scheme
def polling(ONU, ONU_arrive_rate):
	packet, stamp = packet_generation_all_ONU(ONU_arrive_rate)
	absolute_clock = RTT                   # before the first ONU sends data, the OLT needs to send a grant
	polling_init(ONU, packet, stamp, absolute_clock)   # report grant for the first time

	while absolute_clock < PERIOD:
		for i in range(ONU_NUM):
			transmission_time = packet_transmission(ONU[i])
			delay_calculation(ONU[i], stamp[i], absolute_clock)
			absolute_clock += transmission_time
			grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)
			absolute_clock += T_GUARD
			ONU[0].trans_time += transmission_time
			ONU[0].guard_time += T_GUARD
	for i in range(ONU_NUM):
		ONU[i].total_packet += len(packet[i])
	reset(ONU)  # reset some parameters


# statistics
# delay and bandwidth utilization
def statistics(ONU):
	ONU_delay = []
	sum_packet = 0
	sum_delay = 0
	for i in range(ONU_NUM):
		sum_packet += ONU[i].total_packet
		sum_delay += ONU[i].total_delay
		ONU_delay.append(int(ONU[i].total_delay / ONU[i].total_packet))

	average_delay = int(sum_delay / sum_packet)
	bandwidth_utilization = float(ONU[0].trans_time) / float(ONU[0].trans_time + ONU[0].guard_time)
	print 'trans_time:' + '\t' + str(ONU[0].trans_time)
	print 'guard_time:' + '\t' + str(ONU[0].guard_time)
	print 'sum_packet' + '\t' + str(sum_packet)
	print 'sum_delay' + '\t' + str(sum_delay)
	bandwidth_utilization = round(bandwidth_utilization, 3)
	return average_delay, bandwidth_utilization, ONU_delay
						
if __name__ == '__main__':
	ONU = ONU_initialization()
	for i in range(24):
		print 'period:' + '\t' + str(i)
		if i < 12:
			ONU_arrive_rate = set_arrive_rate(i, residence)
		else:
			ONU_arrive_rate = set_arrive_rate(i - 12, business)
		polling(ONU, ONU_arrive_rate)

	average_delay, bandwidth_utilization, ONU_delay = statistics(ONU)
	print 'average_delay:' + '\t' + str(average_delay) + 'μs'
	print 'bandwidth_utilization:' + '\t' + str(bandwidth_utilization)
	print 'respective delay:' + '\n'
	for i in range(ONU_NUM):
		print 'ONU No. :' + str(i + 1) + '\t' + str(ONU_delay[i]) + 'μs' + '\n'