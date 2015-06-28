# Introduction #

For instance, in a header file:

```
/*
 * $Rev::                                 $
 * $Author::                              $
 * $Date::                                $
*/
```

# Details #

Then add the substitution property to the file:

```
svn propset svn:keywords "Rev Author Date"   toto.h
```

# Global version number #

In the root directory of the source tree, run the command:
```
   svnversion -n .
```