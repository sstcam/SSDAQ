import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from datetime import datetime
from ssdaq import subscribers
from target_calib import CameraConfiguration
from ssdaq import sslogger
import logging
from collections import defaultdict
from datetime import datetime
from ssdaq.data._ioimpl import SSDataReader
import ssdaq
from time import sleep
from numpy import nan

color_set1 = [
    (228, 26, 28),
    (55, 126, 184),
    (77, 175, 74),
    (152, 78, 163),
    (255, 127, 0),
    (255, 255, 51),
    (166, 86, 40),
    (247, 129, 191),
    (153, 153, 153),
]
color_set2 = [
    (251, 180, 174),
    (179, 205, 227),
    (204, 235, 197),
    (222, 203, 228),
    (254, 217, 166),
    (255, 255, 204),
    (229, 216, 189),
    (253, 218, 236),
    (242, 242, 242),
]

color_set3 = [
    (166, 206, 227),
    (31, 120, 180),
    (178, 223, 138),
    (51, 160, 44),
    (251, 154, 153),
    (227, 26, 28),
    (253, 191, 111),
    (255, 127, 0),
    (202, 178, 214),
    (106, 61, 154),
    (255, 255, 153),
    (177, 89, 40),
]


class DynamicPlotter:
    def __init__(self, ip, port, sampleinterval=0.1, timewindow=10.0, size=(600, 350)):
        # PyQtGraph stuff
        self._interval = int(sampleinterval * 1000)
        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow()
        self.win.setWindowTitle("Slow signal viewer")
        # data
        self.data = defaultdict(list)  # {'hv_current':list(),'hv_voltage':list()}
        self.time = list()
        self.plts = {}
        self.curve_names = list()
        self.plot_time_window = 10
        self.lastframeindicator = pg.LabelItem(text='')
        self.lastframe = datetime.now()
        self.win.addItem(self.lastframeindicator)
        self.gotdataindicator = pg.LabelItem(text='<font color=\"{}\">{}</font>'.format('green','connected'))
        self.win.addItem(self.gotdataindicator)
        self.counter = 0
        self.win.nextRow()
        # self.win.addItem(pg.TextItem(text='HEJHEJHEJ', color=(200, 200, 200), html=None, anchor=(0, 0), border=None, fill=None, angle=0, rotateAxis=None),row=1 )
        self._add_plot(
            "TMs per readout",
            ("Number of TMs", ""),
            ("Time", "min"),
            ["current nTMs", "av nTMs"],
        )
        self._add_plot(
            "Slow signal amplitude",
            ("Amplitude", "mV"),
            ("Time", "min"),
            ["total amplitude", "max amplitude X 10"],
        )
        self.win.nextRow()
        # self._add_plot('DAC HV Voltage (Super pixels 0-8)',('Voltage','V'),('Time','min'),['dac_suppix_%d'%i for i in range(9)])

        # self._add_plot('DAC HV Voltage (Super pixels 9-15)',('Voltage','V'),('Time','min'),['dac_suppix_%d'%i for i in range(9,16)])

        # self._add_plot('Temperature',('Temperature',u"\u00B0"+'C'),('Time','min'),['temp_powb','temp_auxb','temp_primb'])#,'temp_sipm'
        self.badpixs = np.array(
            [
                25,
                58,
                101,
                304,
                449,
                570,
                653,
                1049,
                1094,
                1158,
                1177,
                1381,
                1427,
                1434,
                1439,
                1765,
                1829,
                1869,
                1945,
                1957,
                2009,
                2043,
            ]
        )
        self.img = pg.ImageItem(levels=(0, 400))
        self.p = self.win.addPlot()
        self.p.addItem(self.img)
        self.c = CameraConfiguration("1.1.0")
        self.m = self.c.GetMapping()

        self.xpix = np.array(self.m.GetXPixVector())
        self.ypix = np.array(self.m.GetYPixVector())
        self.xmap = np.array(self.m.GetRowVector())
        self.ymap = np.array(self.m.GetColumnVector())
        self.map = np.zeros((48, 48), dtype=np.uint64)
        for i in range(2048):
            self.map[self.xmap[i], self.ymap[i]] = i

        self.map = self.map.flatten()
        # label = pg.LabelItem()
        # label2 = pg.TextItem("BLAH")
        # # label2.setText()
        # label.setText("test",color='CCFF00')
        # self.win.addItem(label)
        # self.win.addItem(label2)
        # Add a color scale
        # self.gl = pg.GradientLegend((20, 150), (-10, -10))
        # self.gl.setParentItem(self.img)
        # self.gl.scale(1,-1)
        # self.gl
        # self.colorScale.setLabels('Label')
        # self.p.scene().addItem(self.colorScale)
        # QTimer

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateplots)
        self.timer.start(self._interval)

        self.ss_listener = subscribers.SSReadoutSubscriber(port=port, ip=ip)
        self.ss_listener.start()

        # if(isinstance(ss_calib, np.array)):
        # else:
        # self.ss_calib = np.zeros(64)

    def _add_plot(self, title, labely, labelx, curves):
        self.curve_names += curves
        self.plts[title] = (self.win.addPlot(title=title), curves, list())
        self.plts[title][0].setLabel("left", labely[0], labely[1])
        self.plts[title][0].setLabel("bottom", labelx[0], labelx[1])
        self.plts[title][0].addLegend()
        self.plts[title][0].showGrid(x=True, y=True)
        for i, curve in enumerate(curves):
            t = sum((color_set1[i], (20,)), ())
            self.plts[title][2].append(
                self.plts[title][0].plot(
                    np.linspace(0, 10, 10),
                    np.linspace(0, 10, 10),
                    pen=color_set1[i],
                    fillLevel=0,
                    fillBrush=t,
                    name=curve,
                )
            )
        self.plts[title][0].setXRange(-self.plot_time_window, 0)
        # self.plts[title][2][i].setClickable()

    def get_data(self):
        evs = []
        ntries = 0
        self.lastframeindicator.setText("time since last received frame: {} ".format(datetime.now()-self.lastframe))
        self.counter +=1
        while ntries < 10:
            try:
                ev = self.ss_listener.get_data(timeout=0.1)
                evs.append(ev._get_asic_mapped())
            except:
                ntries += 1
                break
        if len(evs) == 0:
            return
        else:
            data = evs[-1]
        self.gotdata = True
        self.lastframe = datetime.now()
        imgdata = np.zeros((48, 48))
        m = ~np.isnan(data)
        parttms = set(np.where(m)[0])
        nparttms = len(parttms)
        data = data.flatten()
        data[data <= 0] = np.nan

        # data = np.log10(data)
        data[self.badpixs] = np.nan

        # print(data[data>0])
        imgdata[self.xmap, self.ymap] = data

        imgdata[np.isnan(imgdata)] = 0
        self.img.setImage(imgdata.T, levels=(0, 400))

        self.data["total amplitude"].append(np.nansum(data))
        self.data["max amplitude X 10"].append(np.nanmax(data) * 10)
        self.data["current nTMs"].append(nparttms)
        n = np.min([10, len(self.data["current nTMs"])])
        self.data["av nTMs"].append(np.mean(self.data["current nTMs"][-n:]))

        self.time.append(datetime.now())

    def run(self):
        self.app.exec_()

    def _update_plot(self, time, plot):
        for i in range(len(plot[2])):
            plot[2][i].setData(time, self.data[plot[1][i]][::-1], fillLevel=0.5)

    def updateplots(self):
        self.gotdata = False
        self.get_data()

        if self.gotdata:
            stat = ('green','connected')
        else:
            stat = ('red','disconnected')
        self.gotdataindicator.setText('<font color=\"{}\">{}</font>'.format(*stat))

        time = list()
        now = datetime.now()
        for t in self.time:
            time.append((t - now).total_seconds() / 60)
        t = np.array(time)
        if len(t) > 0:
            trange = t[t > t[-1] - self.plot_time_window]
            for k, v in self.plts.items():
                # v[0].setXRange(trange[0], trange[-1])
                self._update_plot(time, v)
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
    if args.sub_ip != "127.0.0.101" and args.sub_port is None:
        args.sub_port = 10025
    else:
        args.sub_port = 9004

    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    plt = DynamicPlotter(ip=args.sub_ip, port=args.sub_port)
    plt.run()


