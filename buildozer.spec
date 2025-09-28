[app]

# (str) Title of your application
title = Sampleapp

# (str) Package name
package.name = nfsApk

# (str) Package domain (needed for android/ios packaging)
package.domain = org.novfensec

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching
source.include_patterns = images/*.png

# (list) Application versioning
version = 0.1

# (list) Application requirements
requirements = python3,kivy==2.3.1,https://github.com/kivymd/KivyMD/archive/master.zip,exceptiongroup,asynckivy,asyncgui,materialyoucolor,android

# (str) Presplash of the application
presplash.filename = %(source.dir)s/images/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/images/favicon.png

# (list) Supported orientations
orientation = portrait

# (int) Target Android API
android.api = 34

# (int) Minimum API your APK / AAB will support
android.minapi = 23

# (list) Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Automatically accept SDK license agreements (useful for CI/CD)
android.accept_sdk_license = True

# (str) Format to package the app for release/debug
android.release_artifact = aab
android.debug_artifact = apk

# (bool) Enable fullscreen
fullscreen = 0

# (bool) Android backup
android.allow_backup = True

# (str) Python-for-Android branch
p4a.branch = develop

# (str) iOS setup
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/ios-control/ios-deploy
ios.ios_deploy_branch = master
ios.codesign.allowed = false


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Warn if run as root
warn_on_root = 1
