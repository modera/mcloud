#!/usr/bin/env python
import os,sys,urllib2,platform,re

# check if root with geteuid
if os.geteuid() != 0:
    print "Please re-run this script with root privileges, i.e. 'sudo ./install.py'\n"
    sys.exit()

# check if running on Mac
mac = (platform.system() == 'Darwin')

# check if all necessary system utilities are present
if mac:
    exitcode = os.system("which clear diskutil grep gunzip dd")
else:
    exitcode = os.system("which clear fdisk grep umount mount cut gunzip dd blockdev")
if exitcode != 0:
    print "Error: your operating system does not include all the necessary utilities to continue."
    if mac:
        print "Utilities necessery: clear diskutil grep gunzip dd"
    else:
        print "Utilities necessery: clear fdisk grep umount mount cut gunzip dd blockdev"
    print "Please install them."
    sys.exit()

os.system("clear")
print "Raspbmc installer for Linux and OS X"
print "http://raspbmc.com"
print "----------------------------------------"

# yes/no prompt adapted from http://code.activestate.com/recipes/577058-query-yesno/
def query_yes_no(question, default="yes"):
    valid = {"yes":"yes", "y":"yes", "ye":"yes", "no":"no", "n":"no"}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)
    while 1:
        print question + prompt
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            print "Please respond with 'yes' or 'no' (or 'y' or 'n').\n"

def chunk_report(bytes_so_far, chunk_size, total_size):
    percent = float(bytes_so_far) / total_size
    percent = round(percent*100, 2)
    sys.stdout.write("Downloaded %0.2f of %0.2f MiB (%0.2f%%)\r" % 
        (float(bytes_so_far)/1048576, float(total_size)/1048576, percent))
    if bytes_so_far >= total_size:
        sys.stdout.write('\n')

def chunk_read(response, file, chunk_size, report_hook):
    total_size = response.info().getheader('Content-Length').strip()
    total_size = int(total_size)
    bytes_so_far = 0
    while 1:
        chunk = response.read(chunk_size)
        file.write(chunk)
        bytes_so_far += len(chunk)
        if not chunk:
            break
        if report_hook:
            report_hook(bytes_so_far, chunk_size, total_size)
    return bytes_so_far

def download(url):
    print "Downloading, please be patient..."
    dl = urllib2.urlopen(url)
    dlFile = open('installer.img.gz', 'w')
    chunk_read(dl, dlFile, 8192, chunk_report)
    #dlFile.write(dl.read())
    dlFile.close()

def deviceinput():
    # they must know the risks!
    verified = "no"
    raw_input("Please ensure you've inserted your SD card, and press Enter to continue.")
    while verified is not "yes":
        print ""
        if mac:
            print "Enter the 'IDENTIFIER' of the device you would like imaged:"
        else:
            print "Enter the 'Disk' you would like imaged, from the following list:"
        listdevices()
        print ""
        if mac:
            device = raw_input("Enter your choice here (e.g. 'disk1', 'disk2'): ")
        else:
            device = raw_input("Enter your choice here (e.g. 'mmcblk0' or 'sdd'): ")
        # Add /dev/ to device if not entered
        if not device.startswith("/dev/"):
            device = "/dev/" + device
        if os.path.exists(device) == True:
            print "It is your own responsibility to ensure there is no data loss! Please backup your system before imaging"
            print "You should also ensure you agree with the Raspbmc License Agreeement"
            cont = query_yes_no("Are you sure you want to install Raspbmc to '\033[31m" + device + "\033[0m' and accept the license agreement?", "no")
            if cont == "no":
                sys.exit()
            else:
                verified = "yes"
        else:
            print "Device doesn't exist"
            # and thus we are not 'verified'
            verified = "no"
    return device

def listdevices():
    if mac:
        print "   #:                       TYPE NAME                    SIZE       IDENTIFIER"
        os.system('diskutil list | grep "0:"')
    else:
        os.system('fdisk -l | grep -E "Disk /dev/"')

def unmount(drive): # unmounts drive
    print "Unmounting all partitions..."
    if mac:
        exitcode = os.system("diskutil unmountDisk " + drive)
    else:
        # check if partitions are mounted; if so, unmount
        if os.system("mount | grep " + drive + " > /dev/null") == 0:
            exitcode = os.system("umount `mount | grep " + drive + " | cut -f1 -d ' '`")
        else:
            # partitions were not mounted; must pass error check
            exitcode = 0
    if exitcode != 0:
        print 'Error: the drive couldn\'t be unmounted, exiting...'
        sys.exit()

