#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  License:
#
#  Copyright (c) 2019 Istvan Szvetlik @ Black Cell Ltd.
#  All rights reserved.
#
#  This package is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; version 2 dated June, 1991.
#  You may not use, modify or distribute this program under any other version
#  of the GNU General Public License.
#
#  This package is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this package; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston,
#  MA  02110-1301  USA
#
#
#  On Debian GNU/Linux systems, the complete text of the GNU General
#  Public License can be found in `/usr/share/common-licenses/GPL-2'.
#
#  Otherwise you can read it here: http://www.gnu.org/licenses/gpl-2.0.txt
#


import argparse
from glob import glob
from datetime import datetime, timedelta
import os, os.path
import shutil
import pwd
import pysftp
from shutil import copyfile
import shutil
import zipfile
import hashlib
import sys

#import stat
#from joblib import Parallel, delayed


parser = argparse.ArgumentParser(description='USM backup script')
today = datetime.strftime(datetime.now(), "%Y-%m-%d")
defstart = datetime.strftime(datetime.now().replace(year = datetime.now().year - 3), "%Y-%m-%d")

#TODO:
# - Restore from SFTP

parser.add_argument('--start', type = bool, default = False, help = 'Begin this is program')
parser.add_argument('--alarm-keep', type = int, default = 60, help = 'Keep this many previous versions of the alarm backups (default: 60)')
parser.add_argument('--alarm-dest', type = str, default = "/backup/alarms", help = 'Location of the alarm backups (default: /backup/alarms)')
parser.add_argument('--config-dest', type = str, default = "/backup/config", help = 'External config backup location (default: /backup/config)')
parser.add_argument('--config-source', type = str, default = "/var/alienvault/backup", help = 'Internal config backup location (default: /var/alienvault/backup)')

parser.add_argument('--log-keep', type = int, default = 365, help = 'Archive logs older than this many days (default: 365 days)')
parser.add_argument('--log-dest', type = str, default = "/home/backup", help = 'Local TEMP! foler for zipped logs (default: /home/backup)')	# local backup and tmp folder!!!
parser.add_argument('--log-source', type = str, default = "/var/ossim/logs", help = 'Location of the logs (default: /var/ossim/logs)')      # /var/ossim/logs - source !!!!

parser.add_argument('--owner', type = str, default = "avserver", help = 'Owner user of the backed up files (default: avserver)')

parser.add_argument('--stopservices', type = bool, default = False, help = 'Whether or not to stop services while backing up / restoring (default: False)')

parser.add_argument('--backup', dest = 'backup', default = True, action = 'store_true', help = "Back up data (default)")
parser.add_argument('--restore', dest = 'backup', action = 'store_false', help = "Restore data")

parser.add_argument('--log-start', type = str, default = defstart, help = 'First log to restore (default: ' + defstart + ')')
parser.add_argument('--log-end', type = str, default = today, help = 'Last log to restore (default: ' + today + ')')

parser.add_argument('--sftp-only', type = bool, default = True, help = 'Whether or not to keep the local backup (default: True)')
parser.add_argument('--sftp-host', type = str, default = "", help = 'SFTP server IP address')												# ftp server IP
parser.add_argument('--sftp-port', type = int, default = "22", help = 'SFTP server PORT')
parser.add_argument('--sftp-user', type = str, default = "", help = 'Username for the SFTP server (default: root)')
parser.add_argument('--sftp-pass', type = str, default = "", help = 'Password for the SFTP server')
parser.add_argument('--sftp-identity', type = str, default = "", help = 'Private key for the SFTP server')

parser.add_argument('--sftp', dest = 'sftp', default = True, action = 'store_true', help = "Use SFTP")										# save space: local or sftp
parser.add_argument('--no-sftp', dest = 'sftp', action = 'store_false', help = "Do not use SFTP")

parser.add_argument('--sftp-dest', type = str, default = "", help = 'remote directory')														# ftp public directory


