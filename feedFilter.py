# Created by: Curtis Szmania
# Date: 10/1/2014
# Initial Creation
# 
# Date: 5/12/2017
# Version 0.01 release

__author__='szmania'

import requests
import feedparser
import logging
import re
import subprocess
import os
import sys

import datetime
import argparse
import abc

from PyQt5.QtGui import *
from PyQt5.Qt import *

# Check if Python3. If so import urllib3.
# if sys.version_info >= (3, 0):
#     import urllib3
# else:
#     import urllib2

# sys.path.append('./libs')
# from libs.pyxenforoapi import Xenforo, LoginError
from pyxenforoapi.pyxenforo import Xenforo, LoginError
# from libs.rutracker.rutracker import Configuration

from lxml import etree
from requests.auth import HTTPDigestAuth
from pytz import timezone
import xml.etree.ElementTree as ET
from requests import session



# ruTrackerRSS_NFL = 'http://feed.rutracker.cc/atom/f/875.atom'
# ruTrackerRSS_NFL_filters = ['Seahawks','Chargers']
# self.deluge_download_torrent_folder = 'G:\\temp\Deluge_Torrents'
LOGFILE_feedFilter = 'feedFilter_log.log'
FILTERS_FILE = 'data\\filters.ini'
ACCOUNTS_FILE = 'data\\accounts.ini'
TORRENT_CLIENTS_FILE = 'data\\torrentClients.ini'

MEGATOOLS_EXEs = ['megacopy', 'megadf', 'megadl', 'megaget', 'megals', 'megamkdir', 'megaput', 'megareg', 'megarm']

class feedFilter_Xenforo(Xenforo):
    def __init__(self, username, password, site, proxy=None):
        # Xenforo.__init__(self, username, password, site, proxy=None)
        """Inititalize a Xenforo instance

        Args:
            username (str): The username you login with
            password (str): Password to your account
            site (str): Website to login to

        Keyword args:
            proxy (dict): Optional to use, specify proxy as a dictionary
            if you wish to use a proxy. The proxy will
            be used on all your actions, only need to
            specify it once

        Examples:
            xf = Xenforo("User", "Password", "https://website.com/")
            xf = Xenforo("User", "Password", "https://website.com",
                         proxy={"http": "http://user:pass@host:port"
                                "https": "https://user:pass@host:port"})

        """

        self.username = username
        self.password = password
        self.site = site
        self.proxy = proxy
        self.session = requests.Session()

        if self.proxy is not None:
            self.session.proxies.update(proxy)

        self.session.headers.update(Xenforo.HEADERS)
        self.session.get(self.site)
        self.login()



    def login(self):
        """Logs into XenForo

        Raises:
            LoginError: If it fails to extract 'LoggedIn' in the HTML
            source. All logged in users have the class
            'LoggedIn' appended to the html id attribute

        """

        data = {
            "login": self.username,
            "register": 0,
            "password": self.password,
            "remember": 1,
            "cookie_check": 1,
            "redirect": "/community/"
        }

        request = self.session.post(self.site + "/login/login", data=data)
        check_if_logged_in = request.content.decode("UTF-8")

        if "LoggedIn" in check_if_logged_in:
            logged_in = True
        elif "LoggedOut" in check_if_logged_in:
            logged_in = False
        else:
            logged_in = None

        if logged_in is False:
            raise LoginError("Unable to login, invalid credentials.")
        elif logged_in is None:
            raise LoginError("Unknown error while trying to login")


