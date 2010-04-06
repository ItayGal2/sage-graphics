Summary: SAGE Scalable Adaptive Graphics Environment
Name: sage-graphics
Version: 3.2
Release: 171
Source0: %{name}-%{version}.tar.gz
License: BSD
Group: Graphics/Streaming
Provides: sage  
BuildRoot: %{_tmppath}/%{name}-%{version}-root 

%if 0%{?suse_version} > 1120
BuildRequires: gcc-c++, libSDL-devel, libreadline6, readline-devel, freeglut, freeglut-devel, ImageMagick, ImageMagick-devel, libMagickWand2, libjpeg-devel
Requires: libjpeg, libSDL-1_2-0
%endif
%if 0%{?suse_version} == 1120
BuildRequires: gcc-c++, libSDL-1_2-0, libSDL-devel, libreadline6, readline-devel, libncurses6, ncurses-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, libMagickWand2
%endif
%if 0%{?suse_version} == 1110
BuildRequires: gcc, gcc43, gcc-c++, gcc43-c++, SDL, SDL-devel, libreadline5, libncurses5, readline-devel, ncurses-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel, libMagickWand1
%endif
%if 0%{?suse_version} == 1100
BuildRequires: gcc, gcc43, gcc-c++, gcc43-c++, SDL, SDL-devel, libreadline5, libncurses5, readline-devel, ncurses-devel,freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel, libMagickWand1
%endif
%if 0%{?centos_version} > 500
BuildRequires: gcc, gcc-c++, SDL, SDL-devel, readline, readline-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel, libXmu, libXmu-devel, libXi, libXi-devel
%endif
%if 0%{?fedora} == 10
BuildRequires: gcc, gcc-c++, SDL, SDL-devel, readline, readline-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel, libXmu, libXmu-devel, libXi, libXi-devel
%endif
%if 0%{?fedora} == 11
BuildRequires: gcc, gcc-c++, SDL, SDL-devel, readline, readline-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel, libXmu, libXmu-devel, libXi, libXi-devel
%endif
%if 0%{?fedora} == 12
BuildRequires: gcc, gcc-c++, SDL, SDL-devel, readline, readline-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel, libXmu, libXmu-devel, libXi, libXi-devel
%endif
%if 0%{?rhel_version} == 406
BuildRequires: gcc, gcc-c++, SDL, SDL-devel, ncurses, ncurses-devel, readline, readline-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel
%endif
%if 0%{?rhel_version} == 501
BuildRequires: gcc, gcc-c++, SDL, SDL-devel, ncurses, ncurses-devel, readline, readline-devel, freeglut, freeglut-devel, libjpeg, libjpeg-devel, ImageMagick, ImageMagick-devel, libXmu, libXmu-devel, libXi, libXi-devel
%endif

#!BuildIgnore: post-build-checks

%description
SAGE is a graphics streaming architecture for supporting collaborative scientific visualization environments with potentially hundreds of megapixels of contiguous display resolution. In collaborative scientific visualization, it is crucial to share high-resolution imagery as well as high-definition video among groups of collaborators at local or remote sites. The network-centered architecture of SAGE allows collaborators to simultaneously run various applications (such as 3D rendering, remote desktop, video streams and 2D maps) on local or remote clusters, and share them by streaming the pixels of each application over ultra-high-speed networks to large tiled displays. SAGE streaming architecture is designed so that the output of arbitrary M by N pixel rendering cluster nodes can be streamed to X by Y pixel display screens, allowing user-definable layouts on the display. The dynamic pixel routing capability of SAGE lets users freely move and resize each application's imagery over tiled displays in run-time, tightly synchronizing the multiple visualization streams to form a single stream.


%package devel  
License:        BSD
Summary:        Include Files mandatory for Development  
Group:          Graphics/Streaming
Requires:       sage = %{version}
 
%description devel
This package contains the necessary include files needed to develop SAGE applications.


%prep
%setup
%build
./configure
make
%install
make PREFIX=${RPM_BUILD_ROOT} install
%clean
%{__rm} -rf %{buildroot}  

%post
ldconfig