parser.add_argument('--sftpid', dest = 'sftpid', default = False, action = 'store_true', help = "Use a private key for SFTP authentication")
parser.add_argument('--sftppass', dest = 'sftpid', action = 'store_false', help = "Use a password for SFTP authentication")

parser.add_argument('--config', dest = 'config', default = True, action = 'store_true', help = "Back up / restore configuration backups (default)")
parser.add_argument('--no-config', dest = 'config', action = 'store_false', help = "Do not back up / restore configuration backups")

parser.add_argument('--log', dest = 'log', default = True, action = 'store_true', help = "Back up / restore logs (default)")
parser.add_argument('--no-log', dest = 'log', action = 'store_false', help = "Do not back up / restore logs")

parser.add_argument('--alarm', dest = 'alarm', default = True, action = 'store_true', help = "Back up / restore alarms (default)")
parser.add_argument('--no-alarm', dest = 'alarm', action = 'store_false', help = "Do not back up / restore alarms")


args = parser.parse_args()


def print_help():
	print("\n");
	print("[INFORMATION]", "How to start this program:\n")
	print("[INFO]","SFTP and/or local backup:\n");
	print(" python3 usmbackup.py --log-keep=365 --sftp-host='ip address' --sftp-user='username' --sftp-pass='your password' --sftp-identity='set save in path your ftp ssh key' --sftp-dest='set save in path your ftp backup folder' --sftp-only=True \n")
	print(" * The --sftp-only : Whether or not to keep the local backup (default: True)");
	print("\n");
	print("[INFO]","Just local backup:\n")
	print(" python3 usmbackup.py --log-keep=365 --no-sftp\n");
	print(" * The default directory: /home/backup or use --log-dest='your directory'");
	print("\n");
	print("[INFO]", "Backup restore:\n");
	print(" python3 usmbackup.py --restore\n");
	print(" * The first log to restore default this year minus three years and last log is today\n");
	print(" * The default directory: /home/backup or use --log-dest='your directory'\n");
	print(" * Your manual set time interval: \n");
	print(" python3 usmbackup.py --restore --log-start='2017-06-01' --log-end='2018-06-01'")
	print("\n")
	# print("All parameter information: \n");
	# print(args);

def ssh_gencmd():
	global args
	cmd = ""
	if args.sftpid: cmd = 'ssh -i "' + args.sftp_identity + '" ' + args.sftp_user + "@" + args.sftp_host + " "
	else: cmd += 'sshpass -p "' + args.sftp_pass + '" ssh ' + args.sftp_user + "@" + args.sftp_host + " "

def sftp_gencmd(_from, _to, remote = "dest"):
	global args
	if args.sftpid:
		cmd = 'sftp -i "' + args.sftp_identity + '" ' + args.sftp_user + "@" + args.sftp_host
	else:
		# cmd = 'sshpass -p "' + args.sftp_pass + '" sftp ' + args.sftp_user + "@" + args.sftp_host				# sshpass - telepiteni szukseges, de nem ajanlott, serulekeny

		cmd = "NO"

		options = pysftp.CnOpts();
		options.hostkeys = None; 
		#options.hostkeys.load(args.sftp_identity);

		try:
			with pysftp.Connection(host=args.sftp_host, username=args.sftp_user, password=args.sftp_pass, cnopts=options) as sftp:  # pysftp - pip install pysftp
				print ("Connection succesfully established ... ");

				print("from: ", _from, " to: ", _to);

				if os.path.isfile(_from):
					sftp.put(_from, _to);
				else:
					raise IOError('Could not find localFile %s' %_from)


				sftp.close()
				# connection closed automatically at the end of the with-block

				cmd = "succesfully";
		except Exception as e:
				print("Failed:", str(e))

	#cmd = ('echo \'%s -r "%s" "%s"\' | ' % ("get" if remote == "src" else "put", _from, _to)) + cmd
	#print("[+]", cmd)
	return cmd

def ssh_chown(path):
	global args
	cmd = ssh_gencmd() + 'chown -R ' + args.owner + ":" + args.owner + ' "' + path + '"'
	if os.system(cmd): raise ValueError("Failed to connect to the remote server")