class MainWindow(QMainWindow):
    def __init__(self, **kwargs):
        QMainWindow.__init__(self)
        self.filtersList = []


    def run_gui(self):
        """
        Run Feed Filter gui.
        """
        self.filtersList = self.read_filters_file()
        self.setup_gui()

    def setup_gui(self):
        """
        Setup gui.
        """
        app = QApplication(sys.argv)
        self.cw = QWidget(self)
        self.setCentralWidget(self.cw)
        self.setMaximumSize(700, 600)

        self.setWindowTitle('Feed Filter')
        self.cwGrid = QGridLayout()
        self.cwGrid.setSpacing(5)
        self.center()
        self.setGeometry(300, 50, 500, 600)
        self.cw.setLayout(self.cwGrid)
        # self.connect(self.btn1, SIGNAL("clicked()"), self.doit)
        self.populate()
        self.signals_slots()

        self.show()
        self.get_widget_initial_sizes()

        app.exec_()

    def center(self):
        """
        Center gui window.
        """
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())


    def get_widget_initial_sizes(self):
        """
        Get widget initial sizes.
        """
        self._width = self.width()
        self._height = self.height()


    def populate(self):
        """
        Populate gui widgets.
        """

        self.populate_mega_manager()

        self.populate_feed_filter_gui()


    def populate_mega_manager(self):
        """
        Populate MEGA Manager widget
        """
        self.megaManagerWidget = QWidget(self.cw)
        self.cwGrid.addWidget(self.megaManagerWidget, 5,5)
        self.megaManagerWidget.setMinimumSize(500,1)

        self.mmGrid = QGridLayout()
        self.mmGrid.setSpacing(5)
        self.megaManagerWidget.setLayout(self.mmGrid)

        self.megaManagerShowBtn = QPushButton("MEGA Manager")
        self.megaManagerShowBtn.setCheckable(True)
        self.mmGrid.addWidget(self.megaManagerShowBtn, 5, 5)
        self.megaManagerShowQLV = QListView()
        self.mmGrid.addWidget(self.megaManagerShowQLV, 6, 5)
        self.megaManagerShowQLV.setVisible(False)
        self.mmQLVGrid = QGridLayout()
        self.mmQLVGrid.setSpacing(5)
        self.megaManagerShowQLV.setLayout(self.mmQLVGrid)

        self.mmAccountsFileLbl = QLabel('MEGA Accounts File:')
        self.mmQLVGrid.addWidget(self.mmAccountsFileLbl, 2, 5)
        self.mmAccountsFileTxt = QLineEdit()
        self.mmQLVGrid.addWidget(self.mmAccountsFileTxt, 2, 6)
        self.mmAccountsFileBtn = QPushButton("...")
        # self.mmAccountsFileBtn.setGeometry(QRect(50, 50, 30, 30))
        self.mmQLVGrid.addWidget(self.mmAccountsFileBtn, 2, 7)
        self.mmAccountsFileBtn.setMaximumSize(30,30)

        self.mmMegaToolsLbl = QLabel('MEGA Tools directory:')
        self.mmQLVGrid.addWidget(self.mmMegaToolsLbl, 4, 5)
        self.mmMegaToolsTxt = QLineEdit()
        self.mmQLVGrid.addWidget(self.mmMegaToolsTxt, 4, 6)
        self.mmMegaToolsBtn = QPushButton("...")
        # self.mmAccountsFileBtn.setGeometry(QRect(50, 50, 30, 30))
        self.mmQLVGrid.addWidget(self.mmMegaToolsBtn, 4, 7)
        self.mmMegaToolsBtn.setMaximumSize(30,30)

        #edited this to make mega manager invisible at this stage
        self.megaManagerWidget.setVisible(False)


    def populate_feed_filter_gui(self):
        """
        Populate Feed Filter gui.
        """
        self.feedFilterWidget = QWidget(self.cw)
        self.cwGrid.addWidget(self.feedFilterWidget, 10,5)
        self.feedFilterWidget.setMinimumSize(500,1)

        self.ffGrid = QGridLayout()
        self.ffGrid.setSpacing(5)
        self.feedFilterWidget.setLayout(self.ffGrid)

        self.feedFilterShowBtn = QPushButton("Feed Filters")
        self.feedFilterShowBtn.setCheckable(True)
        self.ffGrid.addWidget(self.feedFilterShowBtn, 5, 5)
        self.feedFilterShowQLV = QListView()
        self.ffGrid.addWidget(self.feedFilterShowQLV, 10, 5)
        self.feedFilterShowQLV.setVisible(False)

        self.ffQLVGrid = QGridLayout()
        self.ffQLVGrid.setSpacing(5)
        self.feedFilterShowQLV.setLayout(self.ffQLVGrid)

        # self.feedFilterShowQLV_x = self.feedFilterShowQLV.x()
        # self.feedFilterShowQLV_y = self.feedFilterShowQLV.y()

        self.contentsLbl = QLabel('Current Feed Filters:')
        self.ffQLVGrid.addWidget(self.contentsLbl, 0, 0)
        self.contentsTxtEdit = QTextEdit()
        self.ffQLVGrid.addWidget(self.contentsTxtEdit, 1, 0, 1, -1)
        self.contentsTxtEdit.setText(self.getFiltersFileText())
        # self.contentsTxtEdit.setMinimumHeight(100)

        self.filterNameLbl = QLabel("Feed Filter Name:")
        self.ffQLVGrid.addWidget(self.filterNameLbl, 2, 0)
        self.filterNameTxt = QLineEdit()
        self.ffQLVGrid.addWidget(self.filterNameTxt, 2, 1, 1, 2)

        self.urlLbl = QLabel("Feed URL:")
        self.ffQLVGrid.addWidget(self.urlLbl, 4, 0)
        self.urlTxt = QLineEdit()
        self.ffQLVGrid.addWidget(self.urlTxt, 4, 1, 1, 2)

        self.containsLbl = QLabel('Contains (delineated by ",":')
        self.ffQLVGrid.addWidget(self.containsLbl, 6, 0)
        self.containsTxt = QLineEdit()
        self.ffQLVGrid.addWidget(self.containsTxt, 6, 1, 1, 2)

        self.excludesLbl = QLabel('Excludes (delineated by ","):')
        self.ffQLVGrid.addWidget(self.excludesLbl, 8, 0)
        self.excludesTxt = QLineEdit()
        self.ffQLVGrid.addWidget(self.excludesTxt, 8, 1, 1, 2)

        self.clientLbl = QLabel("Torrent Client:")
        self.ffQLVGrid.addWidget(self.clientLbl, 10, 0)
        self.delugeChkBox = QCheckBox('Deluge')
        self.ffQLVGrid.addWidget(self.delugeChkBox, 10, 1)
        self.vuzeChkBox = QCheckBox('Vuze')
        self.ffQLVGrid.addWidget(self.vuzeChkBox, 10, 2)
        # self.clientTxt = QLineEdit()
        # self.ffQLVGrid.addWidget(self.clientTxt, 6, 1, 1, 2)
        # self.clientBtn = QPushButton("...")
        # self.clientBtn.setGeometry(QRect(50, 50, 30, 30))
        # self.ffQLVGrid.addWidget(self.clientBtn, 6, 3)

        self.typeLbl = QLabel('Type:')
        self.ffQLVGrid.addWidget(self.typeLbl, 12, 0)
        self.rssChkBox = QCheckBox('RSS')
        self.ffQLVGrid.addWidget(self.rssChkBox, 12, 1)
        self.htmlChkBox = QCheckBox('HTML')
        self.ffQLVGrid.addWidget(self.htmlChkBox, 12, 2)

        self.enabledChkBox = QCheckBox('Enabled')
        self.ffQLVGrid.addWidget(self.enabledChkBox, 14, 0)

        self.addFilterBtn = QPushButton("Add Feed Filter")
        # self.addFilterBtn.setGeometry(QRect(50, 50, 100, 30))
        self.ffQLVGrid.addWidget(self.addFilterBtn, self.ffQLVGrid.rowCount(),  self.ffQLVGrid.columnCount()-1)

        self.fetchTorrentsBtn = QPushButton("Fetch Torrents")
        self.ffQLVGrid.addWidget(self.fetchTorrentsBtn, self.ffQLVGrid.rowCount() + 1, self.ffQLVGrid.columnCount() - 1)


    def signals_slots(self):
        """
        Signals and slots.
        """
        self.mmAccountsFileBtn.clicked.connect(self.mega_accounts_file_select_file)
        self.mmMegaToolsBtn.clicked.connect(self.mega_tools_select_dir)

        self.megaManagerShowBtn.toggled.connect(self.show_mega_manager)

        self.feedFilterShowBtn.toggled.connect(self.show_feed_filter)
        self.addFilterBtn.clicked.connect(self.add_filter)
        self.rssChkBox.clicked.connect(self.type_chk_box)
        self.htmlChkBox.clicked.connect(self.type_chk_box)

        self.fetchTorrentsBtn.clicked.connect(self.fetchTorrents)


    def type_chk_box(self):
        """
        RSS Feed type checkbox.
        """
        if self.rssChkBox.isChecked():
            self.htmlChkBox.setChecked(False)

        if self.htmlChkBox.isChecked():
            self.rssChkBox.setChecked(False)


    def show_mega_manager(self):
        """
        Show MEGA Manager.
        """
        # self.animation = QPropertyAnimation(self.megaManagerShowQLV, 'size')
        # self.animation.setDuration(200)
        if self.megaManagerShowBtn.isChecked():
            self.megaManagerShowQLV.setVisible(True)
            # self.megaManagerShowQLV_width = self.megaManagerShowQLV.width()
            # self.megaManagerShowQLV_height = self.megaManagerShowQLV.height()
            # # animation.setStartValue(100, 100)
            # self.animation.setStartValue(self.megaManagerShowQLV.size())
            # self.animation.setEndValue(QSize(self.megaManagerShowQLV.width(), 0))
            # self.animation.start()
        else:
            self.megaManagerShowQLV.setVisible(False)
            # self.animation.setStartValue(self.megaManagerShowQLV.size())
            # self.animation.setEndValue(QSize(self.megaManagerShowQLV_width, self.megaManagerShowQLV_height))
            # self.animation.start()
        # self.cw.adjustSize()

        # self.megaManagerWidget.adjustSize()
        # self.adjustSize()


    def show_feed_filter(self):
        """
        Show Feed Filter gui.
        """

        # self.animationff = QPropertyAnimation(self.feedFilterShowQLV, 'visible')
        # self.animationff.setDuration(200)
        if self.feedFilterShowBtn.isChecked():
            self.feedFilterShowQLV.setVisible(True)
            # animation.setStartValue(100, 100)
            # self.animationff.setStartValue(self.feedFilterShowQLV.isVisible())
            # self.animationff.setEndValue(False)
            # self.animationff.start()
            # self.feedFilterShowQLV.setVisible(False)
            # self.feedFilterShowQLV_width = self.feedFilterShowQLV.width()
            # self.feedFilterShowQLV_height = self.feedFilterShowQLV.height()
            # self.animationff.setStartValue(self.feedFilterShowQLV.size())
            # self.animationff.setEndValue(QSize(self.feedFilterShowQLV.width(), 0))
            # self.animationff.start()
            # self.feedFilterShowQLV.resize(0,0)
        else:
            self.feedFilterShowQLV.setVisible(False)

            # self.animationff.setStartValue(self.feedFilterShowQLV.isVisible())
            # self.animationff.setEndValue(True)
            # self.animationff.start()
            # self.animationff.setStartValue(self.feedFilterShowQLV.size())
            # self.animationff.setEndValue(QSize(self.feedFilterShowQLV_width, self.feedFilterShowQLV_height))
            # self.animationff.start()
            # self.feedFilterShowQLV.resize(self.feedFilterShowQLV_width, self.feedFilterShowQLV_height)
            # self.feedFilterShowQLV.setGeometry(QRect(self.feedFilterShowQLV_x, self.feedFilterShowQLV_y, self.feedFilterShowQLV_width, self.feedFilterShowQLV_height))
        # self.cw.adjustSize()
        # self.feedFilterWidget.adjustSize()
        # self.adjustSize()


    def mega_accounts_file_select_file(self):
        """
        MEGA accounts file, select file.
        """
        self.mmAccountsFileTxt.setText(QFileDialog.getOpenFileName(filter="Text file (*.txt)"))

    def mega_tools_select_dir(self):
        """
        Select directory for MEGA tools api location.
        """
        self.mmMegaToolsTxt.setText(QFileDialog.getExistingDirectory(options=QFileDialog.ShowDirsOnly))
        for item in MEGATOOLS_EXEs:
            if not os.path.isfile(self.mmMegaToolsTxt.text()+ '\%s.exe' % item):
                QMessageBox.warning(self, 'MegaTools executable not found!', '"%s" not found!' % item)

    def add_filter(self):
        """
        Add filter.
        """
        filterDict = {}
        filterDict['name'] = self.filterNameTxt.text()
        filterDict['url'] = self.urlTxt.text()
        filterDict['contains'] = self.containsTxt.text()
        filterDict['excludes'] = self.excludesTxt.text()

        clients = []
        if self.delugeChkBox.isChecked():
            clients.append('Deluge')

        if self.vuzeChkBox.isChecked():
            clients.append('Vuze')

        filterDict['client'] = ','.join(clients)

        if self.rssChkBox.isChecked():
            filterDict['type'] = 'RSS'
        elif self.htmlChkBox.isChecked():
            filterDict['type'] = 'HTMl'
        else:
            filterDict['type'] = ''

        if self.enabledChkBox.isChecked():
            filterDict['enabled'] = str(True)


        self.filtersList.append(filterDict)
        self.write_to_filters_file()
        self.read_filters_file()
        self.contentsTxtEdit.setText(self.getFiltersFileText())


    def write_to_filters_file(self, dateTime=None):
        """
        Write to filters file.

        Args:
            dateTime (str): Date time as string for setting last check date.
        """

        with open(FILTERS_FILE, "w") as filtersFile:

            for i in range(len(self.filtersList)):
                dict = self.filtersList[i]
                filtersFile.write('name='+dict['name']+'\n')
                filtersFile.write('url='+dict['url']+'\n')
                filtersFile.write('contains='+dict['contains']+'\n')
                filtersFile.write('excludes='+dict['excludes']+'\n')
                filtersFile.write('client='+dict['client']+'\n')
                filtersFile.write('type='+dict['type']+'\n')
                filtersFile.write('enabled='+dict['enabled']+'\n')

                if dateTime and dict['enabled'] == 'True':
                    filtersFile.write('lastChecked='+ str(dateTime) +'\n')
                else: 
                    filtersFile.write('lastChecked='+ dict['lastChecked'] +'\n')

                filtersFile.write('==========================================\n')

        filtersFile.close()


    def read_filters_file(self):
        """
        Read filters file.
        """
        self.filtersList = []
        with open(FILTERS_FILE, "r") as filtersFile:
            dict = {}

            for line in filtersFile:

                if line.startswith('='):
                    self.filtersList.append(dict)
                    dict = {}
                else:
                    if len(re.findall('=', line)) > 0:
                        dict[line.split('=')[0]] = re.sub('\n','',line.split('=')[1])

        filtersFile.close()



    def getFiltersFileText(self):
        with open(FILTERS_FILE, "r") as filtersFile:
            text = filtersFile.read()

        filtersFile.close()
        return text

    def fetchTorrents(self):
        self.run_feed_filter()
        # qMessageBox = QMessageBox()
        QMessageBox.information(self, 'Fetching done', 'Torrent fetching finished!')


    @abc.abstractmethod
    def run_feed_filter(self):
        pass

    @abc.abstractmethod
    def getAllMegaAccountsStatus(self):
        pass



