# Nagios monitoring for Bacula

## Service checks

If needed, download the [check_service.sh](https://github.com/jonschipp/nagios-plugins/blob/master/check_service.sh) Nagios plugin and place it in `/usr/lib/nagios/plugins/`.

Copy the Nagios NRPE configurion needed.
```
cp nrpe.d/bacula_services.cfg /etc/nagios/nrpe.d/
service nagios-nrpe-server restart
```

Allow nagios user to perform service check as root. 
Add following line to `/etc/sudoers`:
```
nagios ALL=(root) NOPASSWD:/usr/lib/nagios/plugins/check_service.sh
```

Now add the configuration found in `nagios.d/service.cfg` to your Nagios configuration. Of course only add the services needed for that host (fd/sd/director).

## Jobs

The script `bacula_nagios.py` uses the Bacula database the check wether all jobs have been succesfully completed in the last 24 hours and have an expected size. 

You could run the script directly from the Nagios host but I suggest using nrpe to run it from the Bacula host so you won't have to open up MySQL to the network. 

You might need to install the [Python MySQL connector](https://dev.mysql.com/downloads/connector/python/).

Create database user:
```
GRANT SELECT ON bacula.* TO 'nagiosscript'@'localhost' IDENTIFIED BY 'DBPASSWORD';
```

Add active column to Client table so you the check knows which clients are deliberatle non active (anymore).
```
ALTER TABLE Client ADD Active TINYINT(1) DEFAULT 1
```

Place script
Make it executable
```
cp bacula_nagios.py /etc/nagios-plugins/ && chmod +x /etc/nagios-plugins/bacula_nagios.py 
```

Copy the Nagios NRPE configurion needed.
```
cp nrpe.d/bacula_jobs.cfg /etc/nagios/nrpe.d/
service nagios-nrpe-server restart
```

Now add the configuration found in `nagios.d/jobs.cfg` to your Nagios configuration.