def mount(drive): # mounts drive to mount_raspbmc/
    print "Mounting the drive for post-installation settings"
    if mac:
        os.system("diskutil mount -mountPoint mount_raspbmc/ " + drive + "s1")
    else:
        if os.path.exists(drive + "p1"):
            drive = drive + "p"
        os.system("mount " + drive + "1  mount_raspbmc/")

def imagedevice(drive, imagefile):
    print ""
    unmount(drive)
    # use the system's built in imaging and extraction facilities
    print "Please wait while Raspbmc is installed to your SD card..."
    print "This may take some time and no progress will be reported until it has finished."
    if mac:
        os.system("gunzip -c " + imagefile + " | dd of=" + drive + " bs=1m")
    else:
        os.system("gunzip -c " + imagefile + " | dd of=" + drive + " bs=1M")
        # Linux kernel must reload the partition table
        os.system("blockdev --rereadpt " + drive)
    print "Installation complete."

# Post-install settings
def settings(drive):
    if mac:
        unmount(drive)
    if os.path.exists("mount_raspbmc"):
        os.rmdir("mount_raspbmc")
    os.mkdir("mount_raspbmc")
    mount(drive)
    if os.path.exists("mount_raspbmc/start_x.elf"):
        # prompt for USB/NFS setup
        usbnfs = query_yes_no("Would you like to install Raspbmc to a USB stick or an NFS share?\nNote that this still requires an SD card for booting.", "no")
        if usbnfs == "yes":
            print "Please choose the install type:"
            print "1. USB install"
            print "2. NFS install"
            installchoice = raw_input()
            while installchoice != "1" and installchoice != "2":
                print "Please specify a valid option"
                installchoice = raw_input()
            if installchoice == "1":
                usb = open("mount_raspbmc/usb", "w")
                usb.close()
            elif installchoice == "2":
                nfsip = raw_input("NFS server IP Adress (e.g. '192.168.1.100'): ")
                nfspath = raw_input("NFS share path (e.g. '/path/to/nfs/share'): ")
                nfs = open("mount_raspbmc/nfs", "w")
                nfs.write(nfsip + ":" + nfspath + "\n")
                nfs.close()
        # prompt for network setup
        inet = query_yes_no("Would you like to configure networking manually? This is useful if you are configuring WiFi or a non-DHCP network", "no")
        if inet == "yes":
            print "Please choose the network type you would like to configure:"
            print "1. Wired networking, non-DHCP"
            print "2. Wireless networking"
            inetchoice = raw_input()
            while inetchoice != "1" and inetchoice != "2":
                print "Please specify a valid option"
                inetchoice = raw_input()
            if inetchoice == "1":
                mode = "0"
                dhcp = "false"
                ip = raw_input("IP Address (e.g. '192.168.101'): ")
                subnet = raw_input("Subnet Mask (e.g. '255.255.255.0'): ")
                dns = raw_input("DNS Server (e.g. '192.168.1.1'): ")
                gateway = raw_input("Default Gateway (e.g. '192.168.1.1'): ")
                # generic settings
                wifidhcp = "true"
                wifiip = "192.168.1.101"
                wifisubnet = "255.255.255.0"
                wifidns = "192.168.1.1"
                wifigateway = "192.168.1.1"
                ssid = "raspbmc"
                keytype = "1"
                key = "password"
                adhoc = "false"
                enable5g = "false"
            elif inetchoice == "2":
                mode = "1"
                wifidhcp = query_yes_no("Use DHCP?", "yes")  
                if wifidhcp == "no":
                    wifidhcp = "false"
                    wifiip = raw_input("IP Address (e.g. '192.168.101'): ")
                    wifisubnet = raw_input("Subnet Mask (e.g. '255.255.255.0'): ")
                    wifidns = raw_input("DNS Server (e.g. '192.168.1.1'): ")
                    wifigateway = raw_input("Default Gateway (e.g. '192.168.1.1'): ")
                else:
                    wifidhcp = "true"
                    # generic settings
                    wifiip = "192.168.1.101"
                    wifisubnet = "255.255.255.0"
                    wifidns = "192.168.1.1"
                    wifigateway = "192.168.1.1"
                # generic ethernet settings
                dhcp =  "true"
                ip = "192.168.1.101"
                subnet = "255.255.255.0"
                dns = "192.168.1.1"
                gateway = "192.168.1.1"
                # custom options
                adhoc_yn = query_yes_no("Enable ad-hoc networking?", "no")
                if adhoc_yn == "yes":
                    adhoc = "true"
                else:
                    adhoc = "false"
                enable5g_yn = query_yes_no("Enable 5Ghz only?", "no")
                if enable5g_yn == "yes":
                    enable5g = "true"
                else:
                    enable5g = "false"
                ssid = raw_input("Please enter SSID (e.g. 'raspbmc_wifi'): ")
                print "Please enter encryption type"
                print "0. No encryption"
                print "1. WEP Open Key"
                print "2. WEP Shared Key"
                print "3. WEP Dynamic Key"
                print "4. WPA/WPA2"
                keytype = raw_input()
                if keytype != "0":
                    key = raw_input("Please enter encryption key (e.g. 'password'): ")
                else:
                    key = "password"
            settings = open("mount_raspbmc/settings.xml", "w")
            settings.write("<settings>\n")
            # ethernet settings
            settings.write("  <setting id=\"nm.mode\" value=\"" + mode + "\" />\n")
            settings.write("  <setting id=\"nm.dhcp\" value=\"" + dhcp + "\" />\n")
            settings.write("  <setting id=\"nm.address\" value=\"" + ip + "\" />\n")
            settings.write("  <setting id=\"nm.netmask\" value=\"" + subnet + "\" />\n")
            settings.write("  <setting id=\"nm.dns\" value=\"" + dns + "\" />\n")
            settings.write("  <setting id=\"nm.gateway\" value=\"" + gateway + "\" />\n")
            settings.write("  <setting id=\"nm.force_update\" value=\"false\" />\n")
            settings.write("  <setting id=\"nm.uid.enable\" value=\"true\" />\n")
            settings.write("  <setting id=\"nm.search\" value=\"local\" />\n")		     
            # wifi settings
            settings.write("  <setting id=\"nm.wifi.dhcp\" value=\"" + wifidhcp + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.address\" value=\"" + wifiip + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.netmask\" value=\"" + wifisubnet + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.dns\" value=\"" + wifidns + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.gateway\" value=\"" + wifigateway + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.ssid\" value=\"" + ssid + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.security\" value=\"" + keytype + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.key\" value=\"" + key + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.adhoc\" value=\"" + adhoc + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.5GOnly\" value=\"" + enable5g + "\" />\n")
            settings.write("  <setting id=\"nm.wifi.search\" value=\"local\" />\n")
            settings.write("</settings>")
            settings.close()
        unmount(drive)
    else:
        print "Additional configuration such as USB/NFS and networking \033[31mnot supported\033[0m as the installer could not mount a FAT32 filesystem"
    if os.path.exists("mount_raspbmc"):
    	os.rmdir("mount_raspbmc")

def raspbmcinstaller():
    # configure the device to image
    disk = deviceinput()
    # should downloading and extraction be done?
    redl = "" # so that redl == "yes" doesn't throw an error
    if os.path.exists("installer.img.gz"):
        redl = query_yes_no("It appears that the Raspbmc installation image has already been downloaded. Would you like to re-download it?", "no")
    if redl == "yes" or not os.path.exists("installer.img.gz"):
        # call the dl    
        download("http://download.raspbmc.com/downloads/bin/ramdistribution/installer.img.gz")
    # now we can image
    if mac:
        regex = re.compile('/dev/r?(disk[0-9]+?)')
        try:
            disk = re.sub('r?disk', 'rdisk', regex.search(disk).group(0))
        except:
            print "Malformed disk specification -> ", disk
            sys.exit()
    imagedevice(disk, "installer.img.gz")
    # post-install options, if supported by os
    postinstall = query_yes_no("Would you like to setup your post-installation settings [ADVANCED]?", "no")
    if postinstall == "yes":
        settings(disk)
    print ""
    print "Raspbmc is now ready to finish setup on your Pi, please insert the SD card with an active internet connection"
    print ""

raspbmcinstaller()
