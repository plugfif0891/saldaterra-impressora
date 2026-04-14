[app]
title = Saldaterra Impressora
package.name = saldaterra_impressora
package.domain = com.saldaterra
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,xml
version = 1.1
requirements = python3==3.10.14,kivy==2.3.0,jnius,android,certifi,charset-normalizer,urllib3,idna
orientation = portrait
fullscreen = 0
android.minapi = 23
android.api = 33
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a,armeabi-v7a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,WAKE_LOCK,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,REQUEST_INSTALL_PACKAGES,ACCESS_WIFI_STATE
android.wakelock = True
android.allow_backup = True
android.foreground_service = True
android.foreground_service_type = dataSync
android.accept_sdk_license = True
p4a.branch = release-2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1