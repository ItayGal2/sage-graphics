
---


### Prerequisite ###
For SAGE: the runtime and development packages of the following libraries

  * SDL 1.2.8 or later : http://www.libsdl.org<br>Most Linux distributions include the SDL runtime package in default and the development package as an option.</li></ul>

<ul><li>readline 5.0 or later : <a href='http://tiswww.case.edu/php/chet/readline/rltop.html'>http://tiswww.case.edu/php/chet/readline/rltop.html</a><br>Most Linux distributions include the readline runtime package in default and the development package as an option.</li></ul>


For SAGE UI components:
  * python 2.3 or later
  * wxPython 2.6.2 or later
  * Numpy or Numeric


---


### Setup environment ###
  1. Set an environment variable SAGE\_DIRECTORY in your login profile: .profile, .bashrc, .tcshrc, and so on.
```
  setenv SAGE_DIRECTORY sage_path (for tcsh or similar)
  export SAGE_DIRECTORY=sage_path (for bash or similar)

  'sage_path' is the path to the root directory of your SAGE installation. 
  If you install SAGE3.0 in {$HOME}/local, sage_path is {$HOME}/local/sage3.0.
```
  1. Add $SAGE\_DIRECTORY/bin to your PATH in your login profile
```
  set path=($SAGE_DIRECTORY/bin $path)   (for tcsh or similar)
  export PATH=$SAGE_DIRECTORY/bin:$PATH  (for bash or similar)
```

---


### Modify build configuration ###

  1. Open config.mk in SAGE\_DIRECTORY


---


### Compile ###

  1. Execute make in SAGE\_DIRECTORY
  1. If you get errors, check include paths and library paths in make files in subdirectories
  1. Execute make install in SAGE\_DIRECTORY



---


## Links to other pages ##

[Home](SAGE.md)