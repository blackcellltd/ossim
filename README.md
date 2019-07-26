# USM / OSSIM backup
The script main purpose is to archive Raw Logs from USM Logger to an external storage via SFTP or to a mounted NFS.

The SFTP part is ready.

Usage:

python3 usmbackup.py --log-keep=365 --sftp-host='ip address' --sftp-port='' --sftp-user='username' --sftp-pass='your password' --sftp-identity='set save in path your ftp ssh key' --sftp-dest='set save in path your ftp backup folder' --sftp-only=True

Both password and key based authentication works. Skip the --sftp-pass parameter if you are using public key authenticaion.

--log-keep -> How many days to store locally

The script makes a zip archive from the Raw log files from /var/ossim/logs/, copies over sftp and finally deletes the temporary files and the logs from the original location.

To an NFS/SMB share you can save and restore (both USM and OSSIM):

 - Alarms
 - Configuration backups

TODO:

- Restore from SFTP
- Option to save locally or sftp or both

Dependencies:

python 3
pysftp