def file_move(_from, _to, remote = "dest"):
	global args
	# If sftp is "true"
	if args.sftp:
		cmd = sftp_gencmd(_from, _to, remote)

		#print(cmd + "finished!");
		#if os.system(cmd): raise ValueError("Failed to connect to the SFTP server")
		#if remote == "src": rchown(_to)
		"""
		if remote == "dest":
			shutil.remove(_from)
			ssh_chown(_to)
		else:
			print("...")
			#ssh_gencmd() + rm -rf "_from"
			#rchown(_to)
		"""
	else:
		print("else, def(file move)");
		#shutil.move(_from, _to)
		#rchown(_to)

def createpath(root, dirs):
	os.chdir(root)
	dirs = list(dirs)
	path = []
	while len(dirs):
		path.append(dirs.pop(0))
		try: os.mkdir("/".join(path))
		except FileExistsError: pass

def _format(log): return (str(log[0]), str(log[1]), str(log[2]))

def clean(root):
	print("Removing empty log directories in", root)
	def _clean(path):
		if os.path.isdir(path) and not len([_ for _ in os.listdir(path) if _ not in [".", ".."]]): os.rmdir(path)
	for path in glob(root + "/*/*/*"): _clean(path)
	for path in glob(root + "/*/*"): _clean(path)
	for path in glob(root + "/*"): _clean(path)

def rchown(root):
	global args
	print("Recursively changing ownership of", root, "to", args.owner)
	owner = pwd.getpwnam(args.owner)
	os.chown(root, owner.pw_uid, owner.pw_gid)
	if os.path.isdir(root):
		for _root, dirs, files in os.walk(root):
			for dir in dirs: os.chown(os.path.join(_root, dir), owner.pw_uid, owner.pw_gid)
			for file in files: os.chown(os.path.join(_root, file), owner.pw_uid, owner.pw_gid)