%files
%defattr(-,root,root)
/etc/profile.d/sage.csh
/etc/profile.d/sage.sh
/etc/ld.so.conf.d/sage.conf
/usr/local/sage/sageConfig/applications/applications.conf
/usr/local/sage/sageConfig/applications/imageviewer.conf
/usr/local/sage/sageConfig/applications/atlantis.conf
/usr/local/sage/sageConfig/applications/render.conf
/usr/local/sage/sageConfig/applications/VNCViewer.conf
/usr/local/sage/sageConfig/applications/bitplayer.conf
/usr/local/sage/sageConfig/sageBridge.conf
/usr/local/sage/sageConfig/stdtile.conf
/usr/local/sage/sageConfig/fsManager.conf
/usr/local/sage/sageConfig/stdtile-1.conf
/usr/local/sage/sageConfig/stdtile-20.conf
/usr/local/sage/sageConfig/stdtile-2.conf
/usr/local/sage/sageConfig/fileServer/fileServer.conf
/usr/local/sage/dim/device.py
/usr/local/sage/dim/overlays/__init__.py
/usr/local/sage/dim/overlays/wall.py
/usr/local/sage/dim/overlays/pointer.py
/usr/local/sage/dim/overlays/app.py
/usr/local/sage/dim/listener.py
/usr/local/sage/dim/devices/__init__.py
/usr/local/sage/dim/devices/puck.py
/usr/local/sage/dim/devices/joystick.py
/usr/local/sage/dim/devices/mouse.py
/usr/local/sage/dim/hwcapture/go.bat
/usr/local/sage/dim/hwcapture/pucks.py
/usr/local/sage/dim/hwcapture/localPointer.py
/usr/local/sage/dim/hwcapture/managerConn.py
/usr/local/sage/dim/hwcapture/joystick.py
/usr/local/sage/dim/hwcapture/mouse_to_joy.PIE
/usr/local/sage/dim/__init__.py
/usr/local/sage/dim/sageGate.py
/usr/local/sage/dim/overlayManager.py
/usr/local/sage/dim/dim.py
/usr/local/sage/dim/eventManager.py
/usr/local/sage/dim/sageGateBase.py
/usr/local/sage/dim/sageApp.py
/usr/local/sage/dim/deviceManager.py
/usr/local/sage/dim/events.py
/usr/local/sage/dim/eventHandler.py
/usr/local/sage/dim/globals.py
/usr/local/sage/dim/sageData.py
/usr/local/sage/dim/hwcapture.py
/usr/local/sage/dim/sageDisplayInfo.py
/usr/local/sage/dim/overlay.py
/usr/local/sage/bin/bplay-noglut
/usr/local/sage/bin/appLauncher/appLauncher.py
/usr/local/sage/bin/appLauncher/subprocess.py
/usr/local/sage/bin/appLauncher/myprint.py
/usr/local/sage/bin/appLauncher/data.py
/usr/local/sage/bin/appLauncher/KILL_LAUNCHER.py
/usr/local/sage/bin/appLauncher/admin.py
/usr/local/sage/bin/appLauncher/README
/usr/local/sage/bin/appLauncher/GO
/usr/local/sage/bin/appLauncher/request.py
/usr/local/sage/bin/VNCViewer
/usr/local/sage/bin/fsManager
/usr/local/sage/bin/subprocess.py
/usr/local/sage/bin/sageLauncher.py
/usr/local/sage/bin/sagePath.py
/usr/local/sage/bin/checker
/usr/local/sage/bin/atlantis
/usr/local/sage/bin/fsConsole
/usr/local/sage/bin/yuv.frag
/usr/local/sage/bin/uiConsole
/usr/local/sage/bin/render
/usr/local/sage/bin/sageProxy/sageUIDataInfo.py
/usr/local/sage/bin/sageProxy/SAGEGate.py
/usr/local/sage/bin/sageProxy/sageProxy.py
/usr/local/sage/bin/sageProxy/sageDisplayInfo.py
/usr/local/sage/bin/sageProxy/SAGEApp.py
/usr/local/sage/bin/fileServer/dirToDxt.py
/usr/local/sage/bin/fileServer/makeThumbs.py
/usr/local/sage/bin/fileServer/KILL_SERVER.py
/usr/local/sage/bin/fileServer/misc/countPDFpages.py
/usr/local/sage/bin/fileServer/misc/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/discinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/cdrommodule.c
/usr/local/sage/bin/fileServer/misc/mmpython/disc/audioinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/datainfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/vcdinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/lsdvd.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/dvdinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/ifomodule.c
/usr/local/sage/bin/fileServer/misc/mmpython/disc/CDDB.py
/usr/local/sage/bin/fileServer/misc/mmpython/disc/DiscID.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/jpginfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/IPTC.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/bins.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/tiffinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/ImageInfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/pnginfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/image/EXIF.py
/usr/local/sage/bin/fileServer/misc/mmpython/table.py
/usr/local/sage/bin/fileServer/misc/mmpython/version.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/eyeD3/tag.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/eyeD3/frames.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/eyeD3/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/eyeD3/binfuncs.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/eyeD3/utils.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/eyeD3/mp3.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/flacinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/ogginfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/eyed3info.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/pcminfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/m4ainfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/webradioinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/id3.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/mp3info.py
/usr/local/sage/bin/fileServer/misc/mmpython/audio/ac3info.py
/usr/local/sage/bin/fileServer/misc/mmpython/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/synchronizedobject.py
/usr/local/sage/bin/fileServer/misc/mmpython/mminfo
/usr/local/sage/bin/fileServer/misc/mmpython/COPYING
/usr/local/sage/bin/fileServer/misc/mmpython/doc/generate
/usr/local/sage/bin/fileServer/misc/mmpython/doc/.cvsignore
/usr/local/sage/bin/fileServer/misc/mmpython/PKG-INFO
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/iptc/iptc.pot
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/iptc/en.mo
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/iptc/en.po
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/qtudta/qtudta.pot
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/qtudta/en.mo
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/qtudta/en.po
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/aviinfo/en.mo
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/aviinfo/en.po
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/aviinfo/aviinfo.pot
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/id3v2/en.mo
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/id3v2/en.po
/usr/local/sage/bin/fileServer/misc/mmpython/i18n/id3v2/id3v2.pot
/usr/local/sage/bin/fileServer/misc/mmpython/README
/usr/local/sage/bin/fileServer/misc/mmpython/misc/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/misc/xmlinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/CREDITS
/usr/local/sage/bin/fileServer/misc/mmpython/MANIFEST.in
/usr/local/sage/bin/fileServer/misc/mmpython/video/movinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/mkvinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/mpeginfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/vcdinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/__init__.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/asfinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/ogminfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/movlanguages.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/fourcc.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/riffinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/video/realinfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/mediainfo.py
/usr/local/sage/bin/fileServer/misc/mmpython/setup.py
/usr/local/sage/bin/fileServer/misc/mmpython/factory.py
/usr/local/sage/bin/fileServer/misc/imsize.py
/usr/local/sage/bin/fileServer/fileServer.py
/usr/local/sage/bin/sageDisplayManager
/usr/local/sage/bin/sageBridge
/usr/local/sage/bin/bridgeConsole
/usr/local/sage/bin/imageviewer
/usr/local/sage/bin/sage
/usr/local/sage/bin/yuv.vert
/usr/local/sage/lib64/libquanta.so
/usr/local/sage/lib64/libsail.so
/usr/local/sage/ui/Graph.py
/usr/local/sage/ui/fileViewer.py
/usr/local/sage/ui/canvases.py
/usr/local/sage/ui/images/back_up.jpg
/usr/local/sage/ui/images/pause_up.jpg
/usr/local/sage/ui/images/atlantis_down.jpg
/usr/local/sage/ui/images/play_over.jpg
/usr/local/sage/ui/images/no_preview.png
/usr/local/sage/ui/images/hdmovie_up.jpg
/usr/local/sage/ui/images/teravision_up.jpg
/usr/local/sage/ui/images/SAGEapp_19.jpg
/usr/local/sage/ui/images/vra_down.jpg
/usr/local/sage/ui/images/minimize_shape.gif
/usr/local/sage/ui/images/SAGEapp_08.jpg
/usr/local/sage/ui/images/stats_BW_up.jpg
/usr/local/sage/ui/images/inst_down.jpg
/usr/local/sage/ui/images/gadgets_up.jpg
/usr/local/sage/ui/images/default_down.jpg
/usr/local/sage/ui/images/red_circle.gif
/usr/local/sage/ui/images/handle1.jpg
/usr/local/sage/ui/images/play_down.jpg
/usr/local/sage/ui/images/render_up.jpg
/usr/local/sage/ui/images/magicarpet_down.jpg
/usr/local/sage/ui/images/faster_down.jpg
/usr/local/sage/ui/images/stats_BW_over.jpg
/usr/local/sage/ui/images/stop_over.jpg
/usr/local/sage/ui/images/default_over.jpg
/usr/local/sage/ui/images/stats_FPS_down.jpg
/usr/local/sage/ui/images/stop_down.jpg
/usr/local/sage/ui/images/slower_up.jpg
/usr/local/sage/ui/images/stats_FPS_over.jpg
/usr/local/sage/ui/images/bitplay_over.jpg
/usr/local/sage/ui/images/rotate_shape.gif
/usr/local/sage/ui/images/back_over.jpg
/usr/local/sage/ui/images/magicarpet_up.jpg
/usr/local/sage/ui/images/inst_up.jpg
/usr/local/sage/ui/images/app_panel_background.png
/usr/local/sage/ui/images/stats_Nodes_over.jpg
/usr/local/sage/ui/images/scrollRight_down.jpg
/usr/local/sage/ui/images/SAGEapp_14.jpg
/usr/local/sage/ui/images/bitplay_down.jpg
/usr/local/sage/ui/images/mplayer_over.jpg
/usr/local/sage/ui/images/teravision_down.jpg
/usr/local/sage/ui/images/svc_down.jpg
/usr/local/sage/ui/images/handle.jpg
/usr/local/sage/ui/images/stats_BW_down.jpg
/usr/local/sage/ui/images/gadgets_down.jpg
/usr/local/sage/ui/images/stats_Streams_down.jpg
/usr/local/sage/ui/images/scrollLeft_down.jpg
/usr/local/sage/ui/images/remote_down.jpg
/usr/local/sage/ui/images/stop_up.jpg
/usr/local/sage/ui/images/mplayer_up.jpg
/usr/local/sage/ui/images/vncviewer_up.jpg
/usr/local/sage/ui/images/juxtaview_up.jpg
/usr/local/sage/ui/images/SAGEapp_01.jpg
/usr/local/sage/ui/images/teravision_over.jpg
/usr/local/sage/ui/images/remote_over.jpg
/usr/local/sage/ui/images/mplayer_down.jpg
/usr/local/sage/ui/images/play_up.jpg
/usr/local/sage/ui/images/scrollRight_up.jpg
/usr/local/sage/ui/images/app_info_background.png
/usr/local/sage/ui/images/atlantis_up.jpg
/usr/local/sage/ui/images/remote_up.jpg
/usr/local/sage/ui/images/juxtaview_over.jpg
/usr/local/sage/ui/images/stats_FPS_up.jpg
/usr/local/sage/ui/images/SAGEapp_15.jpg
/usr/local/sage/ui/images/default_up.jpg
/usr/local/sage/ui/images/back_down.jpg
/usr/local/sage/ui/images/reset_down.jpg
/usr/local/sage/ui/images/slower_over.jpg
/usr/local/sage/ui/images/SAGEapp_07.jpg
/usr/local/sage/ui/images/SAGEapp_17.jpg
/usr/local/sage/ui/images/pause_over.jpg
/usr/local/sage/ui/images/SAGEapp_04.jpg
/usr/local/sage/ui/images/svc_up.jpg
/usr/local/sage/ui/images/slower_down.jpg
/usr/local/sage/ui/images/juxtaview_down.jpg
/usr/local/sage/ui/images/menu_bar.jpg
/usr/local/sage/ui/images/close_shape.gif
/usr/local/sage/ui/images/retrieving_preview.png
/usr/local/sage/ui/images/scrollLeft_up.jpg
/usr/local/sage/ui/images/stats_Nodes_down.jpg
/usr/local/sage/ui/images/vncviewer_down.jpg
/usr/local/sage/ui/images/svc_over.jpg
/usr/local/sage/ui/images/help.png
/usr/local/sage/ui/images/gadgets_over.jpg
/usr/local/sage/ui/images/atlantis_over.jpg
/usr/local/sage/ui/images/SAGEapp_05.jpg
/usr/local/sage/ui/images/stats_green.jpg
/usr/local/sage/ui/images/green_circle.gif
/usr/local/sage/ui/images/render_down.jpg
/usr/local/sage/ui/images/magicarpet_over.jpg
/usr/local/sage/ui/images/faster_up.jpg
/usr/local/sage/ui/images/SAGEapp_10.jpg
/usr/local/sage/ui/images/stats_Streams_up.jpg
/usr/local/sage/ui/images/hdmovie_over.jpg
/usr/local/sage/ui/images/SAGEapp_02.jpg
/usr/local/sage/ui/images/bitplay_up.jpg
/usr/local/sage/ui/images/vra_up.jpg
/usr/local/sage/ui/images/stats_Streams_over.jpg
/usr/local/sage/ui/images/maximize_shape.gif
/usr/local/sage/ui/images/hdmovie_down.jpg
/usr/local/sage/ui/images/pause_down.jpg
/usr/local/sage/ui/images/faster_over.jpg
/usr/local/sage/ui/images/SAGEapp_06.jpg
/usr/local/sage/ui/images/scrollRight_over.jpg
/usr/local/sage/ui/images/SAGEapp_18.jpg
/usr/local/sage/ui/images/stats_Nodes_up.jpg
/usr/local/sage/ui/images/SAGEapp_03.jpg
/usr/local/sage/ui/images/scrollLeft_over.jpg
/usr/local/sage/ui/preferences.py
/usr/local/sage/ui/sageGate.py
/usr/local/sage/ui/pointers.py
/usr/local/sage/ui/Mywx.py
/usr/local/sage/ui/SAGEShape.py
/usr/local/sage/ui/sageGateBase.py
/usr/local/sage/ui/sageApp.py
/usr/local/sage/ui/launcherAdmin.py
/usr/local/sage/ui/sageui.py
/usr/local/sage/ui/sageAppPerfInfo.py
/usr/local/sage/ui/help.py
/usr/local/sage/ui/misc/__init__.py
/usr/local/sage/ui/misc/imsize.py
/usr/local/sage/ui/SAGEDrawObject.py
/usr/local/sage/ui/globals.py
/usr/local/sage/ui/sageData.py
/usr/local/sage/ui/users.py
/usr/local/sage/ui/sageDisplayInfo.py
/usr/local/sage/ui/setup.py
/usr/local/sage/ui/connectionManager/admin.py
/usr/local/sage/ui/connectionManager/README
/usr/local/sage/ui/connectionManager/ConnectionManager.py
/usr/local/sage/ui/SAGESession.py

