# Introduction #

We changed the way files are stored and search for in a SAGE installation.

# Details #

The changes are the following:
  * "make install" installs sage into $PREFIX/usr/local/sage  (change PREFIX in Makefile)
  * the default config files are now all in "$SAGE\_DIRECTORY/sageConfig" and those shouldn't change.
  * Change configuration files: do so in $HOME/.sageConfig where each user can change them without screwing up the default installation. They will automatically be loaded from there first if they exist there.
  * By default, file library is also per-user in $HOME/.sageConfig/fileServer/fileLibrary.... or any other path as specified in fileServer.conf
  * sage.conf became applications.conf
  * file\_server became fileServer
  * usersServer became connectionManager

# Components #

The search path order for each component is here:


| **Component** | **Config + other file(s)** | **Search path order** |
|:--------------|:---------------------------|:----------------------|
| fsManager     | fsManager.conf             | $PWD ---> ~/.sageConfig ---> $SAGE\_DIRECTORY/sageConfig/ |
|               | stdtile.conf               | $PWD ---> ~/.sageConfig ---> $SAGE\_DIRECTORY/sageConfig/ |
| sageBridge    | sageBridge.conf            | $PWD ---> ~/.sageConfig ---> $SAGE\_DIRECTORY/sageConfig/ |
| appLauncher   | applications.conf          | $PWD ---> ~/.sageConfig/applications ---> $SAGE\_DIRECTORY/sageConfig/applications |
|               | app.conf (e.g. render.conf)| $PWD ---> ~/.sageConfig/applications ---> $SAGE\_DIRECTORY/sageConfig/applications |
| sageLauncher  | sageLauncherSettings.pickle| ~/.sageConfig         |
|               | generated applications.conf & fileServer.conf| ~/.sageConfig         |
| FileServer    | fileServer.conf            | $PWD ---> ~/.sageConfig/fileServer ---> $SAGE\_DIRECTORY/sageConfig/fileServer |
|               | fileLibrary directory      | ~/.sageConfig/fileServer |
| SageUI        | saved-states               | ~/.sageConfig/saved-states |
|               | data, log, prefs           | ~/.sageConfig/sageui  |