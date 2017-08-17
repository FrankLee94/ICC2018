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
CAPACITY = 10.0
PERIOD = 1e7          # 1e7, 10s
RTT = 100             # single trip, 0.1ms
T_GUARD = 5           # 5μs


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

def set_arrive_rate():
	ONU_arrive_rate = []
	ONU_bandwidth = [0.1, 0.1, 0.1, 0.5]   # Gbps
	for item in ONU_bandwidth:
		arrive_rate = int(item * 1000 / 0.6328)
		ONU_arrive_rate.append(arrive_rate)
	return ONU_arrive_rate



# generate packets for a ONU in a PERIOD
def packet_generation(arrive_rate):
	onu_packet = []
	time_stamp = []  # record the generation time of each packet
	time_index = 0
	while time_index < PERIOD:
		Probability_Poisson = random.random()
		if Probability_Poisson == 0.0 or Probability_Poisson == 1.0:
			Probability_Poisson = 0.5
		interval = -(1e6 / arrive_rate_select) * math.log(1 - Probability_Poisson)   # generate a packet
		interval = int(round(interval))
		Probability_Uniform = random.random()
		packet_size = 64 + int (1454 * Probability_Uniform)  # byte
		time_index += interval       # generation time
		onu_packet.append(packet_size)
		time_stamp.append(time_index)
	return onu_packet, time_stamp

# generate packets for all ONU in a PERIOD
def packet_generation_one_period(ONU_arrive_rate):
	packet = [0 for i in range(ONU_NUM)]
	stamp = [0 for i in range(ONU_NUM)]
	for i in range(ONU_NUM):
		onu_packet, time_stamp = packet_generation(ONU_arrive_rate[i])
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
			if grant + trans_packet_size < MAX_GRANT:
				grant += trans_packet_size
				end_packet += 1
			else:
				break
			if len(onu_packet) - 1 == end_packet:
				break
		start_packet = ONU_object.end_packet + 1
	ONU_object.start_packet = start_packet
	ONU_object.end_packet = end_packet
	ONU_object.grant = grant
	ONU_object.current_burden -= grant


# report grant for the first time, absolute_clock = RTT
# grant does not surpass MAX_GRANT, in bit
def polling_init(ONU, packet, stamp, absolute_clock):
	for i in range(ONU_NUM):
		grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)

# packet transmission
def packet_transmission(ONU_object, absolute_clock):
	transmission_time = math.ceil(float(ONU_object.grant) / float(UPSTREAM_RATE))   # bit
	return int(transmission_time)

# packet delay: from packet arrive to transmission starts
def delay_calculation(ONU_object, time_stamp, absolute_clock):
	if ONU_object.start_packet > ONU_object.end_packet:  # no packet
		return
	else:
		for i in range(ONU_object.end_packet - ONU_object.start_packet + 1):
			ONU_object.total_delay += absolute_clock - time_stamp[ONU_object.start_packet + i]

# polling scheme
def polling(ONU, user_status_test, user_status_predict):
	packet, stamp = packet_generation_one_period(user_status_one_period_real)
	absolute_clock = RTT                   # before the first ONU sends data, the OLT needs to send a grant
	polling_init(ONU, packet, stamp, absolute_clock)   # report grant for the first time

	while absolute_clock < PERIOD:
		for i in range(ONU_NUM):
			transmission_time = packet_transmission(ONU[i], absolute_clock)
			delay_calculation(ONU[i], stamp[i], absolute_clock)
			absolute_clock += transmission_time
			grant_determine(ONU[i], packet[i], stamp[i], absolute_clock)
			absolute_clock += T_GUARD
			ONU[0].trans_time += transmission_time
			ONU[0].guard_time + T_GUARD
	for i in range(ONU_NUM):
		ONU[i].total_packet += len(packet[i])


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
	bandwidth_utilization = float(Optical_Network_Unit.trans_time) / float(Optical_Network_Unit.trans_time + Optical_Network_Unit.guard_time)
	bandwidth_utilization = round(bandwidth_utilization, 3)
	return average_delay, average_energy, ONU_delay
						
if __name__ == '__main__':
	ONU = ONU_initialization()
	polling()
	average_delay, average_energy, ONU_delay = statistics(ONU)
	print 'offer load' + '\t' + '0.' + str(i + 1)
	print 'average_delay' + '\t' + str(average_delay) + 'μs'
	print 'bandwidth_utilization' + '\t' + str(bandwidth_utilization)
	print '\n'
