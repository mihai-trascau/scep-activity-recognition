import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, MinuteLocator, SecondLocator
import numpy as np
from StringIO import StringIO
import datetime
import time
from pytz import timezone
import re
from multiprocessing import Process

def parseDate(inputDate):
    dateComponents = [int(token.strip()) for token in re.split("\(|\)|,",inputDate.strip()) if token.strip().isdigit()]
    parsedDate = datetime.datetime(*dateComponents[:-1])
    return parsedDate

def extractData(inputData):
    for line in inputData:
        if line.strip() and not line.startswith("%"):
            datimeRegex = re.compile(r"datime\(.*?\)")
            dates = datimeRegex.findall(line)
            startDate = parseDate(dates[0])
            endDate = parseDate(dates[1])
            tokens = [rawToken.strip() for rawToken in re.split('[(),\[\]]',line.strip()) if rawToken.strip()]
            if tokens:
                extracted = tokens[1:4]
                extracted.extend(tokens[5:7])
                extracted.append(str(time.mktime((startDate + datetime.timedelta(hours=3)).timetuple())))
                extracted.append(str(time.mktime((endDate + datetime.timedelta(hours=3)).timetuple())))
                yield ','.join(extracted)+"\n"

def timelines(y, xstart, xstop, color='b'):
    """Plot timelines at y from xstart to xstop with given color."""   
    plt.hlines(y, xstart, xstop, color, lw=4)
    plt.scatter(xstart,y,s=100,c=color,marker=".",lw=2,edgecolor=color)
    plt.scatter(xstop,y,s=100,c=color,marker=".",lw=2,edgecolor=color)
    plt.xticks(np.arange(min(xstart), max(xstop)+1, 5.0))

def plotEventStream(inputStream):
    data = np.genfromtxt(extractData(inputStream), 
        names=['input_type', 'user', 'input_value', 'last_update', 'confidence', 'start_time', 'end_time'], dtype=None, delimiter=',')
    input_type, user, input_value, last_update, confidence, start_time, end_time = data['input_type'], data['user'], data['input_value'], data['last_update'], data['confidence'], data['start_time'], data['end_time']

    # data = np.genfromtxt(extractData(inputStream),
    #     names=['input_type', 'user', 'input_value', 'last_update', 'confidence'], dtype=None, delimiter=',')
    # input_type, user, input_value, last_update, confidence = data['input_type'], data['user'], data['input_value'], data['last_update'], data['confidence']


    # input_combos = data[['input_type','input_value']]
    # input_combos = data[['input_type','input_value', 'start_time', 'end_time']]
    input_combos = data[['input_type', 'user', 'input_value', 'last_update', 'confidence', 'start_time', 'end_time']]
    input_types, unique_idx, input_type_markers = np.unique(input_combos, 1, 1)
    y = (input_type_markers + 1) / float(len(input_types) + 1)

    # input_types, unique_idx, input_type_markers = np.unique(input_type, 1, 1)
    # y = (input_type_markers + 1) / float(len(input_types) + 1)

    colorMap = {}
    colorMap['pos'] = 'r'
    colorMap['lla'] = 'b'
    colorMap['hla'] = 'g'
    #Plot ok tl black    
    timelines(y, start_time, end_time, colorMap['hla'])
    # for input_ in input_types:
    #     typeFilter = (data[['input_type','input_value']] == input_)
    #     timelines(y[typeFilter], start_time[typeFilter], end_time[typeFilter], colorMap[input_[0]])

    #Setup the plot
    ax = plt.gca()
    # ax.xaxis_date()
    # myFmt = DateFormatter('%H:%M:%S')
    # ax.xaxis.set_major_formatter(myFmt)
    # ax.xaxis.set_major_locator(SecondLocator(interval=20)) # used to be SecondLocator(0, interval=20)

    #To adjust the xlimits a timedelta is needed.
    delta = (end_time.max() - start_time.min())/20

    input_names = []
    for input_ in input_types:
        input_names.append(input_[0].upper() + "(" + input_[1] + ")")
    plt.yticks(y[unique_idx], input_names)
    plt.ylim(0,1)
    plt.xlim(start_time.min()-delta, end_time.max()+delta)
    plt.xlabel('Time')
    plt.show()

f = open("../single_hla_120s_01er_015fd.stream")
g = open("../output.stream")
p1 = Process(target=plotEventStream,args=([g]))
p2 = Process(target=plotEventStream,args=([f]))
p1.start()
p2.start()
p1.join()
p2.join()