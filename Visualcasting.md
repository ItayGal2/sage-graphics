## Introduction ##

SAGE Visualcasting service connects distantly located multiple tiled displays driven by SAGE so that users can share their visualization on those tiled displays while communicating each other via multi-point HD video conferencing supported by Visualcasting.
SAGE Bridge is a SAGE component that enables Visualcasting service. The SAGE Bridge hardware is a cluster of high-performance PCs equipped with 10Gbit Ethernet interfaces. The SAGE Bridge software running on the PC cluster receives pixel streams from applications and distributes to multiple SAGE sessions (a fsManager per session).


## Visualcasting instruction using SAGE Bridge ##

  1. Install SAGE on the SAGE Bridge nodes
    * If your bridge nodes don't have a graphics card,
      * Set SAIL\_ONLY=1 in $SAGE\_DIRECTORY/config.mk
      * Set PROJ\_EXEC=sageBridge bridgeConsole in the Makefile in $SAGE\_DIRECTORY/src directory.
      * Then, build SAGE. Other binaries (fsManager, sageDisplayManager, and so on) won't be built. <br><br>
</li></ul>  1. Edit sageBridge.conf in $SAGE\_DIRECTORY/bin
    * masterIP : the ip address of master node of SAGE Bridge cluster
    * slaveList slaveNum ip1 ip2 ip3 ... : the slave node list of SAGE Bridge cluster (note: for configuring single-node SAGE Bridge, set the slave number to zero)
    * streamPort : base port number to be used for the pixel streams between apps and SAGE Bridge
    * msgPort : message channel port number
    * syncPort : synchronization channel port number
    * rcvNwBufSize, sendNwBufSize, MTU : network parmeters used for the pixel streams between apps and SAGE Bridge <br><br>
</li></ul>  1. Execute the binary "sageBridge" in $SAGE\_DIRECTORY/bin. Users can specify a configuration file name as command-line argument. Otherwise "sageBridge.conf" is used. <br><br>
<ol><li>Execute "fsManager" on display clusters <br><br>
</li><li>You have two options to launch an app for Visualicasting using SAGE Bridge<br>
<ul><li>By command line (test and debugging purpose)<br>
<ul><li>Make sure app configuration file (e.g. render.conf, atlantis.conf, ....) includes following items:<br>
<pre><code>bridgeOn true : determine whether this app uses sageBridge or not<br>
bridgeIP 192.168.81.1 : master IP of SAGE Bridge<br>
bridgePort 42000 : message port of SAGE Bridge<br>
fsIP     192.168.81.11<br>
fsPort   20002 : IP and system port of the first fsManager<br>
</code></pre>
</li><li>By setting bridgeOn true, an app is trying to connect to the SAGE Bridge rather than a FSManager.<br>
</li></ul></li><li>By SAGE Launcher (after confirming SAGE Bridge is working)<br>
<ul><li>Set the bridge parameters above in an app configuration using SAGE Launcher (advanced mode).<br>
</li><li>Start the app with a right-click on the app icon in the SAGE UI. The app uses sageBridge and can then be shared with other SAGE sessions. <br><br>
</li></ul></li></ul></li><li>If users want to share this app to another SAGE session through SAGE UI, just drag an application window from one SAGE session onto the tab of the other session and the app will be shared (obviously the UI must be connected to both SAGE sessions for this to work) <br><br>
</li><li>Alternatively, you can share the applications using uiConsole:<br>
<ul><li>Execute "uiConsole" to be connected to the first fsManager<br>
<blockquote>uiConsole fsManager-1.conf (config file for the first fsManager)<br>
</blockquote></li><li>Execute following command<br>
<pre><code>share appID fsIP2 fsPort2 <br>
    appIDs : assigned in execution order ex) 0, 1, 2,...<br>
    fsIP2, fsPort2 : IP and port number of the second fsManager<br>
</code></pre></li></ul></li></ol>

<blockquote>Then, the app window shows up on the second SAGE session.</blockquote>

<h2>Links to other pages</h2>

<a href='SAGE.md'>Home</a>