/*
 * FILE:   rtp_callback.h
 * AUTHOR: Colin Perkins <csp@csperkins.org>
 *
 * Copyright (c) 2001-2003 University of Southern California
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, is permitted provided that the following conditions
 * are met:
 * 
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 
 * 3. All advertising materials mentioning features or use of this software
 *    must display the following acknowledgement:
 * 
 *      This product includes software developed by the University of Southern
 *      California Information Sciences Institute.
 * 
 * 4. Neither the name of the University nor of the Institute may be used
 *    to endorse or promote products derived from this software without
 *    specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE AUTHORS AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING,
 * BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
 * EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 */

#include "host.h"

/*
 * Packet formats:
 * http://www.cesnet.cz/doc/techzpravy/2010/4k-packet-format/
 */
#define PT_VIDEO 20
#define PT_AUDIO 21
#define PT_VIDEO_LDGM 22

typedef struct {
        /* first word */
        uint32_t substream_bufnum; /* bits 0 - 9 substream
                                      bits 10 - 31 buffer  */

        /* second word */
        uint32_t offset;

        /* third word */
        uint32_t length;

        /* fourth word */
        uint16_t hres;
        uint16_t vres;

        /* fifth word */
        uint32_t fourcc;
        
        /* sixth word */
        uint32_t il_fps; /* bits 0 - 2 interlace flag
                            bits 3 - 12 FPS
                            bits 13 - 16 FPSd
                            bit 17 Fd
                            bit 18 Fi */

} __attribute__((__packed__)) video_payload_hdr_t;


typedef struct {
        /* first word */
        uint32_t substream_bufnum; /* bits 0 - 9 substream
                                      bits 10 - 31 buffer */

        /* second word */
        uint32_t offset;

        /* third word */
        uint32_t length;

        /* fourth word */
        uint32_t quant_sample_rate; /* bits 0 - 5 audio quant.
                                       bits 6 - 31 audio sample rate */

        /* fifth word */
        uint32_t audio_tag;
} __attribute__((__packed__)) audio_payload_hdr_t;

typedef struct {
        /* first word */
        uint32_t substream_bufnum; /* bits 0 - 9 substream
                                      bits 10 - 31 buffer  */

        /* second word */
        uint32_t offset;

        /* third word */
        uint32_t length;

        /* fourth word */
        uint32_t k_m_c; /* bits 0-8 (k>>5)
                           bits 9-17 (m>>5)
                           18 - 22 c 
                           23 - 31 currently unused (must be 0)
                           */

        /* fifth word */
        uint32_t seed;
} __attribute__((__packed__)) ldgm_payload_hdr_t;


void rtp_recv_callback(struct rtp *session, rtp_event *e);
int handle_with_buffer(struct rtp *session,rtp_event *e);
int check_for_frame_completion(struct rtp *);
void process_packet_for_display(char *);
void call_display_frame(void);