%files devel  
%defattr(-,root,root)
/usr/local/sage/include/appInstance.h
/usr/local/sage/include/appleMultiContext.h
/usr/local/sage/include/audioConverter.h
/usr/local/sage/include/audioFileReader.h
/usr/local/sage/include/audioFileWriter.h
/usr/local/sage/include/audioFormatManager.h
/usr/local/sage/include/displayContext.h
/usr/local/sage/include/displayInstance.h
/usr/local/sage/include/envInterface.h
/usr/local/sage/include/fsClient.h
/usr/local/sage/include/fsCore.h
/usr/local/sage/include/fsManager.h
/usr/local/sage/include/fsServer.h
/usr/local/sage/include/messageInterface.h
/usr/local/sage/include/misc.h
/usr/local/sage/include/overlayApp.h
/usr/local/sage/include/overlayPointer.h
/usr/local/sage/include/pixelDownloader.h
/usr/local/sage/include/sageAppAudio.h
/usr/local/sage/include/sageAudioBridge.h
/usr/local/sage/include/sageAudioCircBuf.h
/usr/local/sage/include/sageAudio.h
/usr/local/sage/include/sageAudioManager.h
/usr/local/sage/include/sageAudioModule.h
/usr/local/sage/include/sageAudioReceiver.h
/usr/local/sage/include/sageAudioSync.h
/usr/local/sage/include/sageBase.h
/usr/local/sage/include/sageBlock.h
/usr/local/sage/include/sageBlockPartition.h
/usr/local/sage/include/sageBlockPool.h
/usr/local/sage/include/sageBlockQueue.h
/usr/local/sage/include/sageBridge.h
/usr/local/sage/include/sageBuf.h
/usr/local/sage/include/sageConfig.h
/usr/local/sage/include/sageDisplay.h
/usr/local/sage/include/sageDisplayManager.h
/usr/local/sage/include/sageDoubleBuf.h
/usr/local/sage/include/sageDraw.h
/usr/local/sage/include/sageDrawObject.h
/usr/local/sage/include/sageEvent.h
/usr/local/sage/include/sageFrame.h
/usr/local/sage/include/sage.h
/usr/local/sage/include/sagePixelType.h
/usr/local/sage/include/sageReceiver.h
/usr/local/sage/include/sageRect.h
/usr/local/sage/include/sageSharedData.h
/usr/local/sage/include/sageStreamer.h
/usr/local/sage/include/sageSync.h
/usr/local/sage/include/sageTcpModule.h
/usr/local/sage/include/sageUdpModule.h
/usr/local/sage/include/sageVersion.h
/usr/local/sage/include/sageVirtualDesktop.h
/usr/local/sage/include/sail.h
/usr/local/sage/include/sdlSingleContext.h
/usr/local/sage/include/streamInfo.h
/usr/local/sage/include/streamProtocol.h
/usr/local/sage/include/suil.h
/usr/local/sage/include/tileConfig.h
/usr/local/sage/include/wavConverter.h
