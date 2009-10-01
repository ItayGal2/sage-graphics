/******************************************************************************
 * SAGE - Scalable Adaptive Graphics Environment
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

#ifndef SVC_OUTPUT_SAIL_H
#define SVC_OUTPUT_SAIL_H

#include "SVC_output_module.h"
#include <pthread.h>
#include "sail.h"
#include "misc.h"

class SVC_output_sail: public SVC_output_module
{
public:
    SVC_output_sail();
    void init2();
    void push_data(unsigned char* buf , int width, int height, int b_pixel);
    unsigned char* init(int width, int height, int b_pixel,char* output_addr, int output_port);

private:
    pthread_t outputThreadID;
    int m_width;
    int m_height;
    int m_byte_pixel;
    int m_color_mode;
    int m_flag_done;
    unsigned char* m_inter_buffer;
    sail sageInf;
    int m_flag_notinit;
    char* m_output_addr;
    int m_output_port;
    int framenum;
};
#endif
