[app]
title = 结绳·图修
package.name = knotphotoeditor
package.domain = org.knotphoto
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,ttf
version = 1.0
requirements = python3,kivy,pillow,opencv-python-headless,pytesseract,numpy
orientation = portrait
osx.package_name = KnotPhotoEditor
android.api = 34
android.minapi = 21
android.ndk_api = 21
android.sdk_path = /opt/android-sdk
android.ndk_path = /usr/lib/android-sdk/ndk/26.3.11579264/android-ndk-r26c
android.arch = arm64-v8a
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET
android.wakelock = True
android.accept_sdk_license = True
[buildozer]
log_level = 2
warn_on_root = 0
