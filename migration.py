#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for DWBA in hybrid-PON
# objective: minimize traffic migration, fairness in traffic migration, fairness in packet delay
# JialongLi 2017/08/14


# relative traffic in two areas, period = 2 hours
residence = [0.20, 0.10, 0.05, 0.10, 0.20, 0.20, 0.30, 0.20, 0.40, 0.80, 1.00, 0.90]
business  = [0.05, 0.05, 0.05, 0.40, 0.80, 1.00, 0.90, 1.00, 0.80, 0.20, 0.10, 0.05]