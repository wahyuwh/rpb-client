#### ##     ## ########   #######  ########  ########  ######
 ##  ###   ### ##     ## ##     ## ##     ##    ##    ##    ##
 ##  #### #### ##     ## ##     ## ##     ##    ##    ##
 ##  ## ### ## ########  ##     ## ########     ##     ######
 ##  ##     ## ##        ##     ## ##   ##      ##          ##
 ##  ##     ## ##        ##     ## ##    ##     ##    ##    ##
#### ##     ## ##         #######  ##     ##    ##     ######

# Standard
import sys
import os
import platform

# Logging
import logging
import logging.config

# Services
from services.DiagnosticService import DiagnosticService
from services.ApplicationEntityService import ApplicationEntityService

# PyQt
from PyQt4 import QtGui, QtCore, QtNetwork
from PyQt4.QtGui import QMainWindow
from PyQt4.QtCore import QT_VERSION_STR
from PyQt4.Qt import PYQT_VERSION_STR

# Contexts
from contexts.ConfigDetails import ConfigDetails
from contexts.OCUserDetails import OCUserDetails
from contexts.UserDetails import UserDetails

# Version numbers comparison
from distutils.version import LooseVersion

# UI
import gui.messages
from gui.LoginDialog import LoginDialog
from gui.mainClientUI import MainWindowUI

# Services
from services.AppConfigurationService import AppConfigurationService
from services.HttpConnectionService import HttpConnectionService
from services.UpgradeService import UpgradeService
from services.OCConnectInfo import OCConnectInfo
from services.OCWebServices import OCWebServices

##      ## #### ##    ## ########   #######  ##      ##
##  ##  ##  ##  ###   ## ##     ## ##     ## ##  ##  ##
##  ##  ##  ##  ####  ## ##     ## ##     ## ##  ##  ##
##  ##  ##  ##  ## ## ## ##     ## ##     ## ##  ##  ##
##  ##  ##  ##  ##  #### ##     ## ##     ## ##  ##  ##
##  ##  ##  ##  ##   ### ##     ## ##     ## ##  ##  ##
 ###  ###  #### ##    ## ########   #######   ###  ###

EXIT_CODE_RESTART = -123456789  # Any value


class MainWindow(QMainWindow, MainWindowUI):
    """Main window view shell
    Main view shell where the other modules views are registered
    """

    def __init__(self, parent=None):
        """Constructor of main application widnow
        """
        QMainWindow.__init__(self, parent)

        self._logger = logging.getLogger(__name__)
        logging.config.fileConfig("logging.ini", disable_existing_loggers=False)

        self.setupUi(self)
        self.statusBar.showMessage("Ready")

        self._logger.info(
            "RadPlanBio host: " + ConfigDetails().rpbHost + ":" + str(ConfigDetails().rpbHostPort)
        )
        self._logger.info(
            "Partner site proxy: " + ConfigDetails().proxyHost + ":" + str(ConfigDetails().proxyPort) + " [" + str(ConfigDetails().proxyEnabled) + "]"
        )

        self.svcHttp = HttpConnectionService(ConfigDetails().rpbHost, ConfigDetails().rpbHostPort, UserDetails())
        self.svcHttp.application = ConfigDetails().rpbApplication
        if ConfigDetails().proxyEnabled:
            self.svcHttp.setupProxy(ConfigDetails().proxyHost, ConfigDetails().proxyPort, ConfigDetails().noProxy)
        if ConfigDetails().proxyAuthEnabled:
            self.svcHttp.setupProxyAuth(ConfigDetails().proxyAuthLogin, ConfigDetails().proxyAuthPassword)

        self.lblRPBConnection.setText(
            "[" + UserDetails().username + "]@"+ ConfigDetails().rpbHost + "/" + ConfigDetails().rpbApplication + ":" + str(ConfigDetails().rpbHostPort)
        )

        try:
            defaultAccount = self.svcHttp.getMyDefaultAccount()
        except Exception:
            self._logger.info("HTTP communication failed.")

        if defaultAccount.ocusername and defaultAccount.ocusername != "":
            ocUsername = defaultAccount.ocusername
            ocPasswordHash = self.svcHttp.getOCAccountPasswordHash()
            ocSoapBaseUrl = defaultAccount.partnersite.edc.soapbaseurl

            successful = False
            try:
                # Create connection artifact to OC
                self.ocConnectInfo = OCConnectInfo(ocSoapBaseUrl, ocUsername)
                self.ocConnectInfo.setPasswordHash(ocPasswordHash)

                if ConfigDetails().proxyEnabled:
                    self.ocWebServices = OCWebServices(
                        self.ocConnectInfo,
                        ConfigDetails().proxyHost,
                        ConfigDetails().proxyPort,
                        ConfigDetails().noProxy,
                        ConfigDetails().proxyAuthLogin,
                        ConfigDetails().proxyAuthPassword
                    )
                else:
                    self.ocWebServices = OCWebServices(self.ocConnectInfo)
                
                successful, studies = self.ocWebServices.listAllStudies()
            except:
                self._logger.info("HTTP OC communication failed.", exc_info=True)

            if successful:
                ocUserDetails = OCUserDetails()
                ocUserDetails.username = ocUsername
                ocUserDetails.passwordHash = ocPasswordHash
                ocUserDetails.connected = True
            else:
                QtGui.QMessageBox.warning(self, "Error", "Wrong username or password!")

    def closeEvent(self, event):
        """Cleaning up
        """
        self._logger.debug("Destroying the application.")
        ApplicationEntityService().quit()

    def quit(self):
        """Quit (exit) event handler
        """
        reply = QtGui.QMessageBox.question(
            self,
            "Question",
            gui.messages.QUE_EXIT,
            QtGui.QMessageBox.Yes,
            QtGui.QMessageBox.No
        )

        if reply == QtGui.QMessageBox.Yes:
            self._logger.debug("Destroying the application.")
            ApplicationEntityService().quit()
            QtGui.qApp.quit()