def backup_log():
	global args
	diff = timedelta(days = args.log_keep)
	last = datetime.now() - diff

	logs = []

	for dir in glob(args.log_source+"/*/*/*"):
		path = dir[len(args.log_source) + 1:];
		#print(len(dir), " : ",dir[len(args.log_source) + 1:]);
		#print(path);

		try:
			_year, _month, _day = path.split("/");
			year, month, day = int(_year), int(_month), int(_day);
			#print (year, month, day);
		except: continue
		
		timestamp = datetime(year = year, month = month, day = day)
		
		#print(timestamp, " < ", last);
		if timestamp < last:
			logs.append((_year, _month, _day));
	print("\n");
	print("[INFORMATION]", "Matching logs for the specified time period:", len(logs));
	print(" last: ", last, " dif: ", diff, " DT: ", datetime.now());
	print("\n");
	if len(logs) > 0:
			# If sftp is "true"
			if args.sftp:

				# *** FTP and local BACKUP *** #
				try:
					SFTPCopyOK = True;
					#options = pysftp.CnOpts();
					#options.hostkeys = None;

					#options.hostkeys.load(args.sftp_identity);
					#remove sftp_pass if you're using only public key auth
					with pysftp.Connection(host=args.sftp_host, username=args.sftp_user, password=args.sftp_pass,  port=args.sftp_port, private_key=args.sftp_identity) as sftp:  # pysftp - pip install pysftp
						print("\n");
						print("[OK]","FTP Connection succesfully stablished ... ");
						print("[OK]","The backup is in progress...");
						print("\n");
						try:
							for log in logs:

								path = "/".join(_format(log));
								src_dir = args.log_source + "/" + path;
								dest_dir = args.log_dest + "/" + path;

								print("SRC: ", src_dir, " DEST: ", dest_dir);
								# *** LOCAL BACKUP *** #
								shutil.make_archive(dest_dir, 'zip', src_dir);

								# *** FTP BACKUP *** #
								if (sftp.getcwd() != args.sftp_dest):
									try:
										sftp.chdir(args.sftp_dest);
									except IOError as e:
										print("...");

								print("FTP directory: ",sftp.getcwd());
								# year, month, day  - parameters #
								# print("0: ", str(log[0]), " 1: ", str(log[1]), " 2: ", str(log[2]));
								if sftp.exists(str(log[0]) + '/' + str(log[1])):  							# Test if remote_path exists
									print("exists ftp directory: ", str(log[0]) + '/' + str(log[1]));

									sftp.chmod(str(log[0]), 777);
									sftp.chmod(str(log[0]) + '/' + str(log[1]), 777);

									sftp.put(dest_dir+".zip", str(log[0]) + '/' + str(log[1]) + '/' + str(log[2])+".zip");
									print("[OK]"," backup zip");
								else:
									print("create ftp directory: ", str(log[0]) + '/' + str(log[1]));
									sftp.makedirs(str(log[0]) + '/' + str(log[1]));  # Create remote_path
									sftp.chmod(str(log[0]), 777);
									sftp.chmod(str(log[0]) + '/' + str(log[1]), 777);
									sftp.put(dest_dir+".zip", str(log[0]) + '/' + str(log[1]) + '/' + str(log[2])+".zip");
									print("[OK]", " backup zip");

						except Exception as e:
							print("Error:", str(e))
							SFTPCopyOK = False;
							print("[ERROR] The backup is not finished");

					sftp.close()  # connection closed automatically at the end of the with-block

					print("\n");
					print("Close ftp connect.");
					print("The original journal delete is in progress...");
					if SFTPCopyOK:
						for log in logs:
							src_dir = args.log_source + "/" + str(log[0]) + "/" + str(log[1]) + "/" + str(log[2]);
							#print("DELETE: ",src_dir);
							try:
								if os.path.exists(src_dir):
									shutil.rmtree(src_dir);
								else:
									print("It does not exist: ",src_dir);
							except Exception as e:
								print("DELETE Error:", str(e));

						if args.sftp_only:
							shutil.rmtree(args.log_dest);
						print("\n");
						print("[OK]"," The sftp backup was successfully completed");
						print("\n");
					else:
						print("\n");
						print("[ERROR]", " The sftp backup was not completed");
						print("\n");
				except Exception as e:
					print("Failed backup:", str(e))

			else:
				print("[OK]","The local backup is in progress...");
				for log in logs:
					try:
						path = "/".join(_format(log));
						src_dir = args.log_source + "/" + path;
						dest_dir = args.log_dest + "/" + path;
						print("SRC: ", src_dir, " DEST: ", dest_dir);
						shutil.make_archive(dest_dir, 'zip', src_dir);
						print("ZIP: ",dest_dir);
					except Exception as e:
						print("Error:", str(e))
				print("[OK]"," The local backup is finished");

				print("The original journal delete is in progress...");
				for log in logs:
					src_dir = args.log_source + "/" + str(log[0]) + "/" + str(log[1]) + "/" + str(log[2]);
					# print("DELETE: ",src_dir);
					try:
						if os.path.exists(src_dir):
							shutil.rmtree(src_dir);
						else:
							print("It does not exist: ", src_dir);
					except Exception as e:
						print("DELETE Error:", str(e));
				print("\n");
				print("[OK]", " The backup was successfully completed");
				print("\n");
	else:
		print("[INFORMATION]","no backup");
	 #clean(args.log_source);


