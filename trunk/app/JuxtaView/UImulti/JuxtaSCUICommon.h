/*=============================================================================

  Program: JuxtaView for SAGE
  Module:  JuxtaSCUICommon.h - Part of JuxtaView's UI
  Authors: Arun Rao, arao@evl.uic.edu,
           Ratko Jagodic, rjagodic@evl.uic.edu,
           Nicholas Schwarz, schwarz@evl.uic.edu,
           et al.
  Date:    30 September 2004
  Modified: 9 September 2005

  Copyright (c) 2005 Electronic Visualization Laboratory,
                     University of Illinois at Chicago

  All rights reserved.
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



#ifndef JUXTASCUI_COMMON_H
#define JUXTASCUI_COMMON_H

#define TRANSMISSION_SIZE 10	//send 10 bytes at a time

//Messages To Transmit
#define JVPAN_LEFT "jvleft"
#define JVPAN_RIGHT "jvright"
#define JVPAN_UP "jvup"
#define JVPAN_DOWN "jvdown"
#define JVFAST_PAN_LEFT "jvfleft"
#define JVFAST_PAN_RIGHT "jvfright"
#define JVFAST_PAN_UP "jvfup"
#define JVFAST_PAN_DOWN "jvfdown"
#define JVZOOM_OUT "jvzoomout"
#define JVZOOM_IN "jvzoomin"
#define JVEXTENTS "jvextent"
#define JVOVERVIEW "jvoverv"
#define JVTRANSLATE "jvfreepan"
#define JVQUIT "jvquit"
#define JVRESEND "jvresend"


#endif