##     ## ######## ######## ##     ##  #######  ########   ######  
###   ### ##          ##    ##     ## ##     ## ##     ## ##    ## 
#### #### ##          ##    ##     ## ##     ## ##     ## ##       
## ### ## ######      ##    ######### ##     ## ##     ##  ######  
##     ## ##          ##    ##     ## ##     ## ##     ##       ## 
##     ## ##          ##    ##     ## ##     ## ##     ## ##    ## 
##     ## ########    ##    ##     ##  #######  ########   ######  

    def connectToOpenClinica(self):
        """Connection to OpenClinica SOAP web services
        """
        if not OCUserDetails().connected:
            QtGui.QMessageBox.warning(self, "Error", "Cannot connect to RadPlanBio - OpenClinica SOAP services!")
        else:
            return True

##     ##    ###    #### ##    ##
###   ###   ## ##    ##  ###   ##
#### ####  ##   ##   ##  ####  ##
## ### ## ##     ##  ##  ## ## ##
##     ## #########  ##  ##  ####
##     ## ##     ##  ##  ##   ###
##     ## ##     ## #### ##    ##

def startup():
    """Start the client/upgrade
    """
    logger = logging.getLogger(__name__)
    logging.config.fileConfig("logging.ini", disable_existing_loggers=False)

    # Apply app configuration according the config file
    configure()
    # Internationalisation
    # translate()

    # Log the version of client (useful for remote debuging)
    logger.info("RPB desktop client version: " + ConfigDetails().version)
    logger.info("Qt version: " + QT_VERSION_STR)
    logger.info("PyQt version: " + PYQT_VERSION_STR)

    # Basic services
    svcDiagnostic = DiagnosticService()
    svcDiagnostic.ProxyDiagnostic()

    svcHttp = HttpConnectionService(ConfigDetails().rpbHost, ConfigDetails().rpbHostPort, UserDetails())
    svcHttp.application = ConfigDetails().rpbApplication

    if ConfigDetails().proxyEnabled:
        svcHttp.setupProxy(ConfigDetails().proxyHost, ConfigDetails().proxyPort, ConfigDetails().noProxy)
    if ConfigDetails().proxyAuthEnabled:
        svcHttp.setupProxyAuth(ConfigDetails().proxyAuthLogin, ConfigDetails().proxyAuthPassword)

    # App log
    app = QtGui.QApplication(sys.argv)
    ConfigDetails().logFilePath = (str(QtCore.QDir.currentPath())) + os.sep + "client.log"

    # Startup
    if ConfigDetails().isUpgrading is None or ConfigDetails().isUpgrading == "False":
        # Check whether upgrade was done
        showNotify = False
        if ConfigDetails().upgradeFinished is not None and ConfigDetails().upgradeFinished == "True":
            # Start upgrade procedure
            svcUpgrade = UpgradeService()
            svcUpgrade.cleanup()
            msg = "RadPlanBio client has been successfully upgraded"
            showNotify = True

        # Continue with standard login dialog
        loginDialog = LoginDialog(svcHttp)
        if loginDialog.exec_() == QtGui.QDialog.Accepted:

            # Main application window
            ui = MainWindow()
            ui.show()

            # Upgrade completed notification
            if showNotify:
                reply = QtGui.QMessageBox.information(ui, "Upgrade completed", msg, QtGui.QMessageBox.Ok)
                if reply == QtGui.QMessageBox.Ok:
                    showNotify = False

            # Automatic update check at startup
            if (ConfigDetails().startupUpdateCheck):
                
                # Load version from server, user details updated in login dialog
                latestSoftware = svcHttp.getLatestSoftware(ConfigDetails().identifier)
                
                if latestSoftware != None:
                    latestVersion = str(latestSoftware.version)
                else:
                    latestVersion = ConfigDetails().version

                cmp = lambda x, y: LooseVersion(x).__cmp__(y)
                canUpgrade = cmp(ConfigDetails().version, latestVersion)
                if canUpgrade < 0:
                    ui.upgradePopup()
                    
            currentExitCode = app.exec_()
            return currentExitCode
        else:
            ApplicationEntityService().quit()
            QtGui.qApp.quit()
    else:
        # Start updater (RadPlanBio-update.exe)
        if platform.system() == "Windows":
            if os.path.isfile("./update/RadPlanBio-update.exe"):
                QtCore.QProcess.startDetached("./update/RadPlanBio-update.exe")
            else:
                QtCore.QProcess.startDetached("python ./update/mainUpdate.py")
        elif platform.system() == "Linux":
            if os.path.isfile("./update/RadPlanBio-update"):
                QtCore.QProcess.startDetached("./update/RadPlanBio-update")
            else:
                QtCore.QProcess.startDetached("python ./update/mainUpdate.py")
        else:
            QtCore.QProcess.startDetached("python ./update/mainUpdate.py")

        # Close this one
        ApplicationEntityService().quit()
        QtGui.qApp.quit()