class FeedFilter(MainWindow):
    def __init__(self, **kwargs):
        """
        Feed Filter sifts through peer-to-peer file sharing RSS feeds to find torrent files.
        """
        MainWindow.__init__(self, **kwargs)


        self._setup_log()

        for key, value in kwargs.items():
            setattr(self, key, value)


        logging.debug('')
        logging.debug('')


        self._setup()


    def _setup(self):
        """
        Feed Filter setup.
        """

        logging.debug(' Setting up feedFilter.')


        self.get_torrent_clients_info()

        if (not self.ruTracker_username or self.ruTracker_password) \
                and (not self.tyt_username or self.tyt_password)\
                and (not self.tyt_forums_username or self.tyt_forums_password):

            self.get_accounts_info()

        if self.auto:
            self.run_feed_filter()
        else:
            self.run_gui()


    def __exit__(self):
        """
        Feed Filter "deconstructor".
        """

        logging.debug(' ENTERING DECONSTRUCTOR!!!')
        self.write_to_filters_file()
        # self._teardown_log()

    def _setup_log(self):
        """
        Set up logging.
        """
        
        logging.basicConfig(filename=LOGFILE_feedFilter, level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt="%Y-%m-%d %H:%M:%S")


        # with open("feedFilters.log", "a") as log:
        #     log.write(str(datetime.datetime.now()) +"\n")
        # log.close()


    def _teardown_log(self):
        """
        Tear down logging.
        """
        with open("feedFilter_log.log", "a") as log:
            log.write(str(datetime.datetime.now()) +"\n")
        log.close()


    def get_torrent_clients_info(self):
        """
        Get torrent client's information.
        """
        logging.debug(' Getting torrent client info from torrentClients.cfg file.')

        with open(TORRENT_CLIENTS_FILE, 'r') as cfg:
            lines = cfg.readlines()

        for i in range(len(lines)):
            if '[deluge]' in lines[i]:
                self.deluge_download_torrent_folder = re.sub('torrentDownloadDir=', '', lines[i+1]).rstrip('\r\n')

            elif '[vuze]' in lines[i]:
                self.vuze_download_torrent_folder = re.sub('torrentDownloadDir=', '', lines[i+1]).rstrip('\r\n')


    def get_accounts_info(self):
        """
        Get peer-to-peer account information from accounts.cfg
        """
        logging.debug(' Getting accounts info from accounts.cfg file.')

        with open(ACCOUNTS_FILE, 'r') as cfg:

            lines = cfg.readlines()

        for i in range(len(lines)):
            if '[rutracker]' in lines[i]:
                self.ruTracker_username = re.sub('username=', '', lines[i+1]).rstrip('\r\n')
                self.ruTracker_password = re.sub('password=', '', lines[i+2]).rstrip('\r\n')

            elif '[tenyardtracker]' in lines[i]:
                self.tyt_username = re.sub('username=', '', lines[i+1]).rstrip('\r\n')
                self.tyt_password = re.sub('password=', '', lines[i+2]).rstrip('\r\n')

            elif '[tenyardtracker_forums]' in lines[i]:
                self.tyt_forums_username = re.sub('username=', '', lines[i+1]).rstrip('\r\n')
                self.tyt_forums_password = re.sub('password=', '', lines[i+2]).rstrip('\r\n')


    def run_feed_filter(self):
        """
        Run Feed Filter.
        """
        logging.debug(' Running feedFilter.')

        self._getFeedFilters()
        for i in range(len(self.filtersList)):
            self._process_filter(self.filtersList[i])

        self.write_to_filters_file(dateTime=datetime.datetime.now())


    def _process_filter(self, dict):
        """
        Process filter.

        Args:
            dict (dict): dictionary
        """
        logging.debug('')
        logging.debug(' Processing filter: %s' % (dict['name']))
        feedData = self._getFeedData(dict['url'])


        if dict['client'] == 'Deluge':
            downloadTorrentDir = self.deluge_download_torrent_folder
        elif dict['client'] == 'Vuze':
            downloadTorrentDir = self.vuze_download_torrent_folder

        # dict['feedData'] = feedData
        if dict['enabled'] == 'True':
            posts = self._filterFeed(feedData, dict['lastChecked'], dict['contains'], dict['excludes'])
            if len(posts) > 0:
                logging.debug(' POSTS FOUND!')
            logging.debug(' %d post(s) found for "%s" - "%s"' % (len(posts), dict['name'], dict['url']))

            for i in range(len(posts)):

                logging.debug('    Post title: "%s"' % posts[i].title)
                # if dict['client'] == 'Deluge':
                if 'rutracker' in posts[i].link:
                    topicID = self._getTopicIDFromPostURL(posts[i].link)
                    self._downloadTorrent_ruTracker(topicID, downloadTorrentDir)
                    # self.addTorrentToDeluge(topicID)

                elif 'tenyardtracker' in posts[i].link:
                    torrentURL, session = self._getTorrentURL_RSS_TYT(posts[i])
                    if torrentURL and session:
                        self._downloadTorrent_TYT(torrentURL, session, downloadTorrentDir)


        else:
            logging.debug(' Feed filter "%s" not enabled. Skipping.' % dict['name'])


    def _getFeedFilters(self):
        logging.debug(' Read feeds.')

        self.read_filters_file()


    def _getFeedData(self, url):
        logging.debug(' Getting feed data from "%s".' % url)

        if 'tenyardtracker' in url:
            xf = feedFilter_Xenforo('%s' % self.tyt_forums_username, '%s' % self.tyt_forums_password, 'http://tenyardtracker.com/community')

            # proxies = {
            #     'http': 'http://:@86.105.55.40:3128',
            #     'https': 'https://:@86.105.55.40:3128'
            # }

            # xf = pyxenforo.Xenforo('%s' % self.tyt_forums_username, '%s' % self.tyt_forums_password, 'http://tenyardtracker.com/community',
            #                        proxy=proxies)

            # xf = XenForo('%s' % self.tyt_forums_username, '%s' % self.tyt_forums_password, '//tenyardtracker.com')
            # xf.login()
            # xenforoObj.login()
            stringData = xf.session.get(url)
            data = feedparser.parse(stringData.text)

            # pwdmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            # auth = urllib2.HTTPBasicAuthHandler(pwdmgr)
            # opener = urllib2.build_opener(auth)
            # data = opener.open(url)
            # d = feedparser.parse(data)
            # print('')
            # auth = urllib2.HTTPBasicAuthHandler()
            # data = feedparser.parse(url, handlers=[auth])
            return data

        else:
            data = feedparser.parse(url)
            return data


    def _filterFeed(self, data, lastChecked, contains='', excludes=''):
        logging.debug(' Filtering data in feed which containes "%s" and excludes "%s".' % (contains, excludes))

        posts = []
        for i in range(len(data['entries'])):

            if contains == '':
                termsContains = []
            else:
                termsContains = contains.split(',')

            if excludes == '':
                termsExcludes = []
            else:
                termsExcludes = excludes.split(',')

            if 'tenyardtracker' in data.feed.link:
                updated = data.entries[i].published
                convUpdated = datetime.datetime.strptime(re.sub(' \+.*', '', updated), '%a, %d %b %Y %H:%M:%S')

                # convUpdated = datetime.datetime.strptime(re.sub(' \+.*', '', updated), '%a, %d %b Y %H:%M:%S')
            else:
                updated = data.entries[i].updated
                convUpdated = datetime.datetime.strptime(re.sub('\+.*', '', updated), '%Y-%m-%dT%H:%M:%S') - datetime.timedelta(hours=7)
            try:
                convLastChecked = datetime.datetime.strptime(lastChecked.split('.')[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                convLastChecked = datetime.datetime.strptime('1900-12-10 00:00:00', '%Y-%m-%d %H:%M:%S')

            if convLastChecked < convUpdated:
                foundIncludes = True
                for termContain in termsContains:
                    termContain = termContain.lstrip(' ').rstrip(' ')
                    if not termContain in data.entries[i].title and not termContain.lower() in data.entries[i].title:

                        # logging.debug(' Did not find one term that it must contain "%s" in url: "%s"!' % (termContain, data.entries[i].title))
                        foundIncludes = False

                foundExcludes = False
                for termExclude in termsExcludes:
                    termExclude = termExclude.lstrip(' ').rstrip(' ')
                    if termExclude in data.entries[i].title:
                        # logging.debug(' Found one term that it must exclude "%s" in url: "%s"!' % (termExclude, data.entries[i].title))
                        foundExcludes = True

                if foundIncludes == True and foundExcludes == False:
                    logging.debug(' Found all "contains" and did not find any "excludes" in url: "%s"!' % data.entries[i].title)
                    posts.append(data.entries[i])

        return posts


    def convertFeedURLToTorrentURL(self, feedURL):
        logging.debug(' Convert feed url to torrent url.')

        if 'rutracker' in feedURL:
            postID = re.sub('.*=','',feedURL)
            torrentURL = 'https://rutracker.org/forum/dl.php?t=' + postID
            return torrentURL


    def _getTopicIDFromPostURL(self, feedURL):
        logging.debug('    Get topic id from post url.')

        if 'rutracker' in feedURL:
            topicID = re.sub('.*=','',feedURL)
            return topicID


    def _downloadTorrent_ruTracker(self, topicID, downloadTorrentDir):
        logging.debug('    Downloading torrent file from ruTracker to "%s".' % downloadTorrentDir)
        logging.debug('    Using arguments: ' + ' -t ' + topicID + ' -u ' + self.ruTracker_username + ' -p ' + self.ruTracker_password + ' -o ' + downloadTorrentDir)

        # if self.silent:
        CREATE_NO_WINDOW = 0x08000000
        proc1 = subprocess.call('python libs\\rutracker\\rutracker.py ' + ' -t ' + topicID + ' -u ' + self.ruTracker_username + ' -p ' + self.ruTracker_password + ' -o ' + downloadTorrentDir,  creationflags=CREATE_NO_WINDOW)
        return proc1


    def addTorrentToDeluge(self, topicID):
        logging.debug(' Adding torrent to Deluge topic id: "%s".' % topicID)

        torrent =  'G:\\temp\Deluge_Torrents\\torrent[' + topicID + '].torrent'
        if os.path.isfile(torrent):
            cmd = '"D:\Program Files (x86)\Deluge\deluge-console.exe" add  %s ' % torrent
        # cmd = "C:\Program Files\Vuze\Azureus.exe"
            proc1 = os.system(cmd)


    def addTorrentToVuze(self, topicID):
        logging.debug(' Adding torrent to Vuze topic id: "%s".' % topicID)

        cmd = 'C:\\Program Files\\Vuze\\Azureus.exe ' + os.getcwd() + '\\torrent[' + topicID + '].torrent'
        # cmd = "C:\Program Files\Vuze\Azureus.exe"
        proc1 = os.system('C:\\Program Files\\Vuze\\Azureus.exe ' + os.getcwd() + '\\torrent[' + topicID + '].torrent')


    def _getTorrentURL_RSS_TYT(self, postData):
        logging.debug('    Getting torrent url from TYT rss feed.' )

        torrentPostURL = self._getTYTForumTorrentPostURL(postData['content'][0]['value'])
        # from requests.auth import HTTPDigestAuth
        # url = 'http://tenyardtracker.com/details.php?id=32823'
        #
        # s = requests.session()
        # r = s.get('http://tenyardtracker.com/details.php?id=32823')
        # print(s.cookies)
        # print r.content

        session = requests.Session()
        tty_loginURL = 'http://tenyardtracker.com/members.php?action=takelogin'
        # r = requests.get("http://tenyardtracker.com/members.php?action=login")
        # # Parse it
        # auth_key = re.findall("auth_key' value='(.*?)'", r.text)[0]

        # This is the form data that the page sends when logging in
        login_data = {
            'username': '%s' % self.tyt_username,
            'password': '%s' % self.tyt_password,
        }
        loginDAta = session.post(tty_loginURL, data=login_data)

        if not torrentPostURL == '':
            torrentPostData = session.get(torrentPostURL)
            found = re.findall("torrent=\d*\\'>", torrentPostData.content)

            if len(found) > 0:
                torrentURLPostfix = re.sub("\\'>", '', found[0])
                torrentURL = 'http://tenyardtracker.com/download.php?' + torrentURLPostfix
                return torrentURL, session
            else:
                logging.debug(' Torrent postfix not found in url!')
        else:
            logging.debug(' Torrent post url is blank!')
        return None, None

        # auth = urllib2.HTTPBasicAuthHandler()
        # data = feedparser.parse(torrentPostURL, handlers=[auth])


    def _getTYTForumTorrentPostURL(self, content):
        logging.debug('    Grabbing torrent post url from TYT.')

        found = re.findall('http://tenyardtracker\.com/details\.php\?id=.*">', content)
        if len(found) > 0:
            torrentPostURL = re.sub('">', '', found[0])
            return torrentPostURL
        return ''


    def _downloadTorrent_TYT(self, torrentURL, session, torrentDownloadDir):
        logging.debug(' Downloading torrent from TYT url:"%s".' % torrentURL)

        torrentFile = session.get(torrentURL)
        torrentId = re.sub('http://tenyardtracker.com/download\.php\?torrent=', '', torrentURL)
        with open(torrentDownloadDir + '/tenyardtracker_%s.torrent' % torrentId, 'wb') as f:
            for chunk in torrentFile.iter_content(1024):
                f.write(chunk)

        f.close()


class megaManager(MainWindow):
    def __init__(self, **kwargs):
        MainWindow.__init__(self, **kwargs)




def getArgs():
    parser = argparse.ArgumentParser(description='Feed Filter')

    parser.add_argument('--ruTracker_username', dest='ruTracker_username', default=None,
                        help='Username for account of rutracker.org')

    parser.add_argument('--ruTracker_password', dest='ruTracker_password', default=None,
                        help='Password for account of rutracker.org')

    parser.add_argument('--tytu', dest='tyt_username', default=None,
                        help='Username of account for http://tenyardtracker.com')

    parser.add_argument('--tytp', dest='tyt_password', default=None,
                        help='Password of account for http://tenyardtracker.com')

    parser.add_argument('--tytfu', dest='tyt_forums_username', default=None,
                        help='Username of account for http://tenyardtracker.com/community/')

    parser.add_argument('--tytfp', dest='tyt_forums_password', default=None,
                        help='Password of account for http://tenyardtracker.com/community/')

    parser.add_argument('-a', dest='auto', action='store_true', default=False,
                        help='Autorun Feed Filter fetching, without GUI.')

    # parser.add_argument('-s', dest='silent', action='store_true', default=False,
    #                     help='Silent run_gui of Feed Filter (sifting). No windows.')
    #


    args = parser.parse_args()
    return args.__dict__





def main():
    kwargs = getArgs()
    app = QApplication(sys.argv)
    # mw = MainWindow()
    # mw.run_gui()


    feedFilterObj = FeedFilter(**kwargs)
    # feedFilterObj.fetchTorrents()



if __name__ == "__main__":
    main()


