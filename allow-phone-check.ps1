netsh advfirewall firewall delete rule name="FormBharat phone check" | Out-Null
netsh advfirewall firewall add rule name="FormBharat phone check" dir=in action=allow protocol=TCP localport=5002 remoteip=localsubnet profile=any
if ($LASTEXITCODE -ne 0) { exit 1 }
exit 0
