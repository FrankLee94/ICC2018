#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for DWBA in hybrid-PON
# objective: energy efficiency and latency analysis
# JialongLi 2017/10/18
# if there are no specific instructions, the unit of time is μs
# the minimum time unit is μs

import random

ONU_NUM = 32
WAVELENGTH_NUM = 16
CAPACITY = 10.0
latency_list = [0.0, 0.136, 0.146, 0.157, 0.172, 0.191, 0.222, 0.275, 0.381, 0.661, 1.322]

def traffic_generation(traffic_load):
	traffic = [0.0 for i in range(ONU_NUM)]
	for i in range(ONU_NUM):
		if i < 8:
			traffic[i] = 0.25 * 5 * traffic_load / 0.1
		else:
			traffic[i] = 0.25 * traffic_load / 0.1
	return traffic

# for NEE algorithm, using random fit 
def random_fit(traffic):
	transmitter_num = [0 for i in range(8)]
	burden = [0 for i in range(WAVELENGTH_NUM)]  # 0 is unused, 1 is used
	for i in range(ONU_NUM):
		if traffic[i] > 9.9:
			transmitter_num[i] = int(traffic[i] / 10.0) + 1
			for k in range(transmitter_num[i]):
				for j in range(WAVELENGTH_NUM):
					wavelength_random = random.randint(0, WAVELENGTH_NUM - 1)
					if burden[wavelength_random] + traffic[i] / transmitter_num[i] <= 10.0:
						burden[wavelength_random] += traffic[i] / transmitter_num[i]
						break
		else:
			for j in range(WAVELENGTH_NUM):
				wavelength_random = random.randint(0, WAVELENGTH_NUM - 1)
				if burden[wavelength_random] + traffic[i] <= 10.0:
					burden[wavelength_random] += traffic[i]
					break
	return burden

def latency_NEE(burden):
	count_used_wavelength = 0
	count_latency = 0.0
	for i in range(WAVELENGTH_NUM):
		if burden[i] > 0.0:
			count_used_wavelength += 1
			index = int(burden[i])
			count_latency += latency_list[index]
		else:
			pass
	average_latency = round(count_latency / float(count_used_wavelength), 3)
	print 'average latency' + '\t' + str(average_latency) + 'ms'

def energy_consumption(traffic, rho):
	transmitter_num = [0 for i in range(ONU_NUM)]
	burden = [0 for i in range(WAVELENGTH_NUM)]  # 0 is unused, 1 is used
	for i in range(ONU_NUM):
		if traffic[i] > 10 * rho:
			transmitter_num[i] = int(traffic[i] / 10.0 / rho) + 1
			for k in range(transmitter_num[i]):
				for j in range(WAVELENGTH_NUM):
					if burden[j] + traffic[i] / transmitter_num[i] <= rho * 10.0:
						burden[j] += traffic[i] / transmitter_num[i]
						break
		else:
			transmitter_num[i] = 1
			for j in range(WAVELENGTH_NUM):
				if burden[j] + traffic[i] <= rho * 10.0:
					burden[j] += traffic[i]
					break
	return burden, transmitter_num

def energy_MEE(burden, transmitter_num):
	count_used_wavelength = 0
	count_transmitter = 0
	energy = 0
	for i in range(WAVELENGTH_NUM):
		if burden[i] > 0.0:
			count_used_wavelength += 1
		else:
			pass
	for item in transmitter_num:
		count_transmitter += item
	energy += count_used_wavelength + count_transmitter
	print 'used_wavelength'+ '\t' + str(count_used_wavelength)
	print 'transmitter_num'+ '\t' + str(count_transmitter)
	print 'average energy' + '\t' + str(energy)


if __name__ == '__main__':
	traffic = traffic_generation(0.4)
	rho_list = [0.4, 0.45, 0.5, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
	for rho in rho_list:
		burden, transmitter_num = energy_consumption(traffic, rho)
		print 'rho:  ' + '\t' + str(rho)
		energy_MEE(burden, transmitter_num)