import os
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from datetime import datetime
from ssdaq import subscribers
from target_calib import CameraConfiguration
from ssdaq import sslogger
import logging

color_set1 = [(228,26,28),
              (55,126,184),
                (77,175,74),
                (152,78,163),
                (255,127,0),
                (255,255,51),
                (166,86,40),
                (247,129,191),
                (153,153,153)]
color_set2 = [(251,180,174),
                (179,205,227),
                (204,235,197),
                (222,203,228),
                (254,217,166),
                (255,255,204),
                (229,216,189),
                (253,218,236),
                (242,242,242)]

color_set3 = [(166,206,227),
                (31,120,180),
                (178,223,138),
                (51,160,44),
                (251,154,153),
                (227,26,28),
                (253,191,111),
                (255,127,0),
                (202,178,214),
                (106,61,154),
                (255,255,153),
                (177,89,40)]
class DynamicPlotter():
    def __init__(self,ip,port,sampleinterval=0.1, timewindow=10., size=(600,350)):
        # PyQtGraph stuff
        self._interval = int(sampleinterval*1000)
        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow()
        self.win.setWindowTitle('Slow signal viewer')
        #data
        self.data = {'hv_current':list(),'hv_voltage':list()}
        self.time = list()
        self.plts = {}
        self.curve_names = list()
        self.plot_time_window = 10
        # self.win.addItem(pg.TextItem(text='HEJHEJHEJ', color=(200, 200, 200), html=None, anchor=(0, 0), border=None, fill=None, angle=0, rotateAxis=None),row=1 )
        # self._add_plot('HV current',('Current','A'),('Time','min'),['hv_current'])
        # self._add_plot('HV Voltage',('Voltage','V'),('Time','min'),['hv_voltage'])
        # self._add_plot('DAC HV Voltage (Super pixels 0-8)',('Voltage','V'),('Time','min'),['dac_suppix_%d'%i for i in range(9)])
        # self.win.nextRow()
        # self._add_plot('DAC HV Voltage (Super pixels 9-15)',('Voltage','V'),('Time','min'),['dac_suppix_%d'%i for i in range(9,16)])

        # self._add_plot('Temperature',('Temperature',u"\u00B0"+'C'),('Time','min'),['temp_powb','temp_auxb','temp_primb'])#,'temp_sipm'
        self.badpixs = np.array([  25,   58,  101,  304,  449,  570,  653, 1049, 1094, 1158, 1177,
       1381, 1427, 1434, 1439, 1765, 1829, 1869, 1945, 1957, 2009, 2043])
        self.img = pg.ImageItem(levels=(0,400))
        self.p = self.win.addPlot()
        self.p.addItem(self.img)
        self.c = CameraConfiguration("1.1.0")
        self.m = self.c.GetMapping()
        self.xpix = np.array(self.m.GetXPixVector())
        self.ypix = np.array(self.m.GetYPixVector())
        self.xmap = np.array(self.m.GetRowVector())
        self.ymap = np.array(self.m.GetColumnVector())
        self.map = np.zeros((48,48),dtype=np.uint64)
        for i in range(2048):
            self.map[self.xmap[i],self.ymap[i]] = i

        self.map = self.map.flatten()

         # Add a color scale
        # self.gl = pg.GradientLegend((20, 150), (-10, -10))
        # self.gl.setParentItem(self.img)
        # self.gl.scale(1,-1)
        # self.gl
        # self.colorScale.setLabels('Label')
        #self.p.scene().addItem(self.colorScale)
        # QTimer

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateplots)
        self.timer.start(self._interval)

        self.ss_listener = subscribers.SSReadoutSubscriber(port=port,ip=ip)
        self.ss_listener.start()

        # if(isinstance(ss_calib, np.array)):
        # else:
        # self.ss_calib = np.zeros(64)

    def _add_plot(self,title,labely,labelx,curves):
        self.curve_names += curves
        self.plts[title] = (self.win.addPlot(title=title),curves,list())
        self.plts[title][0].setLabel('left', labely[0], labely[1])
        self.plts[title][0].setLabel('bottom', labelx[0], labelx[1])
        self.plts[title][0].addLegend()
        self.plts[title][0].showGrid(x=True, y=True)
        for i,curve in enumerate(curves):
            t = sum((color_set1[i],(20,)),())
            self.plts[title][2].append(
                                        self.plts[title][0].plot(
                                                                np.linspace(0,10,10),
                                                                np.linspace(0,10,10),
                                                                pen=color_set1[i],
                                                                fillLevel=0,
                                                                fillBrush = t,
                                                                name=curve))
        self.plts[title][0].setXRange(-self.plot_time_window,0)
            # self.plts[title][2][i].setClickable()

    def get_data(self):
        evs = []
        ntries = 0
        while(ntries<10):
            try:
                ev = self.ss_listener.get_data(timeout=0.1)
                evs.append(ev._get_asic_mapped())
            except:
                ntries +=1
                break
        if(len(evs)==0):
            return
        else:
            data = evs[-1]
        imgdata = np.zeros((48,48))
        data = data.flatten()
        data[data<=0] = np.nan
        #print(data)

        #data = np.log10(data)
        data[self.badpixs] = np.nan
        print(data[data>0])
        imgdata[self.xmap,self.ymap] = data
        
        imgdata[np.isnan(imgdata)] = 0
        self.img.setImage(imgdata.T,levels=(0,400))

    def run(self):
        self.app.exec_()


    def _update_plot(self,time,plot):
        for i in range(len(plot[2])):
            plot[2][i].setData(time,self.data[plot[1][i]][::-1],fillLevel=0.5)


    def updateplots(self):
        self.get_data()

        self.app.processEvents()

def slowsignalviewer():
    import argparse
    from ssdaq.utils import common_args as cargs
    parser = argparse.ArgumentParser(
        description="A slow signal readout viewer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cargs.subport(parser, default=None)
    cargs.subaddr(parser)
    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    if  args.sub_ip != "127.0.0.101" and args.sub_port is None:
        args.sub_port = 10025
    else:
        args.sub_port = 9004

    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    plt = DynamicPlotter(ip= args.sub_ip, port = args.sub_port)
    plt.run()

if __name__ == "__main__":
    slowsignalviewer()