def main():
    """Main function
    """
    currentExitCode = EXIT_CODE_RESTART

    while currentExitCode == EXIT_CODE_RESTART:
        currentExitCode = 0
        currentExitCode = startup()

 ######   #######  ##    ## ######## ####  ######   
##    ## ##     ## ###   ## ##        ##  ##    ##  
##       ##     ## ####  ## ##        ##  ##        
##       ##     ## ## ## ## ######    ##  ##   #### 
##       ##     ## ##  #### ##        ##  ##    ##  
##    ## ##     ## ##   ### ##        ##  ##    ##  
 ######   #######  ##    ## ##       ####  ######   

def configure():
    """Read configuration settings from config file
    """
    appConfig = AppConfigurationService(ConfigDetails().configFileName)
    
    section = "RadPlanBioServer"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "host"):
            ConfigDetails().rpbHost = appConfig.get(section)["host"]
        if appConfig.hasOption(section, "port"):
            ConfigDetails().rpbHostPort = appConfig.get(section)["port"]
        if appConfig.hasOption(section, "application"):
            ConfigDetails().rpbApplication = appConfig.get(section)["application"]

    section = "Proxy"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "enabled"):
            ConfigDetails().proxyEnabled = appConfig.getboolean(section, "enabled")
        if appConfig.hasOption(section, "host"):
            ConfigDetails().proxyHost = appConfig.get(section)["host"]
        if appConfig.hasOption(section, "port"):
            ConfigDetails().proxyPort = appConfig.get(section)["port"]
        if appConfig.hasOption(section, "noproxy"):
            ConfigDetails().noProxy = appConfig.get(section)["noproxy"]

    section = "Proxy-auth"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "enabled"):
            ConfigDetails().proxyAuthEnabled = appConfig.getboolean(section, "enabled")
        if appConfig.hasOption(section, "login"):
            ConfigDetails().proxyAuthLogin = appConfig.get(section)["login"]
        if appConfig.hasOption(section, "password"):
            ConfigDetails().proxyAuthPassword = appConfig.get(section)["password"]

    section = "GUI"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "main.width"):
            ConfigDetails().width = int(appConfig.get(section)["main.width"])
        if appConfig.hasOption(section, "main.height"):
            ConfigDetails().height = int(appConfig.get(section)["main.height"])

    section = "DICOM"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "replacepatientnamewith"):
            ConfigDetails().replacePatientNameWith = appConfig.get(section)["replacepatientnamewith"]
        if appConfig.hasOption(section, "constpatientname"):
            ConfigDetails().constPatientName = appConfig.get(section)["constpatientname"]
        if appConfig.hasOption(section, "allowmultiplepatientids"):
            ConfigDetails().allowMultiplePatientIDs = appConfig.getboolean(section, "allowmultiplepatientids")
        if appConfig.hasOption(section, "retainpatientcharacteristicsoption"):
            ConfigDetails().retainPatientCharacteristicsOption = appConfig.getboolean(section, "retainpatientcharacteristicsoption")
        if appConfig.hasOption(section, "retainstudydate"):
            ConfigDetails().retainStudyDate = appConfig.getboolean(section, "retainstudydate")
        if appConfig.hasOption(section, "retainstudytime"):
            ConfigDetails().retainStudyTime = appConfig.getboolean(section, "retainstudytime")
        if appConfig.hasOption(section, "retainseriesdate"):
            ConfigDetails().retainSeriesDate = appConfig.getboolean(section, "retainseriesdate")
        if appConfig.hasOption(section, "retainseriestime"):
            ConfigDetails().retainSeriesTime = appConfig.getboolean(section, "retainseriestime")
        if appConfig.hasOption(section, "retainstudyseriesdescriptions"):
            ConfigDetails().retainStudySeriesDescriptions = appConfig.getboolean(section, "retainstudyseriesdescriptions")
        if appConfig.hasOption(section, "autortstructmatch"):
            ConfigDetails().autoRTStructMatch = appConfig.getboolean(section, "autortstructmatch")
        if appConfig.hasOption(section, "autortstructref"):
            ConfigDetails().autoRTStructRef = appConfig.getboolean(section, "autortstructref")
        if appConfig.hasOption(section, "downloaddicompatientfoldername"):
            ConfigDetails().downloadDicomPatientFolderName = appConfig.get(section)["downloaddicompatientfoldername"]
        if appConfig.hasOption(section, "downloaddicomstudyfoldername"):
            ConfigDetails().downloadDicomStudyFolderName = appConfig.get(section)["downloaddicomstudyfoldername"]

    section = "AE"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "name"):
            ConfigDetails().rpbAE = appConfig.get(section)["name"]
        if appConfig.hasOption(section, "port"):
            ConfigDetails().rpbAEport = int(appConfig.get(section)["port"])
        if appConfig.hasOption(section, "aetsuffix"):
            ConfigDetails().rpbAETsuffix = appConfig.get(section)["aetsuffix"]
            
        if not ApplicationEntityService().isReady:
            if ConfigDetails().rpbAE is not None and ConfigDetails().rpbAE != "":

                # Consider AET suffix option when creating AE for client
                AET = ConfigDetails().rpbAE

                if ConfigDetails().rpbAETsuffix == "host":
                    AET += str(QtNetwork.QHostInfo.localHostName())
                elif ConfigDetails().rpbAETsuffix == "fqdn":
                    AET += str(QtNetwork.QHostInfo.localHostName()) + "." + str(QtNetwork.QHostInfo.localDomainName())

                ApplicationEntityService().init(
                    AET, 
                    ConfigDetails().rpbAEport
                )

    aeCount = 0
    section = "RemoteAEs"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "count"):
            aeCount = int(appConfig.get(section)["count"])

    for i in range(0, aeCount):
        section = "RemoteAE" + str(i)
        if appConfig.hasSection(section):
            address = ""
            if appConfig.hasOption(section, "address"):
                address = appConfig.get(section)["address"]
            port = -1
            if appConfig.hasOption(section, "port"):
                port = int(appConfig.get(section)["port"])
            aet = ""
            if appConfig.hasOption(section, "aet"):
                aet = appConfig.get(section)["aet"]
                
            ConfigDetails().remoteAEs.append(dict(Address=address, Port=port, AET=aet))

    section = "SanityTests"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "patientgendermatch"):
            ConfigDetails().patientGenderMatch = appConfig.getboolean(section, "patientGenderMatch")
        if appConfig.hasOption(section, "patientdobmatch"):
            ConfigDetails().patientDobMatch = appConfig.getboolean(section, "patientDobMatch")

    section = "General"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "startupupdatecheck"):
            ConfigDetails().startupUpdateCheck = appConfig.getboolean(section, "startupupdatecheck")

    section = "Temp"
    if appConfig.hasSection(section):
        if appConfig.hasOption(section, "isupgrading"):
            ConfigDetails().isUpgrading = appConfig.get(section)["isupgrading"]
        if appConfig.hasOption(section, "upgradefinished"):
            ConfigDetails().upgradeFinished = appConfig.get(section)["upgradefinished"]

####    ##    #######  ##    ## 
 ##   ####   ##     ## ###   ## 
 ##     ##   ##     ## ####  ## 
 ##     ##    #######  ## ## ## 
 ##     ##   ##     ## ##  #### 
 ##     ##   ##     ## ##   ### 
####  ######  #######  ##    ## 

# def translate():
    # """Internationalisation
    # """
    # translator = QtCore.QTranslator()
    # translator.load("qt_ru", QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    # app.installTranslator(translator)

if __name__ == '__main__':
    main()
