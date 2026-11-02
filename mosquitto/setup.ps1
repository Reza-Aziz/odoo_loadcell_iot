# Generate sertifikat self-signed + password MQTT. Jalankan sekali dari folder ini:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = 'Stop'

$dir   = $PSScriptRoot
$certs = Join-Path $dir 'certs'
$conf  = Join-Path $dir 'config'
New-Item -ItemType Directory -Force $certs, $conf | Out-Null

$crtPath = Join-Path $certs 'server.crt'
if (Test-Path $crtPath) {
    Write-Host "certs/server.crt sudah ada, dilewati (hapus manual kalau mau regenerate)."
} else {
    $lanIp = (Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -ne $null } |
        Select-Object -First 1).IPv4Address.IPAddress
    $san = "DNS:localhost,IP:127.0.0.1"
    if ($lanIp) { $san += ",IP:$lanIp" }

    docker run --rm -v "${certs}:/certs" alpine/openssl req -x509 -newkey rsa:2048 -nodes `
        -days 3650 `
        -keyout /certs/server.key -out /certs/server.crt `
        -subj "/C=ID/O=ForgeTrack/CN=mosquitto" `
        -addext "subjectAltName=$san"
    if ($LASTEXITCODE -ne 0) { throw "gagal generate certificate" }
    Write-Host "cert dibuat, SAN: $san"
}

$passwdPath = Join-Path $conf 'passwd'
if (Test-Path $passwdPath) {
    Write-Host "config/passwd sudah ada, dilewati."
} else {
    docker run --rm -v "${conf}:/cfg" eclipse-mosquitto:2 `
        mosquitto_passwd -b -c /cfg/passwd iot_user iot_pass
    if ($LASTEXITCODE -ne 0) { throw "gagal membuat password file" }
    Write-Host "user MQTT dibuat: iot_user / iot_pass"
}

# Mosquitto jalan sebagai uid 1883, sedangkan file dari container generator
# dibuat 0600 root -> broker gagal baca. Bind mount Windows mewarisi mode ini.
docker run --rm -v "${dir}:/m" eclipse-mosquitto:2 chmod 644 /m/config/passwd /m/certs/server.key