class DynamicTSPlotter:
    def __init__(self, ip, port, sampleinterval=0.1, timewindow=10.0, size=(600, 350)):
        # PyQtGraph stuff
        self._interval = int(sampleinterval * 1000)
        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow(size=size)
        self.win.setWindowTitle("Trigger and timestamp viewer")
        # data
        self.ro_trig = 0  # readout trigger counter
        self.ro_diff = 0  # test
        self.ro_lts = ssdaq.data.TriggerMessage()  # last readout timestamp
        self.ro_cts = ssdaq.data.TriggerMessage()  # current readout timestamp
        self.data = defaultdict(list)  # {'hv_current':list(),'hv_voltage':list()}
        # self.data = list()
        self.time = list()
        self.plts = {}
        self.curve_names = list()
        self.plot_time_window = 10
        # self.win.addItem(pg.TextItem(text='HEJHEJHEJ', color=(200, 200, 200), html=None, anchor=(0, 0), border=None, fill=None, angle=0, rotateAxis=None),row=1 )
        self._add_plot(
            "Readout Trigger", ("Frequency", "Hz"), ("Time", "min"), ["readout trigger"]
        )
        self._add_plot(
            "(fake) Busy Trigger",
            ("Frequency", "Hz"),
            ("Time", "min"),
            ["busy trigger"],
        )
        self.win.nextRow()
        self._add_plot(
            "Detected Errors",
            ("", ""),
            ("Time", "min"),
            ["invalid timestamp", "readout counter error", "readout timestamp smaller"],
        )
        self._add_plot(
            "Detected Errors",
            ("", ""),
            ("Time", "min"),
            ["invalid timestamp", "busy counter error", "busy timestamp smaller"],
        )
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateplots)
        self.timer.start(self._interval)

        self.ts_listener = subscribers.BasicTimestampSubscriber(port=port, ip=ip)
        self.ts_listener.start()

    def add_timestamp(self, ts):
        self.ro_trig += 1
        self.ro_cts = ts
        if not self.isValidTS(self.ro_lts):
            self.ro_lts = ts
        # self.ro_diff = self.ro_cts.event_counter - self.ro_lts.event_counter

    def isValidTS(self, ts):
        if ts.time.HasField("seconds") and ts.time.HasField("pico_seconds"):
            return True
        else:
            return False

    def get_deltat_in_ps(self, ts_last, ts_current):
        tlast = ts_last.time.seconds * 1e12 + ts_last.time.pico_seconds
        tcurr = ts_current.time.seconds * 1e12 + ts_current.time.pico_seconds
        return tcurr - tlast

    def get_frequency_in_Hz(self):
        if not (
            self.ro_trig or self.isValidTS(self.ro_lts) or self.isValidTS(self.ro_cts)
        ):
            return
        delt = self.get_deltat_in_ps(self.ro_lts, self.ro_cts) * 1e-12
        trig = self.ro_trig  # self.ro_diff
        if delt <= 1e-12:
            return
        else:
            self.ro_trig = 0
            self.ro_lts = self.ro_cts
            return trig / delt

    def _add_plot(self, title, labely, labelx, curves):
        self.curve_names += curves
        self.plts[title] = (self.win.addPlot(title=title), curves, list())
        self.plts[title][0].setLabel("left", labely[0], labely[1])
        self.plts[title][0].setLabel("bottom", labelx[0], labelx[1])
        self.plts[title][0].addLegend()
        self.plts[title][0].showGrid(x=True, y=True)
        for i, curve in enumerate(curves):
            t = sum((color_set1[i], (20,)), ())
            self.plts[title][2].append(
                self.plts[title][0].plot(
                    np.linspace(0, 10, 10),
                    np.linspace(0, 10, 10),
                    pen=color_set1[i],
                    fillLevel=0,
                    fillBrush=t,
                    name=curve,
                )
            )
        self.plts[title][0].setXRange(-self.plot_time_window, 0)
        # self.plts[title][2][i].setClickable()

    def get_ts_data(self):
        timestamp_error = 0
        ntries = 0
        while ntries < 10:
            try:
                tmsg = self.ts_listener.get_data(timeout=0.1)
                if tmsg is not None:
                    if not self.isValidTS(tmsg):
                        timestamp_error += 1

                    if tmsg.type == 1:  # readout triggers only
                        self.add_timestamp(tmsg)
                    # print(tmsg.event_counter,'=?',self.ro_trig,'=?',self.ro_diff)
            except:
                ntries += 1
                break

        ro_frequency = self.get_frequency_in_Hz()
        print("freq =", ro_frequency)

        if ro_frequency is not None:
            self.data["readout trigger"].append(
                ro_frequency
            )  # = np.array(readout_freq)
            self.data["busy trigger"].append(ro_frequency)  # = np.array(readout_freq)
            self.time.append(datetime.now())

    def run(self):
        self.app.exec_()

    def _update_plot(self, time, plot):
        for i in range(len(plot[2])):
            plot[2][i].setData(time, self.data[plot[1][i]][::-1], fillLevel=0.5)

    def updateplots(self):
        self.get_ts_data()
        time = list()
        now = datetime.now()
        for t in self.time:
            time.append((t - now).total_seconds() / 60)
        t = np.array(time)
        if len(t) > 0:
            for k, v in self.plts.items():
                self._update_plot(time[::-1], v)
        self.app.processEvents()


