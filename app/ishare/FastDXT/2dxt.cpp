/******************************************************************************
 * Fast DXT - a realtime DXT compression tool
 *
 * Author : Luc Renambot
 *
 * Copyright (C) 2007 Electronic Visualization Laboratory,
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

//
// Usage: ./2dxt width height type rawfile dxtfile
//

#define NUMTHREAD 2

#include "libdxt.h"

int
main(int argc, char** argv)
{
  byte *in;
  byte *out;
  int nbbytes;

  if (argc != 6)
  {
	fprintf(stderr, "Usage: ./2dxt width height type rawfile dxtfile\n");
	exit(0);
  }
	// Initialize some timing functions and else
  aInitialize();

  /*
    Read an image.
  */
  unsigned long width = atoi(argv[1]);
  unsigned long height = atoi(argv[2]);

  int format = 1;
  format = atoi(argv[3]);

  in = (byte*)memalign(16, width*height*4);
  memset(in, 0, width*height*4);

  FILE *f=fopen(argv[4], "rb");
  int res=(int)fread(in, 1, width*height*4, f);
  fclose(f);

  out = (byte*)memalign(16, width*height*4);
  memset(out, 0, width*height*4);

  fprintf(stderr, "Converting to raw: %ldx%ld\n", width, height);

  double t1, t2;
  t1 = aTime();
  nbbytes = 0;
  switch (format) {
  case 1:
    nbbytes = CompressDXT(in, out, width, height, FORMAT_DXT1, NUMTHREAD);
    fprintf(stderr, "Converted to DXT1: from %d bytes to %ld bytes\n",
	    width*height*4, nbbytes);
    break;
  case 5:
    nbbytes = CompressDXT(in, out, width, height, FORMAT_DXT5, NUMTHREAD);
    fprintf(stderr, "Converted to DXT5: from %d bytes to %ld bytes\n",
	  width*height*4, nbbytes);
    break;
  case 6:
    nbbytes = CompressDXT(in, out, width, height, FORMAT_DXT5YCOCG, NUMTHREAD);
    fprintf(stderr, "Converted to DXT5-YCoCg: from %d bytes to %ld bytes\n",
	    width*height*4, nbbytes);
    break;
  }
  t2 = aTime();

  fprintf(stderr, "Time %.2f sec, Freq %.2f Hz\n",
	  t2-t1, 1.0/(t2-t1) );
  fprintf(stderr, "MP/sec %.2f\n",
          ((double)(width*height)) / ((t2-t1)*1000000.0) );

  FILE *g=fopen(argv[5], "wb+");
  fwrite(&width, 4, 1, g);
  fwrite(&height, 4, 1, g);
  int res2=(int)fwrite(out, 1, nbbytes, g);
  fclose(g);

  memfree(in);
  memfree(out);

  return 0;
}

