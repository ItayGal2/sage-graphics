/******************************************************************************
 * Fast DXT - a realtime DXT compression tool
 *
 * Author : Luc Renambot
 *
 * Copyright (C) 2004 Electronic Visualization Laboratory,
 * University of Illinois at Chicago
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *  * Redistributions in binary form must reproduce the above
 *    copyright notice, this list of conditions and the following disclaimer
 *    in the documentation and/or other materials provided with the distribution.
 *  * Neither the name of the University of Illinois at Chicago nor
 *    the names of its contributors may be used to endorse or promote
 *    products derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
 * LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 * NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * Direct questions, comments etc about SAGE to http://www.evl.uic.edu/cavern/forum/
 *
 *****************************************************************************/

#include "util.h"


#if defined(WIN32)
#include <io.h>
#endif

#if !defined(WIN32)
#include <sys/stat.h>
#include <unistd.h>
#endif

#include <fcntl.h>



void *aligned_malloc(size_t size, size_t align_size) {

  char *ptr,*ptr2,*aligned_ptr;
  int align_mask = (int)align_size - 1;

  ptr=(char *)malloc(size + align_size + sizeof(int));
  if(ptr==NULL) return(NULL);

  ptr2 = ptr + sizeof(int);
  aligned_ptr = ptr2 + (align_size - ((size_t)ptr2 & align_mask));


  ptr2 = aligned_ptr - sizeof(int);
  *((int *)ptr2)=(int)(aligned_ptr - ptr);

  return(aligned_ptr);
}

void aligned_free(void *ptr)
{
	int *ptr2=(int *)ptr - 1;
	ptr = (char*)ptr - *ptr2;
	free(ptr);
}


/// File findind
// From Nvidia toolkit

using namespace std;

string data_path::get_path(std::string filename)
{
  FILE* fp;
  bool found = false;
  for(unsigned int i=0; i < path.size(); i++)
    {
      path_name = path[i] + "/" + filename;
      fp = ::fopen(path_name.c_str(), "r");

      if(fp != 0)
        {
	  fclose(fp);
	  found = true;
	  break;
        }
    }

  if (found == false)
    {
      path_name = filename;
      fp = ::fopen(path_name.c_str(),"r");
      if (fp != 0)
        {
	  fclose(fp);
	  found = true;
        }
    }

  if (found == false)
    return "";

  int loc = path_name.rfind('\\');
  if (loc == -1)
    {
      loc = path_name.rfind('/');
    }

  if (loc != -1)
    file_path = path_name.substr(0, loc);
  else
    file_path = ".";
  return file_path;
}

string data_path::get_file(std::string filename)
{
  FILE* fp;

  for(unsigned int i=0; i < path.size(); i++)
    {
      path_name = path[i] + "/" + filename;
      fp = ::fopen(path_name.c_str(), "r");

      if(fp != 0)
        {
	  fclose(fp);
	  return path_name;
        }
    }

  path_name = filename;
  fp = ::fopen(path_name.c_str(),"r");
  if (fp != 0)
    {
      fclose(fp);
      return path_name;
    }
  return "";
}

// data files, for read only
FILE * data_path::fopen(std::string filename, const char * mode)
{

  for(unsigned int i=0; i < path.size(); i++)
    {
      std::string s = path[i] + "/" + filename;
      FILE * fp = ::fopen(s.c_str(), mode);

      if(fp != 0)
	return fp;
      else if (!strcmp(path[i].c_str(),""))
	{
	  FILE* fp = ::fopen(filename.c_str(),mode);
	  if (fp != 0)
	    return fp;
	}
    }
  // no luck... return null
  return 0;
}

//  fill the file stats structure
//  useful to get the file size and stuff
int data_path::fstat(std::string filename,
#ifdef WIN32
		     struct _stat
#else
		     struct stat
#endif
		     * stat)
{
  for(unsigned int i=0; i < path.size(); i++)
    {
      std::string s = path[i] + "/" + filename;
#ifdef WIN32
      int fh = ::_open(s.c_str(), _O_RDONLY);
#else
      int fh = ::open(s.c_str(), O_RDONLY);
#endif
      if(fh >= 0)
        {
#ifdef WIN32
	  int result = ::_fstat( fh, stat );
#else
	  int result = ::fstat (fh,stat);
#endif
	  if( result != 0 )
            {
	      fprintf( stderr, "An fstat error occurred.\n" );
	      return 0;
            }
#ifdef WIN32
	  ::_close( fh );
#else
	  ::close (fh);
#endif
	  return 1;
    	}
    }
  // no luck...
  return 0;
}