def timestampviewer():
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
    if args.sub_ip != "127.0.0.101" and args.sub_port is None:
        args.sub_port = 10025
    else:
        args.sub_port = 9003

    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    plt = DynamicTSPlotter(ip=args.sub_ip, port=args.sub_port)
    plt.run()


class DynamicTRPlotter:
    def __init__(self, ip, port, sampleinterval=0.1, timewindow=10.0, size=(600, 350)):
        # PyQtGraph stuff
        self._interval = int(sampleinterval * 1000)
        self.app = QtGui.QApplication([])
        self.win = pg.GraphicsWindow()
        self.win.setWindowTitle("Triggerpattern viewer")
        # data
        self.data = defaultdict(list)  # {'hv_current':list(),'hv_voltage':list()}
        self.time = list()
        self.plts = {}
        self.curve_names = list()
        self.plot_time_window = 10
        # self.win.addItem(pg.TextItem(text='HEJHEJHEJ', color=(200, 200, 200), html=None, anchor=(0, 0), border=None, fill=None, angle=0, rotateAxis=None),row=1 )

        self._add_plot(
            "Trigger rate",
            ("Rate Hz", ""),
            ("Time", "min"),
            ["Nominal triggers"],  # , "Busy triggers"],
        )
        # self._add_plot(
        #     "Slow signal amplitude",
        #     ("Amplitude", "mV"),
        #     ("Time", "min"),
        #     ["total amplitude", "max amplitude X 10"],
        # )
        self.win.nextRow()
        self.img = pg.ImageItem(levels=(0, 400))
        self.p = self.win.addPlot()
        self.p.addItem(self.img)
        self.c = CameraConfiguration("1.1.0")
        self.m = self.c.GetMapping()
        from CHECLabPy.plotting.camera import CameraImage, CameraImageImshow
        from CHECLabPy.utils.mapping import (
            get_clp_mapping_from_tc_mapping,
            get_superpixel_mapping,
            get_tm_mapping,
        )

        self.sp_mapping = get_superpixel_mapping(
            get_clp_mapping_from_tc_mapping(self.m)
        )

        self.xpix = np.array(self.sp_mapping.xpix)
        self.ypix = np.array(self.sp_mapping.ypix)
        self.xmap = np.array(self.sp_mapping.row)
        self.ymap = np.array(self.sp_mapping.col)
        print(self.xmap.shape, self.ymap.shape)
        self.map = np.zeros((24, 24), dtype=np.uint64)
        for i in range(512):
            self.map[self.xmap[i], self.ymap[i]] = i

        self.map = self.map.flatten()
        from ssdaq.data._dataimpl.trigger_format import (
            get_SP2bptrigg_mapping,
            get_bptrigg2SP_mapping,
        )

        self.bptmap = get_bptrigg2SP_mapping()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateplots)
        self.timer.start(self._interval)

        self.tr_listener = subscribers.BasicTriggerSubscriber(port=port, ip=ip)
        self.tr_listener.start()

        # if(isinstance(ss_calib, np.array)):
        # else:
        # self.ss_calib = np.zeros(64)

    def _add_plot(self, title, labely, labelx, curves):
        self.curve_names += curves
        self.plts[title] = (self.win.addPlot(title=title), curves, list())
        self.plts[title][0].setLabel("left", labely[0], labely[1])
        self.plts[title][0].setLabel("bottom", labelx[0], labelx[1])
        self.plts[title][0].addLegend()
        self.plts[title][0].showGrid(x=True, y=True)
        for i, curve in enumerate(curves):
            t = sum((color_set1[i], (20,)), ())
            self.plts[title][2].append(
                self.plts[title][0].plot(
                    np.linspace(0, 10, 10),
                    np.linspace(0, 10, 10),
                    pen=color_set1[i],
                    fillLevel=0,
                    fillBrush=t,
                    name=curve,
                )
            )
        self.plts[title][0].setXRange(-self.plot_time_window, 0)
        # self.plts[title][2][i].setClickable()

    def get_data(self):
        evs = []
        ntries = 0
        while ntries < 10:
            try:
                ev = self.tr_listener.get_data(timeout=0.1)
                evs.append(ev)
            except:
                ntries += 1
                break
        if len(evs) == 0:
            return
        else:
            trigg = evs[-1]
        imgdata = np.zeros((48, 48))

        imgdata[self.xmap, self.ymap] = trigg.trigg_union[self.bptmap]

        imgdata[np.isnan(imgdata)] = 0
        self.img.setImage(imgdata.T, levels=(0, 1))
        trig0 = evs[0]
        self.data["Nominal triggers"].append(
            len(evs) / ((trigg.TACK - trig0.TACK) * 1e-9)
        )
        # self.data["max amplitude X 10"].append(np.nanmax(data) * 10)
        # self.data["current nTMs"].append(nparttms)
        # n = np.min([10, len(self.data["current nTMs"])])
        # self.data["av nTMs"].append(np.mean(self.data["current nTMs"][-n:]))

        self.time.append(datetime.now())

    def run(self):
        self.app.exec_()

    def _update_plot(self, time, plot):
        for i in range(len(plot[2])):
            plot[2][i].setData(time, self.data[plot[1][i]][::-1], fillLevel=0.5)

    def updateplots(self):
        self.get_data()
        time = list()
        now = datetime.now()
        for t in self.time:
            time.append((t - now).total_seconds() / 60)
        t = np.array(time)
        if len(t) > 0:
            trange = t[t > t[-1] - self.plot_time_window]
            for k, v in self.plts.items():
                # v[0].setXRange(trange[0], trange[-1])
                self._update_plot(time, v)
        self.app.processEvents()


def triggerpatternviewer():
    import argparse
    from ssdaq.utils import common_args as cargs

    parser = argparse.ArgumentParser(
        description="A trigger pattern viewer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cargs.subport(parser, default=None)
    cargs.subaddr(parser)
    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    if args.sub_ip != "127.0.0.101" and args.sub_port is None:
        args.sub_port = 10026
    else:
        args.sub_port = 9004

    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    plt = DynamicTRPlotter(ip=args.sub_ip, port=args.sub_port)
    plt.run()


if __name__ == "__main__":
    slowsignalviewer()
    timestampviewer()
