#!/usr/bin/env python
# -*- coding: utf-8 -*-
# mpl.use('WXAgg')
from wx.lib.statbmp import *
from datetime import datetime as dt
from collections import defaultdict
import datetime
import time
import urllib2
from pandas_datareader import data, wb
import numpy as np
from numpy import arange, sin, pi
import math
import tempfile
import matplotlib as mpl
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import wx
from wx.lib.agw import ultimatelistctrl as ULC
import wx.lib.mixins.listctrl as listmix
import sqlite3 as sq3

print(plt.__file__)

class GaugeSplash(wx.Frame):
    def __init__(self, bmp, timeout=5000):
        wx.Frame.__init__(self, None, style=wx.FRAME_NO_TASKBAR)
        self.border = 2
        self.SetBackgroundColour(wx.WHITE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.bmp = GenStaticBitmap(self, -1, bmp)
        sizer.Add(self.bmp, 0, wx.EXPAND)
        self.label = wx.StaticText(self, -1, "Loading...")
        self.label.SetBackgroundColour(wx.WHITE)
        sizer.Add(self.label, 0, flag=wx.EXPAND | wx.ALL, border=self.border)
        self.progressHeight = 12
        self.gauge = wx.Gauge(self, -1,
              range=100, size=(-1, self.progressHeight),
              style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.gauge.SetBackgroundColour(wx.WHITE)
        self.gauge.SetForegroundColour(wx.RED)
        sizer.Add(self.gauge, 0, flag=wx.EXPAND | wx.ALL, border=self.border)
        self.CenterOnScreen()
        self.timeout = timeout
        self._splashtimer = wx.PyTimer(self.OnNotify)
        self._splashtimer.Start(self.timeout)
        self.count = 0
        self.visible = True
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.bmp.Layout()
        self.label.Layout()
        self.gauge.Layout()
        self.Layout()
        self.Update()
        wx.Yield()

    def OnNotify(self):
        if not self:
            return
        if self.count < self.gauge.GetRange():
            self._splashtimer.Start(self.timeout/10)
        else:
            self.Close()

    def setTicks(self, count):
        self.gauge.SetRange(count)

    def tick(self, text):
        self.count += 1
        self.label.SetLabel(text)
        self.gauge.SetValue(self.count)
        self.gauge.Update()
        wx.Yield()


'''
    AVERAGES FORMULAS
'''
def moving_average(values, window):
    ma_list = []
    for i, _ in enumerate(values):
        if i == 0:
            ma_list.append(values[i])
        if i > 1 and i < window:
            val = (sum(ma_list) + values[i]) / (len(ma_list) + 1.)
            ma_list.append(val)
    weights = np.repeat(1.0, window) / window
    movingAverage = np.convolve(values, weights, 'valid')
    ma_list.extend(movingAverage.tolist())
    return ma_list

def moving_average_convergence_divergence(values, nslow=26, nfast=12):
    # compute the MACD (Moving Average Convergence/Divergence) using a fast and slow exponential moving avg'
    # return value is emaslow, emafast, macd which are len(x) arrays
    emaslow = moving_average(values, nslow)
    emafast = moving_average(values, nfast)
    return emaslow, emafast, emafast - emaslow

'''
    DATA SOURCES
'''
def GoogleFinanceData(symbol, interval_seconds=60, num_days=1):
    timeStamp = []
    open_ = []
    high = []
    low = []
    close = []
    volume = []
    day = 0
    url_string = "http://www.google.com/finance/getprices?q=%s" % (symbol)
    url_string += "&i=%i&p=%id&f=d,o,h,l,c,v" % (interval_seconds, num_days)
    stockData = urllib2.urlopen(url_string).read()
    for eachLine in stockData.split('\n'):
        splitLine = eachLine.split(',')
        if len(splitLine) == 6 and 'CLOSE' not in splitLine:
            ts, c, h, l, o, v = splitLine
            a_test = list(ts)
            if 'a' not in a_test:
                timeStamp.append(dt.fromtimestamp(day + (interval_seconds * int(''.join(ts)))))
                close.append(float(c))
                high.append(float(h))
                low.append(float(l))
                open_.append(float(o))
                volume.append(int(v))
            else:
                buffler = ''.join(a_test[1:])
                day = float(buffler)
    return timeStamp, close, open_, volume

def YahooFinanceData(symbol, index='yahoo'):
    timeStamp = []
    open_ = []
    high = []
    low = []
    close = []
    volume = []
    adjclose = []
    symbol = symbol.upper()
    dt_end = dt.fromtimestamp(time.time())
    dt_start = dt_end - datetime.timedelta(days=365)
    stock_data = data.DataReader(symbol, index, dt_start, dt_end)
    for i, _ in enumerate(stock_data.index):
        timeStamp.append(stock_data.index[i])
        open_.append(stock_data['Open'][i])
        high.append(stock_data['High'][i])
        low.append(stock_data['Low'][i])
        close.append(stock_data['Close'][i])
        volume.append(stock_data['Volume'][i])
        adjclose.append(stock_data['Adj Close'][i])
    return timeStamp, open_, high, low, close, volume, adjclose


def yahooFundumentals(symbol):
    symbol.upper()
    yahoofund = urllib2.urlopen('http://finance.yahoo.com/quote/%s' % symbol).read()
    marketcap_b = yahoofund.split('$key-stats-0.0.0.$0MARKET_CAP.1">')[1].split('</td>')[0]
    pe_ratio = yahoofund.split('$key-stats-0.0.0.$1PE_RATIO.1">')[1].split('</td>')[0]
    return marketcap_b, pe_ratio

def B_to_billions(value):
    buffer= value.split("B")[0] # Remove the 'B'
    num = float(buffer) * 1000000000. # Convert ###.## into billions
    return num

def k_or_m(num_str):
    korm, interval = '', ''
    if num_str > 1000 and num_str <= 1000000:
        korm = 'K'
        interval = num_str / 1000
    if num_str > 1000000:
        korm = 'M'
        interval = num_str / 1000000
    if num_str <= 1000:
        korm = ''
        interval = num_str
    return korm, interval



'''
    GUI
'''

class Quant(wx.Frame):
    def __init__(self, parent, title):
        super(Quant, self).__init__(parent, title=title, size=(300, 250))

        BMP = wx.Image("bull_n_bear1.jpg").ConvertToBitmap()
        dc = wx.MemoryDC()
        dc.SelectObject(BMP)
        self.splash = GaugeSplash(BMP)
        self.splash.CenterOnScreen()
        self.splash.Show()
        wx.Yield()
        self.loc = wx.IconLocation('program_icon.ico',0)
        self.SetIcon(wx.IconFromLocation(self.loc))
        self.InitUI()
        self.anim = animation.FuncAnimation(self.figure1, self.animate, interval=60003)    # Intervals: 10min
        self.CenterOnScreen()
        self.Fit()
        self.SQL()
        self.Show()


    def show_splash(self):
        bitmap = wx.Image("bull_n_bear1.jpg").ConvertToBitmap()

        splash = wx.SplashScreen(bitmap, wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_NO_TIMEOUT, 0, None, -1,
                                 wx.DefaultPosition, wx.DefaultSize, wx.BORDER_NONE)
        splash.Show()
        wx.Yield()
        return splash

    def SQL(self):
        conn = sq3.connect('db.db')
        c = conn.cursor()

        idfordb = 4
        keyword = 'Python Sentiment'
        value = 7
        sql = "SELECT * FROM stuffToPlot WHERE keyword = ?"
        wordUsed = 'Python Sentiment'

        def tableCreate():
            c.execute("CREATE TABLE stuffToPlot(ID INT, unix REAL, "
                      "datestamp TEXT, keyword TEXT, value REAL)")

        def dataEntry():
            date = str(dt.fromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S'))
            c.execute("INSERT INTO stuffToPlot (ID, unix, datestamp, keyword, value) VALUES (?,?,?,?,?)",
                      (idfordb, time.time(), date, keyword, value))
            conn.commit()   # Save it into the file

        def readData():
            for row in c.execute(sql, [(wordUsed)]):
                print dt.fromtimestamp(row[1]).strftime('%b %Y').replace('6','7')

        #readData()
        # con.execute(query)
        # con.commit()
        # for num in range(stock_data['Close']):
        #     con.execute('INSERT INTO data VALUES(?, ?, ?, ?, ?)',
        #                 (stock_data['Open'][num], stock_data['High'][num],
        #                  stock_data['Low'][num], stock_data['Close'][num], stock_data['Volume'][num]))
        # con.commit()
        # pointer = con.execute('SELECT * FROM data')
        # for i in stock_data:
        #     print pointer.fetchone()

    def InitUI(self):

        self.no_rept_count = 0
        self.tickerlookup = {
            'AAL' : 'American Airlines Group, Inc.',
            'AAPL': 'Apple',
            'ADBE': 'Adobe Systems Incorporated',
            'ADI' : 'Analog Devices, Inc. ',
            'ADP' : 'Automatic Data Processing, Inc.',
            'ADSK': 'Autodesk, Inc.',
            'AKAM': 'Akamai Technologies',
            'ALXN': 'Alexion Pharmaceuticals, Inc.',
            'AMAT': 'Applied Materials, Inc.',
            'AMGN': 'Amgen Inc.',
            'AMZN': 'Amazon.com',
            'ATVI': 'Activision Blizzard, Inc.',
            'AVGO': 'Broadcom Limited',
            'BBBY': 'Bed Bath & Beyond Inc.',
            'BIDU': 'Baidu, Inc.',
            'BIIB': 'Biogen, Inc.',
            'BLDP': 'Ballard Power',
            'BMRN': 'BioMarin Pharmaceutical, Inc.',
            'CA'  : 'CA, Inc.',
            'CELG': 'Celgene Corporation',
            'CERN': 'Cerner Corporation',
            'CHKP': 'Check Point Software Technologies, Ltd.',
            'CHTR': 'Charter Communications, Inc.',
            'CMCSA': 'Comcast Corporation',
            'COST': 'Costco Wholesale Corporation',
            'CSCO': 'Cisco Systems, Inc.',
            'CSX' : 'CSX Corporation',
            'CTRP': 'Ctrip.com International, Ltd.',
            'CTSH': 'Cognizant Technology Solutions Corporation',
            'CTXS': 'Citrix Systems, Inc.',
            'DISCA': 'Discovery Communications, Inc.',
            'DISCK': 'Discovery Communications, Inc.',
            'DISH': 'Dish Network Corporation',
            'DLTR': 'Dollar Tree, Inc.',
            'EA'  : 'Electronic Arts, Inc.',
            'EBAY': 'Ebay Inc',
            'ESRX': 'Express Scrips Holding Company',
            'EXPE': 'Expedia, Inc.',
            'FAST': 'Fastenal Company',
            'FB'  : 'Facebook',
            'FISV': 'Fiserv, Inc.',
            'FOX' : 'Twenty-First Century Fox, Inc.',
            'FOXA': 'Twenty-First Century Fox, Inc.',
            'GILD': 'Gilead Sciences, Inc.',
            'GOOG': 'Google',
            'HSIC': 'Henry Schein, Inc.',
            'ILMN': 'Illumina, Inc.',
            'INCY': 'Incyte Corporation',
            'INTC': 'Intel Corporation',
            'INTU': 'Intuit, Inc.',
            'ISRG': 'Intuitive Surgical, Inc.',
            'JD'  : 'JD.com, Inc.',
            'KHC' : 'The Kraft Heinz Company',
            'LBTYA': 'Liberty Global plc',
            'LBTYK': 'Liberty Global plc',
            'LLTC': 'Linear Technology Corporation',
            'LRCX': 'Lam Research Corporation',
            'LVNTA': 'Liberty Interactive Corporation',
            'MAR' : 'Marriot International',
            'MAT' : 'Mattel, Inc.',
            'MCHP': 'Microchip Technology Incorporated',
            'MDLZ': 'Mondelez Interational',
            'MNST': 'Monster Beverage Corporation',
            'MRVL': 'Marval',
            'MSFT': 'Microsoft',
            'MU'  : 'Micron Technology',
            'MXIM': 'Maxim Integrated Products, Inc.',
            'MYL' : 'Mylan N.V.',
            'NCLH': 'Norwegian Cruise Line Holdings Ltd.',
            'NFLX': 'Netflix',
            'NTAP': 'NetApp, Inc.',
            'NTES': 'NetEase, Inc',
            'NVDA': 'Nvidia',
            'NXPI': 'NXP Semiconductors N.V.',
            'ORLY': 'O\'Reilly Automotive, Inc.',
            'PAYX': 'Paychex, Inc.',
            'PCAR': 'PACCAR, Inc.',
            'PCLN': 'The Priceline Group, Inc.',
            'PYPL': 'PayPal Holdings, Inc.',
            'QCOM': 'QUALCOMM Incorporated',
            'QVCA': 'Liverty Interactive Corporation',
            'REGN': 'Regeneron Pharmaceuticals, Inc.',
            'ROST': 'Ross Stores, Inc.',
            'SBAC': 'SBA Communications Corporation',
            'PLUG': 'Plug Power',
            'SNE' : 'Sony',
            'SBUX': 'Starbucks',
            'SIRI': 'Serius XM Holdings Inc.',
            'SRCL': 'Stericycle, Inc.',
            'STX' : 'Seagate Technology PLC',
            'SWKS': 'Skyworks Solutions, Inc.',
            'SYMC': 'Symantec Corporation',
            'TMUS': 'T-Mobile US, Inc.',
            'TRIP': 'TripAdvisor, Inc',
            'TSCO': 'Tractor Supply Company',
            'TSLA': 'Tesla Motors, Inc.',
            'TXN' : 'Texas Instruments Incorporated',
            'ULTA': 'Ulta Salon, Cosmetics & Fragrance, Inc.',
            'VIAB': 'Biacom Inc.',
            'VOD' : 'Vodafone Group Plc',
            'VRSK': 'Verisk Analytics, Inc.',
            'VRTX': 'Vertex Pharmaceuticals Incorporated',
            'WBA' : 'Wallgreens Boots Alliance, Inc.',
            'WDC' : 'Western Digital Corporation',
            'WFM' : 'Whole Foods Market, Inc.',
            'XLNX': 'Xilinx, Inc.',
            'XRAY': 'DENTSPLY SIRONA, Inc.',
            'YHOO': 'Yahoo! Inc.'
        }



        self.panel = wx.Panel(self)
        sizer = wx.GridBagSizer(0, 0)
        tl_sizer = wx.GridBagSizer(0, 0)
        tc_sizer = wx.GridBagSizer(0, 0)
        tr_sizer = wx.GridBagSizer(0, 0)
        # ml_sizer = wx.GridBagSizer(0, 0)
        # mc_sizer = wx.GridBagSizer(0, 0)
        # mr_sizer = wx.GridBagSizer(0, 0)

        bl_sizer = wx.GridBagSizer(0, 0)
        bc_sizer = wx.GridBagSizer(0, 0)
        br_sizer = wx.GridBagSizer(0, 0)
        fl_sizer = wx.GridBagSizer(0, 0)
        fc_sizer = wx.GridBagSizer(0, 0)
        fr_sizer = wx.GridBagSizer(0, 0)
        box1 = wx.GridBagSizer(0, 0)
        box2 = wx.GridBagSizer(0, 0)
        box3 = wx.BoxSizer(wx.HORIZONTAL)
        br_stockbox = wx.BoxSizer(wx.HORIZONTAL)



        '''
            BOXs
        '''
        box_for_box1 = wx.BoxSizer(wx.HORIZONTAL)
        plt1_text = wx.StaticText(self.panel, label='Company: ')
        box_for_box1.Add(plt1_text, flag=wx.ALIGN_CENTRE_HORIZONTAL, border=5)
        self.plt1_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.plt1_tc.Bind(wx.EVT_TEXT_ENTER, self.plt1_getCompany)
        box_for_box1.Add(self.plt1_tc, flag=wx.ALIGN_CENTRE_HORIZONTAL, border=5)
        box1.Add(box_for_box1, pos=(0, 0), flag=wx.EXPAND | wx.ALL | wx.ALIGN_LEFT, border=5)
        # plt1_text = wx.StaticText(self.panel, label='Input1: ')
        # box1.Add(plt1_text, pos=(0, 2), flag=wx.ALL | wx.ALIGN_CENTRE, border=5)
        # self.plt1_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        # self.plt1_tc.Bind(wx.EVT_TEXT_ENTER, self.plt1_getCompany)
        # box1.Add(self.plt1_tc, pos=(0, 3), flag=wx.EXPAND | wx.ALL, border=5)
        #
        # plt1_text = wx.StaticText(self.panel, label='Input2: ')
        # box1.Add(plt1_text, pos=(0, 4), flag=wx.ALL | wx.ALIGN_CENTRE, border=5)
        # self.plt1_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        # self.plt1_tc.Bind(wx.EVT_TEXT_ENTER, self.plt1_getCompany)
        # box1.Add(self.plt1_tc, pos=(0, 5), flag=wx.EXPAND | wx.ALL, border=5)
        #
        # plt1_text = wx.StaticText(self.panel, label='Input3: ')
        # box1.Add(plt1_text, pos=(0, 6), flag=wx.ALL | wx.ALIGN_CENTRE, border=5)
        # self.plt1_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        # self.plt1_tc.Bind(wx.EVT_TEXT_ENTER, self.plt1_getCompany)
        # box1.Add(self.plt1_tc, pos=(0, 7), flag=wx.EXPAND | wx.ALL, border=5)






        box_for_box2 = wx.BoxSizer(wx.HORIZONTAL)
        plt2_text = wx.StaticText(self.panel, label='Company: ')
        box_for_box2.Add(plt2_text, flag=wx.ALIGN_CENTRE_HORIZONTAL, border=5)
        self.plt2_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.plt2_tc.Bind(wx.EVT_TEXT_ENTER, self.plt2_getCompany)
        box_for_box2.Add(self.plt2_tc, flag=wx.ALIGN_CENTRE_HORIZONTAL, border=5)
        box2.Add(box_for_box2, pos=(0, 0), flag=wx.EXPAND | wx.ALL | wx.ALIGN_LEFT, border=5)

        # plt2_text = wx.StaticText(self.panel, label='Input1: ')
        # box2.Add(plt2_text, pos=(0, 2), flag=wx.ALL | wx.ALIGN_CENTRE, border=5)
        # self.plt2_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        # self.plt2_tc.Bind(wx.EVT_TEXT_ENTER, self.plt2_getCompany)
        # box2.Add(self.plt2_tc, pos=(0, 3), flag=wx.EXPAND | wx.ALL, border=5)
        #
        # plt2_text = wx.StaticText(self.panel, label='Input2: ')
        # box2.Add(plt2_text, pos=(0, 4), flag=wx.ALL | wx.ALIGN_CENTRE, border=5)
        # self.plt2_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        # self.plt2_tc.Bind(wx.EVT_TEXT_ENTER, self.plt2_getCompany)
        # box2.Add(self.plt2_tc, pos=(0, 5), flag=wx.EXPAND | wx.ALL, border=5)
        #
        # plt2_text = wx.StaticText(self.panel, label='Input3: ')
        # box2.Add(plt2_text, pos=(0, 6), flag=wx.ALL | wx.ALIGN_CENTRE, border=5)
        # self.plt2_tc = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        # self.plt2_tc.Bind(wx.EVT_TEXT_ENTER, self.plt2_getCompany)
        # box2.Add(self.plt2_tc, pos=(0, 7), flag=wx.EXPAND | wx.ALL, border=5)



        '''
            List BOX
        '''
        self.choice = wx.Choice(self.panel, choices=sorted(self.tickerlookup.values()))
        box3.Add(self.choice, 1, wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=3)
        tr_sizer.Add(box3, pos=(0, 0), flag=wx.ALIGN_CENTRE_HORIZONTAL)


        '''
            MATPLOTLIB
        '''

        self.figure1 = plt.figure(figsize=(8, 5))
        self.figure2 = plt.figure(figsize=(8, 3))
        self.figure3 = plt.figure(figsize=(8, 5))
        self.figure4 = plt.figure(figsize=(8, 3))
        self.plt1_1 = self.figure1.add_subplot(1, 1, 1)
        self.plt1_2 = self.figure2.add_subplot(1, 1, 1)
        self.plt2_1 = self.figure3.add_subplot(1, 1, 1)
        self.plt2_2 = self.figure4.add_subplot(1, 1, 1)
        self.canvas1 = FigureCanvas(self, -1, self.figure1)
        self.canvas2 = FigureCanvas(self, -1, self.figure2)
        self.canvas3 = FigureCanvas(self, -1, self.figure3)
        self.canvas4 = FigureCanvas(self, -1, self.figure4)
        bc_sizer.Add(self.canvas1, pos=(0, 0))
        bc_sizer.Add(self.canvas2, pos=(1, 0))
        bl_sizer.Add(self.canvas3, pos=(0, 0))
        bl_sizer.Add(self.canvas4, pos=(1, 0))
        self.plt1_1_plot('BLDP', 'Ballard Power')
        self.plt1_2_plot('BLDP', 'Ballard Power')
        self.plt2_1_plot('BLDP', 'Ballard Power')
        self.plt2_2_plot('BLDP', 'Ballard Power')
        self.figure1.set_facecolor('#f0f0f0')
        self.figure2.set_facecolor('#f0f0f0')
        self.figure3.set_facecolor('#f0f0f0')
        self.figure4.set_facecolor('#f0f0f0')
        self.figure1.autofmt_xdate()
        self.figure2.autofmt_xdate()
        self.figure3.autofmt_xdate()
        self.figure4.autofmt_xdate()

        '''
            CHECKBOXES
        '''
        self.cb1 = wx.CheckBox(self.panel, label='Moving Average', style=wx.CHK_2STATE)
        self.cb2 = wx.CheckBox(self.panel, label='MACD', style=wx.CHK_2STATE)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.cb1)
        hbox.Add(self.cb2)
        self.Bind(wx.EVT_CHECKBOX, self.checkMovingAverage, self.cb1)
        self.Bind(wx.EVT_CHECKBOX, self.checkMACD, self.cb2)
        fl_sizer.Add(hbox, pos=(0, 0), flag=wx.EXPAND | wx.GROW)

        '''
            STOCK LIST CONTROL
        '''
        self.ultiStockList = ULC.UltimateListCtrl(self.panel, -1, size=(575,650),
                                                  agwStyle=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES |
                                                           ULC.ULC_SHOW_TOOLTIPS | ULC.ULC_HOT_TRACKING|
                                                           ULC.ULC_SORT_ASCENDING)
        br_stockbox.Add(self.ultiStockList)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnColClick)
        br_sizer.Add(br_stockbox, pos=(0, 0))
        self.ultiSLmethod()


        self.tick1_txt = wx.StaticText(self.panel, label='Loading...')
        self.tick2_txt = wx.StaticText(self.panel, label='Loading...')
        tick1_font = wx.Font(28, wx.ROMAN, wx.NORMAL, wx.BOLD)
        tick2_font = wx.Font(28, wx.ROMAN, wx.NORMAL, wx.BOLD)
        self.tick1_txt.SetFont(tick1_font)
        self.tick2_txt.SetFont(tick2_font)
        box1.Add(self.tick1_txt, pos=(1, 0), flag=wx.EXPAND | wx.ALL, border=3)
        box2.Add(self.tick2_txt, pos=(1, 0), flag=wx.EXPAND | wx.ALL, border=3)
        tc_sizer.Add(box1, pos=(0, 0), flag=wx.ALL)
        tl_sizer.Add(box2, pos=(0, 0), flag=wx.ALL)
        '''
            FIGURES
        '''
        sizer.Add(tl_sizer, pos=(0, 0))
        sizer.Add(tc_sizer, pos=(0, 1))
        sizer.Add(tr_sizer, pos=(0, 2))
        sizer.Add(bl_sizer, pos=(1, 0))
        sizer.Add(bc_sizer, pos=(1, 1))
        sizer.Add(br_sizer, pos=(1, 2))
        sizer.Add(fl_sizer, pos=(2, 0))
        sizer.Add(fc_sizer, pos=(2, 1))
        sizer.Add(fr_sizer, pos=(2, 2))
        self.panel.SetSizerAndFit(sizer)

    '''
        INFORMATION
    '''


    '''
        CHARTS
    '''
    def plt1_1_plot(self, tickerSymbol, companyName):
        gtimestamp, \
        gclose, \
        gopen_, \
        _ = GoogleFinanceData(tickerSymbol, interval_seconds=60)
        ma_close = moving_average(gclose, 30)
        self.plt1_1.plot(gtimestamp, gclose, color='#404040', linewidth=2, label=tickerSymbol)
        self.plt1_1.plot(gtimestamp, ma_close, color='m', label='30min MA')
        self.plt1_1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M%p'))
        self.plt1_1.set_title(companyName, fontsize=20)
        self.plt1_1.grid(True)
        spines = ['left', 'right', 'top', 'bottom']
        for spine in spines:
            self.plt1_1.spines[spine].set_color('none')
        self.plt1_1.set_axis_bgcolor('#f0f0f0')
        self.plt1_1.set_ylabel('Close Price ($US)')
        self.plt1_1.legend(loc='best', frameon=False)
        self.plt1_1.yaxis.set_major_formatter(ticker.FormatStrFormatter('$%1.2f'))
        self.plt1_1.xaxis.label1On = True
        gcl = gclose[-1]
        gts = gtimestamp[-1]
        bbox_color = 'w'
        buffcolor = gclose[-2] - gcl
        if buffcolor > 0:
            bbox_color = '#0be600'
        if buffcolor < 0:
            bbox_color = '#ff3d3d'
        bbox_props = dict(boxstyle='round', fc=bbox_color, ec='k', lw=1)
        closep = '$%1.2f' % gcl
        self.plt1_1.annotate(str(closep), (gts, gcl),
                             xytext=(gts + datetime.timedelta(minutes=4),
                                     gcl), bbox=bbox_props)


    def plt1_2_plot(self, tickerSymbol, companyName):
        gtimestamp, \
        _, \
        _, \
        gvolume = GoogleFinanceData(tickerSymbol, interval_seconds=60)
        gvolume = np.asarray(gvolume)
        korm = ''
        interval = ''
        max_gv = max(gvolume)
        if max_gv >= 1000 and max_gv <= 1000000:
            korm = 'K'
            interval = '(thousands)'
            gvolume = gvolume / 1000
        if max_gv > 1000000:
            korm = 'M'
            interval = '(millions)'
            gvolume = gvolume / 1000000
        self.plt1_2.plot(gtimestamp, gvolume, color='b', label='Volume')
        self.plt1_2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M%p'))
        self.plt1_2.fill_between(gtimestamp, 0, gvolume, facecolor='b', alpha=0.4)
        self.plt1_2.set_title(companyName)
        self.plt1_2.title.set_visible(False)
        self.plt1_2.grid(True)
        spines = ['left', 'right', 'top', 'bottom']
        for spine in spines:
            self.plt1_2.spines[spine].set_color('none')
        self.plt1_2.set_axis_bgcolor('#f0f0f0')
        self.plt1_2.set_ylabel('Volume %s' % interval)
        self.plt1_2.legend(loc='best', frameon=False)
        formatter = ticker.FormatStrFormatter('%i'+korm)
        self.plt1_2.yaxis.set_major_formatter(formatter)
        self.plt1_2.xaxis.label1On = True


            # Specify the color using an html hex string

    def plt1_1update(self):
        plot_title = self.plt1_1.get_title().split('\'')
        self.plt1_1.clear()
        self.plt1_1_plot(self.tickerlookup.keys()[self.tickerlookup.values().index(plot_title[0])], plot_title[0])
        self.plt1_1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M%p'))
        self.figure1.canvas.draw()

    def plt1_2update(self):
        plot_title = self.plt1_2.get_title().split('\'')
        self.plt1_2.clear()
        self.plt1_2_plot(self.tickerlookup.keys()[self.tickerlookup.values().index(plot_title[0])], plot_title[0])
        self.plt1_2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M%p'))
        self.plt1_2.title.set_visible(False)
        self.figure2.canvas.draw()

    def plt2_1_plot(self, tickerSymbol, companyName):
        ytimeStamp, \
        yopen_, \
        _, \
        _, \
        yclose, \
        _, \
        _ = YahooFinanceData(tickerSymbol)
        ma_close = moving_average(yclose, 30)
        self.plt2_1.plot(ytimeStamp, yclose, color='#404040', linewidth=2, label=tickerSymbol)
        self.plt2_1.plot(ytimeStamp, ma_close, color='m', label='30day MA')
        self.plt2_2.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
        self.plt2_1.set_title(companyName, fontsize=20)
        self.plt2_1.grid(True)
        spines = ['left', 'right', 'top', 'bottom']
        for spine in spines:
            self.plt2_1.spines[spine].set_color('none')
        self.plt2_1.set_axis_bgcolor('#f0f0f0')
        self.plt2_1.set_ylabel('Close Price ($US)')
        self.plt2_1.legend(loc='best', frameon=False)
        formatter = ticker.FormatStrFormatter('$%1.2f')
        self.plt2_1.yaxis.set_major_formatter(formatter)
        self.plt2_1.label1On = True
        bbox_color = 'w'
        ycl = yclose[-1]
        yts = ytimeStamp[-1]
        buffcolor = yclose[-2] - ycl
        if buffcolor > 0:
            bbox_color = '#0be600'
        if buffcolor < 0:
            bbox_color = '#ff3d3d'
        bbox_props = dict(boxstyle='round', fc=bbox_color, ec='k', lw=1)
        closep = '$%1.2f' % ycl
        self.plt2_1.annotate(str(closep), (yts, ycl),
                                 xytext=(yts + datetime.timedelta(days=4),
                                         ycl), bbox=bbox_props)

    def plt2_2_plot(self, tickerSymbol, companyName, line_color='r', line_marker=''):
        ytimeStamp, \
        _, \
        _, \
        _, \
        _, \
        yvolume, \
        _ = YahooFinanceData(tickerSymbol)
        yvolume = np.asarray(yvolume)
        korm = ''
        interval = ''
        yv_max = max(yvolume)
        if yv_max > 1000 and yv_max <= 1000000:
            korm = 'K'
            interval = '(thousands)'
            yvolume = yvolume / 1000
        if yv_max > 1000000:
            korm = 'M'
            interval = '(millions)'
            yvolume = yvolume / 1000000
        self.plt2_2.plot(ytimeStamp, yvolume, color='b', label='Volume')
        self.plt2_2.fill_between(ytimeStamp, 0, yvolume, facecolor='b', alpha=0.4)
        self.plt2_2.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
        self.plt2_2.set_title(companyName)
        self.plt2_2.title.set_visible(False)
        self.plt2_2.grid(True)
        spines = ['left', 'right', 'top', 'bottom']
        for spine in spines:
            self.plt2_2.spines[spine].set_color('none')
        self.plt2_2.set_axis_bgcolor('#f0f0f0')
        self.plt2_2.set_ylabel('Volume %s' % interval)
        self.plt2_2.legend(loc='best',frameon=False)
        formatter = ticker.FormatStrFormatter('%i'+korm)
        self.plt2_2.yaxis.set_major_formatter(formatter)
        self.plt2_2.xaxis.label1On = True

    def plt2_1update(self):
        self.plt2_1.clear()
        self.plt2_1_plot(self.tickerlookup.keys()[self.tickerlookup.values().index(self.plt2_2.get_title())], self.plt2_1.get_title())
        self.plt2_1.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M%p'))
        self.figure3.autofmt_xdate()
        self.figure3.canvas.draw()

    def plt2_2update(self):
        self.plt2_2.clear()
        self.plt2_2_plot(self.tickerlookup.keys()[self.tickerlookup.values().index(self.plt2_2.get_title())], self.plt2_1.get_title())
        self.plt2_2.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M%p'))
        self.plt2_2.title.set_visible(False)
        self.figure4.autofmt_xdate()
        self.figure4.canvas.draw()


    '''
        LEFT PANEL
    '''

    def ultiSLmethod(self):
        if self.no_rept_count == 0:
            self.splash.setTicks(len(self.tickerlookup))
        lblList = ['Company', 'Ticker', 'Last', 'P_Chng', '%Chng', 'Volume']
        fontMask = ULC.ULC_MASK_FONTCOLOUR | ULC.ULC_MASK_FONT
        font = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
        drcount = 0
        slc = {}
        dict_len = len(self.tickerlookup)
        for ticker, company in self.tickerlookup.items():
            _, \
            gclose, \
            gopen_, \
            gvolume = GoogleFinanceData(ticker, interval_seconds=60)
            if (len(gclose) == 0):
                continue
            ticlist = ()
            for_close = gclose[-1]
            for_open = gopen_[0]
            for_volume = gvolume[-1]
            ticlist += (company,
                        ticker,
                        '$%1.2f' % for_close,
                        '$%1.2f' % (for_close - for_open),
                        '%1.2f%%' % ((for_close - for_open) / float(for_open)),)
            korm, gvol = k_or_m(for_volume)
            ticlist += ('%i%s' % (gvol, korm),)
            slc.setdefault(drcount, ticlist)
            j = float(drcount / dict_len)
            if self.no_rept_count == 0:
                self.splash.tick("Loading... %d%%" % ((drcount / 107.0)*100))
            drcount += 1
        self.lizt = Sorting_List(self.ultiStockList, slc)
        [self.lizt.InsertColumn(i, lbl) for i, lbl in enumerate(lblList)]
        self.lizt.SetColumnWidth(0, 180)
        numz = 0
        for key, data in slc.iteritems():
            buffcolor = float(data[3].replace('$', ''))
            iddx = self.lizt.Append(data)
            self.lizt.SetItemData(iddx, key)
            for ix in range(3, 5):
                item = self.lizt.GetItem(numz, ix)
                item.SetMask(fontMask)
                item.SetFont(font)
                if buffcolor > 0:
                    item.SetTextColour(wx.GREEN)
                    self.lizt.SetItem(item)
                    continue
                if buffcolor < 0:
                    item.SetTextColour(wx.RED)
                    self.lizt.SetItem(item)
                    continue
                self.lizt.SetItem(item)
            numz += 1

    # def ultilist_update(self):
    #     self.ultiStockList.GetColumn(1)
    #     numz = 0
    #     for key, data in slc.iteritems():
    #         buffcolor = float(data[3].replace('$', ''))
    #         iddx = self.lizt.Append(data)
    #         self.lizt.SetItemData(iddx, key)
    #         for ix in range(3, 5):
    #             item = self.lizt.GetItem(numz, ix)
    #             item.SetMask(fontMask)
    #             item.SetFont(font)
    #             if buffcolor > 0:
    #                 item.SetTextColour(wx.GREEN)
    #                 self.lizt.SetItem(item)
    #                 continue
    #             if buffcolor < 0:
    #                 item.SetTextColour(wx.RED)
    #                 self.lizt.SetItem(item)
    #                 continue
    #             self.lizt.SetItem(item)
    #         numz += 1
    '''
        EVENTS
    '''
    def OnColClick(self, event):
        plot_title = event.GetText()
        ticker = self.tickerlookup.keys()[self.tickerlookup.values().index(plot_title)]
        self.plt1_1.clear()
        self.plt1_2.clear()
        self.plt2_1.clear()
        self.plt2_2.clear()
        self.plt1_1_plot(ticker, plot_title)
        self.plt1_2_plot(ticker, plot_title)
        self.plt2_1_plot(ticker, plot_title)
        self.plt2_2_plot(ticker, plot_title)
        self.figure1.autofmt_xdate()
        self.figure2.autofmt_xdate()
        self.figure3.autofmt_xdate()
        self.figure4.autofmt_xdate()
        self.figure1.canvas.draw()
        self.figure2.canvas.draw()
        self.figure3.canvas.draw()
        self.figure4.canvas.draw()
        self.tick1_txt.SetLabel(ticker)
        self.tick2_txt.SetLabel(ticker)

    def plt1_getCompany(self, event):
        compName = event.GetString()
        self.plt1_1.clear()
        self.plt1_2.clear()
        self.plt1_1_plot(compName, self.tickerlookup[compName])
        self.plt1_2_plot(compName, self.tickerlookup[compName])
        self.figure1.autofmt_xdate()
        self.figure2.autofmt_xdate()
        self.figure1.canvas.draw()
        self.figure2.canvas.draw()
        self.tick1_txt.SetLabel(compName)
        self.tick2_txt.SetLabel(compName)

    def plt2_getCompany(self, event):
        compName = event.GetString()
        self.plt2_1.clear()
        self.plt2_2.clear()
        self.plt2_1_plot(compName, self.tickerlookup[compName])
        self.plt2_2_plot(compName, self.tickerlookup[compName])
        self.figure3.autofmt_xdate()
        self.figure4.autofmt_xdate()
        self.figure3.canvas.draw()
        self.figure4.canvas.draw()

    def checkMovingAverage(self,event):
        dt_start = datetime.datetime(2015, 1, 1)
        dt_end = datetime.datetime(2016, 7, 15)
        self.stock_data = data.DataReader('GOOG', 'google', dt_start, dt_end)
        self.stock_data = np.asarray(self.stock_data['Close']).flatten()
        cb = event.GetEventObject()
        isChecked = cb.GetValue()
        if isChecked:
            self.plt1_2.clear()
            self.stock_data = moving_average(self.stock_data, 15)
            self.plt1_2.plot(self.stock_data, color='m', label='Moving Average')
            self.plt1_2.grid(True)
            self.figure2.canvas.draw()
        if not isChecked:
            self.plt1_2.plot(self.stock_data, visiable=False)
            self.figure2.canvas.draw()

    def checkMACD(self, event):
        dt_start = datetime.datetime(2015, 1, 1)
        dt_end = datetime.datetime(2016, 7, 15)
        self.stock_data = data.DataReader('GOOG', 'google', dt_start, dt_end)
        self.stock_data = np.asarray(self.stock_data['Close']).flatten()
        cb = event.GetEventObject()
        isChecked = cb.GetValue()
        if isChecked:
            self.plt1_2.clear()
            _, _, self.stock_data = moving_average_convergence_divergence(self.stock_data)
            self.plt1_2.plot(self.stock_data, color='m', label='Moving Average')
            self.plt1_2.grid(True)
            self.figure2.canvas.draw()
        if not isChecked:
            self.plt1_2.plot(self.stock_data, visiable=False)
            self.figure2.canvas.draw()

    '''
        ANIMATION
    '''
    def animate(self, i):
        ticker = self.tickerlookup.keys()[self.tickerlookup.values().index(self.plt2_2.get_title())]
        print '#-----------------------------------#'
        print '\t\t\tUPDATING IN PROGRESS'
        print '#-----------------------------------#'
        if self.no_rept_count != 0:
            self.plt1_1update()
            self.plt1_2update()
            self.figure1.autofmt_xdate()
            self.figure2.autofmt_xdate()
            col_state, order = self.lizt.GetSortState()
            self.ultiStockList.ClearAll()
            self.ultiSLmethod()
            self.lizt.SortListItems(col_state, order)
        else:
            self.tick1_txt.SetLabel(ticker)
            self.tick2_txt.SetLabel(ticker)
        self.no_rept_count += 1
        print '#-----------------------------------#'
        print '\t\t\tUPDATING COMPLETE'
        print '#-----------------------------------#'

#--------------------------------------------------------------------------------------

class Sorting_List(ULC.UltimateListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent, Data):
        ULC.UltimateListCtrl.__init__(self, parent, size=(570,650),
                                      agwStyle=ULC.ULC_REPORT | ULC.ULC_HAS_VARIABLE_ROW_HEIGHT |
                                      ULC.ULC_SORT_ASCENDING)
        self.itemDataMap = Data
        listmix.ColumnSorterMixin.__init__(self, len(Data))

    def GetListCtrl(self):
        return self

#--------------------------------------------------------------------------------------

class My_App(wx.App):
    def OnInit(self):

        frame = Quant(None, "QUANT - Bulls n' Bears")
        frame.CenterOnScreen()
        frame.Show(True)
        return True

#--------------------------------------------------------------------------------------

def main():
    app = My_App(False)
    app.MainLoop()

#--------------------------------------------------------------------------------------

if __name__ == '__main__':
    main()
#--------------------------------------------------------------------------------------