def restore_log():
	global args
	start = datetime.strptime(args.log_start, "%Y-%m-%d")
	end = datetime.strptime(args.log_end, "%Y-%m-%d")

	logs = []
	#print("start time: ",start, " End time: ",end);
	for dir in glob(args.log_dest + "/*/*/*"):
		path = dir[len(args.log_dest) + 1:]
		#print("path: ",path);
		try:
			_year, _month, _day = path.split("/");
			year, month, day = int(_year), int(_month), int(_day.replace('.zip',''));
		except: continue

		timestamp = datetime(year = year, month = month, day = day)

		#print("Start: ",start, " < ","Tstamp: ",timestamp," < ", "End: ",end);

		if start <= timestamp <= end:
			logs.append((_year, _month, _day))

	print("\n","[INFORMATION]","Matching logs for the specified time period:", len(logs));

	for log in logs:
		path = "/".join(_format(log));
		src_dir = args.log_dest + "/" + path;
		log_source = (args.log_source + "/" + path).replace('.zip','');

		zipfilePath = (src_dir);
		zip = zipfile.ZipFile(zipfilePath);
		test_zip = zip.testzip();
		if test_zip is not None:
			print("Bad file in zip: %s" %test_zip, "source: ",src_dir);
			#sys.exit(1)
		else:
			print("\nZip file is good, restore: ",log_source);
			#sys.exit(0)
			zip.extractall(log_source);
		zip.close();
		print("\n");
		print("[OK]", " The restore was successfully completed");
		print("\n");
		# old:
		#path = "/".join(_format(log))
		#src_dir, dest_dir = args.log_dest + "/" + path, args.log_source + "/" + path

		#print("Restoring", path)
		#if os.path.isdir(dest_dir): raise FileExistsError()
		#createpath(args.log_source, _format(log)[:-1])
		#file_move(src_dir, dest_dir, remote = "src")

	#clean(args.log_dest)

def backup_config():
	global args
	filelist = glob(args.config_source + "/configuration_*.tar.gz")
	newest = ""
	for file in filelist:
		timestamp = datetime.fromtimestamp(int(file.split("_")[-1].split(".", 1)[0]))
		if newest == "":
			newest, newest_ts = file, timestamp
			continue
		if newest_ts < timestamp: newest, newest_ts = file, timestamp

	for file in filelist:
		if file == newest:
			print("Skipping", file)
			continue
		print("Backing up", file)
		filename = file.split("/")[-1]
		dest_file = args.config_dest + "/" + filename
		if os.path.exists(dest_file): raise FileExistsError()
		file_move(file, dest_file)

def restore_config():
	global args
	for file in glob(args.config_dest + "/configuration_*.tar.gz"):
		print("Restoring", file)
		filename = file.split("/")[-1]
		dest_file = args.config_source + "/" + filename
		if os.path.exists(dest_file): raise FileExistsError()
		file_move(file, dest_file, remote = "src")

def backup_alarm():
	global args

	while 1:
		filelist = glob(args.alarm_dest + "/*.sql.gz")
		if len(filelist) < args.alarm_keep: break
		oldest = ""
		for file in filelist:
			timestamp = datetime.fromtimestamp(int(file.split("/")[-1].split(".", 1)[0]))
			if oldest == "":
				oldest, oldest_ts = file, timestamp
				continue
			if oldest_ts > timestamp: oldest, oldest_ts = file, timestamp
		print("Removing", oldest)
		os.unlink(oldest)

	print("Backing up alarms")
	if os.system("mysqldump -p`grep ^pass /etc/ossim/ossim_setup.conf | sed 's/pass=//'` --no-autocommit --single-transaction alienvault event extra_data idm_data otx_data backlog_event backlog alarm component_tags alarm_ctxs alarm_nets alarm_hosts | pigz >\"" + args.alarm_dest + "/`date +%s`.sql.gz\""): print("Backup failed")
	else: print("Backup completed")

def restore_alarm():
	global args

	newest = ""
	for file in glob(args.alarm_dest + "/*.sql.gz"):
		timestamp = datetime.fromtimestamp(int(file.split("/")[-1].split(".", 1)[0]))
		if newest == "":
			newest, newest_ts = file, timestamp
			continue
		if newest_ts < timestamp: newest, newest_ts = file, timestamp

	if not os.path.isfile(newest): raise FileNotFoundError()
	print("Restoring", file)
	if os.system('zcat "' + file + '" | ossim-db'): print("Restore failed")
	else: print("Restore completed")


if (len(sys.argv) < 2):
	print_help();
else:
	if (args.backup):
		backup_log();
	if(args.backup == False):
		restore_log();

#if args.backup:
	#if args.log: backup_log()
	#if args.config: backup_config()
	#if args.alarm: backup_alarm()
#else:
	#if args.log: restore_log()
	#if args.config: restore_config()
	#if args.alarm: restore_alarm()
